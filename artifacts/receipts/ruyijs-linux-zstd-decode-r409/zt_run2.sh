#!/bin/bash
S=/home/ruyijs-donor-isolated-moz159/native-tls-r358
Z=/root/ruyi-build/ff159/third_party/zstd/lib
rm -rf $S/zt3; mkdir -p $S/zt3/src; chmod -R 777 $S/zt3
cp -r $Z/common $Z/decompress $S/zt3/src/
cp $Z/*.h $S/zt3/src/
cp /tmp/zt_dec.c /tmp/zpayload.inc $S/zt3/src/
chmod -R a+rX $S/zt3
{
docker run --rm --network none --read-only --cap-drop ALL --user 1000:1000 \
 --memory 900m --memory-swap 900m --tmpfs /tmp:rw,mode=1777,size=400m,exec \
 --mount type=bind,src=$S/zt3,dst=/z \
 --entrypoint /bin/bash \
 sha256:a32898229c1715dff280efb9f9edc04543dea16ad79ff9acbe3ffe146a9fe3bd \
 -c 'set -e; cd /z/src && clang-21 -O2 -DZSTD_DISABLE_ASM -I. -I common -I decompress -o /tmp/t zt_dec.c common/*.c decompress/*.c && echo BUILT && /tmp/t'
} > /tmp/z10.log 2>&1
echo "RC=$?" >> /tmp/z10.log
echo END >> /tmp/z10.log
