import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml


ENTRY = Path(__file__).resolve().parents[1] / 'scripts' / 'verify-manifests.py'
spec = importlib.util.spec_from_file_location('manifest_check', ENTRY)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ManifestSummary(unittest.TestCase):
    def test_missing_verified_and_mismatching_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifests, binaries = root/'manifests', root/'binaries'
            manifests.mkdir()
            binaries.mkdir()
            expected = b'abc'
            entry = {'name': 'sample', 'version': '1', 'filename': 'sample.zip', 'size': len(expected),
                     'sha256': hashlib.sha256(expected).hexdigest(), 'source': 'local fixture'}
            (manifests/'one.yaml').write_text(yaml.safe_dump(entry), encoding='utf-8')
            with patch.multiple(checker, MANIFEST_DIR=str(manifests), BIN_DIR=str(binaries)):
                for payload, mode, rc, counts in [
                    (None, [], 0, (0, 1, 0)),
                    (None, ['--require-local'], 1, (0, 1, 0)),
                    (expected, ['--require-local'], 0, (1, 0, 0)),
                    (b'xyz', [], 1, (0, 0, 1)),
                ]:
                    with self.subTest(payload=payload, mode=mode):
                        if payload is not None:
                            (binaries/'sample.zip').write_bytes(payload)
                        output = io.StringIO()
                        with contextlib.redirect_stdout(output):
                            self.assertEqual(checker.main(mode), rc)
                        self.assertIn('实物已核 %s，缺件跳过 %s，失败 %s' % counts, output.getvalue())


if __name__ == '__main__':
    unittest.main()
