"""A real TLS peer negotiates h2; the vendored framing must complete a request."""
import base64, hashlib, json, os, socket, ssl, subprocess, sys, threading, time
from pathlib import Path
BASE, ADDON, PKI, OUT = sys.argv[1:5]
CA = PKI + '/ca'
venv = Path('/tmp/h2v')
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
(native/'tls-pins.json').write_text(json.dumps({
  '127.0.0.1':[hashlib.sha256(der(CA+'/leaf.crt')).hexdigest()],
  'trust_anchors':[{'path':str(native/'anchor.der'),'sha256':hashlib.sha256(ca).hexdigest()}],
})+'\n')
# Server side: the same h2 library in the installed venv, over TLS with ALPN h2.
server_code = r'''
import json, socket, ssl, sys, threading
sys.path.insert(0, sys.argv[1] + '/ruyijs_necko/_h2')
sys.path.insert(0, sys.argv[1])
from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import RequestReceived, DataReceived, StreamEnded
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(sys.argv[2], sys.argv[3])
ctx.set_alpn_protocols(['h2'])
l = socket.socket(); l.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
l.bind(('127.0.0.1', int(sys.argv[4]))); l.listen(2)
state = {'negotiated': None, 'requests': [], 'sent': False}
def serve():
    try:
        # First accept is the readiness probe; close it without a handshake.
        c0, _ = l.accept(); c0.close()
        state['stage'] = 'probe-accepted'
        c, _ = l.accept(); c.settimeout(15)
        state['stage'] = 'client-accepted'
        s = ctx.wrap_socket(c, server_side=True)
        state['stage'] = 'tls-done'
        state['negotiated'] = s.selected_alpn_protocol()
        conn = H2Connection(H2Configuration(client_side=False, header_encoding=None))
        s.settimeout(15)
        def read():
            data = s.recv(65536)
            if not data:
                return None
            return conn.receive_data(data)
        events = read()
        stream = None
        ended = False
        while not ended:
            for ev in events or []:
                if isinstance(ev, RequestReceived):
                    stream = ev.stream_id
                    hdrs = {k.decode(): v.decode() for k, v in ev.headers}
                    state['requests'].append(hdrs)
                if isinstance(ev, StreamEnded):
                    ended = True
            for out in (conn.data_to_send(),):
                if out:
                    s.sendall(out)
            if not ended:
                events = read()
                if events is None:
                    break
        if stream is not None:
            conn.send_headers(stream, [(':status', '200'), ('content-type', 'text/plain'), ('content-length', '5')], end_stream=False)
            conn.send_data(stream, b'hello', end_stream=True)
            out = conn.data_to_send()
            if out:
                s.sendall(out)
                state['sent'] = True
        s.close()
    except Exception as ex:
        state['alert'] = type(ex).__name__ + ': ' + str(ex)[:60]
    finally:
        l.close()
worker = threading.Thread(target=serve)
worker.start()
worker.join(20)
print(json.dumps(state), flush=True)
'''
# Reserve a port, run the server in-process of a child, then drive the client.
port_sock = socket.socket(); port_sock.bind(('127.0.0.1', 0)); port = port_sock.getsockname()[1]; port_sock.close()
server_log = Path('/tmp/h2-server.log')
server = subprocess.Popen([py, '-B', '-c', server_code, str(site), CA+'/leaf.crt', CA+'/leaf.key', str(port)],
                          stdout=subprocess.PIPE, stderr=open(server_log, 'w'), text=True,
                          env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','LD_LIBRARY_PATH')})
# Wait for the listener to actually accept, not a fixed sleep.
probe = socket.socket()
deadline_wait = time.time() + 10
while True:
    try:
        probe.connect(('127.0.0.1', port))
        probe.shutdown(socket.SHUT_RDWR); probe.close(); break
    except OSError:
        if time.time() > deadline_wait:
            break
        time.sleep(0.1)
url = f'https://127.0.0.1:{port}/x'
driver = f'''
import json, sys
sys.path.insert(0, {str(site)!r})
from ruyijs_necko import tls
try:
    reply = tls.fetch("GET", {url!r}, [], b"", http2=True)
    print(json.dumps({{"status": reply.status, "body": reply.body.decode("latin-1"), "proto": reply.protocol}}))
except Exception as error:
    print(json.dumps({{"error": type(error).__name__ + ": " + str(error)[:160]}}))
'''
env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','LD_LIBRARY_PATH')}
p=subprocess.run([py,'-I','-B','-c',driver],capture_output=True,text=True,timeout=60,env=env)
lines=[l for l in p.stdout.strip().splitlines() if l.strip()]
try:
    got=json.loads(lines[-1]) if lines else {'error': f'driver rc={p.returncode}; stdout_tail={p.stdout.strip()[-120:]!r}; stderr_tail={p.stderr.strip()[-200:]!r}'}
except Exception:
    got={'error': f'driver rc={p.returncode} unparseable; stderr: ' + p.stderr.strip()[-160:]}
if 'error' in got:
    value={}; err=got['error']
else:
    value=got; err=''
import time as _t; _t.sleep(0.3)
_srv_lines = server.stdout.readlines() if server.stdout else []
line_state = _srv_lines[-1] if _srv_lines else ''
srv=json.loads(line_state) if line_state else {}
rep={'value':value,'error':err,'server':srv,
     'passed': value.get('status')==200 and value.get('body')=='hello' and srv.get('negotiated')=='h2'}
Path(OUT).write_text(json.dumps(rep,indent=2,sort_keys=True)+'\n')
print(json.dumps({'passed':rep['passed'],'status':value.get('status'),'body':value.get('body'),'negotiated':srv.get('negotiated'),'srv_alert':srv.get('alert'),'err':err[:80]}))
server.terminate()
sys.exit(0 if rep['passed'] else 1)
