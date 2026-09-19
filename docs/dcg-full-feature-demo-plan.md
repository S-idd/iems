# IEMS × DCG: two-phase demo and implementation plan

Phase 1 deterministic demonstration: **COMPLETE for the local macOS ARM64 development rehearsal** on 2026-09-18. The [integrated runbook](phase1-integrated-demo.md) and private `.dcg/rehearsals/phase1-integrated-20260918-145750/results.json` link all ten passing scenarios. Extended capabilities below remain separate future work; this does not promote the development package to an accepted release or start Phase 2.

The split is useful: first prove deterministic protection, then show whether AI adds useful information without changing enforcement. The main Phase 1 presentation is 15–20 minutes after preparation. Infrastructure-heavy demonstrations belong to its extended technical session.

## Phase 1 — DCG demo without the AI model

### Outcome and architecture

Prove: **DCG can deterministically detect, explain, record and block unsafe contract or governed database changes without using the AI model.** This applies to changes checked by the configured engine/policy and operations routed through the gate, not every possible database change.

Decision paths:

```text
Candidate contracts → deterministic DCG → PASS → launcher/build may proceed
                                      → FAIL → launcher/build stops

Service-submitted check → persisted result/run ID → dashboard/logs → webhook

Scratch database candidate snapshot → DCG gate → PASS → reviewed SQL executes
                                             → FAIL → SQL never executes
```

Foundation update (2026-09-17): **Ready** — the uniquely identified `4.0.0-phase1-no-ai-dev.20260917` package is installed alongside the original RC. Two assemblies were byte-identical; all 23 payload checksums pass. Primary installed start/status/stop and real IEMS startup passed with AI disabled. Five focused installed-launcher tests, six IEMS CLI tests and 24 release regressions passed. See [the inspection and verification report](phase1-no-ai-inspection.md) for exact commands, hashes, counts and cleanup evidence.

The original installed RC remains unchanged and retains its known notices mismatch: normalizing the original archive notice to LF exactly reproduces the installed file. The development package uses the later reviewed canonical notice verbatim and validates it before manifest generation. The new Rust binary was necessarily rebuilt from pinned unchanged source with path remapping; no AI-enabled acceptance is claimed. Java JARs are reused unchanged. This is an unpublished development package, not an RC promotion.

Use explicit `DCG_HOME` for this rehearsal. The development `bin/start` supports `DCG_AI_ENABLED=false`; it starts the DCG Java service, while IEMS's separate launcher checks candidates before starting IEMS. The original RC's launcher still requires AI. The isolated DCG service, registry, REST PASS/FAIL checks, dashboard correlation, SQLite restart persistence, and separate Postman flow are now verified; see [service registry/dashboard demo](service-registry-dashboard-demo.md).

### Feature-status table

Status refers to the IEMS demonstration, not merely the existence of DCG source code. **Ready** means an existing IEMS path has prior successful rehearsal evidence; **In progress** means partially integrated; **Planned** means integration/rehearsal remains; **Extended** means outside the main presentation and is not a readiness claim; **Skipped** means excluded or unsupported. Inspection alone does not establish readiness.

