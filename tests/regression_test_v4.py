#!/usr/bin/env python3
"""Run from PiBackup_app/tests; never write to staging or production data."""
import hashlib, http.client, importlib.util, json, os, shutil, socket, sqlite3, tempfile, threading, time, uuid
from pathlib import Path
from PIL import Image
import io
ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / 'phase3_staging'
PORT = 8093
CHUNK = 4*1024**2
results = []
def check(name, fn):
    try:
        fn(); results.append((name, True)); print('PASS:', name, flush=True)
    except Exception as e:
        results.append((name, False)); print('FAIL:', name, type(e).__name__, str(e), flush=True)
def require(condition, message='unexpected result'):
    if not condition: raise AssertionError(message)
def snapshot():
    paths = [ROOT/'application/server.py', ROOT/'data/pibackup.db', STAGE/'application/server.py', STAGE/'data/pibackup.db']
    paths += sorted(p for folder in (ROOT/'application/phase2_backup',ROOT/'checkpoints/phase3.1',ROOT/'checkpoints/phase3.4') for p in folder.rglob('*') if p.is_file())
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
def req(method, path, body=None, token=None, headers=None, expected=200):
    h = dict(headers or {})
    if token: h['Authorization']='Bearer '+token
    if isinstance(body,dict): body=json.dumps(body).encode(); h['Content-Type']='application/json'
    c=http.client.HTTPConnection('127.0.0.1',PORT,timeout=30)
    try:
        c.request(method,path,body,h); r=c.getresponse(); data=json.loads(r.read())
        require(r.status==expected, f'HTTP {r.status}, expected {expected}'); return data
    finally: c.close()
def sql(query,args=()):
    with app.database() as c: return c.execute(query,args).fetchall()
def code(expiry=300):
    value=f'{uuid.uuid4().int%1000000:06d}'
    sql('INSERT OR REPLACE INTO pairing VALUES (1,?,?,0)',(app.digest(value),time.time()+expiry)); return value
def pair(value=None,expected=201):
    return req('POST','/api/pair',{'code':value or code(),'name':'Regression'},expected=expected)
def token(): return pair()['token']
def meta(data,name='sample.jpg',source='Camera'):
    return dict(sha256=hashlib.sha256(data).hexdigest(),size=len(data),name=name,source=source,capture_date='2024-08-15')
def start(m,t,expected=200): return req('POST','/api/uploads/start',m,t,expected=expected)
def chunk(u,b,t,offset=0,expected=200): return req('POST',f'/api/uploads/{u}/chunk',b,t,{'Upload-Offset':str(offset)},expected)
def finish(u,t,expected=200): return req('POST',f'/api/uploads/{u}/finish',{},t,expected=expected)
def upload(data,m,t):
    u=start(m,t)['upload_id']
    for off in range(0,len(data),CHUNK): require(chunk(u,data[off:off+CHUNK],t,off)['offset']==min(off+CHUNK,len(data)))
    require(finish(u,t)['complete']); return u
def integrity():
    require(sql('PRAGMA integrity_check')==[('ok',)]); require(not sql('PRAGMA foreign_key_check'))
def auth():
    t=token(); d=req('GET','/api/device',token=t)['device_id']; req('GET','/api/device',expected=401); req('GET','/api/device',token='invalid',expected=401)
    sql('UPDATE devices SET revoked=1 WHERE id=?',(d,)); req('GET','/api/device',token=t,expected=401)
def pairing():
    c=code(); pair(c); pair(c,403); pair(code(-1),403)
    c=code(); wrong='000000' if c!='000000' else '000001'
    for _ in range(5): pair(wrong,403)
    pair(c,403)
    old=code(); new=code()
    while new==old: new=code()
    pair(old,403); pair(new)
def migration():
    before={t:sql('SELECT * FROM '+t) for t in ('devices','media','media_refs','media_metadata','thumbnail_jobs','trash_refs')}
    app.init(); require(sql('PRAGMA user_version')==[(1,)])
    for t,rows in before.items(): require(sql('SELECT * FROM '+t)==rows,t)
    integrity()
