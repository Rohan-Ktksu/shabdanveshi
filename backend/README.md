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
.\.venv\Scripts\python.exe -m unittest backend.test_api backend.test_retrieval -v
.\.venv\Scripts\python.exe -m backend.evaluate --output backend/evaluation.json
```

Contract tests use an explicit test fixture; they validate request/response handling, not model quality. Real retrieval evaluation is separate. See `ATTRIBUTION.md` before redistributing data.

## Improved Hindi retrieval and compact runtime

Hindi-script descriptions are translated locally with OPUS-MT before retrieval. The API returns `translated_query`; the frontend displays it because translation can lose meaning. Hindi glosses matching an English WordNet lemma of the same part of speech can inherit that sense's retrieval score. Displayed definitions remain unchanged and attributed. Scores are still not calibrated probabilities.

Prepare the compact export with `python -m backend.build_compact`, then set `SHABD_ENGINE=compact` before starting Uvicorn. Compact mode uses SQLite, int8 vectors, precomputed TF-IDF postings and isolated inference processes. `python -m backend.evaluate --compact --output backend/evaluation-compact.json` evaluates it. It trades latency for lower memory; it does not prove compliance with a hosting memory limit. See `../DEPLOYMENT.md` for the required container gate and free-only configuration.