| Capability | Status | Evidence or remaining work |
| --- | --- | --- |
| SQLite IEMS API baseline | Ready | Latest existing Postman rehearsal: 55 requests, 107 assertions. |
| Packaged CLI lint/diff/compatibility and SQLite history | Ready | Installed CLI exposes these commands; existing IEMS PASS/FAIL rehearsals. |
| One contract failure blocking startup | Ready | Real CLI against isolated project copies: compatible dispatch exit 0, breaking exit 1 with no IEMS dispatch. Separate real IEMS health test passed with no AI artifacts. |
| Multiple contracts in one invocation | Ready | Real CLI rehearsal: enrollment and scholarship FAIL, two other PASSs, exit 1 and zero IEMS dispatches. Four independent checks, not one atomic transaction. |
| CLI explanation of a recorded run | Ready | Two stable engine IDs resolve from retained private SQLite history using packaged explain after cleanup. Actual breaking-run explain exit is 1. See [verified runbook](cli-explain-demo.md). |
| Maven demo profile | Ready | Official RC Maven plugin, opt-in `dcg-demo` at validate; four compatible PASS reports and successful package, breaking build stops before package. Plugin is fail-fast and writes JSON evidence. [Verified runbook](maven-build-gate-demo.md). |
| AI-disabled launcher foundation | Ready | Installed development start/status/stop passed; controlled missing-AI copies passed. Use explicit development DCG_HOME; original RC remains unchanged. |
| Service run/result/log retrieval | Verified | Isolated packaged service returned persistent PASS/FAIL run IDs and logs; see [evidence](service-registry-dashboard-demo.md). |
| Same failed run in dashboard | Verified | Real rendered UI showed the full REST failure run ID, FAIL status, and `studentId` path before and after restart. |
| Service failure webhook into IEMS | Verified | Protected, demo-only IEMS DCG inbox received the packaged service failure event; [webhook runbook](webhook-delivery-demo.md). |
| Valid/invalid IEMS runtime payload | Verified locally | Official starter built from source; real APPLIED scholarship publisher handoff validates against dedicated v1 event schema. Valid PASS/1, wrong type FAIL/0, missing required FAIL/0. [Runtime runbook](runtime-payload-validation-demo.md). No broker delivery claimed. |
| Physical schema gate on isolated temporary tables | Ready | Existing script proved optional-column PASS and required-column removal FAIL. This is not yet a migration of an actual IEMS business table. |
| Governed migration of an actual IEMS table | Verified locally, SQLite | Fresh disposable copies of Flyway's real `schools` table: nullable column PASS/executor 1; required `name` removal FAIL/executor 0; exact schema and DB hashes retained. [Migration runbook](database-migration-gate-demo.md). JDBC snapshot remains limited to column names, coarse types and nullability. |
| Candidate restoration and IEMS recovery | Ready | Isolated two-failure rehearsal automatically restored exact candidate bytes, then four PASSs and real IEMS health HTTP 200. Real source files unchanged. |
| PostgreSQL/MySQL acceptance | Extended | Previous smaller API/gate checks exist; full 55-request collection is still unverified on these engines. |
| Compatibility modes, policy packs, nested schema rules | Extended | CLI/core capabilities exist; pin expected outcomes for each selected fixture and policy. |
| Consumer impact | Extended | CLI uses declared consumers and historical results; fill real IEMS metadata and rehearse. No automatic dependency discovery. |
| Contract registry publication, versions and badges | Extended | Packaged service capability; stage separate lifecycle requests. A rejected publication is distinct from a failed queued check. |
| Evidence import/replay/retention | Extended | Service code is packaged; build integration, identity and evidence workflow need IEMS setup. |
| Delivery retries/history | Verified demo | A retryable outage delivery survived DCG restart, then manual retry delivered to IEMS with the same delivery ID and event ID. Automatic retry timing remains unverified. |
| Security/audit/health/metrics and backup/restore | Extended | Use isolated metadata/artifact state and capture actual proof. |
| Gradle | Extended | Requires companion fixture/artifact provisioning; do not convert IEMS from Maven. |
| CI/OIDC | Extended | Requires configured CI, identity policy and reachable service; no simulated production-auth claim. |
| S3 artifact backend | Extended | Requires account-specific infrastructure; beta capability. Skip live execution until prerequisites exist. |
| Continuous discovery of manual database DDL | Skipped | Not provided by current IEMS integration or webhook mechanism. A separate detector would be new work. |

Installed package inspected: `dcg-4.0.0-rc.1-macos-arm64`, with CLI/service JARs and Rust/model artifacts. Its build-info records Java commit `994770c97ed00d00b1a6bf974344a6c68c31d656`; do not assume newer source features are in that binary. Package class/config inspection confirmed service checks, notifications, evidence and shadow inference components; it did not revalidate every endpoint. Use the current support policy: this is a local RC, MySQL and S3 remain beta; SQLite is single-node production-lite. Older architecture documents contain inconsistent maturity labels.

### Implementation tasks, in dependency order

