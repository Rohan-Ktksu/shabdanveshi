"""Package only redistributable runtime resources, never credentials or raw caches."""
import hashlib
from pathlib import Path
import tarfile
from .config import ROOT, DATA, MODEL
from .translation import TRANSLATION_DIR, TRANSLATION_FILES


def main():
    target=ROOT.parent/'runtime-assets.tar.gz'
    files=list((DATA/'compact').glob('*'))
    files += [MODEL/'model_quantized.onnx',MODEL/'tokenizer.json']
    files += [TRANSLATION_DIR/Path(name).name for name in TRANSLATION_FILES]
    files += list((ROOT/'licenses').glob('*'))+[ROOT/'ATTRIBUTION.md']
    with tarfile.open(target,'w:gz') as archive:
        for path in files:
            if path.suffix == '.sqlite' and path.name != 'dictionary.sqlite': continue
            if path.is_file(): archive.add(path,arcname=path.relative_to(ROOT.parent).as_posix())
    with target.open('rb') as source:
        digest=hashlib.file_digest(source,'sha256').hexdigest()
    target.with_suffix(target.suffix+'.sha256').write_text(digest+'\n')
    print(f'{target.name}: {target.stat().st_size:,} bytes; SHA256 {digest}')


if __name__=='__main__': main()
