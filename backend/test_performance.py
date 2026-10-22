"""Regression checks for cached retrieval and memory-aware worker reuse."""
from contextlib import closing
import json
import queue
import sqlite3
import tempfile
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from .cache import ExpiringCache
from .compact import CompactFinder
from .inference import InferenceWorker, can_keep_encoder
from .schemas import PredictionRequest


class CacheTests(unittest.TestCase):
    def test_expiration_and_none_values(self):
        clock = [0]
        cache = ExpiringCache(2, ttl=10, clock=lambda: clock[0])
        cache.put('translation', None)
        self.assertEqual(cache.get('translation'), (True, None))
        clock[0] = 10
        self.assertEqual(cache.get('translation'), (False, None))

    def test_lru_capacity(self):
        cache = ExpiringCache(2)
        cache.put('a', 1); cache.put('b', 2)
        cache.get('a'); cache.put('c', 3)
        self.assertEqual(cache.get('b'), (False, None))
        self.assertEqual(cache.get('a'), (True, 1))
        self.assertEqual(len(cache.items), 2)


class WorkerTests(unittest.TestCase):
    @patch.dict('os.environ', {'SHABD_WARM_ENCODER': '0'})
    def test_explicit_disable(self):
        self.assertFalse(can_keep_encoder())

    @patch.dict('os.environ', {'SHABD_WARM_ENCODER': 'auto'})
    @patch('backend.inference.Path')
    def test_tight_cgroup_does_not_retain_model(self, path):
        path.return_value.exists.return_value = True
        path.return_value.read_text.side_effect = ['536870912', '400000000', 'inactive_file 0']
        self.assertFalse(can_keep_encoder())

    @patch.dict('os.environ', {'SHABD_WARM_ENCODER': 'auto'})
    @patch('backend.inference.Path')
    def test_cgroup_headroom_allows_reuse(self, path):
        path.return_value.exists.return_value = True
        path.return_value.read_text.side_effect = ['536870912', '200000000', 'inactive_file 0']
        self.assertTrue(can_keep_encoder())

    @patch.dict('os.environ', {'SHABD_WARM_ENCODER': 'auto'})
    @patch('backend.inference.Path')
    def test_inactive_file_cache_is_reclaimable(self, path):
        path.return_value.exists.return_value = True
        path.return_value.read_text.side_effect = ['536870912', '500000000', 'inactive_file 300000000']
        self.assertTrue(can_keep_encoder())

    @patch('backend.inference.can_keep_encoder', return_value=True)
    def test_warm_encoder_reuses_process(self, _):
        worker = InferenceWorker()
        worker.process = MagicMock()
        worker.process.poll.return_value = None
        worker.mode = 'encode'
        worker.responses = queue.Queue()
        worker.responses.put({'result': [1, 0]})
        with patch.object(worker, 'start') as start:
            self.assertEqual(worker.request('encode', 'books'), [1, 0])
            start.assert_not_called()
        worker.close()

    @patch('backend.inference.can_keep_encoder', return_value=False)
    def test_worker_released_before_ranking_when_budget_tight(self, _):
        worker = InferenceWorker()
        worker.process = MagicMock(); worker.process.poll.return_value = None
        worker.mode = 'encode'; worker.responses = queue.Queue()
        worker.responses.put({'result': [1, 0]})
        with patch.object(worker, 'close') as close:
            worker.request('encode', 'books')
            close.assert_called_once()

    def test_switching_model_stops_old_worker_first(self):
        worker = InferenceWorker()
        worker.process = MagicMock(); worker.process.poll.return_value = None
        worker.mode = 'encode'
        with patch.object(worker, 'close') as close, patch('backend.inference.subprocess.Popen') as popen, patch('backend.inference.threading.Thread'):
            worker.start('translate')
            close.assert_called_once()
            popen.assert_called_once()
            self.assertEqual(worker.mode, 'translate')

    def test_translation_releases_encoder_before_one_shot_worker(self):
        worker = InferenceWorker()
        with patch.object(worker, 'close') as close, patch('backend.inference.subprocess.run') as run:
            def translate(*args, **kwargs):
                close.assert_called_once()
                return MagicMock(stdout='"books"')
            run.side_effect = translate
            self.assertEqual(worker.request('translate', 'किताबें'), 'books')

    def test_worker_timeout_closes_process(self):
        worker = InferenceWorker(timeout=0)
        worker.process = MagicMock(); worker.process.poll.return_value = None
        worker.mode = 'encode'; worker.responses = queue.Queue()
        with patch.object(worker, 'close') as close:
            import subprocess
            with self.assertRaises(subprocess.TimeoutExpired):
                worker.request('encode', 'books')
            close.assert_called_once()


class CompactCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.finder = CompactFinder.__new__(CompactFinder)
        self.finder.folder = Path(self.temp.name)
        self.finder.last_translation = None
        self.finder.score_cache = ExpiringCache(4)
        self.finder.result_cache = ExpiringCache(64)
        self.finder.inference_cache = ExpiringCache(64)
        self.finder.worker = MagicMock()
        self.finder.worker.request.side_effect = lambda mode, text: 'books' if mode == 'translate' else [1., 0.]
        values = np.array([.9, .8, .7, .6], dtype=np.float32)
        self.finder.compute_scores = MagicMock(return_value=(values, np.zeros(4), values))
        entries = [self.entry('book lover', 'en', ['bibliophile']), self.entry('किताब', 'hi', []),
                   self.entry('book lover', 'en', []), self.entry('e\u0301lan', 'en', [])]
        with closing(sqlite3.connect(self.finder.folder / 'dictionary.sqlite')) as db:
            db.execute('CREATE TABLE entries(id INTEGER PRIMARY KEY,payload TEXT)')
            db.executemany('INSERT INTO entries VALUES (?,?)', [(i, json.dumps(entry)) for i, entry in enumerate(entries)])
            db.commit()

    def entry(self, word, language, aliases):
        return dict(word=word, aliases=aliases, language=language, definition='fixture', definition_language='en',
                    part_of_speech='noun', source='fixture', source_url='https://example.com')

    def test_repeat_search_avoids_inference_and_returns_independent_dicts(self):
        request = PredictionRequest(description='books')
        first = self.finder.search(request)
        first[0]['word'] = 'changed externally'
        second = self.finder.search(request)
        self.assertEqual(second[0]['word'], 'book lover')
        self.assertEqual(self.finder.worker.request.call_count, 1)
        self.assertEqual(self.finder.compute_scores.call_count, 1)

    def test_filter_changes_reuse_scores_but_honor_prefix_alias(self):
        self.finder.search(PredictionRequest(description='books'))
        filtered = self.finder.search(PredictionRequest(description='books', starting_letter='BIB'))
        self.assertEqual([r['word'] for r in filtered], ['bibliophile'])
        self.assertEqual(self.finder.worker.request.call_count, 1)

    def test_languages_and_no_match_prefix(self):
        results = self.finder.search(PredictionRequest(description='books', language='hi'))
        self.assertEqual([r['word'] for r in results], ['किताब'])
        self.assertEqual(self.finder.search(PredictionRequest(description='books', starting_letter='zzzz')), [])

    def test_unicode_prefix_and_length(self):
        results = self.finder.search(PredictionRequest(description='books', starting_letter='é', approximate_length=4))
        self.assertEqual([r['word'] for r in results], ['e\u0301lan'])

    def test_translation_retained_on_cache_hits(self):
        request = PredictionRequest(description='किताबें')
        self.finder.search(request)
        self.finder.last_translation = None
        self.finder.search(request)
        self.assertEqual(self.finder.last_translation, 'books')
        self.assertEqual(self.finder.worker.request.call_count, 2)

    def test_failed_inference_is_not_cached(self):
        self.finder.worker.request.side_effect = RuntimeError('fixture')
        for _ in range(2):
            with self.assertRaises(RuntimeError):
                self.finder.infer('encode', 'books')
        self.assertEqual(self.finder.worker.request.call_count, 2)
