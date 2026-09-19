# DCG webhook notification and delivery demo (Phase 1, no AI)

This rehearsal connects the **real packaged DCG notification outbox** to a separate, protected **IEMS DCG event inbox**. A failed compatibility check creates `CONTRACT_CHECK_FAILED`. DCG persists a delivery record, sends the event to IEMS, and shows delivery status in its API and dashboard. A second check runs while IEMS is down; its retryable delivery survives a DCG restart and is manually retried after IEMS returns. The original run, delivery and event IDs remain the same.

Webhooks report DCG events. They do **not** watch a live database for manual DDL changes. The IEMS `/api/notifications` user inbox is unrelated and remains untouched.

## Components and routes

```text
POST /checks → DCG FAIL result → DCG SQLite outbox → webhook HTTP POST
                                                     ↓
                                        IEMS /api/dcg/webhook
                                                     ↓
                                    separate IEMS DCG inbox SQLite

DCG /api/notification-deliveries ↔ IEMS /api/dcg/events
DCG /ui/notifications displays the delivery history
```

The IEMS receiver is compiled into the actual application JAR. It is available **only** with Spring profile `db-demo` and `--iems.dcg.webhook.enabled=true`. Both the webhook POST and inbox GET require a one-run `Authorization` header whose exact value is generated in memory. An unauthorized request returns 401. The receiver stores DCG event payloads in its own SQLite file, deduplicates repeated event IDs/keys, and persists across IEMS restarts. It accepts operational DCG events other than failed checks as well, because registration and version publication emit events when notifications are enabled. The demo filters by `runId` and `eventType=CONTRACT_CHECK_FAILED` when correlating a check.

| API | Purpose |
| --- | --- |
| DCG `POST /checks`, `GET /checks/{runId}` | Queue then poll the actual compatibility check |
| DCG `GET /api/notification-deliveries?runId=…&sink=webhook` | Inspect persisted delivery and nested event |
| DCG `POST /api/notification-deliveries/{deliveryId}/retry` | Explicitly requeue a failed delivery |
| DCG `GET /ui/notifications?runId=…` | View the real delivery dashboard |
| IEMS `POST /api/dcg/webhook` | Protected DCG event receiver |
| IEMS `GET /api/dcg/events?runId=…&eventType=…` | Protected, read-only demo inbox |

The service uses `notifications.enabled=true`, `notifications.sinks=webhook`, and a URL/auth-header **environment-variable reference**. Its payload contains `eventId`, `eventType`, `contractId`, `runId`, schema versions, summary, and breaking changes. Secrets never appear in Java command arguments, saved reports, or exported Postman environments.

## Exact rehearsal command

Prerequisites: JDK 21, Python 3, Node.js, local Newman at `.dcg/tools/node_modules/newman`, and the verified development DCG package. From the IEMS repository, build the application JAR and run on a **new** evidence path:

```sh
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home
mvn -B -ntp -Dtest=DcgWebhookInboxTest package
python3 scripts/dcg/webhook_delivery_demo.py \
  --evidence "$PWD/.dcg/rehearsals/webhook-delivery-$(date +%Y%m%d-%H%M%S)"
```

The script refuses an existing evidence directory. It verifies the DCG package manifest, uses available loopback ports, creates private task-owned state, generates one-run credentials, starts the actual IEMS and DCG JARs, waits for both health endpoints, and stops only their process groups. DCG check/history is `runtime/checks.db`; DCG contract files are `runtime/contracts/`; the IEMS application database is `runtime/iems-app.db`; the **separate** IEMS DCG inbox is `runtime/iems-dcg-inbox.db`. No existing personal database is opened. Evidence directories are `0700` and files are `0600`.

The runner performs these assertions in order:

