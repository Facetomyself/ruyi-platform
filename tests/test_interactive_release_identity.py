"""Regression: a genuine successful candidate receipt must not qualify the published image."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

root=Path(__file__).resolve().parents[1];p=root/'scripts/verify-trace-interactive.py'
spec=importlib.util.spec_from_file_location('platform_iv',p);checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)


class ReleaseIdentity(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'evidence';shutil.copytree((root/checker.RECORD).parent,self.path);self.record=self.path/'interactive-image.json'
    def load(self,name):return json.loads((self.path/name).read_bytes())
    def change(self,name,obj,recalculate):
        target=self.path/name;target.write_text(json.dumps(obj,sort_keys=True)+'\n')
        if recalculate:
            x=self.load(self.record.name);x['evidence_sha256'][name]=hashlib.sha256(target.read_bytes()).hexdigest();self.record.write_text(json.dumps(x)+'\n')
    def test_exact_release_passes(self):self.assertTrue(checker.verify(self.record)['empty_engine_load']['passed'])
    def test_historical_candidate_still_fails_with_updated_manifest_hash(self):
        x=self.load(checker.SMOKE);x.update(image_id='sha256:3359771a84f563f73f145d67f737d9bf988f2d4345f3b9c8ea30d9b7a8136ac3',archive_sha256='4abcf01605689754fb264614430972b0f0a5224ab9300ac7a6f14eb49a6324bf');self.change(checker.SMOKE,x,True)
        with self.assertRaisesRegex(ValueError,'official release'):checker.verify(self.record)
    def test_receipt_bytes_and_archive_size_are_checked_separately(self):
        x=self.load(checker.HOST);x['archive_bytes']+=1;self.change(checker.HOST,x,False)
        with self.assertRaisesRegex(ValueError,'raw SHA-256'):checker.verify(self.record)
        self.change(checker.HOST,x,True)
        with self.assertRaisesRegex(ValueError,'byte count'):checker.verify(self.record)
    def test_coordinated_rewrite_still_requires_immutable_release_lock(self):
        x=self.load(self.record.name);x['archive']['sha256']='a'*64;self.record.write_text(json.dumps(x)+'\n')
        with self.assertRaisesRegex(ValueError,'image-tagged release lock'):checker.verify(self.record)

if __name__=='__main__':unittest.main()
