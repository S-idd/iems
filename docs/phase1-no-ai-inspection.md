# Phase 1: verified no-AI development package

Result: **COMPLETE** for local macOS ARM64 development packaging and deterministic startup verification, 2026-09-17. This is an unpublished development assembly, not an accepted or published RC. No dashboards, webhooks, Maven gate, runtime validation, database matrix or AI inference work was performed.

## Identity and evidence

- DCG source: `/absolute/path/to/data-contract-governance`; packaging commit `7138c9047db23d118ae32e6815a9c67f97c7b713`, explicitly dirty. Java artifacts remain pinned to `994770c97ed00d00b1a6bf974344a6c68c31d656`.
- IEMS source: `/absolute/path/to/iems`; commit `6e65c66745714b7f84521b50efd31fdbe0d99e98`, explicitly dirty. Existing application changes were preserved.
- Development identity: `4.0.0-phase1-no-ai-dev.20260917`; base runtime version `4.0.0-rc.1`. Assembly timestamp: `2026-09-17T14:55:15Z`; target `aarch64-apple-darwin`.
- Installed package: `$IEMS_ROOT/.dcg/runtime/dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64`.
- Archive: a private local build artifact under `$DCG_SOURCE/target/phase1-development-package/assembly-a/`.
- Archive SHA-256: `03c3269bc597bc515bf694dd975f51fdd3476d81b4e7f6358aa1e01dd5ed6a44`.
- Canonical assembler: `scripts/release/assemble-local.py`. It uses allowlisted inputs, pinned model/contracts/license sources, and the maintained launchers.
- Private evidence directory: `$DCG_SOURCE/target/phase1-development-package`. Source status/inventory snapshots, notices analysis, build log, frozen inputs/provenance, both archives, installation checks, lifecycle proof and test logs are retained there. Runtime credentials and temporary databases are not retained.

`build-info.json` explicitly identifies the development version, source/dirty state, timestamp, launcher changes, input hashes and transformations. Java JAR filenames/embedded versions retain their real base version. The default data directory is isolated by development identity. No global symlink, IEMS installer pin, or default package selection changed.

## Notice mismatch: explained, original installation preserved

Classification: **Line-ending difference** in the original installation. All compared files are valid UTF-8 without BOM.

| Copy | Size | CRLF / lone CR | SHA-256 |
| --- | ---: | --- | --- |
| Original archive / its manifest expectation | 4,921,369 | 1,243 / 20 | `b9cc27b2e5051f893c2d46cfacc388e13c16db9174218d1882ffa91fc5e43976` |
| Installed original RC | 4,920,126 | 0 / 0 | `6fcc4e415f218b74c3f7b8f27e5bf7d7cd47653100f2ec5e4e013b42c669658b` |
| Canonical source, reviewed macOS archive and new development package | 4,911,334 | 1,243 / 0 | `deafccec618c145c42abb3afe5225222d97732ec291af065af8c54e5e4241e0e` |

The exact transformation `original.replace(b'\r\n', b'\n').replace(b'\r', b'\n')` produces the installed bytes and hash. There is no encoding or semantic text difference between those first two copies. The tool/person that normalized the installed file is not established. The canonical assembler uses byte copies; the installer extracts the archive. Neither inspected process intentionally normalizes notices. The original archive's manifest is correct; the installed copy is internally inconsistent with it. Its manifest was not rewritten to hide the mismatch.

The original archive checksum is `48a8331652ed95331bc5d9760fb612daff9165cd662a945470a8abd0cf0cf97d`, matching the IEMS installer pin. The later reviewed archive is `7921446b1efcc229c2fb02218f8a7cce4412d5b300f2215576c1f253df58be0e`. DCG `release-evidence/v0.1.0-rc.1/08-NOTICE-SECURITY-RESULTS.md` records that later reviewed input: removal of accidentally included MySQL class bytes, corrected Jakarta notice extraction and additional source URLs. Thus the reviewed canonical notice is a documented content correction, not merely newline conversion of the older notice. The IEMS installation predates that reviewed archive; do not conflate their acceptance evidence.

Resolution: use the already reviewed canonical notice bytes unchanged as assembly input, validate their hash against reviewed input provenance, then generate a fresh manifest for the uniquely identified development package. New assembler validation rejects tampered notice/SBOM inputs before checksums are generated. A focused test verifies that upstream mixed newline bytes survive packaging unchanged. Legal redistribution/attribution review remains outside this task.

## Executable artifacts and necessary rebuild

