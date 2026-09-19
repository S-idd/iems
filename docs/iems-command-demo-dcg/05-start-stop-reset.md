# 05 — Start, stop and reset safely

Use one isolated state directory per live session. Run the foreground IEMS and background packaged DCG service in **separate terminals**. Do not start the packaged service while an integrated runner is active. Its launcher uses fixed loopback ports **8080 (Java/dashboard)** and **8081 (Rust)**; if either is occupied, leave that listener alone and use the dynamic-port integrated/component runners instead.

| Command group | Demonstrates / expected result | AI | Evidence | Live-safe / stop or recover |
| --- | --- | --- | --- | --- |
| IEMS foreground | Four CLI PASSs, then IEMS health 200. | Chosen by `DCG_AI_ENABLED`; deterministic startup gate in both modes. | Fresh `IEMS_DEMO_STATE` SQLite/logs. | Yes after port preflight; Ctrl-C stops this foreground app. |
| DCG launcher/status | Java health and optional Rust status; `/ui` is same Java service. | `true` for real advisory; `false` for no-AI. | Fresh `DCG_DATA_DIR`, private password/logs. | Yes only with 8080/8081 free; stop with same package/state `bin/stop`. |
| Health/process checks | Inspect ownership and ports; no mutation. | Both. | Read-only. | Yes; never use `pkill` or stop an unrelated PID. |
| Runner cleanup | Release only identity-checked task-owned children after interruption. | Runner controls mode. | Retains evidence. | Yes; use exact evidence path. |
| Disposable reset | Delete only a marker-verified standalone IEMS state or Phase 1 service runtime. | Stopped. | Intentional deletion of selected disposable data. | Only after process/port checks; integrated evidence is retained. |

## Foreground IEMS startup and health

