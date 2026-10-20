"""Install this repo's self-contained skill without overwriting another skill."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil


def files(root: Path) -> dict:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dest', type=Path, default=Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'skills')
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / '.agents' / 'skills' / 'geoscience-github'
    destination = args.dest.expanduser().resolve() / source.name
    if destination.exists():
        if files(source) == files(destination):
            print(f'Already installed and identical: {destination}')
            return
        raise SystemExit(f'Destination exists with different contents; retained without overwriting: {destination}')
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    if files(source) != files(destination):
        raise SystemExit('Installed skill hash verification failed')
    print(f'Installed and verified: {destination}')
    print('Invoke $geoscience-github in your next Codex turn. If discovery is delayed, restart Codex.')


if __name__ == '__main__':
    main()
