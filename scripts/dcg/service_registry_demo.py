#!/usr/bin/env python3
"""Rehearse the packaged DCG registry, REST checks, UI, and SQLite restart."""
import argparse
import base64
import copy
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
import sys
import time
import urllib.error
import urllib.request
import uuid
from bs4 import BeautifulSoup
from dcg_package import PHASE1_CAPABILITIES, select_and_validate, validate_package

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'scripts/dcg/fixtures/multiple-breaking'
NAMES = ('accessibility', 'enrollment', 'notification', 'scholarship')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    return {str(p.relative_to(root)): sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}


def ensure(ok, message):
    if not ok:
        raise RuntimeError(message)


def verify_package(package):
    return validate_package(package, required_capabilities=PHASE1_CAPABILITIES)['version']


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def port_released(port):
    with socket.socket() as sock:
        return sock.connect_ex(('127.0.0.1', port)) != 0


def wait_port_released(port, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_released(port):
            return True
        time.sleep(.2)
    return port_released(port)


def rust_processes():
    lines = subprocess.check_output(['ps', '-axo', 'pid=,comm='], text=True).splitlines()
    return [line for line in lines if line.split() and line.split()[-1].split('/')[-1] == 'dcgaimodel']


def write_private(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    path.chmod(0o600)


def request(base, credentials, method, path, body=None, expected=200):
    data = None if body is None else json.dumps(body).encode()
    headers = {'Authorization': 'Basic ' + base64.b64encode(credentials.encode()).decode(), 'Accept': 'application/json'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            raw = response.read()
            code = response.status
            content_type = response.headers.get('Content-Type', '')
    except urllib.error.HTTPError as error:
        raw = error.read()
        code = error.code
        content_type = error.headers.get('Content-Type', '')
    ensure(code == expected, f'{method} {path}: expected HTTP {expected}, got {code}: {raw[:300]!r}')
    value = json.loads(raw) if 'json' in content_type and raw else raw.decode(errors='replace')
    return code, value


def wait_health(base, process, timeout=90, service='DCG service'):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ensure(process.poll() is None, service + ' exited before health became ready')
        try:
            with urllib.request.urlopen(base + '/actuator/health', timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(.4)
    raise RuntimeError(service + ' health timeout')


def stop_owned(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)
        raise RuntimeError('Owned DCG service required SIGKILL')


def start_service(package, runtime, port, username, password, log_path, *, extra_args=(), extra_env=None):
    # Package config has .example suffix; Spring requires a .properties filename.
    config = runtime / 'application.properties'
    if not config.exists():
        shutil.copyfile(package / 'config/application-local-demo.properties.example', config)
    java_home = os.environ.get('JAVA_HOME')
    ensure(java_home, 'Set JAVA_HOME to Java 21')
    env = {**os.environ, 'APP_SECURITY_USERNAME': username, 'APP_SECURITY_PASSWORD': password,
           'DCG_AI_ENABLED': 'false', 'SHADOW_INFERENCE_ENABLED': 'false', **(extra_env or {})}
    args = [str(Path(java_home) / 'bin/java'), '-jar', str(package / 'lib/contract-service-4.0.0-rc.1.jar'),
            '--spring.config.location=file:' + str(config), '--spring.profiles.active=local-demo',
            '--server.address=127.0.0.1', '--server.port=' + str(port), '--management.server.port=' + str(port),
            '--contracts.root=' + str(runtime / 'contracts'),
            '--contracts.policy-packs=' + str(runtime / 'contracts/policy-packs.json'),
            '--contracts.artifact.backend=filesystem', '--contracts.validation.strict-mode=false',
            '--checks.db.url=', '--checks.db.path=' + str(runtime / 'checks.db'),
            '--app.security.enabled=true', '--app.security.require-non-default-credentials=true',
            '--app.security.evidence-auth.mode=DISABLED', '--shadow.inference.enabled=false',
            '--notifications.enabled=' + ('true' if any(value == '--notifications.enabled=true' for value in extra_args) else 'false'),
            *[value for value in extra_args if value != '--notifications.enabled=true']]
    with log_path.open('w') as log:
        process = subprocess.Popen(args, cwd=runtime, env=env, stdout=log, stderr=log, start_new_session=True)
    try:
        wait_health('http://127.0.0.1:' + str(port), process)
    except BaseException:
        # Startup may be interrupted before the caller receives its process handle.
        stop_owned(process)
        raise
    return process, args


def poll_run(base, credentials, run_id):
    states = []
    for attempt in range(100):
        _, run = request(base, credentials, 'GET', '/checks/' + run_id)
        states.append(run['status'])
        if run['status'] in ('PASS', 'FAIL'):
            return run, states
        ensure(run['status'] in ('QUEUED', 'RUNNING'), 'Unexpected check state: ' + run['status'])
        time.sleep(.3)
    raise RuntimeError('Timed out waiting for check ' + run_id)


def ui_capture(base, credentials, directory, ids):
    directory.mkdir(mode=0o700)
    paths = {'dashboard': '/ui', 'contracts': '/ui/contracts', 'enrollment': '/ui/contracts/iems.enrollment',
             'compatible': '/ui/checks/' + ids['compatible'], 'breaking': '/ui/checks/' + ids['breaking']}
    summary = {}
    for label, route in paths.items():
        code, html = request(base, credentials, 'GET', route)
        ensure(code == 200 and '<html' in html.lower(), 'Real UI page unavailable: ' + label)
        (directory / (label + '.html')).write_text(html)
        text = BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)
        summary[label] = {'route': route, 'http': code, 'text_sha256': sha(text.encode()),
                          'visible_contract': 'iems.enrollment' in text,
                          'visible_pass_id': ids['compatible'] in text,
                          'visible_fail_id': ids['breaking'] in text,
                          'visible_pass': 'PASS' in text, 'visible_fail': 'FAIL' in text,
                          'body_bytes': len(html.encode())}
    contracts_html = (directory / 'contracts.html').read_text()
    enrollment_html = (directory / 'enrollment.html').read_text()
    fail_html = (directory / 'breaking.html').read_text()
    ensure(all('iems.' + name in contracts_html for name in NAMES), 'Four contracts absent from UI')
    ensure('v1' in enrollment_html and 'v2' in enrollment_html, 'Version history absent from UI')
    ensure('studentId' in fail_html, 'Breaking path absent from check UI')
    ensure(all(summary[name]['visible_contract'] for name in ('contracts', 'enrollment')), 'Contract absent from UI')
    ensure(summary['compatible']['visible_pass_id'] and summary['compatible']['visible_pass'], 'PASS UI mismatch')
    ensure(summary['breaking']['visible_fail_id'] and summary['breaking']['visible_fail'], 'FAIL UI mismatch')
    return summary


def verify_postman(base, username, password, ids, output_path):
    runner = ROOT / 'scripts/postman/run_dcg_collection.js'
    env = {**os.environ, 'DCG_DEMO_USERNAME': username, 'DCG_DEMO_PASSWORD': password}
    command = ['node', str(runner), 'Verify existing rehearsal', base,
               ids['compatible'], ids['breaking']]
    completed = subprocess.run(command, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, timeout=90)
    output_path.write_text(completed.stdout)
    ensure(completed.returncode == 0, 'Newman verification failed; see ' + str(output_path))
    return {'exit_code': completed.returncode, 'log': str(output_path), 'folder': 'Verify existing rehearsal'}


def run(evidence, package, validated_package=None):
    validated_package = validated_package or validate_package(package, required_capabilities=PHASE1_CAPABILITIES)
    evidence.mkdir(mode=0o700, parents=False, exist_ok=False)
    os.umask(0o077)
    runtime = evidence / 'runtime'
    runtime.mkdir(mode=0o700)
    (runtime / 'contracts').mkdir(mode=0o700)
    shutil.copyfile(package / 'contracts/policy-packs.json', runtime / 'contracts/policy-packs.json')
    evidence_dir = evidence / 'evidence'
    evidence_dir.mkdir(mode=0o700)
    (evidence / 'dashboard-evidence').mkdir(mode=0o700)
    (evidence / '.dcg-service-demo-marker').write_text(str(uuid.uuid4()))
    package_before = inventory(package)
    rc = ROOT / '.dcg/runtime/dcg-4.0.0-rc.1-macos-arm64'
    rc_before = inventory(rc)
    source_before = inventory(ROOT / 'contracts')
    result = {'result': 'INCOMPLETE', 'package': str(package), 'package_version': validated_package['version'],
              'validated_package': validated_package,
              'ai_enabled': False, 'storage': {'metadata_sqlite': str(runtime / 'checks.db'),
              'artifact_root': str(runtime / 'contracts'), 'iems_application_database': 'not used'},
              'configuration_keys': ['DCG_AI_ENABLED', 'SHADOW_INFERENCE_ENABLED', 'APP_SECURITY_USERNAME',
                                     'APP_SECURITY_PASSWORD', 'checks.db.path', 'contracts.root',
                                     'contracts.validation.strict-mode', 'server.port'],
              'contracts': {}, 'runs': {}}
    ensure(not rust_processes(), 'Stop the existing Rust model before rehearsal')
    port = free_port()
    ensure(port_released(port), 'Selected port became occupied')
    base = 'http://127.0.0.1:' + str(port)
    result['service_port'] = port
    result['dashboard_url'] = base + '/ui'
    username = 'iems-demo'
    password = secrets.token_hex(32)
    credentials = username + ':' + password
    process = None
    try:
        process, args = start_service(package, runtime, port, username, password, evidence / 'service-start.log')
        result['service_command'] = args
        ensure(not rust_processes(), 'Rust started with no-AI service')
        ensure((runtime / 'checks.db').is_file(), 'Isolated SQLite store not created')
        request(base, credentials, 'GET', '/ui')
        _, listed = request(base, credentials, 'GET', '/contracts')
        ensure(not listed, 'New registry is not empty')
        baselines = {}
        for name in NAMES:
            contract_id = 'iems.' + name
            original = ROOT / 'contracts' / contract_id / 'v1.json'
            baseline_bytes = original.read_bytes()
            baseline = json.loads(baseline_bytes)
            baselines[contract_id] = baseline
            body = {'contractId': contract_id, 'ownerTeam': 'iems', 'domain': 'education',
                    'compatibilityMode': 'BACKWARD', 'initialVersion': 'v1', 'schema': baseline}
            status, created = request(base, credentials, 'POST', '/contracts', body, 201)
            ensure(created['contractId'] == contract_id and created['versions'] == ['v1'], 'Unexpected registration result')
            _, fetched = request(base, credentials, 'GET', '/contracts/' + contract_id + '/versions/v1')
            ensure(fetched['schema'] == baseline, 'Published v1 differs from approved schema')
            record = {'contract_id': contract_id, 'registry_http': status, 'versions': created['versions'],
                      'baseline_sha256': sha(baseline_bytes), 'retrieved_schema_canonical_sha256': sha(json.dumps(fetched['schema'], sort_keys=True, separators=(',', ':')).encode()),
                      'submitted_schema_canonical_sha256': sha(json.dumps(baseline, sort_keys=True, separators=(',', ':')).encode()),
                      'owner_team': created['ownerTeam'], 'domain': created['domain']}
            result['contracts'][contract_id] = record
        write_private(evidence_dir / 'contract-registration.json', result['contracts'])
        compatible = copy.deepcopy(baselines['iems.scholarship'])
        compatible['properties']['sourceSystem'] = {'type': 'string'}
        breaking = json.loads((FIXTURES / 'enrollment.json').read_text())
        pinned = json.loads((FIXTURES / 'manifest.json').read_text())['contracts']['iems.enrollment']['fixture_sha256']
        ensure(sha((FIXTURES / 'enrollment.json').read_bytes()) == pinned, 'Breaking fixture changed')
        # Confirm deterministic compatibility before publishing the proposed schema.
        with (evidence_dir / 'compatible-candidate.json').open('w') as output:
            json.dump(compatible, output, indent=2)
        cli = subprocess.run([str(package / 'bin/dcg'), 'check-compat', '--base',
                              str(ROOT / 'contracts/iems.scholarship/v1.json'), '--candidate',
                              str(evidence_dir / 'compatible-candidate.json')],
                             env={**os.environ, 'DCG_AI_ENABLED': 'false'}, capture_output=True, text=True, timeout=30)
        ensure(cli.returncode == 0, 'Compatible candidate was not verified by deterministic engine')
        for contract_id, schema in [('iems.scholarship', compatible), ('iems.enrollment', breaking)]:
            status, published = request(base, credentials, 'POST', '/contracts/' + contract_id + '/versions',
                                        {'version': 'v2', 'schema': schema}, 201)
            ensure(published['version'] == 'v2', 'Version publication failed')
            _, fetched = request(base, credentials, 'GET', '/contracts/' + contract_id + '/versions/v2')
            ensure(fetched['schema'] == schema, 'Published v2 mismatch')
            result['contracts'][contract_id]['proposal_version'] = 'v2'
            result['contracts'][contract_id]['proposal_sha256'] = sha(json.dumps(schema, sort_keys=True, separators=(',', ':')).encode())
        write_private(evidence_dir / 'version-publication.json', result['contracts'])
        _, listed = request(base, credentials, 'GET', '/contracts')
        ensure({item['contractId'] for item in listed} == {'iems.' + n for n in NAMES}, 'Contract list mismatch')
        ids = {}
        for label, contract_id in [('compatible', 'iems.scholarship'), ('breaking', 'iems.enrollment')]:
            body = {'contractId': contract_id, 'baseVersion': 'v1', 'candidateVersion': 'v2',
                    'mode': 'BACKWARD', 'commitSha': 'local-demo', 'triggeredBy': 'iems-service-demo'}
            status, accepted = request(base, credentials, 'POST', '/checks', body, 202)
            ensure(accepted['status'] == 'QUEUED' and accepted['runId'], 'Check was not queued')
            run_id = accepted['runId']
            ids[label] = run_id
            final, states = poll_run(base, credentials, run_id)
            expected = 'PASS' if label == 'compatible' else 'FAIL'
            ensure(final['status'] == expected and final['contractId'] == contract_id, 'Wrong terminal check result')
            _, logs = request(base, credentials, 'GET', '/checks/' + run_id + '/logs')
            ensure(logs and all(entry['runId'] == run_id for entry in logs), 'Check logs missing/mismatched')
            if label == 'breaking':
                ensure(any('studentId' in change and 'integer -> string' in change for change in final['breakingChanges']),
                       'Breaking reason missing integer-to-string change')
            result['runs'][label] = {'run_id': run_id, 'http_accepted': status, 'initial_status': accepted['status'],
                                     'poll_states': states, 'final': final, 'log_count': len(logs),
                                     'request': body}
            write_private(evidence_dir / (label + '-check.json'), {'request': body, 'accepted': accepted})
            write_private(evidence_dir / (label + '-result.json'), final)
            write_private(evidence_dir / (label + '-logs.json'), logs)
        ensure(ids['compatible'] != ids['breaking'], 'Run IDs not unique')
        _, runs = request(base, credentials, 'GET', '/checks')
        ensure({r['runId'] for r in runs} == set(ids.values()), 'Unexpected service check runs')
        result['ui_before_restart'] = ui_capture(base, credentials, evidence / 'dashboard-evidence' / 'before', ids)
        (evidence / 'postman').mkdir(mode=0o700)
        result['newman_before_restart'] = verify_postman(base, username, password, ids, evidence / 'postman/before.log')
        before = {'contracts': listed, 'run_ids': sorted(ids.values()),
                  'versions': {name: request(base, credentials, 'GET', '/contracts/' + name + '/versions')[1]
                               for name in result['contracts']}}
        stop_owned(process)
        process = None
        ensure(port_released(port), 'Service port not released before restart')
        process, _ = start_service(package, runtime, port, username, password, evidence / 'service-restart.log')
        ensure(not rust_processes(), 'Rust started after restart')
        _, after_contracts = request(base, credentials, 'GET', '/contracts')
        ensure(after_contracts == before['contracts'], 'Registry changed across restart')
        after_versions = {name: request(base, credentials, 'GET', '/contracts/' + name + '/versions')[1]
                          for name in result['contracts']}
        ensure(after_versions == before['versions'], 'Versions changed across restart')
        for label, run_id in ids.items():
            _, same = request(base, credentials, 'GET', '/checks/' + run_id)
            ensure(same == result['runs'][label]['final'], 'Check result changed across restart')
            _, logs = request(base, credentials, 'GET', '/checks/' + run_id + '/logs')
            ensure(len(logs) == result['runs'][label]['log_count'], 'Logs changed across restart')
        _, after_runs = request(base, credentials, 'GET', '/checks')
        ensure({r['runId'] for r in after_runs} == set(ids.values()), 'Restart created or lost runs')
        result['ui_after_restart'] = ui_capture(base, credentials, evidence / 'dashboard-evidence' / 'after', ids)
        result['newman_after_restart'] = verify_postman(base, username, password, ids, evidence / 'postman/after.log')
        result['post_restart'] = {'contract_count': len(after_contracts), 'versions': after_versions,
                                  'run_ids': sorted(ids.values()), 'no_new_runs': len(after_runs) == 2}
        write_private(evidence_dir / 'post-restart-verification.json', result['post_restart'])
        result['result'] = 'PASS'
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        if process is not None:
            stop_owned(process)
        result['port_released'] = port_released(port)
        result['rust_after'] = rust_processes()
        result['source_contracts_unchanged'] = source_before == inventory(ROOT / 'contracts')
        result['package_unchanged'] = package_before == inventory(package)
        result['accepted_rc_unchanged'] = rc_before == inventory(rc)
        if not all(result[k] for k in ('port_released', 'source_contracts_unchanged', 'package_unchanged', 'accepted_rc_unchanged')) or result['rust_after']:
            result['result'] = 'INCOMPLETE'
        write_private(evidence / 'results.json', result)
        for path in evidence.rglob('*'):
            path.chmod(0o700 if path.is_dir() else 0o600)
    print('PASS:', evidence / 'results.json')


def serve_existing(evidence, package):
    evidence = evidence.resolve()
    ensure((evidence / '.dcg-service-demo-marker').is_file(), 'Not a DCG rehearsal directory')
    report = json.loads((evidence / 'results.json').read_text())
    ensure(report.get('result') == 'PASS' and report.get('port_released'), 'Rehearsal is not complete or port may be active')
    runtime = evidence / 'runtime'
    ensure((runtime / 'checks.db').is_file() and (runtime / 'contracts').is_dir(), 'Retained runtime missing')
    verify_package(package)
    ensure(not rust_processes(), 'Stop existing Rust model before live presentation')
    port = free_port()
    username = 'iems-demo'
    password = secrets.token_hex(32)
    process = None
    try:
        process, _ = start_service(package, runtime, port, username, password, evidence / 'service-presentation.log')
        print('DCG dashboard: http://127.0.0.1:' + str(port) + '/ui', flush=True)
        print('DCG username: ' + username, flush=True)
        print('DCG temporary password: ' + password, flush=True)
        print('Service status: http://127.0.0.1:' + str(port) + '/actuator/health', flush=True)
        print('Press Ctrl-C to stop this task-owned service.', flush=True)
        while process.poll() is None:
            time.sleep(.5)
        raise RuntimeError('DCG service exited unexpectedly; inspect service-presentation.log')
    except (KeyboardInterrupt, InterruptedError):
        pass
    finally:
        if process is not None:
            stop_owned(process)
        ensure(wait_port_released(port), 'Presentation service port not released')
    print('Presentation service stopped; retained history is unchanged.', flush=True)


def reset(evidence):
    evidence = evidence.resolve()
    ensure((evidence / '.dcg-service-demo-marker').is_file(), 'Not a DCG rehearsal directory')
    ensure(evidence.parent.name == 'rehearsals' and evidence.name.startswith('service-registry-dashboard-'),
           'Refusing reset outside named rehearsal area')
    report = json.loads((evidence / 'results.json').read_text())
    ensure(report.get('port_released'), 'Service port may still be active; stop owned process first')
    runtime = evidence / 'runtime'
    ensure(runtime.is_dir() and not runtime.is_symlink(), 'Runtime missing or unsafe')
    shutil.rmtree(runtime)
    print('Removed only rehearsal-owned runtime state:', runtime)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--dcg-home', type=Path,
                        help='Validated DCG development package; overrides DCG_HOME')
    parser.add_argument('--reset', action='store_true', help='Explicitly delete only this finished rehearsal runtime')
    parser.add_argument('--serve-existing', action='store_true', help='Reopen a completed rehearsal for live browser presentation until Ctrl-C')
    args = parser.parse_args()
    os.umask(0o077)
    ensure(not (args.reset and args.serve_existing), 'Choose reset or serve-existing, not both')
    if args.reset:
        reset(args.evidence)
        return
    ensure(not args.evidence.exists(), 'Evidence directory already exists')
    validated = select_and_validate(args.dcg_home, required_capabilities=PHASE1_CAPABILITIES)
    package = Path(validated['path'])
    if args.serve_existing:
        serve_existing(args.evidence, package)
        return
    def interrupted(signum, frame):
        raise InterruptedError('Signal ' + str(signum) + '; stopping owned service')
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, interrupted)
    run(args.evidence.resolve(), package, validated)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Rehearsal failed:', error, file=sys.stderr)
        raise SystemExit(1)
