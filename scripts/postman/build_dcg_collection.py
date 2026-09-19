#!/usr/bin/env python3
"""Generate the separate DCG service Postman collection from approved IEMS fixtures."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POSTMAN = ROOT / 'postman'
BASE = ROOT / 'contracts'
BREAKING = ROOT / 'scripts/dcg/fixtures/multiple-breaking/enrollment.json'


def script(*lines):
    return [{'listen': 'test', 'script': {'type': 'text/javascript', 'exec': list(lines)}}]


def item(name, method, path, tests, body=None):
    req = {'method': method, 'header': [{'key': 'Accept', 'value': 'application/json'}],
           'url': {'raw': '{{dcg_base_url}}' + path, 'host': ['{{dcg_base_url}}'],
                   'path': path.lstrip('/').split('/')}}
    if body is not None:
        req['header'].append({'key': 'Content-Type', 'value': 'application/json'})
        req['body'] = {'mode': 'raw', 'raw': json.dumps(body, separators=(',', ':'))}
    return {'name': name, 'request': req, 'event': script(*tests)}


def status(code):
    return f'pm.test("HTTP {code}", () => pm.response.to.have.status({code}));'


def register(name):
    cid = 'iems.' + name
    return item('Register ' + cid, 'POST', '/contracts',
                [status(201), 'const j=pm.response.json();',
                 f'pm.test("registered {cid} with v1", () => {{ pm.expect(j.contractId).to.eql("{cid}"); pm.expect(j.versions).to.include("v1"); }});'],
                {'contractId': cid, 'ownerTeam': 'iems', 'domain': 'education',
                 'compatibilityMode': 'BACKWARD', 'initialVersion': 'v1',
                 'schema': '{{schema_' + name + '_v1}}'})


def schema_body_fix(folder):
    # A raw body placeholder must be substituted as a JSON object, not a quoted string.
    for child in folder['item']:
        raw = child['request'].get('body', {}).get('raw')
        if raw:
            for name in ('accessibility', 'enrollment', 'notification', 'scholarship'):
                raw = raw.replace('"{{schema_' + name + '_v1}}"', '{{schema_' + name + '_v1}}')
            raw = raw.replace('"{{schema_scholarship_v2}}"', '{{schema_scholarship_v2}}')
            raw = raw.replace('"{{schema_enrollment_v2}}"', '{{schema_enrollment_v2}}')
            child['request']['body']['raw'] = raw


def poll(label, expected):
    key = label + '_run_id'
    counter = label + '_poll_count'
    return item('Poll ' + label + ' check', 'GET', '/checks/{{' + key + '}}',
                [status(200), 'const j=pm.response.json();',
                 f'pm.test("same run ID", () => pm.expect(j.runId).to.eql(pm.environment.get("{key}")));',
                 f'if (j.status === "QUEUED" || j.status === "RUNNING") {{ const n=Number(pm.environment.get("{counter}") || 0)+1; pm.environment.set("{counter}", n); pm.test("poll bounded to 30", () => pm.expect(n).to.be.below(31)); if(n<31) pm.execution.setNextRequest(pm.info.requestName); }} else {{ pm.test("terminal {expected}", () => pm.expect(j.status).to.eql("{expected}")); pm.environment.set("{label}_status", j.status); }}'])


def submit(label, cid):
    key = label + '_run_id'
    return item('Submit ' + label + ' check', 'POST', '/checks',
                [status(202), 'const j=pm.response.json();',
                 'pm.test("asynchronous acceptance", () => { pm.expect(j.status).to.eql("QUEUED"); pm.expect(j.runId).to.be.a("string").and.not.empty; });',
                 f'pm.environment.set("{key}", j.runId); pm.environment.set("{label}_poll_count", 0);'],
                {'contractId': cid, 'baseVersion': 'v1', 'candidateVersion': 'v2',
                 'mode': 'BACKWARD', 'commitSha': 'postman-demo', 'triggeredBy': 'postman-demo'})


def result_items(label, expected):
    key = label + '_run_id'
    return [item('Retrieve ' + label + ' result', 'GET', '/checks/{{' + key + '}}',
                 [status(200), 'const j=pm.response.json();',
                  f'pm.test("{expected} persisted", () => {{ pm.expect(j.runId).to.eql(pm.environment.get("{key}")); pm.expect(j.status).to.eql("{expected}"); }});']),
            item('Retrieve ' + label + ' logs', 'GET', '/checks/{{' + key + '}}/logs',
                 [status(200), 'const j=pm.response.json();',
                  f'pm.test("logs match {label} run", () => {{ pm.expect(j.length).to.be.above(0); j.forEach(x => pm.expect(x.runId).to.eql(pm.environment.get("{key}"))); }});'])]


def main():
    scholarship = json.loads((BASE / 'iems.scholarship/v1.json').read_text())
    scholarship = copy.deepcopy(scholarship)
    scholarship['properties']['sourceSystem'] = {'type': 'string'}
    variables = [{'key': 'schema_' + n + '_v1', 'value': json.dumps(json.loads((BASE / ('iems.'+n) / 'v1.json').read_text()), separators=(',', ':'))}
                 for n in ('accessibility', 'enrollment', 'notification', 'scholarship')]
    variables += [{'key': 'schema_scholarship_v2', 'value': json.dumps(scholarship, separators=(',', ':'))},
                  {'key': 'schema_enrollment_v2', 'value': json.dumps(json.loads(BREAKING.read_text()), separators=(',', ':'))},
                  {'key': 'compatible_run_id', 'value': ''}, {'key': 'breaking_run_id', 'value': ''}]
    setup = {'name': 'Register and check (fresh isolated service only)', 'item': [
        item('Health and readiness', 'GET', '/actuator/health', [status(200)]),
        item('Verify Basic authentication', 'GET', '/contracts', [status(200)]),
        *[register(n) for n in ('accessibility', 'enrollment', 'notification', 'scholarship')],
        item('List all four contracts', 'GET', '/contracts', [status(200),
             'const ids=pm.response.json().map(x=>x.contractId);',
             'pm.test("four IEMS contracts", () => pm.expect(ids.sort()).to.eql(["iems.accessibility","iems.enrollment","iems.notification","iems.scholarship"]));']),
        *[item('Retrieve ' + n + ' v1', 'GET', '/contracts/iems.' + n + '/versions/v1',
               [status(200), 'pm.test("published schema", () => pm.expect(pm.response.json().schema).to.be.an("object"));'])
          for n in ('accessibility', 'enrollment', 'notification', 'scholarship')],
        item('Publish compatible scholarship v2', 'POST', '/contracts/iems.scholarship/versions',
             [status(201), 'pm.test("v2 published", () => pm.expect(pm.response.json().version).to.eql("v2"));'],
             {'version': 'v2', 'schema': '{{schema_scholarship_v2}}'}),
        item('Retrieve scholarship v2', 'GET', '/contracts/iems.scholarship/versions/v2', [status(200)]),
        item('Publish breaking enrollment v2 proposal', 'POST', '/contracts/iems.enrollment/versions',
             [status(201), 'pm.test("v2 published", () => pm.expect(pm.response.json().version).to.eql("v2"));'],
             {'version': 'v2', 'schema': '{{schema_enrollment_v2}}'}),
        item('Retrieve enrollment v2', 'GET', '/contracts/iems.enrollment/versions/v2', [status(200)]),
        submit('compatible', 'iems.scholarship'), poll('compatible', 'PASS'), *result_items('compatible', 'PASS'),
        submit('breaking', 'iems.enrollment'), poll('breaking', 'FAIL'), *result_items('breaking', 'FAIL')]}
    schema_body_fix(setup)
    verify = {'name': 'Verify existing rehearsal', 'item': [
        item('Health and readiness', 'GET', '/actuator/health', [status(200)]),
        item('Verify Basic authentication and registry', 'GET', '/contracts', [status(200),
             'const ids=pm.response.json().map(x=>x.contractId);',
             'pm.test("all contracts persisted", () => pm.expect(ids.sort()).to.eql(["iems.accessibility","iems.enrollment","iems.notification","iems.scholarship"]));']),
        *[item('Verify ' + n + ' versions', 'GET', '/contracts/iems.' + n + '/versions',
               [status(200), 'const versions=pm.response.json();',
                f'pm.test("{n} v1 persists", () => pm.expect(versions).to.include("v1"));'])
          for n in ('accessibility', 'enrollment', 'notification', 'scholarship')],
        *result_items('compatible', 'PASS'), *result_items('breaking', 'FAIL'),
        item('Dashboard contracts', 'GET', '/ui/contracts', [status(200),
             'pm.test("real HTML lists enrollment", () => pm.expect(pm.response.text()).to.include("iems.enrollment"));']),
        item('Dashboard PASS run', 'GET', '/ui/checks/{{compatible_run_id}}', [status(200),
             'pm.test("PASS and run ID visible", () => { pm.expect(pm.response.text()).to.include(pm.environment.get("compatible_run_id")); pm.expect(pm.response.text()).to.include("PASS"); });']),
        item('Dashboard FAIL run', 'GET', '/ui/checks/{{breaking_run_id}}', [status(200),
             'pm.test("FAIL and run ID visible", () => { pm.expect(pm.response.text()).to.include(pm.environment.get("breaking_run_id")); pm.expect(pm.response.text()).to.include("FAIL"); });'])]}
    collection = {'info': {'name': 'IEMS DCG Governance Service Demo',
                'description': 'Separate DCG registry/check/dashboard demo. Run setup only against a fresh, isolated service with contracts.validation.strict-mode=false. Run verification against a populated service before and after restart. No reset request is included.',
                'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'},
                'auth': {'type': 'basic', 'basic': [{'key': 'username', 'value': '{{dcg_username}}', 'type': 'string'},
                                                  {'key': 'password', 'value': '{{dcg_password}}', 'type': 'string'}]},
                'variable': variables, 'item': [setup, verify]}
    environment = {'name': 'IEMS DCG local isolated service',
                   'values': [{'key': 'dcg_base_url', 'value': 'http://127.0.0.1:8080', 'enabled': True},
                              {'key': 'dcg_username', 'value': '', 'enabled': True},
                              {'key': 'dcg_password', 'value': '', 'enabled': True},
                              {'key': 'compatible_run_id', 'value': '', 'enabled': True},
                              {'key': 'breaking_run_id', 'value': '', 'enabled': True}],
                   '_postman_variable_scope': 'environment'}
    (POSTMAN / 'dcg-governance-collection.json').write_text(json.dumps(collection, indent=2) + '\n')
    (POSTMAN / 'dcg-governance-environment.json').write_text(json.dumps(environment, indent=2) + '\n')


if __name__ == '__main__':
    main()
