#!/usr/bin/env python3
"""Rehearse DCG webhook delivery to the real IEMS demo inbox, including outbox retry."""
import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import service_registry_demo as common
from dcg_package import PHASE1_CAPABILITIES, select_and_validate, validate_package

ROOT = common.ROOT
APP_JAR = ROOT / 'target/inclusive-education-management-system-1.0.0-SNAPSHOT.jar'


def http(method, url, authorization=None, body=None, expected=200):
    headers = {'Accept': 'application/json'}
    if authorization:
        headers['Authorization'] = authorization
    data = None if body is None else json.dumps(body).encode()
    if data is not None:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            status, raw, kind = response.status, response.read(), response.headers.get('Content-Type', '')
    except urllib.error.HTTPError as error:
        status, raw, kind = error.code, error.read(), error.headers.get('Content-Type', '')
    common.ensure(status == expected, f'{method} {urllib.parse.urlsplit(url).path}: expected {expected}, got {status}: {raw[:200]!r}')
    return json.loads(raw) if raw and 'json' in kind else raw.decode(errors='replace')


def start_iems(runtime, port, jwt_secret, admin_password, webhook_auth, log):
    java_home = os.environ.get('JAVA_HOME')
    common.ensure(java_home and APP_JAR.is_file(), 'Java 21 and packaged IEMS JAR required')
    env = {**os.environ, 'IEMS_PORT': str(port), 'IEMS_JWT_SECRET': jwt_secret,
           'IEMS_DEMO_ADMIN_PASSWORD': admin_password,
           'IEMS_JDBC_URL': 'jdbc:sqlite:' + str(runtime / 'iems-app.db'),
           'IEMS_DCG_WEBHOOK_INBOX_DB': str(runtime / 'iems-dcg-inbox.db'),
           'IEMS_DCG_WEBHOOK_AUTH': webhook_auth}
    args = [str(Path(java_home) / 'bin/java'), '-jar', str(APP_JAR),
            '--spring.profiles.active=db-demo,db-sqlite', '--iems.dcg.webhook.enabled=true',
            '--server.address=127.0.0.1', '--server.port=' + str(port)]
    with log.open('w') as output:
        process = subprocess.Popen(args, cwd=runtime, env=env, stdout=output, stderr=output, start_new_session=True)
    try:
        common.wait_health('http://127.0.0.1:' + str(port), process, timeout=100, service='IEMS')
    except BaseException:
        common.stop_owned(process)
        raise
    return process


def dcg_request(base, credentials, method, path, body=None, expected=200):
    return common.request(base, credentials, method, path, body, expected)[1]


def iems_events(base, auth, run_id):
    path = '/api/dcg/events?runId=' + urllib.parse.quote(run_id) + '&eventType=CONTRACT_CHECK_FAILED'
    return http('GET', base + path, auth)


def delivery_for(base, credentials, run_id):
    path = '/api/notification-deliveries?runId=' + urllib.parse.quote(run_id) + '&sink=webhook&limit=20'
    rows = dcg_request(base, credentials, 'GET', path)
    common.ensure(len(rows) <= 1, 'Unexpected duplicate delivery for one check run')
    return rows[0] if rows else None


def await_delivery(base, credentials, run_id, expected, timeout=70):
    deadline = time.monotonic() + timeout
    states = []
    while time.monotonic() < deadline:
        delivery = delivery_for(base, credentials, run_id)
        if delivery:
            states.append(delivery['status'])
            if delivery['status'] == expected:
                return delivery, states
            common.ensure(delivery['status'] != 'FAILED_PERMANENT', 'Delivery failed permanently')
        time.sleep(.3)
    raise RuntimeError('Timed out waiting for ' + expected + ' delivery for ' + run_id)


def await_inbox(base, auth, run_id, timeout=70):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rows = iems_events(base, auth, run_id)
        if len(rows) == 1:
            return rows[0]
        common.ensure(not rows, 'Duplicate IEMS inbox events')
        time.sleep(.3)
    raise RuntimeError('Timed out waiting for IEMS inbox event for ' + run_id)


def notification_count(db):
    with sqlite3.connect(db) as conn:
        return conn.execute('SELECT count(*) FROM notifications').fetchone()[0]


