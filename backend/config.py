import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('SHABD_DATA_DIR', str(ROOT / 'data' / 'generated')))
MODEL = Path(os.environ.get('SHABD_MODEL_DIR', str(ROOT / 'models' / 'multilingual-e5-small')))
MODEL_REVISION = '761b726dd34fb83930e26aab4e9ac3899aa1fa78'
MAX_TOKENS = 128
