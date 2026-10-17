"""Filter/ranking regression checks using an explicitly tiny synthetic index."""
import unittest
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from .engine import Finder
from .schemas import PredictionRequest


class FixtureEncoder:
    def encode(self, texts):
        return np.array([[1., 0.]], dtype=np.float32)


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.finder = Finder.__new__(Finder)
        self.finder.encoder = FixtureEncoder()
        self.finder.entries = [
            self.entry('book lover', 'en', ['bibliophile'], 'noun'),
            self.entry('किताब', 'hi', [], 'noun'),
            self.entry('read', 'en', [], 'verb'),
            self.entry('book lover', 'en', [], 'noun'),
        ]
        self.finder.embeddings = np.array([[.9, 0], [.8, 0], [.7, 0], [.6, 0]], dtype=np.float32)
        self.finder.vectorizer = TfidfVectorizer()
        self.finder.lexical = self.finder.vectorizer.fit_transform(['books', 'book', 'reading', 'collector'])

    def entry(self, word, language, aliases, pos):
        return dict(id=word, word=word, aliases=aliases, language=language,
                    definition='fixture', definition_language='en', part_of_speech=pos,
                    source='fixture', source_url='https://example.com')

    def test_prefix_can_select_synonym_and_is_case_insensitive(self):
        results = self.finder.search(PredictionRequest(description='books', starting_letter='BIB'))
        self.assertEqual([r['word'] for r in results], ['bibliophile'])

    def test_language_length_and_part_of_speech_combine(self):
        query = PredictionRequest(description='books', language='hi', starting_letter='कि',
                                  approximate_length=3, part_of_speech='noun')
        self.assertEqual([r['word'] for r in self.finder.search(query)], ['किताब'])
        self.assertEqual(self.finder.search(query.model_copy(update={'part_of_speech': 'verb'})), [])

    def test_distinct_words_and_result_limit(self):
        results = self.finder.search(PredictionRequest(description='books', language='both', limit=10))
        self.assertEqual([r['word'] for r in results], ['book lover', 'किताब', 'read'])
        self.assertEqual(len(self.finder.search(PredictionRequest(description='books', limit=1))), 1)

    def test_unmatched_prefix_returns_empty(self):
        self.assertEqual(self.finder.search(PredictionRequest(description='books', starting_letter='zzz')), [])


if __name__ == '__main__':
    unittest.main()
