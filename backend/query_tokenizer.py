"""Compact SentencePiece representation of the existing E5 Unigram vocabulary."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import NamedTuple
from .config import MODEL, MAX_TOKENS, ROOT

COMPACT_TOKENIZER = MODEL / 'query-tokenizer.model'
MANIFEST = MODEL / 'query-tokenizer.json'


def prepare():
    # Conversion runs in its own process: the temporary JSON/protobuf objects
    # must be gone before the inference model starts on a small host.
    from sentencepiece import sentencepiece_model_pb2 as pb
    source = (MODEL / 'tokenizer.json').read_bytes()
    data = json.loads(source)
    normalizers = data['normalizer']['normalizers']
    if (data['model']['type'] != 'Unigram' or data['model']['unk_id'] != 3
            or normalizers[0]['type'] != 'Precompiled'
            or normalizers[1] != {'type':'Replace', 'pattern':{'Regex':' {2,}'}, 'content':' '}
            or data['pre_tokenizer'] != {'type':'Metaspace', 'replacement':'▁', 'add_prefix_space':True}):
        raise ValueError('Unsupported tokenizer configuration; do not approximate its vocabulary')
    model = pb.ModelProto()
    model.trainer_spec.model_type = pb.TrainerSpec.UNIGRAM
    model.trainer_spec.vocab_size = len(data['model']['vocab'])
    model.trainer_spec.unk_id, model.trainer_spec.bos_id = 3, 0
    model.trainer_spec.eos_id, model.trainer_spec.pad_id = 2, 1
    model.normalizer_spec.precompiled_charsmap = base64.b64decode(normalizers[0]['precompiled_charsmap'])
    model.normalizer_spec.add_dummy_prefix = True
    model.normalizer_spec.remove_extra_whitespaces = True
    model.normalizer_spec.escape_whitespaces = True
    for index, (word, score) in enumerate(data['model']['vocab']):
        piece = model.pieces.add(piece=word, score=score)
        piece.type = (pb.ModelProto.SentencePiece.UNKNOWN if index == 3 else
                      pb.ModelProto.SentencePiece.CONTROL if index in (0, 1, 2) else
                      pb.ModelProto.SentencePiece.USER_DEFINED if word == '<mask>' else
                      pb.ModelProto.SentencePiece.NORMAL)
    encoded = model.SerializeToString()
    temporary = COMPACT_TOKENIZER.with_suffix('.tmp')
    temporary.write_bytes(encoded)
    temporary.replace(COMPACT_TOKENIZER)
    MANIFEST.write_text(json.dumps({'format':1,
        'source_sha256':hashlib.sha256(source).hexdigest(),
        'model_sha256':hashlib.sha256(encoded).hexdigest()}), encoding='utf-8')


def ensure_prepared():
    source_hash = hashlib.sha256((MODEL / 'tokenizer.json').read_bytes()).hexdigest()
    try:
        manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
        ready = (manifest['format'] == 1 and manifest['source_sha256'] == source_hash
                 and manifest['model_sha256'] == hashlib.sha256(COMPACT_TOKENIZER.read_bytes()).hexdigest())
    except (OSError, ValueError, KeyError):
        ready = False
    if not ready:
        subprocess.run([sys.executable, '-m', 'backend.query_tokenizer'], check=True, cwd=ROOT.parent,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)


class Encoding(NamedTuple):
    ids: list[int]
    attention_mask: list[int]
    type_ids: list[int]


class QueryTokenizer:
    def __init__(self):
        import sentencepiece as spm
        self.processor = spm.SentencePieceProcessor(model_file=str(COMPACT_TOKENIZER))

    def encode(self, text):
        # Fast tokenizers recognize these added tokens before normalization.
        controls = {'<s>':0, '<pad>':1, '</s>':2, '<unk>':3}
        pieces = re.split(r'(<s>|<pad>|</s>|<unk>)', text)
        result = []
        for index, piece in enumerate(pieces):
            if piece in controls:
                result.append(controls[piece])
            else:
                result.extend(self.processor.encode(piece, out_type=int))
                if index < len(pieces)-1 and piece and piece[-1].isspace():
                    result.append(6)  # Preserve the space before an added token.
        return result

    def encode_batch(self, texts):
        rows = [[0, *self.encode(text)[:MAX_TOKENS-2], 2] for text in texts]
        length = max(map(len, rows))
        return [Encoding(ids + [1] * (length-len(ids)), [1] * len(ids) + [0] * (length-len(ids)),
                         [0] * length) for ids in rows]


if __name__ == '__main__':
    prepare()