| Artifact | Treatment | SHA-256 |
| --- | --- | --- |
| CLI JAR | Reused unchanged; matches installed RC and reviewed inputs | `271c34c32ded6a8c08cdd8b9d4f083c2d37457c47f074f5703618be4ddb2ecb1` |
| Service JAR | Reused unchanged; matches installed RC and reviewed inputs | `5a6bec25ef2d9022176e423ab4643fd88e92199804001ffbda99ca9b389ef712` |
| Original Rust executable | Preserved in RC; not reused in development | `c004f10655f1516ed5d4ac90b9cbd2b4fc6c79f3b809447466f0adebfb0a906c` |
| Development Rust executable | Same pinned source, rebuilt with path remapping | `5932bb21d15fbb6b19e3a534437a3f3f082c23f91dbe7f1422e4c67fff2327f8` |

Inspection proved the original Rust binary embeds this developer's absolute home path. The task prohibits those paths and allows rebuilding when necessary. A clean `git archive` export of Rust commit `32ca579095ed5b91749b8c33999556624e58758f` was compiled offline with pinned Rust/Cargo 1.96.0, unchanged Cargo.lock, and remapped home/temp paths. No Rust source or frozen model changes were made. The actual command and build log hash are recorded; model inference was never started. The rebuilt executable has **not** received AI-enabled acceptance.

The development assembler scans payload bytes and recursively scans compressed JAR members for this host's home and macOS home/temp paths. Upstream dependency URL paths and upstream CI constants are not mistaken for this developer's paths. No developer-machine path remains in the packaged payload/provenance. Absolute local paths in this inspection report and private build evidence are intentional; those documents/logs are not package inputs.

## Reproducibility, installation and preservation

Two clean output directories used identical frozen inputs, source templates and development metadata. Both tar.gz files have SHA-256 `03c3269bc597bc515bf694dd975f51fdd3476d81b4e7f6358aa1e01dd5ed6a44`. File/directory inventories, modes, per-file hashes, manifest and provenance match. Archives normalize gzip/tar timestamps, ownership and ordering.

The installed archive contains exactly 24 regular files; all 23 checksum entries pass. Launchers and the Rust binary are 0755; other files are 0644; archive directories are 0755. No logs, databases, temporary fixtures, credentials, editor files or unrelated source were included.

The original installation remains `$IEMS_ROOT/.dcg/runtime/dcg-4.0.0-rc.1-macos-arm64`. Its full before/after file hash/size/mode inventories are in `original-rc-before.json` and `original-rc-after.json`; they compare equal, including the pre-existing notice mismatch. Both RC inventory files have SHA-256 `076561a7a3a373d73a624de1befbc4d22f051831b462b5664b7dbfbda01c9ebe`. Original archives and reviewed staging inputs are also preserved, verified through the initial working-tree inventory. All approved baseline and candidate files compare equal to `contracts-before.json`. No candidate restoration was necessary: breaking tests only changed isolated temporary copies.

Install/verify commands for the already-created archive (installation refuses an existing destination):

```bash
export DCG_SOURCE=/absolute/path/to/data-contract-governance
export IEMS_ROOT=/absolute/path/to/iems
export DEV_NAME=dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64
export ARCHIVE="$DCG_SOURCE/target/phase1-development-package/assembly-a/$DEV_NAME.tar.gz"
(cd "$(dirname "$ARCHIVE")" && shasum -a 256 -c SHA256SUMS)
test ! -e "$IEMS_ROOT/.dcg/runtime/$DEV_NAME" && tar -xzf "$ARCHIVE" -C "$IEMS_ROOT/.dcg/runtime"
# Already installed here: do not extract over it. Verify and select it instead.
export DCG_HOME="$IEMS_ROOT/.dcg/runtime/$DEV_NAME"
(cd "$DCG_HOME" && shasum -a 256 -c SHA256SUMS)
```

The actual installation used Python tarfile's data filter after checking destination absence, identical archive hashes and inventories; `integrity.json` records the checks. No installer default or shared symlink was changed.

## Verified behavior and boundaries

