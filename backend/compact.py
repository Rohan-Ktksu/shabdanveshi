"""Compact retrieval with bounded caches and a memory-aware inference worker."""
from collections import Counter
from contextlib import closing
import json
import re
import sqlite3
import unicodedata
import numpy as np
import regex
from .config import DATA
from .cache import ExpiringCache
from .inference import InferenceWorker
from .memory import release_unused_memory
from .query_tokenizer import ensure_prepared


def normalize(text):
    return unicodedata.normalize('NFC', text).casefold().strip()


def letter_count(text):
    return sum(bool(regex.search(r'\p{L}', c)) for c in regex.findall(r'\X', text))


class CompactFinder:
    def __init__(self):
        self.folder = DATA / 'compact'
        self.metadata = json.loads((self.folder / 'metadata.json').read_text(encoding='utf-8'))
        if self.metadata.get('compact_version') != 1:
            raise ValueError('Unsupported compact index')
        self.stop_words = set(self.metadata['stop_words'])
        self.last_translation = None
        for name in ['dictionary.sqlite', 'vectors.npy', 'norms.npy', 'bridge_target.npy', 'bridge_source.npy', 'posting_rows.npy', 'posting_values.npy']:
            if not (self.folder / name).is_file():
                raise ValueError(f'Missing compact index asset: {name}')
        self.worker = InferenceWorker()
        self.inference_cache = ExpiringCache(64)
        self.score_cache = ExpiringCache(4)  # About 7 MiB for the current corpus.
        self.result_cache = ExpiringCache(64)
        release_unused_memory()
        ensure_prepared()
        release_unused_memory()

    def close(self):
        self.worker.close()
        self.inference_cache.clear()
        self.score_cache.clear()
        self.result_cache.clear()

    def infer(self, mode, text):
        key = (mode, text)
        hit, value = self.inference_cache.get(key)
        if not hit:
            value = self.worker.request(mode, text)
            self.inference_cache.put(key, value)
        return value

    def compute_scores(self, text, vector):
        mapped = []
        def load(name):
            value = np.load(self.folder / name, mmap_mode='r')
            mapped.append(value)
            return value
        try:
            matrix, norms = load('vectors.npy'), load('norms.npy')
            semantic = np.empty(len(matrix), dtype=np.float32)
            for start in range(0, len(matrix), 4096):
                semantic[start:start+4096] = matrix[start:start+4096].astype(np.float32) @ vector / norms[start:start+4096]
            lexical = np.zeros(len(matrix), dtype=np.float32)
            tokens = [t for t in re.findall(r'(?u)\b\w\w+\b', text.lower()) if t not in self.stop_words]
            counts = Counter(tokens + [' '.join(tokens[i:i+2]) for i in range(len(tokens)-1)])
            uri = (self.folder / 'dictionary.sqlite').as_uri() + '?mode=ro'
            with closing(sqlite3.connect(uri, uri=True)) as db:
                terms = []
                for term, count in counts.items():
                    row = db.execute('SELECT idf,start,stop FROM terms WHERE term=?', (term,)).fetchone()
                    if row:
                        terms.append((count * row[0], row[1], row[2]))
                denominator = np.sqrt(sum(t[0]**2 for t in terms)) or 1.
                posting_rows, posting_values = load('posting_rows.npy'), load('posting_values.npy')
                for weight, start, stop in terms:
                    np.add.at(lexical, posting_rows[start:stop], posting_values[start:stop] * (weight / denominator))
            scores = semantic + 0.05 * lexical
            target, source = load('bridge_target.npy'), load('bridge_source.npy')
            original = scores.copy()
            np.maximum.at(scores, target, original[source])
            for array in (semantic, lexical, scores):
                array.flags.writeable = False
            return semantic, lexical, scores
        finally:
            for array in mapped:
                array._mmap.close()

    def rank(self, query, semantic, lexical, scores):
        uri = (self.folder / 'dictionary.sqlite').as_uri() + '?mode=ro'
        with closing(sqlite3.connect(uri, uri=True)) as db:
            # SQLite filters dictionary metadata before Python decodes candidates.
            # Prefixes use the same Unicode normalization as the final alias check.
            filters, parameters = [], []
            if query.starting_letter and query.language != 'both':
                filters.append("json_extract(payload,'$.language') = ?")
                parameters.append(query.language)
            if query.starting_letter and query.part_of_speech:
                filters.append("json_extract(payload,'$.part_of_speech') = ?")
                parameters.append(query.part_of_speech)
            if query.starting_letter:
                db.create_function('prefix_match', 1, lambda word: int(normalize(word).startswith(query.starting_letter)))
                filters.append("(prefix_match(json_extract(payload,'$.word')) OR EXISTS (SELECT 1 FROM json_each(entries.payload,'$.aliases') WHERE prefix_match(value)))")
            if filters:
                sql = 'SELECT id FROM entries WHERE ' + ' AND '.join(filters) + ' ORDER BY id'
                ids = np.fromiter((row[0] for row in db.execute(sql, parameters)), dtype=np.int64)
            else:
                # Common searches need only a handful of ranked dictionary rows.
                # Avoid scanning/decoding the full SQLite table just to filter language.
                ids = np.arange(len(scores))
            order = ids[np.argsort(-scores[ids], kind='stable')]
            results, seen = [], set()
            # Batch reads avoid up to 150,041 individual SQL calls for narrow clues.
            for start in range(0, len(order), 256):
                batch = order[start:start+256]
                placeholders = ','.join('?' for _ in batch)
                records = dict(db.execute(f'SELECT id,payload FROM entries WHERE id IN ({placeholders})', batch.tolist()))
                for index in batch:
                    entry = json.loads(records[int(index)])
                    if query.language != 'both' and entry['language'] != query.language:
                        continue
                    if query.part_of_speech and entry['part_of_speech'] != query.part_of_speech:
                        continue
                    word = next((w for w in [entry['word'], *entry['aliases']]
                                 if (not query.starting_letter or normalize(w).startswith(query.starting_letter))
                                 and (query.approximate_length is None or abs(letter_count(w)-query.approximate_length) <= 1)
                                 and (entry['language'], normalize(w)) not in seen), None)
                    if word is None:
                        continue
                    seen.add((entry['language'], normalize(word)))
                    results.append({k: v for k, v in {**entry, 'word': word,
                        'score': round(float(semantic[index]), 4), 'semantic_score': round(float(semantic[index]), 4),
                        'tfidf_score': round(float(lexical[index]), 4)}.items() if k not in ('id', 'aliases')})
                    if len(results) == query.limit:
                        return results
            return results

    def search(self, query):
        # Filters form part of the result key; cached results cannot bypass a clue.
        result_key = (query.description, query.language, query.starting_letter,
                      query.approximate_length, query.part_of_speech, query.limit)
        hit, cached = self.result_cache.get(result_key)
        if hit:
            self.last_translation, results = cached
            return [dict(result) for result in results]
        hit, cached = self.score_cache.get(query.description)
        if hit:
            self.last_translation, semantic, lexical, scores = cached
        else:
            self.last_translation = self.infer('translate', query.description) if re.search('[\u0900-\u097f]', query.description) else None
            text = self.last_translation or query.description
            vector = np.array(self.infer('encode', text), dtype=np.float32)
            semantic, lexical, scores = self.compute_scores(text, vector)
            self.score_cache.put(query.description, (self.last_translation, semantic, lexical, scores))
        results = self.rank(query, semantic, lexical, scores)
        self.result_cache.put(result_key, (self.last_translation, [dict(result) for result in results]))
        return results
