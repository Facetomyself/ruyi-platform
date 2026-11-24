"""A real TLS peer answers with Content-Encoding: zstd; the client must decode it."""
import base64, hashlib, json, os, socket, ssl, subprocess, sys, threading, time
from pathlib import Path
BASE, ADDON, PKI, OUT, HEX = sys.argv[1:6]
CA = PKI + '/ca'
venv = Path('/tmp/bre')
subprocess.run(['/usr/bin/python3','-I','-B','-m','venv',str(venv)], check=True, timeout=120)
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
(native/'tls-pins.json').write_text(json.dumps({
  '127.0.0.1':[hashlib.sha256(der(CA+'/leaf.crt')).hexdigest()],
  'trust_anchors':[{'path':str(native/'anchor.der'),'sha256':hashlib.sha256(ca).hexdigest()}],
})+'\n')
body = bytes.fromhex(Path(HEX).read_text().strip())
expected = b"hello zstd from an independent encoder"
ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(CA+'/leaf.crt',CA+'/leaf.key')
ctx.set_alpn_protocols(['http/1.1'])
l=socket.socket(); l.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
l.bind(('127.0.0.1',0)); l.listen(2); port=l.getsockname()[1]
seen={'advertised':[], 'sent_zstd':False}
def serve():
    try:
        c,_=l.accept(); c.settimeout(10)
        try:
            s=ctx.wrap_socket(c,server_side=True); d=b''
            while b'\r\n\r\n' not in d:
                x=s.recv(4096)
                if not x: break
                d+=x
            for line in d.split(b'\r\n'):
                if line.lower().startswith(b'accept-encoding:'):
                    seen['advertised'].append(line.split(b':',1)[1].strip().decode('latin-1'))
            # Only answer with brotli if the client said it could take it.
            if 'zstd' in ' '.join(seen['advertised']).lower():
                seen['sent_zstd']=True
                s.sendall(b'HTTP/1.1 200 OK\r\nContent-Encoding: zstd\r\nContent-Length: '
                          + str(len(body)).encode() + b'\r\nConnection: close\r\n\r\n' + body)
            else:
                s.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 5\r\nConnection: close\r\n\r\nplain')
            s.close()
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
    c.load_page(url,"<title>b</title>")
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
decoded = value.get('t')
rep={'value':value,'error':err,'peer':seen,
     'passed': decoded==expected.decode() and seen['sent_zstd'] and value.get('s')==200}
Path(OUT).write_text(json.dumps(rep,indent=2,sort_keys=True)+'\n')
print(json.dumps({'passed':rep['passed'],'status':value.get('s'),'body':decoded,'err':err[:60],'sent_zstd':seen['sent_zstd'],'advertised':seen['advertised']}))
sys.exit(0 if rep['passed'] else 1)