| Scenario | Actual result | Evidence |
| --- | --- | --- |
| Installed package integrity | PASS, 23/23 checks | `integrity.json`, `installed-checksums.log` |
| Real IEMS contract checks using explicit installed DCG_HOME | Four PASSs, exit 0 | `installed-lifecycle-commands.json`, proof JSON |
| Primary installed DCG no-AI start | Exit 0, HTTP 200 | Java process argument `--shadow.inference.enabled=false` |
| Status without AI flag | Exit 0, Java running, Rust disabled | Saved `run/ai-enabled` is false |
| Stop without AI flag | Exit 0, no PID files, ports free | Installed lifecycle proof |
| Actual IEMS start through primary development package | HTTP 200 after four recorded PASSs | Real IEMS JAR; `installed-iems.log` |
| Compatible isolated IEMS dispatch | Exit 0, dispatch marker present | Focused compatible test |
| Breaking integer→string enrollment candidate | Exit 1, no IEMS dispatch marker | Real CLI, one FAIL/three PASSs, Rust tripwire not invoked |
| Missing Rust/model files | Compatible 0, breaking 1; service and actual IEMS healthy | Controlled copies made from installed package |
| Existing unrelated 8081 listener | No-AI lifecycle succeeds; listener untouched | Focused lifecycle test |
| Invalid mode / live mode change | Rejected, exit 1 | Focused lifecycle test |
| Default AI mode with binary absent | Rejected, exit 1 | Default behavior remains AI-enabled |

The DCG service launcher does not check IEMS candidates. IEMS `run_demo.sh` runs lint and real packaged CLI compatibility checks before its final Java `exec`. These are distinct paths; both were verified. The dispatch probe replaces only the final IEMS Java invocation, never compatibility logic. A separate test launches the actual application. The healthy IEMS JVM was deliberately terminated with SIGTERM, exit **143**; this is successful cleanup, not failed startup. DCG's background launcher itself returned 0.

Rust proof combines explicit disabled Java configuration, absent Rust PID/log files, free inference port, process samples before/during/after the primary run, and an executable tripwire in controlled gate fixtures. Missing-artifact lifecycle tests make launching the model impossible. No model was loaded or queried; AI-enabled behavior is not claimed.

## Exact verification commands and results

Executed from the DCG root unless noted. Full launcher arguments, output and exit codes are retained in `installed-lifecycle-commands.json` and each focused test's `commands.json`.

```bash
# Clean source export and required path-remapped rebuild (exported source already staged).
RUSTFLAGS="--remap-path-prefix=$HOME=/build --remap-path-prefix=/private/var/folders=/build/tmp" \
CARGO_TARGET_DIR="$PWD/target/phase1-development-package/rust-target" \
cargo +1.96.0 build --offline --release --locked --target aarch64-apple-darwin \
  --manifest-path target/phase1-development-package/rust-source/Cargo.toml

# Executed separately for assembly-a and assembly-b, with unchanged frozen metadata.
for output in assembly-a assembly-b; do
  python3 scripts/release/assemble-local.py --platform macos-arm64 --java-repo "$PWD" \
    --rust-repo /absolute/path/to/dcgaimodel \
    --inputs target/phase1-development-package/inputs \
    --development-info target/phase1-development-package/development.json \
    --output "target/phase1-development-package/$output"
done
# These output directories now exist; do not rerun over them.
python3 target/phase1-development-package/verify-installed.py

JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home \
DCG_TEST_PACKAGE="$IEMS_ROOT/.dcg/runtime/dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64" \
IEMS_TEST_ROOT="$IEMS_ROOT" \
DCG_TEST_INSTALLED_LAUNCHERS=true \
DCG_TEST_EVIDENCE="$PWD/target/phase1-development-package/focused" \
python3 -m unittest discover -s scripts/release -p test_no_ai_foundation.py -v

JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home \
DCG_HOME="$IEMS_ROOT/.dcg/runtime/dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64" \
python3 "$IEMS_ROOT/scripts/dcg/test_cli.py"

python3 -m unittest discover -s scripts/release -p test_local_packaging.py -v
python3 -m unittest discover -s scripts/release -p 'test_*.py' -v
python3 target/phase1-development-package/final-audit.py
# Audit runs shasum -a 256 -c SHA256SUMS in the installed package,
# bash -n for all four launchers, and git diff --check in both repositories.
```

| Test group | Count / result | Exit |
| --- | --- | ---: |
| Focused installed-launcher no-AI tests | 5 passed | 0 |
| Existing IEMS binary CLI tests with development DCG_HOME | 6 passed | 0 |
| Focused packaging regressions | 20 passed | 0 |
| Broad release discovery | 29 discovered: 24 passed, 5 opt-in skipped (run separately above) | 0 |
| Primary installed lifecycle/IEMS verification | All assertions passed | 0 |
| Both real archive assemblies | Identical outputs | 0 |
| Installed checksums | 23 passed | 0 |
| Shell syntax and both Git whitespace checks | Passed | 0 |

