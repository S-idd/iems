# 03 — Phase 2 AI advisory demo

> AI labels and scores are advisory only. Deterministic DCG makes the final PASS/FAIL decision.

Use the final consolidated r2 package. `DCG_AI_ENABLED=true` on the **IEMS** launcher requests AI mode but its `run_demo.sh` still makes the startup decision with the deterministic CLI; the Rust model belongs to the separate DCG service or the bounded advisory rehearsal. Starting IEMS alone does not prove a live model prediction. For the normal talk use [01](01-quick-live-demo.md); the commands below expand the screens.

| Command group | Demonstrates / expected result | AI | Evidence | Live-safe / stop or recover |
| --- | --- | --- | --- | --- |
| Setup + IEMS | AI-requested IEMS starts when four contracts PASS; health 200. | Enabled, model optional. | Private `IEMS_DEMO_STATE` SQLite/logs. | Yes; run foreground and stop with Ctrl-C. |
| Model CLI | Compatible deterministic PASS and breaking FAIL, with actual three-seed advisory output. | Real model enabled. | New private `AI_CLI_EVIDENCE`. | Yes; wrapper stops its owned Rust child. |
| Service | Real model, REST/advisory/dashboard/webhook and fault records. | Enabled; faults labelled test-only. | New private `AI_SERVICE_EVIDENCE`. | Yes; runner stops Java/Rust/receivers; use its `--cleanup` after interruption. |
| Integrated | Complete Phase 2 plus IEMS/Postman recovery. | Both enabled and disabled modes. | New private `PHASE2_EVIDENCE`. | Yes; runner cleans owned children; `--cleanup` after interruption. |
| Packaged live service | Show `status`, live `/ui` and Postman/API with real Rust. | Enabled; best effort. | Isolated `DCG_DATA_DIR`. | Only after checking 8080/8081 are free; stop with the same package's `bin/stop`. |

## Set the final package; start IEMS with AI requested

Use a fresh private application database and check history. The exact foreground start/stop and port preflight are in [05](05-start-stop-reset.md); these commands create the same safe state here:

```bash
cd /absolute/path/to/iems
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
export PATH="$JAVA_HOME/bin:$PATH"
export DCG_HOME="/absolute/path/to/freshly-extracted/dcg-package"
umask 077
export IEMS_DEMO_STATE=$(mktemp -d "$PWD/.dcg/rehearsals/iems-live-$(date +%Y%m%d-%H%M%S)-XXXXXX")
printf 'isolated IEMS live demo\n' > "$IEMS_DEMO_STATE/.iems-live-demo-marker"
export IEMS_JDBC_URL="jdbc:sqlite:$IEMS_DEMO_STATE/iems.sqlite"
export DCG_SQLITE_PATH="$IEMS_DEMO_STATE/checks.sqlite"
export IEMS_JWT_SECRET="$(openssl rand -hex 40)"
export IEMS_DEMO_ADMIN_PASSWORD="$(openssl rand -hex 24)"
export IEMS_PORT=8090
lsof -nP -iTCP:8090 -sTCP:LISTEN
DCG_AI_ENABLED=true scripts/database/run_demo.sh sqlite > "$IEMS_DEMO_STATE/iems.log" 2>&1
```

The `lsof` command should print **no listener** before launch (its no-listener exit 1 is expected). The final command stays foreground. In another terminal, `curl --noproxy '*' -fsS http://127.0.0.1:8090/actuator/health` should report `UP`/HTTP 200; press **Ctrl-C** in the first terminal to stop IEMS. If port 8090 is occupied, choose another free `IEMS_PORT`; never stop an unrelated listener. These setup commands do not echo secrets or use the normal `.dcg/data/iems.db`. The IEMS process is healthy even if the optional model is unavailable; the integrated runner records that case in its private `$PHASE2_EVIDENCE/results.json`.

## Run compatible and breaking proposals with the real model

Stop any foreground IEMS instance first if you want an uncluttered process view. The wrapper invokes packaged deterministic `check-compat` **before** its owned Rust process and then stops Rust:

```bash
export AI_CLI_EVIDENCE=$(mktemp -d "$PWD/.dcg/rehearsals/ai-cli-$(date +%Y%m%d-%H%M%S)-XXXXXX")
DCG_AI_ENABLED=true python3 scripts/dcg/advisory_rehearsal.py \
  --scenario all --output "$AI_CLI_EVIDENCE/results.json"
python3 -m json.tool "$AI_CLI_EVIDENCE/results.json"
```

Expected: optional enrollment `sourceSystem` gives deterministic **PASS**; `studentId` integer → string gives deterministic **FAIL**. The `advisory` object records actual model labels, all seed probabilities, model artifact hashes, input hash and agreement. Do not preannounce an expected label as guaranteed or call scores calibrated confidence. The wrapper's own exit 0 means both expected outcomes were recorded; the breaking governance command inside it exits 1. Evidence is private; the final `json.tool` command only reads it. For a shorter run, use `--scenario compatible` or `--scenario breaking` with a **new** output filename.

## Service API and dashboard advisory

The maintained service runner is the safe default for real REST/UI proof. It creates an isolated service database and dynamic ports, checks each run ID across `/checks/{runId}`, `/checks/{runId}/advisory`, logs, rendered `/ui/checks/{runId}`, and the deterministic failure webhook, then shuts down:

