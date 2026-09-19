#!/usr/bin/env python3
"""Compare the packaged deterministic CLI and real Rust model on IEMS schemas."""
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def main():
    target = {('Darwin', 'arm64'): 'macos-arm64', ('Linux', 'x86_64'): 'linux-x64'}.get(
        (platform.system(), platform.machine()))
    package = Path(os.environ.get('DCG_HOME', ROOT / '.dcg/runtime' / f'dcg-4.0.0-rc.1-{target}'))
    binary = package / 'bin/dcgaimodel'
    if not binary.is_file():
        raise SystemExit('Install the DCG binary package first, or set DCG_HOME.')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    out = ROOT / '.dcg/ai-demo'
    out.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    endpoint = f'http://127.0.0.1:{port}'
    results = []
    with (out / 'model.log').open('w') as log:
        process = subprocess.Popen([str(binary), 'serve-shadow-inference', '--artifact-root',
                                    str(package / 'model'), '--bind', f'127.0.0.1:{port}'],
                                   stdout=log, stderr=log)
        try:
            for _ in range(120):
                if process.poll() is not None:
                    raise RuntimeError(f'Model exited; inspect {out / "model.log"}')
                try:
                    with opener.open(endpoint + '/health/ready', timeout=1) as response:
                        if response.status == 200:
                            break
                except (OSError, urllib.error.URLError):
                    time.sleep(0.25)
            else:
                raise RuntimeError('Model readiness timed out')
            base = ROOT / 'contracts/iems.enrollment/v1.json'
            for name, expected in [('compatible', 0), ('breaking', 1)]:
                candidate = ROOT / f'scripts/dcg/fixtures/{name}.json'
                check = subprocess.run([str(ROOT / 'scripts/dcg.sh'), 'cli', 'check-compat',
                                        '--base', str(base), '--candidate', str(candidate)],
                                       capture_output=True, text=True, timeout=30)
                if check.returncode != expected:
                    raise RuntimeError(check.stdout + check.stderr)
                payload = {'base_schema': json.loads(base.read_text()),
                           'candidate_schema': json.loads(candidate.read_text()), 'policy_pack': 'baseline'}
                request = urllib.request.Request(endpoint + '/v1/shadow/predict',
                                                 json.dumps(payload).encode(),
                                                 {'Content-Type': 'application/json'})
                with opener.open(request, timeout=30) as response:
                    prediction = json.load(response)
                result = {'scenario': name, 'authoritative_exit': check.returncode,
                          'authoritative_output': check.stdout.strip(), 'advisory_model': prediction}
                results.append(result)
                print(json.dumps(result, indent=2))
            (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
            print('AI predictions are advisory. Only deterministic compatibility controls the gate.')
            print(f'Evidence: {out / "results.json"}')
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    main()
