"""Small, transparent retrieval smoke evaluation; not a general accuracy claim."""
import argparse
import json
import sys
import gzip
from pathlib import Path
from time import perf_counter
from .engine import Finder, normalize
from .schemas import PredictionRequest

# Written before inspecting the retrieval results. Multiple acceptable answers
# acknowledge synonyms; this small hand-authored set is not a held-out benchmark.
CASES = [
    ('en', 'someone who loves collecting books', ['bibliophile', 'booklover', 'book lover']),
    ('en', 'unable to sleep at night', ['insomnia', 'sleeplessness', 'insomniac']),
    ('en', 'fear of being in small enclosed spaces', ['claustrophobia']),
    ('en', 'a feeling of longing for the past', ['nostalgia']),
    ('en', 'understanding and sharing another person\'s feelings', ['empathy']),
    ('en', 'an instrument for measuring temperature', ['thermometer']),
    ('en', 'a person who studies stars and planets', ['astronomer', 'uranologist', 'stargazer']),
    ('en', 'the smell of earth after rain', ['petrichor']),
    ('en', 'नींद न आने की समस्या', ['insomnia', 'sleeplessness']),
    ('en', 'किताबों से प्रेम करने वाला व्यक्ति', ['bibliophile', 'booklover', 'book lover']),
    ('en', 'समय को मापने वाला उपकरण', ['clock', 'timepiece', 'watch']),
    ('en', 'दूसरों की भावनाओं को समझने की क्षमता', ['empathy']),
    ('hi', 'नींद न आने की समस्या', ['अनिद्रा']),
    ('hi', 'दूसरों की मदद करने वाला व्यक्ति', ['परोपकारी', 'मददगार']),
    ('hi', 'जिसे कभी मृत्यु न आए', ['अमर']),
    ('hi', 'पानी में रहने वाली मछली', ['मछली', 'मत्स्य']),
    ('hi', 'inability to fall asleep', ['अनिद्रा']),
    ('hi', 'a device used to tell the time', ['घड़ी']),
    ('hi', 'a place where books are kept for people to read', ['पुस्तकालय', 'ग्रंथालय', 'वाचनालय']),
    ('hi', 'a person who writes poems', ['कवि', 'शायर']),
]


def main():
    # Windows redirected consoles may default to cp1252, which cannot print Hindi.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    parser.add_argument('--compact', action='store_true')
    args = parser.parse_args()
    if args.compact:
        from .compact import CompactFinder
        from .config import DATA
        engine = CompactFinder()
        with gzip.open(DATA / 'entries.json.gz', 'rt', encoding='utf-8') as stream:
            entries = json.load(stream)
    else:
        engine = Finder()
        entries = engine.entries
    vocabulary = {(e['language'], normalize(word)) for e in entries for word in [e['word'], *e['aliases']]}
    rows = []
    for language, description, expected in CASES:
        start = perf_counter()
        suggestions = engine.search(PredictionRequest(description=description, language=language))
        words = [s['word'] for s in suggestions]
        acceptable = {normalize(w) for w in expected}
        rank = next((i + 1 for i, word in enumerate(words) if normalize(word) in acceptable), None)
        row = dict(language=language, description=description, expected=expected, returned=words,
                   translated_query=engine.last_translation,
                   expected_in_corpus=any((language, w) in vocabulary for w in acceptable),
                   rank=rank, elapsed_ms=round((perf_counter() - start) * 1000, 1))
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    summary = dict(cases=len(rows), top1=sum(r['rank'] == 1 for r in rows),
                   top5=sum(r['rank'] is not None for r in rows),
                   covered=sum(r['expected_in_corpus'] for r in rows))
    report = dict(note='Hand-authored smoke set, not a representative accuracy benchmark.',
                  summary=summary, corpus=engine.metadata, cases=rows)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
