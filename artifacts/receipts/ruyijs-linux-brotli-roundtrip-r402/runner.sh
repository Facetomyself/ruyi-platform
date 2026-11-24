set -eu
S=/home/ruyijs-donor-isolated-moz159/native-tls-r358
rm -rf $S/brtest-out; mkdir -p $S/brtest-out; chmod 777 $S/brtest-out
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges=true --user 1000:1000 --memory 1000m --memory-swap 1000m --tmpfs /tmp:rw,mode=1777,size=512m,exec,nosuid,nodev --mount type=bind,src=$S/br-out,dst=/lib,readonly --mount type=bind,src=$S/brtest,dst=/t,readonly --mount type=bind,src=/root/ruyi-build/ff159/obj-x86_64-pc-linux-gnu/dist/include,dst=/inc,readonly --mount type=bind,src=$S/brtest-out,dst=/out sha256:a32898229c1715dff280efb9f9edc04543dea16ad79ff9acbe3ffe146a9fe3bd bash -c 'set -e
/usr/bin/clang-21 -std=gnu99 -O2 -I/t -I/inc -o /out/rt /t/br_roundtrip.c -L/lib -lbrotlidec -Wl,-rpath,/lib
echo COMPILED
/out/rt'
