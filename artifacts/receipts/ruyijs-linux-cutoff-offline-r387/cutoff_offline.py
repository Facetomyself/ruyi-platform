"""Offline proof for the distrust cutoff: parse, bind to a real root, enforce."""
import base64, calendar, hashlib, importlib.util, json, struct, sys, time
from pathlib import Path

REPO = Path(sys.argv[1]); OUT = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location('tlsmod', REPO/'linux_http1/ruyijs_necko/tls.py')
m = importlib.util.module_from_spec(spec); sys.modules['tlsmod'] = m; spec.loader.exec_module(m)

def tlv(tag, body):
    n = len(body)
    if n < 0x80: h = bytes([n])
    else:
        b = n.to_bytes((n.bit_length()+7)//8, 'big'); h = bytes([0x80|len(b)]) + b
    return bytes([tag]) + h + body

def name(cn='example.test'):
    return tlv(0x30, tlv(0x31, tlv(0x30, tlv(0x06, b'\x55\x04\x03') + tlv(0x0c, cn.encode()))))

def leaf(not_before):
    alg = tlv(0x30, tlv(0x06, b'\x2a\x86\x48\xce\x3d\x02\x01'))
    val = tlv(0x30, tlv(0x17, not_before) + tlv(0x17, b'400101000000Z'))
    spki = tlv(0x30, tlv(0x30, b'\x05\x00') + tlv(0x03, b'\x00\x01'))
    tbs = tlv(0x30, tlv(0x02, b'\x01') + alg + name() + val + name() + spki)
    c = tlv(0x30, tbs)
    return struct.pack('>I', len(c)) + c

bundle = (REPO/'native/necko_tls/necko_win/firefox-roots.pem').read_bytes()
anchors = m._anchor_blobs(bundle, REPO)
table = json.loads((REPO/'native/necko_tls/necko_win/firefox-root-constraints.json').read_text())
digest, when = next(iter(table.items()))
cutoff = m._parse_cutoff(when, digest)
bound = any(hashlib.sha256(a).hexdigest() == digest for a in anchors)

# A leaf dated after the cutoff must be refused when that root is trusted.
after = leaf(b'260501000000Z')
refused = False
try:
    m._enforce_cutoff(after, anchors, {digest: cutoff})
except m.TLSError as e:
    refused = 'distrust cutoff' in str(e)
before = leaf(b'260101000000Z')
m._enforce_cutoff(before, anchors, {digest: cutoff})
allowed = True
# The table is irrelevant when the caller does not trust that root.
m._enforce_cutoff(after, [b'\x30\x03xyz'], {digest: cutoff})
ignored = True

rep = {
  'anchors_in_bundle': len(anchors),
  'cutoff_keys': len(table),
  'cutoff_bound_to_bundle_root': bound,
  'cutoff_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(cutoff)),
  'leaf_after_cutoff_refused': refused,
  'leaf_before_cutoff_allowed': allowed,
  'untrusted_root_cutoff_ignored': ignored,
  'passed': bound and refused and allowed and ignored,
}
OUT.write_text(json.dumps(rep, indent=2, sort_keys=True) + '\n')
print(json.dumps(rep))
sys.exit(0 if rep['passed'] else 1)
