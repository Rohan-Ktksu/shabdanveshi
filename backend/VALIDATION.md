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

## Remaining verification

## Compact runtime update

Local OPUS-MT translation and an exact-gloss bridge now connect Hindi entries to matching WordNet senses. The same 20 expected-answer lists remain unchanged. `evaluation-compact.json` records 19/20 covered answers, 11/20 ranked first and 16/20 in the first five. This development set guided changes and is not held-out accuracy. Negation and missing vocabulary still cause failures.

Eleven unit tests pass. Compact searches took roughly 2–5 seconds locally, using separate translation/embedding processes, SQLite and memory-mapped quantized vectors. The earlier timing above describes the original in-process implementation. The frontend displays translated query text so translation mistakes can be noticed.

The original improved in-process service used approximately 1.15 GB on Windows. Docker is not installed locally, so the compact runtime has not yet passed a 512 MB Linux memory limit. The manual runtime-assets workflow enforces that limit before publishing deployable resources. Render deployment and production availability remain unverified.

Public hosting, production CORS, memory limits and end-to-end browser rendering of live results remain unverified. Browser inspection was blocked by the browser access policy in this run. Frontend compilation and local HTTP delivery passed; those checks do not substitute for visual QA.