def jpeg_test():
    b=io.BytesIO(); Image.new('RGB',(640,480)).save(b,'JPEG'); data=b.getvalue()+os.urandom(16); m=meta(data,'regression_'+uuid.uuid4().hex+'.jpg'); t=token(); t2=token(); u=upload(data,m,t)
    sha=m['sha256']; path,size=sql('SELECT path,size FROM media WHERE hash=?',(sha,))[0]; require(Path(path).name==m['name']); require(size==len(data)); require(hashlib.sha256((app.DATA/path).read_bytes()).hexdigest()==sha)
    require(start(m,t)['complete']); require(start(m,t2)['complete'])
    for table,n in [('media',1),('media_metadata',1),('thumbnail_jobs',1),('media_refs',2)]: require(sql(f'SELECT COUNT(*) FROM {table} WHERE hash=?',(sha,))==[(n,)],table)
    require(sql('SELECT status,attempts FROM thumbnail_jobs WHERE hash=?',(sha,))==[('pending',0)])
    require(not (app.DATA/'incomplete'/u).exists()); require(not sql('SELECT id FROM uploads WHERE id=?',(u,)))
    other=data+b'conflict'; m2=meta(other,m['name']); upload(other,m2,t); p=sql('SELECT path FROM media WHERE hash=?',(m2['sha256'],))[0][0]; require(Path(p).stem.endswith('_'+m2['sha256'][:8])); require((app.DATA/path).read_bytes()==data)
def invalid_metadata():
    t=token(); m=meta(b'abc')
    start(dict(m,sha256='bad'),t,400)
    start(dict(m,size=20_000_000_001),t,400)
    start(dict(m,name='../bad'),t,400)
    start(m,None,401)
def oversized_chunk():
    t=token(); m=meta(b'abc'); u=start(m,t)['upload_id']
    # Send only headers: the server must reject the declared size
    # before reading any body. A timeout is a test failure.
    req('POST',f'/api/uploads/{u}/chunk',b'',t,
        {'Upload-Offset':'0','Content-Length':str(CHUNK+1),
         'Content-Type':'application/octet-stream'},expected=400)
    require(start(m,t)['offset']==0)
    require(not (app.DATA/'incomplete'/u).exists())
def ownership():
    t=token(); other=token(); m=meta(b'abc'); u=start(m,t)['upload_id']
    chunk(u,b'abc',other,expected=404)
    finish(u,other,404)
    require(start(m,t)['offset']==0)
    chunk(u,b'abc',t); finish(u,t)
def wrong_hash():
    t=token(); m=meta(b'expected'); u=start(m,t)['upload_id']
    chunk(u,b'badbytes',t); finish(u,t,422)
    require(not sql('SELECT hash FROM media WHERE hash=?',(m['sha256'],)))
    require(not sql('SELECT hash FROM media_metadata WHERE hash=?',(m['sha256'],)))
    require(not sql('SELECT hash FROM thumbnail_jobs WHERE hash=?',(m['sha256'],)))
def resume():
    t=token(); data=os.urandom(CHUNK*2+123); m=meta(data,'resume.bin'); u=start(m,t)['upload_id']; chunk(u,data[:CHUNK],t); require(start(m,t)=={'upload_id':u,'offset':CHUNK}); chunk(u,b'x',t,0,409)
    # Close an incomplete HTTP body before its declared length.
    with socket.create_connection(('127.0.0.1',PORT),timeout=5) as s:
        s.sendall((f'POST /api/uploads/{u}/chunk HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer {t}\r\nUpload-Offset: {CHUNK}\r\nContent-Length: 100\r\n\r\n').encode()+b'partial'); s.shutdown(socket.SHUT_WR)
        while s.recv(4096): pass
    require(start(m,t)['offset']==CHUNK); chunk(u,data[CHUNK:2*CHUNK],t,CHUNK); chunk(u,data[2*CHUNK:],t,2*CHUNK); finish(u,t)
    p=sql('SELECT path FROM media WHERE hash=?',(m['sha256'],))[0][0]; require((app.DATA/p).read_bytes()==data)
def reserve():
    t=token(); u=start(meta(os.urandom(32)),t)['upload_id']; original=app.shutil.disk_usage
    try:
        app.shutil.disk_usage=lambda p: shutil._ntuple_diskusage(10**10,9*10**9,10**9)
        chunk(u,b'x',t,expected=507); require(not (app.DATA/'incomplete'/u).exists())
    finally: app.shutil.disk_usage=original