An initial development path scan rejected an upstream `/home/standards` URL as if it were a local path. The scanner was narrowed to actual host home/macOS path roots, then regression tests and real assembly passed. This initial attempt produced no archive. This is disclosed rather than counted as a successful assembly. Reproducibility covers assembly from frozen binaries; byte-reproducibility of the Rust compilation itself was not tested.

## Demo commands and recovery

```bash
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export DCG_HOME="$IEMS_ROOT/.dcg/runtime/dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64"
export DCG_DATA_DIR="$(mktemp -d /tmp/dcg-phase1-state.XXXXXX)"
export DCG_SQLITE_PATH="$DCG_DATA_DIR/iems-checks.db"
(cd "$DCG_HOME" && shasum -a 256 -c SHA256SUMS)
cd "$IEMS_ROOT"
./scripts/dcg.sh lint
./scripts/dcg.sh check sqlite
DCG_AI_ENABLED=false "$DCG_HOME/bin/start"
"$DCG_HOME/bin/status"
curl --noproxy '*' -fsS http://127.0.0.1:8080/actuator/health
"$DCG_HOME/bin/stop"
```

Expected: checks/start/status/stop exit 0, health 200, Rust disabled. Keep the same DCG_DATA_DIR for status/stop; it holds the saved mode. IEMS itself starts separately with `./scripts/database/run_demo.sh sqlite`, an isolated IEMS_JDBC_URL, IEMS_PORT, and private IEMS_JWT_SECRET/IEMS_DEMO_ADMIN_PASSWORD. Follow the existing database demo credential instructions; never put credentials in evidence. Starting the DCG service is not required for its CLI gate.

If interrupted, use this package's `bin/stop` with the same data directory, inspect logs privately, and confirm owned processes and demo ports are gone before removing that disposable state. Never remove a lock or signal an unrelated process blindly. A failed candidate must be restored from its own recorded backup; never alter v1 to make a check pass. Current tests removed their temporary copies and databases, stopped their processes, and left no stale PID files or occupied test ports. Original IEMS fixtures were untouched and hash-verified.

## Changes in this task and remaining work

Changed during this packaging task:

- DCG `scripts/release/assemble-local.py`: explicit development identity/provenance, isolated state path, notice/SBOM input digest checks, recursive developer-path checks.
- DCG `scripts/release/test_local_packaging.py`: four focused development packaging regressions.
- DCG `scripts/release/test_no_ai_foundation.py`: option to use installed launcher bytes in controlled tests; the five tests predated this task.
- DCG `scripts/release/README.md`: development assembly/test documentation.
- IEMS `docs/phase1-no-ai-inspection.md` and `docs/dcg-full-feature-demo-plan.md`: verified results/runbook/status updates.
- Generated ignored artifacts under DCG `target/phase1-development-package/` and the new IEMS `.dcg/runtime/dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64/` installation.

The pre-existing four maintained launcher edits (`dcg`, `start`, `status`, `stop`) and package README changes were included, not reimplemented. Source working-tree snapshots distinguish those prior changes from this task. Other IEMS source/config/Postman changes, canonical notices and prior release-output files were preserved. Nothing was committed, tagged, pushed, published or deployed.

Limitations: local macOS ARM64 only; Java 21 required; AI-enabled acceptance of the remapped Rust binary and public redistribution review remain undone; the original installation retains its known notice mismatch. No PostgreSQL/MySQL matrix, new API endpoint or service-submitted check/UI/webhook proof is implied.

The packaging task left multiple-contract rejection/reset for separate work. That follow-up is now complete; see the verification below.

## Follow-up: multiple-contract rejection and automatic reset (2026-09-17)

Implemented `scripts/dcg/multiple_contract_demo.py`, two hash-pinned fixtures plus manifest, and four reset/integrity tests. The live rehearsal uses the primary installed development DCG_HOME and temporary IEMS project copies. Enrollment `studentId` integer→string and scholarship `amount` number→string both fail; two other contracts pass. The actual gate exits 1 with zero observed IEMS Java dispatches.

Automatic reset restored exact candidate bytes. Real recovery recorded four PASSs, dispatched IEMS once, and reached HTTP 200. Deliberate SIGTERM returned 143; no forced cleanup was needed and the test port was released. Source contract and installed package inventories remained unchanged; no Rust model ran. Four reset tests and six existing CLI tests passed. No new binary was needed because only IEMS rehearsal tooling changed.

See [the reproducible runbook](multiple-contract-demo.md) and `.dcg/rehearsals/multiple-contracts-20260917-01/results.json`. Next separate task: recorded-run CLI explanation. Other planned integrations remain unchanged.
