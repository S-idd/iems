#!/usr/bin/env python3
"""Gate reviewed SQLite DDL for the real IEMS schools table before execution.

This is an isolated rehearsal, not a generic SQL planner or a direct-SQL guard.
Only the two checked-in, exact migration statements are supported.
"""

from __future__ import annotations

import argparse
from contextlib import closing
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
REHEARSALS = ROOT / ".dcg" / "rehearsals"
BASELINE = ROOT / "src/main/resources/db/portable/sqlite/V1__iems_baseline.sql"
FIXTURES = ROOT / "scripts/database/migration_gate_sql"
SAFE_SQL = b"ALTER TABLE schools ADD COLUMN demo_contact_note VARCHAR(200);\n"
BREAKING_SQL = b"ALTER TABLE schools DROP COLUMN name;\n"
TABLE = "schools"
REQUIRED_COLUMN = "name"
OPTIONAL_COLUMN = "demo_contact_note"
SENTINEL = (900001, 1, "2026-09-18T00:00:00", "Gate Rehearsal School")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes())


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def make_evidence(requested: Path | None = None) -> Path:
    REHEARSALS.mkdir(parents=True, exist_ok=True)
    root = REHEARSALS.resolve()
    if requested is None:
        return Path(tempfile.mkdtemp(prefix="database-migration-gate-", dir=root))
    candidate = requested.absolute()
    if candidate.parent.resolve() != root or not candidate.name.startswith("database-migration-gate-"):
        raise ValueError("Evidence must be a new direct child of .dcg/rehearsals")
    candidate.mkdir(mode=0o700, exist_ok=False)
    return candidate


def schools_ddl() -> str:
    """Read the exact schools CREATE TABLE from IEMS's portable SQLite Flyway V1."""
    statements: list[str] = []
    pending = ""
    for line in BASELINE.read_text().splitlines(keepends=True):
        if line.lstrip().startswith("--"):
            continue
        pending += line
        if sqlite3.complete_statement(pending):
            statements.append(pending.strip())
            pending = ""
    if pending.strip():
        raise ValueError("Incomplete SQLite Flyway baseline statement")
    matches = [s for s in statements if re.match(r"(?is)^create\s+table\s+schools\s*\(", s)]
    if len(matches) != 1:
        raise ValueError("Expected exactly one schools table in SQLite Flyway baseline")
    return matches[0]


def table_info(db: Path) -> list[dict[str, object]]:
    with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("PRAGMA table_info(schools)")]


def sentinel(db: Path) -> dict[str, object]:
    with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as conn:
        row = conn.execute("SELECT id, active, created_at, name FROM schools WHERE id=?", (SENTINEL[0],)).fetchone()
        count = conn.execute("SELECT COUNT(*) FROM schools").fetchone()[0]
    return {"row": list(row) if row else None, "rowCount": count}


def initialize_table(db: Path, ddl: str) -> None:
    if db.exists():
        raise FileExistsError(db)
    with closing(sqlite3.connect(db)) as conn:
        with conn:
            conn.execute(ddl)
            conn.execute("INSERT INTO schools (id, active, created_at, name) VALUES (?, ?, ?, ?)", SENTINEL)
    columns = {row["name"]: row for row in table_info(db)}
    if REQUIRED_COLUMN not in columns or columns[REQUIRED_COLUMN]["notnull"] != 1:
        raise ValueError("Flyway schools.name is no longer NOT NULL")
    if sentinel(db) != {"row": list(SENTINEL), "rowCount": 1}:
        raise ValueError("Failed to initialize IEMS schools sentinel")


def freeze_fixture(source: Path, target: Path, expected: bytes) -> str:
    contents = source.read_bytes()
    if contents != expected:
        raise ValueError(f"Reviewed SQL changed: {source.name}")
    target.write_bytes(contents)
    target.chmod(0o400)
    return sha256(contents)


