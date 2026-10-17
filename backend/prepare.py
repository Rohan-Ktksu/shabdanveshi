"""Download attributed resources, normalize dictionaries and build a resumable index.

Run from the repository root: python -m backend.prepare
Generated artifacts stay outside Git; their source URLs and hashes are recorded.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
import re
import shutil
import urllib.request
from urllib.parse import quote
import zipfile
import numpy as np
from .config import DATA, MODEL, MODEL_REVISION, MAX_TOKENS

SOURCES = {
    'wordnet.zip': 'https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/wordnet.zip',
    'hindi.jsonl': 'https://kaikki.org/dictionary/Hindi/kaikki.org-dictionary-Hindi.jsonl',
}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(part)
    return digest.hexdigest()


def download(url, path):
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.part')
    print(f'Downloading {path.name}', flush=True)
    request = urllib.request.Request(url, headers={'User-Agent': 'ShabdAnveshi/0.2 academic word retrieval'})
    with urllib.request.urlopen(request, timeout=180) as response, open(temp, 'wb') as target:
        shutil.copyfileobj(response, target)
    temp.replace(path)
    print(f'Downloaded {path.name}: {path.stat().st_size:,} bytes', flush=True)


def normalize():
    entries = []
    with zipfile.ZipFile(DATA / 'wordnet.zip') as source:
        for pos in ('noun', 'verb', 'adj', 'adv'):
            for line in source.read(f'wordnet/data.{pos}').decode().splitlines():
                if not line or not line[0].isdigit():
                    continue
                fields, gloss = line.split('|', 1)
                fields = fields.split()
                names = [re.sub(r'\((?:a|p|ip)\)$', '', fields[4 + 2*i]).replace('_', ' ')
                         for i in range(int(fields[3], 16))]
                definition = re.sub(r'"[^"]*"', '', gloss).strip(' ;')
                entries.append(dict(id='wn-' + fields[0] + fields[2], word=names[0], aliases=names[1:],
                                    definition=definition, definition_language='en', language='en',
                                    part_of_speech={'adj': 'adjective', 'adv': 'adverb'}.get(pos, pos),
                                    source='WordNet 3.0', source_url='https://wordnet.princeton.edu/'))
        (DATA / 'WORDNET-LICENSE.txt').write_bytes(source.read('wordnet/LICENSE'))
    allowed = {'noun': 'noun', 'verb': 'verb', 'adj': 'adjective', 'adv': 'adverb'}
    seen = set()
    with open(DATA / 'hindi.jsonl', encoding='utf-8') as stream:
        for line in stream:
            item = json.loads(line)
            word, pos = item.get('word', ''), item.get('pos', '')
            if pos not in allowed or item.get('lang_code') != 'hi' or not re.search('[\u0900-\u097f]', word):
                continue
            for sense in item.get('senses', []):
                if sense.get('form_of') or 'form-of' in sense.get('tags', []):
                    continue
                glosses = sense.get('glosses', [])
                if not glosses:
                    continue
                definition = '; '.join(glosses)
                identity = (word, pos, definition)
                if identity in seen:
                    continue
                seen.add(identity)
                entries.append(dict(id=f'hi-{len(seen)}', word=word, aliases=[], language='hi',
                                    definition=definition, definition_language='en', part_of_speech=allowed[pos],
                                    source='Wiktionary via Kaikki',
                                    source_url=f'https://en.wiktionary.org/wiki/{quote(word)}#Hindi'))
    with gzip.open(DATA / 'entries.json.gz', 'wt', encoding='utf-8') as target:
        json.dump(entries, target, ensure_ascii=False, separators=(',', ':'))
    print(f'Normalized {len(entries):,} word senses ({len(seen):,} Hindi)', flush=True)
    return entries


def passage(entry):
    return f"{entry['word']}. {', '.join(entry['aliases'])}. {entry['definition']}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--download-only', action='store_true')
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 256:
        parser.error('batch-size must be between 1 and 256')
    if not 1 <= args.threads <= 32:
        parser.error('threads must be between 1 and 32')
    DATA.mkdir(parents=True, exist_ok=True)
    tasks = [(url, DATA / name) for name, url in SOURCES.items()]
    for name, upstream in [('tokenizer.json', 'tokenizer.json'), ('model_quantized.onnx', 'onnx/model_quantized.onnx'), ('model-card.md', 'README.md')]:
        tasks.append((f'https://huggingface.co/Xenova/multilingual-e5-small/resolve/{MODEL_REVISION}/{upstream}', MODEL / name))
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda task: download(*task), tasks))
    if args.download_only:
        return
    if (DATA / 'entries.json.gz').exists():
        with gzip.open(DATA / 'entries.json.gz', 'rt', encoding='utf-8') as source:
            entries = json.load(source)
    else:
        entries = normalize()
    signature = {'corpus_sha256': sha256(DATA / 'entries.json.gz'), 'model_sha256': sha256(MODEL / 'model_quantized.onnx'),
                 'tokenizer_sha256': sha256(MODEL / 'tokenizer.json'), 'max_tokens': MAX_TOKENS, 'model_revision': MODEL_REVISION}
    checkpoint = DATA / 'checkpoint.json'
    existing = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
    index_path = DATA / 'embeddings.npy'
    start = existing.get('completed', 0) if existing.get('signature') == signature and index_path.exists() else 0
    matrix = np.lib.format.open_memmap(index_path, mode='r+' if start else 'w+', dtype=np.float32, shape=(len(entries), 384))
    from .encoder import Encoder
    encoder = Encoder(threads=args.threads)
    # Group similar-length texts inside each checkpoint block to reduce padding.
    # Write vectors back to their original rows, preserving dictionary alignment.
    block_size = args.batch_size * 20
    for offset in range(start, len(entries), block_size):
        completed = min(offset + block_size, len(entries))
        ordered = sorted(range(offset, completed), key=lambda i: len(passage(entries[i])))
        for batch_start in range(0, len(ordered), args.batch_size):
            indices = ordered[batch_start:batch_start + args.batch_size]
            matrix[indices] = encoder.encode([passage(entries[i]) for i in indices], 'passage')
        matrix.flush()
        temp = checkpoint.with_suffix('.tmp')
        temp.write_text(json.dumps({'completed': completed, 'signature': signature}))
        temp.replace(checkpoint)
        print(f'Indexed {completed:,}/{len(entries):,}', flush=True)
    metadata = {**signature, 'entries': len(entries), 'languages': {lang: sum(e['language'] == lang for e in entries) for lang in ('en', 'hi')},
                'sources': {name: {'url': url, 'sha256': sha256(DATA / name)} for name, url in SOURCES.items()},
                'created_at': datetime.now(timezone.utc).isoformat()}
    (DATA / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print('Index ready.', flush=True)


if __name__ == '__main__':
    main()
