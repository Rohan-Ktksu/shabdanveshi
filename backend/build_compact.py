"""Export disk-backed retrieval resources from a prepared full index."""
import json
import sqlite3
import numpy as np
from .config import DATA
from .engine import Finder


def main():
    finder = Finder()
    folder = DATA / 'compact'
    folder.mkdir(exist_ok=True)
    matrix = np.lib.format.open_memmap(folder / 'vectors.npy', mode='w+', dtype=np.int8, shape=finder.embeddings.shape)
    norms = np.zeros(len(finder.entries), dtype=np.float32)
    for start in range(0, len(matrix), 4096):
        quantized = np.rint(finder.embeddings[start:start+4096] * 127).clip(-127,127).astype(np.int8)
        matrix[start:start+len(quantized)] = quantized
        norms[start:start+len(quantized)] = np.linalg.norm(quantized.astype(np.float32), axis=1)
    matrix.flush()
    np.save(folder / 'norms.npy', norms)
    np.save(folder / 'bridge_target.npy', finder.bridge.target)
    np.save(folder / 'bridge_source.npy', finder.bridge.source)
    postings = finder.lexical.tocsc()
    np.save(folder / 'posting_rows.npy', postings.indices)
    np.save(folder / 'posting_values.npy', postings.data)
    temp = folder / 'dictionary.build.sqlite'
    with sqlite3.connect(temp) as db:
        db.executescript('DROP TABLE IF EXISTS entries; DROP TABLE IF EXISTS terms; CREATE TABLE entries (id INTEGER PRIMARY KEY, payload TEXT NOT NULL); CREATE TABLE terms (term TEXT PRIMARY KEY, idf REAL, start INTEGER, stop INTEGER);')
        db.executemany('INSERT INTO entries VALUES (?,?)', ((i,json.dumps(e,ensure_ascii=False)) for i,e in enumerate(finder.entries)))
        db.executemany('INSERT INTO terms VALUES (?,?,?,?)', ((word,float(finder.vectorizer.idf_[i]),int(postings.indptr[i]),int(postings.indptr[i+1])) for word,i in finder.vectorizer.vocabulary_.items()))
    db.close()
    temp.replace(folder / 'dictionary.sqlite')
    (folder / 'metadata.json').write_text(json.dumps({**finder.metadata, 'compact_version': 1, 'stop_words': sorted(finder.vectorizer.get_stop_words()), 'vector_format': 'int8 with per-row norm'}),encoding='utf-8')
    print('Compact index exported.', flush=True)


if __name__ == '__main__':
    main()
