"""Read-only integrity check of the pinned, external RuyiJS Linux reference wheel."""
import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

NAME = 'ruyijs-0.2.2+inner.f08e835-py3-none-manylinux_2_39_x86_64.whl'
SIZE = 63_984_101
SHA256 = '8de31db4911f77b544b44f1827cb3cb32ea2335eb3361f9011ea5b9998549ab4'
INFO = 'ruyijs-0.2.2+inner.f08e835.dist-info/'
RECORD = INFO + 'RECORD'
JS = 'ruyijs/_runtime/dist/js'


def digest(stream):
    h=hashlib.sha256()
    for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
    return h


def inventory(entries):
    found={}
    for item in entries:
        n=PurePosixPath(item.filename)
        if (n.is_absolute() or '..' in n.parts or n.as_posix()!=item.filename or '\\' in item.filename
                or item.filename in found or stat.S_IFMT(item.external_attr>>16)!=stat.S_IFREG
                or item.flag_bits&1 or item.file_size<0):
            raise ValueError('unexpected wheel member')
        found[item.filename]=item
    return found


def verify(wheel):
    if not wheel.is_file() or wheel.stat().st_size!=SIZE:
        raise ValueError('external reference wheel size differs')
    with wheel.open('rb') as f:
        outer=digest(f).hexdigest()
        if outer!=SHA256:raise ValueError('external reference wheel SHA-256 differs')
        f.seek(0)
        with zipfile.ZipFile(f) as z:
            entries=inventory(z.infolist())
            if len(entries)!=2072 or sum(v.file_size for v in entries.values())!=170_437_136:
                raise ValueError('unexpected member total or aggregate size')
            if not {'Tag: py3-none-manylinux_2_39_x86_64','Root-Is-Purelib: false'}<=set(z.read(INFO+'WHEEL').decode().splitlines()):
                raise ValueError('wrong reference wheel metadata tag')
            checked=set();js_sha=None
            for name,encoded,size in csv.reader(io.StringIO(z.read(RECORD).decode('utf-8'))):
                if name not in entries or name in checked:raise ValueError('unknown or duplicate RECORD path')
                checked.add(name)
                if name==RECORD:
                    if encoded or size:raise ValueError('RECORD self row must have empty size and digest')
                    continue
                if not re.fullmatch(r'sha256=[A-Za-z0-9_-]{43}',encoded) or size!=str(entries[name].file_size):
                    raise ValueError('missing or incorrect digest/size in RECORD: '+name)
                with z.open(entries[name]) as stream:h=digest(stream)
                if base64.urlsafe_b64encode(h.digest()).decode().rstrip('=')!=encoded[7:]:
                    raise ValueError('file SHA-256 differs from RECORD: '+name)
                if name==JS:js_sha=h.hexdigest()
            if checked!=entries.keys() or js_sha is None:raise ValueError('incomplete wheel RECORD coverage')
            with z.open(JS) as stream:hdr=stream.read(20)
            if hdr[:6]!=b'\x7fELF\x02\x01' or int.from_bytes(hdr[18:20],'little')!=62:raise ValueError('reference js is not an x86_64 ELF')
            return dict(schema=1,scope='external reference only; ZIP/RECORD read-only, no extraction or execution',
                        wheel=NAME,bytes=SIZE,sha256=outer,zip_members=len(entries),record_digests=len(checked)-1,
                        js=dict(path=JS,sha256=js_sha,bytes=entries[JS].file_size,elf='x86_64'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('wheel',nargs='?',type=Path,default=Path(__file__).resolve().parents[1]/'artifacts/binaries/ruyijs'/NAME)
    a=p.parse_args();print(json.dumps(verify(a.wheel),indent=2))
