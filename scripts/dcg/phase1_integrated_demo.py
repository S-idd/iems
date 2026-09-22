#!/usr/bin/env python3
"""Run the verified deterministic Phase 1 DCG/IEMS demonstrations in order."""

from __future__ import annotations

import argparse
from contextlib import closing
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
import urllib.request

from dcg_package import PHASE1_CAPABILITIES, select_and_validate, validate_package
from multiple_contract_demo import ROOT, JAR, inventory, require, rust_processes, sha, stop_child

REHEARSALS = ROOT / '.dcg/rehearsals'
ACCEPTED_RC = ROOT / '.dcg/runtime/dcg-4.0.0-rc.1-macos-arm64'
REQUIRED_SCENARIOS = ('baseline', 'compatible_contract', 'multiple_breaking_contracts',
                      'cli_explain', 'maven_gate', 'service_dashboard', 'webhook_delivery',
                      'runtime_validation', 'migration_gate', 'final_recovery')


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    path.chmod(0o600)


def prepare_evidence(evidence: Path) -> Path:
    root = REHEARSALS.resolve()
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    if evidence.absolute().parent.resolve() != root or not evidence.name.startswith('phase1-integrated-'):
        raise ValueError('Evidence must be a new phase1-integrated-* directory directly under .dcg/rehearsals')
    evidence.mkdir(mode=0o700, exist_ok=False)
    (evidence / '.phase1-integrated-marker').write_text('Phase 1 integrated rehearsal\n')
    return evidence.resolve()


def verify_development_package(package: Path) -> dict:
    validated = validate_package(package, required_capabilities=PHASE1_CAPABILITIES)
    if not ACCEPTED_RC.is_dir():
        raise FileNotFoundError('Accepted RC installation missing')
    if not (ROOT / 'target' / JAR).is_file():
        raise FileNotFoundError('Build current IEMS JAR first with mvn -B -ntp -DskipTests package')
    if not (ROOT / '.dcg/tools/node_modules/newman').is_dir():
        raise FileNotFoundError('Local Newman missing under .dcg/tools/node_modules')
    return validated


def available_port(used: set[int]) -> int:
    for _ in range(30):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        if port not in used:
            used.add(port)
            return port
    raise RuntimeError('Could not choose a unique local port')


def port_released(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(1)
        return sock.connect_ex(('127.0.0.1', port)) != 0


def task_owned_processes(evidence: Path) -> list[str]:
    result = subprocess.run(['ps', '-axo', 'pid=,args='], capture_output=True, text=True, check=True)
    needle = str(evidence.resolve())
    ancestors = {os.getpid()}
    parent = os.getppid()
    while parent > 1 and parent not in ancestors:
        ancestors.add(parent)
        found = subprocess.run(['ps', '-p', str(parent), '-o', 'ppid='], capture_output=True, text=True)
        parent = int(found.stdout.strip()) if found.returncode == 0 and found.stdout.strip().isdigit() else 0
    return [line.strip() for line in result.stdout.splitlines()
            if needle in line and line.strip().split(maxsplit=1)[0].isdigit() and
            int(line.strip().split(maxsplit=1)[0]) not in ancestors]


def process_identity(pid: int) -> str:
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'lstart='], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ''


def process_active(pid: int) -> bool:
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'stat='], capture_output=True, text=True)
    return result.returncode == 0 and bool(result.stdout.strip()) and not result.stdout.strip().startswith('Z')


def stop_recorded_process(evidence: Path) -> bool:
    marker = evidence / 'active-process.json'
    if not marker.exists():
        return True
    record = json.loads(marker.read_text())
    pid = record['pid']
    if process_identity(pid) != record['startedAt']:
        marker.unlink()
        return True
    command = subprocess.run(['ps', '-p', str(pid), '-o', 'command='], capture_output=True, text=True).stdout
    if record['identity'] not in command:
        raise RuntimeError('Owned PID identity changed; refusing to signal it')
    os.killpg(pid, signal.SIGTERM)
    deadline = time.monotonic() + 40
    while process_active(pid) and time.monotonic() < deadline:
        time.sleep(.2)
    if process_active(pid):
        raise RuntimeError('Owned process did not stop after SIGTERM')
    marker.unlink()
    return not record.get('port') or port_released(record['port'])