From Terminal A, with an already built `target/inclusive-education-management-system-1.0.0-SNAPSHOT.jar`:

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
DCG_AI_ENABLED=false scripts/database/run_demo.sh sqlite > "$IEMS_DEMO_STATE/iems.log" 2>&1
```

Expected: `lsof` prints no listener before starting (exit 1 means free); `run_demo.sh` lints/checks all four contracts before Java starts. It remains foreground and writes a private `iems.log`. Choose `DCG_AI_ENABLED=true` on the last line to request advisory mode; **IEMS still makes its startup decision through deterministic DCG**. If 8090 is occupied, choose another unused `IEMS_PORT` before running, without stopping the other process. No credential value is printed by these commands; the generated secrets remain in this shell's environment. The database is under private `IEMS_DEMO_STATE`, not `.dcg/data/iems.db`.

From Terminal B, check the live IEMS health:

```bash
curl --noproxy '*' -i http://127.0.0.1:8090/actuator/health
```

Expected HTTP **200** and `UP`. This is read-only, creates no evidence, and needs no cleanup. Stop IEMS by pressing **Ctrl-C in Terminal A**; do not kill a PID found by a broad process search. For Postman/Newman, use the credential-safe integrated runner in [01](01-quick-live-demo.md), which seeds the notification fixture and runs the entire collection in memory.

## Packaged DCG service, dashboard and Rust status

After the IEMS foreground app is stopped or in another free-port terminal, create an isolated DCG state. `lsof` must show no listeners on both fixed ports before the start command:

```bash
export DCG_DATA_DIR=$(mktemp -d "$PWD/.dcg/rehearsals/dcg-service-live-$(date +%Y%m%d-%H%M%S)-XXXXXX")
lsof -nP -iTCP:8080 -sTCP:LISTEN
lsof -nP -iTCP:8081 -sTCP:LISTEN
DCG_AI_ENABLED=true "$DCG_HOME/bin/start"
"$DCG_HOME/bin/status"
curl --noproxy '*' -i http://127.0.0.1:8080/actuator/health
open http://127.0.0.1:8080/ui
```

Expected: Java `RUNNING`, deterministic enforcement `ACTIVE`, health HTTP **200**, and real Rust `AVAILABLE` if readiness succeeds. If Rust is unavailable, Java remains healthy and status says `UNAVAILABLE`; do not present a fabricated prediction. The dashboard is part of the Java service—there is no separate dashboard process. The launcher prints the isolated password-file path; the browser prompts for `demo` and that one-run password. Keep it local and do not copy it into saved Markdown or exported Postman environments. To show an actual service check/advisory, follow the isolated fixture/Postman steps in [03](03-phase2-ai-advisory-demo.md); starting the service alone has no new check run.

Stop this **task-owned service and its Rust advisory process** using the same `DCG_DATA_DIR` and package:

```bash
"$DCG_HOME/bin/stop"
"$DCG_HOME/bin/status"
```

Expected: first command reports stopped and retains isolated state; second reports Java stopped (its exit 1 is expected). `bin/stop` checks saved process identity before signaling. Use it only for the instance this guide started; do not use `pkill`, `killall`, or an unrelated PID. To demonstrate no-AI mode, stop first, then run `DCG_AI_ENABLED=false "$DCG_HOME/bin/start"`, `"$DCG_HOME/bin/status"`, and `"$DCG_HOME/bin/stop"` against the **same isolated state**. Expected status: `DISABLED`, Rust `STOPPED`. Switching modes while running is rejected by the launcher.

Read-only process/port inspection:

```bash
"$DCG_HOME/bin/status"
lsof -nP -iTCP:8080 -sTCP:LISTEN
lsof -nP -iTCP:8081 -sTCP:LISTEN
```

`status` checks the launcher-owned PID/start-time/command identity. `lsof` lists **any** listener on those ports, including unrelated processes; it grants no permission to stop them. The commands create no evidence and need no recovery.

## Interrupted runners and safe disposable reset

Use the **exact path from the interrupted run**; never substitute the normal data directory. Each cleanup command checks a task marker and owned process identity before signaling, retains evidence, and should leave ports released:

```bash
python3 scripts/dcg/phase1_integrated_demo.py --evidence "$PHASE1_EVIDENCE" --cleanup
python3 scripts/dcg/phase2_integrated_demo.py --evidence "$PHASE2_EVIDENCE" --cleanup
python3 scripts/dcg/phase2_service_demo.py --evidence "$AI_SERVICE_EVIDENCE" --cleanup
```

Run only the line for the evidence variable you actually set. For a packaged service interruption, use `"$DCG_HOME/bin/stop"` with its original `DCG_DATA_DIR`. If cleanup reports an identity mismatch or an unrelated listener, stop and inspect the private logs and [troubleshooting](06-troubleshooting.md); do not override it with a broad kill command.

The Phase 1 service runner has a guarded reset that removes only its **stopped** rehearsal `runtime/` directory, while retaining its results:

```bash
python3 scripts/dcg/service_registry_demo.py --evidence "$SERVICE_EVIDENCE" --reset
```

Expected: reset succeeds only for the named, completed Phase 1 service rehearsal with a released port. AI is disabled there. The script checks its marker/path before deleting. For a standalone IEMS live directory created above, stop foreground IEMS first, then use this guarded deletion; it refuses paths outside `.dcg/rehearsals`, missing markers and an occupied IEMS port:

```bash
python3 - <<'PY'
import os, shutil, socket
from pathlib import Path
root = (Path.cwd() / '.dcg/rehearsals').resolve()
target = Path(os.environ['IEMS_DEMO_STATE']).resolve()
assert target.parent == root and target.name.startswith('iems-live-')
assert (target / '.iems-live-demo-marker').is_file()
with socket.socket() as sock:
    assert sock.connect_ex(('127.0.0.1', int(os.environ['IEMS_PORT']))) != 0, 'IEMS port still active'
shutil.rmtree(target)
print('Removed only', target)
PY
```

This intentionally removes only the selected disposable IEMS SQLite/log directory and creates no new evidence. Retain integrated rehearsal evidence for the presentation. None of these commands removes source contracts, `.dcg/data/iems.db`, a package, or the accepted RC.
