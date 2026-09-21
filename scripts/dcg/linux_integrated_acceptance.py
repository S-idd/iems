#!/usr/bin/env python3
"""Bind the accepted Linux DCG archive to the complete IEMS Phase 2 rehearsal."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import sys
import tarfile

from dcg_package import PHASE2_CAPABILITIES, validate_package
import phase2_integrated_demo as phase2


ARCHIVE_NAME = "dcg-4.0.0-phase1-phase2-dev.20260920-linux-x64.tar.gz"
ARCHIVE_SHA256 = "5ec42c1c412b1ccf4fb650991ffae81804d80c08c3e77388002167cbcc8349bc"
ACCEPTANCE_REPORT_SHA256 = "c18742f6d458ee1e3e039a632d4978fcd717b1f41757b0d1cae0d3afc12e133f"
DCG_COMMIT = "18eda6434049bbebb82c9b3f339fa20521d5081a"
RUST_COMMIT = "32ca579095ed5b91749b8c33999556624e58758f"
STATUS_PROTOCOL = "advisory-v2"
STATUS_LAUNCHER_SHA256 = "1a9b749d04e270c1ee4e954cea95f0259b090868842ddf1a13c1e04398115e1d"
ACCEPTANCE_RUNNER_SHA256 = "29d2df0f371d49b484d98594588e8fe86ff660253904de45f5ed73179aba347c"
TARGET = "x86_64-unknown-linux-gnu"
ACCEPTANCE_CHECKS = (
    "archive checksum, extraction, provenance and native-target match",
    "Java absent produces actionable error",
    "CLI, Java/Rust readiness, loopback listeners and authentication",
    "repeat start leaves original processes running",
    "healthy AI prediction",
    "AI outage preserves authoritative result",
    "AI recovers without restarting Java",
    "scoped shutdown preserves unrelated sentinel",
    "clean and repeated shutdown releases ports and removes process records",
    "additional start/stop cycle 1",
    "additional start/stop cycle 2",
    "relative-path manual package Rust listener is detected and stopped",
    "persistent data integrity and immutable package files",
)
MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024


def require(condition: object, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_wsl2_host(release_path: Path = Path("/proc/sys/kernel/osrelease")) -> dict:
    system, machine = platform.system(), platform.machine().lower()
    require(system == "Linux" and machine in ("x86_64", "amd64"),
            f"This accepted rehearsal requires Linux x86_64, found {system} {machine}")
    require(release_path.is_file(), "Cannot identify the Linux kernel release")
    release = release_path.read_text().strip()
    require("microsoft" in release.lower() and "wsl2" in release.lower(),
            "This acceptance is scoped to WSL2; a different Linux host needs its own acceptance run")
    return {"system": system, "machineArch": "x86_64", "kernelRelease": release,
            "executionEnvironment": "WSL2"}


def verify_acceptance_report(report_path: Path, archive_path: Path) -> dict:
    require(report_path.is_file() and not report_path.is_symlink(),
            f"Acceptance report is not a regular file: {report_path}")
    require(archive_path.is_file() and not archive_path.is_symlink(),
            f"Archive is not a regular file: {archive_path}")
    report = json.loads(report_path.read_text())
    actual_report_hash = sha256(report_path)
    require(actual_report_hash == ACCEPTANCE_REPORT_SHA256,
            "Acceptance report SHA-256 does not match the reviewed PASS report")
    require(isinstance(report, dict), "Acceptance report must be a JSON object")
    require(report.get("status") == "PASS" and not report.get("error") and not report.get("cleanup_error"),
            "Linux archive acceptance did not finish with a clean PASS")
    require(report.get("archive") == ARCHIVE_NAME and archive_path.name == ARCHIVE_NAME,
            "Archive name does not match the accepted Linux development package")
    actual_archive_hash = sha256(archive_path)
    require(report.get("archive_sha256") == ARCHIVE_SHA256 == actual_archive_hash,
            "Archive SHA-256 does not match the accepted Linux development package")
    require(report.get("system") == "Linux" and report.get("machine_arch") == "x86_64"
            and report.get("execution_environment") == "WSL2 (not bare-metal Linux)",
            "Acceptance report is not from the required Linux x86_64 WSL2 environment")
    require(report.get("target") == TARGET and report.get("compatibility_manifest_verified") is True
            and report.get("package_relocated_before_start") is True,
            "Acceptance report is missing native target, compatibility, or relocation proof")
    require(report.get("java_build_commit") == DCG_COMMIT
            and report.get("rust_commit") == RUST_COMMIT
            and report.get("status_protocol") == STATUS_PROTOCOL,
            "Acceptance report source commits or status protocol do not match the accepted package")
    require(report.get("runner_sha256") == ACCEPTANCE_RUNNER_SHA256
            and report.get("status_launcher_sha256") == STATUS_LAUNCHER_SHA256,
            "Acceptance runner or status launcher digest does not match the reviewed PASS report")
    checks = report.get("checks")
    require(isinstance(checks, list) and len(checks) == len(ACCEPTANCE_CHECKS),
            "Acceptance report does not contain exactly 13 checks")
    names = [item.get("check") for item in checks if isinstance(item, dict)]
    require(len(names) == len(checks) and len(set(names)) == len(names)
            and set(names) == set(ACCEPTANCE_CHECKS),
            "Acceptance report check inventory differs from the accepted runner")
    require(all(item.get("status") == "PASS" for item in checks),
            "At least one Linux archive acceptance check did not pass")
    return {
        "result": "PASS",
        "reportSha256": actual_report_hash,
        "archive": ARCHIVE_NAME,
        "archiveSha256": actual_archive_hash,
        "checkCount": len(checks),
        "dcgCommit": DCG_COMMIT,
        "rustCommit": RUST_COMMIT,
        "statusProtocol": STATUS_PROTOCOL,
        "acceptedEnvironment": report["execution_environment"],
        "acceptedAt": report.get("finished_at"),
    }


def extract_archive(archive_path: Path, destination: Path) -> Path:
    require(not destination.exists(), f"Extraction destination already exists: {destination}")
    expected_root = ARCHIVE_NAME.removesuffix(".tar.gz")
    destination.mkdir(mode=0o700)
    seen: set[str] = set()
    total = 0
    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = archive.getmembers()
        require(members, "DCG archive is empty")
        for member in members:
            name = member.name.rstrip("/")
            path = PurePosixPath(name)
            require(name and "\\" not in name and not path.is_absolute()
                    and ".." not in path.parts and path.parts[0] == expected_root,
                    f"Unsafe or unexpected archive entry: {member.name!r}")
            require(name not in seen, f"Duplicate archive entry: {name}")
            seen.add(name)
            require(member.isdir() or member.isreg(),
                    f"Archive links and special files are not allowed: {member.name}")
            require(member.mode & 0o7000 == 0, f"Privileged archive mode is not allowed: {member.name}")
            if member.isreg():
                total += member.size
                require(total <= MAX_UNCOMPRESSED_BYTES, "Archive expands beyond the 2 GiB safety limit")

        for member in members:
            relative = Path(*PurePosixPath(member.name.rstrip("/")).parts)
            target = destination / relative
            if member.isdir():
                target.mkdir(parents=True, exist_ok=False)
                target.chmod(member.mode & 0o777)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            require(source is not None, f"Cannot read archive entry: {member.name}")
            with source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            target.chmod(member.mode & 0o777)
    package = destination / expected_root
    require(package.is_dir() and not package.is_symlink(), "Extracted package root is missing")
    return package.resolve()


def bind_report(evidence: Path, binding: dict, error: BaseException | None = None) -> dict:
    result_path = evidence / "results.json"
    report = json.loads(result_path.read_text()) if result_path.is_file() else {
        "phase": "phase2-linux-integrated-acceptance", "overall_result": "INCOMPLETE"}
    report["linux_archive_acceptance"] = binding
    if error is not None and "error" not in report:
        report["error"] = f"{type(error).__name__}: {error}"
    phase2.p1.write_json(result_path, report)
    return report


def run(args: argparse.Namespace) -> int:
    host = verify_wsl2_host()
    archive = args.archive.expanduser().resolve(strict=True)
    acceptance_report = args.acceptance_report.expanduser().resolve(strict=True)
    accepted = verify_acceptance_report(acceptance_report, archive)
    evidence = phase2.prepare(args.evidence)
    report_copy = evidence / "linux-archive-acceptance-report.json"
    shutil.copyfile(acceptance_report, report_copy)
    binding = {**accepted, "integratedHost": host,
               "acceptanceReport": str(report_copy), "result": "INCOMPLETE"}
    try:
        package = extract_archive(archive, evidence / "accepted-linux-package")
        validated = validate_package(
            package, required_capabilities=PHASE2_CAPABILITIES,
            expected_source_commit=DCG_COMMIT, archive_path=archive,
            expected_archive_sha256=ARCHIVE_SHA256)
        require(validated["platform"] == "linux-x64" and validated["target"] == TARGET,
                "Extracted package is not the accepted native Linux target")
        require(validated["rust"]["sourceCommit"] == RUST_COMMIT,
                "Extracted package Rust commit differs from the accepted report")
        binding.update(result="PASS", packagePath=str(package),
                       packageVersion=validated["version"],
                       rustProvenanceMode=validated["rust"]["provenanceMode"])
        report = phase2.run(evidence, package, validated)
        report = bind_report(evidence, binding)
        phase2.validate_index(report)
        print(f"PASS: {evidence / 'results.json'}")
        return 0
    except BaseException as error:
        bind_report(evidence, binding, error)
        print(f"INCOMPLETE: {type(error).__name__}: {error}; evidence: {evidence}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path,
                        help=f"Exact accepted archive named {ARCHIVE_NAME}")
    parser.add_argument("--acceptance-report", type=Path,
                        help="PASS report produced by the Linux archive acceptance runner")
    parser.add_argument("--evidence", required=True, type=Path,
                        help="New .dcg/rehearsals/phase2-integrated-linux-* directory")
    parser.add_argument("--cleanup", action="store_true",
                        help="Stop only processes recorded by an interrupted integrated run")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.cleanup:
            phase2.cleanup(args.evidence)
            return 0
        require(args.archive is not None and args.acceptance_report is not None,
                "--archive and --acceptance-report are required unless --cleanup is used")
        return run(args)
    except Exception as error:
        print(f"REFUSED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
