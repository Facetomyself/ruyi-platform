"""default_anchors:true must trust the 121-root bundle but refuse our test CA."""
import base64, hashlib, json, os, ssl, socket, subprocess, sys, threading, time
from pathlib import Path
BASE, ADDON, PKI, OUT = sys.argv[1:5]
CA = PKI + '/ca'
venv = Path('/tmp/dar')
subprocess.run(['/usr/bin/python3','-I','-B','-m','venv',str(venv)], check=True, timeout=150)
py = str(venv/'bin'/'python3')
pip = [py,'-I','-B','-m','pip','--isolated','--disable-pip-version-check','--no-cache-dir','--no-input','--require-virtualenv']
for w in (BASE, ADDON):
    subprocess.run(pip+['install','--no-index','--no-deps',w], check=True, timeout=300, stdout=subprocess.DEVNULL)
site = Path(subprocess.check_output([py,'-I','-c','import sysconfig;print(sysconfig.get_path("platlib"))'],text=True).strip())
native = site/'ruyijs_necko'/'_native'
def der(p):
    pem=Path(p).read_bytes(); b,e=b'-----BEGIN CERTIFICATE-----',b'-----END CERTIFICATE-----'
    return base64.b64decode(b''.join(pem[pem.index(b)+len(b):pem.index(e)].split()))
ca=der(CA+'/ca.crt'); (native/'anchor.der').write_bytes(ca)
# default_anchors: bundle only — the test CA is NOT among the 121 Mozilla roots,
# so a leaf chained to it must be refused even with the pin present.
(native/'tls-pins.json').write_text(json.dumps({
  '127.0.0.1':[hashlib.sha256(der(CA+'/leaf.crt')).hexdigest()],
  'default_anchors': True,
})+'\n')
ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(CA+'/leaf.crt',CA+'/leaf.key')
ctx.set_alpn_protocols(['http/1.1'])
l=socket.socket(); l.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
l.bind(('127.0.0.1',0)); l.listen(2); port=l.getsockname()[1]
seen={'requests':[]}
def serve():
    try:
        c,_=l.accept(); c.settimeout(10)
        try:
            s=ctx.wrap_socket(c,server_side=True); d=b''
            while b'\r\n\r\n' not in d:
                x=s.recv(4096)
                if not x: break
                d+=x
            seen['requests'].append(1)
            s.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nhi'); s.close()
        except Exception as ex: seen['alert']=type(ex).__name__
    finally: l.close()
threading.Thread(target=serve,daemon=True).start()
url='https://127.0.0.1:%d/x'%port
snippet='''
import json, time
from ruyijs import Context
url=__U__
with Context() as c:
    c.configure_clock("logical", epoch_ms=0)
    c.load_page(url,"<title>d</title>")
    c.eval("globalThis.r=null; fetch("+json.dumps(url)+").then(async x=>{globalThis.r={s:x.status,t:await x.text()}},e=>{globalThis.r={e:String(e)}});void 0")
    end=time.monotonic()+14;v=None
    while time.monotonic()<end:
        v=c.eval("r")
        if v is not None: break
        c.advance(10,step_ms=2,max_tasks=48); time.sleep(0.02)
    print(json.dumps({"value":v,"log":c.net_log()}))
'''.replace('__U__',repr(url))
env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','LD_LIBRARY_PATH')}
p=subprocess.run([py,'-I','-B','-c',snippet],capture_output=True,text=True,timeout=120,env=env)
got=json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {}
value=got.get('value') or {}
err=(got.get('log') or [{}])[0].get('error','')
rep={'value':value,'error':err,'peer':seen,
     'passed': bool(value.get('e')) and seen.get('requests')==[] and ('chain' in err or 'verification' in err or 'CA' in err)}
Path(OUT).write_text(json.dumps(rep,indent=2,sort_keys=True)+'\n')
print(json.dumps({'passed':rep['passed'],'value':value,'err':err[:70]}))
sys.exit(0 if rep['passed'] else 1)
