#!/bin/bash
S=/home/ruyijs-donor-isolated-moz159/native-tls-r358
{
docker run --rm --network none --read-only --cap-drop ALL --user 1000:1000 \
 --memory 900m --memory-swap 900m --tmpfs /tmp:rw,mode=1777,size=400m,exec \
 --mount type=bind,src=$S/brtest,dst=/t \
 --entrypoint /bin/bash \
 sha256:a32898229c1715dff280efb9f9edc04543dea16ad79ff9acbe3ffe146a9fe3bd \
 -c 'set -e; cd /tmp && clang-21 -O2 -I/t -o /tmp/rt /t/br_roundtrip.c -L/t -lbrotlidec -Wl,-rpath,/t && echo BUILT && LD_LIBRARY_PATH=/t /tmp/rt'
} > /tmp/br_b3.log 2>&1
echo "RC=$?" >> /tmp/br_b3.log
echo END >> /tmp/br_b3.log
