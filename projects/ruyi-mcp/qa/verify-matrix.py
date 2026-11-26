#!/usr/bin/env python3
"""Offline consistency checks for the multi-host live owner receipts (does not start a browser)."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import yaml

root=Path(__file__).resolve().parents[3]
folder=root/'artifacts/receipts/mcp-live-matrix-20261126'
load=lambda file: json.loads((folder/file).read_bytes())
sha=lambda file: hashlib.sha256((folder/file).read_bytes()).hexdigest()
idx=load('matrix.json')
ledger=yaml.safe_load((root/'STATUS.yaml').read_bytes())
entry=ledger['projects']['ruyi-mcp']['container']['trace_owner_production']
assert root/entry['current_matrix']==folder/'matrix.json' and sha('matrix.json')==entry['matrix_sha256']
assert idx['schema']=='ruyi-live-matrix.v1' and set(idx['sets'])=={'original','corrected'}
for name,expected in idx['files'].items():
    assert Path(name).name==name and re.fullmatch('[a-f0-9]{64}',expected) and sha(name)==expected,name

def gate(g,n):
    file=g['gates'][n]; assert file in idx['files']; return load(file)

def git(cwd,*args):
    return subprocess.check_output(['git','-C',str(cwd),*args],text=True).strip()

for version,targets in idx['sets'].items():
    assert set(targets)=={'amd64','arm64'}
    manifests,images,sourcepairs=set(),set(),set()
    for arch,g in targets.items():
        assert re.fullmatch('sha256:[a-f0-9]{64}',g['image_id']) and g['image_id']!=g['parent_id']
        assert dict((n,int(c)) for n,c,*_ in g['run_exit_utc'])=={'standard':0,'paused':0,'expiry':0}
        ident=gate(g,'runtime'); assert ident['uid']==1000 and ident['interfaces']==['lo']
        fields=dict(l.split(':',1) for l in ident['isolation']); assert int(fields['CapEff'],16)==0 and int(fields['NoNewPrivs'])==1 and int(fields['Seccomp'])==2
        assert ident['arch']=={'amd64':'x64','arm64':'arm64'}[arch] and ident['firefoxBuild']=={'amd64':'20261123161729','arm64':'20261125162841'}[arch]
        kernel=root/'artifacts/receipts'/({'amd64':'trace-amd64-r5/runtime-identity.json','arm64':'trace-arm64-native-lease/release/kernel-runtime-identity.json'}[arch])
        assert hashlib.sha256(kernel.read_bytes()).hexdigest()==ident['identitySha']
        pins=ident['pins']; assert pins['platform'] == (idx['starting_platform'] if version=='original' else idx['release_basis']); sourcepairs.add((pins['ruyitrace'],pins['ruyi-mcp']))
        for component in ['ruyitrace','ruyi-mcp']:
            assert re.fullmatch(r'[0-9a-f]{40}',pins[component]);git(root/'submodules'/component,'merge-base','--is-ancestor',pins[component],'HEAD')
            if version=='original': assert pins[component]==git(root,'rev-parse',idx['starting_platform']+':submodules/'+component)
            else: assert pins[component]==ledger['submodules'][component]['commit']==git(root,'rev-parse',':submodules/'+component)
        for mode in ('standard','paused'):
            r=gate(g,mode); assert r['passed'] and all(r['cleanup'].values()); stops=r['checks'][-1]
            assert any(w['name']=='native-rdp' for w in r['checks']) and stops['drainVerified'] and stops['confirmedWriters']>0 and stops['coreRows']>0
            assert stops['leasesAcquired']==2 and stops['sessionNew']==stops['sessionEnd']==1 and stops['sessionEndAcknowledged'] and stops['descriptorRemoved']
            if mode=='paused': assert stops['leasesRevoked']==stops['leasesReleased']==1 and stops['resumedInSameWindowBeforeGateClose'] and stops['stoppedBeforeBorrowerWatchdog']
            else: assert stops['leasesReleased']==2 and stops['leasesRevoked']==0
        exp=gate(g,'expiry'); assert exp['passed'] and exp['expiryVerified'] and exp['browserRetained'] and exp['wrongScopeRejected']==8 and exp['nativeCleanup']['leasesExpired']==1 and exp['canaryClicks']=={'beforeLegitimate':0,'afterLegitimate':1,'beforeExpired':1,'afterExpired':1}
        ssh=gate(g,'ssh');assert ssh['passed'] and ssh['distinctMachines'] and ssh['handshakes']==2 and ssh['exclusiveLease'] and ssh['sameBrowserGeneration'] and ssh['testContainerRemoved'] and ssh['arch']==arch
        assert ssh.get('browserPortForwardedOrPublished',ssh.get('tunnelOrPublishedPort')) is False and ssh['image']==g['image_id'] and ssh['payloadSha256']==ident['manifestSha']
        clean=ssh['cleanup'];assert clean['leases']==[2,2] and clean['bidi']==[1,1] and clean['nativeTitleBetweenGateEdges'] and clean['drainVerified'] and clean['browserReaped'] and clean['descriptorRemoved'];assert all(re.fullmatch('[0-9a-f]{64}',w['sha256']) and w['bytes']>0 for w in clean['writerDigests']) and clean['writerDigests']
        manifests.add(ident['manifestSha']);images.add(g['image_id'])
    assert len(manifests)==len(sourcepairs)==1 and len(images)==2
    print('PASS',version,'both native architectures: standard, paused, expiry and cross-machine SSH stdio')
for k in ('original','corrected'):
    fault=idx['fault'][k]; assert fault['image_id']==idx['sets'][k]['arm64']['image_id'] and fault['receipt'] in idx['files']; r=load(fault['receipt']); assert r['scenario']=='browser-loss'
    ck={w['name']:w for w in r['checks']};assert ck['crash-finalization']['browserExit']==137 and not ck['crash-finalization']['nativeFlushConfirmed'] and not ck['crash-finalization']['drainVerified'] and not ck['crash-finalization']['sessionEndAcknowledged']
    assert ck['retired-run']['rdpRelayRefused'] and ck['retired-run']['browserExited'] and ck['sentinel-after-loss']['challengeRoundTrip']
    if k=='original': assert not r['passed'] and r['failure']['stage']=='crash-lease-accounting' and r['observations']['leaseRevocation']=='zero-recorded'
    else:
        assert r['passed'] and r['requireRetiredClient'] and ck['crash-lease-accounting']['leasesRevoked']==1 and ck['borrowed-control-after-loss']['status']=='proven-retired' and ck['retired-client-quit']['effect']=='lease_already_lost' and ck['recovery-same-client-action']['sameStdioClient'] and ck['recovery-stop']['nativeFlushConfirmed']
print('PASS live process-loss negative control, explicit incomplete capture, corrected retirement and recovery')

# Replay the released Electron verifier's native predicates on the new, separate cases.
deployed=root/'artifacts/receipts/trace-linux-gap-closure-v1/electron-owner'
spec=importlib.util.spec_from_file_location('released_electron_review',deployed/'verify_candidate_d.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
proofs=v.source_custody(deployed)
case='borrow_return_reborrow'; criteria=json.loads((deployed/'custody/criteria.json').read_bytes())['gates']['electron_owner']['cases'][case]
release=idx['electron']; members=load(release['install_verification']); downloads=load(release['release_downloads'])
assert len(downloads['assets'])==6 and set(release['fresh'])=={'amd64','arm64'}
for arch, file in release['fresh'].items():
    r=load(file); rec=r['case_receipt']; run=rec['run']; proj=r['native_readback']; check=r['independent_verification']
    v.validate_run(run,arch,case,proofs[arch],criteria); v.verify_chronology(run,case); retained=v.validate_readback(run,proj,case)
    assert run['artifact']['traceSource']==release['installed_source'] and run['artifact']['mcpPin']==release['mcp']
    assert r['release']['packaging_tag_commit']==release['tag_commit'] and r['timing']['runner_exit']==0
    assert check['fresh_identities_distinct_from_all_ten_historical_cases'] and check['native_original_rehash']['state']=='ordered_close_read_back'
    assert retained['native_writer_sha256']==check['native_original_rehash']['native_writer_sha256'] and retained['result_sha256']==check['native_original_rehash']['result_sha256']
    old=json.loads((deployed/'runs'/(arch+'-'+case+'.json')).read_bytes())
    assert rec['original_sha256']!=old['original_sha256'] and run['process']['firefox_instance_sha256']!=old['run']['process']['firefox_instance_sha256']
    assert (members['archives'][arch]['bytes'],members['archives'][arch]['sha256'])==v.ARCHIVES[arch]
print('PASS independently rehashed Electron release and two new original-launcher native borrow/return/reborrow witnesses')
