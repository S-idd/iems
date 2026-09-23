#!/usr/bin/env python3
"""Run isolated PostgreSQL and MySQL IEMS/DCG acceptance with private evidence."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time

DCG_SCRIPTS = Path(__file__).resolve().parents[1] / 'dcg'
sys.path.insert(0, str(DCG_SCRIPTS))

import phase1_integrated_demo as p1
from dcg_package import PHASE1_CAPABILITIES, validate_package
from multiple_contract_demo import ROOT, inventory, require, rust_processes, sha, stop_child


REHEARSALS = ROOT / '.dcg/rehearsals'
JAR = ROOT / 'target/inclusive-education-management-system-1.0.0-SNAPSHOT.jar'
ENGINES = ('postgres', 'mysql')
FROZEN_LINUX_RESULT_SHA256 = 'd623e89c9ce9e5463f4eff6d97034c547816c16617f8a83cf976b3b099be1d55'
FROZEN_ARCHIVE_SHA256 = '5ec42c1c412b1ccf4fb650991ffae81804d80c08c3e77388002167cbcc8349bc'


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    path.chmod(0o600)


def prepare(evidence: Path) -> Path:
    root = REHEARSALS.resolve()
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    require(evidence.absolute().parent.resolve() == root and evidence.name.startswith('database-matrix-'),
            'Evidence must be a new database-matrix-* directory under .dcg/rehearsals')
    evidence.mkdir(mode=0o700, exist_ok=False)
    (evidence / '.database-matrix-marker').write_text('PostgreSQL/MySQL acceptance\n')
    return evidence.resolve()


def docker(*args: str, input_text: str | None = None, expected: int = 0,
           timeout: int = 120) -> subprocess.CompletedProcess:
    done = subprocess.run(['docker', *args], input=input_text, capture_output=True,
                          text=True, timeout=timeout)
    require(done.returncode == expected,
            f'Docker {args[0]} failed with exit {done.returncode}: {(done.stderr or done.stdout).strip()}')
    return done


def verify_container_engine() -> None:
    require(shutil.which('docker'), 'Docker-compatible CLI is required')
    # Plain `info` works with Docker and Podman's docker CLI emulation. Docker's
    # .ServerVersion template field is not present in Podman's info report.
    docker('info', timeout=30)


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def active_containers(evidence: Path, records: list[dict]) -> None:
    write_json(evidence / 'active-containers.json', records)


def cleanup_containers(evidence: Path) -> bool:
    marker = evidence / 'active-containers.json'
    if not marker.exists():
        return True
    records = json.loads(marker.read_text())
    label = evidence.name
    for record in reversed(records):
        found = subprocess.run(['docker', 'inspect', '--format',
            '{{ index .Config.Labels "iems.dcg.acceptance" }}', record['name']],
            capture_output=True, text=True)
        if found.returncode != 0:
            continue
        require(found.stdout.strip() == label, 'Recorded container ownership label changed; refusing removal')
        docker('rm', '-f', record['name'], timeout=60)
    marker.unlink(missing_ok=True)
    return True


def wait_database(engine: str, name: str, timeout: int = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if engine == 'postgres':
            done = subprocess.run(['docker', 'exec', name, 'pg_isready', '-U', 'postgres', '-d', 'postgres'],
                                  capture_output=True, text=True)
        else:
            done = subprocess.run(['docker', 'exec', name, 'sh', '-c',
                'mysqladmin ping -uroot --password="$MYSQL_ROOT_PASSWORD" --silent'],
                capture_output=True, text=True)
        if done.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError(f'{engine} container did not become ready')


def start_database(engine: str, image: str, evidence: Path, records: list[dict]) -> dict:
    suffix = secrets.token_hex(5)
    name = f'iems-dcg-{engine}-{suffix}'
    port = free_port()
    root_password = secrets.token_hex(24)
    iems_password = secrets.token_hex(24)
    dcg_password = secrets.token_hex(24)
    iems_db, dcg_db = f'iems_{suffix}', f'dcg_{suffix}'
    iems_user, dcg_user = f'iu_{suffix}', f'du_{suffix}'
    env_file = evidence / f'.{engine}-container.env'
    if engine == 'postgres':
        env_file.write_text(f'POSTGRES_PASSWORD={root_password}\nPOSTGRES_USER=postgres\nPOSTGRES_DB=postgres\n')
        container_port = '5432'
    else:
        env_file.write_text(f'MYSQL_ROOT_PASSWORD={root_password}\n')
        container_port = '3306'
    env_file.chmod(0o600)
    try:
        docker('run', '-d', '--rm', '--name', name,
               '--label', f'iems.dcg.acceptance={evidence.name}',
               '--env-file', str(env_file), '-p', f'127.0.0.1:{port}:{container_port}', image,
               timeout=300)
    finally:
        env_file.unlink(missing_ok=True)
    record = {'name': name, 'engine': engine, 'image': image, 'port': port}
    records.append(record)
    active_containers(evidence, records)
    wait_database(engine, name)
    if engine == 'postgres':
        setup = (f"CREATE USER {iems_user} WITH PASSWORD '{iems_password}';\n"
                 f"CREATE USER {dcg_user} WITH PASSWORD '{dcg_password}';\n"
                 f"CREATE DATABASE {iems_db} OWNER {iems_user};\n"
                 f"CREATE DATABASE {dcg_db} OWNER {dcg_user};\n")
        docker('exec', '-i', name, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', 'postgres', '-d', 'postgres',
               input_text=setup)
        iems_url = f'jdbc:postgresql://127.0.0.1:{port}/{iems_db}'
        dcg_url = f'jdbc:postgresql://127.0.0.1:{port}/{dcg_db}'
    else:
        setup = (f"CREATE DATABASE `{iems_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;\n"
                 f"CREATE DATABASE `{dcg_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;\n"
                 f"CREATE USER '{iems_user}'@'%' IDENTIFIED BY '{iems_password}';\n"
                 f"CREATE USER '{dcg_user}'@'%' IDENTIFIED BY '{dcg_password}';\n"
                 f"GRANT ALL PRIVILEGES ON `{iems_db}`.* TO '{iems_user}'@'%';\n"
                 f"GRANT ALL PRIVILEGES ON `{dcg_db}`.* TO '{dcg_user}'@'%';\nFLUSH PRIVILEGES;\n")
        docker('exec', '-i', name, 'sh', '-c',
               'exec mysql -uroot --password="$MYSQL_ROOT_PASSWORD"', input_text=setup)
        options = '?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC'
        iems_url = f'jdbc:mysql://127.0.0.1:{port}/{iems_db}{options}'
        dcg_url = f'jdbc:mysql://127.0.0.1:{port}/{dcg_db}{options}'
    image_id = docker('image', 'inspect', '--format', '{{.Id}}', image).stdout.strip()
    return {'container': name, 'port': port, 'image': image, 'imageId': image_id,
            'iemsUrl': iems_url, 'iemsUser': iems_user, 'iemsPassword': iems_password,
            'dcgUrl': dcg_url, 'dcgUser': dcg_user, 'dcgPassword': dcg_password}


def tool_command(package: Path) -> list[str]:
    build = json.loads((package / 'build-info.json').read_text())
    cli = next(name for name in build['artifacts'] if name.startswith('lib/contract-cli-'))
    java = str(Path(os.environ['JAVA_HOME']) / 'bin/java')
    return [java, '--class-path', str(package / cli), str(ROOT / 'scripts/database/DatabaseTool.java')]


def run_tool(package: Path, env: dict, *args: str, timeout: int = 45) -> None:
    done = subprocess.run([*tool_command(package), *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=timeout)
    require(done.returncode == 0, f'Database tool {args[0]} failed: {(done.stderr or done.stdout).strip()}')


def validate_history(rows: list[dict]) -> dict:
    counts = Counter((row.get('contractId'), row.get('status')) for row in rows)
    expected = Counter({
        ('iems.accessibility', 'PASS'): 1,
        ('iems.enrollment', 'PASS'): 2,
        ('iems.enrollment', 'FAIL'): 1,
        ('iems.notification', 'PASS'): 1,
        ('iems.scholarship', 'PASS'): 1,
    })
    require(counts == expected, f'Unexpected DCG JDBC history: {dict(counts)}')
    return {f'{contract}:{status}': count for (contract, status), count in sorted(counts.items())}


def run_engine(engine: str, image: str, evidence: Path, package: Path,
               records: list[dict], used_ports: set[int]) -> dict:
    engine_dir = evidence / engine
    engine_dir.mkdir(mode=0o700)
    database = start_database(engine, image, evidence, records)
    app_port = p1.available_port(used_ports)
    env = dict(os.environ, DCG_HOME=str(package), DCG_AI_ENABLED='false',
               SHADOW_INFERENCE_ENABLED='false', IEMS_PORT=str(app_port),
               IEMS_JDBC_URL=database['iemsUrl'], IEMS_DB_USER=database['iemsUser'],
               IEMS_DB_PASSWORD=database['iemsPassword'], IEMS_JWT_SECRET=secrets.token_hex(40),
               IEMS_DEMO_ADMIN_PASSWORD=secrets.token_hex(24), GIT_DIR=str(ROOT / '.git'),
               DCG_SCHEMA_GATE_HISTORY=str(engine_dir / 'schema-gate-history.sqlite'))
    prefix = 'DCG_POSTGRES' if engine == 'postgres' else 'DCG_MYSQL'
    env[f'{prefix}_JDBC_URL'] = database['dcgUrl']
    env[f'{prefix}_USER'] = database['dcgUser']
    env[f'{prefix}_PASSWORD'] = database['dcgPassword']
    env['PATH'] = str(Path(env['JAVA_HOME']) / 'bin') + ':' + env.get('PATH', '')
    process = None
    app_log = engine_dir / 'iems.log'
    commands: list[dict] = []
    try:
        argv = [str(ROOT / 'scripts/database/run_demo.sh'), engine]
        with app_log.open('w') as output:
            process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=output, stderr=output,
                                       start_new_session=True)
        p1.active_marker(evidence, process, str(JAR), f'{engine}-iems', app_port)
        p1.health_200(app_port, process, timeout=150)
        run_tool(package, env, 'seed-notification')
        newman = subprocess.run(['node', str(ROOT / 'scripts/postman/run_iems_integrated_collection.js'),
                                 f'http://127.0.0.1:{app_port}'], cwd=ROOT, env=env,
                                capture_output=True, text=True, timeout=240)
        (engine_dir / 'newman.log').write_text(newman.stdout + newman.stderr)
        require(newman.returncode == 0, f'{engine} Newman failed; inspect private log')
        marker = [line.removeprefix('IEMS_INTEGRATED_SUMMARY=') for line in newman.stdout.splitlines()
                  if line.startswith('IEMS_INTEGRATED_SUMMARY=')]
        require(len(marker) == 1, f'{engine} Newman summary missing')
        api = json.loads(marker[0])
        require(api['failures'] == 0 and api['requests'] == 55 and api['assertions'] == 107,
                f'{engine} endpoint count differs from accepted collection')
        commands.append({'stage': 'iems-newman', 'exit': 0, 'log': 'newman.log'})
    finally:
        if process is not None:
            forced = stop_child(process)
            p1.clear_marker(evidence)
            require(not forced and p1.port_released(app_port), f'{engine} IEMS did not stop cleanly')

    demo = subprocess.run([str(ROOT / 'scripts/dcg.sh'), 'demo', engine], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=180)
    (engine_dir / 'dcg-demo.log').write_text(demo.stdout + demo.stderr)
    require(demo.returncode == 0, f'{engine} DCG PASS/FAIL demo failed')
    commands.append({'stage': 'dcg-jdbc-history', 'exit': 0, 'log': 'dcg-demo.log'})

    history_path = engine_dir / 'dcg-history.json'
    history_env = dict(env, IEMS_JDBC_URL=database['dcgUrl'],
                       IEMS_DB_USER=database['dcgUser'], IEMS_DB_PASSWORD=database['dcgPassword'])
    run_tool(package, history_env, 'history', str(history_path))
    history_counts = validate_history(json.loads(history_path.read_text()))

    schema_dir = engine_dir / 'schema-gate'
    schema = subprocess.run([sys.executable, str(ROOT / 'scripts/database/schema_gate_demo.py'),
                             '--evidence', str(schema_dir)], cwd=ROOT, env=env,
                            capture_output=True, text=True, timeout=180)
    (engine_dir / 'schema-gate.log').write_text(schema.stdout + schema.stderr)
    require(schema.returncode == 0, f'{engine} physical schema gate failed')
    schema_result = json.loads((schema_dir / 'results.json').read_text())
    require(schema_result['result'] == 'PASS' and schema_result['safeExit'] == 0
            and schema_result['breakingExit'] == 1 and schema_result['targetPreserved']
            and schema_result['tablesRemoved'], f'{engine} schema-gate evidence incomplete')
    commands.append({'stage': 'physical-schema-gate', 'exit': 0, 'log': 'schema-gate.log'})

    result = {'result': 'PASS', 'engine': engine,
              'container': {'image': database['image'], 'imageId': database['imageId'],
                            'hostPort': database['port']},
              'iems': {'healthHttp': 200, 'port': app_port, 'api': api},
              'dcgHistory': {'rows': len(json.loads(history_path.read_text())), 'counts': history_counts},
              'schemaGate': schema_result, 'aiMode': 'DISABLED', 'commands': commands}
    write_json(engine_dir / 'results.json', result)
    return result


def cleanup(evidence: Path) -> None:
    evidence = evidence.resolve()
    require((evidence / '.database-matrix-marker').is_file(), 'Not database-matrix evidence')
    require(p1.stop_recorded_process(evidence), 'Recorded IEMS process did not stop')
    require(cleanup_containers(evidence), 'Recorded database containers did not stop')
    write_json(evidence / 'manual-cleanup.json', {'result': 'PASS'})


def run(args: argparse.Namespace) -> int:
    package = Path(validate_package(args.dcg_home, required_capabilities=PHASE1_CAPABILITIES)['path'])
    verify_container_engine()
    require(JAR.is_file(), 'Build the IEMS JAR before acceptance')
    require((ROOT / '.dcg/tools/node_modules/newman').is_dir(), 'Install local Newman before acceptance')
    require(not rust_processes(), 'Stop the Rust model before deterministic database acceptance')
    evidence = prepare(args.evidence)
    source_before = inventory(ROOT / 'contracts')
    package_before = inventory(package)
    normal = ROOT / '.dcg/data/iems.db'
    normal_before = (normal.exists(), sha(normal.read_bytes()) if normal.exists() else None)
    report = {'phase': 'postgresql-mysql-acceptance', 'result': 'INCOMPLETE',
              'frozenLinuxMilestone': {'resultSha256': FROZEN_LINUX_RESULT_SHA256,
                                       'archiveSha256': FROZEN_ARCHIVE_SHA256,
                                       'baseCommit': 'e4726a752045720f99f8ff6214a7404918a1dc21',
                                       'referenceOnly': True},
              'engines': {}, 'preservation': {}, 'cleanup': {}}
    records: list[dict] = []
    used_ports: set[int] = set()
    try:
        report['engines']['postgres'] = run_engine('postgres', args.postgres_image, evidence,
                                                   package, records, used_ports)
        report['engines']['mysql'] = run_engine('mysql', args.mysql_image, evidence,
                                                package, records, used_ports)
        report['result'] = 'PASS'
    except BaseException as error:
        report['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        container_cleanup = False
        try:
            container_cleanup = cleanup_containers(evidence)
        except BaseException as cleanup_error:
            report['cleanupError'] = f'{type(cleanup_error).__name__}: {cleanup_error}'
        normal_after = (normal.exists(), sha(normal.read_bytes()) if normal.exists() else None)
        report['preservation'] = {'sourceContractsUnchanged': inventory(ROOT / 'contracts') == source_before,
            'selectedPackageUnchanged': inventory(package) == package_before,
            'normalSqliteDatabaseUnchanged': normal_before == normal_after,
            'frozenLinuxMilestoneNotAccessed': True}
        report['cleanup'] = {'containersRemoved': container_cleanup,
            'activeContainerMarkerRemoved': not (evidence / 'active-containers.json').exists(),
            'activeProcessMarkerRemoved': not (evidence / 'active-process.json').exists(),
            'applicationPortsReleased': all(p1.port_released(p) for p in used_ports),
            'rustProcessesAfter': rust_processes()}
        if not (all(report['preservation'].values()) and all(v is True for k, v in report['cleanup'].items()
                if k != 'rustProcessesAfter') and not report['cleanup']['rustProcessesAfter']):
            report['result'] = 'INCOMPLETE'
        write_json(evidence / 'results.json', report)
    require(report['result'] == 'PASS' and set(report['engines']) == set(ENGINES),
            'Database matrix acceptance incomplete')
    print(f'PASS: {evidence / "results.json"}')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--dcg-home', type=Path)
    parser.add_argument('--postgres-image', default='postgres:16')
    parser.add_argument('--mysql-image', default='mysql:8.0')
    parser.add_argument('--cleanup', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.cleanup:
            cleanup(args.evidence)
            return 0
        require(args.dcg_home is not None, '--dcg-home is required')
        return run(args)
    except Exception as error:
        print(f'INCOMPLETE: {type(error).__name__}: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
