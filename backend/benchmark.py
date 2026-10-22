"""Reproducible local latency checks; public examples, not a hosting guarantee."""
import argparse
import json
import sys
from pathlib import Path
from time import perf_counter
from .compact import CompactFinder
from .schemas import PredictionRequest


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    examples = [
        ('First English search', dict(description='someone who loves books', language='en')),
        ('Different English search, warm encoder', dict(description='a feeling of longing for the past', language='en')),
        ('Repeated English search', dict(description='someone who loves books', language='en')),
        ('Same description, prefix clue', dict(description='someone who loves books', language='en', starting_letter='bib')),
        ('First Hindi search', dict(description='किताबों से प्रेम करने वाला व्यक्ति', language='en')),
        ('Repeated Hindi search', dict(description='किताबों से प्रेम करने वाला व्यक्ति', language='en')),
        ('Same Hindi description, different result language', dict(description='किताबों से प्रेम करने वाला व्यक्ति', language='hi')),
    ]
    finder = CompactFinder()
    rows = []
    try:
        for label, payload in examples:
            start = perf_counter()
            results = finder.search(PredictionRequest(**payload))
            row = dict(case=label, elapsed_ms=round((perf_counter() - start) * 1000, 3),
                       top_word=results[0]['word'] if results else None,
                       encoder_retained=finder.worker.process is not None)
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    finally:
        finder.close()
    if args.output:
        args.output.write_text(json.dumps(dict(
            note='Sequential local Windows measurements with OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1. '
                 'Not HTTP timings, not production latency. Hindi result quality remains experimental.',
            cases=rows), ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
