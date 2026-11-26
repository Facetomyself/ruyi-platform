// Run on the operator machine, not in the Trace owner container. The local SDK spawns ssh as its MCP transport.
import assert from 'node:assert/strict';
import {execFile,spawn} from 'node:child_process';
import {createHash,randomUUID} from 'node:crypto';
import {promises as fs} from 'node:fs';
import {createRequire} from 'node:module';
import path from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
import {pathToFileURL} from 'node:url';
import {promisify} from 'node:util';

const [host,image,mcpRoot] = process.argv.slice(2);
assert.match(host || '',/^[a-zA-Z0-9][a-zA-Z0-9.-]{0,90}$/); assert.match(image || '',/^sha256:[a-f0-9]{64}$/); assert.ok(path.isAbsolute(mcpRoot));
const ssh=['-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ClearAllForwardings=yes','-o','ConnectTimeout=8','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=3',host];
const quote=s=>"'"+s.replaceAll("'","'\\''")+"'";
const remoteArgv=(...args)=>[...ssh,args.map(quote).join(' ')];
// Never relay subprocess output/errors or owner capabilities into the receipt.
async function remote(...args){
  const {stdout}=await promisify(execFile)('ssh',remoteArgv(...args),{timeout:65000,maxBuffer:1024*1024});return stdout.trim();
}
async function upload(args,bytes){
  const child=spawn('ssh',remoteArgv(...args),{stdio:['pipe','ignore','ignore']});
  const end=new Promise((yes,no)=>{child.once('error',no);child.once('close',(code,sig)=>code===0&&!sig?yes():no(new Error('remote write failed')))});
  const timer=setTimeout(()=>child.kill('SIGKILL'),15000); child.stdin.on('error',()=>{});child.stdin.end(bytes);
  try {await end}finally{clearTimeout(timer)}
}
const require=createRequire(path.join(mcpRoot,'package.json'));
const sdk=kind=>import(pathToFileURL(require.resolve(`@modelcontextprotocol/sdk/client/${kind}.js`)).href);
const [{Client},{StdioClientTransport}]=await Promise.all([sdk('index'),sdk('stdio')]);
let cid,stage='preflight',a,b,stopped=false;const nonce=randomUUID();
const name=`ruyi-ssh-witness-${nonce}`;
const rec={schema:'ruyi-native-ssh-stdio.v1',passed:false,image,transport:'operator SDK -> ssh -T -> remote docker exec -i -> MCP stdio',browserPortForwardedOrPublished:false};
const dx=(...args)=>remote('docker','exec',cid,...args);
const helper=async op=>JSON.parse(await dx('node','/tmp/ssh-fixture.mjs',op));
function makeClient(){
  const transport=new StdioClientTransport({command:'ssh',args:remoteArgv('docker','exec','-i','--user','1000:1000','-e','RUYI_MCP_TOOLSET=debug',cid,'/usr/local/bin/node','/opt/live-qa/mcp/build/src/index.js'),stderr:'ignore',env:Object.fromEntries(['HOME','PATH','SSH_AUTH_SOCK'].filter(v=>process.env[v]).map(v=>[v,process.env[v]]))});
  const client=new Client({name:'ruyi-remote-stdio-witness',version:'1'});
  return {close:()=>client.close(),connect:async()=>{await client.connect(transport,{timeout:15000});assert.equal(client.getServerVersion()?.name,'ruyi-mcp'); const list=await client.listTools();assert.ok(list.tools.some(t=>t.name==='ruyi_attach_trace_session'))},
    call:async(name,args={},busy=false)=>{const res=await client.callTool({name,arguments:args},undefined,{timeout:15000});const text=res.content?.[0]?.text;
      if(busy){assert.ok(res.isError&&/\bLEASE_BUSY\b/.test(text));return}
      assert.ok(!res.isError&&typeof text==='string','remote MCP operation failed');return JSON.parse(text)} };
}
try{
  const local= createHash('sha256').update(await fs.readFile('/etc/machine-id')).digest('hex');
  const remoteHash=(await remote('sha256sum','/etc/machine-id')).split(/\s+/)[0];assert.match(remoteHash,/^[0-9a-f]{64}$/);assert.notEqual(local,remoteHash);
  rec.distinctMachines=true;
  const [info]=JSON.parse(await remote('docker','image','inspect',image));assert.equal(info.Id,image);assert.match(info.Config.Labels['ruyi.qa.payload'],/^[a-f0-9]{64}$/);
  rec.arch=info.Architecture;rec.payloadSha256=info.Config.Labels['ruyi.qa.payload'];
  stage='isolated remote fixture';
  cid=await remote('docker','create','--name',name,'--label',`ruyi.qa.ssh=${nonce}`,'--init','--pull=never','--network=none','--read-only','--user','1000:1000','--cap-drop=ALL','--security-opt=no-new-privileges=true','--cpus=2','--memory=2500m','--pids-limit=512','--shm-size=256m','--tmpfs','/tmp:rw,nosuid,nodev,mode=1777,size=1g','-e','HOME=/tmp/home','-e','XDG_RUNTIME_DIR=/tmp/xdg','--entrypoint','/usr/local/bin/node',image,'-e','setTimeout(()=>process.exit(0),240000)');
  assert.match(cid,/^[a-f0-9]{64}$/);await remote('docker','start',cid);
  const [container]=JSON.parse(await remote('docker','container','inspect',cid));assert.equal(container.Image,image);assert.equal(container.HostConfig.NetworkMode,'none');assert.equal(container.HostConfig.ReadonlyRootfs,true);assert.equal(container.Config.Labels['ruyi.qa.ssh'],nonce);
  await dx('/bin/sh','-ec','mkdir -m700 /tmp/home /tmp/xdg; test ! -e /tmp/ssh-fixture.mjs');
  await upload(['docker','exec','-i',cid,'/bin/sh','-ec','umask 077; set -C; tee /tmp/ssh-fixture.mjs >/dev/null'],await fs.readFile(new URL('./ssh-fixture.mjs',import.meta.url)));
  await remote('docker','exec','-d',cid,'/usr/local/bin/node','/tmp/ssh-fixture.mjs','serve');
  const deadline=performance.now()+65000; let ready;
  do{try{ready=await helper('inspect');break}catch{await delay(350)}}while(performance.now()<deadline);
  assert.ok(ready?.running,'remote owner did not get ready');assert.equal(ready.descriptorPath,'/tmp/ruyi-ssh-witness/run/control/session.json');
  const attach={sessionPath:ready.descriptorPath};
  stage='SSH MCP handshake and lease';a=makeClient();b=makeClient();await a.connect();await b.connect();
  const own=await a.call('ruyi_attach_trace_session',attach);assert.equal(own.runId,ready.runId);assert.equal(own.contextId,ready.contextId);assert.equal(own.controlAvailable,true);
  await b.call('ruyi_attach_trace_session',attach,true);
  stage='SSH MCP page action';const query=async c=>(await c.call('ruyi_trace_control',{action:'query',selector:'#value',maxElements:1})).elements;
  assert.equal((await query(a))[0]?.text,'ready');await a.call('ruyi_trace_control',{action:'click',selector:'#write'});assert.equal((await query(a))[0]?.text,'recorded');
  const quit=await a.call('ruyi_browser_quit');assert.equal(quit.effect,'lease_released');assert.equal(quit.browserDisposition,'retained_by_owner');await a.close();a=null;
  stage='SSH reattach and EOF';const res=await b.call('ruyi_attach_trace_session',attach);assert.equal(res.contextId,ready.contextId);assert.equal((await query(b))[0]?.text,'recorded');assert.deepEqual(await helper('inspect'),ready);await b.close();b=null;
  // stdin EOF across the SSH session must return B's lease during server cleanup.
  stage='native remote readback';rec.cleanup=await helper('finish');stopped=true;rec.handshakes=2;rec.exclusiveLease=true;rec.sameBrowserGeneration=true;rec.passed=true;
}catch{rec.failure={stage}}finally{
  for(const c of [a,b])if(c) await c.close().catch(()=>{});
  if(cid&&/^[a-f0-9]{64}$/.test(cid)){
    if(!stopped)await helper('finish').catch(()=>{});
    try {const [c]=JSON.parse(await remote('docker','container','inspect',cid));assert.equal(c.Id,cid);assert.equal(c.Image,image);assert.equal(c.Config.Labels['ruyi.qa.ssh'],nonce);assert.equal(c.Name,`/${name}`); await remote('docker','rm','-f',cid);rec.testContainerRemoved=true;}
    catch{rec.passed=false;rec.testContainerRemoved=false}
  }
}
console.log(JSON.stringify(rec));process.exitCode=rec.passed?0:1;
