#!/usr/bin/env python3
"""Explain existing failure IDs with the real packaged CLI; never run a check."""
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess


def read_failures(history):
    history = Path(history)
    if not history.is_file():
        raise RuntimeError(f'Retained history missing: {history}')
    try:
        with closing(sqlite3.connect(history.resolve().as_uri() + '?mode=ro', uri=True)) as db:
            rows = db.execute("SELECT run_id,contract_id,status,breaking_changes FROM check_runs WHERE status='FAIL' ORDER BY contract_id").fetchall()
    except sqlite3.Error as error:
        raise RuntimeError(f'Retained history unreadable: {error}') from error
    if [row[1] for row in rows] != ['iems.enrollment', 'iems.scholarship'] or rows[0][0] == rows[1][0]:
        raise RuntimeError('Expected two distinct engine-generated failure IDs for enrollment and scholarship')
    return rows


def retain_history(source, destination):
    """SQLite backup API snapshots a closed-writer database, including any WAL."""
    destination = Path(destination)
    with destination.open('xb'):
        pass
    destination.chmod(0o600)
    with closing(sqlite3.connect(Path(source).resolve().as_uri() + '?mode=ro', uri=True)) as src:
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
    read_failures(destination)


def explain_failures(history, package, evidence, env):
    failures = []
    for run_id, contract, status, raw in read_failures(history):
        command = [str(package / 'bin/dcg'), 'explain', '--db', str(history), '--run', run_id]
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
        name = contract.removeprefix('iems.') + '-explain.txt'
        log = evidence / name
        log.write_text(result.stdout + '\n[stderr]\n' + result.stderr)
        log.chmod(0o600)
        # This CLI returns 1 for a resolved breaking run AND for an unknown ID.
        # Exit alone is insufficient: require its recorded FAIL and explanation.
        if result.returncode != 1 or 'Recorded status: FAIL' not in result.stdout or 'Why this matters:' not in result.stdout or 'How to fix:' not in result.stdout:
            raise RuntimeError(f'CLI explain did not resolve {contract} ({run_id}); exit {result.returncode}; see {name}')
        reasons = json.loads(raw)
        changes = []
        for reason in reasons:
            match = re.fullmatch(r'Field type changed: (.+) \((.+) -> (.+)\)', reason)
            if not match:
                raise RuntimeError(f'Unsupported stored change format: {reason}')
            field, previous, proposed = match.groups()
            if f"Field '{field}' changed type." not in result.stdout:
                raise RuntimeError(f'CLI explanation does not match stored field for {contract}')
            changes.append({'field': field, 'previous_type': previous, 'proposed_type': proposed,
                            'reason': reason, 'source': 'check_runs.breaking_changes'})
        if not changes:
            raise RuntimeError('Recorded failure has no type-change reasons')
        remediation = result.stdout.split('How to fix:\n', 1)[1].split('\n\n', 1)[0]
        failures.append({'contract': contract, 'run_id': run_id, 'verdict': status,
                         'explain_exit': result.returncode, 'lookup_resolved': True,
                         'explanation_source': 'dcg-cli', 'identity_source': 'check_runs',
                         'command': command, 'raw_output': name, 'stdout': result.stdout,
                         'changes': changes, 'remediation_from_cli': remediation})
    summary = {'ai_enabled': False, 'explain_exit_semantics': '1 = successfully explained a breaking run when output confirms recorded FAIL; 2 = database/command error',
               'history': str(history), 'failures': failures}
    output = evidence / 'explain-summary.json'
    output.write_text(json.dumps(summary, indent=2) + '\n')
    output.chmod(0o600)
    return summary