1. Packaging/lifecycle and isolated multiple-contract rejection/reset are complete. The [final integrated rehearsal](phase1-integrated-demo.md) ran the verified CLI, explanation, Maven, service/dashboard, webhook, [runtime APPLIED event validation](runtime-payload-validation-demo.md), and [physical migration gate](database-migration-gate-demo.md) in sequence, with baseline and recovery API collections passing. The next separate task, if requested, is Phase 2 AI advisory integration.
2. The isolated baseline → two breaking contracts → blocked startup → automatic restore → healthy recovery sequence is integrated with the broader presenter sequence and full API collection. The runner uses task-owned ports and never changes an existing IEMS process.
3. The official opt-in Maven profile and real scholarship APPLIED publisher boundary are verified. A dedicated event schema has required fields and ISO timestamp serialization. Current db-demo disables actual brokers.
4. Start the packaged service independently of Rust. Stage IEMS versions, submit a failed check, and correlate its run ID across API, logs and UI.
5. The protected demo-only IEMS DCG receiver/inbox is verified with a real packaged webhook, outage, persisted outbox and manual recovery; see [webhook runbook](webhook-delivery-demo.md). It remains separate from IEMS user notifications.
6. The isolated actual-table SQLite migration gate is verified and linked from the final integrated evidence. Governance and webhook Postman assets remain separate; runtime malformed payloads are exercised at the serialized publisher boundary, not through a fake endpoint.

Multiple-contract/reset update (2026-09-17): the real packaged CLI returned both failures with launcher exit 1 and no IEMS dispatch. Exact automatic restoration then permitted real IEMS HTTP 200. Four reset/integrity tests and six existing CLI tests passed. See [commands, fixture details and evidence](multiple-contract-demo.md).

### Main presentation sequence: approximately 19 minutes

| Time | Show | Expected result | Evidence |
| --- | --- | --- | --- |
| 0–2 min | Working SQLite IEMS; run Postman | Application requests pass | Sanitized Newman summary and health response |
| 2–4 min | Optional `sourceSystem` addition; diff/check | PASS, exit 0 | Exact schema pair/hashes and output |
| 4–6 min | `studentId`: integer → string; diff/explain | FAIL, exit 1; precise field/type reason | Saved run ID, diff and explanation |
| 6–8 min | Two candidate contracts changed; rerun launcher | Both failures reported; app never starts | All contract results, wrapper exit, zero Java dispatches |
| 8–9 min | Dedicated Maven demo profile | Incompatible proposal blocks build | Build exit and official JSON evidence; verified in integrated run |
| 9–12 min | Submit failure to service; open same run in UI; show webhook inbox | Completed FAIL and matching event | Service/UI and webhook are distinct isolated runs; correlate IDs within each |
| 12–14 min | Valid and invalid real IEMS payload | Valid accepted; invalid rejected before publishing | Publisher handoff counts; verified in integrated run |
| 14–17 min | Physical schema gate | Optional column applied; required-column removal blocked | Before/candidate/after snapshots and gate history |
| 17–19 min | Restore candidates, restart IEMS, API checks | Contracts PASS and application recovers | Restored hashes, startup result, Postman summary |

Prebuild artifacts, stage service data, and prepare browser tabs before presenting. Do not squeeze unresolved integration work into the 20-minute slot. Run the full collection during rehearsal; the live demo may use selected baseline/recovery requests provided their setup dependencies are included.

### Command runbook — existing capabilities

Commands are written for Bash from the IEMS repository. Use a dedicated disposable database. Keep the setup shell open: later commands use its variables. Reuse existing demo credentials only with the database they initialized. Do not use `git reset` or overwrite v1 to recover.

**A. Prepare one unique rehearsal and candidate backups.**