def active_marker(evidence: Path, process: subprocess.Popen, identity: str, stage: str,
                  port: int | None = None) -> None:
    write_json(evidence / 'active-process.json', {'pid': process.pid, 'startedAt': process_identity(process.pid),
                                                  'identity': identity, 'stage': stage, 'port': port})


def clear_marker(evidence: Path) -> None:
    (evidence / 'active-process.json').unlink(missing_ok=True)


def isolated_project(evidence: Path) -> Path:
    app = evidence / 'runtime/api-project'
    app.mkdir(parents=True, mode=0o700)
    shutil.copytree(ROOT / 'contracts', app / 'contracts')
    shutil.copytree(ROOT / 'runtime-contracts', app / 'runtime-contracts')
    shutil.copytree(ROOT / 'scripts', app / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
    (app / 'target').mkdir()
    os.link(ROOT / 'target' / JAR, app / 'target' / JAR)
    return app


def assert_disposable_targets(evidence: Path, app: Path, database: Path, history: Path) -> None:
    owned = evidence.resolve()
    require(owned.parent == REHEARSALS.resolve() and
            owned.name.startswith(('phase1-integrated-', 'phase2-integrated-')),
            'Not a named integrated rehearsal')
    for path in (app, database, history):
        require(path.resolve().is_relative_to(owned) and path.resolve() != owned,
                f'Refusing non-disposable path: {path}')
    require(app.resolve() != ROOT.resolve() and database.resolve() != (ROOT / '.dcg/data/iems.db').resolve(),
            'Refusing real IEMS project/database target')


def health_200(port: int, process: subprocess.Popen, timeout: int = 110) -> None:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        require(process.poll() is None, 'IEMS exited before healthy; inspect private application log')
        try:
            with opener.open(f'http://127.0.0.1:{port}/actuator/health', timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(.5)
    raise RuntimeError('IEMS health timeout')


def check_rows(db: Path) -> list[list[str]]:
    with closing(sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True)) as conn:
        return [list(row) for row in conn.execute('SELECT contract_id,status FROM check_runs ORDER BY contract_id')]


def wait_demo_admin(database: Path, process: subprocess.Popen, timeout: int = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        require(process.poll() is None, 'IEMS exited before demo admin initialization')
        if database.is_file():
            with closing(sqlite3.connect(database)) as conn:
                row = conn.execute("SELECT id FROM users WHERE username='demo-admin'").fetchone()
            if row:
                return
        time.sleep(.2)
    raise RuntimeError('IEMS health was ready but demo admin was not initialized')


def validate_api_rows(rows: list[list[str]]) -> None:
    expected = [[f'iems.{name}', 'PASS'] for name in ('accessibility', 'enrollment', 'notification', 'scholarship')]
    require(rows == expected, f'Expected four baseline contract PASS rows, got {rows}')


def api_run(evidence: Path, app: Path, stage: str, env: dict[str, str],
            used_ports: set[int], commands: list[dict], *, newman: bool) -> dict:
    runtime = evidence / 'runtime'
    port = available_port(used_ports)
    database = runtime / f'{stage}-iems.sqlite'
    history = runtime / f'{stage}-dcg-checks.sqlite'
    assert_disposable_targets(evidence, app, database, history)
    app_env = dict(env, IEMS_PORT=str(port), IEMS_JDBC_URL='jdbc:sqlite:' + str(database),
                   DCG_SQLITE_PATH=str(history), IEMS_JWT_SECRET=secrets.token_hex(40),
                   IEMS_DEMO_ADMIN_PASSWORD=secrets.token_hex(24), GIT_DIR=str(ROOT / '.git'))
    app_env['PATH'] = str(Path(app_env['JAVA_HOME']) / 'bin') + ':' + app_env.get('PATH', '')
    argv = [str(app / 'scripts/database/run_demo.sh'), 'sqlite']
    app_log = evidence / f'{stage}-iems.log'
    process = None
    api_summary = None
    try:
        with app_log.open('w') as output:
            process = subprocess.Popen(argv, cwd=app, env=app_env, stdout=output, stderr=output,
                                       start_new_session=True)
        active_marker(evidence, process, str(app / 'target' / JAR), stage, port)
        health_200(port, process)
        wait_demo_admin(database, process)
        require(not rust_processes(), 'Rust model observed while IEMS was running')
        if newman:
            seed = subprocess.run([sys.executable, str(ROOT / 'scripts/postman/seed_notification.py'), str(database)],
                                  cwd=ROOT, env=app_env, capture_output=True, text=True, timeout=20)
            (evidence / f'{stage}-seed.log').write_text(seed.stdout + seed.stderr)
            commands.append({'stage': stage + '-seed', 'argv': ['python3', 'scripts/postman/seed_notification.py',
                                                               str(database)], 'exit': seed.returncode,
                             'log': f'{stage}-seed.log'})
            require(seed.returncode == 0, 'Notification fixture failed')
            node_args = ['node', str(ROOT / 'scripts/postman/run_iems_integrated_collection.js'),
                         f'http://127.0.0.1:{port}']
            completed = subprocess.run(node_args, cwd=ROOT, env=app_env, capture_output=True, text=True, timeout=180)
            newman_log = evidence / f'{stage}-newman.log'
            newman_log.write_text(completed.stdout + completed.stderr)
            commands.append({'stage': stage + '-api', 'argv': node_args, 'exit': completed.returncode,
                             'log': newman_log.name})
            require(completed.returncode == 0, f'{stage} Newman failed; inspect private log')
            marker = [line.removeprefix('IEMS_INTEGRATED_SUMMARY=') for line in completed.stdout.splitlines()
                      if line.startswith('IEMS_INTEGRATED_SUMMARY=')]
            require(len(marker) == 1, 'Newman did not report request/assertion counts')
            api_summary = json.loads(marker[0])
            require(api_summary['failures'] == 0 and api_summary['requests'] > 0 and
                    api_summary['assertions'] > 0, 'Newman summary incomplete')
        rows = check_rows(history)
        validate_api_rows(rows)
        result = {'result': 'PASS', 'healthHttp': 200, 'port': port, 'applicationDb': str(database),
                  'dcgCheckHistory': str(history), 'contractRows': rows, 'api': api_summary,
                  'newmanLog': f'{stage}-newman.log' if newman else None}
        return result
    finally:
        if process is not None:
            forced = stop_child(process)
            commands.append({'stage': stage + '-start', 'argv': argv, 'health': 200 if history.exists() else None,
                             'shutdownExit': process.returncode, 'forcedCleanup': forced, 'log': app_log.name})
            clear_marker(evidence)
            require(not forced and port_released(port), f'{stage} IEMS process/port not cleanly released')


def run_child(evidence: Path, stage: str, argv: list[str], env: dict[str, str],
              commands: list[dict], timeout: int = 900) -> str:
    log = evidence / f'{stage}.log'
    process = None
    try:
        with log.open('w') as output:
            process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=output, stderr=output,
                                       start_new_session=True)
            identity = next((arg for arg in argv if arg.endswith('.py')), argv[0])
            active_marker(evidence, process, identity, stage)
            process.wait(timeout=timeout)
        commands.append({'stage': stage, 'argv': argv, 'exit': process.returncode, 'log': log.name})
        require(process.returncode == 0, f'{stage} exited {process.returncode}; inspect {log.name}')
        return log.read_text()
    except BaseException:
        if process is not None and process.poll() is None:
            stop_child(process)
        raise
    finally:
        clear_marker(evidence)


def require_result(path: Path, expected: str = 'PASS') -> dict:
    require(path.is_file(), f'Missing required sub-evidence: {path}')
    value = json.loads(path.read_text())
    require(value.get('result') == expected, f'{path}: expected {expected}, got {value.get("result")}')
    return value


def check_multiple(value: dict) -> None:
    require(value['blocking_exit'] == 1 and value['blocked_java_dispatch_count'] == 0,
            'Breaking launcher did not block Java')
    require(value['automatic_reset_exact'] and value['recovery_health'] == 200 and
            value['recovery_port_released'], 'Multiple-contract reset/recovery failed')
    failures = {row[0] for row in value['breaking_rows'] if row[1] == 'FAIL'}
    require(failures == {'iems.enrollment', 'iems.scholarship'}, 'Expected both CLI failures')
    require(set(value['failure_run_ids']) == failures and len(set(value['failure_run_ids'].values())) == 2,
            'Missing stable CLI failure IDs')
    require(all(item['lookup_resolved'] and item['exit'] == 1 for item in value['explain_commands']),
            'CLI explanation did not resolve both failures')


def check_maven(value: dict) -> None:
    items = {item['scenario']: item for item in value['scenarios']}
    compatible, breaking = items['compatible'], items['multiple-breaking']
    require(compatible['exit'] == 0 and len(compatible['verdicts']) == 4 and
            set(compatible['verdicts'].values()) == {'PASS'} and compatible['artifacts_after'],
            'Compatible Maven build did not package JAR')
    require(breaking['exit'] != 0 and breaking['verdicts'] ==
            {'iems.accessibility': 'PASS', 'iems.enrollment': 'FAIL'} and
            not breaking['artifacts_after'] and not breaking['packaging_reached'],
            'Breaking Maven build did not fail fast at validate')
    require(value['goal'] == 'check-compat' and value['phase'] == 'validate' and
            value['contracts_unchanged'] and value['package_unchanged'] and value['rc_unchanged'],
            'Maven gate provenance/preservation failed')


def check_service(value: dict) -> None:
    require(len(value['contracts']) == 4 and all(item['versions'] == ['v1']
            for item in value['contracts'].values()), 'Service registry baseline incomplete')
    runs = value['runs']
    require(runs['compatible']['final']['status'] == 'PASS' and
            runs['breaking']['final']['status'] == 'FAIL' and
            runs['breaking']['final']['runId'] == runs['breaking']['run_id'] and
            runs['breaking']['final']['contractId'] == 'iems.enrollment', 'Service run mismatch')
    require(value['ui_before_restart'] and value['ui_after_restart'] and
            value['post_restart']['no_new_runs'] and value['port_released'], 'Dashboard/persistence proof missing')


def check_webhook(value: dict) -> None:
    delivered, retry = value['runs']['delivered'], value['runs']['retry']
    require(delivered['check_status'] == retry['check_status'] == 'FAIL' and
            delivered['inbox_before_restart']['runId'] == delivered['run_id'] and
            retry['delivery_status_before_recovery'] == 'FAILED_RETRYABLE' and
            retry['delivery_status_after_recovery'] == 'DELIVERED', 'Webhook status mismatch')
    inbox = retry['inbox_after_recovery']
    require(inbox['runId'] == retry['run_id'] and inbox['contractId'] == 'iems.enrollment' and
            inbox['eventId'] == retry['event_id'] and value['ui']['retry_run_id_visible'] and
            value['newman']['exit_code'] == 0 and value['dcg_port_released'] and
            value['iems_port_released'], 'Webhook correlation/manual retry proof missing')


def check_runtime(directory: Path) -> dict:
    names = ('valid-payload', 'wrong-type', 'missing-required')
    rows = {name: json.loads((directory / f'{name}-result.json').read_text()) for name in names}
    require(rows['valid-payload']['validation'] == 'PASS' and
            rows['valid-payload']['boundaryInvocationCount'] == 1, 'Valid payload did not cross once')
    for name, field in (('wrong-type', 'amount'), ('missing-required', 'studentId')):
        require(rows[name]['validation'] == 'FAIL' and rows[name]['boundaryInvocationCount'] == 0 and
                field in rows[name]['message'], f'{name} was not blocked by official validator')
    hashes = {row['schemaSha256'] for row in rows.values()}
    require(len(hashes) == 1 and not rust_processes(), 'Runtime schema/Rust observation mismatch')
    result = {'result': 'PASS', 'contractId': 'iems.scholarship.applied', 'version': 'v1',
              'schemaSha256': hashes.pop(), 'scenarios': rows, 'brokerDelivery': 'not tested; publisher handoff only'}
    write_json(directory / 'results.json', result)
    return result


def check_migration(value: dict) -> None:
    safe, breaking = value['safe'], value['breaking']
    require(safe['gateVerdict'] == 'PASS' and safe['executorAttempts'] == 1 and
            safe['executorExitCode'] == 0 and safe['optionalColumnPresent'] and
            safe['reviewedSqlSha256'] == safe['offeredSqlSha256'], 'Safe migration proof incomplete')
    require(breaking['gateVerdict'] == 'FAIL' and breaking['executorAttempts'] == 0 and
            breaking['preSchemaSha256'] == breaking['postSchemaSha256'] and
            breaking['preDatabaseSha256'] == breaking['postDatabaseSha256'] and
            breaking['requiredColumnPresent'] and breaking['sentinelPreserved'] and
            value['normalIemsDatabaseUntouched'], 'Breaking migration changed data or reached executor')


def validate_index(report: dict) -> None:
    require(report['ai_enabled'] is False and report['overall_result'] == 'PASS',
            'Phase 1 result must be a deterministic no-AI PASS')
    require(set(report['scenarios']) == set(REQUIRED_SCENARIOS), 'Required scenario missing from index')
    for name in REQUIRED_SCENARIOS:
        row = report['scenarios'][name]
        require(row['result'] == 'PASS' and Path(row['evidence']).is_file(),
                f'{name} lacks passing, retained sub-evidence')
    require(all(report[k] for k in ('source_contracts_unchanged', 'accepted_rc_unchanged',
                                  'development_package_unchanged', 'normal_iems_database_unchanged',
                                  'ports_released', 'task_process_released')) and
            not report['rust_processes_after'] and not report['task_owned_processes_after'],
            'Final preservation/cleanup audit failed')


def run(evidence: Path, package: Path, validated_package: dict | None = None) -> dict:
    original_contracts = inventory(ROOT / 'contracts')
    package_before = inventory(package)
    rc_before = inventory(ACCEPTED_RC)
    normal = ROOT / '.dcg/data/iems.db'
    normal_before = (normal.exists(), sha(normal.read_bytes()) if normal.exists() else None)
    require(not rust_processes(), 'Stop existing Rust process before Phase 1')
    env = dict(os.environ, DCG_HOME=str(package), DCG_AI_ENABLED='false',
               SHADOW_INFERENCE_ENABLED='false')
    require(env.get('JAVA_HOME'), 'Set JAVA_HOME to JDK 21')
    env['PATH'] = str(Path(env['JAVA_HOME']) / 'bin') + ':' + env.get('PATH', '')
    validated_package = validated_package or verify_development_package(package)
    report = {'phase': 'phase1-deterministic', 'ai_enabled': False, 'overall_result': 'INCOMPLETE',
              'package': str(package), 'scenarios': {}, 'commands': [], 'ports': [],
              'validated_package': validated_package,
              'source_contracts_unchanged': False, 'accepted_rc_unchanged': False,
              'development_package_unchanged': False, 'normal_iems_database_unchanged': False,
              'rust_processes_before': rust_processes(), 'rust_processes_after': [], 'ports_released': False}
    used_ports: set[int] = set()
    app = isolated_project(evidence)
    original_project_contracts = inventory(app / 'contracts')
    try:
        report['current_stage'] = 'baseline'
        print('A. Working IEMS baseline and full Postman collection', flush=True)
        baseline = api_run(evidence, app, 'baseline', env, used_ports, report['commands'], newman=True)
        baseline_path = evidence / 'baseline-result.json'; write_json(baseline_path, baseline)
        report['scenarios']['baseline'] = {'result': 'PASS', 'command': 'run_demo.sh sqlite + IEMS Postman collection',
                                           'exit_code': 0, 'evidence': str(baseline_path),
                                           'boundary_proof': 'four CLI PASS rows, HTTP 200, real Newman assertions',
                                           'api': baseline['api'], 'limitation': 'isolated SQLite app data'}
        report['ports'].append(baseline['port'])

        report['current_stage'] = 'compatible_contract'
        print('B. Compatible optional contract proposal and allowed startup', flush=True)
        target = app / 'contracts/iems.enrollment/candidate.json'
        previous = target.read_bytes()
        fixture = ROOT / 'scripts/dcg/fixtures/compatible.json'
        try:
            target.write_bytes(fixture.read_bytes())
            diff_argv = [str(package / 'bin/dcg'), 'diff', '--base',
                         str(app / 'contracts/iems.enrollment/v1.json'), '--candidate', str(target)]
            diff = subprocess.run(diff_argv, cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
            (evidence / 'compatible-diff.log').write_text(diff.stdout + diff.stderr)
            report['commands'].append({'stage': 'compatible-diff', 'argv': diff_argv,
                                       'exit': diff.returncode, 'log': 'compatible-diff.log'})
            require(diff.returncode == 0 and 'sourceSystem' in diff.stdout + diff.stderr,
                    'Compatible diff did not identify sourceSystem')
            compatible = api_run(evidence, app, 'compatible', env, used_ports, report['commands'], newman=False)
            compatible['changedSchemaPath'] = 'sourceSystem'
            compatible['candidateSha256'] = sha(target.read_bytes())
        finally:
            target.write_bytes(previous)
            require(target.read_bytes() == previous, 'Compatible candidate did not reset byte-exactly')
        compatible_path = evidence / 'compatible-result.json'; write_json(compatible_path, compatible)
        report['scenarios']['compatible_contract'] = {'result': 'PASS', 'command': 'dcg diff; run_demo.sh sqlite',
                 'exit_code': 0, 'evidence': str(compatible_path), 'contract_id': 'iems.enrollment',
                 'changed_path': 'sourceSystem', 'boundary_proof': 'four recorded CLI PASSs and IEMS HTTP 200',
                 'limitation': 'compatible optional field in isolated project copy'}
        report['ports'].append(compatible['port'])

        report['current_stage'] = 'multiple_breaking_contracts'
        print('C. Two breaking contracts, blocked launcher, stable CLI explanations', flush=True)
        multiple_dir = evidence / 'multiple-contracts'
        argv = [sys.executable, str(ROOT / 'scripts/dcg/multiple_contract_demo.py'),
                '--evidence', str(multiple_dir), '--retain-history']
        run_child(evidence, 'multiple-contracts', argv, env, report['commands'])
        multiple_path = multiple_dir / 'results.json'; multiple = require_result(multiple_path)
        check_multiple(multiple)
        report['scenarios']['multiple_breaking_contracts'] = {'result': 'PASS', 'command': argv,
            'exit_code': 0, 'evidence': str(multiple_path), 'contract_ids': list(multiple['failure_run_ids']),
            'run_ids': multiple['failure_run_ids'], 'launcher_exit': 1,
            'boundary_proof': 'two independent CLI FAILs, zero IEMS Java dispatches, exact candidate reset',
            'limitation': 'four separate checks, not one atomic transaction'}
        explanation = multiple_dir / 'explain-summary.json'
        require(explanation.is_file() and len(json.loads(explanation.read_text())['failures']) == 2,
                'Retained CLI explanations missing')
        report['scenarios']['cli_explain'] = {'result': 'PASS', 'command': 'dcg explain --db history.sqlite --run <each stable ID>',
            'exit_code': 1, 'evidence': str(explanation), 'run_ids': multiple['failure_run_ids'],
            'boundary_proof': 'both recorded FAIL IDs resolved from retained SQLite history',
            'limitation': 'resolved breaking explain exits 1; output distinguishes it from missing ID'}

        report['current_stage'] = 'maven_gate'
        print('D. Official Maven validate-phase gate in disposable copies', flush=True)
        maven_dir = evidence / 'maven-gate'
        argv = [sys.executable, str(ROOT / 'scripts/dcg/maven_gate_demo.py'), '--evidence', str(maven_dir)]
        run_child(evidence, 'maven-gate', argv, env, report['commands'], timeout=1200)
        maven_path = maven_dir / 'results.json'; maven = require_result(maven_path); check_maven(maven)
        report['scenarios']['maven_gate'] = {'result': 'PASS', 'command': argv, 'exit_code': 0,
            'evidence': str(maven_path), 'plugin_goal': maven['goal'], 'phase': maven['phase'],
            'boundary_proof': 'compatible JAR built; breaking validate fails before any JAR',
            'limitation': 'fail-fast: Maven reports enrollment first, not both failures'}

        report['current_stage'] = 'service_dashboard'
        print('E1. Packaged service, registry, REST, dashboard', flush=True)
        service_dir = evidence / 'service-dashboard'
        argv = [sys.executable, str(ROOT / 'scripts/dcg/service_registry_demo.py'),
                '--dcg-home', str(package), '--evidence', str(service_dir)]
        run_child(evidence, 'service-dashboard', argv, env, report['commands'], timeout=900)
        service_path = service_dir / 'results.json'; service = require_result(service_path); check_service(service)
        report['scenarios']['service_dashboard'] = {'result': 'PASS', 'command': argv, 'exit_code': 0,
            'evidence': str(service_path), 'contract_ids': list(service['contracts']),
            'run_ids': {k: v['run_id'] for k, v in service['runs'].items()},
            'boundary_proof': 'REST IDs/statuses match rendered UI before and after service restart',
            'limitation': 'separate isolated service run from webhook rehearsal'}
        report['ports'].append(service['service_port'])

        report['current_stage'] = 'webhook_delivery'
        print('E2. Real IEMS webhook inbox and persisted manual retry', flush=True)
        webhook_dir = evidence / 'webhook-delivery'
        argv = [sys.executable, str(ROOT / 'scripts/dcg/webhook_delivery_demo.py'),
                '--dcg-home', str(package), '--evidence', str(webhook_dir)]
        run_child(evidence, 'webhook-delivery', argv, env, report['commands'], timeout=900)
        webhook_path = webhook_dir / 'results.json'; webhook = require_result(webhook_path); check_webhook(webhook)
        report['scenarios']['webhook_delivery'] = {'result': 'PASS', 'command': argv, 'exit_code': 0,
            'evidence': str(webhook_path), 'contract_id': 'iems.enrollment',
            'run_ids': {k: v['run_id'] for k, v in webhook['runs'].items()},
            'boundary_proof': 'outbox/inbox run+event IDs match; outage persists; manual retry delivered once',
            'limitation': 'manual retry; webhook service run is distinct from dashboard sub-rehearsal'}
        report['ports'].extend([webhook['dcg_port'], webhook['iems_port']])

        report['current_stage'] = 'runtime_validation'
        print('F. Official starter at real scholarship publisher boundary', flush=True)
        runtime_dir = evidence / 'runtime-validation'; runtime_dir.mkdir(mode=0o700)
        runtime_env = dict(env, IEMS_DCG_RUNTIME_EVIDENCE=str(runtime_dir))
        argv = ['mvn', '-B', '-ntp', '-Dtest=ScholarshipAppliedEventBoundaryTest', 'test']
        run_child(evidence, 'runtime-validation', argv, runtime_env, report['commands'], timeout=300)
        runtime = check_runtime(runtime_dir)
        report['scenarios']['runtime_validation'] = {'result': 'PASS', 'command': argv, 'exit_code': 0,
            'evidence': str(runtime_dir / 'results.json'), 'contract_id': runtime['contractId'],
            'version': runtime['version'], 'boundary_proof': 'valid publisher 1; wrong type 0; missing required 0',
            'limitation': 'broker-disabled profile proves handoff, not Kafka delivery'}

        report['current_stage'] = 'migration_gate'
        print('G. Governed physical SQLite migration gate on IEMS schools', flush=True)
        argv = [sys.executable, str(ROOT / 'scripts/database/iems_migration_gate.py')]
        migration_output = run_child(evidence, 'migration-gate', argv, env, report['commands'], timeout=180)
        lines = [line for line in migration_output.splitlines() if line.startswith('{"result":')]
        require(len(lines) == 1, 'Migration runner did not identify retained evidence')
        migration_path = Path(json.loads(lines[0])['evidence']) / 'results.json'
        migration = require_result(migration_path, 'COMPLETE'); check_migration(migration)
        report['scenarios']['migration_gate'] = {'result': 'PASS', 'command': argv, 'exit_code': 0,
            'evidence': str(migration_path), 'table': 'schools', 'required_column': 'name',
            'boundary_proof': 'safe SQL executor 1; breaking SQL executor 0; schema/DB hashes and sentinel unchanged',
            'limitation': 'governed SQLite runner, not Flyway internal hook or direct-SQL prevention'}

        report['current_stage'] = 'final_recovery'
        print('H. Fresh IEMS recovery and full Postman collection', flush=True)
        require(inventory(app / 'contracts') == original_project_contracts,
                'Disposable project candidates did not restore exactly')
        final = api_run(evidence, app, 'final-recovery', env, used_ports, report['commands'], newman=True)
        final_path = evidence / 'final-recovery-result.json'; write_json(final_path, final)
        report['scenarios']['final_recovery'] = {'result': 'PASS',
            'command': 'run_demo.sh sqlite + IEMS Postman collection', 'exit_code': 0,
            'evidence': str(final_path), 'api': final['api'],
            'boundary_proof': 'fresh DB, four contract PASSs, HTTP 200 and real Newman assertions',
            'limitation': 'new isolated application DB; prior failed proposals are not applied'}
        report['ports'].append(final['port'])
        report['overall_result'] = 'PASS'
    except BaseException as error:
        report['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        report['source_contracts_unchanged'] = inventory(ROOT / 'contracts') == original_contracts
        report['accepted_rc_unchanged'] = inventory(ACCEPTED_RC) == rc_before
        report['development_package_unchanged'] = inventory(package) == package_before
        report['normal_iems_database_unchanged'] = normal_before == (normal.exists(),
                                                  sha(normal.read_bytes()) if normal.exists() else None)
        report['rust_processes_after'] = rust_processes()
        report['ports_released'] = all(port_released(port) for port in report['ports'])
        report['task_process_released'] = not (evidence / 'active-process.json').exists()
        report['task_owned_processes_after'] = task_owned_processes(evidence)
        if report['overall_result'] == 'PASS':
            try:
                validate_index(report)
            except Exception as error:
                report['overall_result'] = 'INCOMPLETE'
                report['audit_error'] = str(error)
        write_json(evidence / 'results.json', report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--dcg-home', type=Path,
                        help='Validated DCG development package; overrides DCG_HOME')
    parser.add_argument('--cleanup', action='store_true', help='Stop a recorded task-owned process after interruption')
    args = parser.parse_args()
    os.umask(0o077)
    if args.cleanup:
        evidence = args.evidence.resolve()
        require((evidence / '.phase1-integrated-marker').is_file(), 'Not an integrated evidence directory')
        require(stop_recorded_process(evidence), 'Owned process/port still active')
        if (evidence / 'results.json').is_file():
            prior = json.loads((evidence / 'results.json').read_text())
            require(all(port_released(port) for port in prior.get('ports', [])),
                    'A recorded task-owned port is still active')
        require(not task_owned_processes(evidence) and not rust_processes(),
                'Task-owned or Rust process still active')
        write_json(evidence / 'manual-cleanup.json', {'result': 'PASS', 'ownedProcessReleased': True})
        print('Task-owned process released; retained evidence unchanged:', evidence)
        return 0
    validated = select_and_validate(args.dcg_home, required_capabilities=PHASE1_CAPABILITIES)
    package = Path(validated['path'])
    verify_development_package(package)
    evidence = prepare_evidence(args.evidence)
    try:
        report = run(evidence, package, validated)
        require(report['overall_result'] == 'PASS', 'Integrated Phase 1 verification incomplete')
        print('PASS:', evidence / 'results.json')
        return 0
    except BaseException as error:
        if not (evidence / 'results.json').exists():
            write_json(evidence / 'results.json', {'phase': 'phase1-deterministic', 'ai_enabled': False,
                                                   'overall_result': 'INCOMPLETE', 'error': str(error)})
        print(f'INCOMPLETE: {type(error).__name__}: {error}; evidence: {evidence}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
