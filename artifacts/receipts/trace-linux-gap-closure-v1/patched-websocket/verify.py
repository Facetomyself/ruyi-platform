#!/usr/bin/env python3
"""Offline patched-Gecko acceptance core and frozen ARM64 command (stdlib only)."""

import argparse
import configparser
from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import struct
import tarfile
import zipfile

HERE = Path(__file__).resolve().parent
ARCH, MACHINE = 'linux/arm64', 183
BUILD, VERSION = '20261125162841', '159.0'
PRODUCT = 'f177682d8dc4e028ad450a00f2d78acc4063e321'
GECKO = '9a2dc53c369c7ae5172018b35988e1d2ffeff402'
GECKO_TREE = '7a8dd864f3e99cc350dbb47dcaf123fe60218c51'
PATCH = '3cecbf0b086ff1b630f79ce493d2c4f64782bdf96feb05a9d0a9db57fff3e45b'
SOURCE_SET = 'd97edbcbb9e3d9849518d8b00f1ac24ff7b0b5ba6266ce436c69b9b46472baf5'
IMAGE = 'sha256:ecb43c4ef8f448d41bce4213954bb202d308287fc21826ad38952b52e331c8ab'
BASE = 'sha256:9073c375ff26a8248e055e54f1ca28f289d92fc7f253d36685973fa8ecdd33bc'
STOCK_OVERLAY = 'sha256:1ae4616eeabc8d3b4317e25162221fe2f47dc1c60d8a14f91af2a4d22215791e'
KERNEL = '53747262e3af06ec0e4b98806efed38225b51b3c83b8b8d877eba133e4c9eacf'
KERNEL_BYTES = 74812416
LIBXUL = '2e67090fb4450346076c45a39b1871d589f5da458a2f2cba710091c3e337fb24'
ARCHIVE = '10d940ce5a502fe7652ae7685534e16c7fdeb03579ea48d730453597e458ee33'
ARCHIVE_BYTES = 494839061
ARCHIVE_PROOF = '4691dc0c2183cdfd42c2871578aa2431ea7ef4abdd435f39fbd6c97729ed165f'
IMAGE_MANIFEST = '26a2aa3dc226a79ecf746d68862b423b2fbe0f3824152f6676924fd89a56c215'
FIXTURE = 'b831052eca466c39856b182b96029051791766de22633a31d317610251074658'
SCRIPT = 'e59743eb8c208764e7ddb1ea43ad3f80c39a1fa989d05d2fdfecee52ba4b314f'
INDEX_SHA = '185aac65ddd85fd0b8973e18981fe37ba6c7b1edba3bc85473ad5a4b6cac71f3'

@dataclass(frozen=True)
class LanePins:
    arch: str
    machine: int
    native_arch: str
    host: str
    elf_label: str
    build: str
    product: str
    base: str
    stock_overlay: str
    image: str
    kernel: str
    kernel_bytes: int
    libxul: str
    archive: str
    archive_bytes: int
    archive_proof: str
    image_manifest: str
    source_set: str
    day: str

    @property
    def cpu(self):
        return self.arch.split('/')[1]

    @property
    def archive_name(self):
        return f'ruyitrace-native-{self.cpu}-{self.image[7:23]}.docker.tar.gz'

    @property
    def kernel_name(self):
        return f'firefox-{VERSION}.en-US.linux-{self.native_arch}.tar.xz'


ARM64 = LanePins(arch=ARCH, machine=MACHINE, native_arch='aarch64', host='oracle-reverse-dev', elf_label='AArch64',
                 build=BUILD, product=PRODUCT, base=BASE, stock_overlay=STOCK_OVERLAY, image=IMAGE,
                 kernel=KERNEL, kernel_bytes=KERNEL_BYTES, libxul=LIBXUL, archive=ARCHIVE, archive_bytes=ARCHIVE_BYTES,
                 archive_proof=ARCHIVE_PROOF, image_manifest=IMAGE_MANIFEST, source_set=SOURCE_SET, day='2026-11-26')


SOURCES = ('Policy.sys.mjs', 'RuyiNativeTelemetryChild.sys.mjs', 'RuyiNativeTelemetryParent.sys.mjs',
           'Start.sys.mjs', 'Writer.sys.mjs', 'build_image.py', 'compute/Compute.sys.mjs',
           'config.py', 'launch.py', 'net/Network.sys.mjs')
ORIGINALS = ('native-ready.json', 'native-armed.json', 'native-events.jsonl', 'native-sealed.json')
ROOT_MEMBERS = sorted((*ORIGINALS, 'home', 'native-config.json', 'native-start', 'native-stop',
                       'native-writer.lock', 'profile', 'xdg'))
IDS = ('schema', 'runId', 'origin', 'mode', 'documentPath', 'enabled', 'writerPid', 'contentPid',
       'browsingContextId', 'innerWindowId')
DROPS = dict(invalid=0, scope=0, limit=0, protocol=0, io=0)
TRANSPORT = dict(socketProcessEnabled=True, httpNetworkAccessOnSocketProcessEnabled=False,
                 forceUseSocketProcessEnvPresent=False, socketProcessLaunched=True)
TX = [[1, 1, 5], [10, 1, 1], [8, 1, 2]]
RX = [[1, 1, 5], [1, 0, 4], [9, 1, 1], [0, 1, 4], [8, 1, 2]]
CLOSE = [[8, 1, 2]]
WS_ORDER = [[1, d, *f] for d, f in (('tx', TX[0]), ('rx', RX[0]), ('rx', RX[1]), ('rx', RX[2]),
                                      ('tx', TX[1]), ('rx', RX[3]), ('tx', TX[2]), ('rx', RX[4]))]
PAIRS = [[n, k] for n in (1, 2, 3) for k in ('enter', 'return')]
THROW = [[1, 'enter'], [1, 'throw']]
CASES = {
    'websocket': dict(fragment_and_ping=WS_ORDER, upgrade_only=[[1, 'tx', *CLOSE[0]], [1, 'rx', *CLOSE[0]]],
                      skip=[], disabled=[], other_origin=[]),
    'jscall': dict(normal=PAIRS, throw=THROW, skip=[], disabled=[], other_origin=[]),
    'wasm': dict(call_export=PAIRS, trap=THROW, compile_only=[], instantiate_only=[], disabled=[], other_origin=[]),
    'http': dict(fetch=[[1, 'network', 'GET', 200]], redirect=[[1, 'network', 'GET', 302], [1, 'network', 'GET', 200]],
                 cache_hit=[[1, 'cache', 'GET', 200]], skip=[], disabled=[], other_origin=[]),
}
CELLS = {f'{g}--{c}' for g, cases in CASES.items() for c in cases}


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('ascii')


