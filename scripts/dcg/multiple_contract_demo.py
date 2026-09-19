#!/usr/bin/env python3
"""Rehearse two rejected contracts, automatic reset, and real IEMS recovery.

Requires an explicitly selected verified no-AI development DCG_HOME and Java 21.
Only temporary copies are changed. Evidence is retained; private DBs are removed.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import sqlite3
import subprocess
import tempfile
import time
import urllib.request

from cli_explain import retain_history as snapshot_history, explain_failures, read_failures
from dcg_package import PHASE1_CAPABILITIES, validate_package

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'scripts/dcg/fixtures/multiple-breaking'
JAR = 'inclusive-education-management-system-1.0.0-SNAPSHOT.jar'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    return {str(p.relative_to(root)): sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


@contextmanager
def candidates(app, fixtures=FIXTURES):
    """Validate every input before any mutation; restore exact bytes on all exits."""
    manifest = json.loads((fixtures / 'manifest.json').read_text())
    replacements = {}
    for name, item in manifest['contracts'].items():
        require(name in ('iems.enrollment', 'iems.scholarship'), 'Unexpected fixture contract')
        require(Path(item['file']).name == item['file'], 'Fixture path must be a filename')
        require(sha((app / 'contracts' / name / 'v1.json').read_bytes()) == item['baseline_sha256'],
                f'Baseline changed for {name}; review fixture before rehearsal')
        data = (fixtures / item['file']).read_bytes()
        require(sha(data) == item['fixture_sha256'], f'Fixture integrity failed: {name}')
        replacements[app / 'contracts' / name / 'candidate.json'] = data
    require(len(replacements) == 2, 'Exactly two breaking fixtures required')
    originals = {p: p.read_bytes() for p in replacements}
    try:
        for path, data in replacements.items():
            path.write_bytes(data)
        yield
    finally:
        for path, data in originals.items():
            path.write_bytes(data)
        require(all(p.read_bytes() == data for p, data in originals.items()), 'Candidate reset failed')


def verify_package(package):
    return validate_package(package, required_capabilities=PHASE1_CAPABILITIES)['version']


def history(path):
    with sqlite3.connect(path) as db:
        return db.execute('SELECT contract_id,status FROM check_runs ORDER BY contract_id').fetchall()


def rust_processes():
    lines = subprocess.check_output(['ps', '-axo', 'pid=,comm='], text=True).splitlines()
    return [line for line in lines if line.split() and line.split()[-1].split('/')[-1] == 'dcgaimodel']


def stop_child(process):
    """Stop only the new process group owned by this rehearsal."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=30)
        return False
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)
        return True


