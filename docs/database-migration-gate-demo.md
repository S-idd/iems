# Physical IEMS migration gate (Phase 1)

This rehearsal governs the real `schools` table from IEMS's portable SQLite
Flyway V1 baseline (`src/main/resources/db/portable/sqlite/V1__iems_baseline.sql`).
The runner extracts that exact `CREATE TABLE schools` statement into fresh
private SQLite files and inserts one sentinel school. `schools.name` is a real
`NOT NULL` application field. The safe proposal adds nullable
`demo_contact_note VARCHAR(200)`; the breaking proposal would drop `name`.
Neither proposal changes an approved schema baseline or the normal IEMS DB.

The boundary is: live JDBC snapshot using the existing `DatabaseTool.java`
format → official packaged DCG CLI `check-compat --mode BACKWARD` → observed
SQLite SQL executor **only on exit 0**. The target executor receives the
reviewed SQL file after its SHA-256 is checked again. For the safe proposal,
the same SQL is first applied to a separate disposable candidate DB to obtain
the actual proposed schema. For the breaking proposal, the expected candidate
snapshot removes the known `name` field; the destructive SQL is never run,
even in the scratch DB. DCG alone decides compatibility. This narrow runner
supports only the two checked-in, exact SQL statements, not arbitrary DDL.

Run from the IEMS repository root:

```sh
cd /absolute/path/to/iems
export DCG_HOME="$PWD/.dcg/runtime/dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64"
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home
DCG_AI_ENABLED=false python3 scripts/database/iems_migration_gate.py
DCG_AI_ENABLED=false python3 -m unittest discover -s scripts/database \
  -p 'test_iems_migration_gate.py' -v
```

Each invocation creates a private, non-overwritable
`.dcg/rehearsals/database-migration-gate-*/` directory. The runner accepts no
database URL: it creates `safe.sqlite`, `breaking.sqlite`, and a safe proposal
DB only inside that new directory, and overrides any inherited
`IEMS_JDBC_URL`. A path outside the rehearsal root or an existing evidence
directory is rejected. It records the normal default `.dcg/data/iems.db`
file's hash before/after without connecting to it. The evidence directory has
owner-only access; no credentials or environment dumps are retained.

Expected presenter proof:

| Proposal | DCG output | Target executor | Physical result |
| --- | --- | ---: | --- |
| `ALTER TABLE schools ADD COLUMN demo_contact_note VARCHAR(200);` | PASS | 1 call | New nullable column, `name` and sentinel row remain |
| `ALTER TABLE schools DROP COLUMN name;` | FAIL, `Field removed: name` | 0 calls | Exact same snapshot and DB hash; `name` and sentinel row remain |

Open `safe-gate.log`, `breaking-gate.log`, `executor-observation.json`, the
pre/post schema JSON and `PRAGMA table_info` JSON, then `results.json` in the
private evidence directory. The breaking executor observation has an empty
statement list, and both the pre/post schema SHA-256 and database-file SHA-256
are equal. The SQL hash offered to the safe executor equals the reviewed hash.
Multiple fresh final-script/test rehearsals are retained. The consolidated
evidence and test logs are at
`.dcg/rehearsals/database-migration-gate-abn5gzgy/`; an independent fresh
rehearsal is at `.dcg/rehearsals/database-migration-gate-twy37c10/`.

Presenter wording: “DCG checks the proposed schema before this governed
migration runner invokes SQL. The optional change passes; removal of a required
IEMS field fails, so our SQL executor is never called. The SQLite table and
sentinel row are unchanged after rejection.” This does not prevent a database
administrator from running unrestricted direct SQL. The gate is not wired into
Flyway's internal execution hook; it is a separate reviewed migration runner
using IEMS's Flyway table definition. The JDBC snapshot captures column names,
coarse types, and nullability, not complete SQLite DDL semantics such as
indexes, defaults, checks, foreign keys, or permissions. PostgreSQL and MySQL
were not tested in this task.

Reset is automatic for the next run: each run creates new databases. There are
no persistent child processes; SQLite connections are closed and the runner
checks it can acquire a write lock afterward. Retain the ignored evidence for
review. AI is forced off for DCG subprocesses and the test run; no Rust/model
process was observed before or after the rehearsal. The next separate Phase 1
task is the final integrated rehearsal; this task does not start it.
