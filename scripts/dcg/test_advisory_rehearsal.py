"""Fault injection is test-only; these predictions are never labelled as real model output."""
import importlib.util
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
import threading
import time
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).with_name('advisory_rehearsal.py')
spec = importlib.util.spec_from_file_location('advisory_rehearsal', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AdvisoryIsolationTest(unittest.TestCase):
    def check(self, verdict):
        return {'inputHash': 'example-hash', 'deterministicVerdict': verdict, '_payload': {}}

    def predictions(self, label):
        probabilities = {'safe': 1.0 if label == 'SAFE' else 0.0,
                         'warning': 0.0, 'breaking': 1.0 if label == 'BREAKING' else 0.0}
        return [{'seed': seed, 'label': label, 'probabilities': probabilities} for seed in module.SEEDS]

    def test_valid_advice_preserves_both_verdicts(self):
        for verdict, label in [('PASS', 'SAFE'), ('FAIL', 'BREAKING')]:
            with self.subTest(verdict=verdict), patch.object(module, 'predict', return_value=self.predictions(label)):
                result = module.advise(self.check(verdict), 'http://127.0.0.1:1', .1, {})
                self.assertEqual((result['advisoryStatus'], result['agreement'], result['deterministicVerdict']),
                                 ('AVAILABLE', 'AGREES', verdict))
                self.assertTrue(result['advisoryOnly'])
                self.assertEqual(result['inputHash'], 'example-hash')

    def test_test_only_disagreement_cannot_change_fail(self):
        with patch.object(module, 'predict', return_value=self.predictions('SAFE')):
            result = module.advise(self.check('FAIL'), 'http://127.0.0.1:1', .1, {})
        self.assertEqual(result['agreement'], 'DISAGREES')
        self.assertEqual(result['deterministicVerdict'], 'FAIL')

    def test_advisory_failures_preserve_both_verdicts(self):
        for error, status in [(ConnectionRefusedError(), 'UNAVAILABLE'),
                              (socket.timeout(), 'TIMEOUT'), (ValueError(), 'INVALID_OUTPUT'),
                              (ConnectionResetError(), 'UNAVAILABLE')]:
            for verdict in ('PASS', 'FAIL'):
                with self.subTest(error=type(error).__name__, verdict=verdict):
                    with patch.object(module, 'predict', side_effect=error):
                        result = module.advise(self.check(verdict), 'http://127.0.0.1:1', .1, {})
                    self.assertEqual(result['advisoryStatus'], status)
                    self.assertEqual(result['deterministicVerdict'], verdict)
                    self.assertEqual(result['agreement'], 'NOT_AVAILABLE')

    def test_strict_response_validation(self):
        self.assertEqual(len(module.validate({'predictions': self.predictions('SAFE')})), 3)
        invalid = self.predictions('SAFE')
        invalid[0]['probabilities']['safe'] = float('nan')
        with self.assertRaises(ValueError):
            module.validate({'predictions': invalid})
        invalid = self.predictions('SAFE')
        invalid[0]['seed'] = []
        with self.assertRaises(ValueError):
            module.validate({'predictions': invalid})

    def test_real_http_timeout_malformed_and_crash(self):
        for mode, expected in [('slow', 'TIMEOUT'), ('malformed', 'INVALID_OUTPUT'),
                               ('crash', 'UNAVAILABLE')]:
            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *_):
                    pass

                def do_POST(self):
                    self.rfile.read(int(self.headers['Content-Length']))
                    if mode == 'slow':
                        time.sleep(.1)
                    if mode == 'crash':
                        self.connection.close()
                        return
                    body = b'{"predictions":[]}'
                    try:
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(body)
                    except BrokenPipeError:
                        pass

            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for verdict in ('PASS', 'FAIL'):
                    with self.subTest(mode=mode, verdict=verdict):
                        result = module.advise(self.check(verdict),
                                               f'http://127.0.0.1:{server.server_port}', .02, {})
                        self.assertEqual(result['advisoryStatus'], expected)
                        self.assertEqual(result['deterministicVerdict'], verdict)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == '__main__':
    unittest.main()