def java_command(package: Path) -> list[str]:
    jar = package / "lib/contract-cli-4.0.0-rc.1-all.jar"
    if not jar.is_file() or not (package / "bin/dcg").is_file():
        raise FileNotFoundError("Set DCG_HOME to the installed verified development package")
    java = str(Path(os.environ["JAVA_HOME"]) / "bin/java") if os.environ.get("JAVA_HOME") else "java"
    return [java, "--class-path", str(jar), str(ROOT / "scripts/database/DatabaseTool.java")]


def db_env(db: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["IEMS_JDBC_URL"] = "jdbc:sqlite:" + str(db.resolve())
    env.pop("IEMS_DB_USER", None)
    env.pop("IEMS_DB_PASSWORD", None)
    env["DCG_AI_ENABLED"] = "false"
    return env


def jdbc_snapshot(command: list[str], db: Path, output: Path) -> dict:
    subprocess.run(command + ["snapshot", TABLE, str(output)], cwd=ROOT, env=db_env(db),
                   check=True, capture_output=True, text=True, timeout=45)
    value = json.loads(output.read_text())
    write_json(output, value)
    return value


def candidate_without_required(base: dict) -> dict:
    """Model the exact reviewed DROP COLUMN without executing destructive SQL."""
    candidate = copy.deepcopy(base)
    if REQUIRED_COLUMN not in candidate["properties"] or REQUIRED_COLUMN not in candidate["required"]:
        raise ValueError("Expected required schools.name in JDBC snapshot")
    del candidate["properties"][REQUIRED_COLUMN]
    candidate["required"].remove(REQUIRED_COLUMN)
    return candidate


def run_gate(package: Path, base: Path, candidate: Path, history: Path, log: Path) -> int:
    command = [str(package / "bin/dcg"), "check-compat", "--base", str(base),
               "--candidate", str(candidate), "--mode", "BACKWARD", "--contract-id",
               "iems.database.schools", "--record-db", str(history),
               "--commit-sha", subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()]
    env = os.environ.copy()
    env["DCG_AI_ENABLED"] = "false"
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    log.write_text(result.stdout + result.stderr)
    return result.returncode


class ObservedExecutor:
    def __init__(self, java: list[str]):
        self.java = java
        self.attempts = 0
        self.log: list[dict[str, object]] = []

    def execute(self, db: Path, sql: Path, reviewed_hash: str) -> None:
        offered_hash = file_hash(sql)
        if offered_hash != reviewed_hash:
            raise ValueError("Migration SQL changed between review and execution")
        self.attempts += 1
        result = subprocess.run(self.java + ["execute", str(sql)], cwd=ROOT, env=db_env(db),
                                capture_output=True, text=True, timeout=45)
        self.log.append({"sqlSha256": offered_hash, "exitCode": result.returncode,
                         "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode != 0:
            raise RuntimeError("Reviewed SQL executor failed; see private observation log")


def check_normal_db_unchanged(before: tuple[bool, str | None]) -> bool:
    normal = ROOT / ".dcg/data/iems.db"
    after = (normal.exists(), file_hash(normal) if normal.exists() else None)
    return before == after


def apply_after_pass(verdict: int, executor: ObservedExecutor, db: Path,
                     sql: Path, reviewed_hash: str) -> bool:
    """The only call site allowed to send reviewed SQL to the target executor."""
    if verdict != 0:
        return False
    executor.execute(db, sql, reviewed_hash)
    return True


def rust_process_observation() -> dict[str, object]:
    result = subprocess.run(["pgrep", "-af", "dcg.*(infer|model)|dcg-ai"],
                            capture_output=True, text=True, timeout=10)
    return {"exitCode": result.returncode, "matches": result.stdout.strip()}


def verify_unlocked(db: Path) -> None:
    with closing(sqlite3.connect(db, timeout=0.5)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("ROLLBACK")


def run_rehearsal(evidence: Path, package: Path) -> dict:
    os.umask(0o077)
    normal = ROOT / ".dcg/data/iems.db"
    normal_before = (normal.exists(), file_hash(normal) if normal.exists() else None)
    rust_before = rust_process_observation()
    if rust_before["matches"]:
        raise RuntimeError("DCG model/Rust process already running; stop it before this no-AI rehearsal")
    java = java_command(package)
    ddl = schools_ddl()
    (evidence / "schools-flyway-ddl.sql").write_text(ddl + "\n")
    safe_sql, breaking_sql = evidence / "safe-migration.sql", evidence / "breaking-migration.sql"
    safe_hash = freeze_fixture(FIXTURES / "safe_add_school_contact_note.sql", safe_sql, SAFE_SQL)
    breaking_hash = freeze_fixture(FIXTURES / "breaking_drop_school_name.sql", breaking_sql, BREAKING_SQL)
    safe_db, breaking_db, proposal_db = (evidence / name for name in
                                         ("safe.sqlite", "breaking.sqlite", "safe-proposal.sqlite"))
    for db in (safe_db, breaking_db, proposal_db):
        initialize_table(db, ddl)
    history = evidence / "dcg-history.sqlite"
    safe_base = evidence / "safe-pre-schema.json"
    safe_proposal = evidence / "safe-candidate-schema.json"
    safe_post = evidence / "safe-post-schema.json"
    breaking_base = evidence / "breaking-pre-schema.json"
    breaking_proposal = evidence / "breaking-candidate-schema.json"
    breaking_post = evidence / "breaking-post-schema.json"

    jdbc_snapshot(java, safe_db, safe_base)
    with closing(sqlite3.connect(proposal_db)) as conn:
        with conn:
            conn.execute(safe_sql.read_text())
    jdbc_snapshot(java, proposal_db, safe_proposal)
    safe_executor = ObservedExecutor(java)
    safe_exit = run_gate(package, safe_base, safe_proposal, history, evidence / "safe-gate.log")
    if safe_exit != 0:
        raise RuntimeError(f"Safe proposal did not PASS DCG gate (exit {safe_exit})")
    if not apply_after_pass(safe_exit, safe_executor, safe_db, safe_sql, safe_hash):
        raise RuntimeError("Safe gate did not call executor")
    jdbc_snapshot(java, safe_db, safe_post)
    safe_columns = {row["name"] for row in table_info(safe_db)}
    if (safe_post.read_bytes() != safe_proposal.read_bytes() or
            OPTIONAL_COLUMN not in safe_columns or REQUIRED_COLUMN not in safe_columns or
            sentinel(safe_db) != {"row": list(SENTINEL), "rowCount": 1}):
        raise RuntimeError("Safe executed schema/data differs from approved proposal")

    jdbc_snapshot(java, breaking_db, breaking_base)
    before_info = table_info(breaking_db)
    before_sentinel = sentinel(breaking_db)
    before_db_hash = file_hash(breaking_db)
    write_json(evidence / "breaking-pre-table-info.json", before_info)
    write_json(evidence / "breaking-pre-sentinel.json", before_sentinel)
    write_json(breaking_proposal, candidate_without_required(json.loads(breaking_base.read_text())))
    breaking_executor = ObservedExecutor(java)
    breaking_exit = run_gate(package, breaking_base, breaking_proposal, history, evidence / "breaking-gate.log")
    if file_hash(breaking_sql) != breaking_hash:
        raise RuntimeError("Breaking proposal SQL changed after review")
    if breaking_exit != 1:
        raise RuntimeError(f"Breaking proposal expected DCG FAIL (1), got {breaking_exit}")
    if apply_after_pass(breaking_exit, breaking_executor, breaking_db, breaking_sql, breaking_hash):
        raise RuntimeError("Breaking SQL unexpectedly reached executor")
    jdbc_snapshot(java, breaking_db, breaking_post)
    after_info = table_info(breaking_db)
    after_sentinel = sentinel(breaking_db)
    after_db_hash = file_hash(breaking_db)
    write_json(evidence / "breaking-post-table-info.json", after_info)
    write_json(evidence / "breaking-post-sentinel.json", after_sentinel)
    if (breaking_executor.attempts != 0 or breaking_executor.log or
            breaking_base.read_bytes() != breaking_post.read_bytes() or
            before_info != after_info or before_sentinel != after_sentinel or
            before_db_hash != after_db_hash or
            REQUIRED_COLUMN not in {row["name"] for row in after_info}):
        raise RuntimeError("Blocked proposal changed the target or reached SQL executor")
    if not check_normal_db_unchanged(normal_before):
        raise RuntimeError("Normal IEMS SQLite database changed during rehearsal")
    for db in (safe_db, breaking_db, proposal_db):
        verify_unlocked(db)
    rust_after = rust_process_observation()
    if rust_after["matches"]:
        raise RuntimeError("DCG model/Rust process observed after no-AI rehearsal")
    write_json(evidence / "executor-observation.json", {
        "safe": {"attempts": safe_executor.attempts, "statements": safe_executor.log},
        "breaking": {"attempts": breaking_executor.attempts, "statements": breaking_executor.log},
    })
    result = {
        "result": "COMPLETE", "table": TABLE, "requiredColumn": REQUIRED_COLUMN,
        "optionalColumn": OPTIONAL_COLUMN, "baselineSource": str(BASELINE),
        "baselineSourceSha256": file_hash(BASELINE), "creationPath": "IEMS portable SQLite Flyway V1 schools CREATE TABLE",
        "databasePaths": {"safe": str(safe_db), "breaking": str(breaking_db), "safeProposal": str(proposal_db)},
        "normalIemsDatabaseUntouched": True, "normalIemsDatabaseExisted": normal_before[0],
        "normalIemsDatabasePath": str(normal),
        "normalIemsDatabaseSha256Before": normal_before[1],
        "normalIemsDatabaseSha256After": file_hash(normal) if normal.exists() else None,
        "safe": {"sqlSha256": safe_hash, "reviewedSqlSha256": safe_hash,
                 "offeredSqlSha256": safe_executor.log[0]["sqlSha256"], "gateExitCode": safe_exit,
                 "gateVerdict": "PASS", "executorAttempts": safe_executor.attempts,
                 "preSchemaSha256": file_hash(safe_base), "candidateSchemaSha256": file_hash(safe_proposal),
                 "postSchemaSha256": file_hash(safe_post), "executorExitCode": safe_executor.log[0]["exitCode"],
                 "optionalColumnPresent": True,
                 "requiredColumnPresent": True, "sentinelPreserved": True},
        "breaking": {"sqlSha256": breaking_hash, "gateExitCode": breaking_exit,
                     "gateVerdict": "FAIL", "executorAttempts": breaking_executor.attempts,
                     "preSchemaSha256": file_hash(breaking_base),
                     "candidateSchemaSha256": file_hash(breaking_proposal),
                     "postSchemaSha256": file_hash(breaking_post),
                     "preDatabaseSha256": before_db_hash, "postDatabaseSha256": after_db_hash,
                     "requiredColumnPresent": True, "sentinelPreserved": before_sentinel == after_sentinel,
                     "tableInfoUnchanged": before_info == after_info},
        "aiDisabled": True, "rustStarted": False,
        "rustProcessObservation": {"before": rust_before, "after": rust_after},
        "cleanup": {"childProcessesRemaining": False, "databaseConnectionsClosed": True,
                    "evidenceRetained": True},
        "limitations": ["SQLite only", "JDBC snapshot compares column names, coarse types and nullability only",
                        "Direct SQL outside this runner bypasses the gate", "This runner does not invoke Flyway itself"],
    }
    write_json(evidence / "results.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, help="new directory directly under .dcg/rehearsals")
    args = parser.parse_args()
    evidence = make_evidence(args.evidence)
    try:
        package = Path(os.environ.get("DCG_HOME", ROOT / ".dcg/runtime/dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64"))
        result = run_rehearsal(evidence, package)
        print(json.dumps({"result": result["result"], "evidence": str(evidence),
                          "safe": result["safe"]["gateVerdict"],
                          "breaking": result["breaking"]["gateVerdict"]}))
        return 0
    except Exception as exc:
        (evidence / "error.txt").write_text(f"{type(exc).__name__}: {exc}\n")
        print(f"INCOMPLETE: {exc}; private evidence: {evidence}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