def slots():
    t=token(); app.SLOTS.acquire(); app.SLOTS.acquire()
    try: start(meta(b'busy'),t,503)
    finally: app.SLOTS.release(); app.SLOTS.release()
    start(meta(b'busy'),t)
def retention():
    t=token(); old=start(meta(os.urandom(20)),t)['upload_id']; fresh=start(meta(os.urandom(20)),t)['upload_id']; chunk(old,b'x',t); chunk(fresh,b'y',t)
    sql('UPDATE uploads SET updated=? WHERE id=?',(time.time()-90000,old)); start(meta(os.urandom(20)),t)
    require(not sql('SELECT id FROM uploads WHERE id=?',(old,))); require(not (app.DATA/'incomplete'/old).exists()); require((app.DATA/'incomplete'/fresh).read_bytes()==b'y')
def binary(path,t,expected=200,range_value=None):
    h={'Authorization':'Bearer '+t} if t else {}
    if range_value: h['Range']=range_value
    conn=http.client.HTTPConnection('127.0.0.1',PORT,timeout=30)
    try:
        conn.request('GET',path,headers=h); r=conn.getresponse(); data=r.read(); require(r.status==expected,f'HTTP {r.status}, expected {expected}'); return data,dict(r.getheaders())
    finally: conn.close()
def gallery_test():
    t=token(); d=req('GET','/api/device',token=t)['device_id']; data=os.urandom(32); m=meta(data,'gallery.bin','Unique folder'); upload(data,m,t)
    from urllib.parse import urlencode
    q=urlencode({'device':d,'folder':'Unique folder','from':'2024-08-15','to':'2024-08-15','limit':1})
    result=req('GET','/api/gallery?'+q,token=t); require(result['total']==1 and result['items'][0]['sha256']==m['sha256'])
    require(not req('GET','/api/gallery?'+q+'&page=2',token=t)['items'])
    all_items=req('GET','/api/gallery?limit=100',token=t)['items']; require(len({i['sha256'] for i in all_items})==len(all_items)); require([i['date'] for i in all_items]==sorted([i['date'] for i in all_items],reverse=True))
    require('Unique folder' in req('GET','/api/gallery/filters',token=t)['folders'])
    for query in ('limit=101','page=0','from=bad','from=2025-01-01&to=2024-01-01','limit=1&limit=2'):
        req('GET','/api/gallery?'+query,token=t,expected=400)
    req('GET','/api/gallery',expected=401)
    path='/api/media/'+m['sha256']; require(req('GET',path,token=t)['size']==len(data)); require(binary(path+'/download',t)[0]==data)
    binary(path+'/download',None,401); binary(path+'/stream',t,415); binary(path+'/thumbnail',t,404)
    req('GET','/api/media/'+'0'*64,token=t,expected=404)
def photo_test():
    t=token(); b=io.BytesIO(); Image.new('RGB',(800,400),(23,45,67)).save(b,'PNG'); data=b.getvalue()+os.urandom(12); m=meta(data,'photo.png'); upload(data,m,t); sha=m['sha256']
    while app.process_thumbnail(): pass
    path='/api/media/'+sha; detail=req('GET',path,token=t); require(detail['media_type']=='photo' and detail['width']==800 and detail['height']==400 and detail['thumbnail_ready'])
    thumb,_=binary(path+'/thumbnail',t); im=Image.open(io.BytesIO(thumb)); require(im.format=='JPEG' and im.size==(320,160)); require(binary(path+'/download',t)[0]==data)
    require(sql("SELECT COUNT(*) FROM thumbnail_jobs WHERE status='unsupported'")[0][0]>0)
