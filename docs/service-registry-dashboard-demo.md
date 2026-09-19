# DCG service, registry, dashboard, and Postman rehearsal (Phase 1, no AI)

This rehearsal exercises the **packaged DCG service**, its actual REST API, SQLite-backed check history, filesystem contract registry, and Thymeleaf dashboard. It uses the verified IEMS development package and keeps all state under a new private `.dcg/rehearsals/service-registry-dashboard-*` directory. The IEMS application database is not opened. No webhook, Rust process, or inference is needed.

## Verified component flow and endpoint inventory

```text
Postman / Python HTTP client --Basic auth--> packaged contract-service JAR
                                        ├── /contracts registry → rehearsal runtime/contracts
                                        ├── /checks async queue → rehearsal runtime/checks.db
                                        └── /ui rendered dashboard → same registry and history
```

The package includes the UI templates and static assets. Its `bin/start` defaults to port 8080; the rehearsal launches the **same packaged JAR** directly on an available loopback port to isolate state and avoid a port conflict. Health is `GET /actuator/health` (no Basic authentication); registry, check, and UI routes require Basic authentication. The relevant routes are:

| Purpose | Method and route | Result |
| --- | --- | --- |
| Register contract and immutable `v1` | `POST /contracts` | `201`; registration itself creates the first version |
| List/detail | `GET /contracts`, `GET /contracts/{id}` | `200` |
| Version history/schema | `GET /contracts/{id}/versions`, `GET /contracts/{id}/versions/{v}` | `200` |
| Publish next version | `POST /contracts/{id}/versions` | `201`, monotonic `v1`, `v2`, … |
| Submit check | `POST /checks` | `202 QUEUED`, unique `runId`; acceptance is not PASS |
| List/poll run | `GET /checks`, `GET /checks/{runId}` | Poll QUEUED/RUNNING until PASS/FAIL |
| Run logs | `GET /checks/{runId}/logs` | Persistent JSON log array |
| Rendered UI | `GET /ui`, `/ui/contracts`, `/ui/contracts/{id}`, `/ui/checks/{runId}` | `200` HTML |

Registry schemas and metadata are files under `runtime/contracts`; check runs and logs use `runtime/checks.db`. These are **two DCG stores**, both isolated from the IEMS application database. The package does not need an external database, S3, or model for this flow.

The demo passes `--contracts.validation.strict-mode=false` **only in the isolated rehearsal**. Normally strict publication rejects an incompatible version before a queued service check can compare it. Here the pinned breaking enrollment `v2` is stored as an explicit proposal so `POST /checks` can produce a real persisted FAIL. This is a presentation configuration, not a claim that incompatible publication is safe or approved in strict mode. All four approved baseline schemas stay byte-identical.

## Run and review

Prerequisites: JDK 21, Python 3 with `beautifulsoup4`, Node.js, the already installed `.dcg/tools/node_modules/newman`, and an extracted DCG package with the required service/dashboard capabilities. The script applies the [shared package validation contract](dcg-package-validation.md) before starting. It refuses an existing evidence directory and does not overwrite existing history.

From the IEMS repository:

```sh
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home
export DCG_HOME="/absolute/path/to/extracted/dcg-package"
export DCG_AI_ENABLED=false
python3 scripts/dcg/service_registry_demo.py \
  --dcg-home "$DCG_HOME" \
  --evidence "$PWD/.dcg/rehearsals/service-registry-dashboard-$(date +%Y%m%d-%H%M%S)"
```

This is the start/status/stop workflow: the script verifies checksums, starts its own Java process, waits for `/actuator/health`, performs the API and UI checks, captures Newman verification, stops only that process group, verifies the port is free, restarts on the retained state, verifies persistence, then stops it again. The status and all selected ports are in `results.json`; live status is the health endpoint while the script is running. It generates a random local Basic password in process memory and never writes it to a committed file, command argument, report, or exported environment. `APP_SECURITY_USERNAME` and `APP_SECURITY_PASSWORD` are passed only as child environment variables. The command includes `DCG_AI_ENABLED=false`, `SHADOW_INFERENCE_ENABLED=false`, and `--shadow.inference.enabled=false`; the runner verifies no `dcgaimodel` process before, during, or after. `--notifications.enabled=false` keeps webhooks out of scope.

To reopen the retained run for a **live browser presentation**, use the command below. It verifies the package, starts the same service against the retained state on a new free loopback port, and prints its URL and one-time Basic credentials to your terminal only. Open that URL in a browser; `GET /actuator/health` at the printed port is the status check. Press **Ctrl-C** to stop only that service. Do not copy the printed password into screenshots, logs, or exported Postman environments.

```sh
python3 scripts/dcg/service_registry_demo.py \
  --dcg-home "$DCG_HOME" \
  --evidence "$PWD/.dcg/rehearsals/service-registry-dashboard-20260918-04" \
  --serve-existing
```

A completed rehearsal retains `runtime/checks.db`, `runtime/contracts`, REST responses/logs in `evidence/`, actual authenticated rendered HTML in `dashboard-evidence/before` and `dashboard-evidence/after`, Newman logs in `postman/`, and `results.json`. All are private (directories `0700`, files `0600`). `results.json` reports `PASS` only after restart and cleanup succeed. A failed run exits nonzero with a clear error and retains its evidence. Use a **new path** to repeat; do not interpret an unexpected registration `409` as success.

