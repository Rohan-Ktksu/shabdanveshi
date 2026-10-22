"""Isolated inference, optionally serving multiple encoder requests."""
import json
import sys


def run(request, model):
    if request['mode'] == 'translate':
        return model.translate(request['text'])
    return model.encode([request['text']])[0].tolist()


def load(mode):
    if mode == 'translate':
        from .translation import Translator
        return Translator()
    if mode == 'encode':
        from .encoder import Encoder
        return Encoder(threads=1)
    raise ValueError('Unsupported inference mode')


def main():
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    if '--serve' in sys.argv:
        model = mode = None
        for line in sys.stdin:
            try:
                request = json.loads(line)
                if model is None:
                    mode = request['mode']
                    model = load(mode)
                if request['mode'] != mode:
                    raise ValueError('Models must not overlap in a worker')
                print(json.dumps({'result': run(request, model)}, ensure_ascii=False), flush=True)
            except Exception:
                print(json.dumps({'error': 'inference_failed'}), flush=True)
                return
    else:
        request = json.load(sys.stdin)
        print(json.dumps(run(request, load(request['mode'])), ensure_ascii=False))


if __name__ == '__main__':
    main()