def run(evidence, package, retain_history=False):
    evidence.mkdir(parents=True, exist_ok=False, mode=0o700)
    evidence.chmod(0o700)
    report = {'result': 'INCOMPLETE', 'commands': [], 'source_contracts_before': inventory(ROOT / 'contracts')}
    package_before = inventory(package)
    report['package'] = str(package)
    report['package_version'] = verify_package(package)
    report['fixtures'] = json.loads((FIXTURES / 'manifest.json').read_text())
    env = dict(os.environ)
    if env.get('JAVA_HOME'):
        env['PATH'] = env['JAVA_HOME'] + '/bin:' + env['PATH']
    real_java = shutil.which('java', path=env['PATH'])
    require(real_java is not None, 'Java 21 required')
    require(not rust_processes(), 'Stop the existing Rust model before the no-AI rehearsal')

    def command(args, label, expected=0):
        process = subprocess.Popen(list(map(str, args)), env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=90)
            result = subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
        finally:
            if process.poll() is None:
                stop_child(process)
        (evidence / f'{label}.log').write_text(result.stdout + result.stderr)
        report['commands'].append({'argv': list(map(str, args)), 'exit': result.returncode, 'log': f'{label}.log'})
        require(result.returncode == expected, f'{label}: expected exit {expected}, got {result.returncode}; inspect log')
        return result.returncode

    try:
        with tempfile.TemporaryDirectory(prefix='iems-multiple-contracts-') as directory:
            temp = Path(directory)
            app = temp / 'iems'
            app.mkdir()
            shutil.copytree(ROOT / 'contracts', app / 'contracts')
            shutil.copytree(ROOT / 'scripts', app / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            (app / 'target').mkdir()
            shutil.copyfile(ROOT / 'target' / JAR, app / 'target' / JAR)
            before = inventory(app / 'contracts')
            tools = temp / 'tools'
            tools.mkdir()
            marker = temp / 'iems-java-dispatches'
            # Observe the real final Java dispatch; never stub the engine or IEMS.
            shim = tools / 'java'
            shim.write_text('#!/bin/bash\ncase "$*" in *inclusive-education-management-system*) '
                            'printf "dispatched\\n" >> "$IEMS_DISPATCH_MARKER";; esac\n'
                            'exec "$IEMS_REAL_JAVA" "$@"\n')
            shim.chmod(0o755)
            env.update(PATH=str(tools) + ':' + env['PATH'], IEMS_REAL_JAVA=real_java,
                       IEMS_DISPATCH_MARKER=str(marker), DCG_HOME=str(package), DCG_AI_ENABLED='false',
                       GIT_DIR=str(ROOT / '.git'), IEMS_JDBC_URL='jdbc:sqlite:' + str(temp / 'iems.db'),
                       IEMS_JWT_SECRET=secrets.token_hex(40), IEMS_DEMO_ADMIN_PASSWORD=secrets.token_hex(20))
            ids = sorted(p.name for p in (app / 'contracts').glob('iems.*'))
            expected_pass = [(name, 'PASS') for name in ids]
            env['DCG_SQLITE_PATH'] = str(temp / 'baseline.db')
            command([app / 'scripts/dcg.sh', 'lint'], 'baseline-lint')
            command([app / 'scripts/dcg.sh', 'check', 'sqlite'], 'baseline-check')
            report['baseline_rows'] = history(env['DCG_SQLITE_PATH'])
            require(report['baseline_rows'] == expected_pass, 'Initial candidates must all pass')
            print('1. Baseline: all four contracts PASS.', flush=True)
            try:
                with candidates(app):
                    print('2. Applying two breaking fixtures: enrollment.studentId and scholarship.amount.', flush=True)
                    report['breaking_contract_hashes'] = inventory(app / 'contracts')
                    env['DCG_SQLITE_PATH'] = str(temp / 'breaking.db')
                    report['blocking_exit'] = command([app / 'scripts/database/run_demo.sh', 'sqlite'], 'two-failures', 1)
                    rows = history(env['DCG_SQLITE_PATH'])
                    report['breaking_rows'] = rows
                    expected = [(name, 'FAIL' if name in report['fixtures']['contracts'] else 'PASS') for name in ids]
                    require(rows == expected, 'Expected exactly two FAILs and two PASSs')
                    report['blocked_java_dispatch_count'] = len(marker.read_text().splitlines()) if marker.exists() else 0
                    require(report['blocked_java_dispatch_count'] == 0, 'Breaking gate dispatched IEMS Java')
                    print('3. Both contracts FAIL; launcher exit 1; IEMS Java dispatches: 0.', flush=True)
            finally:
                report['restored_contract_hashes'] = inventory(app / 'contracts')
                report['automatic_reset_exact'] = report['restored_contract_hashes'] == before
                require(report['automatic_reset_exact'], 'Temporary contracts were not restored exactly')
            if retain_history:
                retained = evidence / 'history.sqlite'
                snapshot_history(temp / 'breaking.db', retained)
                report['retained_history'] = str(retained)
                summary = explain_failures(retained, package, evidence, env)
                summary.update(overall_breaking_exit=report['blocking_exit'],
                               blocked_java_dispatch_count=report['blocked_java_dispatch_count'])
                (evidence / 'explain-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
                report['failure_run_ids'] = {item['contract']: item['run_id'] for item in summary['failures']}
                report['explain_commands'] = [{'command': item['command'], 'exit': item['explain_exit'],
                                              'lookup_resolved': item['lookup_resolved']} for item in summary['failures']]
                print('Stable IDs and deterministic CLI explanations retained in ' + str(retained), flush=True)
            print('4. Automatic reset: original candidate bytes verified. Starting recovery.', flush=True)
            env['DCG_SQLITE_PATH'] = str(temp / 'recovery.db')
            with socket.socket() as s:
                s.bind(('127.0.0.1', 0))
                port = s.getsockname()[1]
            env['IEMS_PORT'] = str(port)
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with (evidence / 'recovery.log').open('w') as log:
                app_process = subprocess.Popen([str(app / 'scripts/database/run_demo.sh'), 'sqlite'],
                                               env=env, stdout=log, stderr=log, start_new_session=True)
                try:
                    for _ in range(120):
                        require(app_process.poll() is None, 'Recovery process exited before healthy')
                        try:
                            with opener.open(f'http://127.0.0.1:{port}/actuator/health', timeout=1) as response:
                                if response.status == 200:
                                    report['recovery_health'] = 200
                                    break
                        except OSError:
                            pass
                        time.sleep(.5)
                    else:
                        raise RuntimeError('Recovery health timeout')
                    report['recovery_rows'] = history(env['DCG_SQLITE_PATH'])
                    require(report['recovery_rows'] == expected_pass, 'Recovery checks did not all pass')
                    report['recovery_java_dispatch_count'] = len(marker.read_text().splitlines())
                    require(report['recovery_java_dispatch_count'] == 1, 'Expected one real recovery dispatch')
                    require(not rust_processes(), 'Unexpected Rust model process')
                finally:
                    report['forced_child_cleanup'] = stop_child(app_process)
                    report['intentional_shutdown_exit'] = app_process.returncode
                    report['commands'].append({'argv': [str(app / 'scripts/database/run_demo.sh'), 'sqlite'],
                                               'health': report.get('recovery_health'), 'shutdown_exit': app_process.returncode})
                with socket.socket() as s:
                    report['recovery_port_released'] = s.connect_ex(('127.0.0.1', port)) != 0
                require(report['recovery_port_released'], 'Recovery port still occupied')
                require(not report.get('forced_child_cleanup'), 'Recovery required forced shutdown')
            report['result'] = 'PASS'
        if retain_history:
            report['history_readable_after_cleanup'] = {row[1]: row[0] for row in read_failures(evidence / 'history.sqlite')} == report['failure_run_ids']
            require(report['history_readable_after_cleanup'], 'Retained IDs no longer resolve after cleanup')
    except BaseException as error:
        report['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        report['source_contracts_after'] = inventory(ROOT / 'contracts')
        report['source_contracts_unchanged'] = report['source_contracts_after'] == report['source_contracts_before']
        report['package_unchanged'] = inventory(package) == package_before
        report['rust_processes_after'] = rust_processes()
        if not report['source_contracts_unchanged'] or not report['package_unchanged'] or report['rust_processes_after']:
            report['result'] = 'INCOMPLETE'
        (evidence / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
        for path in evidence.iterdir():
            if path.is_file():
                path.chmod(0o600)
    require(report['result'] == 'PASS', 'Final preservation/cleanup verification failed')
    print('PASS: two failures blocked Java; candidates reset exactly; IEMS recovered (HTTP 200).')
    print(f'Evidence: {evidence / "results.json"}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True, help='New directory for this rehearsal')
    parser.add_argument('--retain-history', action='store_true', help='Retain private breaking-check history and real CLI explanations')
    args = parser.parse_args()
    os.umask(0o077)
    if not os.environ.get('DCG_HOME'):
        parser.error('Set DCG_HOME explicitly to the verified development package')
    def interrupted(signum, frame):
        raise InterruptedError(f'Rehearsal interrupted by signal {signum}; resetting temporary fixtures')
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, interrupted)
    try:
        run(args.evidence.resolve(), Path(os.environ['DCG_HOME']).resolve(), args.retain_history)
    except (Exception, KeyboardInterrupt) as error:
        print(f'Rehearsal failed: {error}', file=__import__('sys').stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