```bash
export AI_SERVICE_EVIDENCE="$PWD/.dcg/rehearsals/phase2-service-live-$(date +%Y%m%d-%H%M%S)"
DCG_AI_ENABLED=true python3 scripts/dcg/phase2_service_demo.py --dcg-home "$DCG_HOME" --evidence "$AI_SERVICE_EVIDENCE"
python3 -m json.tool "$AI_SERVICE_EVIDENCE/real-breaking.json"
```

Expected: real compatible `PASS/AVAILABLE`, real breaking `FAIL/AVAILABLE`, actual label/probabilities, `advisoryOnly: true`, and matching run IDs in the persisted API/log/webhook records. The JSON is a saved response from the real service; the runner also verifies the live rendered dashboard and then releases the port. For an interrupted run: `python3 scripts/dcg/phase2_service_demo.py --evidence "$AI_SERVICE_EVIDENCE" --cleanup`. Test-only fault cases in this runner are **not** normal presentation defaults; see [04](04-extended-fault-scenarios.md).

For a **live** service/dashboard screen, use the exact packaged launcher with a new isolated state. It requires ports 8080/8081; the two `lsof` checks must show no listeners first. The fixture copies go **only** into `DCG_DATA_DIR`, never the approved source contracts or package:

```bash
export DCG_DATA_DIR=$(mktemp -d "$PWD/.dcg/rehearsals/dcg-ai-live-$(date +%Y%m%d-%H%M%S)-XXXXXX")
mkdir -p "$DCG_DATA_DIR/contracts/iems.enrollment"
cp "$DCG_HOME/contracts/policy-packs.json" "$DCG_DATA_DIR/contracts/policy-packs.json"
cp contracts/iems.enrollment/metadata.yaml contracts/iems.enrollment/v1.json "$DCG_DATA_DIR/contracts/iems.enrollment/"
cp scripts/dcg/fixtures/compatible.json "$DCG_DATA_DIR/contracts/iems.enrollment/v2.json"
cp scripts/dcg/fixtures/breaking.json "$DCG_DATA_DIR/contracts/iems.enrollment/v3.json"
lsof -nP -iTCP:8080 -sTCP:LISTEN
lsof -nP -iTCP:8081 -sTCP:LISTEN
DCG_AI_ENABLED=true "$DCG_HOME/bin/start"
"$DCG_HOME/bin/status"
```

Expected: Java healthy and Rust `AVAILABLE` when readiness succeeds. These commands create private service state and a one-run password file under `DCG_DATA_DIR`; `bin/start` refuses port 8080 conflict and treats port 8081 conflict as AI `UNAVAILABLE`. Never stop the unrelated listener to force availability. Import the [DCG governance collection](../../postman/dcg-governance-collection.json) and [blank environment](../../postman/dcg-governance-environment.json); enter the local Basic password from the printed file path **in Postman only** and run folder **Phase 2.2 — real service AI advisory**. Do not export the filled environment. `POST /checks` yields a new `runId`. With the live service's ID in `RUN_ID`, these read-only commands prompt for the password instead of putting it on the command line:

```bash
export RUN_ID='<runId returned by this live service>'
curl --noproxy '*' --user demo "http://127.0.0.1:8080/checks/$RUN_ID"
curl --noproxy '*' --user demo "http://127.0.0.1:8080/checks/$RUN_ID/advisory"
open "http://127.0.0.1:8080/ui/checks/$RUN_ID"
```

Expected: the first API response is the authoritative `PASS` or `FAIL`; the second is separate `AVAILABLE` advisory data (or a truthful unavailable status). The browser may prompt for the same one-run Basic credentials. `curl --user demo` prompts interactively; do not replace it with a password in a saved command. Stop this owned launcher with `"$DCG_HOME/bin/stop"` after the screen, keeping the same `DCG_DATA_DIR`; see [05](05-start-stop-reset.md). A run ID from an earlier isolated store is **not** valid in this new store. The [verified Phase 2 advisory runbook](../phase2-ai-advisory-demo.md) documents the same package fixture layout and Postman folders.

## Full Phase 2 and alternate modes

```bash
export PHASE2_EVIDENCE="$PWD/.dcg/rehearsals/phase2-integrated-$(date +%Y%m%d-%H%M%S)"
python3 scripts/dcg/phase2_integrated_demo.py --dcg-home "$DCG_HOME" --evidence "$PHASE2_EVIDENCE"
```

Expected: all **13** indexed scenarios PASS, including no-AI IEMS baseline and final recovery (each 55 Newman requests/107 assertions), real-model CLI and service results, AI-requested startup/Maven blocking, runtime/migration regression and cleanup. The runner controls AI modes internally and refuses an existing directory. On interruption use `python3 scripts/dcg/phase2_integrated_demo.py --evidence "$PHASE2_EVIDENCE" --cleanup`.

To show **no-AI mode** without a long integrated rerun, use a fresh isolated service state and the package's `DCG_AI_ENABLED=false bin/start`/`bin/status`/`bin/stop` sequence in [05](05-start-stop-reset.md). Expected status: `AI advisory mode: DISABLED` and `Rust advisory process: STOPPED`. To show **model unavailable** safely, run the [controlled scenario](04-extended-fault-scenarios.md); it verifies compatible PASS and breaking FAIL with `UNAVAILABLE` and no fabricated scores. Neither mode changes deterministic enforcement.
