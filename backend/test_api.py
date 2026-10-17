import unittest
from fastapi.testclient import TestClient
from .main import create_app
from .schemas import PredictionRequest
from .engine import letter_count


class RecordingFinder:
    metadata = {'languages': {'en': 1, 'hi': 1}}

    def search(self, query):
        self.query = query
        return [{'word': 'किताब', 'definition': 'book', 'definition_language': 'en', 'language': 'hi',
                 'part_of_speech': 'noun', 'score': .8, 'semantic_score': .8, 'tfidf_score': 0.,
                 'source': 'test fixture', 'source_url': 'https://en.wiktionary.org/wiki/किताब#Hindi'}]


class APIContractTests(unittest.TestCase):
    def setUp(self):
        self.finder = RecordingFinder()
        self.app = create_app(self.finder)
        self.client = TestClient(self.app)

    def test_prediction_preserves_hindi_and_filters(self):
        response = self.client.post('/api/predict', json={'description': 'पढ़ने वाली चीज', 'language': 'hi',
                                    'starting_letter': 'कि', 'approximate_length': 3, 'part_of_speech': 'noun'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.finder.query.starting_letter, 'कि')
        self.assertEqual(response.json()['suggestions'][0]['definition_language'], 'en')
        self.assertTrue(response.json()['warnings'])

    def test_rejects_invalid_requests(self):
        for payload in [{'description': '  '}, {'description': 'x' * 1001},
                        {'description': 'book lover', 'limit': True},
                        {'description': 'book lover', 'language': 'fr'},
                        {'description': 'book lover', 'approximate_length': 0},
                        {'description': 'book lover', 'starting_letter': '<script>'},
                        {'description': 'book lover', 'unexpected': 'value'}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post('/api/predict', json=payload).status_code, 422)

    def test_busy_service_reports_retry(self):
        self.app.state.busy.acquire()
        try:
            self.assertEqual(self.client.post('/api/predict', json={'description': 'book lover'}).status_code, 429)
        finally:
            self.app.state.busy.release()

    def test_unavailable_service_is_not_fake_success(self):
        self.app.state.finder = None
        self.assertEqual(self.client.get('/api/health').status_code, 503)
        self.assertEqual(self.client.get('/api/health').json()['status'], 'unavailable')
        self.assertEqual(self.client.post('/api/predict', json={'description': 'book lover'}).status_code, 503)

    def test_cors_only_allows_configured_origin(self):
        headers = {'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST'}
        self.assertEqual(self.client.options('/api/predict', headers=headers).headers.get('access-control-allow-origin'), headers['Origin'])
        headers['Origin'] = 'https://unconfigured.example'
        self.assertNotIn('access-control-allow-origin', self.client.options('/api/predict', headers=headers).headers)

    def test_visible_character_count(self):
        self.assertEqual(letter_count('किताब'), 3)
        self.assertEqual(letter_count('book lover'), 9)
        self.assertEqual(PredictionRequest(description=' a book ').description, 'a book')


if __name__ == '__main__':
    unittest.main()
