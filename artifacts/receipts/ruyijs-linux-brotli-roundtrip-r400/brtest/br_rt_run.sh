set -eu
S=/home/ruyijs-donor-isolated-moz159/native-tls-r358
rm -rf $S/brtest-out; mkdir -p $S/brtest-out; chmod 777 $S/brtest-out
exec docker run --rm --network none --read-only --cap-drop ALL --user 1000:1000 --memory 800m --memory-swap 800m --tmpfs /tmp:rw,mode=1777,size=512m,exec --mount type=bind,src=$S/br-out,dst=/lib,readonly --mount type=bind,src=$S/brtest,dst=/t,readonly --mount type=bind,src=/root/ruyi-build/ff159/obj-x86_64-pc-linux-gnu/dist/include,dst=/inc,readonly --entrypoint /bin/sh sha256:a32898229c1715dff280efb9f9edc04543dea16ad79ff9acbe3ffe146a9fe3bd -c 'set -e
clang-21 -std=gnu99 -O2 -I/t/.. -I/inc -I/t -o /tmp/rt /t/br_roundtrip.c -L/lib -lbrotlidec -Wl,-rpath,/lib
/tmp/rt'
