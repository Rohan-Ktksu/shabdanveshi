"""Local OPUS-MT query translation; dictionary results remain source-backed."""
import json
import threading
import numpy as np
import onnxruntime as ort
import sentencepiece as spm
from .config import ROOT

TRANSLATION_REVISION = '99853100ed9d932987a6816e8cf7b1b6742a6116'
TRANSLATION_DIR = ROOT / 'models' / 'opus-mt-hi-en'
TRANSLATION_FILES = ['config.json', 'source.spm', 'target.spm', 'vocab.json',
                     'onnx/encoder_model_quantized.onnx', 'onnx/decoder_model_quantized.onnx']


class Translator:
    def __init__(self):
        options = ort.SessionOptions()
        options.enable_cpu_mem_arena = False
        options.enable_mem_pattern = False
        options.add_session_config_entry('session.disable_prepacking', '1')
        options.intra_op_num_threads = 2
        self.encoder = ort.InferenceSession(str(TRANSLATION_DIR / 'encoder_model_quantized.onnx'), options)
        self.decoder = ort.InferenceSession(str(TRANSLATION_DIR / 'decoder_model_quantized.onnx'), options)
        self.source = spm.SentencePieceProcessor(model_file=str(TRANSLATION_DIR / 'source.spm'))
        self.target = spm.SentencePieceProcessor(model_file=str(TRANSLATION_DIR / 'target.spm'))
        self.vocab = json.loads((TRANSLATION_DIR / 'vocab.json').read_text(encoding='utf-8'))
        self.inverse = {value: key for key, value in self.vocab.items()}
        self.config = json.loads((TRANSLATION_DIR / 'config.json').read_text())
        self.lock = threading.Lock()

    def translate(self, text):
        with self.lock:
            return self._translate(text)

    def _translate(self, text):
        config = self.config
        pieces = self.source.encode(text, out_type=str)
        # Fall back to multilingual retrieval instead of silently losing a suffix.
        if len(pieces) > 128:
            return None
        ids = np.array([[self.vocab.get(p, self.vocab['<unk>']) for p in pieces] + [config['eos_token_id']]], dtype=np.int64)
        attention = np.ones_like(ids)
        hidden = self.encoder.run(None, {'input_ids': ids, 'attention_mask': attention})[0]
        beams = [([config['decoder_start_token_id']], 0.)]
        finished = []
        for _ in range(64):
            batch = len(beams)
            logits = self.decoder.run(['logits'], {
                'input_ids': np.array([b[0] for b in beams], dtype=np.int64),
                'encoder_hidden_states': np.repeat(hidden, batch, axis=0),
                'encoder_attention_mask': np.repeat(attention, batch, axis=0),
            })[0][:, -1, :].astype(np.float64)
            logits[:, config['pad_token_id']] = -np.inf
            logits -= logits.max(axis=1, keepdims=True)
            logprob = logits - np.log(np.exp(logits).sum(axis=1, keepdims=True))
            scores = logprob + np.array([b[1] for b in beams])[:, None]
            best = np.argpartition(scores.ravel(), -12)[-12:]
            best = best[np.argsort(-scores.ravel()[best])]
            next_beams = []
            for candidate_rank, index in enumerate(best):
                parent, token = np.unravel_index(index, scores.shape)
                sequence = beams[parent][0] + [int(token)]
                score = float(scores[parent, token])
                if token == config['eos_token_id']:
                    if candidate_rank < 6:
                        finished.append((sequence, score / (len(sequence) - 1)))
                elif len(next_beams) < 6:
                    next_beams.append((sequence, score))
            beams = next_beams
            finished = sorted(finished, key=lambda item: item[1], reverse=True)[:6]
            if not beams or (len(finished) == 6 and finished[-1][1] >= max(b[1] / (len(b[0]) - 1) for b in beams)):
                break
        if not finished:
            return None
        sequence = max(finished, key=lambda item: item[1])[0]
        return self.target.decode([self.inverse[i] for i in sequence
                                   if i not in (config['pad_token_id'], config['eos_token_id'])]).strip() or None
