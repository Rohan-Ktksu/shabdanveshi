"""Compare compact and reference token IDs, padding, masks and truncation."""
import gzip
import json
import random
from tokenizers import Tokenizer
from .config import MODEL, DATA, MAX_TOKENS
from .query_tokenizer import QueryTokenizer, ensure_prepared


def main():
    ensure_prepared()
    reference = Tokenizer.from_file(str(MODEL / 'tokenizer.json'))
    reference.enable_truncation(max_length=MAX_TOKENS)
    reference.enable_padding(pad_id=1, pad_token='<pad>')
    compact = QueryTokenizer()
    texts = ['someone who loves books', 'किताबों से प्रेम करने वाला व्यक्ति',
        'नींद न आने की समस्या', 'a feeling of longing for the past', 'जिसे कभी मृत्यु न आए',
        'किताबों  के   प्रेमी', 'café déjà vu', 'hello\tthere', 'hello\nthere',
        'hello   there', 'simple 😀 emojis', 'hello 𓀀𓀁 unknown', 'word\x00word',
        '<s>hello</s>', '<pad> hello <unk> there', '<mask> hello',
        'hello</s>there<s>again', 'a person who cannot sleep', 'an instrument for measuring temperature',
        'a feeling of sadness and happiness', 'नमस्ते दुनिया', 'stars and planets '*200]
    corpus = DATA / 'entries.json.gz'
    if corpus.exists():
        with gzip.open(corpus, 'rt', encoding='utf-8') as source:
            entries = json.load(source)
        texts += [e['definition'] for e in random.Random(42).sample(entries, min(1000, len(entries)))]
    texts = ['query: '+text for text in texts]
    original, derived = reference.encode_batch(texts), compact.encode_batch(texts)
    for index, (first, second) in enumerate(zip(original, derived)):
        assert first.ids == second.ids, f'Token IDs differ in fixture {index}'
        assert first.attention_mask == second.attention_mask, f'Mask differs in fixture {index}'
        assert first.type_ids == second.type_ids, f'Type IDs differ in fixture {index}'
    print(f'Compact tokenization matches reference IDs/masks/padding for {len(texts)} fixtures.')


if __name__ == '__main__':
    main()
