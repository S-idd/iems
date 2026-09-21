#!/usr/bin/env python3
"""Focused trust-binding and extraction tests for Linux IEMS/DCG acceptance."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import linux_integrated_acceptance as linux


class LinuxIntegratedAcceptanceTest(unittest.TestCase):
    def temporary(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="iems-linux-acceptance-test-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    @staticmethod
    def accepted_report(archive_name: str, archive_sha256: str) -> dict:
        return {
            "status": "PASS", "archive": archive_name, "archive_sha256": archive_sha256,
            "system": "Linux", "machine_arch": "x86_64",
            "execution_environment": "WSL2 (not bare-metal Linux)",
            "target": linux.TARGET, "compatibility_manifest_verified": True,
            "package_relocated_before_start": True, "java_build_commit": linux.DCG_COMMIT,
            "rust_commit": linux.RUST_COMMIT, "status_protocol": linux.STATUS_PROTOCOL,
            "runner_sha256": linux.ACCEPTANCE_RUNNER_SHA256,
            "status_launcher_sha256": linux.STATUS_LAUNCHER_SHA256,
            "finished_at": "2026-09-20T11:39:38Z",
            "checks": [{"check": name, "status": "PASS"} for name in linux.ACCEPTANCE_CHECKS],
        }

    def report_fixture(self) -> tuple[Path, Path, str]:
        root = self.temporary()
        archive = root / "fixture.tar.gz"
        archive.write_bytes(b"accepted archive fixture")
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        report = root / "acceptance-report.json"
        report.write_text(json.dumps(self.accepted_report(archive.name, digest)))
        return archive, report, digest

    def test_exact_pass_report_and_archive_are_bound(self):
        archive, report, digest = self.report_fixture()
        with patch.object(linux, "ARCHIVE_NAME", archive.name), \
             patch.object(linux, "ARCHIVE_SHA256", digest), \
             patch.object(linux, "ACCEPTANCE_REPORT_SHA256", linux.sha256(report)):
            result = linux.verify_acceptance_report(report, archive)
        self.assertEqual("PASS", result["result"])
        self.assertEqual(13, result["checkCount"])
        self.assertEqual(digest, result["archiveSha256"])

    def test_only_linux_x86_64_wsl2_host_is_accepted(self):
        release = self.temporary() / "osrelease"
        release.write_text("6.18.33.2-microsoft-standard-WSL2\n")
        with patch.object(linux.platform, "system", return_value="Linux"), \
             patch.object(linux.platform, "machine", return_value="x86_64"):
            self.assertEqual("WSL2", linux.verify_wsl2_host(release)["executionEnvironment"])
        release.write_text("6.18.0-generic\n")
        with patch.object(linux.platform, "system", return_value="Linux"), \
             patch.object(linux.platform, "machine", return_value="x86_64"), \
             self.assertRaisesRegex(RuntimeError, "scoped to WSL2"):
            linux.verify_wsl2_host(release)

    def test_failed_or_missing_acceptance_check_is_rejected(self):
        archive, report, digest = self.report_fixture()
        data = json.loads(report.read_text())
        data["checks"][4]["status"] = "FAIL"
        report.write_text(json.dumps(data))
        with patch.object(linux, "ARCHIVE_NAME", archive.name), \
             patch.object(linux, "ARCHIVE_SHA256", digest), \
             patch.object(linux, "ACCEPTANCE_REPORT_SHA256", linux.sha256(report)), \
             self.assertRaisesRegex(RuntimeError, "did not pass"):
            linux.verify_acceptance_report(report, archive)

    def test_archive_hash_mismatch_is_rejected(self):
        archive, report, digest = self.report_fixture()
        archive.write_bytes(b"changed")
        with patch.object(linux, "ARCHIVE_NAME", archive.name), \
             patch.object(linux, "ARCHIVE_SHA256", digest), \
             patch.object(linux, "ACCEPTANCE_REPORT_SHA256", linux.sha256(report)), \
             self.assertRaisesRegex(RuntimeError, "SHA-256"):
            linux.verify_acceptance_report(report, archive)

    def make_tar(self, archive: Path, root_name: str, *, unsafe: str | None = None,
                 symlink: bool = False) -> None:
        with tarfile.open(archive, "w:gz") as output:
            root = tarfile.TarInfo(root_name)
            root.type, root.mode = tarfile.DIRTYPE, 0o755
            output.addfile(root)
            name = unsafe or f"{root_name}/bin/dcg"
            item = tarfile.TarInfo(name)
            if symlink:
                item.type, item.linkname, item.mode = tarfile.SYMTYPE, "/tmp/escape", 0o777
                output.addfile(item)
            else:
                content = b"#!/bin/sh\n"
                item.size, item.mode = len(content), 0o755
                output.addfile(item, io.BytesIO(content))

    def test_safe_archive_extracts_under_private_destination(self):
        root = self.temporary()
        name = "fixture-linux-x64"
        archive = root / f"{name}.tar.gz"
        self.make_tar(archive, name)
        destination = root / "extracted"
        with patch.object(linux, "ARCHIVE_NAME", archive.name):
            package = linux.extract_archive(archive, destination)
        self.assertEqual((destination / name).resolve(), package)
        self.assertEqual(b"#!/bin/sh\n", (package / "bin/dcg").read_bytes())
        self.assertTrue((package / "bin/dcg").stat().st_mode & 0o100)

    def test_path_traversal_and_links_are_rejected(self):
        for unsafe, symlink, message in (
                ("fixture-linux-x64/../escape", False, "Unsafe"),
                (None, True, "links and special")):
            with self.subTest(unsafe=unsafe, symlink=symlink):
                root = self.temporary()
                name = "fixture-linux-x64"
                archive = root / f"{name}.tar.gz"
                self.make_tar(archive, name, unsafe=unsafe, symlink=symlink)
                with patch.object(linux, "ARCHIVE_NAME", archive.name), \
                     self.assertRaisesRegex(RuntimeError, message):
                    linux.extract_archive(archive, root / "extracted")
                self.assertFalse((root / "escape").exists())


if __name__ == "__main__":
    unittest.main()
