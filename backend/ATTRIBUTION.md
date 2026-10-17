# Data and model attribution

## English lexical data

Princeton University **WordNet 3.0**, downloaded from the NLTK data distribution:

- https://wordnet.princeton.edu/
- https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/wordnet.zip

The original WordNet license is included in `licenses/WORDNET-LICENSE.txt` and extracted to `data/generated/WORDNET-LICENSE.txt` by the preparation script. Preserve it with any distributed dictionary/index artifacts. We normalize synsets into word, aliases, part of speech and definition fields; no claim of authorship is made over the dictionary.

## Hindi lexical data

Hindi entries from **English Wiktionary contributors**, extracted by **Wiktextract / Kaikki.org**:

- Dataset: https://kaikki.org/dictionary/Hindi/
- Download: https://kaikki.org/dictionary/Hindi/kaikki.org-dictionary-Hindi.jsonl
- Extraction reference: Tatu Ylonen (2022), *Wiktextract: Wiktionary as Machine-Readable Structured Data*, LREC, pp. 1317–1325.
- Copyright and licensing: https://en.wiktionary.org/wiki/Wiktionary:Copyrights
- CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/

The derived Hindi dictionary is offered under CC BY-SA 4.0. We select noun, verb, adjective and adverb senses, omit inflection-only entries, join glosses and retain each entry's Wiktionary URL for contributor/history attribution. The dataset has **Hindi headwords but English definitions**. These definitions are not presented as Hindi translations. The frontend displays source links and a definition-language notice.

Kaikki labels its language-specific postprocessed export as deprecated. The preparation script currently uses that documented endpoint; if it is retired, a replacement extraction pipeline is required. Downloads are cached, and SHA-256 hashes record the exact data used. The upstream data can change between clean builds.

## Multilingual model

- Original model: **intfloat/multilingual-e5-small**, MIT license, https://huggingface.co/intfloat/multilingual-e5-small
- ONNX conversion: **Xenova/multilingual-e5-small**, https://huggingface.co/Xenova/multilingual-e5-small
- Pinned conversion revision: `761b726dd34fb83930e26aab4e9ac3899aa1fa78`

Inference uses ONNX Runtime and the Hugging Face Tokenizers library. Inputs carry E5's `query:` / `passage:` prefixes, followed by masked mean pooling and L2 normalization. This project truncates at 128 tokens, uses quantized weights, and records both settings and asset hashes. These choices can change quality relative to the original unquantized model.

Model weights, raw corpora and generated indexes are excluded from Git. Their licenses and provenance must accompany any later artifact distribution. No dictionary or model content is claimed as original project work.