```bash
cd /absolute/path/to/iems
export DCG_HOME="$PWD/.dcg/runtime/dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64"
mkdir -p .dcg/rehearsals
export DEMO_DIR="$(mktemp -d "$PWD/.dcg/rehearsals/two-phase.XXXXXX")"
umask 077
mkdir -p "$DEMO_DIR/backups"
cp -R contracts/. "$DEMO_DIR/backups/"
export DCG_SQLITE_PATH="$DEMO_DIR/cli-checks.db"
export IEMS_JDBC_URL="jdbc:sqlite:$DEMO_DIR/iems.db"
export IEMS_JWT_SECRET="$(openssl rand -hex 32)"
export IEMS_DEMO_ADMIN_PASSWORD="$(openssl rand -hex 24)"
(cd "$DCG_HOME" && shasum -a 256 -c SHA256SUMS) > "$DEMO_DIR/package-verification.txt"
./scripts/dcg.sh lint
./scripts/dcg.sh check sqlite
```

Expected: baseline PASS/exit 0. If existing candidates fail, stop and record the starting state; do not silently replace them. Preserve a private file of required environment values for terminal restarts; exclude credentials and JWTs from shared evidence.

**B. Start IEMS and run Postman.** Build before the presentation if needed.

```bash
mvn -DskipTests package
./scripts/database/run_demo.sh sqlite > "$DEMO_DIR/iems.log" 2>&1 &
IEMS_DEMO_PID=$!
curl --fail http://127.0.0.1:8090/actuator/health
```

Wait for a healthy response before continuing; startup is not instantaneous. Verify the captured PID is still running and the log has no port conflict, so an unrelated existing instance cannot produce a false pass.

```bash
python3 scripts/postman/seed_notification.py "$DEMO_DIR/iems.db"
.dcg/tools/node_modules/.bin/newman run postman/iems-api-collection.json \
  --environment postman/iems-demo.postman_environment.json \
  --env-var "adminPassword=$IEMS_DEMO_ADMIN_PASSWORD"
```

Expected: 55 requests/107 assertions pass for the present collection revision. Newman is already installed locally; a fresh machine needs `npm install --prefix .dcg/tools newman`. Import the same collection/environment in Postman for the live presentation. Seed one notification before each complete run. Default Newman output can contain the refresh-token URL: keep raw runner output private and share only a redacted summary.

**C. Show the exact safe and breaking pairs used again in Phase 2.** These commands do not edit candidates.

```bash
./scripts/dcg.sh cli diff --base contracts/iems.enrollment/v1.json \
  --candidate scripts/dcg/fixtures/compatible.json
./scripts/dcg.sh cli check-compat --base contracts/iems.enrollment/v1.json \
  --candidate scripts/dcg/fixtures/compatible.json --mode BACKWARD \
  --contract-id iems.enrollment --record-db "$DCG_SQLITE_PATH"
./scripts/dcg.sh cli diff --base contracts/iems.enrollment/v1.json \
  --candidate scripts/dcg/fixtures/breaking.json
./scripts/dcg.sh cli check-compat --base contracts/iems.enrollment/v1.json \
  --candidate scripts/dcg/fixtures/breaking.json --mode BACKWARD \
  --contract-id iems.enrollment --record-db "$DCG_SQLITE_PATH"
printf 'Compatibility exit: %s\n' "$?"
```

Expected: safe compatibility exits 0; breaking compatibility exits 1 with `Field type changed: studentId (integer -> string)`. `diff` exits 0 when the diff succeeds, even when the change is breaking. Do not interpret its exit as a compatibility verdict. Run expected failures in an interactive shell without `set -e`, or capture them explicitly.

```bash
DEMO_RUN_ID=$(python3 - <<'PY'
import os, sqlite3
with sqlite3.connect(os.environ['DCG_SQLITE_PATH']) as db:
    print(db.execute("SELECT run_id FROM check_runs WHERE status='FAIL' ORDER BY created_at DESC LIMIT 1").fetchone()[0])
PY
)
./scripts/dcg.sh cli explain --run "$DEMO_RUN_ID" --db "$DCG_SQLITE_PATH"
```

Expected: explanation of the recorded failure; `explain` returns 1 for a breaking run. Capture exact schemas, hashes, verdict, reason and run ID. The CLI's explanation is deterministic, not model-generated prose.

