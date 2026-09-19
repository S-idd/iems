#!/usr/bin/env python3
"""Fresh, isolated Phase 2 service checks with real and simulated advisory modes."""
from __future__ import annotations

import argparse
import http.server
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.request

from bs4 import BeautifulSoup
from dcg_package import PHASE2_SERVICE_CAPABILITIES, select_and_validate, validate_package
from phase1_integrated_demo import available_port, port_released, process_active, process_identity, write_json
from multiple_contract_demo import ROOT, require, stop_child


def cleanup_owned(evidence: Path) -> bool:
    """Stop only recorded child process groups whose identity still matches."""
    marker = evidence / 'active-processes.json'
    if not marker.exists():
        return True
    records = json.loads(marker.read_text())
    for record in reversed(records):
        pid = record['pid']
        if process_identity(pid) != record['startedAt']:
            continue
        command = subprocess.run(['ps', '-p', str(pid), '-o', 'command='],
                                 capture_output=True, text=True).stdout
        require(record['identity'] in command, 'Owned process identity changed; refusing to signal')
        os.killpg(pid, signal.SIGTERM)
        deadline = time.monotonic() + 30
        while process_active(pid) and time.monotonic() < deadline:
            time.sleep(.2)
        require(not process_active(pid), 'Recorded service child did not stop')
    marker.unlink()
    return True


def validate_advisory(run: dict, advisory: dict, expected: str, *, test_only: bool = False) -> None:
    require(run['status'] in ('PASS', 'FAIL') and advisory['runId'] == run['runId'], 'Run/advisory mismatch')
    require(advisory['advisoryOnly'] and advisory['status'] == expected, 'Incorrect advisory status')
    require(advisory['testOnlyAdapter'] is test_only, 'Test-only provenance mismatch')
    if expected == 'AVAILABLE':
        require(advisory['predictionLabel'] in ('SAFE', 'WARNING', 'BREAKING') and
                len(advisory['seedPredictions']) == 3 and advisory['probabilities'], 'Missing real prediction')
        expected_agreement = 'AGREES' if advisory['predictionLabel'] == ('SAFE' if run['status'] == 'PASS' else 'BREAKING') else 'DISAGREES'
        require(advisory['agreement'] == expected_agreement, 'Agreement does not match decision/label')
    else:
        require(advisory['predictionLabel'] is None and advisory['probabilities'] is None and
                advisory['agreement'] == 'NOT_AVAILABLE', 'Fabricated unavailable/fault prediction')


def api(base: str, method: str, route: str, body: dict | None = None) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(base + route, data=data, method=method,
                                     headers={'Accept': 'application/json', 'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=5) as response:
            raw, code = response.read(), response.status
    except urllib.error.HTTPError as error:
        raw, code = error.read(), error.code
    if route.startswith('/ui'):
        return code, raw.decode()
    return code, json.loads(raw) if raw else None


def await_health(base: str, process: subprocess.Popen, timeout: float = 100) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        require(process.poll() is None, 'Service exited before health; see stage log')
        try:
            if api(base, 'GET', '/actuator/health')[0] == 200:
                return
        except OSError:
            pass
        time.sleep(.25)
    raise RuntimeError('Service health timeout')


def check(base: str, version: str, name: str, hooks: list[dict], webhook: bool) -> dict:
    before = len(hooks)
    code, accepted = api(base, 'POST', '/checks', {'contractId': 'iems.enrollment', 'baseVersion': 'v1',
             'candidateVersion': version, 'mode': 'BACKWARD', 'commitSha': name,
             'triggeredBy': 'phase2-integrated'})
    require(code == 202 and accepted['runId'], 'Check not queued')
    run_id = accepted['runId']
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        _, run = api(base, 'GET', '/checks/' + run_id)
        status, advisory = api(base, 'GET', '/checks/' + run_id + '/advisory')
        if run['status'] in ('PASS', 'FAIL') and status == 200 and (not webhook or run['status'] == 'PASS' or
                                                                      any(h.get('runId') == run_id for h in hooks[before:])):
            _, logs = api(base, 'GET', '/checks/' + run_id + '/logs')
            hook = [h for h in hooks[before:] if h.get('runId') == run_id]
            require(all(item['runId'] == run_id for item in logs), 'Mismatched check logs')
            if webhook and run['status'] == 'FAIL':
                require(len(hook) == 1 and hook[0]['eventType'] == 'CONTRACT_CHECK_FAILED', 'Deterministic webhook missing')
                require('advisory' not in json.dumps(hook[0]).lower(), 'Webhook treats advisory as authority')
            return {'run': run, 'advisory': advisory, 'logs': logs, 'webhook': hook}
        time.sleep(.2)
    raise RuntimeError('Run/advisory/webhook timeout: ' + run_id)


def dashboard(base: str, item: dict) -> dict:
    run, advisory = item['run'], item['advisory']
    code, html = api(base, 'GET', '/ui/checks/' + run['runId'])
    visible = BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)
    require(code == 200 and run['runId'] in visible and run['status'] in visible and
            advisory['status'] in visible and advisory['agreement'] in visible,
            'Rendered dashboard missing correlated decision/advisory')
    if advisory['predictionLabel']:
        require(advisory['predictionLabel'] in visible, 'Dashboard missing actual advisory label')
    if advisory['testOnlyAdapter']:
        require('test' in visible.lower(), 'Dashboard does not identify test-only advisory')
    return {'http': code, 'runIdVisible': True, 'decisionVisible': True,
            'advisoryVisible': True, 'agreementVisible': True, 'testOnlyMarked': advisory['testOnlyAdapter']}


class Receiver(http.server.BaseHTTPRequestHandler):
    events: list[dict] = []
    mode = 'TIMEOUT'

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        if self.path == '/hook':
            self.events.append(json.loads(raw))
            self.send_response(200); self.end_headers()
            return
        if self.mode == 'TIMEOUT':
            time.sleep(1.1)
        if self.mode == 'INVALID_OUTPUT':
            payload = {'predictions': []}
        else:
            payload = {'predictions': [{'seed': seed, 'label': 'SAFE',
                       'probabilities': {'safe': 1.0, 'warning': 0.0, 'breaking': 0.0}}
                       for seed in ('20260826', '20260827', '20260828')]}
        try:
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
            self.wfile.write(json.dumps(payload).encode())
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *_):
        pass


