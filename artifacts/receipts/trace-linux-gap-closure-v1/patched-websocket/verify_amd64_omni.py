#!/usr/bin/env python3
"""Prove the exact AMD64 pre-overlay omni.ja build-information-only delta."""

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import struct
import tarfile
import zipfile
import zlib

import verify as common

BASE_IMAGE = 'sha256:eb73d165ea9adc15864aeb054bc90a78670618c5c0606827997d357f1cae05c6'
BASE_DOCKER = '8f08567095d752cea64d121a759433eee5c1eb694a10d3e4fe495f058c2b1cd7'
BASE_DOCKER_BYTES = 379999761
BASE_LAYER = 'blobs/sha256/986a00917d0a1bbdc30a2f408f9313928344b2611cfe217ba1197d7e1a7fed2a'
CANDIDATE_KERNEL = '25017b78ddd69c0beaac895b93a26ab8d0fcbb597ad5add20a5ae0e1ad2f9982'
CANDIDATE_KERNEL_BYTES = 81716568
BASE_OMNI = dict(bytes=48049483, sha256='1167a101f5e50332a767a3dcdcec4f7acbb7242c25d3613a760fd0f3caab61c7')
CANDIDATE_OMNI = dict(bytes=48049519, sha256='a6767fac0cda262c6c5f1675d73cc1727a48f1d88079b8eb707e4828eac52575')
HTML = 'chrome/toolkit/content/global/buildconfig.html'
TOKEN = b' MOZBUILD_STATE_PATH=/root/.mozbuild'
ANCHOR = b'<p>--enable-application=browser'
BASE_BUILD_CONFIG = dict(bytes=2522, sha256='bb5f0de9d13643a0d63f5c420a231186622e34e739b83cf2ca062cf12b94fbce')
NEW_BUILD_CONFIG = dict(bytes=2558, sha256='4c240e5f65f69efb1fc36c32ea8cb2033f80d7c382ddcaf6bf4d3cbf2f0e355e')
ACTOR = 'modules/ActorManagerParent.sys.mjs'
ACTOR_ANCHOR = b'ActorManagerParent.addJSWindowActors(JSWINDOWACTORS);'
ACTOR_HOOK = b'''
// RuyiTrace local opt-in only; packaged in this normal Gecko parent startup module.
if (Services.env.get("MOZ_RUYITRACE_NATIVE_DIR")) {
  try {
    ChromeUtils.importESModule("resource://gre/modules/ruyi-native/Start.sys.mjs").boot();
  } catch (error) {
    Cu.reportError(error);
  }
}
'''
ATTRS = ('orig_filename', 'date_time', 'compress_type', 'flag_bits', 'create_system', 'create_version',
         'extract_version', 'reserved', 'volume', 'internal_attr', 'external_attr', 'extra', 'comment')


def member_index(archive):
    names = archive.namelist()
    common.need(0 < len(names) <= 3000 and len(set(names)) == len(names) and not archive.comment,
                'unexpected ZIP names/comment or duplicate members')
    for i in archive.infolist():
        common.need(i.filename == i.orig_filename and not i.filename.startswith('/') and '\\' not in i.filename
                    and '..' not in i.filename.split('/') and 0 <= i.file_size <= 16 * 1024**2,
                    'unsafe ZIP member or member size')
    return names


def native_omni(path):
    common.need(common.opened(path, CANDIDATE_KERNEL_BYTES) == CANDIDATE_KERNEL, 'wrong AMD native Firefox archive')
    value = None
    with tarfile.open(path, 'r|xz') as archive:
        for member in archive:
            if member.name == 'firefox/omni.ja':
                common.need(value is None and member.isfile() and member.size == CANDIDATE_OMNI['bytes'], 'native omni member shape')
                value = archive.extractfile(member).read()
    common.need(value is not None, 'missing native omni')
    common.same(common.bytes_record(value), CANDIDATE_OMNI, 'wrong native omni bytes')
    return value


def original_release_omni(path):
    """Read the exact R5 CLI2 config/member from the immutable local Docker release."""
    common.need(common.opened(path, BASE_DOCKER_BYTES) == BASE_DOCKER, 'wrong original Docker release')
    cfg, manifest, value = None, None, None
    cfg_path = 'blobs/sha256/' + BASE_IMAGE[7:]
    with tarfile.open(path, 'r|gz') as release:
        for m in release:
            if m.name == cfg_path:
                raw = release.extractfile(m).read()
                common.same('sha256:' + common.sha(raw), BASE_IMAGE, 'wrong R5 config digest')
                cfg = common.object_at(raw)
            elif m.name == 'manifest.json':
                manifest = json.loads(release.extractfile(m).read())
            elif m.name == BASE_LAYER:
                with tarfile.open(fileobj=release.extractfile(m), mode='r|') as layer:
                    for item in layer:
                        if item.name.removeprefix('./') == 'browser/omni.ja':
                            common.need(value is None and item.isfile() and item.size == BASE_OMNI['bytes'], 'baseline root omni shape')
                            value = layer.extractfile(item).read()
    common.need(cfg is not None and type(manifest) is list and len(manifest) == 1 and value is not None,
                'incomplete baseline Docker archive')
    common.same([cfg['os'], cfg['architecture'], manifest[0]['Config'], manifest[0]['RepoTags']],
                ['linux', 'amd64', cfg_path, ['ruyitrace/cli:r5-cli2-amd64']], 'wrong baseline config/tag')
    layers = [f'blobs/sha256/{x.removeprefix("sha256:")}' for x in cfg['rootfs']['diff_ids']]
    common.same(manifest[0]['Layers'], layers, 'wrong original Docker layer order')
    common.need(BASE_LAYER in layers, 'baseline omni layer missing from original image')
    common.same(common.bytes_record(value), BASE_OMNI, 'wrong baseline omni bytes')
    return value


