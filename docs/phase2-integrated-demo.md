# Phase 2 integrated DCG–IEMS rehearsal

The original command below is the verified macOS ARM64 rehearsal. For the accepted Linux x86-64 WSL2 archive, use the trust-bound [Linux integrated acceptance](linux-integrated-acceptance.md); it verifies the existing archive-acceptance report and exact archive before running these same 13 IEMS scenarios.

This local macOS ARM64 development rehearsal shows that deterministic DCG owns every PASS/FAIL decision. The Rust model adds an optional advisory label and scores; it never approves a broken schema, starts IEMS, changes Maven packaging, executes SQL, or changes runtime event validation.

## Verified execution map

| Stage | Existing source of truth | Private state and process boundary |
| --- | --- | --- |
| IEMS baseline and recovery | `phase1_integrated_demo.api_run`, full IEMS Newman collection | Fresh disposable project, application SQLite and DCG check-history SQLite; owned IEMS Java and a selected loopback port |
| Real CLI advisory | `advisory_rehearsal.py` | Packaged CLI runs first; owned Rust model starts on a free loopback port, then stops |
| AI-requested startup gate | IEMS `run_demo.sh sqlite` and packaged CLI | Disposable breaking `candidate.json`, dispatch marker, isolated SQLite; byte-exact reset |
| Multiple contracts and explanations | `multiple_contract_demo.py` | Disposable copies; two retained stable run IDs and private history; no IEMS dispatch |
| Maven validate gate | `maven_gate_demo.py --ai-requested` | Disposable source copies, official JSON reports and local plugin repository; no JAR for breaking proposal |
| Service, dashboard, webhook, persistence, faults | `phase2_service_demo.py` | Fresh service SQLite and copied fixtures; real run/advisory/log/dashboard readback after Java restart; dynamic loopback service/model/receiver ports; copied schemas removed after run |
| Runtime APPLIED event | `ScholarshipAppliedEventBoundaryTest` | Private result JSON; publisher handoff assertions; broker disabled |
| Governed migration | `iems_migration_gate.py` | Its own private SQLite evidence directory; safe and breaking reviewed SQL only |

The package is supplied by the caller and checked using the [shared validation contract](dcg-package-validation.md) before any service starts. Validation covers the exact manifest inventory, provenance, native Mach-O ARM64 binary, Java/Rust/model artifacts, feature schema, SBOM/notices and Phase 1 plus Phase 2 capabilities. Both `DCG_AI_ENABLED=false` and `true` run against this one selected package. The runner checks the selected package, accepted RC, approved source contracts and normal IEMS database before and after. It refuses an existing evidence directory. All application ports are chosen dynamically; an already running unrelated Rust process causes a refusal rather than termination.

## Run and recover

From the IEMS root, with Java 21 and the existing local Newman installation:

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
export DCG_HOME="/absolute/path/to/extracted/dcg-package"
EVIDENCE="$PWD/.dcg/rehearsals/phase2-integrated-$(date +%Y%m%d-%H%M%S)"
python3 scripts/dcg/phase2_integrated_demo.py --dcg-home "$DCG_HOME" --evidence "$EVIDENCE"
```

Allow roughly 5–15 minutes on a warmed local machine: Maven copies/builds and two full Postman runs dominate. The runner stops its owned children on normal completion or failure and writes `$EVIDENCE/results.json`. If interrupted, use:

```bash
python3 scripts/dcg/phase2_integrated_demo.py --evidence "$EVIDENCE" --cleanup
```

Inspect any active process marker before manual action. Cleanup only signals a recorded process whose PID, start time, and command identity still match. The service sub-runner also records its active child PIDs. It does not terminate unrelated Java or Rust processes. A failed stage produces `INCOMPLETE` and preserves private evidence for diagnosis.

## Presenter sequence

1. Open `results.json` and `baseline.json`. Show four PASS rows, IEMS health 200, the full Newman count, and Rust absent with `DCG_AI_ENABLED=false`.
2. Open `real-cli.json`. Show the compatible deterministic PASS and breaking `studentId` integer-to-string FAIL alongside the actual three-seed labels, probabilities, artifact hashes, input hashes and computed agreement. Do not call the scores calibrated probabilities.
3. Show `ai-startup-gate.json` and `maven-gate/results.json`: a breaking proposal returns launcher exit 1 with zero IEMS Java dispatches; Maven exits during validate and produces no JAR even with AI requested. Maven is fail-fast and reports its first failure only.
4. Show `multiple-contracts/results.json` and `explain-summary.json`: enrollment and scholarship both fail with separate stable CLI run IDs, while IEMS remains blocked.
5. Show `service/real-breaking.json`, `service/persistence-after-restart.json`, and the `dashboard` verification in `service/results.json`. The REST run, advisory, logs, rendered check page and `CONTRACT_CHECK_FAILED` webhook all share the deterministic run ID. The same run, advisory, logs and dashboard correlation remain available after the Java service restarts. The webhook has no AI authority field.
6. Show `service/unavailable-compatible.json`, `service/unavailable-breaking.json`, `service/timeout.json`, `service/invalid-output.json`, and `service/test-only-disagreement.json`. The latter three are controlled test-only fault/advisory simulations. The SAFE advisory against deterministic FAIL is explicitly marked test-only and enforcement stays FAIL. Normal service startup does not enable the test-only adapter.
7. Show the runtime-validation result (valid publisher handoff 1; wrong-type and missing-required 0), then the migration-gate result (safe SQL executor 1; breaking executor 0, unchanged hashes and sentinel).
8. Finish with `final-recovery.json`, the final Newman log, preservation and cleanup fields. IEMS is healthy with a fresh isolated database after the intentional failures.

The dashboard pages are checked against a live rendered service response during the rehearsal. For a visible screen during a talk, replay the service in a separate disposable presentation session using the package and copied contracts; the integrated runner itself shuts the service down as part of its safety contract. Do not reuse the normal IEMS database.

## Claims and limits

This proves local development behavior on macOS ARM64. The Linux archive has separately passed all 13 native WSL2 package checks; the Linux integrated runner is implemented, and its full WSL2 result must be recorded before claiming Linux IEMS integration acceptance. AI is advisory only; score calibration is unverified. Runtime evidence proves publisher handoff, not Kafka delivery. Webhook retry was previously demonstrated as **manual** retry, not automatic retry. The physical migration gate covers the governed SQLite runner, not unrestricted direct SQL. PostgreSQL/MySQL acceptance remains incomplete. The model supplies risk labels and scores, not explanations or corrections. The package is an unpublished development build; no commit, tag, release, push or deployment is part of this rehearsal.
