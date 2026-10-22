# Python search service

Run commands from the repository root with Python 3.12 in a virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m backend.prepare
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Preparation downloads WordNet, Hindi Wiktionary data and a quantized multilingual E5 model. It then encodes the dictionary on CPU. This is a one-time, potentially lengthy preparation step. Progress is checkpointed every 20 batches; rerunning resumes from the last flushed checkpoint when source/model hashes match. All generated data and weights stay under `backend/` on the project's drive. For pip downloads, `--cache-dir .pip-cache` keeps the package cache on that drive too.

Endpoints: `GET /api/health`, `GET /api/examples`, `POST /api/predict`. Interactive schema: `/docs`. The frontend request format is documented in `frontend/README.md`.

## Retrieval

The full dictionary is searched by multilingual semantic similarity. An uncalibrated baseline ranks by `semantic cosine + 0.05 * TF-IDF cosine`. Returned `score` is semantic cosine, not a probability, and may not decrease strictly because the keyword term affects ordering. Both component scores are also returned. There is no claim that these weights are optimal.

Language and part-of-speech filters are exact. Prefixes are normalized to NFC and case-folded. Approximate length allows ±1 **letter-containing Unicode grapheme cluster**, excluding spaces and punctuation; this makes Hindi combining marks part of their visible character rather than separate code units. Distinct word/language pairs are deduplicated.

Cross-language queries use the same embedding space. Hindi suggestions currently carry English definitions and an explicit language/source notice. Coverage is limited to the dictionaries: uncommon words and missing concepts cannot be recovered reliably. The model can return weak matches for vague or unrelated queries; the frontend must not call scores accuracy/confidence.

## Configuration

- `CORS_ORIGINS`: comma-separated frontend origins; defaults only to localhost development origins. Set `https://rohan-ktksu.github.io` for GitHub Pages (origin only, no repository path).
- `SHABD_DATA_DIR` / `SHABD_MODEL_DIR`: optional paths for generated index and model assets.
- One inference request is admitted at a time; concurrent requests receive 429 and can be retried.
- Missing data returns 503 for search and `unavailable` health, not synthetic answers.

Use one Uvicorn worker initially: multiple workers duplicate model/dictionary memory. Measure memory before choosing a host; do not assume a small free instance can load the full corpus and model.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest backend.test_api backend.test_retrieval backend.test_bridge backend.test_performance -v
.\.venv\Scripts\python.exe -m backend.evaluate --output backend/evaluation.json
```

Contract tests use an explicit test fixture; they validate request/response handling, not model quality. Real retrieval evaluation is separate. See `ATTRIBUTION.md` before redistributing data.

## Improved Hindi retrieval and compact runtime

Hindi-script descriptions are translated locally with OPUS-MT before retrieval. The API returns `translated_query`; the frontend displays it because translation can lose meaning. Hindi glosses matching an English WordNet lemma of the same part of speech can inherit that sense's retrieval score. Displayed definitions remain unchanged and attributed. Scores are still not calibrated probabilities.

Prepare the compact export with `python -m backend.build_compact`, then set `SHABD_ENGINE=compact` before starting Uvicorn. Compact mode uses SQLite, int8 vectors, precomputed TF-IDF postings and isolated inference processes. `python -m backend.evaluate --compact --output backend/evaluation-compact.json` evaluates it. See `../DEPLOYMENT.md` for the required container gate and free-only configuration.

## Search latency

Compact mode retains one encoder worker if the container's current memory usage plus a 160 MiB ranking/cache reserve fits its limit. Reclaimable inactive file pages are excluded from that usage estimate. If the limit is unreadable or headroom is insufficient, the worker is released before ranking. Set `SHABD_WARM_ENCODER=0` to always release it. Translation closes any retained encoder first, runs separately, and exits before embedding. There is still only one admitted search at a time, and shutdown closes the worker.

Three bounded in-memory caches expire entries after ten minutes: 64 inference values, four score sets (about 7 MiB for this corpus), and 64 result sets. A final-result key includes every request field. Changing filters can reuse scoring without bypassing clues. Failed inference is not cached; shutdown/restart clears all caches. These caches do not persist queries to disk.

Candidate records are read in score-ordered batches. Common searches avoid a complete metadata scan; prefix searches use SQLite to check words and aliases before fetching ranked candidates. Ranking weights, stable ties, translations and Unicode clue rules remain unchanged.

With resources prepared, run `python -m backend.benchmark --output backend/performance-local.json` to compare a first description, a different warm description, repeats and filter changes. Use `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1` to match Docker. Timings vary by hardware; a fresh Hindi translation and a sleeping Render instance remain slow paths. The GitHub runtime check tests the new worker lifecycle under a hard 512 MB limit before deployment.