def same(actual, expected, reason):
    # JSON comparisons must distinguish e.g. true vs 1 and 8.0 vs 8.
    need(canonical(actual) == canonical(expected), reason)


def object_at(raw):
    def unique(items):
        out = dict(items)
        need(len(out) == len(items), 'duplicate JSON field')
        return out

    def invalid(value):
        raise ValueError('invalid JSON constant: ' + value)

    need(0 < len(raw) <= 131072, 'JSON byte bound')
    obj = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=invalid)
    need(type(obj) is dict, 'expected JSON object')
    return obj


def match(value, regex, reason):
    need(type(value) is str and re.fullmatch(regex, value) is not None, reason)


def bytes_record(raw):
    return dict(bytes=len(raw), sha256=sha(raw))


def load_zip(path):
    need(path.is_file() and not path.is_symlink() and path.stat().st_size <= 600000, 'bounded regular ZIP required')
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        need(1 < len(infos) < 650 and sum(x.file_size for x in infos) <= 2000000, 'ZIP expansion bound')
        out = {}
        for info in infos:
            name = info.filename
            match(name, r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', 'unsafe ZIP path')
            need(not ({'.', '..'} & set(name.split('/'))) and info.orig_filename == name and name not in out
                 and not info.is_dir() and stat.S_ISREG(info.external_attr >> 16) and 0 < info.file_size <= 131072,
                 'duplicate, nonregular or oversized ZIP entry')
            out[name] = archive.read(info)
            need(len(out[name]) == info.file_size, 'ZIP length mismatch')
    index = out.pop('original-byte-index.json')
    need(sha(index) == INDEX_SHA, 'unexpected original-byte index SHA-256')
    same(object_at(index), {name: bytes_record(raw) for name, raw in out.items()}, 'original-byte index mismatch')
    return out


class Evidence:
    def __init__(self, blobs):
        self.blobs, self.used = blobs, set()

    def raw(self, name):
        need(name in self.blobs, 'missing original: ' + name)
        self.used.add(name)
        return self.blobs[name]

    def obj(self, name):
        return object_at(self.raw(name))

    def end(self):
        need(self.used == set(self.blobs), 'extra unreviewed evidence member')


def opened(p, limit):
    need(p.is_file() and not p.is_symlink() and p.stat().st_size == limit, 'artifact size or type mismatch')
    digest = hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def elf_notes(head):
    need(len(head) >= 64 and head[:6] == b'\x7fELF\x02\x01', 'wrong native ELF class or endianness')
    machine = struct.unpack_from('<H', head, 18)[0]
    off = struct.unpack_from('<Q', head, 32)[0]
    ent, count = struct.unpack_from('<HH', head, 54)
    need(ent == 56 and 0 < count <= 128 and 64 <= off <= len(head) - ent * count, 'invalid ELF program headers')
    notes = {}
    for i in range(count):
        typ, _, pos, _, _, size, _, _ = struct.unpack_from('<IIQQQQQQ', head, off + ent * i)
        if typ != 4:
            continue
        end = pos + size
        need(end <= len(head), 'ELF note segments outside readback bound')
        while pos < end:
            need(end - pos >= 12, 'truncated ELF note header')
            namesz, descsz, kind = struct.unpack_from('<III', head, pos)
            begin = pos + 12
            desc = begin + ((namesz + 3) & ~3)
            pos = desc + ((descsz + 3) & ~3)
            need(pos <= end, 'truncated ELF note body')
            identity = (head[begin:begin + namesz].rstrip(b'\0'), kind)
            if identity in {(b'GNU', 3), (b'mzbldid', 1)}:
                need(identity not in notes, 'duplicate ELF build ID note')
                notes[identity] = head[desc:desc + descsz]
    return machine, notes


def read_kernel_archive(path, receipt, *, pins=ARM64):
    """Rehash every TAR member from the pinned archive, without extracting files."""
    need(opened(path, pins.kernel_bytes) == pins.kernel, 'local complete kernel archive SHA mismatch')
    seen = set()
    with tarfile.open(path, 'r|xz') as arc:
        for item in arc:
            name = item.name
            need(name in receipt['members'] and name not in seen, 'missing, duplicate or unexpected TAR member')
            seen.add(name)
            expected = receipt['members'][name]
            if item.isdir():
                same(expected, dict(type='directory'), 'native TAR member kind')
                continue
            need(item.isfile() and expected['type'] == 'file' and item.size == expected['bytes'], 'native TAR member shape')
            with arc.extractfile(item) as stream:
                head = stream.read(65536)
                digest = hashlib.sha256(head)
                total = len(head)
                for part in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(part)
                    total += len(part)
            same(dict(type='file', bytes=total, sha256=digest.hexdigest()), expected, 'native TAR member readback')
            if name == 'firefox/libxul.so':
                machine, notes = elf_notes(head)
                same([machine, notes[(b'GNU', 3)].hex(), notes[(b'mzbldid', 1)].rstrip(b'\0').decode('ascii')],
                     [pins.machine, receipt['packaged_libxul']['elf_build_id'], pins.build], 'packaged ELF architecture/GNU/upstream IDs')
            if name in {'firefox/application.ini', 'firefox/platform.ini'}:
                parser = configparser.ConfigParser(interpolation=None)
                parser.read_string(head.decode('utf-8'))
                s, v = ('App', 'Version') if name.endswith('/application.ini') else ('Build', 'Milestone')
                same([parser[s][v], parser[s]['BuildID'], parser[s]['SourceStamp']], [VERSION, pins.build, GECKO],
                     'packaged INI source/build stamp')
    need(seen == receipt['members'].keys(), 'native archive member enumeration mismatch')


def read_operator_archive(path, proof, *, pins=ARM64):
    """Rehash the full gzip, its selected config, and all five uncompressed layers."""
    need(opened(path, pins.archive_bytes) == pins.archive, 'local complete operator archive SHA mismatch')
    selected = f'blobs/sha256/{pins.image[7:]}'
    docs, diff, names = {}, {}, set()
    with gzip.open(path, 'rb') as source:
        with tarfile.open(fileobj=source, mode='r|') as arc:
            for item in arc:
                name = item.name
                match(name, r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', 'invalid Docker TAR member name')
                need(name not in names and not ({'.', '..'} & set(name.split('/'))) and len(names) < 128,
                     'unexpected Docker TAR member set')
                names.add(name)
                if item.isdir():
                    continue
                need(item.isfile() and 0 <= item.size <= 2**31, 'invalid Docker TAR member type or size')
                with arc.extractfile(item) as stream:
                    if name in {'manifest.json', 'repositories', selected}:
                        need(0 < item.size <= 131072, 'invalid Docker config or manifest size')
                        docs[name] = stream.read()
                        continue
                    if not re.fullmatch(r'blobs/sha256/[a-f0-9]{64}', name):
                        continue
                    digest, count = hashlib.sha256(), 0
                    unpack = gzip.GzipFile(fileobj=stream) if stream.peek(2).startswith(b'\x1f\x8b') else stream
                    with unpack:
                        for part in iter(lambda: unpack.read(1024 * 1024), b''):
                            count += len(part)
                            need(count <= 2**31, 'Docker layer expansion bound')
                            digest.update(part)
                    diff[name] = 'sha256:' + digest.hexdigest()
        for pad in iter(lambda: source.read(65536), b''):
            need(not any(pad), 'nonzero Docker TAR trailer')
    manifest = json.loads(docs['manifest.json'])
    need(type(manifest) is list and len(manifest) == 1, 'expected one Docker image manifest')
    m = manifest[0]
    need(m['Config'] == selected and not m.get('RepoTags'), 'unexpected Docker selected config or mutable tags')
    same(object_at(docs.get('repositories', b'{}')), {}, 'named repository entries')
    cfg_b = docs[selected]
    need('sha256:' + sha(cfg_b) == pins.image, 'local Docker config digest')
    cfg = object_at(cfg_b)
    same([cfg['os'], cfg['architecture'], cfg['config']['User'], cfg['rootfs']['type']],
         ['linux', pins.cpu, '1000:1000', 'layers'], 'local Docker platform or unprivileged user')
    same([diff[n] for n in m['Layers']], cfg['rootfs']['diff_ids'], 'local Docker content differs from claimed layers')
    same(cfg['rootfs']['diff_ids'], proof['rootfs_diffids'], 'local Docker content differs from installed-run host layers')
    labels = cfg['config']['Labels']
    same([labels['io.ruyitrace.native.base'], labels['io.ruyitrace.native.package.sha256'],
          labels['io.ruyitrace.product.scope']],
         [pins.base, proof['installed_package_sha256'], 'native-events-candidate'], 'local Docker package labels')
    need(not cfg['config'].get('ExposedPorts') and not cfg['config'].get('Volumes'), 'unexpected Docker ports or volumes')
    return dict(bytes=pins.archive_bytes, sha256=pins.archive, config=pins.image, diff_ids=cfg['rootfs']['diff_ids'], gzip_crc=True)


def validate_release(e, *, pins=ARM64):
    proof_b = e.raw('export/archive-proof.json')
    img_b = e.raw('image/image.json')
    need(sha(proof_b) == pins.archive_proof and sha(img_b) == pins.image_manifest, 'wrong release proof or runtime manifest SHA')
    proof, img = object_at(proof_b), object_at(img_b)
    package_b = e.raw('export/installed-package.json')
    package = object_at(package_b)
    files = {name: sha(e.raw(f'source/{name}')) for name in SOURCES}
    need(sha(canonical(files)) == pins.source_set and img['source_set_sha256'] == pins.source_set, 'mixed product source bytes')
    levels = proof['rootfs_diffids']
    need(len(set(levels)) == len(levels) == 5 and levels[-1] == img['overlay_diff_id'], 'rootfs diffID chain')
    for x in levels:
        match(x, r'sha256:[a-f0-9]{64}', 'bad layer digest')
    same(proof, dict(schema='ruyitrace.native-artifact-readback.v1', source=pins.product, platform=pins.arch,
                     image_id=pins.image, base=pins.base, build_id=pins.build, archive_sha256=pins.archive, archive_bytes=pins.archive_bytes,
                     gzip_crc_verified=True, installed_bytes_match=True, diffid_readback=True, passed=True,
                     config_ids=[pins.image], repository_tags=0, archive=pins.archive_name,
                     patched_kernel_sha256=pins.kernel, installed_package_sha256=sha(package_b),
                     rootfs_diffids=levels, source_files=files, utc=proof['utc']), 'wrong export identity or installed readback')
    ctrl = e.obj('export/controller.json')
    need(ctrl['ok'] is True and ctrl['source'] == pins.product and ctrl['image'] == pins.image, 'wrong export controller')
    same(img, dict(package, candidate_image_id=pins.image, manifest_sha256=sha(package_b), overlay_diff_id=levels[-1]),
         'runtime did not use exported installed bytes')
    same([img[k] for k in ('architecture', 'build_id', 'old_build_id', 'firefox_version', 'firefox_root',
                           'base_image_id', 'patched_firefox_archive_sha256', 'scope', 'source_sha256')],
         [pins.cpu, pins.build, pins.build, VERSION, '/browser', pins.base, pins.kernel, 'native-events-candidate', files], 'mixed build identity')
    same(img['archive_modules'], {'modules/ruyi-native/' + n: v for n, v in files.items() if n.endswith('.sys.mjs')},
         'runtime archive module source digest mismatch')
    before, after = img['old_package_sha256'], img['package_sha256']
    same(sorted(before), sorted(after), 'runtime package inventory changed')
    same({n for n in before if before[n] != after[n]} == {'libxul.so', 'omni.ja'}, True,
         'runtime overlay must change libxul and omni.ja only')
    need(after['libxul.so'] == pins.libxul and img['pre_overlay_omni_sha256'] == before['omni.ja'], 'native/JS overlay conflated')
    return levels, img


def check_tokens(raw, tokens, label):
    for token in tokens:
        need(token.encode('ascii') in raw, f'{label}: missing source invariant: {token}')


def validate_kernel(e, img, *, pins=ARM64):
    lineage = e.obj('kernel/lineage.json')
    patch, actualdiff = e.raw('kernel/gecko-v2.patch'), e.raw('kernel/effective.diff')
    src = lineage['source']
    need(lineage['arch'] == pins.native_arch and lineage['schema'] == 1 and src['gecko_commit'] == GECKO
         and src['gecko_tree'] == GECKO_TREE and sha(patch) == PATCH, 'wrong native Gecko source/patch')
    same(src['patch'], bytes_record(patch), 'native build patch hash/length')
    same(src['effective_diff'], bytes_record(actualdiff), 'native patched source diff hash/length')
    same(lineage['upstream_build_id'], dict(baseline=pins.build, candidate=pins.build, reused_upstream_stamp=True), 'upstream stamp')
    baseline_b, native_b, independent_b = (e.raw('kernel/' + n) for n in ('baseline.json', 'build.json', 'readback.json'))
    baseline, native, independent = map(object_at, (baseline_b, native_b, independent_b))
    same(lineage['package']['native_receipt'], bytes_record(native_b), 'build receipt digest')
    same(lineage['package']['independent_receipt'], bytes_record(independent_b), 'independent package receipt digest')
    same(independent['independent_reference'], bytes_record(native_b), 'independent package references another build')
    for rec in (baseline, native, independent):
        same(rec['arch'], pins.native_arch, 'foreign architecture in package chain')
        same(rec['metadata'], dict(source_stamp=GECKO, upstream_build_id=pins.build, version=VERSION), 'mixed source stamp')
        need(len(rec['members']) == 56, 'native package member count')
    same(native['stage_checked'], True, 'unverified staging substitution')
    same(native['members'], independent['members'], 'independent binary package member mismatch')
    same(native['archive'], dict(bytes=pins.kernel_bytes, sha256=pins.kernel), 'wrong kernel archive SHA or size')
    same(independent['archive'], native['archive'], 'independent readback used another kernel archive')
    same({k: lineage['package'][k] for k in ('bytes', 'sha256', 'member_count', 'name')},
         dict(bytes=pins.kernel_bytes, sha256=pins.kernel, member_count=56, name=pins.kernel_name),
         'native lineage package identity')
    a, b = baseline['members'], native['members']
    same(set(a) == set(b), True, 'added or removed package members')
    same(sorted(n for n in a if canonical(a[n]) != canonical(b[n])), ['firefox/libxul.so'], 'native archive delta')
    same(e.obj('kernel/member-delta.json'), dict(same_upstream_stamp=True, added=[], removed=[],
                                                changed=['firefox/libxul.so'], unchanged=55), 'declared package delta')
    linked, packaged = native['relinked_libxul'], native['packaged_libxul']
    same(lineage['libxul']['linked'], linked, 'relink identity')
    same(lineage['libxul']['packaged'], packaged, 'packaged ELF identity')
    same(lineage['libxul']['baseline_packaged'], baseline['packaged_libxul'], 'baseline ELF identity')
    same(independent['packaged_libxul'], packaged, 'independent readback of packaged ELF')
    need(linked['machine'] == packaged['machine'] == pins.machine and linked['elf_build_id'] == packaged['elf_build_id']
         and linked['sha256'] != packaged['sha256'] == pins.libxul
         and linked['elf_build_id'] != baseline['packaged_libxul']['elf_build_id'], 'ELF architecture/relink vs upstream stamp')
    same({k: b['firefox/libxul.so'][k] for k in ('bytes', 'sha256')},
         {k: packaged[k] for k in ('bytes', 'sha256')}, 'packaged ELF is not the archive member')
    same(a['firefox/libxul.so']['sha256'], img['old_package_sha256']['libxul.so'], 'wrong runtime base libxul')
    inv = img['patched_firefox_inventory']
    same(inv['archive_member_count'], len(b), 'wrong installed native inventory count')
    installed_files = {'firefox/' + n: x['sha256'] for n, x in inv['files'].items()}
    native_files = {n: x['sha256'] for n, x in b.items() if x['type'] == 'file'}
    same(installed_files, dict(native_files, **{'firefox/omni.ja': img['package_sha256']['omni.ja']}),
         'runtime native inventory differs beyond the app overlay')
    same(native_files['firefox/omni.ja'], img['pre_overlay_omni_sha256'], 'wrong pre-overlay omni.ja')
    for path in ('firefox', 'browser/omni.ja', 'libxul.so', 'omni.ja'):
        same(installed_files['firefox/' + path], img['package_sha256'][path], 'installed member hash mismatch')
    check_tokens(e.raw('kernel/relinked-elf.txt'), (pins.elf_label, linked['elf_build_id']), 'relinked ELF')
    check_tokens(e.raw('kernel/build.log'), ('toolkit/library/build/libxul.so', 'build finally finished successfully!'), 'build log')
    phases = ('apply_reviewed_patch', 'native_incremental_build', 'upstream_rust_networking_audit', 'package_verified')
    if pins.arch == ARM64.arch:  # The ARM record contains this separate object-only canary.
        phases += ('compile_patched_websocket_objects',)
    check_tokens(e.raw('kernel/phases.log'), phases, 'build phases')
    audit_b = e.raw('kernel/networking-audit.json')
    audit, gk = object_at(audit_b), lineage['gkrust']
    same(gk['upstream_networking_audit'], bytes_record(audit_b), 'upstream audit digest')
    same([audit['exit_code'], audit['archive_audit'], audit['upstream_audit_sources'], audit['archive_stability'],
          audit['pin'], audit['generated_source_stamp'], audit['generated_build_id'], audit['arch'], audit['core_backend'],
          audit['sandbox'], audit['wasm_sandbox'], gk['candidate_sha256']],
         [0, 'passed', 'match', 'sha256-before-after-v1', GECKO, GECKO, pins.build, pins.native_arch, True, True, True,
          audit['sha256']], 'upstream networking audit continuity or result')
    match(gk['baseline_sha256'], r'[a-f0-9]{64}', 'invalid Rust baseline digest')
    if pins.arch == ARM64.arch:
        same(gk['baseline_sha256'], gk['candidate_sha256'], 'frozen ARM Rust archive continuity')
    check_tokens(e.raw('kernel/native-work.sh'), ('upstream_rust_networking_audit', 'check_binary --networking'), 'audit invocation')
    return packaged['elf_build_id']


def validate_v2_sources(e):
    patch = e.raw('kernel/gecko-v2.patch')
    signature = (b'+  [must_use] void onFrame(in nsIChannel aChannel, in unsigned long aSerial,\n'
                 b'+                         in boolean aOutgoing, in unsigned short aOpcode,\n'
                 b'+                         in boolean aFin, in unsigned long aLength);')
    need(patch.count(signature) == 1, 'native length-only listener ABI changed')
    for raw in (patch, e.raw('kernel/effective.diff')):
        check_tokens(raw, ('nsIRuyiWebSocketFrameListener', 'stopRuyiMetadataListener(',
                           'mFailures + mPendingCallbacks + mPendingSends', 'mActive = false;',
                           '++mPendingCallbacks;', '++mPendingSends;', 'aLimit = mLimit;',
                           'kRuyiMaxLength = 65536;', 'kRuyiMaxFrames = 128;', 'kRuyiMaxConnections = 8;',
                           'kRuyiMaxStats = 65535;', 'nsIOService::UseSocketProcess()',
                           'RegisterRuyiChannel(', 'GetInnerWindowID()', 'loading->Equals(triggering)',
                           'Preserve the original wire framing'), 'Gecko V2 API/budget/scope')
    net = e.raw('source/net/Network.sys.mjs')
    check_tokens(net, ('onFrame(subject, serial, outgoing, opcode, fin, length)',
                       'direction: outgoing ? "tx" : "rx", opcode, fin, length',
                       'service.stopRuyiMetadataListener(wgp.innerWindowId, listener, nativeLimit, nativeFailures)',
                       'limit + nativeLimit.value', 'failures + nativeFailures.value', 'NS_RUYI_UNSUPPORTED',
                       'MAX_CONNECTIONS = 8;', 'MAX_FRAMES = 128;', 'MAX_LENGTH = 65536;', 'MAX_STATS = 0xffff;'),
                 'overlay bridge')
    check_tokens(e.raw('source/Policy.sys.mjs'), ('LIMIT = 4096;',), 'strict writer budget')
    check_tokens(e.raw('source/Start.sys.mjs'), ('this.writer.drops.limit + network.limit',
                 'this.writer.drops.protocol + network.failures', 'reply.sent !== this.childSeen', 'this.seal("ok")'),
                 'native limit/pending → writer seal')
    check_tokens(e.raw('source/Writer.sys.mjs'), ('status === "ok" && Object.values(this.drops).every(n => n === 0)',
                 'this.count("io")', 'length > 256', 'Services.io.socketProcessLaunched',
                 '"network.http.network_access_on_socket_process.enabled"', '"MOZ_FORCE_USE_SOCKET_PROCESS"'), 'writer completeness')


def read_criteria(e):
    raw = e.raw('scope/qa-snapshot.tar')
    need(sha(raw) == FIXTURE, 'wrong immutable fixture')
    expected = ['contract/criteria.json', 'contract/intake.py', 'qa/fixture.py', 'qa/run_case.py', 'qa/target.js']
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as arc:
        same(arc.getnames(), expected, 'unexpected fixture archive members')
        need(all(x.isfile() and 0 < x.size <= 100000 for x in arc.getmembers()), 'nonregular fixture member')
        files = {n: arc.extractfile(n).read() for n in expected}
    need(sha(files['qa/target.js']) == SCRIPT, 'wrong fixture target script source')
    for name, locus, digest in (('add', 7, 'f2f415504deccd0e'), ('trap', 8, '14de952378bf4340')):
        line = files['qa/target.js'].decode('ascii').splitlines()[locus]
        m = re.fullmatch(rf"  const {name}Hex = '([0-9a-f]+)';", line)
        need(m is not None and hashlib.sha1(bytes.fromhex(m[1])).hexdigest()[:16] == digest, 'wasm module/config locus')
    return object_at(files['contract/criteria.json'])


def rows_of(raw):
    need(raw.endswith(b'\n') and b'\r' not in raw and len(raw) <= 131072, 'writer has no final line boundary')
    out = [object_at(line) for line in raw[:-1].split(b'\n')]
    need(len(out) <= 4097 and all(len(line) <= 256 for line in raw[:-1].split(b'\n')), 'writer row/byte budget')
    return out


def scope_ids(header, gate, enabled):
    ids = {k: header[k] for k in IDS}
    same(header, dict(ids, state='header'), 'writer header schema')
    match(ids['runId'], '[a-f0-9]{32}', 'run identity')
    match(ids['origin'], r'http://127\.0\.0\.1:[1-9][0-9]{3,4}', 'literally authorized local origin')
    need(1024 <= int(ids['origin'].rsplit(':', 1)[1]) <= 65535, 'scope port range')
    same([ids[k] for k in ('schema', 'mode', 'enabled', 'documentPath')], [1, gate, enabled, '/harness'], 'writer scope')
    need(all(type(ids[k]) is int and ids[k] > 0 for k in IDS[-4:])
         and ids['writerPid'] > 1 and ids['writerPid'] != ids['contentPid'], 'writer/content/window identity')
    return ids


def validate_seal(ids, ready, armed, seal, gate, count):
    same(ready, dict(ids, state='ready'), 'ready writer identity')
    same(armed, dict(ids, state='armed'), 'armed writer identity')
    child = count if gate in {'jscall', 'wasm'} else 0
    same(seal, dict(ids, state='sealed', complete=True, status='ok', accepted=count,
                    drops=DROPS, childSent=child, childSeen=child,
                    **({'nativeTransport': TRANSPORT} if gate == 'websocket' else {})),
         'incomplete, unsupported, native pending/protocol, limit/IO drop, drain, or transport mismatch')


def project(gate, case, rows):
    wanted = CASES[gate][case]
    if gate == 'websocket':
        exp = [dict(family=gate, kind='frame', connection=conn, direction=direction, opcode=op,
                    fin=bool(fin), length=length, seq=i) for i, (conn, direction, op, fin, length) in enumerate(wanted, 1)]
    elif gate == 'http':
        exp = [dict(family=gate, kind='transaction', chain=chain, transport=transport,
                    method=method, status=status, seq=i) for i, (chain, transport, method, status) in enumerate(wanted, 1)]
    else:
        exp = [dict(family=gate, call=n, kind=k, seq=i, functionKind='js' if gate == 'jscall' else 'wasm',
                    **({'moduleId': 1, 'functionIndex': 0} if gate == 'wasm' else {}))
               for i, (n, k) in enumerate(wanted, 1)]
    same(rows, exp, 'native frame order, row allowlist or regression boundaries failed')
    return wanted


def validate_scope(e, key, fields, ids, host, run, gate, case):
    prefix = f'scope/{key}'
    conf_b, ctrl_b = (e.raw(f'{prefix}/{n}') for n in ('native-config.json', 'controls.json'))
    same(fields, dict(config_sha256=sha(conf_b), controls_sha256=sha(ctrl_b)), 'scope original bytes')
    conf = {k: ids[k] for k in ('schema', 'runId', 'origin', 'mode', 'enabled')}
    conf['profile'] = '/runs/case/native/profile'
    if gate == 'websocket':
        conf['websocketPath'] = '/qa-ws'
    if gate == 'http':
        conf['httpPath'] = {'cache_hit': '/qa-cache', 'redirect': '/qa-redirect'}.get(case, '/qa-http')
    if gate == 'jscall':
        conf.update(scriptPath='/target.js', functionName='fixedAdd', jsStartLine=13, jsStartColumn=20)
    if gate == 'wasm':
        trap = case == 'trap'
        conf.update(scriptPath='/target.js', functionName='trap' if trap else 'add', wasmCompileLine=31,
                    wasmEntryOffset=33 if trap else 35, wasmFunctionIndex=0,
                    wasmModuleHash='14de952378bf4340' if trap else 'f2f415504deccd0e')
    same(object_at(conf_b), conf, 'authorized exact loopback route, fixture, mode, or scope mismatch')
    same(run['scope_sha256'], sha(ids['origin'].encode('ascii')), 'origin hash joined to a different scope')
    files = {'native-config.json': dict(mode='0o600', **bytes_record(conf_b))}
    for n, mode in (('native-start', '0o600'), ('native-stop', '0o600'), ('native-writer.lock', '0o400')):
        files[n] = dict(mode=mode, **bytes_record(b''))
    same(object_at(ctrl_b), dict(attempt=host['attempt'], run_id=ids['runId'], files=files,
                                native_root_members=ROOT_MEMBERS), 'wrong marker or extra native output (including .pending)')


def verify_peer(peer, common, rid, role, spec, projected):
    g, c = common['gate'], common['case']
    tx, rx, measured, before, upgrades = [], [], [], [], 0
    if g == 'websocket':
        tx, rx = ([], []) if c == 'skip' else (CLOSE, CLOSE) if c == 'upgrade_only' else (TX, RX)
        upgrades = int(c != 'skip')
        if projected:
            same([[x[2:] for x in projected if x[1] == d] for d in ('tx', 'rx')], [tx, rx],
                 'native per-direction transcript differs from raw peer frame observer')
        metrics = {
            'fragment_and_ping': dict(upgrade_101=upgrades, client_to_server=tx, server_to_client=rx),
            'upgrade_only': dict(upgrade_101=upgrades, data_frames=0, close_each_way=1),
            'skip': dict(upgrade_101=upgrades, frames=len(tx + rx)),
            'disabled': dict(upgrade_101=upgrades, data_tx_plus_rx=sum(f[0] < 8 for f in tx + rx)),
            'other_origin': dict(other_upgrade_101=upgrades),
        }[c]
    elif g == 'http':
        if c in {'fetch', 'disabled', 'other_origin'}:
            measured = [['/qa-http', 200]]
        elif c == 'redirect':
            measured = [['/qa-redirect', 302], ['/qa-final', 200]]
        elif c == 'cache_hit':
            before = [['/qa-cache', 200]]
        metrics = {'redirect': dict(statuses=[x[1] for x in measured]), 'cache_hit': dict(new_route_gets=len(measured)),
                   'other_origin': dict(other_route_gets=len(measured)), 'skip': dict(route_gets=len(measured))}.get(c)
        if metrics is None:
            metrics = dict(route_gets=len(measured), responses_200=sum(x[1] == 200 for x in measured))
    else:
        metrics = None
    same(metrics, spec.get('peer', spec.get('framePeer')), 'peer metric differs from preregistered design')
    same(peer, dict(common, schema=1, run_id=rid, pre_measure_http=before, measured_http=measured, upgrades_101=upgrades,
                    client_to_server=tx, server_to_client=rx, server_messages=sum(x[0] == 1 for x in tx),
                    metrics=metrics, documents_ready=['other', 'primary'] if role == 'other' else ['primary'],
                    failures=[], measured=True, result_count=1), 'independent peer raw observer/controls differ')
    return metrics


def validate_case(e, gate, case, scope, spec, stock, levels, *, pins=ARM64):
    key = f'{gate}--{case}'
    raw = lambda n: e.raw(f'lane/{key}/{n}')
    obs = [raw(f'native/{n}') for n in ORIGINALS]
    ready, armed, original, sealed = obs
    header, *rows = rows_of(original)
    ids = scope_ids(header, gate, case != 'disabled')
    rid = ids['runId']
    validate_seal(ids, object_at(ready), object_at(armed), object_at(sealed), gate, len(rows))
    out = project(gate, case, rows)
    common = dict(arch=pins.arch, gate=gate, case=case)
    host = object_at(raw('host.json'))
    attempt = host['attempt']
    match(attempt, 'run-[a-f0-9]{20}', 'host attempt ID')
    same(host, dict(common, schema='ruyitrace.gap-host-run.v1', host=pins.host, attempt=attempt,
                    remote='/var/lib/ruyitrace-gap-qa-v1/attempts/' + attempt, code=0, remaining_containers=0,
                    docker_local_socket=True, base=False, image_id=pins.image, snapshot_sha256=FIXTURE,
                    additional_native_event_files=[], rootfs_layers=levels), 'host/image/attempt/output scan mismatch')
    run = object_at(raw('run.json'))
    role = 'other' if case == 'other_origin' else 'primary'
    times = tuple(datetime.fromisoformat(run[n]) for n in ('started_utc', 'finished_utc'))
    need(all(t.tzinfo == timezone.utc and t.date().isoformat() == pins.day for t in times)
         and 0 < (times[1] - times[0]).total_seconds() <= 165, 'candidate measurement time window')
    process = run['writer_process']
    need(type(process['start_ticks']) is int and process['start_ticks'] > 0, 'missing process birth identity')
    same(process, dict(pid=ids['writerPid'], start_ticks=process['start_ticks'], executable='/browser/firefox',
                       libxul_mapped=True, uid=1000, no_new_privs=1, seccomp=2, cap_eff='0000000000000000'),
         'writer OS identity or isolation')
    same(run, dict(common, schema='ruyitrace.native-run.v1', image_id=pins.image, build_id=pins.build, fixture_js_sha256=SCRIPT,
                   writer_process=process, run_id=rid, scope='installed-product-native-observation',
                   scope_sha256=sha(ids['origin'].encode('ascii')), native_metrics=spec['native'], native_status='ok',
                   native_rows=len(out), native_product_pass=True, browser_reaped=True, browser_exit=0,
                   native_files_scan=['native-events.jsonl'], open_public_ports=False, page_origin_control=role,
                   page_witness=True, peer_witness=gate in {'http', 'websocket'}, passed=True,
                   started_utc=run['started_utc'], finished_utc=run['finished_utc']),
         'mixed build, incomplete run or substituted native metrics')
    validate_scope(e, key, scope, ids, host, run, gate, case)
    page_b, peer_b = raw('page.json'), raw('peer.json')
    page = object_at(page_b)
    same(page, dict(common, schema=1, run_id=rid, observation=spec['workload'], ack_role=role), 'page workload witness')
    metrics = verify_peer(object_at(peer_b), common, rid, role, spec, out)
    same([page['observation'], metrics], [stock['page'], stock['peer']], 'stock and final workload drift')
    same(object_at(raw('native-projection.json')), dict(run_id=rid, rows=out, original_sha256=sha(original),
                                                       seal_sha256=sha(sealed)), 'projection lost original SHA custody')
    return dict(rid=rid, attempt=attempt, original=obs, page=page_b, peer=peer_b, out=out, scope=run['scope_sha256'],
                process=process, host=host['host'], times=times, raw_sha256=sha(original), seal_sha256=sha(sealed))


def validate_packet(e, gate, runs, observers, indexed, *, pins=ARM64, producer_intakes=False):
    root = f'intake/{pins.cpu}-{gate}'
    common = dict(arch=pins.arch, gate=gate, source=pins.product, fixture_sha256=FIXTURE, artifact_sha256=pins.archive, build_id=pins.build)
    candidate, seen, cases, total = e.raw(f'{root}/candidate.json'), set(), {}, 0
    roles = ('native', 'workload', *({'websocket': ('framePeer',), 'http': ('peer',)}.get(gate, ())))
    for case, r in runs.items():
        rid, hashes = r['rid'], {}
        for role in roles:
            prefix = f'{root}/cases/{case}/{role}'
            raw, obs = (e.raw(f'{prefix}/{n}') for n in ('source.bin', 'observation.json'))
            exp = dict(common, schema='ruyitrace.proposed-observation.v1', case=case, run_id=rid, observer=observers[role],
                       source_sha256=sha(raw), complete=True, dropped=0, io_errors=0)
            if role == 'native':
                original = b'RUI_NATIVE_ORIGINALS_1\n' + b''.join(struct.pack('>Q', len(x)) + x for x in r['original'])
                same_bytes = e.raw(f'{prefix}/original.bin') == original
                need(same_bytes, 'packet resynthesizes or substitutes the four native originals')
                who = dict(os=r['process'], image=pins.image, host=r['host'], run_id=rid)
                expected = {k: v for k, v in common.items() if k not in {'source', 'build_id'}}
                same(object_at(raw), dict(expected, schema='ruyitrace.proposed-native-projection.v1', case=case,
                                         run_id=rid, original_sha256=sha(original), authorized_scope_sha256=r['scope'],
                                         writer_instance_sha256=sha(canonical(who)), all_run_outputs_scanned=True,
                                         posthoc_origin_exclusion=False, source_members=4, unexpected_fixture_rows=0,
                                         tail_complete=True, dropped=0, io_errors=0, rows=r['out']),
                     'intake native identity/custody/completion')
            else:
                work = role == 'workload'
                need(raw == r['page' if work else 'peer'], 'packet substituted page or peer original bytes')
                exp['metrics'] = object_at(raw)['observation' if work else 'metrics']
            same(object_at(obs), exp, 'intake observer identity or loss status')
            hashes[role] = sha(obs)
            need(hashes[role] not in seen, 'duplicate observer receipt')
            seen.add(hashes[role])
            total += 1
        cases[case] = dict(run_id=rid, observers=hashes)
    same(object_at(candidate), dict(common, schema='ruyitrace.proposed-candidate.v1', collection_kind='product-run', cases=cases),
         'intake candidate drift')
    outcome = e.obj(f'{root}/intake-result.json')
    same(outcome, dict(arch=pins.arch, cases=len(runs), gate=gate, observations=total, product_qualified=False,
                       status='eligible_for_manual_review',
                       reason='package authenticity, origin attribution, independent collector and human witness still require review'),
         'intake exceeds structural review ceiling')
    if not producer_intakes:
        same(indexed, dict(candidate_sha256=sha(candidate), intake=outcome), 'intake packet index mismatch')
    return total


def stock_controls(e, criteria, *, pins=ARM64):
    stock = e.obj('controls/stock-workload.json')
    same([stock[k] for k in ('schema', 'arch', 'source_image', 'firefox_build_id', 'page_source_sha256',
                             'passed_workload_cases', 'passed_new_product_sinks')],
         ['ruyitrace.native-event-control-set.v1', pins.arch, pins.base, pins.build, SCRIPT, 22, 0], 'wrong stock workload-only control')
    pairs = {(x['gate'], x['case']): x for x in stock['cases']}
    need(len(stock['cases']) == len(pairs) == 22 and {f'{g}--{c}' for g, c in pairs} == CELLS, 'stock workload case set')
    run_ids = set()
    for (g, c), r in pairs.items():
        spec = criteria['gates'][g]['cases'][c]
        rid = r['run_id']
        match(rid, '[a-f0-9]{32}', 'stock run identity')
        need(rid not in run_ids, 'duplicate stock run identity')
        run_ids.add(rid)
        same([r['writer_observed'], r['browser_exit'], r['source_role'], r['page'], r['peer']],
             [False, -15, 'other' if c == 'other_origin' else 'primary', spec['workload'],
              spec.get('peer', spec.get('framePeer'))], 'stock result has product credit or wrong workload')
    return pairs, run_ids


def stock_unsupported(e, *, pins=ARM64):
    raw = rows_of(e.raw('controls/unsupported/native-events.jsonl'))
    need(len(raw) == 1, 'historical unsupported stock writer output includes rows')
    ids = {k: raw[0][k] for k in IDS if k != 'documentPath'}
    match(ids['runId'], '[a-f0-9]{32}', 'stock unsupported run identity')
    same([ids['mode'], ids['enabled']], ['websocket', True], 'stock unsupported must actually request WS producer')
    ready = e.obj('controls/unsupported/native-ready.json')
    seal = e.obj('controls/unsupported/native-sealed.json')
    same(raw[0], dict(ids, state='header'), 'historical writer header')
    same(ready, dict(ids, state='ready'), 'historical ready')
    same(seal, dict(ids, state='sealed', status='unsupported', complete=False, accepted=0, drops=DROPS,
                    childSent=None, childSeen=0), 'stock unsupported is not a sealed zero')
    same(e.obj('controls/unsupported/smoke.json'), dict(image=pins.stock_overlay, scope='blank enabled smoke', peer=None,
         browser_exit=0, ready=ready, armed=None, sealed=seal, raw=raw), 'wrong historical unsupported run')
    return ids['runId']


def verify(blobs, *, pins=ARM64, producer_intakes=False):
    e = Evidence(blobs)
    levels, img = validate_release(e, pins=pins)
    elf = validate_kernel(e, img, pins=pins)
    validate_v2_sources(e)
    criteria = read_criteria(e)
    stock, run_ids = stock_controls(e, criteria, pins=pins)
    stock_run = stock_unsupported(e, pins=pins)
    need(stock_run not in run_ids, 'stock witnesses reused run identity')
    run_ids.add(stock_run)
    scope = e.obj('scope/index.json')
    same(scope, dict(platform=pins.arch, schema='ruyitrace.authorized-scope-readback.v2', qa_snapshot_sha256=FIXTURE,
                     scopes=scope['scopes']), 'scope readback index')
    same(sorted(scope['scopes']), sorted(CELLS), 'scope readback case set')
    intake = {} if producer_intakes else e.obj('intake/index.json')
    if not producer_intakes:
        same(sorted(intake), sorted(f'{pins.cpu}-{g}' for g in CASES), 'intake gate set')
    summary = e.obj('lane/summary.json')
    by_key = {(x['gate'], x['case']): x for x in summary['observations']}
    need(len(by_key) == len(summary['observations']) == 22 and {f'{g}--{c}' for g, c in by_key} == CELLS, 'lane case set')
    same(summary, dict(arch=pins.arch, schema='ruyitrace.gap-lane.v1', stock_control=False, image_id=pins.image, snapshot=FIXTURE,
                       completed=22, requested=22, passed=True, observations=summary['observations']), 'whole lane receipt')
    intervals, attempts, results = [], set(), {}
    for gate, cases in CASES.items():
        specs = criteria['gates'][gate]['cases']
        same(sorted(specs), sorted(cases), 'preregistered case set')
        runs = {}
        for case in cases:
            try:
                key = f'{gate}--{case}'
                r = validate_case(e, gate, case, scope['scopes'][key], specs[case], stock[(gate, case)], levels, pins=pins)
                need(r['rid'] not in run_ids and r['attempt'] not in attempts, 'duplicate or historical run identity')
                run_ids.add(r['rid'])
                attempts.add(r['attempt'])
                intervals.append(r['times'])
                same(by_key[(gate, case)], dict(attempt=r['attempt'], gate=gate, case=case, issue=None,
                     passed=True, native_rows=len(r['out']), scope='installed-product-native-observation'), 'lane summary row')
                runs[case] = r
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(f'{gate}/{case}: {exc}') from exc
        total = validate_packet(e, gate, runs, criteria['observer_sources'], intake.get(f'{pins.cpu}-{gate}'),
                                pins=pins, producer_intakes=producer_intakes)
        results[gate] = dict(cases=len(runs), packet_observations=total, native_rows=sum(len(r['out']) for r in runs.values()),
                             originals={c: dict(run_id=r['rid'], original_sha256=r['raw_sha256'], seal_sha256=r['seal_sha256'],
                                                rows=len(r['out'])) for c, r in sorted(runs.items())})
    intervals.sort()
    need(all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:])), 'overlapping case attempts')
    e.end()
    return dict(schema='ruyitrace.patched-websocket-offline-review.v1', status='qualified', platform=pins.arch,
                scope='native installed image, approved loopback synthetic QA only', build_id=pins.build,
                runtime_source=pins.product, source_set_sha256=pins.source_set, gecko_source=GECKO, patch_sha256=PATCH,
                browser_image_id=pins.image, operator_archive_sha256=pins.archive, operator_archive_bytes=pins.archive_bytes,
                firefox_archive_sha256=pins.kernel, firefox_archive_bytes=pins.kernel_bytes, libxul_sha256=pins.libxul,
                libxul_elf_build_id=elf, accepted_cases=22, regression_cases_on_new_bytes=17,
                historical_stock_websocket='unsupported-not-zero', native_transport=TRANSPORT,
                websocket_positive=dict(peer_client_to_server=TX, peer_server_to_client=RX, native_order=WS_ORDER,
                                        application_received_message_lengths=[5, 8], scope_local_connections=1),
                gates=results)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', type=Path, default=HERE / 'arm64-originals.zip')
    parser.add_argument('--kernel-tar', type=Path, help='also rehash the full native Firefox TAR.XZ and every member')
    parser.add_argument('--operator-tar', type=Path, help='also rehash the full Docker TAR.GZ, config and image layers')
    parser.add_argument('--artifact-report', action='store_true', help='emit separate full-byte receipt (requires both TARs)')
    args = parser.parse_args(argv)
    if args.artifact_report and not (args.kernel_tar and args.operator_tar):
        parser.error('--artifact-report requires both --kernel-tar and --operator-tar')
    try:
        blobs = load_zip(args.zip)
        verdict = verify(blobs)
        kernel = object_at(blobs['kernel/readback.json'])
        if args.kernel_tar:
            read_kernel_archive(args.kernel_tar, kernel)
        if args.operator_tar:
            operator = read_operator_archive(args.operator_tar, object_at(blobs['export/archive-proof.json']))
        if args.artifact_report:
            verdict = dict(schema='ruyitrace.patched-websocket-full-byte-review.v1', platform=ARCH, passed=True,
                           evidence_index_sha256=INDEX_SHA, installed_archive_proof_sha256=ARCHIVE_PROOF,
                           native_firefox=dict(kernel['archive'], checked_members=len(kernel['members']),
                                               **kernel['metadata'], elf=kernel['packaged_libxul']), operator=operator)
    except (ValueError, KeyError, OSError, EOFError, TypeError, tarfile.TarError, zipfile.BadZipFile) as exc:
        parser.exit(1, f'qualification failed: {exc}\n')
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
