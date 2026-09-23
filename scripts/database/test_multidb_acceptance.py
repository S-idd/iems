#!/usr/bin/env python3
"""Focused isolation and evidence checks for PostgreSQL/MySQL acceptance."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import multidb_acceptance as matrix


class DatabaseMatrixAcceptanceTest(unittest.TestCase):
    def temporary(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix='iems-database-matrix-test-'))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def test_evidence_is_private_new_and_scoped(self):
        root = self.temporary()
        with patch.object(matrix, 'REHEARSALS', root):
            evidence = matrix.prepare(root / 'database-matrix-fixture')
            self.assertEqual(0o700, evidence.stat().st_mode & 0o777)
            self.assertTrue((evidence / '.database-matrix-marker').is_file())
            with self.assertRaises(FileExistsError):
                matrix.prepare(evidence)
            with self.assertRaisesRegex(RuntimeError, 'Evidence must be'):
                matrix.prepare(root / 'wrong-name')

    def test_exact_expected_jdbc_history_is_required(self):
        rows = [
            {'contractId': 'iems.accessibility', 'status': 'PASS'},
            {'contractId': 'iems.enrollment', 'status': 'PASS'},
            {'contractId': 'iems.enrollment', 'status': 'PASS'},
            {'contractId': 'iems.enrollment', 'status': 'FAIL'},
            {'contractId': 'iems.notification', 'status': 'PASS'},
            {'contractId': 'iems.scholarship', 'status': 'PASS'},
        ]
        self.assertEqual(6, sum(matrix.validate_history(rows).values()))
        with self.assertRaisesRegex(RuntimeError, 'Unexpected DCG JDBC history'):
            matrix.validate_history(rows[:-1])

    def test_container_probe_is_portable_to_podman_emulation(self):
        with patch.object(matrix.shutil, 'which', return_value='/usr/bin/docker'), \
             patch.object(matrix, 'docker') as docker:
            matrix.verify_container_engine()
        docker.assert_called_once_with('info', timeout=30)

        with patch.object(matrix.shutil, 'which', return_value=None), \
             self.assertRaisesRegex(RuntimeError, 'Docker-compatible CLI'):
            matrix.verify_container_engine()

    def test_runtime_timezone_is_normalized_without_changing_host(self):
        with patch.dict(matrix.os.environ,
                        {'TZ': 'Asia/Calcutta', 'JAVA_TOOL_OPTIONS': '-Xmx64m'}, clear=False):
            environment = matrix.normalized_runtime_environment()
            self.assertEqual('UTC', environment['TZ'])
            self.assertEqual('-Duser.timezone=UTC', environment['JAVA_TOOL_OPTIONS'])
            self.assertEqual('Asia/Calcutta', matrix.os.environ['TZ'])
            self.assertEqual('-Xmx64m', matrix.os.environ['JAVA_TOOL_OPTIONS'])

    def test_cleanup_only_removes_containers_with_owned_label(self):
        evidence = self.temporary() / 'database-matrix-fixture'
        evidence.mkdir()
        marker = evidence / 'active-containers.json'
        marker.write_text(json.dumps([{'name': 'owned'}]))
        inspected = matrix.subprocess.CompletedProcess([], 0, evidence.name + '\n', '')
        with patch.object(matrix.subprocess, 'run', return_value=inspected), \
             patch.object(matrix, 'docker') as docker:
            self.assertTrue(matrix.cleanup_containers(evidence))
        docker.assert_called_once_with('rm', '-f', 'owned', timeout=60)
        self.assertFalse(marker.exists())

        marker.write_text(json.dumps([{'name': 'not-owned'}]))
        wrong = matrix.subprocess.CompletedProcess([], 0, 'different-run\n', '')
        with patch.object(matrix.subprocess, 'run', return_value=wrong), \
             patch.object(matrix, 'docker') as docker, \
             self.assertRaisesRegex(RuntimeError, 'ownership label changed'):
            matrix.cleanup_containers(evidence)
        docker.assert_not_called()
        self.assertTrue(marker.exists())


if __name__ == '__main__':
    unittest.main()