**D. Demonstrate one failure, then two contracts, then blocked startup.** Stop only the IEMS process started in B; wait until port 8090 has no listener.

```bash
kill "$IEMS_DEMO_PID"
wait "$IEMS_DEMO_PID" || true
cp scripts/dcg/fixtures/breaking.json contracts/iems.enrollment/candidate.json
./scripts/dcg.sh check sqlite
printf 'Single-change exit: %s\n' "$?"
python3 - <<'PY'
import json
from pathlib import Path
p = Path('contracts/iems.scholarship/candidate.json')
schema = json.loads(p.read_text())
schema['properties']['studentId']['type'] = 'string'
p.write_text(json.dumps(schema, indent=2) + '\n')
PY
./scripts/dcg.sh check sqlite
printf 'Multiple-change exit: %s\n' "$?"
./scripts/database/run_demo.sh sqlite
printf 'Startup gate exit: %s\n' "$?"
lsof -nP -iTCP:8090 -sTCP:LISTEN
```

Expected: enrollment and scholarship FAIL, other unchanged contracts PASS; aggregate exit 1; no new IEMS listener. Infrastructure errors are exit 2 and must not be counted as successful compatibility rejection. Save uncommitted candidate hashes: the recorded Git commit alone does not identify these edits.

**E. Physical database gate.** This existing script uses temporary tables, not IEMS business tables.

```bash
IEMS_JDBC_URL="jdbc:sqlite:$DEMO_DIR/schema-gate.db" \
  python3 scripts/database/schema_gate_demo.py
```

Expected: safe addition executes; removal of required `name` returns compatibility exit 1; final snapshot retains `name`. The whole demonstration script exits 0 because the rejection was expected. Capture the generated `.dcg/schema-demo/<unique-id>/` snapshots and `.dcg/data/schema-gates.db` records. The script drops its temporary tables afterward; retain the snapshots as proof.

**F. Reset and prove recovery.** Restore exactly the candidates backed up in A, preserving any pre-existing work.

```bash
for contract in contracts/iems.*; do
  cp "$DEMO_DIR/backups/${contract##*/}/candidate.json" "$contract/candidate.json"
done
./scripts/dcg.sh check sqlite
./scripts/database/run_demo.sh sqlite > "$DEMO_DIR/iems-recovery.log" 2>&1 &
IEMS_DEMO_PID=$!
```

After health is UP, repeat B's seed/Newman commands. Expected: gate PASS and API assertions pass. At the end, stop only captured demo process IDs; retain private logs, backups and databases until evidence is reviewed. If interrupted after D, perform this restoration before any unrelated development. Restore any extra files added by later fixture work from their own backups; the commands above modify only the two candidates.

### Command runbook — service and runtime rehearsal

The packaged service, registry, dashboard, REST history, restart persistence and separate Postman collection are verified. Use the exact one-shot start/status/stop/restart command and private evidence walkthrough in [service registry/dashboard demo](service-registry-dashboard-demo.md). That rehearsal creates `v1` through `POST /contracts`, publishes isolated `v2` proposals through the version API, polls the real service for PASS/FAIL, and correlates the same run IDs in its rendered UI. Do not use the superseded direct-file staging command here.

The runtime APPLIED event proof uses
`IEMS_DCG_RUNTIME_EVIDENCE="$evidence_dir" DCG_AI_ENABLED=false mvn -B -ntp -Dtest=ScholarshipAppliedEventBoundaryTest test`
from the IEMS root, after creating a new private evidence directory. The
[runtime runbook](runtime-payload-validation-demo.md) has the exact artifact
install and test commands. Its malformed serialized payloads are test seams at
the real publisher boundary; there is no runtime-validation Postman endpoint.
The `dcg-demo` Maven profile is verified separately; retain the actual gate
reports and distinguish them from Maven test results.

The verified webhook command, receiver API, outbox recovery and Postman collection are in [the webhook runbook](webhook-delivery-demo.md). The IEMS user-notification routes remain separate from this DCG event inbox.

### Extended Phase 1 technical session

