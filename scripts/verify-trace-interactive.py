#!/usr/bin/env python3
"""Verify offline interactive-image evidence against the immutable image source tag."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile

import yaml

ROOT = Path(__file__).resolve().parent.parent
TRACE = ROOT / 'submodules/ruyitrace'
IMAGE_SOURCE = {
    'branch': 'main',
    'commit': '9f8dbb9bbbd322c2e6a17b05b89fd23690067f2c',
    'repository': 'Facetomyself/ruyitrace',
    'tag': 'product/interactive-r5-cli2-v1-amd64',
}
RECORD = 'artifacts/receipts/trace-interactive-r5/interactive-image.json'
SMOKE = 'empty-engine-final.json'
HOST = 'empty-engine-final-host185.json'
EVIDENCE = {
    SMOKE, HOST, 'acceptance.json', 'product-readback.json', 'release-export.json',
    'local-view.json', 'operator-release.json', 'resource-measurements.json', 'transport-release.json',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(content):
    return hashlib.sha256(content).hexdigest()


def object_pairs(pairs):
    result = {}
    for key, val in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = val
    return result


def load(content):
    value = json.loads(content, object_pairs_hook=object_pairs)
    require(isinstance(value, dict), 'expected JSON object')
    return value


def git(*args):
    return subprocess.check_output(['git', '-C', str(TRACE), *args], stderr=subprocess.DEVNULL)


def tagged_file(path):
    return git('show', f'{IMAGE_SOURCE["commit"]}:product/interactive/{path}')


def check_archive(path, data, export):
    """When supplied, check the on-disk gzip and its actual Docker-save manifest/config."""
    expected = data['archive']
    with path.open('rb') as stream:
        h = hashlib.sha256()
        size = 0
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            size += len(block)
            require(size <= expected['bytes'], 'on-disk archive byte count')
            h.update(block)
        require(size == expected['bytes'] and h.hexdigest() == expected['sha256'], 'on-disk archive bytes/SHA-256')
        stream.seek(0)
        with tarfile.open(fileobj=stream, mode='r:gz') as saved:
            def member(name, limit):
                info = saved.getmember(name)
                require(info.isfile() and info.size <= limit, 'Docker-save manifest/config member shape')
                with saved.extractfile(info) as f:
                    return f.read()

            manifest = json.loads(member('manifest.json', 65536), object_pairs_hook=object_pairs)
            require(isinstance(manifest, list) and len(manifest) == 1, 'Docker-save single-image manifest')
            entry = manifest[0]
            require(entry['RepoTags'] == [data['name']], 'Docker-save repository tag')
            config = member(entry['Config'], 1024 * 1024)
            require('sha256:' + digest(config) == data['image_id'], 'Docker-save image config digest')
            cfg = load(config)
            require(cfg['os'] + '/' + cfg['architecture'] == data['platform'], 'Docker-save platform')
            require(cfg['config']['Labels']['io.ruyitrace.interactive.parent'] == data['parent_image_id'], 'Docker-save parent image label')
            require(cfg['rootfs']['diff_ids'] == [layer['diff_id'] for layer in export['layers']]
                    and len(entry['Layers']) == len(export['layers']), 'Docker-save layer graph / export receipt')


def verify(path, archive_path=None):
    data = load(path.read_bytes())
    require(data['schema'] == 'ruyitrace-interactive-image.v1' and data['platform'] == 'linux/amd64', 'platform record schema and platform')
    require(data['source'] == IMAGE_SOURCE, 'immutable image source commit/tag (not a later Trace source pin)')
    # Fresh submodule checkouts may omit local tags. The canonical commit is fixed above;
    # a present local tag must still resolve to that exact commit.
    tag = f'refs/tags/{IMAGE_SOURCE["tag"]}'
    if subprocess.run(['git', '-C', str(TRACE), 'show-ref', '--quiet', '--verify', tag], check=False).returncode == 0:
        require(git('rev-parse', f'{tag}^{{commit}}').decode().strip() == IMAGE_SOURCE['commit'], 'local image tag moved from pinned commit')
    git('merge-base', '--is-ancestor', IMAGE_SOURCE['commit'], 'HEAD')
    lock = load(tagged_file('release-lock.json'))
    archive = data['archive']
    require(type(archive['bytes']) is int and archive['bytes'] > 0 and re.fullmatch(r'[0-9a-f]{64}', archive['sha256']), 'platform archive size/SHA-256 shape')
    require(re.fullmatch(r'sha256:[0-9a-f]{64}', data['image_id']), 'platform image ID shape')
    require(lock['schema'] == 2 and data['image_id'] == lock['image_id'] and archive == lock['archive'], 'platform image ID/archive SHA-256/bytes vs image-tagged release lock')
    for key in ('name', 'platform', 'firefox_build_id', 'added_image_bytes'):
        require(data[key] == lock[key], f'platform {key} vs image-tagged release lock')
    require(data['parent_image_id'] == lock['parent_image'], 'parent image vs image-tagged release lock')

    require(set(data['evidence_sha256']) == EVIDENCE, 'exact set of current raw receipts')
    evidence = {}
    raw = {}
    for name in sorted(EVIDENCE):
        receipt = path.parent / name
        require(receipt.is_file() and not receipt.is_symlink(), f'{name}: expected regular receipt')
        raw[name] = receipt.read_bytes()
        require(digest(raw[name]) == data['evidence_sha256'][name], f'{name}: raw SHA-256 mismatch')
        evidence[name] = load(raw[name])
    require(raw['acceptance.json'] == tagged_file('qa/acceptance-native.json'), 'native acceptance bytes vs image-tagged source')

    smoke = evidence[SMOKE]
    require(smoke['image_id'] == data['image_id'] and smoke['archive_sha256'] == archive['sha256'], 'raw empty-engine image ID/archive SHA-256 vs official release (candidate receipts are not valid)')
    require(smoke['scope'] == 'isolated fresh engine, same physical amd64 host'
            and all(smoke[k] is True for k in ('passed', 'loaded_tag', 'headed_owner_ready'))
            and smoke['additional_parent_config'] is False and smoke['viewer_uds_http'] == 200
            and all(type(smoke[k]) is int and smoke[k] == 0 for k in ('initial_images', 'stop_exit', 'extra_binary_or_QA_mounts')),
            'raw empty-engine smoke verdict')
    host = evidence[HOST]
    require(host['image_id'] == smoke['image_id'] and host['archive_sha256'] == smoke['archive_sha256']
            and type(host['archive_bytes']) is int and host['archive_bytes'] == archive['bytes'], 'raw host image ID/archive SHA-256/byte count vs empty-engine proof and official release')
    require(host['schema'] == 'ruyitrace-interactive-empty-engine-host.v1' and host['host'] == 'host185'
            and host['platform'] == data['platform'] and host['private_namespaces'] == ['mount', 'net', 'pid']
            and host['public_ingress_used'] is False and all(host[k] is True for k in ('passed', 'main_docker_unchanged', 'host_tcp_listeners_unchanged')),
            'raw host isolation/daemon/listener verdict')
    require(host['smoke_script_sha256'] == digest(tagged_file('qa/empty-engine.sh')), 'raw host smoke script vs image-tagged QA script')
    require(data['empty_engine_load'] == {
        'additional_parent_config': smoke['additional_parent_config'], 'archive_bytes': host['archive_bytes'],
        'archive_sha256': smoke['archive_sha256'], 'extra_binary_or_qa_mounts': smoke['extra_binary_or_QA_mounts'],
        'image_id': smoke['image_id'], 'initial_images': smoke['initial_images'], 'passed': smoke['passed'],
        'viewer_uds_http': smoke['viewer_uds_http'],
    }, 'empty-engine release summary vs raw observations')
    require(lock['verification']['empty_engine_load'] is True and lock['verification']['second_physical_host_tested'] is False,
            'image-tagged lock empty-engine claims')

    export = evidence['release-export.json']
    require(export['passed'] is True and export['image_id'] == data['image_id'] and export['archive_sha256'] == archive['sha256']
            and type(export['archive_bytes']) is int and export['archive_bytes'] == archive['bytes'] and export['name'] == archive['name']
            and export['tag'] == data['name'] and export['parent_image_id'] == data['parent_image_id']
            and export['added_image_bytes'] == data['added_image_bytes'] and export['platform'] == data['platform'], 'export receipt release identity')
    manifest = evidence['product-readback.json']
    require(manifest['passed'] is True and manifest['platform'] == data['platform'] and manifest['public_tcp_ports'] == 0
            and manifest['manifest_sha256'] == lock['layer_manifest_sha256'], 'installed layer-manifest readback vs image-tagged release lock')
    native = evidence['acceptance.json']
    a = data['acceptance']
    trace = native['native_after_stop']['trace']
    identity = native['identity_before_disconnect']
    require(native['passed'] is True and native['image_id'] == data['image_id'] and identity['build_id'] == data['firefox_build_id']
            and native['identity_first_connected'] == identity == native['identity_after_reconnect'] and a['reconnect_same_owner'] is True,
            'native acceptance image/build/reconnect identity')
    require(a['native'] is True and trace['native_start_observed'] is True and trace['native_stop_observed'] is True
            and a['exclusive_single_viewer'] == native['interaction']['second_client_rejected'] == 'after-valid-vncauth-submission'
            and a['no_published_ports'] is True and native['no_container_published_ports'] is True
            and a['page_receipt_after_reconnect'] is True and a['page_receipt'] == native['page_final']['acks'][-1]
            == {'clicks': 3, 'drops': 1, 'sliderOK': True, 'submits': 1, 'textOK': True, 'titleOK': True}, 'native acceptance viewer and page outcome')
    require(a['native_clicks'] == trace['fixture_native_clicks'] == 1
            and a['closed_window_markers'] == trace['closed_title_markers'] == 0
            and a['non_click_events'] == trace['non_click_event_rows'] == 0
            and all(a[k] == trace[k] for k in ('session', 'window_id', 'writer_pid'))
            and a['cli_gate'] == {'on': native['capture_on']['observed'], 'off': native['capture_off']['observed'], 'marker': native['capture_off']['marker']}
            == {'on': 'open', 'off': 'closed', 'marker': 'withdrawn'}, 'native acceptance trace and gate counts')
    t = data['transport']
    tr = evidence['transport-release.json']
    require(tr['passed'] is True and t['ssh_loopback_tcp_forward'] is True and tr['regular_authorized_ssh_tcp_forward'] is True
            and t['websocket_upgrade'] == tr['websocket_upgrade'] == 101
            and t['raw_viewer_published'] is False and tr['raw_viewer_published'] is False
            and t['sshd_modified'] is False and tr['sshd_or_firewall_modified'] is False, 'private transport receipt')
    op = evidence['operator-release.json']
    require(op['passed'] is True and all(data['operator'][k] is True and op[k] is True for k in
            ('start', 'status', 'arm', 'on', 'off', 'stop', 'non_tty_code_refused'))
            and data['operator']['profile_outside_output_mount'] is True and op['host_profile_absent'] is True, 'operator receipt')
    require(evidence['local-view.json']['passed'] is True, 'local viewer receipt')
    require(evidence['resource-measurements.json']['interactive_image_id'] == data['image_id'], 'resource receipt image identity')
    require(set(data['limits']) == {'arm', 'keystroke_or_trajectory_persistence', 'os_ime_candidate_flow',
                                  'physical_keyboard_or_trackpad', 'recording', 'second_physical_host'}
            and all(value is False for value in data['limits'].values()), 'declared limits')
    if archive_path is not None:
        check_archive(archive_path, data, export)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='also verify the supplied local gzip bytes and Docker-save manifest')
    args = parser.parse_args()
    try:
        status = yaml.safe_load((ROOT / 'STATUS.yaml').read_text(encoding='utf-8'))['projects']['ruyitrace']
        require(status['interactive_image'] == RECORD, 'unexpected platform receipt path in STATUS.yaml')
        data = verify(ROOT / RECORD, args.archive)
    except subprocess.CalledProcessError:
        print('FAIL  interactive image source commit/file unavailable or outside Trace checkout ancestry', file=sys.stderr)
        return 1
    except (KeyError, TypeError, ValueError, OSError, tarfile.TarError) as exc:
        print(f'FAIL  interactive image: {exc}', file=sys.stderr)
        return 1
    print(f'PASS  interactive image {data["image_id"]}, archive {data["archive"]["bytes"]} bytes; raw evidence and tagged lock agree')
    if args.archive is not None:
        print('PASS  local archive SHA-256, byte count, Docker-save manifest and image config')
    return 0


if __name__ == '__main__':
    sys.exit(main())
