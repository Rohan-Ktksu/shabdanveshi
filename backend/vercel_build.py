"""Bundle checksum-pinned assets at build time, never during a cold request."""
import os
from .config import DATA, MODEL

ASSETS_URL = 'https://github.com/Rohan-Ktksu/shabdanveshi/releases/download/runtime-1/runtime-assets.tar.gz'
ASSETS_SHA256 = 'd91b32e8f816f3048ed31822bb017d3fb3f40902f207a30413841af33f6485af'


def main():
    os.environ.setdefault('ASSETS_URL', ASSETS_URL)
    os.environ.setdefault('ASSETS_SHA256', ASSETS_SHA256)
    if not (DATA / 'compact' / 'metadata.json').exists():
        from .bootstrap import main as bootstrap
        bootstrap()
    required = [MODEL/'model_quantized.onnx', MODEL/'tokenizer.json',
                MODEL.parent/'opus-mt-hi-en'/'encoder_model_quantized.onnx',
                MODEL.parent/'opus-mt-hi-en'/'decoder_model_quantized.onnx',
                DATA/'compact'/'dictionary.sqlite', DATA/'compact'/'vectors.npy']
    if not all(path.is_file() for path in required):
        raise RuntimeError('Build is missing model/index assets; refusing an incomplete deployment')
    print('Verified runtime assets are ready to bundle. No startup download is required.')


if __name__ == '__main__':
    main()
