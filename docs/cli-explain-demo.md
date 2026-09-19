# Deterministic CLI explanation with stable run IDs

Verified 2026-09-17: **COMPLETE**, using the installed `4.0.0-phase1-no-ai-dev.20260917` macOS ARM64 package. No new binary or DCG source changes were needed. This is recorded deterministic governance output, not AI-generated advice.

## Verified capability and limitations

The packaged command is:

```bash
"$DCG_HOME/bin/dcg" explain --db "$HISTORY" --run "$RUN_ID"
```

`explain --help` confirms these flags. Each CLI check records its own engine-generated UUID in `check_runs.run_id`. The CLI recorder also writes status, contract ID, breaking-change messages and warnings. The original multiple-contract rehearsal deleted all three temporary check-history databases at cleanup, so its old IDs cannot be recovered from those deleted databases. The opt-in mode now retains only a safe SQLite snapshot of the new breaking-check database.

Real packaged behavior differs from the original proposal's example: **a successfully explained breaking run exits 1, not 0**. Missing IDs also return 1, so the workflow additionally requires actual explanation output, `Recorded status: FAIL`, and a matching stored field. Database errors return 2. No exit code is rewritten in evidence.

| Information | Verified source |
| --- | --- |
| Contract ID and run UUID | Retained `check_runs` row; CLI text does not print them |
| FAIL verdict | Retained row and CLI `Recorded status: FAIL` |
| Field | CLI text, such as `Field 'studentId' changed type.` |
| Old/new types | Retained engine `breaking_changes` message; CLI headline omits types |
| Compatibility reason | CLI explains parser/downstream-validation impact |
| Remediation | Actual CLI `How to fix` section, retained verbatim |
| Full JSON Pointer | Not supplied for these changes; evidence records the actual field name |

The stored messages are `Field type changed: studentId (integer -> string)` and `Field type changed: amount (number -> string)`. The CLI advises maintaining the previous type or adding a new field. It also emits generic optionality/version guidance and a `userId` example. Those are real generic engine output, **not a validated patch for these fixtures**. Making these already-optional fields optional does not itself undo the incompatible type change. Raw output is preserved rather than silently corrected.

## Run the retained-history rehearsal

Prerequisites: Java 21, the verified development package, built IEMS JAR, Python 3, and no running Rust inference server. Run from IEMS:

```bash
cd /absolute/path/to/iems
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home
export DCG_AI_ENABLED=false
export DCG_HOME="$PWD/.dcg/runtime/dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64"
python3 scripts/dcg/multiple_contract_demo.py \
  --evidence "$PWD/.dcg/rehearsals/cli-explain-$(date +%Y%m%d-%H%M%S)" \
  --retain-history
```

Each run requires a new evidence directory; existing directories are refused. It retains `history.sqlite` only from the breaking batch, with four original rows (two PASS and two FAIL). Baseline/recovery history, the application database and the temporary project remain disposable. The snapshot uses SQLite's backup API with a read-only source after the blocking launcher and its writers exit. No unsafe live file copy is used.

The same byte-exact candidate reset, real recovery and child-process cleanup apply with or without the flag. Retained IDs resolve after their writers and the recovery application have exited. Explaining an ID only queries history; it never reruns `check-compat` or invents an ID.

Evidence directory mode is 0700; files are 0600. Runtime credentials are not copied to evidence. A deliberately retained database is still private local data; keep it out of commits/screenshots unless reviewed.

## Current verified evidence and exact replay commands

Private evidence directory used for the verified run: `$IEMS_ROOT/.dcg/rehearsals/cli-explain-20260917-01`.

| Contract | Stable run ID | Lookup result |
| --- | --- | --- |
| `iems.enrollment` | `7052cc18-6612-4baa-af16-5f1bc6a95c88` | Resolved FAIL, explain exit 1 |
| `iems.scholarship` | `f074bb8d-a2ff-47e6-82b7-299339d0ebf9` | Resolved FAIL, explain exit 1 |

These IDs belong to this retained database. A new rehearsal correctly creates different IDs. Read `results.json` → `failure_run_ids` or `explain-summary.json` → `failures` for that rehearsal's IDs.