For a deliberate reset **after the service has stopped**, remove only the owned runtime state and retain evidence:

```sh
python3 scripts/dcg/service_registry_demo.py \
  --evidence "$PWD/.dcg/rehearsals/service-registry-dashboard-<chosen-run>" --reset
```

The reset checks its marker, directory name, and recorded released-port status before deleting that run's `runtime/`; it never touches the source contracts, accepted RC, installed package, IEMS application database, or another rehearsal.

## Presenter walkthrough

The script registers `iems.accessibility`, `iems.enrollment`, `iems.notification`, and `iems.scholarship` using the approved `contracts/iems.*/v1.json` schemas. `POST /contracts` creates `v1` atomically; no second baseline publication is sent. Every retrieved `v1` is parsed and compared with the submitted JSON, and both canonical schema hashes are recorded. Metadata genuinely defined by IEMS is `ownerTeam=iems`, `domain=education`, `compatibilityMode=BACKWARD`. There is no separate registry-generated contract ID or display-name field; the contract ID is the identifier. The service's timestamps live in its REST responses, and run creation/finish timestamps are in each check result.

The compatible proposal adds optional `sourceSystem: string` to `iems.scholarship` and is first checked by the deterministic CLI, then published as `v2`. The pinned breaking `iems.enrollment` proposal changes `studentId` from integer to string and is published as `v2` in the isolated non-strict registry. Both are submitted through `POST /checks` with `baseVersion=v1`, `candidateVersion=v2`, `mode=BACKWARD`. The service returns `202 QUEUED`, after which the runner polls `GET /checks/{runId}` until the scholarship result is PASS and the enrollment result is FAIL. It fetches `/logs` for both and confirms the failed result names `studentId (integer -> string)`. Retrieval does not create additional checks.

Open the saved `dashboard-evidence/before/*.html` in a browser to inspect the **real rendered responses captured from the packaged server**, or use `--serve-existing` and open its live authenticated `/ui` URL. The runner requests `/ui`, `/ui/contracts`, `/ui/contracts/iems.enrollment`, and each `/ui/checks/{runId}` while the server is live. It checks the four contract IDs on the registry page, `v1` and `v2` on enrollment details, each full run ID/status, and the breaking field on the FAIL page. The REST IDs are recorded in `results.json`; the matching actual HTML is retained before and after restart. These are rendered server pages, not mockups. The authenticated pages are captured as HTML rather than screenshots because credentials are deliberately not exported to a browser profile.

The script then gracefully stops the service, confirms the port is free, and restarts the same JAR against the **same isolated storage**. It retrieves all contracts, versions, runs, logs, and UI pages using the original IDs, verifies no extra runs, runs Newman verification again, and stops the owned process. The service port changes between independent rehearsals; use the port in each run's `results.json`. The completed 2026-09-18 rehearsal used port `55954` and exited with the port released.

## Postman/Newman

Import [DCG governance collection](../postman/dcg-governance-collection.json) and [DCG local environment](../postman/dcg-governance-environment.json) separately from the existing IEMS API collection. The exported environment has blank credential fields. For a live manual run, enter the current isolated service URL and task-specific Basic credentials **in Postman's local environment only**. Do not export the filled environment. The collection has:

- **Register and check (fresh isolated service only):** health, auth, four registrations, list/retrieve baselines, publish/retrieve two proposals, submit both async checks, bounded polling, results and logs. Run once against a fresh service. No destructive reset request is in the collection.
- **Verify existing rehearsal:** 13 read-only requests for the four contracts, versions, both results/logs, and matching real dashboard pages. Run before and after restart using the original run IDs.

For automated verification the runner calls `scripts/postman/run_dcg_collection.js`, which loads the exported environment into memory and injects the one-run password from its process environment. The password is not passed on the command line or exported to a file. The 2026-09-18 full fresh-service Newman setup run passed **43 requests / 104 assertions**, zero failures. The read-only folder passed **13 requests / 25 assertions** before restart and the same after restart. Its logs are under the private evidence paths.

`postman/dcg-governance-collection.json` is generated by `python3 scripts/postman/build_dcg_collection.py`. Rebuild only when the source fixtures or requests intentionally change. Keep the existing IEMS API Postman collection independent.

## Tests and evidence

```sh
IEMS_DCG_SERVICE_EVIDENCE="$PWD/.dcg/rehearsals/service-registry-dashboard-20260918-04" \
  python3 -m unittest discover -s scripts/dcg -p 'test_service_registry_demo.py' -v

# From the DCG repository, with JAVA_HOME set to JDK 21:
./mvnw -B -ntp -pl contract-service -am \
  -Dtest=ContractServiceApiIntegrationTest,UiControllerIntegrationTest,CheckRunnerIntegrationTest,CheckRunStoreSqliteContractTest \
  -Dsurefire.failIfNoSpecifiedTests=false test
```

The private local report `.dcg/rehearsals/service-registry-dashboard-20260918-04/results.json` records the two run IDs, schema hashes, REST and dashboard correlations, persistence, unchanged source/package inventories, absence of Rust, and released port. The full Postman write/poll run is in `.dcg/rehearsals/service-registry-dashboard-postman-full-20260918-01/`.

The current service does not continuously discover manual DDL changes in an IEMS database. This task does not enable webhooks, runtime payload validation, physical migration gating, PostgreSQL/MySQL matrices, S3, CI/OIDC, or AI. The next separate Phase 1 task is **webhook notification and delivery verification**.
