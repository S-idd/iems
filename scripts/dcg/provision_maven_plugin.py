#!/usr/bin/env python3
"""Stage already-built, hash-pinned official DCG artifacts in a private file repository.

Does not rebuild, publish, or edit the installed DCG distribution.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

PINS = Path(__file__).with_name('maven-plugin-artifacts.json')


def provision(build_root, destination):
    pins = json.loads(PINS.read_text())
    if destination.exists():
        raise FileExistsError(f'Refusing existing repository: {destination}')
    data = {}
    for name, item in pins['artifacts'].items():
        value = (build_root / item['source']).read_bytes()
        if hashlib.sha256(value).hexdigest() != item['sha256']:
            raise RuntimeError(f'Unverified artifact: {item["source"]}')
        data[name] = value
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix='.dcg-maven-stage-') as temporary:
        stage = Path(temporary) / 'repository'
        stage.mkdir(mode=0o700)
        for name, value in data.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value)
            for algorithm in ('sha1', 'sha256'):
                Path(str(path) + '.' + algorithm).write_text(hashlib.new(algorithm, value).hexdigest() + '\n')
        (stage / 'provenance.json').write_text(json.dumps(pins, indent=2) + '\n')
        for path in stage.rglob('*'):
            path.chmod(0o700 if path.is_dir() else 0o600)
        if destination.exists():
            raise FileExistsError(destination)
        stage.rename(destination)
    return len(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-root', type=Path, required=True)
    parser.add_argument('--repository', type=Path, default=Path(__file__).resolve().parents[2] / '.dcg/maven-repository')
    args = parser.parse_args()
    os.umask(0o077)
    print(f'Staged {provision(args.build_root, args.repository)} verified artifacts in {args.repository}')


if __name__ == '__main__':
    main()
