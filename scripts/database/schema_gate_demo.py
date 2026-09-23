#!/usr/bin/env python3
"""Prove a real DDL change is gated on an isolated pair of demo tables.
Set IEMS_JDBC_URL, IEMS_DB_USER and IEMS_DB_PASSWORD for a disposable database.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import secrets
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path,
                        help='New private evidence directory; default is .dcg/schema-demo/<random>')
    args = parser.parse_args()
    if not os.environ.get('IEMS_JDBC_URL'):
        raise SystemExit('Set IEMS_JDBC_URL to a disposable demo database.')
    target = {('Darwin', 'arm64'): 'macos-arm64', ('Linux', 'x86_64'): 'linux-x64'}.get((platform.system(), platform.machine()))
    package = Path(os.environ.get('DCG_HOME', ROOT / '.dcg/runtime' / f'dcg-4.0.0-rc.1-{target}'))
    java = str(Path(os.environ['JAVA_HOME']) / 'bin/java') if os.environ.get('JAVA_HOME') else 'java'
    command = [java, '--class-path', str(package / 'lib/contract-cli-4.0.0-rc.1-all.jar'),
               str(ROOT / 'scripts/database/DatabaseTool.java')]
    suffix = secrets.token_hex(6)
    live, scratch = 'dcg_gate_live_' + suffix, 'dcg_gate_scratch_' + suffix
    evidence = args.evidence.absolute() if args.evidence else ROOT / '.dcg/schema-demo' / suffix
    evidence.mkdir(parents=True, mode=0o700, exist_ok=False)
    created = []
    report = {'result': 'INCOMPLETE', 'engine': 'postgres' if os.environ['IEMS_JDBC_URL'].startswith(
        'jdbc:postgresql:') else 'mysql' if os.environ['IEMS_JDBC_URL'].startswith('jdbc:mysql:') else 'sqlite',
        'safeExit': None, 'breakingExit': None, 'targetPreserved': False, 'tablesRemoved': False}
    def sql(text):
        path = evidence / (secrets.token_hex(5) + '.sql')
        path.write_text(text + ';\n')
        return command + ['execute', str(path)]
    def execute(text):
        subprocess.run(sql(text), check=True, timeout=30)
    def snapshot(table, name):
        path = evidence / name
        subprocess.run(command + ['snapshot', table, str(path)], check=True, timeout=30)
        return path
    try:
        for table in [live, scratch]:
            execute(f'CREATE TABLE {table} (id INTEGER NOT NULL PRIMARY KEY, name VARCHAR(200) NOT NULL)')
            created.append(table)
        base = snapshot(live, 'base.json')
        execute(f'ALTER TABLE {scratch} ADD COLUMN website VARCHAR(200)')
        safe = snapshot(scratch, 'compatible.json')
        result = subprocess.run([str(ROOT / 'scripts/dcg/gate.sh'), str(base), str(safe), '--',
                                 *sql(f'ALTER TABLE {live} ADD COLUMN website VARCHAR(200)')], timeout=45)
        report['safeExit'] = result.returncode
        if result.returncode != 0:
            raise RuntimeError('Compatible migration failed')
        current = snapshot(live, 'after-compatible.json')
        if 'website' not in json.loads(current.read_text())['properties']:
            raise RuntimeError('Compatible migration did not add website')
        execute(f'ALTER TABLE {scratch} DROP COLUMN name')
        breaking = snapshot(scratch, 'breaking.json')
        result = subprocess.run([str(ROOT / 'scripts/dcg/gate.sh'), str(current), str(breaking), '--',
                                 *sql(f'ALTER TABLE {live} DROP COLUMN name')], timeout=45)
        report['breakingExit'] = result.returncode
        if result.returncode != 1:
            raise RuntimeError(f'Expected compatibility rejection (1), got {result.returncode}')
        final = snapshot(live, 'after-blocked.json')
        if 'name' not in json.loads(final.read_text())['properties']:
            raise RuntimeError('Breaking migration changed the protected target')
        report['targetPreserved'] = True
        report['result'] = 'PASS'
        print('VERIFIED: optional column applied; dropping name blocked; target still has name.')
        print('Schema evidence:', evidence)
    except BaseException as error:
        report['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        for table in reversed(created):
            execute(f'DROP TABLE {table}')
        report['tablesRemoved'] = True
        (evidence / 'results.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        for path in evidence.rglob('*'):
            path.chmod(0o700 if path.is_dir() else 0o600)


if __name__ == '__main__':
    main()
