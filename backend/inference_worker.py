"""Short-lived inference process for hosts with tight memory limits."""
import json
import sys


def main():
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    request = json.load(sys.stdin)
    if request['mode'] == 'translate':
        from .translation import Translator
        result = Translator().translate(request['text'])
    elif request['mode'] == 'encode':
        from .encoder import Encoder
        result = Encoder(threads=1).encode([request['text']])[0].tolist()
    else:
        raise ValueError('Unsupported inference mode')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
