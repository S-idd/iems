# 02 — Phase 1 deterministic demo

Use the [quick guide](01-quick-live-demo.md) for the normal talk. This page expands each Phase 1 boundary. The Phase 1 integrated and component service runners validate the selected consolidated package before use. All examples use fresh private evidence paths. Run from IEMS; Java 21, Maven, Python 3, Node/Newman and the built IEMS JAR are prerequisites.

| Command group | Demonstrates / expected result | AI | Evidence | Live-safe / stop or recover |
| --- | --- | --- | --- | --- |
| Setup | Select the Phase 1 package. | Disabled. | None. | Yes; no process. |
| CLI | Lint, compatible PASS and breaking FAIL using fixed fixtures. | Disabled. | New private `CLI_EVIDENCE` and SQLite history. | Yes; no server. Keep the expected exit 1 visible. |
| Multiple + explain | Two FAILs, launcher exit 1, zero IEMS dispatch, stable explanations. | Disabled. | New `MULTI_EVIDENCE`; retained `history.sqlite`. | Yes; runner stops its own IEMS process and resets disposable candidates. |
| Maven | Compatible JAR; breaking gate fails at `validate` with no JAR. | Disabled. | New `MAVEN_EVIDENCE`. | Yes; temporary projects removed. |
| Service/dashboard | Registry, checks, rendered UI and restart persistence. | Disabled. | New `SERVICE_EVIDENCE`. | Yes; runner stops Java; `--serve-existing` is stopped with Ctrl-C. |
| Webhook | Failure delivery, outage and **manual** retry. | Disabled. | New `WEBHOOK_EVIDENCE`. | Yes; runner stops IEMS/DCG; `--serve-existing` stops with Ctrl-C. |
| Runtime/migration | Publisher handoffs 1/0/0 and SQLite executor 1/0. | Disabled. | New private directories. | Yes; no persistent process. |
| Integrated | All Phase 1 stages and final IEMS recovery. | Disabled. | New `PHASE1_EVIDENCE`. | Yes; use `--cleanup` after interruption. |

## Setup and individual CLI checks

```bash
cd /absolute/path/to/iems
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
export PATH="$JAVA_HOME/bin:$PATH"
export DCG_HOME="/absolute/path/to/freshly-extracted/dcg-package"
export DCG_AI_ENABLED=false
umask 077
export CLI_EVIDENCE=$(mktemp -d "$PWD/.dcg/rehearsals/cli-live-$(date +%Y%m%d-%H%M%S)-XXXXXX")
export DCG_SQLITE_PATH="$CLI_EVIDENCE/checks.sqlite"
./scripts/dcg.sh lint
"$DCG_HOME/bin/dcg" check-compat \
  --base contracts/iems.enrollment/v1.json \
  --candidate scripts/dcg/fixtures/compatible.json \
  --mode BACKWARD --contract-id iems.enrollment --record-db "$DCG_SQLITE_PATH"
"$DCG_HOME/bin/dcg" check-compat \
  --base contracts/iems.enrollment/v1.json \
  --candidate scripts/dcg/fixtures/breaking.json \
  --mode BACKWARD --contract-id iems.enrollment --record-db "$DCG_SQLITE_PATH"
```

The final command **intentionally exits 1** for `studentId: integer → string`; exit 2 would be an error, not a successful demonstration. The compatible command exits 0. The approved `v1.json` and source `candidate.json` files are never edited. `./scripts/dcg.sh check sqlite` is available for checking all **current source candidates**, but its result depends on their current contents; the fixed-fixture commands above are the reproducible presentation path.

## Multiple-breaking proposal and stable CLI explanations

```bash
export MULTI_EVIDENCE="$PWD/.dcg/rehearsals/multiple-contracts-$(date +%Y%m%d-%H%M%S)"
python3 scripts/dcg/multiple_contract_demo.py --evidence "$MULTI_EVIDENCE" --retain-history
python3 -m json.tool "$MULTI_EVIDENCE/explain-summary.json"
```

Expected: enrollment and scholarship FAIL, overall launcher exit **1**, IEMS Java dispatch **0**, exact candidate reset and healthy recovery. The runner already invokes the real `dcg explain` for both stable run IDs. To replay either one against its retained read-only history, use its actual ID from that run:

```bash
export HISTORY="$MULTI_EVIDENCE/history.sqlite"
export RUN_ID=$(python3 -c 'import json,os,pathlib; p=pathlib.Path(os.environ["MULTI_EVIDENCE"])/"results.json"; print(json.loads(p.read_text())["failure_run_ids"]["iems.enrollment"])')
"$DCG_HOME/bin/dcg" explain --db "$HISTORY" --run "$RUN_ID"
```

An explained recorded FAIL also exits **1**. Confirm `Recorded status: FAIL` and the explanation text; exit 1 alone also occurs for an unknown ID. For scholarship, replace `iems.enrollment` with `iems.scholarship` in the ID extraction. This is deterministic CLI explanation, not model-generated text. No process remains after the multiple runner.

