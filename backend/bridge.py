"""Link exact English translation glosses to WordNet senses of the same POS."""
from collections import defaultdict
import re
import unicodedata
import numpy as np


def key(text):
    return unicodedata.normalize('NFC', text).strip().casefold()


class GlossBridge:
    def __init__(self, entries):
        english = defaultdict(list)
        for index, entry in enumerate(entries):
            if entry['language'] == 'en':
                for word in [entry['word'], *entry['aliases']]:
                    english[(key(word), entry['part_of_speech'])].append(index)
        pairs = set()
        for index, entry in enumerate(entries):
            if entry['language'] != 'hi':
                continue
            for gloss in re.split('[,;]', entry['definition']):
                gloss = re.sub(r'\([^)]*\)', '', gloss).strip()
                gloss = re.sub(r'^(?:an? |the |to )', '', gloss, flags=re.I).strip()
                for source in english.get((key(gloss), entry['part_of_speech']), []):
                    pairs.add((index, source))
        self.target = np.array([p[0] for p in sorted(pairs)], dtype=np.int64)
        self.source = np.array([p[1] for p in sorted(pairs)], dtype=np.int64)

    def apply(self, scores):
        result = scores.copy()
        # The linked WordNet sense contributes its context; no new definitions
        # or hand-written query/answer pairs are introduced.
        np.maximum.at(result, self.target, scores[self.source])
        return result
