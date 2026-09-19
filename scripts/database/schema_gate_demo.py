#!/usr/bin/env python3
"""Prove a real DDL change is gated on an isolated pair of demo tables.
Set IEMS_JDBC_URL, IEMS_DB_USER and IEMS_DB_PASSWORD for a disposable database.
"""
import json
import os
from pathlib import Path
import platform
import secrets
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    if not os.environ.get('IEMS_JDBC_URL'):
        raise SystemExit('Set IEMS_JDBC_URL to a disposable demo database.')
    target = {('Darwin', 'arm64'): 'macos-arm64', ('Linux', 'x86_64'): 'linux-x64'}.get((platform.system(), platform.machine()))
    package = Path(os.environ.get('DCG_HOME', ROOT / '.dcg/runtime' / f'dcg-4.0.0-rc.1-{target}'))
    java = str(Path(os.environ['JAVA_HOME']) / 'bin/java') if os.environ.get('JAVA_HOME') else 'java'
    command = [java, '--class-path', str(package / 'lib/contract-cli-4.0.0-rc.1-all.jar'),
               str(ROOT / 'scripts/database/DatabaseTool.java')]
    suffix = secrets.token_hex(6)
    live, scratch = 'dcg_gate_live_' + suffix, 'dcg_gate_scratch_' + suffix
    evidence = ROOT / '.dcg/schema-demo' / suffix
    evidence.mkdir(parents=True)
    created = []
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
        if result.returncode != 0:
            raise RuntimeError('Compatible migration failed')
        current = snapshot(live, 'after-compatible.json')
        assert 'website' in json.loads(current.read_text())['properties']
        execute(f'ALTER TABLE {scratch} DROP COLUMN name')
        breaking = snapshot(scratch, 'breaking.json')
        result = subprocess.run([str(ROOT / 'scripts/dcg/gate.sh'), str(current), str(breaking), '--',
                                 *sql(f'ALTER TABLE {live} DROP COLUMN name')], timeout=45)
        if result.returncode != 1:
            raise RuntimeError(f'Expected compatibility rejection (1), got {result.returncode}')
        final = snapshot(live, 'after-blocked.json')
        assert 'name' in json.loads(final.read_text())['properties']
        print('VERIFIED: optional column applied; dropping name blocked; target still has name.')
        print('Schema evidence:', evidence)
    finally:
        for table in reversed(created):
            execute(f'DROP TABLE {table}')


if __name__ == '__main__':
    main()
