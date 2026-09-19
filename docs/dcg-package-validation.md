# DCG development-package validation contract

The IEMS rehearsal runners accept a caller-selected, extracted DCG development package. They do not contain a historical package fallback. Select the package with `--dcg-home`; if that option is absent, the runners use `DCG_HOME`. When both are set, the command-line value wins and the evidence records that precedence without recording the other environment value. If neither is set, validation fails before any service starts or disposable fixture is changed.

`scripts/dcg/dcg_package.py` canonicalizes the selected directory and rejects a missing directory, the DCG source checkout, the normal IEMS `.dcg/data` tree, package symlinks, unsafe manifest paths, incomplete file inventories and non-executable launchers. It validates every `SHA256SUMS` entry, requires an exact manifest inventory, and cross-checks build provenance, Java artifacts, the Rust artifact, the configuration, notices and CycloneDX SBOM.

The local rehearsal accepts a native macOS ARM64 package on a macOS ARM64 host or a native Linux x86_64 package on a Linux x86_64 host. The validator matches the package target to the current host and reads the Rust executable header. It requires a thin Mach-O ARM64 binary on macOS or an ELF64 x86-64 binary on Linux; a platform name in a directory or version string is insufficient. Other host/architecture pairs fail before a service starts.

The validated result records the canonical path, package version, target, DCG and Java source commits and dirty state, CLI/service/Rust hashes, Rust source commit, frozen model hashes, feature-schema version, manifest result, SBOM and notice hashes, JAR inspection evidence and verified capabilities. A caller can additionally require an exact DCG source commit and archive SHA-256. Each primary runner writes this object into its `results.json` (`validated_package` in the service runner, `development_package` in integrated runners).

Capability checks inspect launchers and packaged JAR contents rather than version-name substrings:

- Phase 1 requires the CLI, deterministic no-AI behavior, Maven-gate inputs and the service/dashboard.
- The Phase 2 service runner requires service/dashboard, advisory persistence and V13 migrations, advisory REST classes, Rust/model support, best-effort and fault-safe advisory behavior, and a test-only adapter that defaults to disabled.
- Phase 2 integrated requires both sets.

The validator does not mutate the selected package. Runners pass its canonical path explicitly to child demonstrations and keep all generated state under a new private rehearsal directory.

Recommended invocation:

```sh
python3 scripts/dcg/phase2_integrated_demo.py \
  --dcg-home "/absolute/path/to/extracted/dcg-package" \
  --evidence "$PWD/.dcg/rehearsals/phase2-integrated-$(date +%Y%m%d-%H%M%S)"
```

Environment fallback:

```sh
export DCG_HOME="/absolute/path/to/extracted/dcg-package"
python3 scripts/dcg/phase2_integrated_demo.py \
  --evidence "$PWD/.dcg/rehearsals/phase2-integrated-$(date +%Y%m%d-%H%M%S)"
```
