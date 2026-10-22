# Backend validation

Checked 18 October 2026 on the local Windows development computer.

- Full index: 150,041 senses (117,659 English; 32,382 Hindi).
- All stored vectors are finite and unit-normalized. Five sampled rows spanning both languages and the resumed index were re-encoded; cosine agreement exceeded 0.99. Quantized batched inference can differ slightly from single-item inference.
- Ten API and retrieval-filter unit tests pass. These use synthetic fixtures and do not measure semantic quality.
- Real HTTP health, English/Hindi/both result languages, prefix filtering, source URLs and development CORS passed against the running service.
- The five live requests took approximately 38–78 ms for server-side retrieval after loading. This is a local observation, not a hosting latency guarantee.

## Retrieval smoke evaluation

The 20 hand-authored cases were written before checking model results. Expected-answer lists were kept unchanged after evaluation. Full results and resource hashes are in `evaluation.json`.

| Measure | Result |
| --- | --- |
| Expected answer exists in corpus | 19 / 20 |
| Expected answer ranked first | 8 / 20 |
| Expected answer in first five | 13 / 20 |

This is a small diagnostic set, not a representative accuracy benchmark. English examples such as bibliophile, insomnia, nostalgia, empathy and thermometer ranked first. Hindi descriptions involving negation performed poorly; one insomnia query returned unrelated sleep concepts. Some relevant synonyms can also be counted as misses by the fixed expected lists. Petrichor was absent from this corpus.

Hindi retrieval is experimental and needs improvement before a reliable public release. The interface discloses this limitation. Do not interpret successful HTTP responses or the multilingual model name as proof of language quality.

## Compact runtime update

Local OPUS-MT translation and an exact-gloss bridge now connect Hindi entries to matching WordNet senses. The same 20 expected-answer lists remain unchanged. `evaluation-compact.json` records 19/20 covered answers, 11/20 ranked first and 16/20 in the first five. This development set guided changes and is not held-out accuracy. Negation and missing vocabulary still cause failures.

Eleven unit tests pass. Compact searches took roughly 2–5 seconds locally, using separate translation/embedding processes, SQLite and memory-mapped quantized vectors. The earlier timing above describes the original in-process implementation. The frontend displays translated query text so translation mistakes can be noticed.

The original improved in-process service used approximately 1.15 GB on Windows. The `runtime-1` asset workflow subsequently passed its 512 MB container check. Both public deployments and real English/Hindi searches were verified on 18 October 2026; see the project README for that historical deployment and its latency observations.

## Speed update — 22 October 2026

- All 28 API/retrieval/bridge/cache/worker tests pass locally. They check expiry, LRU bounds, filter changes, Unicode aliases, independent result dictionaries, worker reuse, memory fallback, timeout cleanup and model isolation.
- The TypeScript/Vite production build passes.
- The same 20 descriptions, expected-answer lists and assets were evaluated again. `evaluation-performance.json` retains **19/20 covered, 11/20 first and 16/20 first five**, matching the previous compact evaluation; all 20 returned word lists are identical. This is still a development diagnostic, not held-out accuracy.
- `performance-local.json` records direct, sequential Python searches with one BLAS/OMP thread. First English search: **1,612.262 ms**; different English description with the model retained: **168.604 ms**; repeated English: **0.028 ms**; repeated Hindi: **0.066 ms**; reapplying result language to cached Hindi scores: **21.067 ms**. These exclude HTTP and free-host startup. Prefix filtering still required a dictionary metadata scan (**1,161.249 ms** in that run).
- First Hindi search remained **2,972.434 ms** locally. A new Hindi translation closes the encoder and loads translation separately, preserving the model-isolation design. This remains a slower path than a warm English query.
- The API smoke test runs separately against a real local HTTP server, covering repeats, distinct descriptions, multiple Hindi descriptions, model switches, language filters, prefix aliases and an impossible prefix.

Docker is unavailable locally. The final runtime passed the **2 GB/no-extra-swap GitHub container check**, corresponding to the Vercel Hobby memory budget; retaining the original encoder reliably on Render's 512 MB budget was not established. [Successful CI run](https://github.com/Rohan-Ktksu/shabdanveshi/actions/runs/39793080917) includes all 28 tests, the frontend build and the real API workload. No OOM kills occurred. All 20 returned word lists matched the original code on the same Linux runner. Its diagnostic counts were 10/20 first answers and 16/20 first-five answers; quantized CPU execution can differ from Windows, so the unchanged original code is the same-platform comparison.

The production API is now **https://shabdanveshi-api.vercel.app**, published through the Vercel CLI. Health reported ready with both corpus counts, and requests with the GitHub Pages Origin passed CORS. `performance-live.json` records sequential public requests following a health request: first English **2.973 s**, different English **0.412 s**, repeated English **0.951 s**, first Hindi **3.374 s** and repeated Hindi **0.093 s**, including HTTP/network delay. Both book-lover descriptions returned bibliophile first. Server processing times are recorded separately. These observations exclude a full cold start and are not guarantees; per-instance caches disappear when a function instance is recycled. Hindi-only/both result quality remains experimental, including the weak first result recorded for one language-change example.

Vercel bundles the verified assets at build time. The production model, Hugging Face tokenizer, original graph optimization settings, ranking rules and expected-answer lists are preserved. Native Git auto-deploy remains pending because Vercel's API reports a missing login connection; the CLI deployment is independent of that connection.

The final public Vercel API also passed `SHABD_SMOKE_URL=https://shabdanveshi-api.vercel.app python -m backend.deployment_smoke`: ten lifecycle/filter requests plus the unchanged 20 diagnostic descriptions. Its counts were 10/20 first and 16/20 first five, consistent with the Linux container diagnostic. The strict original-code comparison was performed in CI, not against the historical Render service.
