"""Low-memory retrieval: SQLite, mapped postings, and isolated inference workers."""
from collections import Counter
from contextlib import closing
import json
import os
import re
import sqlite3
import subprocess
import sys
import unicodedata
import numpy as np
import regex
from .config import DATA, ROOT


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

    def infer(self, mode, text):
        result = subprocess.run([sys.executable, '-m', 'backend.inference_worker'],
            input=json.dumps({'mode':mode,'text':text}), text=True, encoding='utf-8',
            capture_output=True, timeout=90, check=True, cwd=ROOT.parent,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        return json.loads(result.stdout)

    def search(self, query):
        self.last_translation = self.infer('translate', query.description) if re.search('[\u0900-\u097f]',query.description) else None
        text = self.last_translation or query.description
        vector = np.array(self.infer('encode', text), dtype=np.float32)
        mapped = []
        def load(name):
            value = np.load(self.folder / name, mmap_mode='r')
            mapped.append(value)
            return value
        try:
            matrix, norms = load('vectors.npy'), load('norms.npy')
            semantic = np.empty(len(matrix), dtype=np.float32)
            for start in range(0,len(matrix),4096):
                semantic[start:start+4096] = matrix[start:start+4096].astype(np.float32) @ vector / norms[start:start+4096]
            lexical = np.zeros(len(matrix),dtype=np.float32)
            tokens = [t for t in re.findall(r'(?u)\b\w\w+\b',text.lower()) if t not in self.stop_words]
            counts = Counter(tokens + [' '.join(tokens[i:i+2]) for i in range(len(tokens)-1)])
            # Read-only connection prevents concurrent web requests mutating data.
            uri = (self.folder / 'dictionary.sqlite').as_uri() + '?mode=ro'
            with closing(sqlite3.connect(uri,uri=True)) as db:
                terms=[]
                for term,count in counts.items():
                    row=db.execute('SELECT idf,start,stop FROM terms WHERE term=?',(term,)).fetchone()
                    if row: terms.append((count*row[0],row[1],row[2]))
                denominator=np.sqrt(sum(t[0]**2 for t in terms)) or 1.
                posting_rows,posting_values=load('posting_rows.npy'),load('posting_values.npy')
                for weight,start,stop in terms:
                    np.add.at(lexical,posting_rows[start:stop],posting_values[start:stop]*(weight/denominator))
                scores=semantic+0.05*lexical
                target,source=load('bridge_target.npy'),load('bridge_source.npy')
                original=scores.copy()
                np.maximum.at(scores,target,original[source])
                results=[];seen=set()
                for index in np.argsort(-scores,kind='stable'):
                    entry=json.loads(db.execute('SELECT payload FROM entries WHERE id=?',(int(index),)).fetchone()[0])
                    if query.language!='both' and entry['language']!=query.language: continue
                    if query.part_of_speech and entry['part_of_speech']!=query.part_of_speech: continue
                    word=next((w for w in [entry['word'],*entry['aliases']]
                               if (not query.starting_letter or normalize(w).startswith(query.starting_letter))
                               and (query.approximate_length is None or abs(letter_count(w)-query.approximate_length)<=1)
                               and (entry['language'],normalize(w)) not in seen),None)
                    if word is None: continue
                    seen.add((entry['language'],normalize(word)))
                    results.append({k:v for k,v in {**entry,'word':word,'score':round(float(semantic[index]),4),
                        'semantic_score':round(float(semantic[index]),4),'tfidf_score':round(float(lexical[index]),4)}.items() if k not in ('id','aliases')})
                    if len(results)==query.limit: break
                return results
        finally:
            for array in mapped:
                array._mmap.close()