def run(evidence, package=None, validated_package=None):
    common.ensure(not evidence.exists(), 'Evidence directory already exists')
    if package is None:
        validated_package = select_and_validate(None, required_capabilities=PHASE1_CAPABILITIES)
        package = Path(validated_package['path'])
    else:
        validated_package = validated_package or validate_package(package, required_capabilities=PHASE1_CAPABILITIES)
    os.umask(0o077)
    evidence.mkdir(mode=0o700)
    (evidence / '.dcg-webhook-demo-marker').write_text('IEMS DCG webhook demo\n')
    runtime = evidence / 'runtime'
    runtime.mkdir(mode=0o700)
    (runtime / 'contracts').mkdir(mode=0o700)
    (evidence / 'evidence').mkdir(mode=0o700)
    common.ensure(APP_JAR.is_file(), 'Build IEMS JAR before webhook rehearsal')
    package_before = common.inventory(package)
    contracts_before = common.inventory(ROOT / 'contracts')
    jar_hash = common.sha(APP_JAR.read_bytes())
    common.ensure(not common.rust_processes(), 'Rust model already running')
    dcg_port = common.free_port()
    iems_port = common.free_port()
    common.ensure(dcg_port != iems_port, 'Port collision')
    dcg_base = 'http://127.0.0.1:' + str(dcg_port)
    iems_base = 'http://127.0.0.1:' + str(iems_port)
    username = 'iems-dcg-demo'
    password = secrets.token_hex(32)
    credentials = username + ':' + password
    jwt_secret = secrets.token_urlsafe(64)
    admin_password = secrets.token_urlsafe(32)
    webhook_auth = 'Basic ' + base64.b64encode(secrets.token_bytes(32)).decode()
    webhook_url = iems_base + '/api/dcg/webhook'
    dcg_args = ('--notifications.enabled=true', '--notifications.sinks=webhook',
                '--notifications.webhook.enabled=true',
                '--notifications.webhook.url-env=DCG_DEMO_WEBHOOK_URL',
                '--notifications.webhook.auth-header-env=DCG_DEMO_WEBHOOK_AUTH',
                '--notifications.retry.initial-delay=60s',
                '--notifications.retry.max-attempts=3',
                '--notifications.dispatch.poll-interval-ms=1000')
    dcg_env = {'DCG_DEMO_WEBHOOK_URL': webhook_url, 'DCG_DEMO_WEBHOOK_AUTH': webhook_auth}
    iems = dcg = None
    report = {'result': 'INCOMPLETE', 'dcg_port': dcg_port, 'iems_port': iems_port,
              'package': str(package), 'validated_package': validated_package,
              'iems_jar_sha256': jar_hash,
              'configuration_keys': ['DCG_AI_ENABLED', 'SHADOW_INFERENCE_ENABLED', 'IEMS_DCG_WEBHOOK_AUTH',
                                     'IEMS_DCG_WEBHOOK_INBOX_DB', 'DCG_DEMO_WEBHOOK_URL', 'DCG_DEMO_WEBHOOK_AUTH'],
              'storage': {'dcg_checks': str(runtime / 'checks.db'),
                          'dcg_contracts': str(runtime / 'contracts'),
                          'iems_application': str(runtime / 'iems-app.db'),
                          'iems_dcg_inbox': str(runtime / 'iems-dcg-inbox.db')},
              'ai_enabled': False, 'runs': {}}
    try:
        iems = start_iems(runtime, iems_port, jwt_secret, admin_password, webhook_auth, evidence / 'iems-start.log')
        common.ensure((runtime / 'iems-app.db').is_file(), 'IEMS app database missing')
        common.ensure((runtime / 'iems-dcg-inbox.db').is_file(), 'IEMS DCG inbox missing')
        common.ensure(notification_count(runtime / 'iems-app.db') == 0, 'IEMS user notification table not empty')
        # Exact secret header is required; the public route itself is demo-only.
        http('GET', iems_base + '/api/dcg/events', expected=401)
        http('POST', webhook_url, body={'eventId': 'untrusted'}, expected=401)
        common.ensure(not http('GET', iems_base + '/api/dcg/events', webhook_auth), 'Inbox not empty')
        dcg, _ = common.start_service(package, runtime, dcg_port, username, password,
                                       evidence / 'dcg-start.log', extra_args=dcg_args, extra_env=dcg_env)
        common.ensure(not common.rust_processes(), 'Rust model started')
        baseline = json.loads((ROOT / 'contracts/iems.enrollment/v1.json').read_text())
        breaking = json.loads((common.FIXTURES / 'enrollment.json').read_text())
        pinned = json.loads((common.FIXTURES / 'manifest.json').read_text())['contracts']['iems.enrollment']['fixture_sha256']
        common.ensure(common.sha((common.FIXTURES / 'enrollment.json').read_bytes()) == pinned, 'Breaking fixture changed')
        registered = dcg_request(dcg_base, credentials, 'POST', '/contracts',
                                 {'contractId': 'iems.enrollment', 'ownerTeam': 'iems', 'domain': 'education',
                                  'compatibilityMode': 'BACKWARD', 'initialVersion': 'v1', 'schema': baseline}, 201)
        common.ensure(registered['versions'] == ['v1'], 'Baseline registration failed')
        published = dcg_request(dcg_base, credentials, 'POST', '/contracts/iems.enrollment/versions',
                                {'version': 'v2', 'schema': breaking}, 201)
        common.ensure(published['version'] == 'v2', 'Breaking proposal not published')
        report['registration'] = {'contract_id': 'iems.enrollment', 'versions': ['v1', 'v2'],
                                  'baseline_sha256': common.sha((ROOT / 'contracts/iems.enrollment/v1.json').read_bytes()),
                                  'proposal_sha256': common.sha((common.FIXTURES / 'enrollment.json').read_bytes())}
        for label, commit in [('delivered', 'webhook-online'), ('retry', 'webhook-outage')]:
            if label == 'retry':
                common.stop_owned(iems)
                iems = None
                common.ensure(common.wait_port_released(iems_port), 'IEMS port not released before outage check')
            body = {'contractId': 'iems.enrollment', 'baseVersion': 'v1', 'candidateVersion': 'v2',
                    'mode': 'BACKWARD', 'commitSha': commit, 'triggeredBy': 'iems-webhook-demo'}
            accepted = dcg_request(dcg_base, credentials, 'POST', '/checks', body, 202)
            common.ensure(accepted['status'] == 'QUEUED', 'Check not queued')
            final, states = common.poll_run(dcg_base, credentials, accepted['runId'])
            common.ensure(final['status'] == 'FAIL', 'Breaking check did not FAIL')
            run_id = accepted['runId']
            expected = 'DELIVERED' if label == 'delivered' else 'FAILED_RETRYABLE'
            delivery, delivery_states = await_delivery(dcg_base, credentials, run_id, expected)
            common.ensure(delivery['event']['runId'] == run_id and delivery['event']['contractId'] == 'iems.enrollment',
                          'Outbox event does not correlate with check')
            record = {'run_id': run_id, 'check_status': final['status'], 'check_poll_states': states,
                      'delivery_id': delivery['deliveryId'], 'event_id': delivery['event']['eventId'],
                      'delivery_status_before_recovery': delivery['status'], 'delivery_poll_states': delivery_states,
                      'attempt_count_before_recovery': delivery['attemptCount']}
            report['runs'][label] = record
            common.write_private(evidence / 'evidence' / (label + '-check.json'), final)
            common.write_private(evidence / 'evidence' / (label + '-delivery-before.json'), delivery)
            if label == 'delivered':
                received = await_inbox(iems_base, webhook_auth, run_id)
                common.ensure(received['eventId'] == record['event_id'] and received['contractId'] == 'iems.enrollment',
                              'IEMS inbox does not correlate with outbox')
                record['inbox_before_restart'] = received
        common.ensure(report['runs']['delivered']['run_id'] != report['runs']['retry']['run_id'], 'Run IDs duplicated')
        first_delivery = report['runs']['delivered']['delivery_id']
        second_delivery = report['runs']['retry']['delivery_id']
        common.ensure(first_delivery != second_delivery, 'Delivery IDs duplicated')
        # Persisted DCG outbox must survive service restart while IEMS is still unavailable.
        common.stop_owned(dcg)
        dcg = None
        common.ensure(common.wait_port_released(dcg_port), 'DCG port not released before restart')
        dcg, _ = common.start_service(package, runtime, dcg_port, username, password,
                                       evidence / 'dcg-restart.log', extra_args=dcg_args, extra_env=dcg_env)
        same = delivery_for(dcg_base, credentials, report['runs']['retry']['run_id'])
        common.ensure(same and same['deliveryId'] == second_delivery and same['status'] == 'FAILED_RETRYABLE',
                      'Failed delivery did not persist across DCG restart')
        iems = start_iems(runtime, iems_port, jwt_secret, admin_password, webhook_auth, evidence / 'iems-restart.log')
        first_inbox = await_inbox(iems_base, webhook_auth, report['runs']['delivered']['run_id'])
        common.ensure(first_inbox['eventId'] == report['runs']['delivered']['event_id'],
                      'Previously delivered IEMS event lost on restart')
        retried = dcg_request(dcg_base, credentials, 'POST',
                              '/api/notification-deliveries/' + second_delivery + '/retry', expected=200)
        common.ensure(retried['deliveryId'] == second_delivery, 'Retry created a new delivery ID')
        final_delivery, retry_states = await_delivery(dcg_base, credentials, report['runs']['retry']['run_id'], 'DELIVERED')
        second_inbox = await_inbox(iems_base, webhook_auth, report['runs']['retry']['run_id'])
        common.ensure(final_delivery['event']['eventId'] == second_inbox['eventId'], 'Retried event ID mismatch')
        common.ensure(final_delivery['deliveryId'] == second_delivery and final_delivery['attemptCount'] >= 2,
                      'Retry did not reuse and attempt original delivery')
        common.ensure(len(iems_events(iems_base, webhook_auth, report['runs']['retry']['run_id'])) == 1,
                      'Retried event duplicated in IEMS inbox')
        report['runs']['retry']['delivery_status_after_recovery'] = final_delivery['status']
        report['runs']['retry']['attempt_count_after_recovery'] = final_delivery['attemptCount']
        report['runs']['retry']['retry_states'] = retry_states
        report['runs']['retry']['inbox_after_recovery'] = second_inbox
        common.write_private(evidence / 'evidence/retry-delivery-after.json', final_delivery)
        common.write_private(evidence / 'evidence/retry-inbox.json', second_inbox)
        common.ensure(notification_count(runtime / 'iems-app.db') == 0,
                      'DCG webhook unexpectedly wrote IEMS user notifications')
        _, ui = common.request(dcg_base, credentials, 'GET', '/ui/notifications?runId=' + report['runs']['retry']['run_id'])
        common.ensure(report['runs']['retry']['run_id'] in ui and 'DELIVERED' in ui,
                      'DCG notifications dashboard missing retried delivery')
        (evidence / 'evidence/dcg-notifications.html').write_text(ui)
        report['ui'] = {'route': '/ui/notifications', 'retry_run_id_visible': True,
                        'delivery_status_visible': True}
        report['user_notification_rows'] = notification_count(runtime / 'iems-app.db')
        newman_env = {**os.environ, 'DCG_DEMO_USERNAME': username,
                      'DCG_DEMO_PASSWORD': password, 'IEMS_DCG_WEBHOOK_AUTH': webhook_auth}
        newman = subprocess.run(['node', str(ROOT / 'scripts/postman/run_dcg_webhook_collection.js'),
                                 dcg_base, iems_base, report['runs']['delivered']['run_id'],
                                 report['runs']['retry']['run_id']], env=newman_env,
                                capture_output=True, text=True, timeout=90)
        (evidence / 'evidence/postman-webhook.log').write_text(newman.stdout + newman.stderr)
        common.ensure(newman.returncode == 0, 'Postman webhook verification failed; inspect evidence/postman-webhook.log')
        report['newman'] = {'exit_code': newman.returncode,
                            'collection': 'postman/dcg-webhook-collection.json'}
        report['result'] = 'PASS'
    except BaseException as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        if dcg is not None:
            common.stop_owned(dcg)
        if iems is not None:
            common.stop_owned(iems)
        report['dcg_port_released'] = common.wait_port_released(dcg_port)
        report['iems_port_released'] = common.wait_port_released(iems_port)
        report['rust_after'] = common.rust_processes()
        report['package_unchanged'] = package_before == common.inventory(package)
        report['contracts_unchanged'] = contracts_before == common.inventory(ROOT / 'contracts')
        report['iems_jar_unchanged'] = jar_hash == common.sha(APP_JAR.read_bytes())
        if not all(report[key] for key in ('dcg_port_released', 'iems_port_released', 'package_unchanged',
                                            'contracts_unchanged', 'iems_jar_unchanged')) or report['rust_after']:
            report['result'] = 'INCOMPLETE'
        common.write_private(evidence / 'results.json', report)
        for path in evidence.rglob('*'):
            path.chmod(0o700 if path.is_dir() else 0o600)
    print('PASS:', evidence / 'results.json')


