#!/usr/bin/env python3
"""Run authoritative IEMS contract checks, then attach optional Rust advice."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
RC = ROOT / '.dcg/runtime/dcg-4.0.0-rc.1-macos-arm64'
SEEDS = {'20260826', '20260827', '20260828'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def cases():
    fixtures = ROOT / 'scripts/dcg/fixtures'
    def pair(name, file):
        return (name, ROOT / f'contracts/{name}/v1.json', file)
    return {
        'compatible': [pair('iems.enrollment', fixtures / 'compatible.json')],
        'breaking': [pair('iems.enrollment', fixtures / 'breaking.json')],
        'multiple-breaking': [pair('iems.enrollment', fixtures / 'multiple-breaking/enrollment.json'),
                              pair('iems.scholarship', fixtures / 'multiple-breaking/scholarship.json')],
    }


def check(package, item):
    name, base, candidate = item
    run = subprocess.run([str(package / 'bin/dcg'), 'check-compat', '--base', str(base),
                          '--candidate', str(candidate), '--mode', 'BACKWARD'],
                         capture_output=True, text=True, timeout=40)
    if run.returncode not in (0, 1):
        raise RuntimeError(f'DCG infrastructure failed for {name}: exit {run.returncode}')
    payload = {'base_schema': json.loads(base.read_text()),
               'candidate_schema': json.loads(candidate.read_text()), 'policy_pack': 'baseline'}
    return {'contractId': name, 'governanceExitCode': run.returncode,
            'deterministicVerdict': 'PASS' if run.returncode == 0 else 'FAIL',
            'deterministicReason': run.stdout.strip()[-2000:],
            'baseSha256': sha(base.read_bytes()), 'candidateSha256': sha(candidate.read_bytes()),
            'inputHash': sha(encoded(payload)), '_payload': payload}


def validate(response):
    if not isinstance(response, dict) or set(response) != {'predictions'}:
        raise ValueError('invalid envelope')
    items = response['predictions']
    if not isinstance(items, list) or len(items) != 3 or not all(isinstance(x, dict) for x in items):
        raise ValueError('invalid prediction count')
    if any(not isinstance(x.get('seed'), str) for x in items) or {x['seed'] for x in items} != SEEDS:
        raise ValueError('invalid seeds')
    for item in items:
        if not isinstance(item.get('label'), str) or item['label'] not in {'SAFE', 'WARNING', 'BREAKING'}:
            raise ValueError('invalid label')
        values = item.get('probabilities')
        if not isinstance(values, dict) or set(values) != {'safe', 'warning', 'breaking'}:
            raise ValueError('invalid probability names')
        if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v)
               or v < 0 or v > 1 for v in values.values()) or abs(sum(values.values()) - 1) > .01:
            raise ValueError('invalid probabilities')
    return items


def predict(endpoint, payload, timeout):
    body = encoded(payload)
    if len(body) > 1024 * 1024:
        raise ValueError('request too large')
    request = urllib.request.Request(endpoint + '/v1/shadow/predict', body,
                                     {'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        body = response.read(65537)
    if len(body) > 65536:
        raise ValueError('response too large')
    return validate(json.loads(body))


def advise(check_result, endpoint, timeout, artifact_hashes):
    start = time.monotonic()
    result = {'advisoryStatus': 'UNAVAILABLE', 'modelVersion': 'frozen-v9-three-seed',
              'modelArtifactSha256': artifact_hashes, 'featureSchemaVersion': 'dcg-features-v6',
              'predictions': None, 'inferenceDurationMs': 0,
              'inputHash': check_result['inputHash'],
              'deterministicVerdict': check_result['deterministicVerdict'],
              'agreement': 'NOT_AVAILABLE', 'advisoryOnly': True}
    if endpoint is None:
        return result
    try:
        predictions = predict(endpoint, check_result['_payload'], timeout)
        result['predictions'] = predictions
        expected = 'SAFE' if check_result['deterministicVerdict'] == 'PASS' else 'BREAKING'
        result['agreement'] = 'AGREES' if all(x['label'] == expected for x in predictions) else 'DISAGREES'
        result['advisoryStatus'] = 'AVAILABLE'
    except (TimeoutError, socket.timeout):
        result['advisoryStatus'] = 'TIMEOUT'
    except (ValueError, json.JSONDecodeError):
        result['advisoryStatus'] = 'INVALID_OUTPUT'
    except urllib.error.URLError as error:
        result['advisoryStatus'] = 'TIMEOUT' if isinstance(error.reason, (TimeoutError, socket.timeout)) else 'UNAVAILABLE'
    except OSError:
        result['advisoryStatus'] = 'UNAVAILABLE'
    finally:
        result['inferenceDurationMs'] = round((time.monotonic() - start) * 1000)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=[*cases(), 'all'], default='all')
    parser.add_argument('--endpoint', help='Existing loopback model URL; skips model launch')
    parser.add_argument('--timeout-ms', type=int, default=500)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not 1 <= args.timeout_ms <= 5000:
        parser.error('timeout must be 1..5000 ms')
    if args.endpoint and not args.endpoint.startswith('http://127.0.0.1:'):
        parser.error('endpoint must use loopback')
    package = Path(os.environ.get('DCG_HOME', RC))
    if not (package / 'bin/dcg').is_file():
        parser.error('DCG_HOME must contain a binary package')
    selected = cases() if args.scenario == 'all' else {args.scenario: cases()[args.scenario]}
    # All governance decisions finish before any model startup or inference.
    checked = {name: [check(package, pair) for pair in pairs] for name, pairs in selected.items()}
    model_files = sorted((package / 'model/data/experiments/v9-multiclass-cpu-100e/models').glob('*.json'))
    hashes = {path.name: sha(path.read_bytes()) for path in model_files}
    endpoint = args.endpoint
    process = None
    if os.environ.get('DCG_AI_ENABLED', 'true').lower() == 'false':
        endpoint = None
    elif endpoint is None and (package / 'bin/dcgaimodel').is_file():
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        endpoint = f'http://127.0.0.1:{port}'
        log_path = args.output.with_suffix('.model.log') if args.output else ROOT / '.dcg/ai-demo/model.log'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with log_path.open('w') as log:
                process = subprocess.Popen([str(package / 'bin/dcgaimodel'), 'serve-shadow-inference',
                                            '--artifact-root', str(package / 'model'), '--bind', f'127.0.0.1:{port}'],
                                           stdout=log, stderr=log)
        except OSError:
            endpoint = None
        if process is not None:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and process.poll() is None:
                try:
                    with opener.open(endpoint + '/health/ready', timeout=.3) as response:
                        if response.status == 200:
                            break
                except (OSError, urllib.error.URLError):
                    time.sleep(.05)
            else:
                endpoint = None
    try:
        result = {}
        for name, checks in checked.items():
            entries = []
            for checked_item in checks:
                entry = {k: v for k, v in checked_item.items() if k != '_payload'}
                entry['advisory'] = advise(checked_item, endpoint, args.timeout_ms / 1000, hashes)
                entries.append(entry)
            result[name] = {'finalEnforcementResult': 'FAIL' if any(x['governanceExitCode'] == 1 for x in entries) else 'PASS',
                            'contracts': entries}
        output = args.output or ROOT / '.dcg/ai-demo/results.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
        print(f'Evidence: {output}')
    finally:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    main()
