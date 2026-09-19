# IEMS + DCG local database and AI demo

This demo runs IEMS against **one of SQLite, PostgreSQL, or MySQL at a time**.
The packaged DCG CLI checks four IEMS event contracts before the app starts and
records results in a **separate DCG history database** on the same engine. A
verified Rust binary provides advisory schema predictions. Java 21, Maven,
Python 3, and the [installed DCG binary](dcg-cli-demo.md) are required. No DCG
source build or container runtime is needed.

## What runs where

| Component | SQLite | PostgreSQL | MySQL |
| --- | --- | --- | --- |
| IEMS data | `.dcg/data/iems.db` | fresh IEMS database | fresh IEMS database |
| DCG check history | `.dcg/data/checks.db` | separate DCG database | separate DCG database |
| IEMS schema | `db/portable/sqlite` | `db/portable/postgres` | `db/portable/mysql` |
| DCG CLI and AI model | packaged release binary | same binary | same binary |

The portable Flyway baseline contains IEMS's current entity schema, including
school code and district. It is for **fresh demo databases**. Existing IEMS
PostgreSQL databases retain their original migration history under
`db/migration`, including V14. Do not change an existing application's Flyway
location to the portable baseline. IEMS uses Hibernate `validate`, so Hibernate
cannot create or alter its tables at runtime. The demo profiles disable broker
listeners and publishing, email delivery, and Redis caching so the database/API path can run
locally without those services. This does not test event delivery.

## Start SQLite

From the IEMS root, after installing the DCG binary:

```bash
mvn -DskipTests package
export IEMS_JWT_SECRET="$(openssl rand -hex 32)"
export IEMS_DEMO_ADMIN_PASSWORD="$(openssl rand -base64 30)"
./scripts/database/run_demo.sh sqlite
```

The startup script lints/contracts checks with the DCG binary, applies the
approved Flyway baseline to the IEMS database, validates it, and starts the API
at `http://127.0.0.1:8090`. In another terminal use the same admin password:

```bash
IEMS_DEMO_ADMIN_PASSWORD="$IEMS_DEMO_ADMIN_PASSWORD" python3 scripts/database/api_smoke.py
```

The smoke script logs in as the local `demo-admin`, registers sample users,
then exercises school, student, scholarship and accessibility API flows. It
soft-deletes the school at the end. The demo
admin is seeded only when the fresh IEMS database has no users. The password is
supplied by the operator through an environment variable; the app never prints
it. Keep the terminal session and local `.dcg/` state private. Stop the app with
Ctrl-C before switching databases; all profiles use port 8090.

## Start PostgreSQL or MySQL

Create **two empty databases per engine**, one for IEMS and one for DCG history.
Grant each user ownership/DDL permissions on its own database only. The IEMS
user must be able to run Flyway's baseline migration. These commands show the
required environment variables; choose your own database names and passwords.

PostgreSQL:

```bash
export IEMS_JDBC_URL='jdbc:postgresql://127.0.0.1:5432/iems_demo'
export IEMS_DB_USER='iems_demo'
export IEMS_DB_PASSWORD='<IEMS database password>'
export DCG_POSTGRES_JDBC_URL='jdbc:postgresql://127.0.0.1:5432/iems_dcg_demo'
export DCG_POSTGRES_USER='dcg_demo'
export DCG_POSTGRES_PASSWORD='<DCG database password>'
./scripts/database/run_demo.sh postgres
```

MySQL 8 with a `utf8mb4_0900_ai_ci` database collation:

```bash
export IEMS_JDBC_URL='jdbc:mysql://127.0.0.1:3306/iems_demo'
export IEMS_DB_USER='iems_demo'
export IEMS_DB_PASSWORD='<IEMS database password>'
export DCG_MYSQL_JDBC_URL='jdbc:mysql://127.0.0.1:3306/iems_dcg_demo'
export DCG_MYSQL_USER='dcg_demo'
export DCG_MYSQL_PASSWORD='<DCG database password>'
./scripts/database/run_demo.sh mysql
```

Use suitable TLS/JDBC options for your own server. The application and history
users should not share a database: their Flyway histories are independent.
`run_demo.sh` requires the DCG CLI check to pass before the app starts. It does
not put passwords on the DCG command line. Set `IEMS_JWT_SECRET` and
`IEMS_DEMO_ADMIN_PASSWORD` as shown for SQLite in the same shell.

For a direct API check while the app runs:

```bash
python3 scripts/database/api_smoke.py
```

## Show how a schema change gets blocked

Use only a disposable local database for this rehearsal. Set the `IEMS_JDBC_URL`
and server credentials for that database, or use this SQLite shortcut:

```bash
export IEMS_JDBC_URL="jdbc:sqlite:$PWD/.dcg/data/schema-demo.db"
python3 scripts/database/schema_gate_demo.py
```

The script creates two uniquely named temporary tables and records actual JDBC
schema snapshots. It proposes `website` as an optional column; DCG returns PASS
and the wrapped `ALTER TABLE` runs. It then proposes removing required `name`;
DCG returns FAIL (exit 1), so the wrapped SQL never executes. It reads the
live table again and verifies `name` is still present. The script removes its
own temporary tables, retains snapshots under `.dcg/schema-demo/`, and records
gate outcomes in `.dcg/data/schema-gates.db`.

The general gate is:

```bash
./scripts/dcg/gate.sh BASE.json CANDIDATE.json -- your-migration-command arguments
```

Use it with snapshots of the **same database engine** and a candidate built in
an isolated scratch database. The passed command must apply exactly the reviewed
candidate; the wrapper cannot prove arbitrary commands match the snapshot.
Protect the migration operation in CI/deployment by invoking it only through
this gate. Direct SQL or an out-of-band tool can still change the database.

The demo app has an additional startup check: before Flyway runs, it verifies
every portable migration's SHA-256 against
`src/main/resources/db/portable/approved.sha256` and rejects added, missing or
modified files. This keeps an unreviewed migration from running in the demo
profiles. The approval manifest is a review control, not a signature or an
access-control boundary. To approve a planned migration, first use the DCG
schema gate against a scratch database, review the SQL and snapshots, then
update the manifest in the same reviewed change. Existing versioned migrations
remain subject to Flyway's own checksum validation.

## Show the AI model

```bash
python3 scripts/dcg/ai_demo.py
```

This starts the packaged Rust binary on a temporary loopback port, sends IEMS
`enrollment` compatible and breaking schema pairs, prints the three model seed
labels/probabilities beside the authoritative DCG CLI result, saves
`.dcg/ai-demo/results.json`, then stops the model. In the verified run, the
compatible addition received three `SAFE` predictions and the `studentId`
integer-to-string change received three `BREAKING` predictions. The model is
**advisory**; the deterministic DCG check decides PASS/FAIL and controls the
gate. A model outage or disagreement does not approve a breaking change.

## Local verification performed

On 2026-09-17, the school, student, scholarship and accessibility API smoke passed against
SQLite 3.43, PostgreSQL 18.3 and MySQL 8.0.46 using isolated local databases. The DCG gate accepted and
blocked the intended SQL on all three engines, and the Rust model produced
predictions for both cases. Ten JUnit tests passed, including one
that injects an unapproved migration and confirms startup approval rejects it.