def reconstruct(original, archive, expected_html):
    """Rebuild the AMD64 ZIP byte-for-byte from the only permitted insertion."""
    i = archive.getinfo(HTML)
    old_html = archive.read(i)
    common.need(all(x.flag_bits == 0 and x.compress_type == zipfile.ZIP_STORED for x in archive.infolist())
                and all(len(x.extra) == 0 for x in archive.infolist()), 'unexpected native ZIP encoding')
    start = i.header_offset
    common.need(original[start:start + 4] == b'PK\x03\x04', 'local ZIP header')
    nlen, xlen = struct.unpack_from('<HH', original, start + 26)
    data = start + 30 + nlen + xlen
    common.need(original[data:data + len(old_html)] == old_html and i.compress_size == len(old_html), 'stored member bytes')
    gap = len(expected_html) - len(old_html)
    changed = bytearray(original[:data] + expected_html + original[data + len(old_html):])
    payload_fields = (zlib.crc32(expected_html), len(expected_html), len(expected_html))
    struct.pack_into('<III', changed, start + 14, *payload_fields)
    central = cursor = archive.start_dir + gap
    for entry in archive.infolist():
        common.need(changed[cursor:cursor + 4] == b'PK\x01\x02', 'unexpected central ZIP record')
        namesz, extrasz, commentsz = struct.unpack_from('<HHH', changed, cursor + 28)
        old_rel = struct.unpack_from('<I', changed, cursor + 42)[0]
        common.same(old_rel, entry.header_offset, 'unexpected original ZIP header offset')
        if entry.filename == HTML:
            struct.pack_into('<III', changed, cursor + 16, *payload_fields)
        if old_rel > start:
            struct.pack_into('<I', changed, cursor + 42, old_rel + gap)
        cursor += 46 + namesz + extrasz + commentsz
    common.need(changed[cursor:cursor + 4] == b'PK\x05\x06' and cursor + 22 == len(changed), 'unexpected ZIP end record')
    common.same(struct.unpack_from('<I', changed, cursor + 16)[0], archive.start_dir, 'original central directory offset')
    struct.pack_into('<I', changed, cursor + 16, central)
    return changed


def compare(original, candidate, count=2674):
    with zipfile.ZipFile(io.BytesIO(original)) as base, zipfile.ZipFile(io.BytesIO(candidate)) as patched:
        names = member_index(base)
        common.same(member_index(patched), names, 'native ZIP membership or order differs')
        common.same(len(names), count, 'native ZIP member count')
        delta, unchanged = {}, {}
        for n in names:
            a, b = base.getinfo(n), patched.getinfo(n)
            common.need(all(getattr(a, key) == getattr(b, key) for key in ATTRS), 'native ZIP entry metadata changed')
            x, y = base.read(a), patched.read(b)  # Read all bytes and validate CRC, including any compiled/cache content.
            if x != y:
                delta[n] = dict(original=common.bytes_record(x), candidate=common.bytes_record(y))
            else:
                unchanged[n] = common.bytes_record(x)
        common.same(list(delta), [HTML], 'native ZIP has a loaded member or another build member change')
        old, new = base.read(HTML), patched.read(HTML)
        common.need(old.count(ANCHOR) == 1 and TOKEN not in old and new.count(TOKEN) == 1, 'unexpected configure token position')
        common.need(old.replace(ANCHOR, ANCHOR + TOKEN, 1) == new, 'buildconfig HTML has other content changes')
        common.need(reconstruct(original, base, new) == candidate, 'native ZIP changes go beyond the insertion and corrected ZIP fields')
        return dict(members=count, unchanged=len(unchanged), unchanged_member_index_sha256=common.sha(common.canonical(unchanged)),
                    changed=delta, added=[], removed=[], metadata_unchanged=True, order_unchanged=True,
                    reconstructs_identical_archive=True, inserted_configure_option=TOKEN.decode('ascii').strip(),
                    identical_js_and_mjs=sum(n.endswith(('.js', '.mjs')) for n in unchanged),
                    identical_wasm=sum(n.endswith('.wasm') for n in unchanged))


