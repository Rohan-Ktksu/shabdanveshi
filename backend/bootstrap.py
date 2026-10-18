"""Fetch a hash-pinned release archive and extract only runtime data."""
import hashlib
import os
from pathlib import Path
import re
import tarfile
import urllib.request
from urllib.parse import urlparse
from .config import ROOT, DATA


def main():
    url=os.environ.get('ASSETS_URL','')
    digest=os.environ.get('ASSETS_SHA256','').lower()
    if urlparse(url).scheme!='https' or not re.fullmatch('[0-9a-f]{64}',digest):
        raise ValueError('Set HTTPS ASSETS_URL and its 64-character ASSETS_SHA256')
    DATA.mkdir(parents=True,exist_ok=True)
    archive=DATA/'runtime-download.tar.gz'
    with urllib.request.urlopen(url,timeout=180) as response, archive.open('wb') as target:
        while chunk:=response.read(1024*1024): target.write(chunk)
    with archive.open('rb') as source:
        if hashlib.file_digest(source,'sha256').hexdigest()!=digest:
            raise ValueError('Runtime archive checksum mismatch')
    with tarfile.open(archive,'r:gz') as source:
        for member in source.getmembers():
            allowed=member.name.startswith(('backend/models/','backend/licenses/','backend/data/generated/compact/')) or member.name=='backend/ATTRIBUTION.md'
            destination=(ROOT.parent/member.name).resolve()
            if not allowed or not destination.is_relative_to(ROOT.parent.resolve()) or not member.isfile():
                raise ValueError('Archive contains an unexpected path or link')
        source.extractall(ROOT.parent,filter='data')
    archive.unlink()


if __name__=='__main__': main()
