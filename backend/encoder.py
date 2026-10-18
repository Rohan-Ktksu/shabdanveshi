"""Quantized multilingual E5 inference with documented masked mean pooling."""
import threading
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer
from .config import MODEL, MAX_TOKENS


class Encoder:
    def __init__(self, threads=4):
        options = ort.SessionOptions()
        options.enable_cpu_mem_arena = False
        options.enable_mem_pattern = False
        options.add_session_config_entry('session.disable_prepacking', '1')
        options.intra_op_num_threads = threads
        self.session = ort.InferenceSession(str(MODEL / 'model_quantized.onnx'), options,
                                           providers=['CPUExecutionProvider'])
        self.tokenizer = Tokenizer.from_file(str(MODEL / 'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=MAX_TOKENS)
        self.tokenizer.enable_padding(pad_id=1, pad_token='<pad>')
        self.lock = threading.Lock()

    def encode(self, texts, kind='query'):
        if kind not in ('query', 'passage'):
            raise ValueError('Expected query or passage')
        with self.lock:
            tokens = self.tokenizer.encode_batch([f'{kind}: {text}' for text in texts])
            arrays = {
                'input_ids': np.asarray([t.ids for t in tokens], dtype=np.int64),
                'attention_mask': np.asarray([t.attention_mask for t in tokens], dtype=np.int64),
                'token_type_ids': np.asarray([t.type_ids for t in tokens], dtype=np.int64),
            }
            hidden = self.session.run(None, {i.name: arrays[i.name] for i in self.session.get_inputs()})[0]
        mask = arrays['attention_mask'][..., None].astype(np.float32)
        pooled = (hidden * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1e-9)
        return (pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-9)).astype(np.float32)
