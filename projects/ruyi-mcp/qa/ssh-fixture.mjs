// Only for a new private native QA container. No external listener or browser data leaves it.
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { createHash, randomUUID } from 'node:crypto';
import { once } from 'node:events';
import { promises as fs } from 'node:fs';
import { createServer } from 'node:http';
import { promisify } from 'node:util';
import path from 'node:path';
const exec=promisify(execFile), base='/tmp/ruyi-ssh-witness', out=`${base}/run`, cli='/opt/live-qa/cli/bin/ruyitrace';
const json=async p=>JSON.parse(await fs.readFile(p,'utf8'));
const generation=async pid=>{
  const st=await fs.readFile(`/proc/${pid}/stat`,'utf8').catch(e=>{if(e.code==='ENOENT'||e.code==='ESRCH')return '';throw e});
  if(!st.startsWith(`${pid} (`)) return null;
  const fields=st.slice(st.lastIndexOf(')')+1).trim().split(/\s+/); return ['Z','X','x'].includes(fields[0])?null:fields[19];
};
async function call(action,...args){
  const {stdout}=await exec(process.execPath,[cli,action,'--json',...args],{timeout:60000,maxBuffer:1024*1024});
  const value=JSON.parse(stdout); assert.notEqual(value.ok,false); return value;
}
async function serve(){
  await fs.mkdir(base,{mode:0o700});
  const marker=`ssh-witness-${randomUUID()}`;
  const script=`document.querySelector('#write').onclick=()=>{document.title=${JSON.stringify(marker)};document.querySelector('#value').textContent='recorded';};\n`;
  const html='<!doctype html><title>SSH fixture</title><button id="write">Record once</button><output id="value">ready</output><script src="/case.js"></script><script>let beats=0; const pulse=setInterval(()=>{void document.title;if(++beats>1500)clearInterval(pulse)},100);</script>';
  const http=createServer((req,res)=>{
    if(req.method!=='GET'||!['/case','/case.js'].includes(req.url))return res.writeHead(404).end();
    const js=req.url==='/case.js';res.writeHead(200,{'content-type':js?'application/javascript':'text/html','cache-control':'no-store'}).end(js?script:html);
  });
  http.listen(0,'127.0.0.1');await once(http,'listening');const origin=`http://127.0.0.1:${http.address().port}`;
  try {
    const start=await call('start','--gated','--gate','auto','--mcp','--sinks','core,click','--out',out,'--firefox','/browser/firefox','--receipt','/identity-input','--acceptance','/opt/ruyitrace/proofs/baseline.json','--origin',origin,'--',`${origin}/case`);
    const state=await json(`${out}/state.json`);
    assert.equal(start.running,true); assert.equal(start.gate.confirmation,'session-started'); assert.equal(start.descriptorPath,`${out}/control/session.json`);
    assert.equal(await generation(state.browser.pid),state.browser.startTime);
    await fs.writeFile(`${base}/ready.json`,JSON.stringify({run:start.runId,context:start.contextId,browser:state.browser,owner:state.owner,origin,marker}),{mode:0o600,flag:'wx'});
  } catch(e){http.close();throw e}
}
async function control(action){
  const ready=await json(`${base}/ready.json`);
  const status=await call('status','--run',out);
  assert.equal(status.runId,ready.run);assert.equal(status.pid,ready.browser.pid);
  assert.equal(status.contextId,ready.context);assert.equal(status.running,true);
  assert.equal(await generation(ready.browser.pid),ready.browser.startTime);assert.equal(await generation(ready.owner.pid),ready.owner.startTime);
  if(action==='inspect')return {running:true,browserPid:ready.browser.pid,creationTime:ready.browser.startTime,runId:ready.run,contextId:ready.context,descriptorPath:status.descriptorPath};
  assert.equal(action,'finish');const reply=await call('stop','--run',out), r=await json(`${out}/result.json`);
  assert.deepEqual(reply.result,r); assert.equal(r.runId,ready.run);assert.equal(r.passed,true);assert.equal(r.completion,'requested-stop');assert.equal(r.gate.confirmation,'session-stopped');
  assert.equal(await generation(ready.browser.pid),null);
  await assert.rejects(fs.stat(status.descriptorPath),{code:'ENOENT'});
  let witnessed=false;const readback=[];
  for(const writer of r.gate.writers){
    assert.ok(Number.isSafeInteger(writer.pid)&&writer.pid>1);
    const p=path.join(out,'domtrace',`trace_process_${writer.pid}.jsonl`),st=await fs.lstat(p);
    assert.ok(st.isFile()&&st.size>0&&st.size<=8*1024*1024); const data=await fs.readFile(p,'utf8');assert.ok(data.endsWith('\n'));
    let opened=false,closed=false,writeSeen=false;
    for(const line of data.trimEnd().split('\n')){const row=JSON.parse(line);if(row.session!==writer.session)continue;
      if(row.type==='session_started'&&row.pid===writer.pid){assert.equal(opened,false);opened=true}
      else if(row.type==='session_stopped'&&row.pid===writer.pid){assert.ok(opened&&!closed);closed=true}
      else if(opened&&!closed&&row.type==='set'&&row.ctx==='top'&&row.ctx_origin===ready.origin&&row.interface==='Document'&&row.member==='title'&&row.value===ready.marker){writeSeen=true}
    }
    witnessed ||= opened&&closed&&writeSeen;
    readback.push({bytes:st.size,sha256:createHash('sha256').update(data).digest('hex')});
  }
  assert.ok(witnessed);const m=r.mcp;
  assert.equal(m.leasesAcquired,2);assert.equal(m.leasesReleased,2);assert.equal(m.leasesRevoked+m.leasesExpired,0);assert.ok(m.drainVerified);
  assert.equal(m.bidi.sessionNew,1);assert.equal(m.bidi.sessionEnd,1);assert.ok(m.bidi.sessionEndAcknowledged);
  return {browserReaped:true,descriptorRemoved:true,nativeTitleBetweenGateEdges:true,writerDigests:readback,leases:[2,2],bidi:[1,1],drainVerified:true};
}
try{const op=process.argv[2];if(op==='serve')await serve();else if(['inspect','finish'].includes(op))console.log(JSON.stringify(await control(op)));else throw new Error('Unknown QA action')}
catch{console.error('Remote QA helper failed: '+String(process.argv[2]));process.exitCode=1}
