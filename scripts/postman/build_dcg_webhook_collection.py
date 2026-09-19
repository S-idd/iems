#!/usr/bin/env python3
"""Generate a read-only Postman collection for the DCG→IEMS webhook demo."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POSTMAN = ROOT / 'postman'


def request(name, method, base, path, tests, *, iems=False):
    headers = [{'key': 'Accept', 'value': 'application/json'}]
    if iems:
        headers.append({'key': 'Authorization', 'value': '{{iems_dcg_auth}}'})
    return {'name': name, 'request': {'method': method, 'header': headers,
            'url': {'raw': base + path, 'host': [base], 'path': path.lstrip('/').split('/')},
            **({'auth': {'type': 'noauth'}} if iems else {})},
            'event': [{'listen': 'test', 'script': {'type': 'text/javascript', 'exec': tests}}]}


def s(code):
    return f'pm.test("HTTP {code}", () => pm.response.to.have.status({code}));'


def delivery(label):
    return request(label + ' DCG delivery', 'GET', '{{dcg_base_url}}',
                   '/api/notification-deliveries?runId={{' + label + '_run_id}}&sink=webhook',
                   [s(200), 'const rows=pm.response.json();',
                    'pm.test("one delivered webhook", () => { pm.expect(rows).to.have.length(1); pm.expect(rows[0].status).to.eql("DELIVERED"); pm.expect(rows[0].event.eventType).to.eql("CONTRACT_CHECK_FAILED"); });',
                    f'pm.environment.set("{label}_event_id", rows[0].event.eventId);',
                    f'pm.test("run correlated", () => pm.expect(rows[0].event.runId).to.eql(pm.environment.get("{label}_run_id")));'])


def inbox(label):
    return request(label + ' IEMS inbox', 'GET', '{{iems_base_url}}',
                   '/api/dcg/events?runId={{' + label + '_run_id}}&eventType=CONTRACT_CHECK_FAILED',
                   [s(200), 'const rows=pm.response.json();',
                    f'pm.test("matching inbox event", () => {{ pm.expect(rows).to.have.length(1); pm.expect(rows[0].eventId).to.eql(pm.environment.get("{label}_event_id")); pm.expect(rows[0].runId).to.eql(pm.environment.get("{label}_run_id")); pm.expect(rows[0].contractId).to.eql("iems.enrollment"); }});'], iems=True)


def main():
    items = [request('DCG health', 'GET', '{{dcg_base_url}}', '/actuator/health', [s(200)]),
             request('IEMS health', 'GET', '{{iems_base_url}}', '/actuator/health', [s(200)], iems=True),
             request('IEMS inbox rejects missing authorization', 'GET', '{{iems_base_url}}', '/api/dcg/events', [s(401)]),
             delivery('online'), inbox('online'), delivery('retry'), inbox('retry'),
             request('DCG retry run result', 'GET', '{{dcg_base_url}}', '/checks/{{retry_run_id}}',
                     [s(200), 'pm.test("check remains FAIL", () => pm.expect(pm.response.json().status).to.eql("FAIL"));']),
             request('DCG delivery dashboard', 'GET', '{{dcg_base_url}}', '/ui/notifications?runId={{retry_run_id}}',
                     [s(200), 'pm.test("run and DELIVERED visible", () => { pm.expect(pm.response.text()).to.include(pm.environment.get("retry_run_id")); pm.expect(pm.response.text()).to.include("DELIVERED"); });'])]
    # The missing-auth request must not inherit the IEMS auth header.
    items[2]['request']['header'] = [{'key': 'Accept', 'value': 'application/json'}]
    collection = {'info': {'name': 'IEMS DCG Webhook Delivery Verification',
        'description': 'Read-only verification of the isolated DCG service outbox and separate IEMS DCG inbox after the webhook rehearsal. No retry or reset requests.',
        'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'},
        'auth': {'type': 'basic', 'basic': [{'key': 'username', 'value': '{{dcg_username}}', 'type': 'string'},
                                          {'key': 'password', 'value': '{{dcg_password}}', 'type': 'string'}]},
        'item': items}
    values = [{'key': k, 'value': '', 'enabled': True} for k in
              ('dcg_base_url', 'iems_base_url', 'dcg_username', 'dcg_password', 'iems_dcg_auth', 'online_run_id', 'retry_run_id')]
    environment = {'name': 'IEMS DCG webhook isolated rehearsal', 'values': values,
                   '_postman_variable_scope': 'environment'}
    (POSTMAN / 'dcg-webhook-collection.json').write_text(json.dumps(collection, indent=2) + '\n')
    (POSTMAN / 'dcg-webhook-environment.json').write_text(json.dumps(environment, indent=2) + '\n')


if __name__ == '__main__':
    main()
