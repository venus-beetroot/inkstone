"""Paths and download helpers shared by the build scripts."""
import os, subprocess, tarfile, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'build' / 'cache'
PKG = CACHE / 'pkg'

SOURCES = {
    'kanji.json': 'https://raw.githubusercontent.com/davidluzgouveia/kanji-data/master/kanji.json',
    'complete.min.json': 'https://raw.githubusercontent.com/drkameleon/complete-hsk-vocabulary/main/complete.min.json',
    'dictionary.txt': 'https://raw.githubusercontent.com/skishore/makemeahanzi/master/dictionary.txt',
    'accents.txt': 'https://raw.githubusercontent.com/mifunetoshiro/kanjium/master/data/source_files/raw/accents.txt',
    **{f'n{n}.csv': f'https://raw.githubusercontent.com/jamsinclair/open-anki-jlpt-decks/main/src/n{n}.csv' for n in range(1, 6)},
}


def source(name):
    """Return the cached path of a raw data file, downloading it on first use."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if not path.exists():
        print('downloading', name)
        urllib.request.urlretrieve(SOURCES[name], path)
    return path


def npm_package(spec):
    """Return the unpacked directory of an npm package, e.g. 'hanzi-writer@3.7.3'."""
    PKG.mkdir(parents=True, exist_ok=True)
    folder = PKG / spec.replace('/', '_')
    if not folder.exists():
        print('fetching', spec)
        out = subprocess.run(['npm', 'pack', spec, '--silent'], cwd=PKG, check=True, capture_output=True, text=True).stdout.strip().splitlines()[-1]
        folder.mkdir()
        with tarfile.open(PKG / out) as t:
            for m in t.getmembers():
                m.name = m.name.split('/', 1)[1] if '/' in m.name else ''
                if m.name:
                    t.extract(m, folder)
        os.remove(PKG / out)
    return folder