def checked_review(original, candidate):
    common.same(common.bytes_record(original), BASE_OMNI, 'original root omni identity')
    common.same(common.bytes_record(candidate), CANDIDATE_OMNI, 'native root omni identity')
    z = compare(original, candidate)
    common.same(z['changed'][HTML], dict(original=BASE_BUILD_CONFIG, candidate=NEW_BUILD_CONFIG), 'actual HTML identities')
    return dict(schema='ruyitrace.amd64-native-omni-review.v1', platform='linux/amd64', baseline_image=BASE_IMAGE,
                baseline_root_omni=BASE_OMNI, candidate_kernel=dict(bytes=CANDIDATE_KERNEL_BYTES, sha256=CANDIDATE_KERNEL),
                candidate_root_omni=CANDIDATE_OMNI, zip_review=z)


def operator_omni(path, layer_member, image, package):
    """Read actual Firefox/package bytes from the independently selected Docker overlay."""
    names = {'browser/omni.ja', 'browser/libxul.so', 'opt/ruyitrace-native/package.json', 'browser/.wh..wh..opq'}
    seen = set()
    installed = None
    with tarfile.open(path, 'r|gz') as archive:
        for m in archive:
            if m.name != layer_member:
                continue
            common.need(m.isfile(), 'operator overlay is not a regular layer')
            f = archive.extractfile(m)
            fileobj = gzip.GzipFile(fileobj=f) if f.peek(2).startswith(b'\x1f\x8b') else f
            with tarfile.open(fileobj=fileobj, mode='r|') as layer:
                for item in layer:
                    n = item.name.removeprefix('./')
                    if n not in names:
                        continue
                    common.need(n not in seen and item.isfile(), 'operator file duplicate or type mismatch: ' + n)
                    seen.add(n)
                    with layer.extractfile(item) as p:
                        if n == 'browser/omni.ja':
                            common.need(0 < item.size <= 64 * 1024**2, 'operator root omni size')
                            installed = p.read()
                            common.same(common.sha(installed), image['package_sha256']['omni.ja'], 'operator root omni bytes')
                        elif n == 'browser/libxul.so':
                            h = hashlib.sha256()
                            for data in iter(lambda: p.read(1024**2), b''):
                                h.update(data)
                            common.same(h.hexdigest(), image['package_sha256']['libxul.so'], 'operator installed libxul hash')
                        elif n == 'opt/ruyitrace-native/package.json':
                            common.need(item.size == len(package) and p.read() == package, 'operator installed package bytes')
                        else:
                            common.same(item.size, 0, 'operator Firefox root opaque marker')
            break
    common.need(seen == names and installed is not None, 'operator overlay missing actual Firefox/package bytes')
    return installed


def compare_overlay(native, installed, sources, image):
    """The operator overlay adds seven exact modules and one actor hook, independently of the native packaging delta."""
    with zipfile.ZipFile(io.BytesIO(native)) as a, zipfile.ZipFile(io.BytesIO(installed)) as b:
        old, new = member_index(a), member_index(b)
        modules = {'modules/ruyi-native/' + n: raw for n, raw in sources.items() if n.endswith('.sys.mjs')}
        common.need(len(modules) == 7 and ACTOR in old, 'operator actor and seven-module originals are required')
        common.same(new, old + sorted(modules), 'operator omni membership or order drift')
        for n in old:
            raw = a.read(n)
            if n == ACTOR:
                common.need(raw.count(ACTOR_ANCHOR) == 1 and raw.rstrip().endswith(ACTOR_ANCHOR), 'operator actor anchor')
                common.same(common.sha(raw), image['old_actor_sha256'], 'native actor hash')
                raw += ACTOR_HOOK
                common.same(common.sha(raw), image['actor_sha256'], 'operator actor hash')
            common.need(b.read(n) == raw, 'operator overlay changed an unexpected preexisting member: ' + n)
        for n, raw in modules.items():
            common.need(b.read(n) == raw, 'operator overlay module differs from registered source: ' + n)
        return dict(schema='ruyitrace.amd64-operator-omni-review.v1', platform='linux/amd64', image_id=image['candidate_image_id'],
                    native_root_omni=common.bytes_record(native), operator_root_omni=common.bytes_record(installed),
                    retained_members=len(old) - 1, changed_startup_member=ACTOR, added_source_modules=sorted(modules),
                    retained_buildconfig_sha256=common.sha(b.read(HTML)))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-docker', type=Path, required=True)
    p.add_argument('--kernel-tar', type=Path, required=True)
    args = p.parse_args(argv)
    try:
        result = checked_review(original_release_omni(args.baseline_docker), native_omni(args.kernel_tar))
    except (ValueError, KeyError, OSError, tarfile.TarError, zipfile.BadZipFile, struct.error) as exc:
        p.exit(1, f'AMD native omni review failed: {exc}\n')
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
