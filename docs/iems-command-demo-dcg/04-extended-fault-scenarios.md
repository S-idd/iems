# 04 — Extended controlled fault scenarios

**Not part of the default live sequence.** These are controlled local tests, not real-model predictions or production failure injection. The service runner uses isolated SQLite, dynamic loopback ports and its `phase2-rehearsal` profile for synthetic timeout, invalid-output and disagreement cases. It also checks that the normal `local-demo` profile rejects the test-only adapter. No source contract or normal IEMS database is changed.

| Scenario | Command/evidence | Expected deterministic result | Expected advisory result | AI / safety / recovery |
| --- | --- | --- | --- | --- |
| Model unavailable | Shared runner; `unavailable-compatible.json`, `unavailable-breaking.json` | Compatible PASS; breaking FAIL | `UNAVAILABLE`, no label or scores | AI requested, absent endpoint; controlled and live-safe only as an extended test; runner stops Java/receiver. |
| Model timeout | `timeout-compatible.json`, `timeout.json` | PASS / FAIL unchanged | `TIMEOUT`, no label or scores; bounded call | Test-only adapter; never claim real model timed out. |
| Invalid model output | `invalid-output-compatible.json`, `invalid-output.json` | PASS / FAIL unchanged | `INVALID_OUTPUT`, no label or scores | Test-only malformed response; no production adapter. |
| Test-only disagreement | `test-only-disagreement.json` | Breaking proposal still FAIL | Synthetic SAFE, `DISAGREES` | Explicitly test-only; not a real model prediction. |

Set the final package and run all four controlled scenarios in **one fresh private rehearsal**:

```bash
cd /absolute/path/to/iems
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
export PATH="$JAVA_HOME/bin:$PATH"
export DCG_HOME="/absolute/path/to/freshly-extracted/dcg-package"
export FAULT_EVIDENCE="$PWD/.dcg/rehearsals/phase2-service-faults-$(date +%Y%m%d-%H%M%S)"
DCG_AI_ENABLED=true python3 scripts/dcg/phase2_service_demo.py --dcg-home "$DCG_HOME" --evidence "$FAULT_EVIDENCE"
```

Expected overall `PASS`. The same run also records two **real** model cases; keep those separate from these synthetic cases when presenting. The runner refuses an existing directory, shuts down its owned Java/Rust/HTTP receivers and records released ports. On interruption:

```bash
python3 scripts/dcg/phase2_service_demo.py --evidence "$FAULT_EVIDENCE" --cleanup
```

Read only the four controlled outcomes; this command prints no credentials:

```bash
python3 - <<'PY'
import json, os
from pathlib import Path
e = Path(os.environ['FAULT_EVIDENCE'])
for name in ('unavailable-compatible', 'unavailable-breaking',
             'timeout-compatible', 'timeout',
             'invalid-output-compatible', 'invalid-output',
             'test-only-disagreement'):
    item = json.loads((e / (name + '.json')).read_text())
    run, advice = item['run'], item['advisory']
    print(name, run['runId'], run['status'], advice['status'],
          advice['predictionLabel'], advice['agreement'],
          'testOnly=', advice['testOnlyAdapter'])
PY
```

The result should show `None` for unavailable, timeout and invalid-output labels; their probabilities are also null in each private JSON file. The disagreement row must show deterministic `FAIL`, synthetic `SAFE`, `DISAGREES`, and `testOnly=True`. `results.json` records the normal-profile rejection (`normalRuntimeAdapterRejected.exit=1`). Failure webhooks still follow deterministic FAILs, not model output. These commands read evidence after all services stop, so no manual port reset is needed. For the full final sequence including IEMS recovery, use [03](03-phase2-ai-advisory-demo.md).