## Maven gate, registry/dashboard and webhook

```bash
export MAVEN_EVIDENCE="$PWD/.dcg/rehearsals/maven-gate-$(date +%Y%m%d-%H%M%S)"
python3 scripts/dcg/maven_gate_demo.py --evidence "$MAVEN_EVIDENCE"
```

Expected: compatible Maven `verify` creates a JAR; breaking build exits nonzero in plugin `check-compat` at `validate`, before packaging and with no JAR. The official plugin writes JSON reports; Maven is fail-fast and reports only the first actual failure. The runner uses disposable project copies and stops its owned processes.

```bash
export SERVICE_EVIDENCE="$PWD/.dcg/rehearsals/service-registry-dashboard-$(date +%Y%m%d-%H%M%S)"
python3 scripts/dcg/service_registry_demo.py --dcg-home "$DCG_HOME" --evidence "$SERVICE_EVIDENCE"
python3 scripts/dcg/service_registry_demo.py --dcg-home "$DCG_HOME" --evidence "$SERVICE_EVIDENCE" --serve-existing
```

Expected: four registered contracts, PASS/FAIL checks, matching REST/dashboard run IDs and persistence across a restart. The first command captures private evidence and stops Java. The second opens that completed state on a fresh loopback port, prints a one-time local Basic password **only to the terminal**, and stays foreground until **Ctrl-C**. Open the printed `/ui` URL; do not copy the password into screenshots or export a filled Postman environment. The isolated registry temporarily permits publishing a breaking proposal so the service can record the failing check; this is not strict publication approval.

```bash
export WEBHOOK_EVIDENCE="$PWD/.dcg/rehearsals/webhook-delivery-$(date +%Y%m%d-%H%M%S)"
python3 scripts/dcg/webhook_delivery_demo.py --dcg-home "$DCG_HOME" --evidence "$WEBHOOK_EVIDENCE"
python3 scripts/dcg/webhook_delivery_demo.py --dcg-home "$DCG_HOME" --evidence "$WEBHOOK_EVIDENCE" --serve-existing
```

Expected: `CONTRACT_CHECK_FAILED` delivery correlates to the DCG run and IEMS inbox; an outage is retained as retryable and a **manual retry** delivers once. The first command stops both owned services. The second reopens saved state for browser/Postman; press **Ctrl-C** to stop it. Temporary credentials are printed locally only. Webhooks report failed checks; they do not continuously watch arbitrary manual database DDL.

## Runtime validator and physical SQLite migration gate

```bash
export RUNTIME_EVIDENCE=$(mktemp -d "$PWD/.dcg/rehearsals/runtime-validation-$(date +%Y%m%d-%H%M%S)-XXXXXX")
IEMS_DCG_RUNTIME_EVIDENCE="$RUNTIME_EVIDENCE" DCG_AI_ENABLED=false \
  mvn -B -ntp -Dtest=ScholarshipAppliedEventBoundaryTest test
```

Expected: valid scholarship APPLIED event PASS and publisher handoff **1**; wrong-type amount and missing studentId FAIL with handoffs **0**. The private evidence is in `$RUNTIME_EVIDENCE`. This is publisher invocation with messaging disabled, not Kafka delivery; the test leaves no server to stop.

```bash
export MIGRATION_EVIDENCE="$PWD/.dcg/rehearsals/database-migration-gate-$(date +%Y%m%d-%H%M%S)"
DCG_AI_ENABLED=false python3 scripts/database/iems_migration_gate.py --evidence "$MIGRATION_EVIDENCE"
```

Expected: nullable schools-column addition PASS/executor **1**; required `name` removal FAIL/executor **0**, with unchanged breaking-database/schema hashes and sentinel. The runner makes isolated SQLite files, never points at the normal IEMS database, and closes them on exit. It governs only reviewed SQL through this runner; unrestricted direct SQL is outside scope.

## Complete Phase 1 integrated rehearsal

```bash
mvn -B -ntp -DskipTests package
export PHASE1_EVIDENCE="$PWD/.dcg/rehearsals/phase1-integrated-$(date +%Y%m%d-%H%M%S)"
python3 scripts/dcg/phase1_integrated_demo.py --dcg-home "$DCG_HOME" --evidence "$PHASE1_EVIDENCE"
```

Expected: all ten indexed Phase 1 scenarios PASS; baseline and recovery each show IEMS HTTP 200 and Newman **55 requests/107 assertions/0 failures**. The build touches generated `target/` only; the runner uses disposable copies/databases, stops its children and retains private evidence. After interruption, run `python3 scripts/dcg/phase1_integrated_demo.py --evidence "$PHASE1_EVIDENCE" --cleanup`; see [05](05-start-stop-reset.md). The verified prior run is `.dcg/rehearsals/phase1-integrated-20260918-145750/results.json`.
