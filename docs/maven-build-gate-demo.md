# Phase 1 Maven build gate — verified local demo

Result: **COMPLETE for the opt-in official plugin gate** on 2026-09-18, macOS ARM64. IEMS is a single-module JAR/Spring Boot project. Its root `pom.xml` controls final packaging. The added `dcg-demo` profile has no activation rule, so normal Maven builds remain unchanged. It uses the genuine Java DCG engine through the official plugin; no CLI shell replacement, service or model process is involved.

## Configuration and lifecycle

Profile: `dcg-demo`. Plugin: `com.ideas.contracts:contract-maven-plugin:4.0.0-rc.1`, goal `check-compat`, explicitly bound to **validate**. Existing compilation, tests and Spring Boot repackage remain in their normal phases. The four executions check `iems.accessibility`, `iems.enrollment`, `iems.notification` and `iems.scholarship` against their `v1.json`/`candidate.json` files in that order, with BACKWARD mode. `remoteReportingMode=DISABLED` prevents service calls. Paths are configurable through `-Ddcg.contracts.dir`, `-Ddcg.reports.dir`, and `-Ddcg.plugin.repository.url` or their profile defaults. Nothing is tied to a developer home directory in the POM.

The official plugin writes a separate **JSON evidence report per executed check**, not SQLite check history. The user explicitly selected this supported format for the Maven gate. It fails at the first incompatible execution. Thus the multiple-breaking build shows accessibility PASS and enrollment FAIL, then stops; notification and scholarship are *not evaluated by that Maven invocation*. The earlier CLI rehearsal remains the proof of both simultaneous contract failures. Do not present the Maven log as reporting both.

## Verified plugin binaries and provisioning

The installed DCG development distribution contains only CLI/service JARs. The official RC Maven plugin and its core/build-support dependencies were found in the verified earlier Java build workspace. All 69 inspected source/POM files match pinned commit `994770c97ed00d00b1a6bf974344a6c68c31d656`; its build log matches development-package provenance. All 32 core engine class files match the installed CLI. Plugin JAR SHA-256: `5ec8707e821f90fd373b1c86fcf2265ef39200a38e0d305721191fa58694c625`.

`maven-plugin-artifacts.json` pins seven POM/JAR inputs. `provision_maven_plugin.py` checks each hash, then stages only those artifacts and Maven checksum sidecars in private `.dcg/maven-repository/`. It refuses an existing destination. This is a local file repository for the demo, not a public release or a rebuild. No existing DCG installation was modified.

For a fresh IEMS checkout with the verified source build available, run once:

```bash
cd /absolute/path/to/iems
python3 scripts/dcg/provision_maven_plugin.py \
  --build-root /absolute/path/to/reviewed/dcg-java-build
```

The directory is already provisioned in this workspace; the command intentionally refuses to replace it. The default plugin repository URL is local to the IEMS checkout. Maven still resolves ordinary third-party dependencies from its configured repositories/cache. The plugin's JSON evidence is offline with respect to any DCG service.

## Presenter commands

Select Java 21. `DCG_HOME` and `DCG_AI_ENABLED` make the demonstration context explicit; the official Maven plugin itself does not require DCG_HOME, Rust or model artifacts.

```bash
cd /absolute/path/to/iems
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home
export DCG_HOME="$PWD/.dcg/runtime/dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64"
export DCG_AI_ENABLED=false
mvn -B -ntp verify -Pdcg-demo
```

Compatible candidates: four plugin PASS reports, application tests, JAR and `BUILD SUCCESS`, Maven exit 0. Separate disposable tests confirmed both the exact `mvn -B -ntp verify -Pdcg-demo` command and `mvn -B -ntp validate -Pdcg-demo` with no extra `-D` arguments. The exact verify command exited 0, wrote four PASS reports, ran the application tests and produced a JAR with SHA-256 `35cac8e38176bc6681240bac1a9a233c633ee079d3ab792d669181fdb58c4c47`. The validate command wrote four reports under `target/dcg/`.

For breaking fixtures and automatic reset, **use the disposable runner**, not the real project candidates:

```bash
python3 scripts/dcg/maven_gate_demo.py \
  --evidence "$PWD/.dcg/rehearsals/maven-gate-$(date +%Y%m%d-%H%M%S)"
```

It refuses an existing evidence directory, copies only the POM/source/contracts into disposable projects, pins fixture hashes, and restores exact candidate bytes in `finally`. It creates a clean target for each first build. It runs compatible, profile-off, enrollment-breaking, recovery, two-fixture-breaking, recovery, and missing-AI compatible/breaking scenarios. It captures full Maven logs and JSON reports, plugin verdicts, JUnit totals and artifact hashes. Private evidence directories are mode 0700; files are 0600. It does not capture full environments or credentials. It removes temporary builds after testing; it does not delete or replace existing user artifacts.

