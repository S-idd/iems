# PostgreSQL and MySQL acceptance

This acceptance runs IEMS and deterministic DCG against fresh PostgreSQL and
MySQL databases. It is independent of the accepted Linux/SQLite milestone and
does not open, extract, rebuild, or modify that archive or its evidence.

The frozen Linux/SQLite reference is:

| Item | Accepted value |
| --- | --- |
| IEMS base commit | `e4726a752045720f99f8ff6214a7404918a1dc21` |
| Linux archive SHA-256 | `5ec42c1c412b1ccf4fb650991ffae81804d80c08c3e77388002167cbcc8349bc` |
| Linux integrated result SHA-256 | `d623e89c9ce9e5463f4eff6d97034c547816c16617f8a83cf976b3b099be1d55` |

The database-matrix work belongs on `codex/postgres-mysql-acceptance`. Do not
replace the accepted archive or write new evidence into its accepted evidence
directory.

## What the runner proves

For each engine, the runner creates two databases in a uniquely named,
labelled Docker-compatible container: one for IEMS application data and one for
DCG check history. It then verifies:

- IEMS health is HTTP 200 after Flyway initializes the portable baseline.
- The complete Postman collection passes with 55 requests and 107 assertions.
- DCG records the expected compatible and breaking outcomes through JDBC.
- A compatible physical DDL change executes only after deterministic PASS.
- A breaking physical DDL change returns exit 1 and never removes the required
  target column.
- Temporary tables, IEMS processes, containers, credentials, and port bindings
  are cleaned up.
- Source contracts, the selected DCG package, and the normal SQLite database
  retain their original hashes.

The runner sets `TZ=UTC` and `-Duser.timezone=UTC` only for its owned Java
children. This avoids legacy host timezone aliases that PostgreSQL rejects and
does not change the WSL2 or macOS host timezone.

AI is disabled throughout this acceptance. Deterministic DCG is the final
PASS/FAIL authority.

## Prerequisites

Use Java 21, Python 3, Node.js, Docker or Podman Docker-CLI emulation, Maven,
and an extracted DCG package for the current host. Build IEMS and install
Newman locally:

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
export PATH="$JAVA_HOME/bin:$PATH"

mvn -B -ntp -DskipTests package
npm install --prefix .dcg/tools --save-exact newman@6.2.2
```

These commands create Maven output and ignored local tooling. They do not start
AI or create database evidence. On Linux, set `JAVA_HOME` to the Java 21 home
instead of using `/usr/libexec/java_home`.

The container engine must be running. The default images are the fully
qualified `docker.io/library/postgres:16` and `docker.io/library/mysql:8.0`.
Fully qualified names prevent Podman on Linux distributions from resolving a
short name to an image with a different initialization contract. The first run
may download either image.

MySQL readiness is an authenticated `SELECT 1`, rather than an unauthenticated
process ping. This prevents database creation from racing the image's temporary
initialization server before the configured root password is active.

## Run the matrix

Run from the IEMS repository root. Point `DCG_HOME` at a verified extracted
package for the current host:

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
export PATH="$JAVA_HOME/bin:$PATH"
export DCG_HOME=/absolute/path/to/extracted/dcg-package
export EVIDENCE="$PWD/.dcg/rehearsals/database-matrix-$(date -u +%Y%m%dT%H%M%SZ)"

python3 scripts/database/multidb_acceptance.py \
  --dcg-home "$DCG_HOME" \
  --evidence "$EVIDENCE"
```

Expected: the final line is `PASS: .../results.json`. Credentials are generated
for this run, passed through process environments or a temporary mode-600
container environment file, and removed. They are not written to `results.json`.
The evidence is private and disposable under `.dcg/rehearsals/`.

Inspect the concise result without opening private logs:

```bash
jq '{
  result,
  frozenLinuxMilestone,
  engines: (.engines | with_entries(.value |= {
    result, aiMode, iems, dcgHistory, schemaGate
  })),
  preservation,
  cleanup
}' "$EVIDENCE/results.json"
```

Expected: the overall and both engine results are `PASS`; both endpoint runs
show 55 requests, 107 assertions, and zero failures; all preservation and
cleanup flags are true; and `rustProcessesAfter` is empty.

## Recover an interrupted run

Use only the exact evidence directory created by this runner:

```bash
python3 scripts/database/multidb_acceptance.py \
  --evidence "$EVIDENCE" \
  --cleanup
```

The cleanup path validates the database-matrix marker, checks each recorded
container's ownership label before removing it, and considers only the recorded
IEMS process identity. It retains the evidence and does not touch normal IEMS
data, the accepted Linux archive, accepted evidence, or unrelated processes.

## Verified development result

On 2026-09-23, the matrix passed on macOS ARM64 with Docker Desktop 29.7.2,
`docker.io/library/postgres:16`, and `docker.io/library/mysql:8.0`. The private
evidence index is
`.dcg/rehearsals/database-matrix-auth-ready-20260923T142811Z/results.json`;
its SHA-256 is
`5d5ac82570f4b367c9fb2e324928556ce833b856fcffe448901a933a0e67d0e2`.
Both engines passed the full endpoint suite, JDBC history verification, and the
physical migration gate. All preservation and cleanup checks passed.

This result covers the development host above. A Linux run should create a new
`database-matrix-*` evidence directory and use the already accepted Linux
package as a read-only input.
