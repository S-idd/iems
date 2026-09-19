# Runtime scholarship payload validation (Phase 1)

The genuine boundary is `ScholarshipService.createScholarship`: after saving a new
application it builds a `ScholarshipEvent` with `eventType=APPLIED`, then calls
`ScholarshipAppliedEventBoundary.publish` immediately before the existing
`EventPublisherService.publishScholarshipEvent` handoff. Validation failure throws
the official `ContractPayloadValidationException` before that handoff and the
service transaction rolls back. The normal publisher remains responsible for
Kafka; the `db-demo` profile sets `app.messaging.enabled=false`, so the local
proof is one publisher invocation, not broker delivery.

The runtime schema is `runtime-contracts/iems.scholarship.applied/v1.json`:
contract ID `iems.scholarship.applied`, version `v1`, SHA-256
`723e42c30b0383571d390726b9063f7d3edbc1c30e332fbefc0b96f908d8c95a`.
It describes the seven actual APPLIED event fields and requires all seven.
`amount` must be a number and `timestamp` a string. The existing approved
baseline schemas are unchanged. The dedicated event schema is intentionally
stricter because this producer always sets those fields.

The integration uses the official DCG
`com.ideas.contracts:contract-validation-spring-boot-starter:4.0.0-rc.1`, built
locally from the DCG source. It is not part of the installed no-AI CLI package;
a fresh machine must install/build that Maven artifact before compiling IEMS.
The starter's actual properties are `contract.validation.enabled` and
`contract.validation.contracts-root`. IEMS exposes them as
`DCG_RUNTIME_VALIDATION_ENABLED` (default `false`) and
`DCG_RUNTIME_CONTRACTS_ROOT` (default `runtime-contracts`). Run from the IEMS
repository root, or set the latter to an absolute path. The dedicated mapper
is shared by the boundary and Kafka value serializer. It writes ISO timestamp
strings; the prior default Kafka serializer wrote timestamp arrays and would
not have matched the contract. The focused test validates the actual serialized
Kafka JSON against the schema, including number semantics and field names.

## Rehearsal

```sh
cd /absolute/path/to/data-contract-governance
JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home \
  ./mvnw -B -ntp -pl contract-validation-spring-boot-starter -am -DskipTests install

cd /absolute/path/to/iems
evidence_dir=$(mktemp -d "$PWD/.dcg/rehearsals/runtime-validation-$(date +%Y%m%d-%H%M%S)-XXXXXX")
IEMS_DCG_RUNTIME_EVIDENCE="$evidence_dir" DCG_AI_ENABLED=false \
  JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home \
  mvn -B -ntp -Dtest=ScholarshipAppliedEventBoundaryTest test \
  > "$evidence_dir/application-log.txt" 2>&1
JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home mvn -B -ntp test
```

The test uses a real `ScholarshipEvent` and serializer for the valid case.
Because Java's `BigDecimal` field cannot hold a string, the wrong-type and
missing-field cases use the controlled serialized JSON seam immediately before
the same official validator and publish action. They are not HTTP endpoints.
The test double counts handoffs: valid `PASS/1`, wrong `amount` type `FAIL/0`
with `$.amount`, and missing `studentId` `FAIL/0` with a required-property
error. Null `amount` also fails. The off-default test confirms normal handoff
when validation is disabled. The full IEMS test suite also loads the Spring
context without a broker under its test configuration.

Private evidence from the final 2026-09-18 rehearsal is under
`.dcg/rehearsals/runtime-validation-20260918-142212-gKTGXz/` (ignored by Git).
Its `results.json` summarizes hashes, validation outcomes, handoff counts,
configuration, tests and process observation. The three scenario JSON files
contain demo payloads and deterministic error paths; `application-log.txt`
and `iems-full-test-log.txt` contain the focused and full test results.
Focused tests: 6/6; full IEMS tests: 20/20.
`DCG_AI_ENABLED=false` was set, no AI integration was called, and `pgrep` found
no DCG model/Rust process. No broker or Rust process was started by this run.

For a live IEMS run, enable validation explicitly with
`DCG_RUNTIME_VALIDATION_ENABLED=true`; use the existing `db-demo` profile to
keep messaging disabled. Present the successful application handoff as
**publisher invocation**, not Kafka delivery. The malformed scenarios are
developer rehearsal tests at the serialized boundary, not public Postman
requests. Reset by unsetting `DCG_RUNTIME_VALIDATION_ENABLED` or leaving its
default false. The rehearsal has no running processes or changed database to
clean up; retain the ignored evidence directory for review.

Known limit: this validates only the APPLIED scholarship producer path. Other
event types and consumer paths are not governed here. The event is validated
before the publisher call, but this local no-broker profile cannot establish
delivery acknowledgments. Next separate Phase 1 task: a physical database
migration gate against an actual IEMS business table.
