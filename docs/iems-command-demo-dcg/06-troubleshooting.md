# 06 — Troubleshooting the local demo

All inspection commands below are **read-only**, safe during the live presentation, and create no new evidence. They work with either AI mode unless a row says otherwise. Keep log output in a private terminal; do not paste credentials, token-bearing Postman traces or raw schemas into slides. If a runner fails, keep its evidence and rerun with a **new** path after addressing the cause. Use [05 — start, stop and reset](05-start-stop-reset.md) for identity-checked cleanup.

| Problem | Verified check and fix | AI / expected result / recovery |
| --- | --- | --- |
| Port already in use | Inspect 8080/8081/8090 with `lsof` below. Packaged DCG uses fixed 8080/8081; use a dynamic-port component/integrated runner if occupied. Change only `IEMS_PORT` for a fresh IEMS foreground start. | Either mode. Do **not** kill another listener. |
| DCG service not ready | Run package `status` with the same `DCG_DATA_DIR`, inspect its private Java log and health response. | Java must report `RUNNING`/health 200. Stop only this launcher with `bin/stop`, then restart if needed. |
| Rust advisory unavailable | `status` distinguishes `AVAILABLE`, `UNAVAILABLE` and no-AI `DISABLED`; inspect private Rust log. | Deterministic Java can remain healthy. For controlled outage proof use [04](04-extended-fault-scenarios.md); never claim missing advice is a PASS/FAIL decision. |
| IEMS health fails | Check live health and the private `IEMS_DEMO_STATE/iems.log`. Verify four gate checks passed and the isolated SQLite URL/port were set. | Either mode. A breaking contract intentionally blocks Java before health; recover by running a new disposable rehearsal, not editing approved source contracts. |
| Postman/Newman failure | Inspect the runner's private `baseline-newman.log` or `final-recovery-newman.log` and `results.json`. | Integrated runner injects the one-run admin password in memory and seeds a notification. Manual Postman must use the **same** server password and seed before each full run. Stop/restart with new evidence if state is contaminated. |
| Candidate reset issue | Read `multiple-contracts/results.json` for `automatic_reset_exact` and source/package preservation. | Phase 1 runner edits only a temporary copy. Do not overwrite a source `candidate.json` from `v1.json`; it may contain an intentional proposal. Run a new evidence directory. |
| Maven gate output confusing | Read `maven-gate/results.json` and `multiple-breaking/build.log`. | Expected breaking `validate` exit is 1 and no JAR. Maven is fail-fast; the separate CLI runner proves both failures. |
| Dashboard cannot be reached | Check live DCG health/status and use the URL **printed by the current launcher or `--serve-existing`**, not a saved port from another rehearsal. | Either mode. `/ui` may demand Basic auth even when `/actuator/health` is public. Use the current one-run credentials locally; stop with Ctrl-C or `bin/stop` as appropriate. |
| Evidence appears missing or incomplete | Inspect private directory permissions, `results.json` `current_stage`/`error`, and the stage log. | An `INCOMPLETE` result is not a demonstration PASS. Preserve it, clean only owned processes, and use a fresh directory. |

## Exact read-only checks

Use these from the IEMS repository after setting `DCG_HOME` and the relevant evidence variables from the other guides:

```bash
cd /absolute/path/to/iems
lsof -nP -iTCP:8080 -sTCP:LISTEN
lsof -nP -iTCP:8081 -sTCP:LISTEN
lsof -nP -iTCP:8090 -sTCP:LISTEN
```

An empty result/exit 1 means no listener; a reported PID may be unrelated. These commands create no evidence or cleanup action. For the packaged DCG instance **only when `DCG_DATA_DIR` points to its isolated state**:

```bash
"$DCG_HOME/bin/status"
curl --noproxy '*' -i http://127.0.0.1:8080/actuator/health
tail -n 80 "$DCG_DATA_DIR/logs/java.log"
tail -n 80 "$DCG_DATA_DIR/logs/rust.log"
```

`status`/health should identify Java readiness and advisory state; logs are private evidence, not shareable output. In no-AI mode `rust.log` may not exist—that is expected. If the service is unhealthy, use `"$DCG_HOME/bin/stop"` with that same `DCG_DATA_DIR` before a restart; do not signal arbitrary Java/Rust PIDs. For the foreground IEMS instance created in [05](05-start-stop-reset.md):

```bash
curl --noproxy '*' -i "http://127.0.0.1:${IEMS_PORT}/actuator/health"
tail -n 80 "$IEMS_DEMO_STATE/iems.log"
```

Expected healthy response HTTP 200. This reads only the disposable app's log. Stop that foreground IEMS with Ctrl-C in its own terminal; if startup failed before Java dispatch, inspect gate output in this log and start a fresh isolated session.

For an integrated Phase 2 result or a Postman failure, inspect the private index and relevant log without dumping the whole environment:

```bash
python3 -c 'import json,os,pathlib; p=pathlib.Path(os.environ["PHASE2_EVIDENCE"])/"results.json"; r=json.loads(p.read_text()); print(r.get("overall_result"),r.get("current_stage"),r.get("error"),r.get("cleanup"))'
tail -n 80 "$PHASE2_EVIDENCE/baseline-newman.log"
tail -n 80 "$PHASE2_EVIDENCE/final-recovery-newman.log"
```

`baseline-newman.log` and `final-recovery-newman.log` exist only after those stages run; a missing later file can simply mean the runner stopped earlier. Retain these private logs. The collection order, one-run admin password and notification seed are handled by `scripts/postman/run_iems_integrated_collection.js` and the integrated runner. Do not export a filled Postman environment.

For candidate reset, Maven and evidence permissions:

```bash
python3 -c 'import json,os,pathlib; p=pathlib.Path(os.environ["PHASE1_EVIDENCE"])/"multiple-contracts/results.json"; r=json.loads(p.read_text()); print(r.get("automatic_reset_exact"),r.get("blocking_exit"),r.get("blocked_java_dispatch_count"))'
python3 -m json.tool "$PHASE1_EVIDENCE/maven-gate/results.json"
tail -n 80 "$PHASE1_EVIDENCE/maven-gate/multiple-breaking/build.log"
stat -f '%Sp %N' "$PHASE2_EVIDENCE" "$PHASE2_EVIDENCE/results.json"
```

Expected reset `True`, breaking exit 1, Java dispatch 0; Maven's breaking scenario has no JAR. Evidence directory should be owner-only (`drwx------`) and results file owner-only (`-rw-------`). For a different component run, replace the path with its **actual** evidence directory; never mix run IDs or ports from two isolated stores.

Finally, if the package itself is questioned, verify its manifest **without editing it**:

```bash
(cd "$DCG_HOME" && shasum -a 256 -c SHA256SUMS)
```

Expected every file `OK`. This is read-only, works in either AI mode, creates no evidence, and needs no cleanup. If any file differs, stop the presentation and investigate; do not repair the accepted RC or overwrite the development package in place.
