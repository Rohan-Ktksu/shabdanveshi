"""Dictionary retrieval with real multilingual embeddings and TF-IDF comparison."""
import gzip
import json
import unicodedata
import numpy as np
import regex
from sklearn.feature_extraction.text import TfidfVectorizer
from .config import DATA, MODEL, MAX_TOKENS, MODEL_REVISION
from .encoder import Encoder
from .prepare import sha256, passage
from .schemas import PredictionRequest
from .bridge import GlossBridge
from .translation import Translator


def normalize(text):
    return unicodedata.normalize('NFC', text).casefold().strip()


def letter_count(text):
    return sum(bool(regex.search(r'\p{L}', cluster)) for cluster in regex.findall(r'\X', text))


class Finder:
    def __init__(self):
        metadata = json.loads((DATA / 'metadata.json').read_text(encoding='utf-8'))
        if metadata['corpus_sha256'] != sha256(DATA / 'entries.json.gz') or metadata['max_tokens'] != MAX_TOKENS or metadata['model_revision'] != MODEL_REVISION:
            raise ValueError('Corpus or model configuration changed; rebuild with python -m backend.prepare')
        if metadata['model_sha256'] != sha256(MODEL / 'model_quantized.onnx') or metadata['tokenizer_sha256'] != sha256(MODEL / 'tokenizer.json'):
            raise ValueError('Model assets changed; rebuild the index')
        with gzip.open(DATA / 'entries.json.gz', 'rt', encoding='utf-8') as stream:
            self.entries = json.load(stream)
        checkpoint = json.loads((DATA / 'checkpoint.json').read_text())
        if checkpoint.get('completed') != len(self.entries) or any(
            checkpoint.get('signature', {}).get(key) != metadata[key]
            for key in ('corpus_sha256', 'model_sha256', 'tokenizer_sha256', 'max_tokens', 'model_revision')
        ):
            raise ValueError('Index build is incomplete; resume python -m backend.prepare')
        self.embeddings = np.load(DATA / 'embeddings.npy', mmap_mode='r')
        if self.embeddings.shape != (len(self.entries), 384):
            raise ValueError('Incomplete embedding index')
        self.encoder = Encoder()
        self.vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=120000, dtype=np.float32)
        self.lexical = self.vectorizer.fit_transform([passage(entry) for entry in self.entries])
        self.metadata = metadata
        self.bridge = GlossBridge(self.entries)
        self.translator = Translator()
        self.last_translation = None

    def search(self, query: PredictionRequest):
        self.last_translation = None
        if regex.search(r'[\u0900-\u097f]', query.description) and getattr(self, 'translator', None):
            self.last_translation = self.translator.translate(query.description)
        search_text = self.last_translation or query.description
        vector = self.encoder.encode([search_text])[0]
        semantic = np.asarray(self.embeddings @ vector)
        lexical = (self.lexical @ self.vectorizer.transform([search_text]).T).toarray().ravel()
        # Semantic-first ranking. TF-IDF is an explicitly uncalibrated tie-break aid.
        scores = semantic + 0.05 * lexical
        if getattr(self, 'bridge', None):
            scores = self.bridge.apply(scores)
        order = np.argsort(-scores, kind='stable')
        results, seen = [], set()
        for number in order:
            entry = self.entries[int(number)]
            if query.language != 'both' and entry['language'] != query.language:
                continue
            if query.part_of_speech and entry['part_of_speech'] != query.part_of_speech:
                continue
            choices = [entry['word'], *entry['aliases']]
            word = next((word for word in choices
                         if (not query.starting_letter or normalize(word).startswith(query.starting_letter))
                         and (query.approximate_length is None or abs(letter_count(word) - query.approximate_length) <= 1)
                         and (entry['language'], normalize(word)) not in seen), None)
            if word is None:
                continue
            seen.add((entry['language'], normalize(word)))
            results.append({key: value for key, value in {
                **entry, 'word': word, 'score': round(float(semantic[number]), 4),
                'semantic_score': round(float(semantic[number]), 4), 'tfidf_score': round(float(lexical[number]), 4),
            }.items() if key not in ('aliases', 'id')})
            if len(results) == query.limit:
                break
        return results
