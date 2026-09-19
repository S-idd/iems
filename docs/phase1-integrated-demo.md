# Final deterministic DCG–IEMS Phase 1 rehearsal

This presenter run uses a selected and verified native development package in
deterministic no-AI mode and
the existing component runners. It is one sequential rehearsal with separate
private evidence for each boundary. The service/dashboard run and webhook run
use different isolated DCG stores and different run IDs; each proves its own
REST/UI or outbox/inbox correlation.

## Prerequisites and one-command run

Use JDK 21, Maven, Python 3 (including `beautifulsoup4`), Node.js, the local
`.dcg/tools/node_modules/newman`, the provisioned `.dcg/maven-repository`, and
an extracted development package with the required Phase 1 capabilities. Package
selection and verification follow the [shared validation contract](dcg-package-validation.md).
Build the current IEMS JAR first;
this is a generated `target/` artifact, not a package or contract edit.

```sh
cd /absolute/path/to/iems
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home
export DCG_HOME="/absolute/path/to/extracted/dcg-package"
export DCG_AI_ENABLED=false
mvn -B -ntp -DskipTests package
python3 scripts/dcg/phase1_integrated_demo.py \
  --dcg-home "$DCG_HOME" \
  --evidence "$PWD/.dcg/rehearsals/phase1-integrated-$(date +%Y%m%d-%H%M%S)"
```

Allow about 3–5 minutes for the automated run and 15–20 minutes to present
the saved evidence. The runner refuses an existing evidence directory, verifies
the selected package before starting a service or changing a disposable fixture,
and keeps evidence directories at mode `0700`. It
records commands and exit codes without credentials. `IEMS_JWT_SECRET`, the
demo admin password, DCG Basic credentials, and webhook authentication are
generated for each isolated process and never written to the top index.

The runner stops its own processes in default mode. If interrupted, run this
one-command cleanup using **that run's exact evidence directory**:

```sh
python3 scripts/dcg/phase1_integrated_demo.py \
  --evidence "$PWD/.dcg/rehearsals/phase1-integrated-<chosen-run>" --cleanup
```

The cleanup command checks the saved process identity before signaling it,
checks recorded ports, and leaves evidence intact. It refuses unrelated PIDs.
After a failed stage, inspect the top-level `results.json` and that stage's
private log, then start a new evidence directory. Never rerun over an existing
one or restore real source candidates from `v1.json`: only disposable copies
are modified and the component runners restore them byte-exactly.

## Presentation sequence

| Show | Expected visible proof | Speaker note |
| --- | --- | --- |
| Baseline terminal and IEMS Postman collection | Four CLI PASS rows, health 200, 55 requests/107 assertions | App data and DCG check history are separate private SQLite files. |
| Compatible proposal | `sourceSystem` addition in real CLI diff, four PASSs, IEMS health 200 | This is deterministic compatibility, not merely REST acceptance. |
| Two breaking proposals and CLI explanation | Enrollment `studentId` and scholarship `amount` FAIL; launcher exit 1; Java dispatches 0; two stable explain IDs | Explain succeeds for a recorded failure while returning exit 1; inspect output and stored IDs. |
| Maven evidence | Compatible `verify` builds a JAR; breaking build fails at plugin `check-compat` in `validate`, with no JAR | Maven fails fast at enrollment and does not report the later scholarship failure. |
| DCG registry, REST and dashboard | Four registered contracts; compatible PASS and breaking FAIL with matching REST/UI run IDs before/after restart | Open saved `service-dashboard/dashboard-evidence/` HTML or reopen the retained service for a live view. |
| Webhook delivery | Failed check ID matches outbox and IEMS inbox; outage `FAILED_RETRYABLE`, restart persistence, manual retry `DELIVERED`, one inbox event | This is manual retry after an outage; it does not prove automatic retry timing. |
| Runtime payload validation | Valid `APPLIED` event PASS/publisher 1; wrong `amount` type FAIL/0; missing `studentId` FAIL/0 | Broker-disabled profile proves handoff, not Kafka delivery. |
| Physical migration | Real IEMS `schools` table: nullable `demo_contact_note` PASS/executor 1; remove required `name` FAIL/executor 0, equal pre/post schema and DB hashes | Governed SQLite runner only; direct administrator SQL can bypass it. |
| Final recovery terminal and Postman | Fresh IEMS health 200; four PASSs; 55 requests/107 assertions; ports released | Source contracts, accepted RC and development package compare byte-identically. |

Use one terminal for the automated runner and a second to inspect the private
index and logs. Import `postman/iems-api-collection.json` for the IEMS screen;
the runner actually executes it twice with in-memory credentials. Import the
separate DCG governance and webhook collections for their respective screens.
The automatically captured dashboard HTML is the rendered response from the
real packaged service. To show a live dashboard after the run, use the
component runbooks' `--serve-existing` commands with the nested
`service-dashboard/` or `webhook-delivery/` evidence path; they print temporary
credentials in the terminal and stop on Ctrl-C. Do not export filled Postman
environments or put those credentials in screenshots.

The evidence index is `<chosen-run>/results.json`. Each scenario links to its
real sub-evidence, including contract/version/run IDs, commands, exit codes,
boundary proof and limits. A missing or failed required sub-result makes the
integrated result incomplete. Migration evidence lives in its own fresh
`.dcg/rehearsals/database-migration-gate-*/` directory and is linked from the
index. It never shares the IEMS app, DCG service, webhook inbox or CLI history
database.

Verified integrated run: `.dcg/rehearsals/phase1-integrated-20260918-145750/results.json`.
It completed all ten required scenarios, with 55 requests and 107 assertions
passing in both the baseline and final IEMS collections. The CLI retained two
failure IDs; Maven built the compatible JAR and stopped the breaking build at
`validate`; the service/dashboard and webhook runs retained their distinct
correlated IDs. Default cleanup released every recorded port, and the explicit
`--cleanup` command also passed. `post-run-verification.json` records 10 passing
orchestration tests, 8 passing Maven-gate tests, syntax checks, both Git
whitespace checks and the cleanup result. The failed preliminary attempts are retained
privately as `phase1-integrated-20260918-144943` (demo-admin readiness race)
and `phase1-integrated-20260918-145022` (Maven disposable copy omitted the
new runtime contract). Both issues were corrected and the complete sequence
was rerun in a fresh directory.

AI is outside Phase 1. The runner sets `DCG_AI_ENABLED=false` and
`SHADOW_INFERENCE_ENABLED=false`, and verifies no Rust model process at the
start, in component runners, and at the end. Verification here is local macOS
ARM64 development behavior, not a published release or PostgreSQL/MySQL
acceptance run. Nothing in this rehearsal commits, tags, pushes, publishes or
deploys artifacts.
