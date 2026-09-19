# IEMS live API demo in Postman

Import [the collection](iems-api-collection.json) and [the local environment](iems-demo.postman_environment.json) into Postman. Select **IEMS Demo (local)**, set its `adminPassword` to the same value used for `IEMS_DEMO_ADMIN_PASSWORD` by the API server, and run the **whole collection in order**. The collection shows authentication, schools, students, scholarships, accessibility reports, notifications, and final cleanup. Each request has a status check; key responses also verify the returned record or state. A new run ID avoids name collisions when the demo is repeated.

Start the API against a disposable SQLite database with the `db-demo,db-sqlite` profiles. The example below assumes the application JAR has already been built with `mvn package`:

```sh
mkdir -p .dcg/data
export IEMS_JWT_SECRET="$(openssl rand -base64 48)"
export IEMS_DEMO_ADMIN_PASSWORD="$(openssl rand -base64 24)"
export IEMS_JDBC_URL="jdbc:sqlite:$PWD/.dcg/data/iems-postman-demo.db"
java -jar target/inclusive-education-management-system-1.0.0-SNAPSHOT.jar \
  --spring.profiles.active=db-demo,db-sqlite
```

In another terminal, after the server is healthy, prepare the notification used by the final folder:

```sh
python3 scripts/postman/seed_notification.py .dcg/data/iems-postman-demo.db
```

Seed one notification before **each** full run. Notification creation normally comes from the Kafka consumer, which is disabled in the local database demo. The seed helper creates only that fixture; every API call in the collection still goes through Postman. The demo changes data: it creates users and applications, updates states, deletes a report and notification, deactivates the school, and logs out the student. Use an isolated database.

For a command-line rehearsal with Newman, install it with `npm install --prefix .dcg/tools newman`, then run:

```sh
.dcg/tools/node_modules/.bin/newman run postman/iems-api-collection.json \
  --environment postman/iems-demo.postman_environment.json \
  --env-var "adminPassword=$IEMS_DEMO_ADMIN_PASSWORD"
```

The JSON collection is generated from `scripts/postman/build_collection.py`; regenerate it after edits with `python3 scripts/postman/build_collection.py`. DCG checks are demonstrated separately.

DCG governance and webhook demonstrations use their own collections: [service registry/checks](dcg-governance-collection.json) with [blank local environment](dcg-governance-environment.json), and [webhook delivery](dcg-webhook-collection.json) with [blank local environment](dcg-webhook-environment.json). Follow the verified [service runbook](../docs/service-registry-dashboard-demo.md) and [webhook runbook](../docs/webhook-delivery-demo.md). The DCG collection is kept separate from the IEMS API collection; never export a filled credential environment.

For the Phase 2.2 AI service demo, follow the [advisory runbook](../docs/phase2-ai-advisory-demo.md). The DCG collection has separate real-model, post-restart, controlled-fault and read-only fault-verification folders. The linked `/checks/{runId}/advisory` assertions distinguish optional inference from the authoritative `/checks/{runId}` PASS/FAIL. The exported environment keeps credentials and run IDs blank.
