#!/usr/bin/env python3
"""Focused selection, integrity, provenance, platform, and capability tests."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import dcg_package as package
import phase2_service_demo as service


LIVE_PACKAGE = os.environ.get("IEMS_DCG_PACKAGE_TEST_ROOT")


@unittest.skipUnless(LIVE_PACKAGE, "Set IEMS_DCG_PACKAGE_TEST_ROOT to a verified package")
class PackageSelectionValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonical = Path(LIVE_PACKAGE).resolve()
        package.validate_package(cls.canonical, required_capabilities=package.PHASE2_CAPABILITIES)

    def clone(self) -> Path:
        temporary = Path(tempfile.mkdtemp(prefix="iems-dcg-package-test-"))
        self.addCleanup(lambda: shutil.rmtree(temporary, ignore_errors=True))
        target = temporary / "package"
        shutil.copytree(self.canonical, target, copy_function=os.link)
        return target

    @staticmethod
    def digest(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def manifest_update(self, root: Path, name: str, digest: str) -> None:
        manifest = root / "SHA256SUMS"
        lines = []
        found = False
        for line in manifest.read_text().splitlines():
            _, current = line.split("  ", 1)
            if current == name:
                line, found = f"{digest}  {name}", True
            lines.append(line)
        self.assertTrue(found, name)
        manifest.unlink()
        manifest.write_text("\n".join(lines) + "\n")

    def replace(self, root: Path, name: str, data: bytes) -> str:
        target = root / name
        target.unlink()
        target.write_bytes(data)
        if name.startswith("bin/"):
            target.chmod(0o755)
        digest = self.digest(data)
        self.manifest_update(root, name, digest)
        return digest

    def save_build(self, root: Path, build: dict) -> None:
        data = (json.dumps(build, indent=2, sort_keys=True) + "\n").encode()
        self.replace(root, "build-info.json", data)

    def test_01_cli_selects_valid_package(self):
        result = package.select_and_validate(self.canonical, environment={},
                                             required_capabilities=package.PHASE2_CAPABILITIES)
        self.assertEqual("cli", result["selection"]["source"])

    def test_02_environment_selects_valid_package(self):
        result = package.select_and_validate(None, environment={"DCG_HOME": str(self.canonical)},
                                             required_capabilities=package.PHASE1_CAPABILITIES)
        self.assertEqual("environment", result["selection"]["source"])

    def test_03_cli_overrides_environment(self):
        result = package.select_and_validate(self.canonical, environment={"DCG_HOME": "/missing"})
        self.assertTrue(result["selection"]["cliPrecedenceApplied"])
        self.assertEqual(str(self.canonical), result["path"])

    def test_04_missing_configuration_fails_clearly(self):
        with self.assertRaisesRegex(package.PackageValidationError, "--dcg-home or DCG_HOME"):
            package.select_and_validate(None, environment={})

    def test_05_missing_directory_fails(self):
        with self.assertRaisesRegex(package.PackageValidationError, "does not exist"):
            package.validate_package("/private/tmp/this-dcg-package-does-not-exist")

    def test_06_source_checkout_is_rejected(self):
        root = Path(tempfile.mkdtemp(prefix="fake-dcg-source-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        (root / ".git").mkdir(); (root / "contract-service").mkdir(); (root / "pom.xml").write_text("<project/>")
        with self.assertRaisesRegex(package.PackageValidationError, "source checkout"):
            package.validate_package(root)

    def test_07_tampered_payload_is_rejected(self):
        root = self.clone()
        target = root / "README.md"; target.unlink(); target.write_text("tampered\n")
        with self.assertRaisesRegex(package.PackageValidationError, "checksum mismatch"):
            package.validate_package(root)

    def test_08_missing_manifest_is_rejected(self):
        root = self.clone(); (root / "SHA256SUMS").unlink()
        with self.assertRaisesRegex(package.PackageValidationError, "missing required file: SHA256SUMS"):
            package.validate_package(root)

    def test_09_manifest_provenance_mismatch_is_rejected(self):
        root = self.clone(); build = json.loads((root / "build-info.json").read_text())
        cli = next(name for name in build["artifacts"] if "contract-cli" in name)
        build["artifacts"][cli] = "0" * 64
        self.save_build(root, build)
        with self.assertRaisesRegex(package.PackageValidationError, "Manifest/provenance"):
            package.validate_package(root)

    def test_10_wrong_platform_is_rejected(self):
        root = self.clone(); build = json.loads((root / "build-info.json").read_text())
        build["target"] = "x86_64-unknown-linux-gnu"
        build["development"]["rust_reuse"]["target"] = build["target"]
        self.save_build(root, build)
        with self.assertRaisesRegex(package.PackageValidationError, "Wrong package target"):
            package.validate_package(root)

    def test_11_wrong_rust_architecture_is_rejected(self):
        root = self.clone(); binary = bytearray((root / "bin/dcgaimodel").read_bytes())
        binary[4:8] = (0x01000007).to_bytes(4, "little")
        digest = self.replace(root, "bin/dcgaimodel", bytes(binary))
        build = json.loads((root / "build-info.json").read_text())
        build["artifacts"]["bin/dcgaimodel"] = digest
        build["development"]["rust_reuse"]["artifact_sha256"] = digest
        self.save_build(root, build)
        with self.assertRaisesRegex(package.PackageValidationError, "not a thin macOS ARM64"):
            package.validate_package(root)

    def test_11_linux_x86_64_package_is_accepted_on_native_linux(self):
        root = self.clone()
        binary = bytearray((root / "bin/dcgaimodel").read_bytes())
        binary[:20] = bytes(20)
        binary[:4] = b"\x7fELF"
        binary[4] = 2
        binary[5] = 1
        binary[18:20] = (62).to_bytes(2, "little")
        digest = self.replace(root, "bin/dcgaimodel", bytes(binary))
        build = json.loads((root / "build-info.json").read_text())
        build["target"] = "x86_64-unknown-linux-gnu"
        build["artifacts"]["bin/dcgaimodel"] = digest
        build["development"]["rust_reuse"]["target"] = build["target"]
        build["development"]["rust_reuse"]["artifact_sha256"] = digest
        self.save_build(root, build)
        with patch.object(package.platform, "system", return_value="Linux"), \
             patch.object(package.platform, "machine", return_value="x86_64"):
            result = package.validate_package(root, required_capabilities=package.PHASE2_CAPABILITIES)
        self.assertEqual("linux-x64", result["platform"])
        self.assertEqual("x86_64-unknown-linux-gnu", result["target"])

    def test_11_linux_wrong_rust_architecture_is_rejected(self):
        root = self.clone()
        binary = bytearray((root / "bin/dcgaimodel").read_bytes())
        binary[:20] = bytes(20)
        binary[:4] = b"\x7fELF"
        binary[4] = 2
        binary[5] = 1
        binary[18:20] = (183).to_bytes(2, "little")
        digest = self.replace(root, "bin/dcgaimodel", bytes(binary))
        build = json.loads((root / "build-info.json").read_text())
        build["target"] = "x86_64-unknown-linux-gnu"
        build["artifacts"]["bin/dcgaimodel"] = digest
        build["development"]["rust_reuse"]["target"] = build["target"]
        build["development"]["rust_reuse"]["artifact_sha256"] = digest
        self.save_build(root, build)
        with patch.object(package.platform, "system", return_value="Linux"), \
             patch.object(package.platform, "machine", return_value="x86_64"), \
             self.assertRaisesRegex(package.PackageValidationError, "not a Linux ELF64 x86-64"):
            package.validate_package(root)

    def test_12_missing_phase1_capability_is_rejected(self):
        root = self.clone(); build = json.loads((root / "build-info.json").read_text())
        for name in ("bin/dcg", "bin/start"):
            data = (root / name).read_text().replace("requested_ai_mode", "removed_ai_mode")
            if name == "bin/start":
                data = data.replace("no Rust model process started", "model bypassed")
            digest = self.replace(root, name, data.encode())
            build["packaged_launcher_sha256"][name] = digest
        self.save_build(root, build)
        with self.assertRaisesRegex(package.PackageValidationError, "deterministic-no-ai"):
            package.validate_package(root, required_capabilities=package.PHASE1_CAPABILITIES)

    def test_13_missing_phase2_capability_is_rejected(self):
        root = self.clone(); build = json.loads((root / "build-info.json").read_text())
        service_name = next(name for name in build["artifacts"] if "contract-service" in name)
        source = root / service_name
        output = io.BytesIO()
        removed = "BOOT-INF/classes/com/ideas/contracts/service/model/CheckRunAdvisoryResponse.class"
        with zipfile.ZipFile(source) as reader, zipfile.ZipFile(output, "w") as writer:
            for info in reader.infolist():
                if info.filename != removed:
                    writer.writestr(info, reader.read(info.filename))
        digest = self.replace(root, service_name, output.getvalue())
        build["artifacts"][service_name] = digest
        build["development"]["java_build"]["service_sha256"] = digest
        self.save_build(root, build)
        with self.assertRaisesRegex(package.PackageValidationError, "advisory-rest"):
            package.validate_package(root, required_capabilities=package.PHASE2_CAPABILITIES)

    def test_14_selected_package_is_accepted_for_phase1_capabilities(self):
        result = package.validate_package(self.canonical,
                                          required_capabilities=package.PHASE1_CAPABILITIES)
        self.assertIn("deterministic-no-ai", result["capabilities"])
        self.assertTrue(package.PHASE1_CAPABILITIES <= set(result["capabilities"]))

    def test_15_future_version_is_accepted_without_source_change(self):
        root = self.clone(); build = json.loads((root / "build-info.json").read_text())
        build["version"] = "5.0.0-phase1-phase2-dev.future"
        build["development"]["version"] = build["version"]
        self.save_build(root, build)
        self.assertEqual(build["version"], package.validate_package(
            root, required_capabilities=package.PHASE2_CAPABILITIES)["version"])

    def test_16_runner_validates_before_starting_service(self):
        evidence = Path(tempfile.mkdtemp(prefix="phase2-service-invalid-"))
        evidence.rmdir()
        self.addCleanup(lambda: shutil.rmtree(evidence, ignore_errors=True))
        argv = ["phase2_service_demo.py", "--dcg-home", "/missing/package", "--evidence", str(evidence)]
        with patch.object(sys, "argv", argv), patch.object(service.subprocess, "Popen") as popen:
            with self.assertRaisesRegex(package.PackageValidationError, "does not exist"):
                service.main()
        popen.assert_not_called()
        self.assertFalse(evidence.exists())

    def test_17_validated_metadata_is_json_evidence_ready(self):
        value = package.validate_package(self.canonical, required_capabilities=package.PHASE2_CAPABILITIES)
        encoded = json.loads(json.dumps({"validated_package": value}))
        self.assertEqual("PASS", encoded["validated_package"]["checksums"]["result"])
        self.assertEqual(40, len(encoded["validated_package"]["source"]["commit"]))

    def test_18_test_only_adapter_defaults_disabled(self):
        value = package.validate_package(self.canonical, required_capabilities=package.PHASE2_CAPABILITIES)
        self.assertTrue(value["jarEvidence"]["testOnlyAdapterDisabledByDefault"])

    def test_19_expected_archive_and_source_hashes_are_enforced(self):
        archive = os.environ.get("IEMS_DCG_PACKAGE_TEST_ARCHIVE")
        expected = os.environ.get("IEMS_DCG_PACKAGE_TEST_ARCHIVE_SHA256")
        if not archive or not expected:
            self.skipTest("Archive hash inputs not set")
        source_commit = json.loads((self.canonical / "build-info.json").read_text())["development"][
            "packaging_source"]["commit"]
        result = package.validate_package(self.canonical, archive_path=archive,
                                          expected_archive_sha256=expected,
                                          expected_source_commit=source_commit)
        self.assertEqual(expected, result["archive"]["sha256"])


if __name__ == "__main__":
    unittest.main()
