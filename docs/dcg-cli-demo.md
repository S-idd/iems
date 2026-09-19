# IEMS DCG binary CLI demo

This integration runs the packaged DCG 4.0.0-rc.1 CLI against IEMS event
contracts and records check history in SQLite, PostgreSQL or MySQL. It needs
Java 21 and Bash; no DCG source build, Maven, Docker, server or Rust inference
process is needed. IEMS application storage remains PostgreSQL.

## Install once

From the IEMS repository root:

```bash
./scripts/dcg/install.sh /absolute/path/to/dcg-4.0.0-rc.1-macos-arm64.tar.gz
# Linux x64: supply dcg-4.0.0-rc.1-linux-x64.tar.gz instead.
./scripts/dcg.sh cli --help
```

The installer checks a pinned archive SHA-256 and all payload checksums before
installing under ignored `.dcg/runtime`. The pins identify the current local
release candidate; a new artifact requires explicit review and updated pins.
Alternatively export `DCG_HOME=/absolute/path/to/extracted/dcg-package`.
An externally supplied DCG_HOME is trusted by the caller and is not verified by
the wrapper. The upstream package remains an unpublished release candidate.

## Rehearse immediately with SQLite

```bash
./scripts/dcg.sh lint
./scripts/dcg.sh check sqlite
./scripts/dcg.sh demo sqlite
```

`check` compares every `contracts/iems.*/v1.json` with its `candidate.json`.
Candidates initially match the baseline. Edit a candidate to propose a change;
keep v1 as the review baseline. The four contracts cover enrollment, scholarship,
accessibility and notification events. Fields follow the Java event classes and
notification map in `EventPublisherService`. These are manually maintained
structural contracts, not generated schemas or runtime payload validation.
Required-field guarantees and timestamp serialization are not imposed in this
initial demo because IEMS does not yet enforce those consistently at publishing.
Do not treat the schemas as exhaustive descriptions of nullable runtime payloads.

`demo` uses separate enrollment fixtures: adding optional `sourceSystem` passes;
changing `studentId` from integer to string fails. Both results are recorded.
It succeeds only when the real binary returns exactly 0 then 1; a persistence
failure (2) fails the rehearsal. Demo fixtures never replace the candidates.

SQLite history defaults to `.dcg/data/checks.db`. Override with
`DCG_SQLITE_PATH=/absolute/path/to/checks.db`. Binary installs, history, local
service test data and credentials are ignored by Git.

## PostgreSQL and MySQL

Provision an empty, dedicated database named `iems_dcg_demo` on each local
server and a user with permission to create/alter DCG tables and write history.
**Do not point recording at the IEMS application database.** The binary applies
its own Flyway migrations and owns its `flyway_schema_history` table.

Export the connection settings in your shell, using your existing credentials:

```bash
export DCG_POSTGRES_JDBC_URL='jdbc:postgresql://127.0.0.1:5432/iems_dcg_demo'
export DCG_POSTGRES_USER='dcg_demo'
read -r -s -p 'PostgreSQL password: ' DCG_POSTGRES_PASSWORD; echo
export DCG_POSTGRES_PASSWORD
./scripts/dcg.sh check postgres
./scripts/dcg.sh demo postgres

export DCG_MYSQL_JDBC_URL='jdbc:mysql://127.0.0.1:3306/iems_dcg_demo'
export DCG_MYSQL_USER='dcg_demo'
read -r -s -p 'MySQL password: ' DCG_MYSQL_PASSWORD; echo
export DCG_MYSQL_PASSWORD
./scripts/dcg.sh check mysql
./scripts/dcg.sh demo mysql

./scripts/dcg.sh demo-all
```

These password prompts use Bash syntax; run them in `bash` on macOS.
Credentials reach DCG through environment variable names, not command-line
password arguments. The wrapper does not source `.env` files. Use JDBC options
appropriate to your server's authentication/TLS configuration; no TLS settings
are disabled by default.

## Inspect history and use as a gate

Run this SQL using your normal client on the selected history database:

```sql
SELECT contract_id, base_version, candidate_version, status, commit_sha
FROM check_runs
ORDER BY created_at DESC;
```

The recorded commit SHA identifies the current IEMS checkout; uncommitted schema
edits are not represented by that SHA. Commit reviewed candidates before using
history as release evidence.

```bash
# An explicit build gate using the installed binary:
./scripts/dcg.sh lint && ./scripts/dcg.sh check sqlite && mvn verify
# Raw CLI remains available; arguments pass through unchanged:
./scripts/dcg.sh cli diff --base contracts/iems.enrollment/v1.json \
  --candidate scripts/dcg/fixtures/breaking.json
```

Normal checks preserve exit 0 (PASS), 1 (incompatible) and 2 (execution or
persistence error). `check` processes all contracts and returns the highest exit
code. `demo-all` validates all three configurations first, then stops if a store
fails. The database demo launcher now invokes lint and check before starting IEMS.
CI and event publishing do not currently invoke this gate.

## Verification

```bash
python3 scripts/dcg/test_cli.py
```

Tests execute the installed binary against temporary SQLite history and verify
stored results, breaking exit codes, persistence errors, missing server settings,
and invocation from outside the repository (including paths containing spaces).

Local acceptance on 2026-09-17: verified archive and payload checksums; all four
contracts linted and passed; enrollment PASS and FAIL rows were queried in SQLite,
PostgreSQL 18.3 and MySQL 8.0.46. Server tests used isolated local data directories
and ports 55439/53369, not the IEMS database. Those test instances were stopped
after verification. Logs remain in ignored `.dcg/test-services/`.