```bash
export HISTORY="$IEMS_ROOT/.dcg/rehearsals/cli-explain-20260917-01/history.sqlite"
"$DCG_HOME/bin/dcg" explain --db "$HISTORY" --run 7052cc18-6612-4baa-af16-5f1bc6a95c88
# Expected exit 1: resolved breaking run; inspect Recorded status: FAIL.
"$DCG_HOME/bin/dcg" explain --db "$HISTORY" --run f074bb8d-a2ff-47e6-82b7-299339d0ebf9
# Expected exit 1 for the scholarship failure too.
```

If using `set -e`, capture each expected nonzero explain exit explicitly rather than allowing the shell to abort the presentation. A return code alone does not prove lookup succeeded.

Retained files:

- `results.json`: original/recovery verdicts, exact reset proof, run IDs and explanation command exits.
- `history.sqlite`: the selected breaking-check batch and its original UUIDs/messages.
- `enrollment-explain.txt`, `scholarship-explain.txt`: genuine CLI stdout plus separately labelled stderr.
- `explain-summary.json`: actual CLI stdout, exact command/exit, database-derived identity/type context and field-level provenance; `ai_enabled: false`.
- `post-cleanup-explain.json`: a second real invocation for each ID after the entire rehearsal exited; the database hash and four-row count remained unchanged.
- Existing baseline/rejection/recovery logs: operational evidence, with no full environment dump.

Suggested presenter wording: “These are two real recorded failures from our startup gate. Each has its own stable run ID. The CLI reads that history and explains the deterministic type incompatibility. No model is running. After restoring the candidates exactly, all four checks passed and IEMS started.”

## Verification and cleanup

Executed from the IEMS root, with JAVA_HOME/DCG_HOME as above:

```bash
python3 scripts/dcg/test_cli_explain.py -v
python3 scripts/dcg/test_multiple_contract_demo.py -v
python3 scripts/dcg/test_cli.py
python3 scripts/dcg/multiple_contract_demo.py \
  --evidence "$PWD/.dcg/rehearsals/cli-explain-20260917-01" --retain-history
# Both exact explain commands above were also executed after rehearsal cleanup.
git diff --check
git -C /absolute/path/to/data-contract-governance diff --check
```

| Group | Result | Exit |
| --- | --- | ---: |
| New real CLI/history tests | 6 passed | 0 |
| Existing reset/integrity tests | 4 passed | 0 |
| Existing IEMS binary CLI tests | 6 passed | 0 |
| Full retained-history rehearsal | PASS | 0 |
| Breaking startup gate inside rehearsal | Expected incompatibility, two FAIL/two PASS; zero Java dispatches | 1 |
| Enrollment/scholarship explain, during and after rehearsal | Both IDs resolved; genuine stored FAIL explained | 1 each |
| Missing/corrupt history negative tests | Clear `Explain failed:` errors; no fabricated success | 2 each |
| Git whitespace checks, both repos | PASS | 0 |

Tests cover engine-generated distinct IDs, both lookups after writer exit, unchanged DB hash/no rerun, private permissions, refusal to overwrite evidence/history, missing/corrupt DB handling and rejection of failed/empty CLI explanations. Existing reset tests cover normal completion, exceptions and handled interruption exceptions. Package behavior did not change, so DCG release/package regressions were not rerun; installed package checksums and before/after inventory were verified by the live runner.

Recovery restored exact candidate bytes, recorded four PASSs, dispatched real IEMS once and reached HTTP 200. Intentional SIGTERM returned 143; no forced stop was needed. The recovery port was released, temporary project/application databases were removed, and Rust remained absent. Real source contracts and installed package hashes were unchanged.

The retained history and text evidence remain by design. Keep them for the presentation; afterward remove only this explicitly selected evidence directory if no longer needed. Deleting it removes the ability to resolve these IDs. Do not delete package directories or reset real candidates. The history wrapper rejects missing files before opening SQLite, while the bare CLI may create an empty DB when given a nonexistent file in an existing directory; always use the recorded absolute path.

Files changed: `multiple_contract_demo.py` adds the opt-in snapshot/explain mode and private permissions; new `cli_explain.py` performs safe retention and real CLI explanation; new `test_cli_explain.py` verifies those behaviors; this document, the multiple-contract runbook and feature plan record only verified changes. No baseline, fixture, Java/Rust source, package binary or default IEMS startup behavior changed. Nothing was committed, tagged, pushed, published or deployed.

Next separate Phase 1 implementation: **Maven build gate**. Service/dashboard, webhook, runtime validation, physical database gating and Phase 2 AI remain outside this task.