## Actual results

Private evidence: `.dcg/rehearsals/maven-gate-20260918-01/results.json` and per-scenario logs/reports.

| Scenario | Maven exit/result | Official DCG reports | Final JAR |
| --- | --- | --- | --- |
| Compatible `verify -Pdcg-demo` | 0, BUILD SUCCESS; 10 tests passed | Four PASS | Created, SHA-256 `5bc94852388729644a8bcacb4664de65063ae1fef410de0e3e4deeb9ca5fd690` |
| Normal `verify` (profile off) | 0, BUILD SUCCESS; 10 tests passed | No gate | Created |
| Enrollment breaking | 1, BUILD FAILURE at validate | Accessibility PASS, enrollment FAIL | **Not created** |
| Enrollment reset/recovery | 0, BUILD SUCCESS; 10 tests passed | Four PASS | Created |
| Two fixtures breaking | 1, BUILD FAILURE at validate | Accessibility PASS, enrollment FAIL; later two not evaluated | **Not created** |
| Two-fixture reset/recovery | 0, BUILD SUCCESS; 10 tests passed | Four PASS | Created |
| Missing AI compatible, validate | 0, BUILD SUCCESS | Four PASS | Not requested at validate |
| Missing AI breaking, validate | 1, BUILD FAILURE | Accessibility PASS, enrollment FAIL | Not created |

Both failing builds started with **zero** JARs in clean disposable targets and ended with zero; their logs contain the official failing `check-compat` goal and no JAR/Boot packaging goal. No stale artifact can be mistaken for a new incompatible package. The two breaking fixture sets were restored byte-for-byte. Recovery passed all four checks and packaged successfully. The normal profile-off build demonstrates opt-in behavior. The missing-AI scenarios deliberately pointed `DCG_HOME` to an absent directory; the plugin still enforced PASS and FAIL. The process monitor saw no Rust inference or IEMS application JAR startup. The accepted RC, development package and real source contract inventories remained byte-identical before and after.

Maven 3.9.12 ran on Java 21.0.10. The four successful `verify` builds each ran **10 application tests, zero failures/errors/skips**. Gate failures stopped at validate before application tests, which is distinct from a test skip. The plugin's own focused DCG test group ran **2 tests, zero failures/errors/skips**. An initial rehearsal falsely marked a successful compatible build incomplete because its log parser expected a fully qualified packaging label; actual Maven output uses `jar:3.3.0:jar`. The parser was corrected and the complete scenario set rerun in a fresh directory. The initial real Maven build succeeded; only the rehearsal's assertion was wrong.

## Verification commands

```bash
# IEMS root, with JAVA_HOME/DCG_HOME exported as above:
IEMS_MAVEN_GATE_EVIDENCE="$PWD/.dcg/rehearsals/maven-gate-20260918-01" \
  python3 scripts/dcg/test_maven_gate_demo.py -v
python3 scripts/dcg/test_cli.py
python3 scripts/dcg/test_cli_explain.py -v
python3 scripts/dcg/test_multiple_contract_demo.py -v
git diff --check

# DCG root:
JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home \
  mvn -B -ntp -pl contract-maven-plugin -am \
  -Dtest=CheckCompatibilityMojoTest -Dsurefire.failIfNoSpecifiedTests=false test
git diff --check
```

Results: 8 Maven gate tests, 6 CLI tests, 6 explain/history tests, 4 reset tests, and 2 DCG plugin tests passed; each command exited 0. The 8 Maven gate tests cover opt-in profile, official bindings, real build evidence, packaging prevention, byte-exact reset, absent AI, process observations and evidence refusal. The exact presenter command was also run successfully in a separate disposable copy (exit 0; four PASS reports). No DCG package contents changed, so release packaging tests were not repeated. Both Git whitespace checks pass.

If interrupted, inspect the new evidence directory and let the runner's `finally` restore its disposable candidates. It stops only its own child process groups. Real IEMS candidates were never edited. No Rust process or IEMS app process remains. The preliminary inspection report is retained at `.dcg/rehearsals/maven-gate-inspection-20260917-01/`; its earlier BLOCKED status records the now-resolved JSON-vs-SQLite decision and is historical, not the current readiness result.

Presenter wording: “This opt-in Maven profile runs the official deterministic DCG engine at validate. A compatible build passes all four contracts and packages IEMS. A breaking enrollment contract fails Maven before packaging. Maven stops on its first failure; the separate CLI rehearsal shows both enrollment and scholarship failures together.”

Remaining limits: local macOS ARM64 rehearsal only; plugin JSON evidence is separate from CLI SQLite history; Maven fail-fast means it does not aggregate later failures. No service, registry, dashboard, webhook, runtime validation, database migration gate or AI feature was added. Nothing was committed, tagged, pushed, published or deployed.

Next separate Phase 1 task: DCG service, registry and dashboard integration.
