#!/usr/bin/env python3
"""Isolated storage API tests; no staging data used."""
import importlib.util, tempfile, threading, http.client, json, hashlib
from pathlib import Path
from phase4a_storage_update import updated, ROOT

def main():
    source=ROOT/'phase3_staging/application/server.py'
    raw=source.read_bytes()
    if b"if self.path == '/api/storage':" not in raw: raw=updated(raw)
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/'application'; p.mkdir(); f=p/'server.py'; f.write_bytes(raw)
        spec=importlib.util.spec_from_file_location('isolated',f); app=importlib.util.module_from_spec(spec); spec.loader.exec_module(app); app.init()
        token='test-only'; device='test-device'
        with app.database() as c: c.execute('INSERT INTO devices VALUES (?,?,?,?,0)',(device,'Test',app.digest(token),0))
        with app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler) as server:
            t=threading.Thread(target=server.serve_forever); t.start()
            def get(token=None):
                conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
                try:
                    conn.request('GET','/api/storage',headers={'Authorization':'Bearer '+token} if token else {}); r=conn.getresponse(); return r.status,json.loads(r.read())
                finally: conn.close()
            try:
                assert get()[0]==401 and get('wrong')[0]==401; print('PASS: Missing and invalid token')
                status,d=get(token); assert status==200 and d['stored_media_bytes']==0 and d['stored_media_count']==0; assert d['available_backup_bytes']==max(0,d['free_bytes']-d['reserve_bytes']); assert d['total_bytes']>=d['used_bytes']+d['free_bytes']; print('PASS: Authenticated storage and reserve')
                with app.database() as c: c.execute('INSERT INTO media VALUES (?,?,?)',('a'*64,'originals/test',123))
                status,d=get(token); assert status==200 and d['stored_media_bytes']==123 and d['stored_media_count']==1; print('PASS: Unique stored media accounting')
                with app.database() as c: c.execute('UPDATE devices SET revoked=1 WHERE id=?',(device,))
                assert get(token)[0]==401; print('PASS: Revoked token')
            finally: server.shutdown(); t.join()
    print('RESULT: 4/4 storage groups passed')
if __name__=='__main__': main()
