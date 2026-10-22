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
- `performance-local.json` records direct, sequential Python searches with one BLAS/OMP thread. First English search: **1,911.509 ms**; different English description with the model retained: **244.314 ms**; repeated English: **0.056 ms**; repeated Hindi: **0.100 ms**; reapplying result language to cached Hindi scores: **59.017 ms**. These exclude HTTP and free-host startup. Prefix filtering still required a dictionary metadata scan (**1,210.280 ms** in that run).
- First Hindi search remained **4,445.991 ms** locally. Retaining both models would exceed the intended memory design, so a new Hindi translation still closes the encoder and loads translation separately. No first-Hindi speed improvement is claimed.
- The API smoke test runs separately against a real local HTTP server, covering repeats, distinct descriptions, multiple Hindi descriptions, model switches, language filters, prefix aliases and an impossible prefix.

Docker is unavailable locally. **The modified runtime has not yet passed the new 512 MB GitHub check or been deployed.** The check uses existing `runtime-1` assets, exercises the new lifecycle with a hard memory limit/no extra swap, and fails on OOM kills. Sync the Render Blueprint or select **After CI Checks Pass** before deployment. Historical production timings are not predictions of the new runtime's production latency.