Keep PostgreSQL/MySQL, compatibility modes, policy packs, consumer impact, evidence import/replay, automatic retry timing at scale, security/audit, backup/recovery, Gradle, CI/OIDC and S3 here. Also include registry/version publication, nested schema constraints, badges and metrics to retain full-feature coverage. Each must acquire its own command/fixture/evidence/reset entry before live presentation. They are not silently complete because the package or source contains a related class.

Available command entry points include `./scripts/database/run_demo.sh postgres`, `./scripts/database/run_demo.sh mysql`, `./scripts/dcg.sh demo-all`, and `./scripts/dcg.sh cli check-compat ... --mode FORWARD` or `FULL`. They require the documented per-engine IEMS/DCG credentials or real schema arguments; ellipses are not runnable commands. Finalize exact per-environment commands during this extended implementation rather than inventing infrastructure or plugin availability now.

### Phase 1 rehearsal checklist and completion criteria

- [x] Verify development-package checksums, identity/JDK, reproducibility and installed no-AI lifecycle; preserve original RC. See inspection report (2026-09-17).
- [x] Confirm no Rust process was started for Phase 1 and service inference is disabled.
- [x] Use isolated databases, recorded task-owned ports and private credentials; baseline API passes 55 requests/107 assertions.
- [x] Verify safe, single-failure and multiple-failure fixtures plus expected exit codes.
- [x] Prove isolated no-AI startup dispatch is blocked by a breaking candidate; final healthy IEMS startup and API recovery pass.
- [x] Rehearse Maven profile and real runtime boundary; no Planned item presented as done.
- [x] Correlate service submission, result, logs, dashboard and webhook by run ID in the isolated local demo; see [service](service-registry-dashboard-demo.md) and [webhook](webhook-delivery-demo.md) evidence.
- [x] Prove physical rejected SQL never executed using zero executor calls and equal schema/DB hashes.
- [x] Restore candidates byte-for-byte and pass recovery API checks.
- [x] Complete a timed automated rehearsal within 20 minutes; preserve private evidence for every main step. Live presenter pacing remains a separate practice exercise.

The local deterministic Phase 1 implementation is complete: every main row passed with AI absent, all integration gaps closed, and recovery repeatable. Extended items need a separate readiness checklist and explicit skips; they do not lengthen the main presentation.

## Phase 2 — DCG demo with the AI model

**Local macOS ARM64 development status (2026-09-19): COMPLETE for the Phase 2 advisory scope.** The final [integrated rehearsal](phase2-integrated-demo.md) passed all 13 required stages with the verified r3 development package; private evidence is `.dcg/rehearsals/phase2-integrated-20260919-final/results.json`. It includes real SAFE/PASS and BREAKING/FAIL model outputs, AI-requested startup and Maven blocking, a correlated service/dashboard/webhook run, unavailable and test-only fault cases for both deterministic verdicts, explicit test-only disagreement, runtime and SQLite migration regressions, and fresh IEMS/Postman recovery. The Phase 2 plan text below records earlier planning assumptions; its “planned” and “reserved” wording should not be used as the current implementation status. Genuine real-model disagreement and low-confidence fixtures were not found or claimed; the disagreement demo is explicitly test-only. The accepted RC was not replaced, and PostgreSQL/MySQL and Linux acceptance remain open.

### Outcome, actual outputs and decision order

Prove: **AI adds advisory risk information while deterministic DCG rules retain final governance authority.** The broader proposed claim about AI-generated explanations must be narrowed until that output actually exists.

The installed model's observed response contains per-seed `label` and probabilities for `safe`, `warning`, and `breaking`. Existing evidence showed SAFE for the optional field and BREAKING for the integer-to-string change. These are previous observations, not guaranteed future predictions or a calibrated confidence guarantee. Do not average seeds or relabel probabilities as certainty without a documented method.

