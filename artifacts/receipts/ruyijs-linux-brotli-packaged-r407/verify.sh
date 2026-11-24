#!/bin/bash
S=/home/ruyijs-donor-isolated-moz159/native-tls-r358
{
docker run --rm --network none --read-only --cap-drop ALL --user 1000:1000 \
 --memory 1000m --memory-swap 1000m --tmpfs /tmp:rw,mode=1777,size=512m,exec \
 --mount type=bind,src=$S/wh-base,dst=/b,readonly \
 --mount type=bind,src=$S/r406-out,dst=/w,readonly \
 --mount type=bind,src=$S/brtest,dst=/t,readonly \
 sha256:a32898229c1715dff280efb9f9edc04543dea16ad79ff9acbe3ffe146a9fe3bd \
 bash -c 'python3 -IB -m venv /tmp/v >/dev/null
V=/tmp/v/bin/python
$V -IB -m pip --isolated --disable-pip-version-check --no-cache-dir --no-input install --no-index --no-deps /b/*.whl /w/*.whl >/dev/null 2>&1
SI=$($V -I -c "import sysconfig;print(sysconfig.get_path(\"platlib\"))")
echo "offered: $($V -I -B -c "
import sys; sys.path.insert(0, \"$SI\")
from ruyijs_necko import tls
print(tls._offerable_encodings())")"
$V -I -B -c "
import sys, binascii
sys.path.insert(0, \"$SI\")
from ruyijs_necko import tls
raw = bytes.fromhex(open(\"/t/payload.hex\").read().strip())
out = tls._decode(raw, \"br\")
print(\"decoded:\", out.decode())
assert out == b\"hello brotli from an independent encoder\", \"mismatch\"
print(\"DECODE_VIA_PACKAGE_OK\")
"
'
} > /tmp/r406_e2.log 2>&1
echo "RC=$?" >> /tmp/r406_e2.log
echo END >> /tmp/r406_e2.log