def serve_existing(evidence, package):
    evidence = evidence.resolve()
    common.ensure((evidence / '.dcg-webhook-demo-marker').is_file(), 'Not a DCG webhook rehearsal')
    report = json.loads((evidence / 'results.json').read_text())
    common.ensure(report.get('result') == 'PASS' and report.get('dcg_port_released')
                  and report.get('iems_port_released'), 'Completed, stopped rehearsal required')
    runtime = evidence / 'runtime'
    common.ensure((runtime / 'checks.db').is_file() and (runtime / 'iems-dcg-inbox.db').is_file(),
                  'Retained DCG/IEMS webhook state missing')
    common.verify_package(package)
    common.ensure(common.sha(APP_JAR.read_bytes()) == report['iems_jar_sha256'],
                  'IEMS JAR changed since this rehearsal; rerun from fresh evidence')
    common.ensure(not common.rust_processes(), 'Rust model already running')
    dcg_port, iems_port = common.free_port(), common.free_port()
    common.ensure(dcg_port != iems_port, 'Port collision')
    username = 'iems-dcg-demo'
    password = secrets.token_hex(32)
    webhook_auth = 'Basic ' + base64.b64encode(secrets.token_bytes(32)).decode()
    jwt_secret = secrets.token_urlsafe(64)
    admin_password = secrets.token_urlsafe(32)
    webhook_url = 'http://127.0.0.1:' + str(iems_port) + '/api/dcg/webhook'
    dcg_args = ('--notifications.enabled=true', '--notifications.sinks=webhook',
                '--notifications.webhook.enabled=true',
                '--notifications.webhook.url-env=DCG_DEMO_WEBHOOK_URL',
                '--notifications.webhook.auth-header-env=DCG_DEMO_WEBHOOK_AUTH',
                '--notifications.dispatch.poll-interval-ms=1000')
    dcg_env = {'DCG_DEMO_WEBHOOK_URL': webhook_url, 'DCG_DEMO_WEBHOOK_AUTH': webhook_auth}
    iems = dcg = None
    try:
        iems = start_iems(runtime, iems_port, jwt_secret, admin_password, webhook_auth,
                          evidence / 'iems-presentation.log')
        dcg, _ = common.start_service(package, runtime, dcg_port, username, password,
                                       evidence / 'dcg-presentation.log', extra_args=dcg_args,
                                       extra_env=dcg_env)
        print('DCG delivery dashboard: http://127.0.0.1:' + str(dcg_port) + '/ui/notifications', flush=True)
        print('DCG API username: ' + username, flush=True)
        print('DCG API temporary password: ' + password, flush=True)
        print('IEMS DCG inbox: http://127.0.0.1:' + str(iems_port) + '/api/dcg/events', flush=True)
        print('IEMS inbox temporary Authorization header: ' + webhook_auth, flush=True)
        print('Press Ctrl-C to stop both task-owned services.', flush=True)
        while iems.poll() is None and dcg.poll() is None:
            time.sleep(.5)
        raise RuntimeError('Presentation service exited unexpectedly; inspect presentation logs')
    except (KeyboardInterrupt, InterruptedError):
        pass
    finally:
        if dcg is not None:
            common.stop_owned(dcg)
        if iems is not None:
            common.stop_owned(iems)
        common.ensure(common.wait_port_released(dcg_port) and common.wait_port_released(iems_port),
                      'Presentation ports not released')
    print('Presentation services stopped; retained webhook evidence is unchanged.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--dcg-home', type=Path,
                        help='Validated DCG development package; overrides DCG_HOME')
    parser.add_argument('--serve-existing', action='store_true', help='Reopen both services for a live demo until Ctrl-C')
    args = parser.parse_args()
    os.umask(0o077)
    def interrupted(signum, frame):
        raise InterruptedError('Signal ' + str(signum) + '; stopping owned services')
    import signal
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, interrupted)
    if args.serve_existing:
        validated = select_and_validate(args.dcg_home, required_capabilities=PHASE1_CAPABILITIES)
        serve_existing(args.evidence, Path(validated['path']))
    else:
        common.ensure(not args.evidence.exists(), 'Evidence directory already exists')
        validated = select_and_validate(args.dcg_home, required_capabilities=PHASE1_CAPABILITIES)
        run(args.evidence.resolve(), Path(validated['path']), validated)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Webhook rehearsal failed:', error, file=sys.stderr)
        raise SystemExit(1)
