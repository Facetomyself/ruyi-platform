set -eu
S=/home/ruyijs-donor-isolated-moz159/native-tls-r358
rm -rf $S/br-out; mkdir -p $S/br-out; chmod 777 $S/br-out
exec docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges=true \
 --user 1000:1000 --memory 1200m --memory-swap 1200m \
 --tmpfs /tmp:rw,mode=1777,size=768m,exec,nosuid,nodev \
 --mount type=bind,src=/root/ruyi-build/ff159/modules/brotli,dst=/brotli,readonly \
 --mount type=bind,src=$S/br-out,dst=/out \
 sha256:a32898229c1715dff280efb9f9edc04543dea16ad79ff9acbe3ffe146a9fe3bd \
 bash -c 'set -e
mkdir -p /tmp/b/brotli /tmp/b/common /tmp/b/dec
cp /brotli/include/brotli/*.h /tmp/b/brotli/
cp /brotli/common/*.c /brotli/common/*.h /tmp/b/common/
cp /brotli/dec/*.c /brotli/dec/*.h /tmp/b/dec/
ls /tmp/b/common/*.c /tmp/b/dec/*.c | wc -l
/usr/bin/clang-21 -std=gnu99 -O2 -fPIC -shared -I/tmp/b -I/tmp/b/common -I/tmp/b/dec -o /out/libbrotlidec.so /tmp/b/common/*.c /tmp/b/dec/*.c 2>&1 | tail -6

'