| AI capability/scenario | Status | What can honestly be shown |
| --- | --- | --- |
| Same safe/breaking IEMS proposals | Ready | Existing `ai_demo.py` calls the packaged model and captures deterministic results plus per-seed labels/probabilities. |
| Risk probability display | Ready | Show raw per-seed class probabilities. A model probability is not demonstrated statistical calibration. |
| Human-readable comparison panel | Planned | Display engine reasons separately from model scores and label their provenance. |
| AI-generated explanation/correction | Skipped | Not a field in the inspected model response. CLI `explain` is deterministic. |
| Severity ranking / additional review suggestions | Planned | Could be an explicitly labelled application rule using model scores; not an existing model capability. |
| AI consumer prioritization | Skipped | No verified output. Existing CLI impact uses declared metadata/history. |
| Actual disagreement | Planned | Find and freeze a genuine mismatch fixture; never promise the model will disagree on demand. |
| Low-confidence case | Planned | Find a real fixture meeting a documented review threshold; otherwise skip or label a simulated UI test. |
| Model outage with continued governance | Verified for Phase 2.1 local development package | CLI checks retain PASS/FAIL and the installed development launcher keeps Java healthy when Rust is missing, fails, or times out; see `phase2-ai-advisory-demo.md`. |

Required enforcement order:

```text
Developer proposal → deterministic engine → persisted PASS/FAIL
                                           ↓
                                advisory prediction/display
                                           ↓
                          enforcement retains original result
```

The Phase 2.1 `advisory_rehearsal.py` runs authoritative CLI checks before optional inference and records unavailable advice without changing the verdict. The service source check runner persists the deterministic result before dispatching a shadow observation; verify this behavior in the exact packaged service during the later service rehearsal. The synchronous comparison endpoint is a demo view and must not be used as an availability-critical gate. The accepted RC still requires initial Rust readiness. The separate `4.0.0-phase2-ai-launcher-dev.20260918-r4` package starts Java first and passed local AI-ready, missing, failed, timeout, disabled, and unrelated-listener host tests; it is not an accepted RC or release.

AI must not approve publication, execute SQL, override FAIL, change a build exit, or become required for IEMS startup. Never silently replace a real prediction with a desired label.

### Implementation tasks

1. Reuse the exact Phase 1 baseline/compatible/breaking files and their hashes. Keep the deterministic result immutable in comparison output.
2. Display each seed's label/probabilities beside the deterministic verdict and reason. Use explicit fields such as `deterministicReason` and `modelProbabilities` to avoid misattribution.
3. Change advisory orchestration later so model startup/request failure yields an unavailable warning after the deterministic result has been produced. It must preserve the gate exit. The current script is not yet that resilient wrapper.
4. Search genuine model outputs for disagreement and low-confidence fixtures. Freeze reproducible inputs. If unavailable, label those cases Skipped in the live model session; a fault-injection test may demonstrate UI/enforcement behavior but must be labelled simulated.
5. Choose and document any human-review threshold before using it. Review recommendations derived from thresholds are application policy, not generated model advice.

### Presentation sequence: approximately 8–10 minutes

| Step | Scenario | Deterministic expectation | AI expectation / evidence |
| --- | --- | --- | --- |
| 1 | Same optional-field proposal | PASS | Show actual labels/probabilities; prior observation SAFE |
| 2 | Same integer-to-string proposal | FAIL | Show actual labels/probabilities; prior observation BREAKING |
| 3 | Genuine disagreement fixture, if found | Verdict dictated by rules | Highlight difference and unchanged enforcement; otherwise explicitly skip |
| 4 | Model unavailable | Safe stays PASS; breaking stays FAIL | Warning; no missing or overwritten governance result |
| 5 | Genuine low-confidence fixture, if found | Verdict dictated by rules | Show per-seed probabilities, defined threshold and human-review suggestion; otherwise skip |
| 6 | Restore advisory model and compare | Same deterministic results | New prediction evidence correlated to identical inputs |

### Commands, expected results and evidence

**Existing real-model comparison:**

```bash
python3 scripts/dcg/ai_demo.py
```

This uses the same two enrollment fixtures from Phase 1, starts the packaged Rust binary on an available loopback port, runs deterministic checks before each prediction, writes `.dcg/ai-demo/results.json`, and stops its model process. Expected scenario verdicts: compatible exit 0, breaking exit 1. The overall demonstration script exits 0 when both expected verdicts and prediction calls complete. It is not itself a deploy gate. Copy the results and model log into the private rehearsal directory because rerunning overwrites them:

