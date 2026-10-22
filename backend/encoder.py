"""Quantized multilingual E5 inference with documented masked mean pooling."""
import threading
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer
from .config import MODEL, MAX_TOKENS
from .memory import release_unused_memory


class Encoder:
    def __init__(self, threads=4, transient_tokenizer=False):
        options = ort.SessionOptions()
        options.enable_cpu_mem_arena = False
        options.enable_mem_pattern = False
        options.add_session_config_entry('session.disable_prepacking', '1')
        options.intra_op_num_threads = threads
        self.session = ort.InferenceSession(str(MODEL / 'model_quantized.onnx'), options,
                                           providers=['CPUExecutionProvider'])
        self.transient_tokenizer = transient_tokenizer
        self.tokenizer = None if transient_tokenizer else self.make_tokenizer()
        self.lock = threading.Lock()
        if transient_tokenizer:
            release_unused_memory()

    @staticmethod
    def make_tokenizer():
        tokenizer = Tokenizer.from_file(str(MODEL / 'tokenizer.json'))
        tokenizer.enable_truncation(max_length=MAX_TOKENS)
        tokenizer.enable_padding(pad_id=1, pad_token='<pad>')
        return tokenizer

    def encode(self, texts, kind='query'):
        if kind not in ('query', 'passage'):
            raise ValueError('Expected query or passage')
        with self.lock:
            tokenizer = self.tokenizer if self.tokenizer is not None else self.make_tokenizer()
            tokens = tokenizer.encode_batch([f'{kind}: {text}' for text in texts])
            arrays = {
                'input_ids': np.asarray([t.ids for t in tokens], dtype=np.int64),
                'attention_mask': np.asarray([t.attention_mask for t in tokens], dtype=np.int64),
                'token_type_ids': np.asarray([t.type_ids for t in tokens], dtype=np.int64),
            }
            if self.transient_tokenizer:
                # The large vocabulary is no longer needed once IDs are copied.
                del tokenizer, tokens
                release_unused_memory()
            hidden = self.session.run(None, {i.name: arrays[i.name] for i in self.session.get_inputs()})[0]
        mask = arrays['attention_mask'][..., None].astype(np.float32)
        pooled = (hidden * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1e-9)
        return (pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-9)).astype(np.float32)