def video_test():
    import subprocess
    p=app.ROOT/'sample.mp4'; subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=c=blue:s=640x360:r=10','-t','1','-c:v','mpeg4','-threads','1',str(p)],check=True,timeout=30)
    data=p.read_bytes(); t=token(); m=meta(data,'video.mp4'); upload(data,m,t)
    while app.process_thumbnail(): pass
    path='/api/media/'+m['sha256']; d=req('GET',path,token=t); require(d['media_type']=='video' and d['width']==640 and d['height']==360 and d['duration']>0)
    thumb,_=binary(path+'/thumbnail',t); require(Image.open(io.BytesIO(thumb)).size==(320,180))
    require(binary(path+'/stream',t)[0]==data); require(binary(path+'/download',t)[0]==data)
    for value,expected in [('bytes=0-99',data[:100]),('bytes=100-',data[100:]),('bytes=-50',data[-50:])]:
        body,h=binary(path+'/stream',t,206,value); require(body==expected and 'Content-Range' in h)
    for value in ('bytes=999999999-','bytes=5-2','bytes=0-1,4-5'):
        _,h=binary(path+'/stream',t,416,value); require(h['Content-Range']==f'bytes */{len(data)}')
def worker_test():
    t=token(); data=os.urandom(40); m=meta(data,'unsupported.bin'); upload(data,m,t); sha=m['sha256']; sql("UPDATE thumbnail_jobs SET status='processing',attempts=1 WHERE hash=?",(sha,))
    stop=threading.Event(); worker=threading.Thread(target=app.thumbnail_worker,args=(stop,)); worker.start()
    try:
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            if sql('SELECT status,attempts FROM thumbnail_jobs WHERE hash=?',(sha,))==[('unsupported',2)]: break
            time.sleep(.2)
        else: raise AssertionError('worker recovery timed out')
    finally: stop.set(); worker.join()

def trash_post(action,t,expected=200,**obj):
    return req('POST','/api/trash/'+action,obj,t,expected=expected)
def trash_items(t,sha):
    return [r for r in req('GET','/api/trash?limit=100',token=t)['items'] if r['sha256']==sha]
def trash_fixture():
    t=token(); t2=token(); data=os.urandom(80); m=meta(data,'trash.bin'); upload(data,m,t); start(m,t2)
    sha=m['sha256']; path=app.DATA/sql('SELECT path FROM media WHERE hash=?',(sha,))[0][0]
    return t,t2,m,sha,path

def trash_shared():
    t,t2,m,sha,path=trash_fixture(); detail=req('GET','/api/media/'+sha,token=t)
    ref=detail['references'][0]
    trash_post('delete',t,400,sha256=sha,scope='all')
    trash_post('delete',None,401,sha256=sha,scope='all',confirm=True)
    require(trash_post('delete',t,sha256=sha,scope='selected',references=[ref],confirm=True)['deleted']==1)
    items=trash_items(t2,sha); require(len(items)==1 and abs(items[0]['expires_at']-items[0]['deleted_at']-30*86400)<1)
    require(path.exists()); require(len(req('GET','/api/media/'+sha,token=t2)['references'])==1)
    trash_post('purge',t2,ids=[items[0]['id']],confirm=True); require(path.exists())
    trash_post('delete',t,sha256=sha,scope='all',confirm=True)
    req('GET','/api/media/'+sha,token=t,expected=404); require(path.exists())
    ids=[r['id'] for r in trash_items(t,sha)]; trash_post('restore',t,ids=ids,confirm=True)
    require(len(req('GET','/api/media/'+sha,token=t)['references'])==1)

def trash_rebackup():
    t,t2,m,sha,path=trash_fixture(); trash_post('delete',t,sha256=sha,scope='all',confirm=True)
    require(start(m,t)['complete']); ids=[r['id'] for r in trash_items(t,sha)]
    trash_post('restore',t,ids=ids,confirm=True)
    require(sql('SELECT COUNT(*) FROM media_refs WHERE hash=?',(sha,))==[(2,)])
    trash_post('delete',t,sha256=sha,scope='all',confirm=True)
    ids=[r['id'] for r in trash_items(t,sha)]; trash_post('purge',t,ids=ids[:1],confirm=True); require(path.exists())
    trash_post('purge',t,ids=ids[1:],confirm=True); require(not path.exists())
    for table in ('media','media_metadata','thumbnail_jobs','trash_refs'): require(not sql('SELECT hash FROM '+table+' WHERE hash=?',(sha,)))
    require(start(m,t)['offset']==0)