1. Missing IEMS webhook authorization returns 401; the inbox starts empty.
2. Register approved `iems.enrollment` `v1`, then publish the pinned `studentId: integer → string` `v2` proposal in an **isolated non-strict DCG registry**. Strict publication normally rejects this proposal before a queued check; the relaxed setting is only for this REST failure demonstration.
3. Submit a real check, poll `QUEUED` to `FAIL`, then match its run ID, contract ID and event ID across DCG delivery `DELIVERED` and the IEMS inbox.
4. Stop IEMS, submit another failed check with a distinct commit SHA, and observe DCG `FAILED_RETRYABLE` after its first HTTP attempt. The compatibility result remains `FAIL` while the receiver is unavailable.
5. Restart DCG against its original SQLite outbox while IEMS remains down; the same failed `deliveryId` persists. Restart IEMS against its original inbox and confirm the first event remains there.
6. Call DCG's real retry API, wait for the **same** delivery to reach `DELIVERED` on attempt 2, and confirm one matching event in IEMS. This proves a manual recovery path; automatic retry timing is configured but is **not** claimed as separately demonstrated here.
7. Confirm the DCG `/ui/notifications` page shows the retried run and `DELIVERED`, the IEMS user `notifications` table still has zero rows, and the read-only Postman verification succeeds.
8. Stop both owned services, release both ports, and confirm no Rust model started and the source contracts, package, and built IEMS JAR stayed unchanged.

A completed run retains `results.json`, all four isolated stores, sanitized check/delivery/inbox JSON in `evidence/`, real `dcg-notifications.html`, Newman output, and service logs. The private local report `.dcg/rehearsals/webhook-delivery-20260918-04/results.json` records the exact IDs and both before/after states. That run used DCG port `56340` and an isolated IEMS loopback port; both are now released.

## Show the retained data live

The automated run stops its services. To reopen the completed state for a browser/Postman presentation:

```sh
python3 scripts/dcg/webhook_delivery_demo.py \
  --evidence "$PWD/.dcg/rehearsals/webhook-delivery-20260918-04" \
  --serve-existing
```

The command verifies the package and exact IEMS JAR hash, starts both JARs with the retained stores, and prints new loopback URLs and temporary credentials **to the terminal only**. Open the printed DCG `/ui/notifications` URL to show the two delivery records. Use the printed IEMS inbox URL/header to inspect matching events. Press **Ctrl-C** to stop both. Do not put the printed secret values into a saved document or exported Postman environment.

Import the separate [webhook collection](../postman/dcg-webhook-collection.json) and [blank environment](../postman/dcg-webhook-environment.json). Fill its local variables from the running presentation and the report's two run IDs. The collection only reads health, DCG check/delivery/UI state, IEMS inbox state, and the expected unauthorized response; it contains no retry/reset request. Automated verification injects credentials in memory through `scripts/postman/run_dcg_webhook_collection.js`. The verified run passed **9 requests and 17 assertions** with zero failures.

## Tests and limits

```sh
IEMS_DCG_WEBHOOK_EVIDENCE="$PWD/.dcg/rehearsals/webhook-delivery-20260918-04" \
  python3 -m unittest discover -s scripts/dcg -p 'test_webhook_delivery_demo.py' -v

# From the DCG source repository, with JAVA_HOME set to JDK 21:
./mvnw -B -ntp -pl contract-service -am \
  -Dtest=PolicyPackRegistryNotificationTest,WebhookNotificationSinkTest,PolicyPackNotificationIntegrationTest,NotificationServiceTest,NotificationOutboxStoreTest \
  -Dsurefire.failIfNoSpecifiedTests=false test
```

The IEMS receiver's own `DcgWebhookInboxTest` covers missing authorization, malformed payloads, duplicate delivery, conflict handling, SQLite persistence, and controller HTTP statuses. The exact local rehearsal is a single-node SQLite demo. It does not establish production webhook authentication, external delivery, automatic retry timing, PostgreSQL/MySQL behavior, or continuous detection of database DDL. Runtime payload validation and governed physical migrations remain separate work.
