#!/usr/bin/env python3
"""Orchestrate the local Phase 2 DCG/IEMS advisory rehearsal in fresh evidence."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

import phase1_integrated_demo as p1
import phase2_service_demo as service_demo
from dcg_package import PHASE2_CAPABILITIES, select_and_validate, validate_package
from multiple_contract_demo import ROOT, inventory, require, rust_processes, sha

REQUIRED = ('baseline', 'real_compatible', 'real_breaking', 'startup_gate', 'maven_gate',
            'multiple_breaking', 'service_dashboard_webhook', 'unavailable', 'faults',
            'test_only_disagreement', 'runtime_validation', 'migration_gate', 'final_recovery')


def prepare(evidence: Path) -> Path:
    root = p1.REHEARSALS.resolve()
    require(evidence.absolute().parent.resolve() == root and evidence.name.startswith('phase2-integrated-'),
            'Evidence must be a new phase2-integrated-* directory under .dcg/rehearsals')
    evidence.mkdir(mode=0o700, exist_ok=False)
    (evidence / '.phase2-integrated-marker').write_text('Phase 2 integrated rehearsal\n')
    return evidence.resolve()


def verify_selected_package(package: Path) -> dict:
    validated = validate_package(package, required_capabilities=PHASE2_CAPABILITIES)
    require((ROOT / 'target' / p1.JAR).is_file(), 'Build IEMS JAR before rehearsal')
    require((ROOT / '.dcg/tools/node_modules/newman').is_dir(), 'Install local Newman before rehearsal')
    return validated


def scenario(report: dict, name: str, evidence: Path, command: object, *, deterministic: object,
             advisory: object = None, proof: str, limitation: str = '', **extra) -> None:
    require(evidence.is_file(), f'Missing required sub-evidence: {evidence}')
    report['scenarios'][name] = {'result': 'PASS', 'command': command, 'exit_code': 0,
        'deterministic_result': deterministic, 'advisory_status': advisory, 'evidence': str(evidence),
        'boundary_proof': proof, 'limitation': limitation, **extra}


def validate_index(report: dict) -> None:
    require(report['overall_result'] == 'PASS' and set(report['scenarios']) == set(REQUIRED),
            'Required scenario missing or overall incomplete')
    for name in REQUIRED:
        row = report['scenarios'][name]
        require(row['result'] == 'PASS' and Path(row['evidence']).is_file() and row['boundary_proof'],
                f'{name}: missing result, retained evidence, or boundary proof')
    require(all(report['preservation'].values()), 'Source/package/database preservation failed')
    require(report['cleanup']['ports_released'] and report['cleanup']['processes_released'] and
            not report['cleanup']['rust_processes_after'], 'Task cleanup incomplete')


def ai_startup_gate(evidence: Path, app: Path, env: dict, commands: list[dict]) -> dict:
    candidate = app / 'contracts/iems.enrollment/candidate.json'
    previous = candidate.read_bytes()
    marker = evidence / 'ai-startup-java-dispatches'
    tools_dir = evidence / 'startup-tools'; tools_dir.mkdir(mode=0o700)
    shim = tools_dir / 'java'
    shim.write_text('#!/bin/bash\ncase "$*" in *inclusive-education-management-system*) '
                    'printf "dispatched\\n" >> "$IEMS_DISPATCH_MARKER";; esac\n'
                    'exec "$IEMS_REAL_JAVA" "$@"\n')
    shim.chmod(0o700)
    history = evidence / 'ai-startup-history.sqlite'
    app_env = dict(env, DCG_AI_ENABLED='true', GIT_DIR=str(ROOT / '.git'),
                   IEMS_JDBC_URL='jdbc:sqlite:' + str(evidence / 'ai-startup-iems.sqlite'),
                   DCG_SQLITE_PATH=str(history), IEMS_JWT_SECRET=secrets.token_hex(40),
                   IEMS_DEMO_ADMIN_PASSWORD=secrets.token_hex(24),
                   IEMS_DISPATCH_MARKER=str(marker), IEMS_REAL_JAVA=str(Path(env['JAVA_HOME']) / 'bin/java'),
                   PATH=str(tools_dir) + ':' + env['PATH'])
    argv = [str(app / 'scripts/database/run_demo.sh'), 'sqlite']
    try:
        candidate.write_bytes((ROOT / 'scripts/dcg/fixtures/breaking.json').read_bytes())
        done = subprocess.run(argv, cwd=app, env=app_env, capture_output=True, text=True, timeout=60)
        (evidence / 'ai-startup-gate.log').write_text(done.stdout + done.stderr)
        commands.append({'stage': 'ai-startup-gate', 'argv': argv, 'exit': done.returncode,
                         'log': 'ai-startup-gate.log', 'ai_requested': True})
        rows = p1.check_rows(history)
        dispatch = len(marker.read_text().splitlines()) if marker.exists() else 0
        require(done.returncode == 1 and ['iems.enrollment', 'FAIL'] in rows and dispatch == 0,
                'AI-enabled startup gate did not block breaking proposal before Java dispatch')
        result = {'result': 'PASS', 'exit': done.returncode, 'rows': rows, 'javaDispatchCount': dispatch,
                  'aiRequested': True}
        p1.write_json(evidence / 'ai-startup-gate.json', result)
        return result
    finally:
        candidate.write_bytes(previous)
        require(candidate.read_bytes() == previous, 'Startup fixture reset failed')


def run(evidence: Path, package: Path, validated_package: dict | None = None) -> dict:
    source = inventory(ROOT / 'contracts')
    normal = ROOT / '.dcg/data/iems.db'
    normal_hash = (normal.exists(), sha(normal.read_bytes()) if normal.exists() else None)
    rc_hash = inventory(p1.ACCEPTED_RC)
    package_hash = inventory(package)
    require(not rust_processes(), 'A Rust model is already active; leave unrelated processes untouched')
    base_env = dict(os.environ, DCG_HOME=str(package), DCG_AI_ENABLED='false', SHADOW_INFERENCE_ENABLED='false')
    require(base_env.get('JAVA_HOME'), 'Set JAVA_HOME to JDK 21')
    base_env['PATH'] = str(Path(base_env['JAVA_HOME']) / 'bin') + ':' + base_env.get('PATH', '')
    validated_package = validated_package or verify_selected_package(package)
    report = {'phase': 'phase2-ai-advisory', 'overall_result': 'INCOMPLETE', 'ai_modes': [],
              'scenarios': {}, 'development_package': validated_package,
              'model_provenance': {}, 'preservation': {}, 'cleanup': {}, 'commands': [], 'ports': []}
    used_ports: set[int] = set()
    app = p1.isolated_project(evidence)
    app_before = inventory(app / 'contracts')
    try:
        report['current_stage'] = 'baseline'
        print('A. No-AI IEMS baseline + Postman', flush=True)
        baseline = p1.api_run(evidence, app, 'baseline', base_env, used_ports, report['commands'], newman=True)
        p1.write_json(evidence / 'baseline.json', baseline)
        require(not rust_processes(), 'Rust started in no-AI baseline')
        scenario(report, 'baseline', evidence / 'baseline.json', 'run_demo.sh sqlite + Newman',
                 deterministic='PASS x4', advisory='DISABLED/absent',
                 proof='HTTP 200, four PASS history rows, zero Rust processes, Newman assertions',
                 limitation='Disposable SQLite application database', api=baseline['api'])
        report['ports'].append(baseline['port']); report['ai_modes'].append('disabled')

        report['current_stage'] = 'real_cli'
        print('B/C. Real Rust model CLI advice', flush=True)
        cli_path = evidence / 'real-cli.json'
        argv = [sys.executable, str(ROOT / 'scripts/dcg/advisory_rehearsal.py'), '--scenario', 'all',
                '--output', str(cli_path)]
        p1.run_child(evidence, 'real-cli', argv, dict(base_env, DCG_AI_ENABLED='true'), report['commands'])
        cli = json.loads(cli_path.read_text())
        for name, expected in (('compatible', 'PASS'), ('breaking', 'FAIL')):
            item = cli[name]['contracts'][0]
            advice = item['advisory']
            require(cli[name]['finalEnforcementResult'] == expected and item['deterministicVerdict'] == expected and
                    advice['advisoryStatus'] == 'AVAILABLE' and len(advice['predictions']) == 3,
                    f'Real {name} CLI result incomplete')
            scenario(report, 'real_' + name, cli_path, argv, deterministic=expected,
                     advisory='AVAILABLE', proof='Actual packaged CLI verdict precedes real Rust inference',
                     run_id=None, contract_id=item['contractId'], label=[x['label'] for x in advice['predictions']],
                     probabilities=[x['probabilities'] for x in advice['predictions']],
                     agreement=advice['agreement'], input_hash=advice['inputHash'],
                     model_artifacts=advice['modelArtifactSha256'])
        report['model_provenance'] = {'version': cli['compatible']['contracts'][0]['advisory']['modelVersion'],
            'artifact_sha256': cli['compatible']['contracts'][0]['advisory']['modelArtifactSha256'],
            'feature_schema_version': cli['compatible']['contracts'][0]['advisory']['featureSchemaVersion']}
        report['ai_modes'].append('available')

        report['current_stage'] = 'startup_gate'
        print('C. AI-requested IEMS startup remains blocked by deterministic FAIL', flush=True)
        startup = ai_startup_gate(evidence, app, base_env, report['commands'])
        scenario(report, 'startup_gate', evidence / 'ai-startup-gate.json', 'run_demo.sh sqlite',
                 deterministic='FAIL', advisory='optional', proof='launcher exit 1 and Java dispatch count 0',
                 launcher_exit=startup['exit'], java_dispatch_count=startup['javaDispatchCount'])

        # A compatible proposal still starts IEMS when the advisory process is absent.
        candidate = app / 'contracts/iems.enrollment/candidate.json'
        previous = candidate.read_bytes()
        try:
            candidate.write_bytes((ROOT / 'scripts/dcg/fixtures/compatible.json').read_bytes())
            ai_compatible = p1.api_run(evidence, app, 'ai-compatible-no-model',
                                       dict(base_env, DCG_AI_ENABLED='true'),
                                       used_ports, report['commands'], newman=False)
            p1.write_json(evidence / 'ai-compatible-no-model.json', ai_compatible)
            report['ports'].append(ai_compatible['port'])
        finally:
            candidate.write_bytes(previous)
            require(candidate.read_bytes() == previous, 'Compatible AI fixture reset failed')

        report['current_stage'] = 'multiple_breaking'
        print('D. Two breaking contracts + stable explain IDs', flush=True)
        multiple_dir = evidence / 'multiple-contracts'
        argv = [sys.executable, str(ROOT / 'scripts/dcg/multiple_contract_demo.py'),
                '--evidence', str(multiple_dir), '--retain-history']
        p1.run_child(evidence, 'multiple-contracts', argv, base_env, report['commands'], timeout=900)
        multiple = p1.require_result(multiple_dir / 'results.json'); p1.check_multiple(multiple)
        scenario(report, 'multiple_breaking', multiple_dir / 'results.json', argv,
                 deterministic='FAIL x2', advisory='disabled',
                 proof='two failures, launcher exit 1, zero Java dispatch, stable explain run IDs',
                 run_ids=multiple['failure_run_ids'], limitation='Maven separately remains fail-fast')

        report['current_stage'] = 'maven_gate'
        print('C. Maven validate gate with AI requested', flush=True)
        maven_dir = evidence / 'maven-gate'
        argv = [sys.executable, str(ROOT / 'scripts/dcg/maven_gate_demo.py'),
                '--evidence', str(maven_dir), '--ai-requested']
        p1.run_child(evidence, 'maven-gate', argv, dict(base_env, DCG_AI_ENABLED='true'),
                     report['commands'], timeout=1800)
        maven = p1.require_result(maven_dir / 'results.json'); p1.check_maven(maven)
        require(maven['ai_enabled'], 'Maven AI-request mode was not applied')
        scenario(report, 'maven_gate', maven_dir / 'results.json', argv,
                 deterministic='PASS compatible; FAIL breaking', advisory='not in Maven decision path',
                 proof='breaking exits at validate and creates no JAR with DCG_AI_ENABLED=true',
                 limitation='Official plugin JSON reports; first failing contract only')

        report['current_stage'] = 'service'
        print('E-H. Fresh service, dashboard, webhook, unavailable and test-only faults', flush=True)
        service_dir = evidence / 'service'
        argv = [sys.executable, str(ROOT / 'scripts/dcg/phase2_service_demo.py'),
                '--dcg-home', str(package), '--evidence', str(service_dir)]
        p1.run_child(evidence, 'service', argv, dict(base_env, DCG_AI_ENABLED='true'),
                     report['commands'], timeout=900)
        service = p1.require_result(service_dir / 'results.json')
        require(service['portsReleased'] and service['processesStopped'], 'Service cleanup failed')
        report['ports'].extend(service['ports'])
        for name, key, status, advice in (
            ('service_dashboard_webhook', 'real-breaking', 'FAIL', 'AVAILABLE'),
            ('unavailable', 'unavailable-breaking', 'FAIL', 'UNAVAILABLE'),
            ('faults', 'timeout', 'FAIL', 'TIMEOUT'),
            ('test_only_disagreement', 'test-only-disagreement', 'FAIL', 'AVAILABLE')):
            item = service['runs'][key]
            require(item['run']['status'] == status and item['advisory']['status'] == advice,
                    f'{name} service status mismatch')
            scenario(report, name, service_dir / (key + '.json'), argv,
                     deterministic=status, advisory=advice,
                     proof='service REST/log/UI and deterministic webhook correlation' if name == 'service_dashboard_webhook'
                           else 'deterministic FAIL unchanged by optional advisory',
                     run_id=item['run']['runId'], label=item['advisory']['predictionLabel'],
                     probabilities=item['advisory']['probabilities'], agreement=item['advisory']['agreement'],
                     test_only=item['advisory']['testOnlyAdapter'])
        require(service['runs']['unavailable-compatible']['run']['status'] == 'PASS' and
                service['runs']['unavailable-compatible']['advisory']['status'] == 'UNAVAILABLE' and
                service['runs']['invalid-output']['advisory']['status'] == 'INVALID_OUTPUT' and
                service['runs']['invalid-output-compatible']['run']['status'] == 'PASS' and
                service['runs']['timeout-compatible']['run']['status'] == 'PASS' and
                all(v['advisoryVisible'] and v['decisionVisible'] for v in service['dashboard'].values()),
                'Unavailable/fault PASS or dashboard proof missing')
        report['scenarios']['unavailable']['compatible_run_id'] = service['runs']['unavailable-compatible']['run']['runId']
        report['scenarios']['unavailable']['iems_health_http'] = ai_compatible['healthHttp']
        report['scenarios']['unavailable']['iems_evidence'] = str(evidence / 'ai-compatible-no-model.json')
        report['scenarios']['faults']['invalid_output_run_id'] = service['runs']['invalid-output']['run']['runId']
        report['scenarios']['faults']['timeout_compatible_run_id'] = service['runs']['timeout-compatible']['run']['runId']
        report['scenarios']['faults']['invalid_output_compatible_run_id'] = service['runs']['invalid-output-compatible']['run']['runId']
        report['ai_modes'] += ['unavailable', 'timeout', 'invalid_output', 'test_only_disagreement']

        report['current_stage'] = 'runtime_validation'
        print('I. Runtime payload validator regression', flush=True)
        runtime_dir = evidence / 'runtime-validation'; runtime_dir.mkdir(mode=0o700)
        argv = ['mvn', '-B', '-ntp', '-Dtest=ScholarshipAppliedEventBoundaryTest', 'test']
        p1.run_child(evidence, 'runtime-validation', argv,
                     dict(base_env, IEMS_DCG_RUNTIME_EVIDENCE=str(runtime_dir)), report['commands'], timeout=300)
        runtime = p1.check_runtime(runtime_dir)
        scenario(report, 'runtime_validation', runtime_dir / 'results.json', argv,
                 deterministic='valid PASS; wrong type/missing required FAIL', advisory='not authoritative',
                 proof='publisher handoffs 1/0/0', limitation='Kafka broker delivery not proven')

        report['current_stage'] = 'migration_gate'
        print('J. Governed SQLite migration gate regression', flush=True)
        argv = [sys.executable, str(ROOT / 'scripts/database/iems_migration_gate.py')]
        output = p1.run_child(evidence, 'migration-gate', argv, base_env, report['commands'], timeout=240)
        marker = [line for line in output.splitlines() if line.startswith('{"result":')]
        require(len(marker) == 1, 'Migration runner did not identify evidence')
        migration_path = Path(json.loads(marker[0])['evidence']) / 'results.json'
        migration = p1.require_result(migration_path, 'COMPLETE'); p1.check_migration(migration)
        scenario(report, 'migration_gate', migration_path, argv,
                 deterministic='safe PASS; breaking FAIL', advisory='not authoritative',
                 proof='executor calls 1/0; failed DDL preserves DB/schema hashes and sentinel',
                 limitation='governed SQLite runner only; direct SQL is outside gate')

        report['current_stage'] = 'final_recovery'
        print('K. Final fresh IEMS recovery + Postman', flush=True)
        require(inventory(app / 'contracts') == app_before, 'Disposable contract candidates did not reset')
        final = p1.api_run(evidence, app, 'final-recovery', base_env, used_ports, report['commands'], newman=True)
        p1.write_json(evidence / 'final-recovery.json', final)
        scenario(report, 'final_recovery', evidence / 'final-recovery.json', 'run_demo.sh sqlite + Newman',
                 deterministic='PASS x4', advisory='DISABLED/absent',
                 proof='fresh IEMS health 200 and Newman assertions after fault scenarios', api=final['api'])
        report['ports'].extend([final['port']])
        report['overall_result'] = 'PASS'
    except BaseException as error:
        report['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        report['preservation'] = {
            'source_contracts_unchanged': inventory(ROOT / 'contracts') == source,
            'normal_iems_database_unchanged': normal_hash == (normal.exists(), sha(normal.read_bytes()) if normal.exists() else None),
            'accepted_rc_unchanged': inventory(p1.ACCEPTED_RC) == rc_hash,
            'selected_package_unchanged': inventory(package) == package_hash,
            'disposable_candidates_restored': inventory(app / 'contracts') == app_before}
        report['cleanup'] = {'ports_released': all(p1.port_released(port) for port in report['ports']),
            'processes_released': not p1.task_owned_processes(evidence) and
                                  not (evidence / 'active-process.json').exists(),
            'rust_processes_after': rust_processes()}
        shutil.rmtree(app, ignore_errors=True)
        report['cleanup']['disposable_project_removed'] = not app.exists()
        if report['overall_result'] == 'PASS':
            try: validate_index(report)
            except Exception as error:
                report['overall_result'] = 'INCOMPLETE'; report['audit_error'] = str(error)
        p1.write_json(evidence / 'results.json', report)
    return report


def cleanup(evidence: Path) -> None:
    evidence = evidence.resolve()
    require((evidence / '.phase2-integrated-marker').is_file(),
            'Not a Phase 2 integrated evidence directory')
    require(p1.stop_recorded_process(evidence), 'Recorded process did not stop')
    require(service_demo.cleanup_owned(evidence / 'service'), 'Service child cleanup failed')
    prior = json.loads((evidence / 'results.json').read_text()) if (evidence / 'results.json').exists() else {}
    require(all(p1.port_released(p) for p in prior.get('ports', [])), 'A task port remains bound')
    p1.write_json(evidence / 'manual-cleanup.json', {'result': 'PASS', 'portsReleased': True})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--dcg-home', type=Path,
                        help='Validated DCG development package; overrides DCG_HOME')
    parser.add_argument('--cleanup', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    if args.cleanup:
        cleanup(args.evidence)
        return 0
    validated = select_and_validate(args.dcg_home, required_capabilities=PHASE2_CAPABILITIES)
    package = Path(validated['path'])
    verify_selected_package(package)
    evidence = prepare(args.evidence)
    try:
        report = run(evidence, package, validated)
        validate_index(report)
        print('PASS:', evidence / 'results.json')
        return 0
    except BaseException as error:
        if not (evidence / 'results.json').exists():
            p1.write_json(evidence / 'results.json', {'phase': 'phase2-ai-advisory',
                'overall_result': 'INCOMPLETE', 'error': f'{type(error).__name__}: {error}'})
        print(f'INCOMPLETE: {type(error).__name__}: {error}; evidence: {evidence}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
