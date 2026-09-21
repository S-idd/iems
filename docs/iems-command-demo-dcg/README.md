# IEMS + DCG presenter command guides

These commands present the **verified local macOS ARM64 development demo**. Work from the IEMS repository root, represented below as `/absolute/path/to/iems`. Start with [01 — quick live demo](01-quick-live-demo.md); it runs the final integrated rehearsal and gives a short evidence walkthrough. Use the other guides when the audience asks to see a boundary in more detail. The Linux x86-64 archive has passed its native WSL2 package acceptance; use the separate [Linux integrated acceptance](../linux-integrated-acceptance.md) to bind that accepted archive to the complete IEMS rehearsal.

The **final verified development package** is:

```text
/absolute/path/to/freshly-extracted/dcg-4.0.0-phase1-phase2-dev.20260919-r2-macos-arm64
```

The Phase 1 and Phase 2 runners now use this same consolidated package after applying the [shared package validation contract](../dcg-package-validation.md). `--dcg-home` overrides `DCG_HOME`; neither runner has a historical package fallback.

## Recommended 10–15 minute sequence

| Time | Show | Evidence-backed claim |
| --- | --- | --- |
| 0–2 min | Baseline IEMS health and Postman/Newman | Four contracts PASS; 55 requests/107 assertions pass without AI. |
| 2–5 min | Compatible and breaking CLI proposals | Optional `sourceSystem` passes; `studentId` integer → string fails. |
| 5–7 min | Startup/Maven blocks and two CLI explanations | Breaking launcher exits 1 with zero Java dispatch; Maven stops at `validate`; two stable failure IDs explain the changes. |
| 7–10 min | Real-model advisory and DCG service/dashboard/webhook | The actual model returns labels/scores; service run ID ties deterministic FAIL to advisory, dashboard and failure webhook. |
| 10–12 min | Unavailable/fault and test-only disagreement evidence | PASS/FAIL do not change when advice is missing or disagrees. |
| 12–15 min | Runtime/migration regressions and final recovery | Publisher handoffs 1/0/0; governed SQLite executor calls 1/0; final IEMS/Postman passes. |

**Limits to say aloud:** AI labels and scores are advisory only and their calibration is unverified. The model does not generate explanations or corrections. The runtime test proves publisher handoff, not Kafka delivery. Webhook retry shown here is manual, not automatic. The migration gate covers its governed SQLite runner, not unrestricted direct SQL. PostgreSQL/MySQL and Linux acceptance are outside this completed local development rehearsal. Never use a normal IEMS database or accepted RC as disposable demo state.

## Guides

- [01 — Quick live demo](01-quick-live-demo.md)
- [02 — Phase 1 deterministic demo](02-phase1-deterministic-demo.md)
- [03 — Phase 2 AI advisory demo](03-phase2-ai-advisory-demo.md)
- [04 — Extended fault scenarios](04-extended-fault-scenarios.md)
- [05 — Start, stop and reset](05-start-stop-reset.md)
- [06 — Troubleshooting](06-troubleshooting.md)

Each guide labels its runnable commands with the expected outcome, AI mode, evidence location, live-demo safety, and stop/recovery action. Integrated runners create new private evidence and stop their owned processes. They refuse reused evidence paths. Existing unrelated processes, source contracts, normal databases, package archives and accepted RC artifacts are outside their reset scope.