```bash
cp .dcg/ai-demo/results.json "$DEMO_DIR/ai-results.json"
cp .dcg/ai-demo/model.log "$DEMO_DIR/ai-model.log"
shasum -a 256 contracts/iems.enrollment/v1.json \
  scripts/dcg/fixtures/compatible.json scripts/dcg/fixtures/breaking.json \
  > "$DEMO_DIR/ai-input-hashes.txt"
```

**Existing deterministic path with the model absent:** after the preceding script exits, confirm its model process stopped. The command below invokes no AI at all:

```bash
./scripts/dcg.sh cli check-compat --base contracts/iems.enrollment/v1.json \
  --candidate scripts/dcg/fixtures/breaking.json --mode BACKWARD
printf 'Breaking gate exit without AI: %s\n' "$?"
```

Expected: FAIL/exit 1. This proves the existing CLI's independence. It does not prove that the current AI wrapper displays a graceful warning; that remains planned.

**Reserved commands for later advisory integration — not present today:**

```bash
# Planned only: unified comparison, outage warning and genuine curated fixtures.
python3 scripts/dcg/advisory_rehearsal.py --scenario compatible
python3 scripts/dcg/advisory_rehearsal.py --scenario breaking
python3 scripts/dcg/advisory_rehearsal.py --scenario disagreement
python3 scripts/dcg/advisory_rehearsal.py --scenario unavailable
python3 scripts/dcg/advisory_rehearsal.py --scenario low-confidence
```

Implement a clearly documented exit convention: a rehearsal may return 0 when an expected FAIL was correctly observed, but the actual governance command must still return 1 for incompatibility. Record both values. The unavailable scenario must use a controlled failed endpoint/process and demonstrate the warning plus preserved deterministic result. Disagreement/low-confidence scenarios cannot be marked Ready without actual reproducible model outputs; simulated fixtures belong in labelled integration tests only.

### Reset, limitations and completion criteria

Stop only model/service processes owned by this rehearsal, using their captured identities; do not kill unrelated listeners. Restore any temporary inference configuration and candidate backups. Reuse Phase 1 recovery steps to confirm IEMS still starts and its API flow passes. Never roll back database data blindly to reset a schema demonstration.

Claims that must not be made in either phase:

- DCG automatically monitors or blocks arbitrary manual live database changes.
- Every SQL constraint/index/default is represented by the current snapshot converter.
- The CLI's local recording automatically emits the service webhook.
- A class existing in the service JAR proves that an IEMS integration was tested.
- Model probabilities are calibrated certainty, or the model generated an explanation supplied by deterministic code.
- Simulated disagreement/low-confidence output was produced by the real model.
- The current paired launcher or AI script has no initial model availability dependency.
- Local RC rehearsals prove production readiness, HA, managed failover or certification of all backend combinations.

Phase 2 checklist:

- [ ] Phase 1 is fully green with AI absent.
- [ ] Same exact schemas/hashes are used across both phases.
- [ ] Actual model outputs and deterministic outputs are recorded separately.
- [ ] AI timeout/startup failure yields a warning while the real gate remains authoritative.
- [ ] Genuine disagreement and low-confidence fixtures are captured, or explicitly marked Skipped.
- [ ] If a review threshold is used, its origin and meaning are stated accurately.
- [ ] Recovery restores the advisory layer without changing deterministic results.
- [ ] Evidence contains model/package identity, input hashes, per-seed probabilities, governance exit and run IDs where available, plus sanitized screenshots/logs.

The complete requested Phase 2 is achieved only when all five cases are genuinely demonstrated. A session with Skipped disagreement/low-confidence cases must be reported as partial coverage, even if safe/breaking/outage demonstrations pass. AI-generated explanation/recommendation and consumer prioritization remain excluded until independently implemented and verified; they are not prerequisites for accurately demonstrating the current model's risk predictions.
