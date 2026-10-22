"""Reuse one encoder worker when memory permits; never overlap two models."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from .config import ROOT


def can_keep_encoder():
    """Reserve 96 MiB for ranking and cache overhead inside a Linux cgroup."""
    if os.environ.get('SHABD_WARM_ENCODER', 'auto') == '0':
        return False
    for limit_path, current_path, stat_path, cache_key in [
        ('/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory.current', '/sys/fs/cgroup/memory.stat', 'inactive_file'),
        ('/sys/fs/cgroup/memory/memory.limit_in_bytes', '/sys/fs/cgroup/memory/memory.usage_in_bytes', '/sys/fs/cgroup/memory/memory.stat', 'total_inactive_file'),
    ]:
        if Path(limit_path).exists():
            try:
                raw = Path(limit_path).read_text().strip()
                if raw == 'max':
                    return True
                current = int(Path(current_path).read_text())
                try:
                    stats = dict(line.split() for line in Path(stat_path).read_text().splitlines())
                    # Follow Docker's memory-accounting convention: inactive file
                    # pages are reclaimable, unlike the live model's allocations.
                    current -= max(0, min(current, int(stats.get(cache_key, 0))))
                except (OSError, ValueError):
                    pass
                retain = current + 96 * 1024**2 < int(raw)
                if os.environ.get('SHABD_MEMORY_DIAGNOSTICS') == '1':
                    print(json.dumps({'encoder_working_bytes': current, 'limit_bytes': int(raw),
                                      'reserve_bytes': 96 * 1024**2, 'retain_encoder': retain}), file=sys.stderr, flush=True)
                return retain
            except (OSError, ValueError):
                return False  # A detected but unreadable limit must not be guessed.
    return True  # Local development without a container memory limit.


class InferenceWorker:
    def __init__(self, timeout=90):
        self.process = None
        self.mode = None
        self.responses = None
        self.timeout = timeout

    def close(self):
        process, self.process = self.process, None
        self.mode = None
        if process is not None:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            for stream in (process.stdin, process.stdout):
                if stream:
                    stream.close()

    def start(self, mode):
        self.close()
        process = subprocess.Popen([sys.executable, '-m', 'backend.inference_worker', '--serve'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding='utf-8', bufsize=1, cwd=ROOT.parent,
            env={**os.environ, 'PYTHONPATH': os.pathsep.join(sys.path)},
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        responses = queue.Queue()
        self.process, self.mode, self.responses = process, mode, responses

        def read():
            try:
                for line in process.stdout:
                    responses.put(json.loads(line))
            except (ValueError, OSError):
                pass
            finally:
                responses.put({'error': 'worker_stopped'})
        threading.Thread(target=read, daemon=True).start()

    def request(self, mode, text):
        if mode == 'translate':
            # Translation cannot coexist with the warm encoder on a small host.
            # Its original one-shot path avoids a reader thread/process teardown.
            self.close()
            result = subprocess.run([sys.executable, '-m', 'backend.inference_worker'],
                input=json.dumps({'mode': mode, 'text': text}), text=True, encoding='utf-8',
                capture_output=True, timeout=self.timeout, check=True, cwd=ROOT.parent,
                env={**os.environ, 'PYTHONPATH': os.pathsep.join(sys.path)},
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            return json.loads(result.stdout)
        if self.process is None or self.process.poll() is not None or self.mode != mode:
            self.start(mode)
        try:
            self.process.stdin.write(json.dumps({'mode': mode, 'text': text}) + '\n')
            self.process.stdin.flush()
            response = self.responses.get(timeout=self.timeout)
            if not isinstance(response, dict) or 'result' not in response:
                failure = subprocess.CalledProcessError(self.process.poll() or 1, 'inference worker')
                failure.worker_error_type = response.get('error_type', 'worker_stopped') if isinstance(response, dict) else 'invalid_response'
                raise failure
            result = response['result']
        except queue.Empty as exc:
            self.close()
            raise subprocess.TimeoutExpired('inference worker', self.timeout) from exc
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            self.close()
            if isinstance(exc, subprocess.CalledProcessError):
                raise
            raise subprocess.CalledProcessError(1, 'inference worker') from exc
        if mode != 'encode' or not can_keep_encoder():
            self.close()
        return result