def trash_expiry():
    t,t2,m,sha,path=trash_fixture(); trash_post('delete',t,sha256=sha,scope='all',confirm=True)
    ids=[r['id'] for r in trash_items(t,sha)]
    sql('UPDATE trash_refs SET expires_at=? WHERE id=?',(time.time()-1,ids[0]))
    trash_post('restore',t,404,ids=[ids[0]],confirm=True)
    stop=threading.Event(); worker=threading.Thread(target=app.trash_worker,args=(stop,)); worker.start()
    try:
        deadline=time.monotonic()+10
        while sql('SELECT id FROM trash_refs WHERE id=?',(ids[0],)) and time.monotonic()<deadline: time.sleep(.1)
        require(not sql('SELECT id FROM trash_refs WHERE id=?',(ids[0],))); require(path.exists())
    finally: stop.set(); worker.join()
    trash_post('empty',t,confirm=True); require(not path.exists()); require(req('GET','/api/trash',token=t)['total']==0)
    req('GET','/api/trash',expected=401)

def trash_thumbnail():
    t=token(); b=io.BytesIO(); Image.new('RGB',(400,200)).save(b,'PNG'); data=b.getvalue()+os.urandom(12); m=meta(data,'trash.png'); upload(data,m,t); sha=m['sha256']
    while app.process_thumbnail(): pass
    path=app.DATA/sql('SELECT thumbnail_path FROM media_metadata WHERE hash=?',(sha,))[0][0]; require(path.exists())
    trash_post('delete',t,sha256=sha,scope='all',confirm=True); require(path.exists())
    trash_post('purge',t,ids=[r['id'] for r in trash_items(t,sha)],confirm=True); require(not path.exists())

def main():
    global app
    before=snapshot(); require(shutil.disk_usage(ROOT).free>3_100_000_000,'insufficient free space for tests')
    try:
        with tempfile.TemporaryDirectory(prefix='regression_',dir=ROOT) as tmp:
            p=Path(tmp); (p/'application').mkdir(); (p/'data').mkdir(); shutil.copy2(STAGE/'application/server.py',p/'application/server.py')
            with sqlite3.connect((STAGE/'data/pibackup.db').as_uri()+'?mode=ro',uri=True) as src, sqlite3.connect(p/'data/pibackup.db') as dst: src.backup(dst)
            shutil.copytree(STAGE/'data/originals',p/'data/originals'); shutil.copytree(STAGE/'data/incomplete',p/'data/incomplete'); shutil.copytree(STAGE/'data/thumbnails',p/'data/thumbnails')
            spec=importlib.util.spec_from_file_location('isolated_server',p/'application/server.py'); app=importlib.util.module_from_spec(spec); spec.loader.exec_module(app); require(app.ROOT==p); app.init()
            with app.ThreadingHTTPServer(('127.0.0.1',PORT),app.Handler) as server:
                thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
                try:
                    for name,fn in [('Repeated migration and record preservation',migration),('Authentication and revocation',auth),('Pairing lifecycle',pairing),('JPEG integrity, metadata, jobs, cross-device dedup and filename conflict',jpeg_test),('Invalid metadata and unauthorized requests',invalid_metadata),('Oversized chunk header rejection',oversized_chunk),('Cross-device upload ownership',ownership),('Incorrect SHA-256 rejection',wrong_hash),('Multi-chunk resume and interrupted body',resume),('Simulated disk reserve',reserve),('Simulated request slot saturation',slots),('Simulated retention expiry',retention),('Gallery filters, pagination and authorization',gallery_test),('Photo thumbnails and originals',photo_test),('Video thumbnails and HTTP ranges',video_test),('Background worker recovery',worker_test),('Shared reference deletion and restore',trash_shared),('Rebackup and last-reference purge',trash_rebackup),('Automatic expiry and empty trash',trash_expiry),('Thumbnail removal on purge',trash_thumbnail),('Final database integrity',integrity)]: check(name,fn)
                finally: server.shutdown(); thread.join()
    finally: check('Original file checksums unchanged',lambda:require(snapshot()==before))
    print(f'RESULT: {sum(ok for _,ok in results)}/{len(results)} groups passed')
    return 0 if all(ok for _,ok in results) else 1
if __name__=='__main__': raise SystemExit(main())
