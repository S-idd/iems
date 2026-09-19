# 01 — Quick live demo

Use this page during the normal 10–15 minute talk. The integrated runner actually starts IEMS and DCG in disposable state, executes Postman/Newman, runs real AI, then stops its owned processes. Health values shown afterward are **recorded HTTP responses**, because the runner closes the services safely. For a foreground live health/dashboard screen, use [05](05-start-stop-reset.md).

| Command block | Demonstrates / expected result | AI | Private evidence | Live-safe / recovery |
| --- | --- | --- | --- | --- |
| 1 — setup | Select Java 21 and the checksum-verified consolidated r2 package. | Runner controls both modes. | No new evidence. | Yes; no process starts. |
| 2 — integrated run | Baseline, proposals, blocking, real advisory, faults and recovery; final `PASS`. | Disabled, available, unavailable and labelled test-only modes. | New `0700` directory at `$DEMO_EVIDENCE`. | Yes; runner stops owned children. On interruption run its `--cleanup` command in [05](05-start-stop-reset.md). |
| 3 — evidence walkthrough | Print the nine essential outcomes without credentials. | Values are read from retained evidence. | Read-only. | Yes; no process to stop. |

**1. Set the final package and a new evidence path** (from any terminal):

```bash
cd /absolute/path/to/iems
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
export PATH="$JAVA_HOME/bin:$PATH"
export DCG_HOME="/absolute/path/to/freshly-extracted/dcg-package"
export DEMO_EVIDENCE="$PWD/.dcg/rehearsals/phase2-integrated-$(date +%Y%m%d-%H%M%S)"
```

**2. Run IEMS baseline through final recovery**. The runner uses the existing IEMS JAR and local Newman installation; see [troubleshooting](06-troubleshooting.md) if a prerequisite is absent.

```bash
python3 scripts/dcg/phase2_integrated_demo.py --dcg-home "$DCG_HOME" --evidence "$DEMO_EVIDENCE"
```

**3–9. Show the proof in order**. This reads saved results only; it prints no passwords or raw schemas.

```bash
python3 - <<'PY'
import json, os
from pathlib import Path
e = Path(os.environ['DEMO_EVIDENCE'])
read = lambda name: json.loads((e / name).read_text())
index, baseline, cli, service, recovery = (read(name) for name in
    ('results.json', 'baseline.json', 'real-cli.json', 'service/results.json', 'final-recovery.json'))
print('2 IEMS baseline:', baseline['healthHttp'], baseline['contractRows'])
print('3 Postman/Newman:', baseline['api']['requests'], 'requests,', baseline['api']['assertions'], 'assertions,', baseline['api']['failures'], 'failures')
for label in ('compatible', 'breaking'):
    c = cli[label]['contracts'][0]
    print('4/5 proposal:', label, c['deterministicVerdict'], c['advisory']['advisoryStatus'], [p['label'] for p in c['advisory']['predictions']])
gate = read('ai-startup-gate.json')
print('6/7 deterministic block: launcher exit', gate['exit'], 'IEMS Java dispatches', gate['javaDispatchCount'])
for label in ('real-compatible', 'real-breaking'):
    item = service['runs'][label]
    print('8 real AI service:', label, item['run']['runId'], item['run']['status'], item['advisory']['predictionLabel'], item['advisory']['agreement'])
print('9 final recovery:', recovery['healthHttp'], recovery['api']['requests'], 'requests,', recovery['api']['failures'], 'failures')
print('overall:', index['overall_result'], 'cleanup:', index['cleanup'])
PY
```

Expected: baseline and recovery HTTP **200**, four PASS contracts, Newman **55 requests/107 assertions/0 failures** both times; compatible **PASS**, breaking **FAIL**; launcher exit **1** with **0** IEMS dispatches; real advisory `AVAILABLE` with actual labels/scores and final `PASS`. The model may produce different labels on a future build; never assume a label before reading the evidence. For exact scores, run IDs, model/input hashes, Maven proof and webhook correlation, open the private `$DEMO_EVIDENCE/results.json` and `$DEMO_EVIDENCE/service/results.json`. The presenter should not copy credential-bearing logs into slides.
