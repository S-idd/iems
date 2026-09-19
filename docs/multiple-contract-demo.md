# Multiple-contract rejection and automatic reset

Verified on 2026-09-17 using the installed macOS ARM64 no-AI development package. This rehearsal uses the real DCG Java CLI, real IEMS shell launcher and real IEMS application JAR. It changes only a temporary project copy; approved baselines, current candidates and the installed package remain untouched.

Run from the IEMS repository with Java 21 and the already built application JAR:

```bash
cd /absolute/path/to/iems
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home
export DCG_HOME="$PWD/.dcg/runtime/dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64"
python3 scripts/dcg/multiple_contract_demo.py \
  --evidence "$PWD/.dcg/rehearsals/multiple-contracts-$(date +%Y%m%d-%H%M%S)"
```

The evidence directory must be new. No separate DCG service or Rust inference process is needed. The runner verifies package checksums before use and refuses to run while a Rust model is already running. It chooses an available local IEMS port and creates private disposable SQLite databases and credentials. It stops only its own process group and removes temporary project copies/databases when finished. No shared database or existing IEMS instance is used.

| Step | Expected result |
| --- | --- |
| Baseline | Four contracts PASS |
| Enrollment fixture | `studentId`: integer → string; FAIL |
| Scholarship fixture | `amount`: number → string; FAIL |
| Existing startup gate | Four checks recorded: two FAIL, two PASS; exit 1 |
| Dispatch observation | Zero IEMS Java dispatches while broken |
| Automatic reset | Both candidate files restored to their exact previous bytes |
| Recovery | Four PASSs; one real IEMS Java dispatch; health HTTP 200 |
| Cleanup | Intentional SIGTERM shutdown; test port released; source/package hashes unchanged |

The wrapper checks each contract separately; this is not an atomic multi-contract database transaction. Its nonzero result prevents the final IEMS `exec`. A small Java wrapper records attempts to launch the IEMS JAR, then delegates to the real Java executable. It never replaces compatibility decisions or fakes application startup. Thus zero blocked dispatches proves enforcement more directly than an absent health response.

The overall rehearsal exits **0** only when expected rejection, reset, recovery and cleanup all pass. The actual breaking launcher command exits **1**, retained in evidence. IEMS exits **143** after the runner deliberately sends SIGTERM; this is not a startup failure. Unexpected errors or an interruption return nonzero.

Fixtures live in `scripts/dcg/fixtures/multiple-breaking/`. The manifest pins each baseline and fixture SHA-256. Every fixture is verified before any candidate mutation. If a baseline or fixture changes, the runner stops for review; it does not update the expected hash automatically. Reset runs in `finally`, including on exceptions and handled SIGINT/SIGTERM. SIGKILL or power loss cannot execute cleanup handlers, but the real project candidates are still safe because only disposable copies are edited. Do not manually restore real candidates from v1: the starting candidates may contain intentional compatible edits.

Evidence contains `results.json`, baseline lint/check logs, the two-failure log and recovery log. It records verdict rows, dispatch counts, candidate hashes, package preservation, health and shutdown results. Random credentials stay in process environment and disposable runtime state; do not capture the environment for sharing. Evidence is private by default (directory mode 0700).

## Verification performed

Successful live evidence: `.dcg/rehearsals/multiple-contracts-20260917-01/results.json`.

- Baseline: four PASS rows.
- Rejection: enrollment FAIL, scholarship FAIL, accessibility PASS, notification PASS; exit 1 and zero Java dispatches.
- Reset: exact hash match for all temporary contract files.
- Recovery: four PASS rows, one real dispatch and HTTP 200.
- Cleanup: exit 143 after deliberate SIGTERM, no forced shutdown, recovery port released, no Rust model process.
- Real source contracts and installed development package unchanged.

Regression commands:

```bash
python3 scripts/dcg/test_multiple_contract_demo.py -v
JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home \
DCG_HOME="$PWD/.dcg/runtime/dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64" \
python3 scripts/dcg/test_cli.py
git diff --check
```

Four reset/integrity tests and six existing binary CLI tests passed. Reset coverage includes normal exit, runtime error, KeyboardInterrupt and handled termination exception, plus preflight rejection of stale baselines and tampered fixture bytes. The live rehearsal separately verifies actual engine decisions and real application recovery. These results do not claim API collection, database matrix, webhook, dashboard, Maven gate or AI acceptance.

Optional retained-history mode is now verified: add `--retain-history` to keep only the breaking-check database and produce real CLI explanations for both stable failure IDs. See [CLI explanation runbook](cli-explain-demo.md) for private retention, exact replay commands and the packaged exit-1 convention. Without the flag, all history databases remain disposable as before.

Next separate Phase 1 implementation: Maven build gate.