def run(evidence: Path, package: Path, validated_package: dict | None = None) -> dict:
    validated_package = validated_package or validate_package(
        package, required_capabilities=PHASE2_SERVICE_CAPABILITIES)
    require(os.environ.get('JAVA_HOME'), 'Set JAVA_HOME to Java 21')
    evidence.mkdir(mode=0o700, exist_ok=False)
    (evidence / '.phase2-service-marker').write_text('Phase 2 service rehearsal\n')
    runtime = evidence / 'runtime'; runtime.mkdir(mode=0o700)
    contracts = runtime / 'contracts/iems.enrollment'; contracts.mkdir(parents=True, mode=0o700)
    for source, destination in (
        (ROOT / 'contracts/iems.enrollment/metadata.yaml', contracts / 'metadata.yaml'),
        (ROOT / 'contracts/iems.enrollment/v1.json', contracts / 'v1.json'),
        (ROOT / 'scripts/dcg/fixtures/compatible.json', contracts / 'v2.json'),
        (ROOT / 'scripts/dcg/fixtures/breaking.json', contracts / 'v3.json'),
        (package / 'contracts/policy-packs.json', runtime / 'contracts/policy-packs.json')):
        shutil.copyfile(source, destination)
    used: set[int] = set()
    service_port, model_port, fault_port, hook_port, dead_port = [available_port(used) for _ in range(5)]
    base = f'http://127.0.0.1:{service_port}'
    receiver = http.server.ThreadingHTTPServer(('127.0.0.1', hook_port), Receiver)
    fault = http.server.ThreadingHTTPServer(('127.0.0.1', fault_port), Receiver)
    threads = [threading.Thread(target=server.serve_forever, daemon=True) for server in (receiver, fault)]
    for thread in threads: thread.start()
    report = {'result': 'INCOMPLETE', 'commands': [], 'ports': sorted(used), 'runs': {}, 'dashboard': {},
              'validated_package': validated_package}
    service_jar = package / validated_package['artifacts']['service']['path']
    owned: list[subprocess.Popen] = []
    def start(name: str, argv: list[str], env: dict | None = None) -> subprocess.Popen:
        log = evidence / (name + '.log')
        with log.open('w') as output:
            process = subprocess.Popen(argv, cwd=runtime, env=env, stdout=output, stderr=output, start_new_session=True)
        owned.append(process)
        report['commands'].append({'stage': name, 'argv': argv, 'pid': process.pid, 'log': log.name})
        write_json(evidence / 'active-processes.json', [
            {'pid': p.pid, 'startedAt': process_identity(p.pid),
             'identity': str(package / ('bin/dcgaimodel' if 'dcgaimodel' in str(p.args) else
                                        validated_package['artifacts']['service']['path']))}
            for p in owned if p.poll() is None])
        return process
    def stop(process: subprocess.Popen) -> None:
        if process.poll() is None:
            forced = stop_child(process)
            require(not forced, 'Owned process required forced shutdown')
        require(process.poll() is not None, 'Owned process still alive')
        write_json(evidence / 'active-processes.json', [
            {'pid': p.pid, 'startedAt': process_identity(p.pid),
             'identity': str(package / ('bin/dcgaimodel' if 'dcgaimodel' in str(p.args) else
                                        validated_package['artifacts']['service']['path']))}
            for p in owned if p.poll() is None])
    def service(name: str, endpoint: str, *, test_only: bool = False) -> subprocess.Popen:
        args = [str(Path(os.environ['JAVA_HOME']) / 'bin/java'), '-jar', str(service_jar),
                '--spring.profiles.active=' + ('phase2-rehearsal' if test_only else 'local-demo'),
                '--server.address=127.0.0.1', f'--server.port={service_port}',
                '--contracts.root=' + str(runtime / 'contracts'),
                '--contracts.policy-packs=' + str(runtime / 'contracts/policy-packs.json'),
                '--checks.db.path=' + str(runtime / 'history.db'), '--checks.db.fail-fast-startup=true',
                '--app.security.enabled=false', '--checks.runner.poll-interval=100ms',
                '--shadow.inference.enabled=true', '--shadow.inference.endpoint=' + endpoint,
                '--shadow.inference.timeout=500ms',
                '--shadow.inference.test-only-adapter=' + str(test_only).lower(),
                '--notifications.enabled=true', '--notifications.sinks=webhook',
                '--notifications.webhook.enabled=true',
                f'--notifications.webhook.url=http://127.0.0.1:{hook_port}/hook',
                '--notifications.dispatch.poll-interval-ms=100']
        process = start(name, args)
        await_health(base, process)
        return process
    try:
        model = start('rust-real', [str(package / 'bin/dcgaimodel'), 'serve-shadow-inference',
                      '--artifact-root', str(package / 'model'), '--bind', f'127.0.0.1:{model_port}'])
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                if api(f'http://127.0.0.1:{model_port}', 'GET', '/health/ready')[0] == 200: break
            except OSError: time.sleep(.05)
        else: raise RuntimeError('Real Rust model readiness timeout')
        live = service('java-real', f'http://127.0.0.1:{model_port}/v1/shadow/predict')
        for name, version, status in (('real-compatible', 'v2', 'PASS'), ('real-breaking', 'v3', 'FAIL')):
            item = check(base, version, name, Receiver.events, True)
            validate_advisory(item['run'], item['advisory'], 'AVAILABLE')
            require(item['run']['status'] == status, 'Real-model deterministic verdict changed')
            if status == 'FAIL':
                require(any('studentId' in text and 'integer -> string' in text for text in item['run']['breakingChanges']), 'Wrong breaking reason')
            report['dashboard'][name] = dashboard(base, item)
            report['runs'][name] = item
            write_json(evidence / (name + '.json'), item)
        stop(live)
        stop(model)
        restarted = service('java-real-restart', f'http://127.0.0.1:{dead_port}/v1/shadow/predict')
        persisted = {}
        for name in ('real-compatible', 'real-breaking'):
            original = report['runs'][name]
            run_id = original['run']['runId']
            run_status, run_after = api(base, 'GET', '/checks/' + run_id)
            advisory_status, advisory_after = api(base, 'GET', '/checks/' + run_id + '/advisory')
            logs_status, logs_after = api(base, 'GET', '/checks/' + run_id + '/logs')
            require(run_status == advisory_status == logs_status == 200,
                    'Persisted run, advisory, or logs unavailable after restart')
            require(run_after == original['run'] and advisory_after == original['advisory']
                    and logs_after == original['logs'],
                    'Run, advisory, or logs changed across service restart')
            persisted[name] = {'runId': run_id, 'run': True, 'advisory': True, 'logs': True,
                               'dashboard': dashboard(base, original)}
        report['persistenceAfterRestart'] = persisted
        write_json(evidence / 'persistence-after-restart.json', persisted)
        stop(restarted)
        unavailable = service('java-unavailable', f'http://127.0.0.1:{dead_port}/v1/shadow/predict')
        for name, version, status in (('unavailable-compatible', 'v2', 'PASS'), ('unavailable-breaking', 'v3', 'FAIL')):
            item = check(base, version, name, Receiver.events, True)
            validate_advisory(item['run'], item['advisory'], 'UNAVAILABLE')
            require(item['run']['status'] == status, 'Unavailable model changed verdict')
            report['dashboard'][name] = dashboard(base, item)
            report['runs'][name] = item; write_json(evidence / (name + '.json'), item)
        stop(unavailable)
        test = service('java-test-only-faults', f'http://127.0.0.1:{fault_port}/v1/shadow/predict', test_only=True)
        for name, mode, expected, version, status in (
            ('timeout-compatible', 'TIMEOUT', 'TIMEOUT', 'v2', 'PASS'),
            ('timeout', 'TIMEOUT', 'TIMEOUT', 'v3', 'FAIL'),
            ('invalid-output-compatible', 'INVALID_OUTPUT', 'INVALID_OUTPUT', 'v2', 'PASS'),
            ('invalid-output', 'INVALID_OUTPUT', 'INVALID_OUTPUT', 'v3', 'FAIL'),
            ('test-only-disagreement', 'DISAGREEMENT', 'AVAILABLE', 'v3', 'FAIL')):
            Receiver.mode = mode
            item = check(base, version, name, Receiver.events, True)
            validate_advisory(item['run'], item['advisory'], expected, test_only=True)
            require(item['run']['status'] == status, 'Test-only fault changed deterministic verdict')
            require(item['advisory']['inferenceDurationMs'] <= 2000, 'Advisory exceeded configured bound')
            if name == 'test-only-disagreement':
                require(item['advisory']['predictionLabel'] == 'SAFE' and item['advisory']['agreement'] == 'DISAGREES',
                        'Test-only disagreement missing')
            report['dashboard'][name] = dashboard(base, item)
            report['runs'][name] = item; write_json(evidence / (name + '.json'), item)
        stop(test)
        # The synthetic adapter must fail startup under the normal local-demo profile.
        normal_args = [str(Path(os.environ['JAVA_HOME']) / 'bin/java'), '-jar',
                       str(service_jar),
                       '--spring.profiles.active=local-demo', '--server.address=127.0.0.1',
                       f'--server.port={service_port}', '--app.security.enabled=false',
                       '--shadow.inference.enabled=true', '--shadow.inference.test-only-adapter=true',
                       '--checks.db.path=' + str(runtime / 'normal-adapter-rejection.db')]
        rejected = start('normal-adapter-rejection', normal_args)
        try:
            code = rejected.wait(timeout=45)
        except subprocess.TimeoutExpired:
            stop(rejected)
            raise RuntimeError('Normal runtime unexpectedly accepted test-only adapter')
        log = (evidence / 'normal-adapter-rejection.log').read_text()
        require(code != 0 and 'Test-only advisory adapter requires the phase2-rehearsal profile' in log,
                'Normal runtime did not reject test-only adapter')
        report['normalRuntimeAdapterRejected'] = {'exit': code, 'reasonVisible': True,
                                                   'portReleased': port_released(service_port)}
        require(report['normalRuntimeAdapterRejected']['portReleased'], 'Rejected normal service retained port')
        report['result'] = 'PASS'
    finally:
        for process in reversed(owned):
            if process.poll() is None:
                try: stop(process)
                except Exception as error: report.setdefault('cleanupErrors', []).append(str(error))
        for server in (receiver, fault): server.shutdown(); server.server_close()
        for thread in threads: thread.join(timeout=5)
        report['portsReleased'] = all(port_released(port) for port in used)
        report['processesStopped'] = all(p.poll() is not None for p in owned)
        (evidence / 'active-processes.json').unlink(missing_ok=True)
        shutil.rmtree(runtime / 'contracts', ignore_errors=True)
        report['copiedSchemasRemoved'] = not (runtime / 'contracts').exists()
        if not (report['portsReleased'] and report['processesStopped'] and report['copiedSchemasRemoved']):
            report['result'] = 'INCOMPLETE'
        write_json(evidence / 'results.json', report)
    require(report['result'] == 'PASS', 'Service integration/cleanup incomplete')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--dcg-home', type=Path,
                        help='Validated DCG development package; overrides DCG_HOME')
    parser.add_argument('--cleanup', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    if args.cleanup:
        evidence = args.evidence.resolve()
        require((evidence / '.phase2-service-marker').is_file(),
                'Not a Phase 2 service evidence directory')
        cleanup_owned(evidence)
        return 0
    validated = select_and_validate(args.dcg_home, required_capabilities=PHASE2_SERVICE_CAPABILITIES)
    package = Path(validated['path'])
    run(args.evidence.resolve(), package, validated)
    print('PASS:', args.evidence / 'results.json')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
