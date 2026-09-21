#!/usr/bin/env python3
"""Select and verify an immutable DCG development package for IEMS rehearsals."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import stat
import zipfile


IEMS_ROOT = Path(__file__).resolve().parents[2]
NORMAL_DATA = IEMS_ROOT / ".dcg" / "data"
HEX_256 = re.compile(r"[0-9a-f]{64}")
HEX_160 = re.compile(r"[0-9a-f]{40}")

PHASE1_CAPABILITIES = frozenset({
    "cli", "deterministic-no-ai", "maven-gate-inputs", "service-dashboard",
})
PHASE2_SERVICE_CAPABILITIES = frozenset({
    "service-dashboard", "advisory-persistence", "advisory-rest", "rust-model-advisory",
    "best-effort-ai", "fault-safe-advisory", "test-only-adapter-guard",
})
PHASE2_CAPABILITIES = PHASE1_CAPABILITIES | PHASE2_SERVICE_CAPABILITIES

NATIVE_TARGETS = {
    ("Darwin", "arm64"): ("macos-arm64", "aarch64-apple-darwin"),
    ("Linux", "x86_64"): ("linux-x64", "x86_64-unknown-linux-gnu"),
}


class PackageValidationError(ValueError):
    """The selected package is missing, unsafe, incompatible, or unverifiable."""


def _require(condition: object, message: str) -> None:
    if not condition:
        raise PackageValidationError(message)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_relative(name: str) -> Path:
    path = Path(name)
    _require(name and not path.is_absolute() and ".." not in path.parts and path.as_posix() == name,
             f"Unsafe package manifest path: {name!r}")
    return path


def select_path(cli_value: str | Path | None, environment: dict[str, str] | None = None) -> tuple[Path, dict]:
    """Select CLI before environment and disclose only the selection decision."""
    env = os.environ if environment is None else environment
    env_value = env.get("DCG_HOME")
    if cli_value:
        selected = Path(cli_value)
        source = "cli"
    elif env_value:
        selected = Path(env_value)
        source = "environment"
    else:
        raise PackageValidationError("Select a DCG package with --dcg-home or DCG_HOME; no fallback is used")
    return selected, {"source": source, "cliPrecedenceApplied": bool(cli_value and env_value),
                      "environmentWasSet": bool(env_value)}


def _manifest(package: Path) -> tuple[dict[str, str], str]:
    manifest = package / "SHA256SUMS"
    _require(manifest.is_file() and not manifest.is_symlink(), "DCG package is missing SHA256SUMS")
    entries: dict[str, str] = {}
    for line in manifest.read_text(encoding="ascii").splitlines():
        parts = line.split("  ", 1)
        _require(len(parts) == 2 and HEX_256.fullmatch(parts[0]), "Malformed SHA256SUMS entry")
        relative = _safe_relative(parts[1]).as_posix()
        _require(relative not in entries and relative != "SHA256SUMS", "Duplicate or recursive manifest entry")
        entries[relative] = parts[0]
    _require(entries, "SHA256SUMS is empty")
    actual_files: set[str] = set()
    for path in package.rglob("*"):
        _require(not path.is_symlink(), f"Package symlink is not allowed: {path.relative_to(package)}")
        if path.is_file():
            actual_files.add(path.relative_to(package).as_posix())
    _require(actual_files == set(entries) | {"SHA256SUMS"},
             "Package file inventory does not exactly match SHA256SUMS")
    for name, expected in entries.items():
        path = package / name
        _require(path.is_file() and _sha(path) == expected, f"Package checksum mismatch: {name}")
    return entries, _sha(manifest)


def _single_artifact(artifacts: dict[str, str], pattern: str, label: str) -> str:
    matches = [name for name in artifacts if re.fullmatch(pattern, name)]
    _require(len(matches) == 1, f"Expected exactly one {label} artifact in provenance")
    return matches[0]


def _native_target() -> tuple[str, str]:
    host = (platform.system(), platform.machine().lower())
    selected = NATIVE_TARGETS.get(host)
    _require(selected is not None,
             f"Unsupported native host for DCG rehearsal: {host[0]} {host[1]}; "
             "expected macOS arm64 or Linux x86_64")
    return selected


def _validate_rust_binary(path: Path, platform_label: str) -> None:
    header = path.read_bytes()[:20]
    if platform_label == "macos-arm64":
        _require(len(header) >= 8 and header[:4] == b"\xcf\xfa\xed\xfe" and
                 int.from_bytes(header[4:8], "little") == 0x0100000C,
                 "Rust binary is not a thin macOS ARM64 Mach-O executable")
        return
    _require(len(header) >= 20 and header[:4] == b"\x7fELF" and header[4] == 2 and
             header[5] == 1 and int.from_bytes(header[18:20], "little") == 62,
             "Rust binary is not a Linux ELF64 x86-64 executable")


def _rust_provenance_mode(build: dict, development: dict, rust_commit: str,
                          java_commit: str, source_commit: str, source_dirty: bool,
                          target: str, artifact_sha256: str) -> str:
    """Validate each supported development-build provenance shape without weakening old packages."""
    rust_reuse = development.get("rust_reuse", {})
    if rust_reuse:
        _require(rust_reuse.get("source_commit") == rust_commit, "Rust source provenance disagrees")
        _require(rust_reuse.get("artifact_sha256") == artifact_sha256
                 and rust_reuse.get("target") == target, "Rust artifact provenance disagrees")
        return "reviewed-artifact-reuse"

    development_source = build.get("development_source", {})
    if development_source:
        _require(development_source == {
            "java_build_commit": java_commit,
            "rust_commit": rust_commit,
            "packaging_commit": source_commit,
            "clean": True,
        }, "Current-source development provenance disagrees")
        _require(source_dirty is False and development.get("java_build_commit") == java_commit
                 and development.get("rust_commit") == rust_commit,
                 "Current-source development identity disagrees")
        if target == "x86_64-unknown-linux-gnu":
            expected_remapping = {
                "schema_version": 1,
                "applied": True,
                "source_prefix": "<builder-home>",
                "destination_prefix": "/dcg-build-home",
                "reason": "Prevent developer-specific absolute source paths in the packaged Rust executable",
                "rustflags": "--remap-path-prefix=<builder-home>=/dcg-build-home",
            }
            _require(build.get("rust_path_remapping") == expected_remapping,
                     "Linux Rust path-remapping provenance disagrees")
        return "clean-current-source-build"

    rust_rebuild = build.get("rust_rebuild", {})
    _require(rust_rebuild.get("source_dirty") is False
             and rust_commit in rust_rebuild.get("source_export", ""),
             "Rust artifact build provenance disagrees")
    return "reviewed-source-rebuild"


def _jar_capabilities(package: Path, cli_name: str, service_name: str) -> tuple[set[str], dict]:
    capabilities: set[str] = set()
    with zipfile.ZipFile(package / cli_name) as cli:
        cli_entries = set(cli.namelist())
    if {"com/ideas/contracts/cli/ContractCliApplication.class",
        "com/ideas/contracts/cli/CheckCompatCommand.class"} <= cli_entries:
        capabilities.update(("cli", "maven-gate-inputs"))

    with zipfile.ZipFile(package / service_name) as service:
        service_entries = set(service.namelist())
        core_names = [name for name in service_entries if re.fullmatch(
            r"BOOT-INF/lib/contract-core-[^/]+\.jar", name)]
        _require(len(core_names) == 1, "Service JAR must contain exactly one contract-core JAR")
        core_bytes = service.read(core_names[0])
        properties = service.read("BOOT-INF/classes/application.properties").decode("utf-8")
    with zipfile.ZipFile(io.BytesIO(core_bytes)) as core:
        core_entries = set(core.namelist())

    dashboard = {"BOOT-INF/classes/templates/ui/dashboard.html",
                 "BOOT-INF/classes/templates/ui/check-detail.html",
                 "BOOT-INF/classes/static/ui-checks.js"}
    if dashboard <= service_entries and "BOOT-INF/classes/com/ideas/contracts/service/UiController.class" in service_entries:
        capabilities.add("service-dashboard")
    migrations = {"db/migration/V13__create_check_run_advisories.sql",
                  "db/migration-mysql/V13__create_check_run_advisories.sql"}
    if migrations <= core_entries and "BOOT-INF/classes/com/ideas/contracts/service/CheckRunStore.class" in service_entries:
        capabilities.add("advisory-persistence")
    if {"BOOT-INF/classes/com/ideas/contracts/service/CheckController.class",
        "BOOT-INF/classes/com/ideas/contracts/service/model/CheckRunAdvisoryResponse.class"} <= service_entries:
        capabilities.add("advisory-rest")
    if {"BOOT-INF/classes/com/ideas/contracts/service/ShadowInferenceObserver.class",
        "BOOT-INF/classes/com/ideas/contracts/service/HttpShadowInferenceGateway.class"} <= service_entries:
        capabilities.add("fault-safe-advisory")
    adapter_default = "shadow.inference.test-only-adapter=${SHADOW_INFERENCE_TEST_ONLY_ADAPTER:false}" in properties
    if adapter_default and "BOOT-INF/classes/com/ideas/contracts/service/ShadowInferenceProperties.class" in service_entries:
        capabilities.add("test-only-adapter-guard")
    return capabilities, {"nestedCore": core_names[0], "testOnlyAdapterDisabledByDefault": adapter_default,
                          "v13Migrations": sorted(migrations & core_entries),
                          "dashboardAssets": sorted(dashboard & service_entries)}


def validate_package(package_value: str | Path, *, required_capabilities: set[str] | frozenset[str] = frozenset(),
                     expected_source_commit: str | None = None, archive_path: str | Path | None = None,
                     expected_archive_sha256: str | None = None) -> dict:
    raw = Path(package_value).expanduser().absolute()
    _require(raw.exists(), f"Selected DCG package does not exist: {raw}")
    _require(raw.is_dir() and not raw.is_symlink(), f"Selected DCG package is not a regular directory: {raw}")
    package = raw.resolve(strict=True)
    _require(not ((package / ".git").exists() and (package / "pom.xml").is_file()
                  and (package / "contract-service").is_dir()), "DCG source checkout cannot be used as a package")
    try:
        package.relative_to(NORMAL_DATA.resolve())
    except ValueError:
        pass
    else:
        raise PackageValidationError("DCG package cannot be inside the normal IEMS data directory")

    required = ["bin/dcg", "bin/start", "bin/status", "bin/stop", "bin/dcgaimodel",
                "config/application-local-demo.properties.example", "build-info.json",
                "THIRD-PARTY-NOTICES.txt", "sbom.cdx.json", "SHA256SUMS"]
    for name in required:
        _require((package / name).is_file(), f"DCG package is missing required file: {name}")
    for name in ("bin/dcg", "bin/start", "bin/status", "bin/stop", "bin/dcgaimodel"):
        _require(stat.S_IMODE((package / name).stat().st_mode) & 0o111, f"Package launcher is not executable: {name}")

    entries, manifest_hash = _manifest(package)
    build = json.loads((package / "build-info.json").read_text())
    version = build.get("version")
    _require(isinstance(version, str) and "-dev" in version and build.get("publication_status", "").startswith("Unpublished"),
             "Selected package is not an unpublished development package")
    artifacts = build.get("artifacts", {})
    _require(isinstance(artifacts, dict), "build-info artifacts are missing")
    for name, expected in artifacts.items():
        _safe_relative(name)
        _require(entries.get(name) == expected and HEX_256.fullmatch(expected or ""),
                 f"Manifest/provenance artifact mismatch: {name}")
    cli_name = _single_artifact(artifacts, r"lib/contract-cli-[^/]+-all\.jar", "CLI JAR")
    service_name = _single_artifact(artifacts, r"lib/contract-service-[^/]+\.jar", "service JAR")
    _require("bin/dcgaimodel" in artifacts, "Rust artifact provenance is missing")

    dependency = build.get("dependency_evidence", {})
    _require(dependency.get("notices_sha256") == entries.get("THIRD-PARTY-NOTICES.txt"),
             "Notice digest does not match build-info")
    _require(dependency.get("sbom_sha256") == entries.get("sbom.cdx.json"),
             "SBOM digest does not match build-info")
    sbom = json.loads((package / "sbom.cdx.json").read_text())
    _require(sbom.get("bomFormat") == "CycloneDX", "Packaged SBOM is not CycloneDX JSON")
    packaged_launchers = build.get("packaged_launcher_sha256", {})
    _require(set(packaged_launchers) == {"bin/dcg", "bin/start", "bin/status", "bin/stop"},
             "Packaged launcher provenance is incomplete")
    for name, digest in packaged_launchers.items():
        _require(entries.get(name) == digest, f"Packaged launcher does not match manifest: {name}")
    packaged_config = build.get("packaging_inputs", {}).get("config/application-local-demo.properties.example")
    _require(packaged_config == entries.get("config/application-local-demo.properties.example"),
             "Packaged configuration does not match provenance")

    development = build.get("development", {})
    packaging_source = development.get("packaging_source", {})
    source_commit = packaging_source.get("commit") or build.get("java_actual_source_commit")
    source_dirty = packaging_source.get("dirty")
    _require(HEX_160.fullmatch(source_commit or "") and isinstance(source_dirty, bool),
             "Development package must record a 40-character DCG source commit and dirty state")
    java_source_commit = build.get("java_actual_source_commit") or build.get("java_build_commit")
    java_source_dirty = build.get("java_actual_source_dirty")
    _require(HEX_160.fullmatch(java_source_commit or "") and
             (java_source_dirty is None or isinstance(java_source_dirty, bool)),
             "Java source provenance is incomplete")
    if build.get("java_actual_source_commit") is not None:
        _require(java_source_commit == source_commit, "Java and packaging source provenance disagree")
    java_build = development.get("java_build", {})
    if java_build:
        _require(java_build.get("source_commit") == java_source_commit
                 and isinstance(java_build.get("source_dirty"), bool),
                 "Development Java source provenance disagrees")
        _require(java_build.get("cli_sha256") == artifacts[cli_name]
                 and java_build.get("service_sha256") == artifacts[service_name],
                 "Development Java artifact hashes disagree")
    if expected_source_commit:
        _require(source_commit == expected_source_commit, "Selected package DCG source commit does not match expectation")

    platform_label, expected_target = _native_target()
    target = build.get("target")
    _require(target == expected_target,
             f"Wrong package target for native {platform_label} rehearsal: {target}")
    rust_path = package / "bin/dcgaimodel"
    _validate_rust_binary(rust_path, platform_label)
    rust_commit = build.get("rust_commit")
    _require(HEX_160.fullmatch(rust_commit or ""), "Rust source provenance is incomplete")
    rust_provenance_mode = _rust_provenance_mode(
        build, development, rust_commit, java_source_commit, source_commit, source_dirty,
        target, artifacts["bin/dcgaimodel"])

    source_artifacts = build.get("source_artifacts", {})
    model_hashes = {name: digest for name, digest in source_artifacts.items() if name.startswith("model/")}
    _require(len(model_hashes) >= 4, "Frozen model provenance is incomplete")
    for name, digest in source_artifacts.items():
        _safe_relative(name)
        _require(entries.get(name) == digest, f"Source artifact does not match manifest: {name}")
    model_files = sorted(name for name in model_hashes if "/models/seed-" in name)
    _require(len(model_files) == 3, "Expected three frozen seed model artifacts")
    model_documents = [json.loads((package / name).read_text()) for name in model_files]
    feature_versions = {item.get("feature_version") for item in model_documents}
    _require(len(feature_versions) == 1 and None not in feature_versions, "Frozen models disagree on feature schema version")

    capabilities, jar_evidence = _jar_capabilities(package, cli_name, service_name)
    launcher_text = "\n".join((package / name).read_text() for name in ("bin/dcg", "bin/start", "bin/status", "bin/stop"))
    if all(marker in launcher_text for marker in ("DCG_AI_ENABLED", "requested_ai_mode", "no Rust model process started")):
        capabilities.add("deterministic-no-ai")
    if all(marker in launcher_text for marker in ("AI advisory", "UNAVAILABLE", "dcgaimodel")):
        capabilities.add("best-effort-ai")
    capabilities.add("rust-model-advisory")
    missing = sorted(set(required_capabilities) - capabilities)
    _require(not missing, "Selected package is missing required capabilities: " + ", ".join(missing))

    archive = None
    if archive_path is not None or expected_archive_sha256 is not None:
        _require(archive_path is not None and expected_archive_sha256 is not None,
                 "archive_path and expected_archive_sha256 must be supplied together")
        archive_file = Path(archive_path).resolve(strict=True)
        actual_archive_hash = _sha(archive_file)
        _require(actual_archive_hash == expected_archive_sha256, "Archive SHA-256 does not match expectation")
        archive = {"path": str(archive_file), "sha256": actual_archive_hash}

    return {
        "path": str(package), "version": version, "platform": platform_label, "target": target,
        "source": {"commit": source_commit, "dirty": source_dirty,
                   "javaCommit": java_source_commit, "javaDirty": java_source_dirty},
        "artifacts": {"cli": {"path": cli_name, "sha256": artifacts[cli_name]},
                      "service": {"path": service_name, "sha256": artifacts[service_name]},
                      "rust": {"path": "bin/dcgaimodel", "sha256": artifacts["bin/dcgaimodel"]}},
        "rust": {"sourceCommit": rust_commit, "binarySha256": artifacts["bin/dcgaimodel"],
                 "provenanceMode": rust_provenance_mode},
        "models": model_hashes, "featureSchemaVersion": next(iter(feature_versions)),
        "capabilities": sorted(capabilities), "requiredCapabilities": sorted(required_capabilities),
        "checksums": {"result": "PASS", "entries": len(entries), "manifestSha256": manifest_hash},
        "sbomSha256": entries["sbom.cdx.json"], "noticeSha256": entries["THIRD-PARTY-NOTICES.txt"],
        "jarEvidence": jar_evidence, "archive": archive,
    }


def select_and_validate(cli_value: str | Path | None, *, environment: dict[str, str] | None = None,
                        required_capabilities: set[str] | frozenset[str] = frozenset(),
                        expected_source_commit: str | None = None) -> dict:
    path, selection = select_path(cli_value, environment)
    result = validate_package(path, required_capabilities=required_capabilities,
                              expected_source_commit=expected_source_commit)
    result["selection"] = selection
    return result
