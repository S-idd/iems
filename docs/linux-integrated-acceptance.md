# Linux IEMS–DCG integrated acceptance

This runner binds the already accepted Linux DCG archive to the complete IEMS Phase 2 rehearsal. It refuses a different archive name, archive hash, DCG commit, Rust commit, status protocol, host type, or incomplete archive-acceptance report before it starts IEMS.

The pinned inputs are:

| Input | Accepted value |
| --- | --- |
| Archive | `dcg-4.0.0-phase1-phase2-dev.20260920-linux-x64.tar.gz` |
| Archive SHA-256 | `5ec42c1c412b1ccf4fb650991ffae81804d80c08c3e77388002167cbcc8349bc` |
| Acceptance report SHA-256 | `c18742f6d458ee1e3e039a632d4978fcd717b1f41757b0d1cae0d3afc12e133f` |
| DCG commit | `18eda6434049bbebb82c9b3f339fa20521d5081a` |
| Rust commit | `32ca579095ed5b91749b8c33999556624e58758f` |
| Native target | `x86_64-unknown-linux-gnu` |
| Status protocol | `advisory-v2` |
| Accepted host class | Linux x86-64 under WSL2 |

## Prepare the current IEMS checkout

Run on the same AlmaLinux WSL2 machine used for archive acceptance. Java 21, Maven, Node.js, npm and Python 3 must be available. Install the current clean DCG validation starter and Maven plugin into the local Maven repository before building IEMS. These commands create only ignored Maven output, local Maven artifacts and a private Newman installation; they do not change the accepted binary archive.

```bash
JAVA_BIN="$(find "$HOME/jdk21" -type f -path '*/bin/java' -perm -u+x -print -quit)"
test -n "$JAVA_BIN"
export JAVA_HOME="${JAVA_BIN%/bin/java}"
export PATH="$JAVA_HOME/bin:$PATH"

java -version

cd "$HOME/projects/dcg-current-linux/data-contract-governance"
test "$(git rev-parse HEAD)" = "18eda6434049bbebb82c9b3f339fa20521d5081a"
./mvnw -B -ntp \
  -pl contract-validation-spring-boot-starter,contract-maven-plugin \
  -am -DskipTests install

test -f "$HOME/.m2/repository/com/ideas/contracts/contract-validation-spring-boot-starter/4.0.0-rc.1/contract-validation-spring-boot-starter-4.0.0-rc.1.jar"
test -f "$HOME/.m2/repository/com/ideas/contracts/contract-maven-plugin/4.0.0-rc.1/contract-maven-plugin-4.0.0-rc.1.jar"

cd "$HOME/projects/dcg-current-linux/iems"
mvn -B -ntp -DskipTests package
npm install --prefix .dcg/tools --save-exact newman@6.2.2
```

Expected: Java reports Temurin 21; the DCG reactor ends with `BUILD SUCCESS`; both local artifact checks pass; IEMS Maven creates `target/inclusive-education-management-system-1.0.0-SNAPSHOT.jar`; and Newman is present at `.dcg/tools/node_modules/newman`. AI is not started by these preparation commands. Maven may retry a temporary repository connection. The existing duplicate `org.apache.flink:flink-json` declaration is a model warning and does not cause this preparation failure; a missing `com.ideas.contracts` artifact means the DCG install step did not complete successfully.

## Run the bound Linux integration

The following paths match the accepted build and report shown by the WSL2 development workflow. If the accepted run was intentionally retained under another new work directory, change only `LINUX_BUILD`; keep the pinned filenames.

```bash
cd "$HOME/projects/dcg-current-linux/iems"

export LINUX_BUILD="$HOME/projects/dcg-development-linux-20260920T111703Z"
export DCG_ARCHIVE="$LINUX_BUILD/acceptance-handoff/dcg-4.0.0-phase1-phase2-dev.20260920-linux-x64.tar.gz"
export DCG_ACCEPTANCE_REPORT="$LINUX_BUILD/acceptance/acceptance-report.json"

test -f "$DCG_ARCHIVE"
test -f "$DCG_ACCEPTANCE_REPORT"
printf '%s  %s\n' \
  '5ec42c1c412b1ccf4fb650991ffae81804d80c08c3e77388002167cbcc8349bc' \
  "$DCG_ARCHIVE" | sha256sum --check
printf '%s  %s\n' \
  'c18742f6d458ee1e3e039a632d4978fcd717b1f41757b0d1cae0d3afc12e133f' \
  "$DCG_ACCEPTANCE_REPORT" | sha256sum --check
jq -e '.status == "PASS" and ([.checks[].status] | all(. == "PASS"))' "$DCG_ACCEPTANCE_REPORT"

export EVIDENCE="$PWD/.dcg/rehearsals/phase2-integrated-linux-$(date -u +%Y%m%dT%H%M%SZ)"
python3 scripts/dcg/linux_integrated_acceptance.py \
  --archive "$DCG_ARCHIVE" \
  --acceptance-report "$DCG_ACCEPTANCE_REPORT" \
  --evidence "$EVIDENCE"
```

Expected: the runner first verifies the WSL2 host and all 13 archive-acceptance checks, safely extracts the exact archive into the new private evidence directory, validates package provenance and capabilities, and runs all 13 IEMS Phase 2 scenarios. The final line is `PASS: .../results.json`.

The rehearsal controls both AI-disabled and AI-enabled stages. AI labels and scores are advisory only. Deterministic DCG makes every final PASS/FAIL decision. All application databases, DCG history, logs and the extracted package stay under the new private evidence directory. The normal IEMS database, approved contracts, accepted archive and acceptance report are read-only inputs.

## Inspect the result

```bash
jq '{
  overall_result,
  linux_archive_acceptance,
  scenarios: (.scenarios | with_entries(.value |= {
    result, deterministic_result, advisory_status
  })),
  preservation,
  cleanup
}' "$EVIDENCE/results.json"
```

Expected: `overall_result` and `linux_archive_acceptance.result` are `PASS`; all 13 scenario results are `PASS`; every preservation flag is `true`; ports and owned processes are released. This command is read-only.

## Recover after an interruption

```bash
python3 scripts/dcg/linux_integrated_acceptance.py \
  --evidence "$EVIDENCE" \
  --cleanup
```

Expected: only PIDs recorded by this rehearsal are considered for shutdown, recorded ports are free, and `manual-cleanup.json` reports `PASS`. The command retains evidence and does not delete the accepted archive, normal IEMS data, or unrelated processes.

## Native verification boundary

The archive itself has passed its Linux x86-64 WSL2 acceptance. This integrated runner and its trust-boundary tests pass on macOS, but the complete command above must finish on WSL2 before claiming Linux IEMS–DCG integration acceptance. A bare-metal Linux host or a different Linux architecture requires a separate acceptance report and reviewed pin update.
