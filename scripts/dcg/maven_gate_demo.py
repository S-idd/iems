#!/usr/bin/env python3
"""Real Maven gate rehearsal in disposable copies; official JSON evidence, no AI."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import threading
import xml.etree.ElementTree as ET

from multiple_contract_demo import ROOT, FIXTURES, inventory, require, sha, stop_child, verify_package, rust_processes


@contextmanager
def breaking(app, names):
    manifest = json.loads((FIXTURES / 'manifest.json').read_text())['contracts']
    changes = {}
    for name in names:
        item = manifest[name]
        require(sha((app / 'contracts' / name / 'v1.json').read_bytes()) == item['baseline_sha256'], 'Stale baseline')
        data = (FIXTURES / item['file']).read_bytes()
        require(sha(data) == item['fixture_sha256'], 'Tampered fixture')
        changes[app / 'contracts' / name / 'candidate.json'] = data
    saved = {path: path.read_bytes() for path in changes}
    try:
        for path, data in changes.items():
            path.write_bytes(data)
        yield
    finally:
        for path, data in saved.items():
            path.write_bytes(data)
        require(all(path.read_bytes() == data for path, data in saved.items()), 'Reset failed')


def packaging_reached(log):
    return any(marker in log for marker in ('--- jar:', '--- spring-boot:', 'maven-jar-plugin:', 'spring-boot-maven-plugin:'))


def assert_no_packaging(before, after, log):
    require(not before, 'Build target must start without artifacts; stale artifacts invalidate proof')
    require(not after, 'Failing gate produced an application artifact')
    require(not packaging_reached(log),
            'Packaging goal reached after gate failure')
    require('contract-maven-plugin:4.0.0-rc.1:check-compat' in log and 'DCG compatibility failed:' in log,
            'Maven failed for a reason other than the contract gate')


def run(evidence, repository, package, *, ai_requested=False):
    evidence.mkdir(parents=True, exist_ok=False, mode=0o700)
    env = dict(os.environ, DCG_AI_ENABLED='true' if ai_requested else 'false')
    if env.get('JAVA_HOME'):
        env['PATH'] = env['JAVA_HOME'] + '/bin:' + env['PATH']
    report = {'result': 'INCOMPLETE', 'profile': 'dcg-demo', 'plugin': 'com.ideas.contracts:contract-maven-plugin:4.0.0-rc.1',
              'goal': 'check-compat', 'phase': 'validate', 'ai_enabled': ai_requested, 'history_format': 'official JSON evidence',
              'package': str(package), 'package_version': verify_package(package), 'scenarios': []}
    original_rc = ROOT / '.dcg/runtime/dcg-4.0.0-rc.1-macos-arm64'
    preserved = {name: inventory(path) for name, path in [('contracts', ROOT / 'contracts'), ('package', package), ('rc', original_rc)]}
    report['source_contracts_before'] = preserved['contracts']
    report['maven_java_version'] = subprocess.check_output(['mvn', '-version'], env=env, text=True)
    observations = []
    finished = threading.Event()
    def observe():
        while not finished.wait(.2):
            observations.extend(rust_processes())
            lines = subprocess.check_output(['ps', '-axo', 'comm=,args='], text=True).splitlines()
            observations.extend(line for line in lines if line.split() and line.split()[0].endswith('/java')
                                and '-jar ' in line and '/target/inclusive-education-management-system' in line)
    require(not rust_processes(), 'Stop the Rust model before this no-AI rehearsal')
    watcher = threading.Thread(target=observe)
    watcher.start()

    def build(app, name, expected=0, profile=True, phase='verify', missing_ai=False):
        folder = evidence / name
        folder.mkdir(mode=0o700)
        reports = folder / 'reports'
        artifact_before = {p.name: sha(p.read_bytes()) for p in (app / 'target').glob('*.jar')}
        command = ['mvn', '-B', '-ntp', phase]
        if profile:
            command += ['-Pdcg-demo', '-Ddcg.plugin.repository.url=' + repository.as_uri(), '-Ddcg.reports.dir=' + str(reports)]
        effective_env = dict(env)
        if missing_ai:
            effective_env['DCG_HOME'] = str(app / 'missing-ai-and-cli')
        log_path = folder / 'build.log'
        with log_path.open('w') as log:
            process = subprocess.Popen(command, cwd=app, env=effective_env, stdout=log, stderr=log, start_new_session=True)
            try:
                code = process.wait(timeout=600)
            finally:
                if process.poll() is None:
                    stop_child(process)
        text = log_path.read_text()
        artifact_after = {p.name: sha(p.read_bytes()) for p in (app / 'target').glob('*.jar')}
        verdicts = {p.stem: json.loads(p.read_text())['localStatus'] for p in reports.glob('*.json')}
        tests = {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0}
        for path in (app / 'target/surefire-reports').glob('TEST-*.xml'):
            suite = ET.parse(path).getroot()
            for key in tests:
                tests[key] += int(suite.get(key, '0'))
        item = {'scenario': name, 'command': command, 'exit': code, 'verdicts': verdicts, 'tests': tests,
                'contract_hashes': inventory(app / 'contracts'), 'artifacts_before': artifact_before, 'artifacts_after': artifact_after,
                'packaging_reached': packaging_reached(text), 'missing_ai_artifacts': missing_ai}
        report['scenarios'].append(item)
        (folder / 'artifact-inventory-before.json').write_text(json.dumps(artifact_before, indent=2))
        (folder / 'artifact-inventory-after.json').write_text(json.dumps(artifact_after, indent=2))
        require(code == expected, f'{name}: expected {expected}, got {code}; see {log_path}')
        if expected:
            require(verdicts == {'iems.accessibility': 'PASS', 'iems.enrollment': 'FAIL'}, 'Unexpected fail-fast results')
            assert_no_packaging(artifact_before, artifact_after, text)
            item['not_evaluated'] = ['iems.notification', 'iems.scholarship']
        elif profile:
            require(verdicts == {f'iems.{n}': 'PASS' for n in ('accessibility', 'enrollment', 'notification', 'scholarship')}, 'Expected four PASS reports')
            if phase == 'verify':
                require(bool(artifact_after) and item['packaging_reached'], 'Successful verify did not package')
        else:
            require(not verdicts and 'contract-maven-plugin:' not in text, 'Gate ran without opt-in profile')
        print(f'{name}: Maven exit {code}, {verdicts or "gate inactive"}', flush=True)

    def copy_app(parent, name):
        app = parent / name
        app.mkdir()
        shutil.copyfile(ROOT / 'pom.xml', app / 'pom.xml')
        # The runtime starter tests load the separate, event-specific schema.
        # Keep the disposable Maven project faithful to the current IEMS tree.
        for directory in ('src', 'contracts', 'runtime-contracts'):
            shutil.copytree(ROOT / directory, app / directory)
        return app

    try:
        with tempfile.TemporaryDirectory(prefix='iems-maven-gate-') as directory:
            temporary = Path(directory)
            build(copy_app(temporary, 'compatible'), 'compatible')
            build(copy_app(temporary, 'normal'), 'profile-off', profile=False)
            for label, names in [('single', ['iems.enrollment']), ('multiple', ['iems.enrollment', 'iems.scholarship'])]:
                app = copy_app(temporary, label)
                before = inventory(app / 'contracts')
                try:
                    with breaking(app, names):
                        build(app, label + '-breaking', expected=1)
                finally:
                    require(inventory(app / 'contracts') == before, 'Candidate reset not exact')
                    report[label + '_reset_exact'] = True
                build(app, label + '-recovery')
            app = copy_app(temporary, 'missing-ai')
            build(app, 'missing-ai-compatible', phase='validate', missing_ai=True)
            with breaking(app, ['iems.enrollment']):
                build(app, 'missing-ai-breaking', expected=1, phase='validate', missing_ai=True)
            report['missing_ai_reset_exact'] = inventory(app / 'contracts') == preserved['contracts']
        report['temporary_projects_removed'] = not Path(directory).exists()
        report['result'] = 'PASS'
    except BaseException as error:
        report['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        finished.set()
        watcher.join(timeout=10)
        report['rust_or_iems_startup_observations'] = observations
        report['rust_after'] = rust_processes()
        for name, path in [('contracts', ROOT / 'contracts'), ('package', package), ('rc', original_rc)]:
            report[name + '_unchanged'] = inventory(path) == preserved[name]
        if observations or report['rust_after'] or not all(report[n + '_unchanged'] for n in preserved):
            report['result'] = 'INCOMPLETE'
        (evidence / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
        for path in evidence.rglob('*'):
            path.chmod(0o700 if path.is_dir() else 0o600)
    require(report['result'] == 'PASS', 'Preservation/process checks failed')
    print(f'PASS: {evidence / "results.json"}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--repository', type=Path, default=ROOT / '.dcg/maven-repository')
    parser.add_argument('--ai-requested', action='store_true',
                        help='Run the same deterministic Maven gate with DCG_AI_ENABLED=true')
    args = parser.parse_args()
    os.umask(0o077)
    require(bool(os.environ.get('DCG_HOME')), 'Set DCG_HOME to the verified development package')
    def interrupted(signum, frame):
        raise InterruptedError(f'Signal {signum}; resetting disposable candidates')
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, interrupted)
    run(args.evidence.resolve(), args.repository.resolve(), Path(os.environ['DCG_HOME']).resolve(),
        ai_requested=args.ai_requested)


if __name__ == '__main__':
    main()
