#!/usr/bin/env python3
"""PiBackup phase 3.1: database migration and media metadata."""
import argparse
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
DB = DATA / 'pibackup.db'

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

@contextmanager
def database():
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=10)
    c.execute('PRAGMA foreign_keys = ON')
    try:
        with c:
            yield c
    finally:
        c.close()

def init():
    os.umask(0o077)
    with database() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS pairing (id INTEGER PRIMARY KEY CHECK(id=1), code_hash TEXT NOT NULL, expires REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS devices (id TEXT PRIMARY KEY, name TEXT NOT NULL, token_hash TEXT UNIQUE NOT NULL, created REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);''')
    DB.chmod(0o600)
    media_init()
    migrate_schema()

def pair():
    code = f'{secrets.randbelow(1000000):06d}'
    with database() as c:
        c.execute('BEGIN IMMEDIATE')
        old = c.execute('SELECT code_hash FROM pairing WHERE id=1').fetchone()
        while old and hmac.compare_digest(old[0], digest(code)):
            code = f'{secrets.randbelow(1000000):06d}'
        c.execute('INSERT OR REPLACE INTO pairing VALUES (1,?,?,0)', (digest(code), time.time()+300))
    print(f'Previous code invalidated.\nPairing code: {code}\nExpires in: 5 minutes')

def register(code, name):
    with database() as c:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute('SELECT code_hash,expires,attempts FROM pairing WHERE id=1').fetchone()
        if not row or row[1] <= time.time() or row[2] >= 5:
            return None
        if not hmac.compare_digest(row[0], digest(code)):
            c.execute('UPDATE pairing SET attempts=attempts+1 WHERE id=1')
            return None
        token, device = secrets.token_urlsafe(32), str(uuid.uuid4())
        c.execute('INSERT INTO devices VALUES (?,?,?,?,0)', (device,name,digest(token),time.time()))
        c.execute('DELETE FROM pairing WHERE id=1')
        return {'device_id':device,'token':token}

# Media API: serialized metadata and filesystem changes, two active requests.
import threading
import shutil
import re
from datetime import datetime, timezone

CHUNK = 4 * 1024**2
MAX_FILE = 20 * 1000**3
RESERVE = 3 * 1000**3
RETENTION = 86400
MEDIA_LOCK = threading.RLock()
SLOTS = threading.BoundedSemaphore(2)

class MediaError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message

def media_init():
    for folder in ('originals','incomplete','thumbnails'):
        (DATA / folder).mkdir(mode=0o700, exist_ok=True)
    with database() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS media (hash TEXT PRIMARY KEY, path TEXT UNIQUE NOT NULL, size INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS media_refs (device TEXT NOT NULL, hash TEXT NOT NULL, source TEXT NOT NULL, name TEXT NOT NULL, media_date TEXT NOT NULL, PRIMARY KEY(device,hash,source,name,media_date));
        CREATE TABLE IF NOT EXISTS uploads (id TEXT PRIMARY KEY, device TEXT NOT NULL, hash TEXT NOT NULL, size INTEGER NOT NULL, source TEXT NOT NULL, name TEXT NOT NULL, media_date TEXT NOT NULL, updated REAL NOT NULL);''')


def migrate_schema():
    with database() as c:
        version = c.execute(
            "PRAGMA user_version"
        ).fetchone()[0]

        if version == 1:
            return

        if version != 0:
            raise RuntimeError("Unsupported schema version")

        c.executescript("""
        BEGIN IMMEDIATE;

        CREATE TABLE media_metadata (
            hash TEXT PRIMARY KEY,
            media_type TEXT NOT NULL DEFAULT 'unknown',
            mime_type TEXT,
            width INTEGER,
            height INTEGER,
            duration REAL,
            thumbnail_path TEXT,
            FOREIGN KEY(hash) REFERENCES media(hash)
        );

        CREATE TABLE trash_refs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device TEXT NOT NULL,
            hash TEXT NOT NULL,
            source TEXT NOT NULL,
            name TEXT NOT NULL,
            media_date TEXT NOT NULL,
            deleted_by TEXT NOT NULL,
            deleted_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            FOREIGN KEY(hash) REFERENCES media(hash),
            FOREIGN KEY(device) REFERENCES devices(id),
            FOREIGN KEY(deleted_by) REFERENCES devices(id)
        );

        CREATE TABLE thumbnail_jobs (
            hash TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN (
                    'pending', 'processing', 'completed',
                    'failed', 'unsupported'
                )),
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            updated REAL NOT NULL,
            FOREIGN KEY(hash) REFERENCES media(hash)
        );

        CREATE INDEX idx_gallery_date
            ON media_refs(media_date DESC);

        CREATE INDEX idx_gallery_device
            ON media_refs(device, media_date DESC);

        CREATE INDEX idx_gallery_source
            ON media_refs(source, media_date DESC);

        CREATE INDEX idx_gallery_hash
            ON media_refs(hash);

        CREATE INDEX idx_trash_expiry
            ON trash_refs(expires_at);

        CREATE INDEX idx_trash_hash
            ON trash_refs(hash);

        CREATE INDEX idx_thumbnail_status
            ON thumbnail_jobs(status, updated);

        INSERT INTO media_metadata(hash)
            SELECT hash FROM media;

        INSERT INTO thumbnail_jobs(hash, updated)
            SELECT hash, strftime('%s','now') FROM media;

        PRAGMA user_version = 1;

        COMMIT;
        """)

def cleanup(c):
    for (uid,) in c.execute('SELECT id FROM uploads WHERE updated < ?', (time.time()-RETENTION,)).fetchall():
        (DATA/'incomplete'/uid).unlink(missing_ok=True)
        c.execute('DELETE FROM uploads WHERE id=?',(uid,))

def media_date(obj):
    for key in ('capture_date','modified_date'):
        try:
            d = datetime.fromisoformat(obj.get(key,''))
            if 1900 <= d.year <= datetime.now().year+1: return d.date().isoformat()
        except (ValueError,TypeError): pass
    return datetime.now(timezone.utc).date().isoformat()

def add_ref(c, device, sha, source, name, date):
    c.execute(
        'INSERT OR IGNORE INTO media_metadata(hash) VALUES (?)',
        (sha,)
    )
    c.execute(
        'INSERT OR IGNORE INTO thumbnail_jobs(hash, updated) VALUES (?,?)',
        (sha, time.time())
    )
    c.execute('INSERT OR IGNORE INTO media_refs VALUES (?,?,?,?,?)',(device,sha,source,name,date))

def start_upload(c, device, obj):
    sha,size,name,source = (obj.get(k) for k in ('sha256','size','name','source'))
    if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha) or type(size) is not int or not 0<size<=MAX_FILE:
        raise MediaError(400,'invalid hash or size')
    if not isinstance(name,str) or not name or name in ('.','..') or any(x in name for x in ('/','\\','\x00')) or len(name.encode())>220 or not isinstance(source,str) or not 0<len(source)<=1024:
        raise MediaError(400,'invalid name or source')
    date=media_date(obj)
    row=c.execute('SELECT path,size FROM media WHERE hash=?',(sha,)).fetchone()
    if row:
        if row[1]!=size or not (DATA/row[0]).is_file(): raise MediaError(409,'stored media mismatch')
        add_ref(c,device,sha,source,name,date)
        return {'complete':True,'sha256':sha}
    row=c.execute('SELECT id FROM uploads WHERE device=? AND hash=? AND size=? AND source=? AND name=? AND media_date=?',(device,sha,size,source,name,date)).fetchone()
    if row:
        uid=row[0]; path=DATA/'incomplete'/uid
        c.execute('UPDATE uploads SET updated=? WHERE id=?',(time.time(),uid))
        return {'upload_id':uid,'offset':path.stat().st_size if path.exists() else 0}
    uid=uuid.uuid4().hex
    c.execute('INSERT INTO uploads VALUES (?,?,?,?,?,?,?,?)',(uid,device,sha,size,source,name,date,time.time()))
    return {'upload_id':uid,'offset':0}

def upload_row(c, device, uid):
    row=c.execute('SELECT hash,size,source,name,media_date FROM uploads WHERE id=? AND device=?',(uid,device)).fetchone()
    if not row: raise MediaError(404,'upload not found')
    return row

def finish_upload(c,device,uid):
    sha,size,source,name,date=upload_row(c,device,uid)
    path=DATA/'incomplete'/uid
    if not path.exists() or path.stat().st_size!=size: raise MediaError(409,'upload incomplete')
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''): h.update(block)
    if h.hexdigest()!=sha: raise MediaError(422,'hash mismatch')
    row=c.execute('SELECT path,size FROM media WHERE hash=?',(sha,)).fetchone()
    if row:
        if row[1]!=size or not (DATA/row[0]).is_file(): raise MediaError(409,'stored media mismatch')
    else:
        folder=DATA/'originals'/date[:4]/date[5:7]; folder.mkdir(parents=True,exist_ok=True)
        target=folder/name; stem,suffix=Path(name).stem,Path(name).suffix
        n=0
        while True:
            try: os.link(path,target); break
            except FileExistsError:
                n+=1; target=folder/(stem+'_'+sha[:8]+('' if n==1 else '_'+str(n))+suffix)
        c.execute('INSERT INTO media VALUES (?,?,?)',(sha,str(target.relative_to(DATA)),size))
    add_ref(c,device,sha,source,name,date)
    c.execute('DELETE FROM uploads WHERE id=?',(uid,))
    c.commit()
    path.unlink(missing_ok=True)
    return {'complete':True,'sha256':sha}



# Phase 3.2–3.4 media access
import io
import mimetypes
import subprocess
from urllib.parse import urlsplit, parse_qs, quote
from PIL import Image, ImageOps, UnidentifiedImageError

PHOTO_FORMATS={'JPEG':'image/jpeg','PNG':'image/png','GIF':'image/gif','WEBP':'image/webp','BMP':'image/bmp','TIFF':'image/tiff'}
VIDEO_EXT={'.mp4': 'video/mp4', '.mov':'video/quicktime', '.m4v':'video/mp4', '.webm':'video/webm', '.mkv':'video/x-matroska', '.avi':'video/x-msvideo', '.3gp':'video/3gpp'}

def safe_path(relative, folder):
    path=(DATA/relative).resolve()
    if not path.is_relative_to((DATA/folder).resolve()):
        raise MediaError(500,'invalid stored path')
    return path

def thumbnail_info(path):
    try:
        with Image.open(path) as im:
            mime=PHOTO_FORMATS.get(im.format)
            if not mime: return None
            im=ImageOps.exif_transpose(im)
            width,height=im.size
            im.thumbnail((320,320))
            out=io.BytesIO(); im.convert('RGB').save(out,'JPEG',quality=80)
            return ('photo',mime,width,height,None,out.getvalue())
    except UnidentifiedImageError:
        pass
    mime=VIDEO_EXT.get(path.suffix.lower())
    if not mime: return None
    probe=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height:format=duration','-of','json',str(path)],capture_output=True,check=True,timeout=30)
    info=json.loads(probe.stdout); streams=info.get('streams',[])
    if not streams: return None
    stream=streams[0]; duration=info.get('format',{}).get('duration')
    frame=subprocess.run(['ffmpeg','-nostdin','-v','error','-threads','1','-i',str(path),'-map','0:v:0','-frames:v','1','-vf','scale=320:320:force_original_aspect_ratio=decrease','-threads','1','-f','image2pipe','-vcodec','mjpeg','pipe:1'],capture_output=True,check=True,timeout=60)
    with Image.open(io.BytesIO(frame.stdout)) as im:
        out=io.BytesIO(); im.convert('RGB').save(out,'JPEG',quality=80)
    return ('video',mime,stream['width'],stream['height'],float(duration) if duration not in (None,'N/A') else None,out.getvalue())

def process_thumbnail():
    with MEDIA_LOCK:
        return _process_thumbnail()

def _process_thumbnail():
    with database() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute("SELECT j.hash,m.path FROM thumbnail_jobs j JOIN media m ON m.hash=j.hash WHERE j.attempts<3 AND (j.status='pending' OR (j.status='failed' AND j.updated<?)) ORDER BY j.updated,j.hash LIMIT 1",(time.time()-30,)).fetchone()
        if not row: return False
        sha,relative=row
        c.execute("UPDATE thumbnail_jobs SET status='processing',attempts=attempts+1,updated=? WHERE hash=?",(time.time(),sha))
    temp=None
    try:
        info=thumbnail_info(safe_path(relative,'originals'))
        with database() as c:
            if info is None:
                c.execute("UPDATE thumbnail_jobs SET status='unsupported',updated=? WHERE hash=?",(time.time(),sha))
            else:
                kind,mime,w,h,duration,payload=info
                if shutil.disk_usage(DATA).free-len(payload)<RESERVE: raise OSError('storage reserve')
                target=DATA/'thumbnails'/(sha+'.jpg'); temp=target.with_suffix('.tmp')
                temp.write_bytes(payload); os.replace(temp,target)
                c.execute('UPDATE media_metadata SET media_type=?,mime_type=?,width=?,height=?,duration=?,thumbnail_path=? WHERE hash=?',(kind,mime,w,h,duration,str(target.relative_to(DATA)),sha))
                c.execute("UPDATE thumbnail_jobs SET status='completed',last_error=NULL,updated=? WHERE hash=?",(time.time(),sha))
    except Exception as e:
        if temp: temp.unlink(missing_ok=True)
        with database() as c:
            c.execute("UPDATE thumbnail_jobs SET status='failed',last_error=?,updated=? WHERE hash=?",(type(e).__name__,time.time(),sha))
    return True

def thumbnail_worker(stop):
    with database() as c:
        c.execute("UPDATE thumbnail_jobs SET status=CASE WHEN attempts>=3 THEN 'failed' ELSE 'pending' END WHERE status='processing'")
    while not stop.is_set():
        try:
            if process_thumbnail(): continue
        except (OSError,sqlite3.Error): pass
        stop.wait(1)

def gallery(c, query):
    allowed={'device','folder','from','to','page','limit'}
    if set(query)-allowed or any(len(v)!=1 for v in query.values()): raise MediaError(400,'invalid filters')
    q={k:v[0] for k,v in query.items()}
    page=int(q.get('page','1')); limit=int(q.get('limit','50'))
    if not 1<=page<=1000000 or not 1<=limit<=100: raise MediaError(400,'invalid pagination')
    clauses=[]; args=[]
    for key,column,op in [('device','device','='),('folder','source','='),('from','media_date','>='),('to','media_date','<=')]:
        if key in q:
            if key in ('from','to') and datetime.strptime(q[key],'%Y-%m-%d').date().isoformat()!=q[key]: raise MediaError(400,'invalid date')
            clauses.append('r.'+column+op+'?'); args.append(q[key])
    if q.get('from','')>q.get('to','9999'): raise MediaError(400,'invalid date range')
    where=' WHERE '+' AND '.join(clauses) if clauses else ''
    base=' FROM media_refs r'+where
    total=c.execute('SELECT COUNT(DISTINCT r.hash)'+base,args).fetchone()[0]
    rows=c.execute('SELECT r.hash,MAX(r.media_date)'+base+' GROUP BY r.hash ORDER BY MAX(r.media_date) DESC,r.hash LIMIT ? OFFSET ?',args+[limit,(page-1)*limit]).fetchall()
    return {'items':[media_detail(c,sha,date) for sha,date in rows],'page':page,'limit':limit,'total':total}

def media_detail(c,sha,date=None):
    row=c.execute('SELECT m.size,x.media_type,x.mime_type,x.width,x.height,x.duration,x.thumbnail_path,j.status FROM media m JOIN media_metadata x ON x.hash=m.hash JOIN thumbnail_jobs j ON j.hash=m.hash WHERE m.hash=? AND EXISTS(SELECT 1 FROM media_refs WHERE hash=m.hash)',(sha,)).fetchone()
    if not row: raise MediaError(404,'media not found')
    refs=[dict(zip(('device','device_name','folder','name','date'),r)) for r in c.execute('SELECT r.device,d.name,r.source,r.name,r.media_date FROM media_refs r JOIN devices d ON d.id=r.device WHERE r.hash=? ORDER BY r.media_date DESC,r.device,r.source,r.name',(sha,))]
    size,kind,mime,w,h,duration,thumb,status=row
    return dict(sha256=sha,size=size,media_type=kind,mime_type=mime,width=w,height=h,duration=duration,thumbnail_ready=bool(thumb),thumbnail_status=status,date=date or refs[0]['date'],name=refs[0]['name'],references=refs)

def byte_range(value,size):
    if not value: return 0,size-1,200
    match=re.fullmatch(r'bytes=(\d*)-(\d*)',value)
    if not match or size<=0: raise MediaError(416,'invalid range')
    a,b=match.groups()
    if not a:
        if not b or int(b)<=0: raise MediaError(416,'invalid range')
        return max(0,size-int(b)),size-1,206
    start=int(a); end=min(size-1,int(b)) if b else size-1
    if start>=size or end<start: raise MediaError(416,'invalid range')
    return start,end,206



# Phase 3.5–3.6 recycle bin
TRASH_RETENTION=30*86400

def trash_purge(c, ids=None, expired=False):
    if expired:
        rows=c.execute('SELECT id,hash FROM trash_refs WHERE expires_at<=?',(time.time(),)).fetchall()
    elif ids is None:
        rows=c.execute('SELECT id,hash FROM trash_refs').fetchall()
    else:
        rows=[]
        for i in ids:
            row=c.execute('SELECT id,hash FROM trash_refs WHERE id=?',(i,)).fetchone()
            if not row: raise MediaError(404,'trash reference not found')
            rows.append(row)
    c.executemany('DELETE FROM trash_refs WHERE id=?',[(i,) for i,_ in rows])
    paths=[]
    for sha in {h for _,h in rows}:
        if c.execute('SELECT 1 FROM media_refs WHERE hash=? UNION ALL SELECT 1 FROM trash_refs WHERE hash=?',(sha,sha)).fetchone(): continue
        row=c.execute('SELECT m.path,x.thumbnail_path FROM media m JOIN media_metadata x ON x.hash=m.hash WHERE m.hash=?',(sha,)).fetchone()
        if not row: raise MediaError(500,'missing media metadata')
        paths.append(safe_path(row[0],'originals'))
        if row[1]: paths.append(safe_path(row[1],'thumbnails'))
        for table in ('thumbnail_jobs','media_metadata','media'):
            c.execute('DELETE FROM '+table+' WHERE hash=?',(sha,))
    # Commit before unlink: never leave a recoverable reference pointing to a deleted file.
    c.commit()
    failures=0
    for path in paths:
        try: path.unlink(missing_ok=True)
        except OSError: failures+=1
    return {'purged':len(rows),'physical_files':len(paths)-failures,'unlink_errors':failures}

def trash_cleanup():
    with MEDIA_LOCK, database() as c:
        c.execute('BEGIN IMMEDIATE')
        return trash_purge(c,expired=True)

def trash_worker(stop):
    while not stop.is_set():
        try:
            result=trash_cleanup()
            if result['unlink_errors']: print('Trash cleanup: filesystem removal failed',flush=True)
        except (OSError,sqlite3.Error,MediaError): print('Trash cleanup failed',flush=True)
        stop.wait(60)

def trash_ids(obj):
    ids=obj.get('ids')
    if not isinstance(ids,list) or not 1<=len(ids)<=100 or any(type(i) is not int or not 0<i<2**63 for i in ids) or len(set(ids))!=len(ids): raise MediaError(400,'invalid trash ids')
    return ids

def trash_action(c,device,path,obj):
    if obj.get('confirm') is not True: raise MediaError(400,'confirmation required')
    if path=='/api/trash/delete':
        sha=obj.get('sha256'); scope=obj.get('scope')
        if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha): raise MediaError(400,'invalid hash')
        rows=c.execute('SELECT device,hash,source,name,media_date FROM media_refs WHERE hash=?',(sha,)).fetchall()
        if scope=='selected':
            refs=obj.get('references')
            if not isinstance(refs,list) or not 1<=len(refs)<=100: raise MediaError(400,'invalid references')
            selected=[]
            for ref in refs:
                if not isinstance(ref,dict) or any(not isinstance(ref.get(k),str) for k in ('device','folder','name','date')): raise MediaError(400,'invalid reference')
                row=(ref['device'],sha,ref['folder'],ref['name'],ref['date'])
                if row not in rows: raise MediaError(404,'reference not found')
                if row not in selected: selected.append(row)
            rows=selected
        elif scope!='all': raise MediaError(400,'invalid scope')
        if not rows: raise MediaError(404,'media not found')
        now=time.time()
        c.executemany('INSERT INTO trash_refs(device,hash,source,name,media_date,deleted_by,deleted_at,expires_at) VALUES (?,?,?,?,?,?,?,?)',[r+(device,now,now+TRASH_RETENTION) for r in rows])
        c.executemany('DELETE FROM media_refs WHERE device=? AND hash=? AND source=? AND name=? AND media_date=?',rows)
        return {'deleted':len(rows)}
    if path=='/api/trash/restore':
        ids=trash_ids(obj); rows=[]
        for i in ids:
            row=c.execute('SELECT device,hash,source,name,media_date FROM trash_refs WHERE id=? AND expires_at>?',(i,time.time())).fetchone()
            if not row: raise MediaError(404,'recoverable reference not found')
            rows.append(row)
        c.executemany('INSERT OR IGNORE INTO media_refs VALUES (?,?,?,?,?)',rows)
        c.executemany('DELETE FROM trash_refs WHERE id=?',[(i,) for i in ids])
        return {'restored':len(ids)}
    if path=='/api/trash/purge': return trash_purge(c,trash_ids(obj))
    if path=='/api/trash/empty': return trash_purge(c)
    raise MediaError(404,'not found')


class Handler(BaseHTTPRequestHandler):
    def trash_request(self,write=False):
        try:
            url=urlsplit(self.path)
            auth=self.headers.get('Authorization','')
            with database() as c:
                row=c.execute('SELECT id FROM devices WHERE token_hash=? AND revoked=0',(digest(auth[7:]),)).fetchone() if auth.startswith('Bearer ') else None
            if not row: raise MediaError(401,'unauthorized')
            device=row[0]
            if write:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=65536: raise MediaError(400,'invalid length')
                raw=self.rfile.read(length)
                if len(raw)!=length: raise MediaError(400,'incomplete request')
                obj=json.loads(raw)
                if not isinstance(obj,dict): raise MediaError(400,'invalid body')
                with MEDIA_LOCK,database() as c:
                    c.execute('BEGIN IMMEDIATE')
                    if not c.execute('SELECT 1 FROM devices WHERE id=? AND revoked=0',(device,)).fetchone(): raise MediaError(401,'unauthorized')
                    result=trash_action(c,device,url.path,obj)
            else:
                if url.path!='/api/trash': raise MediaError(404,'not found')
                q=parse_qs(url.query,keep_blank_values=True,max_num_fields=2)
                if set(q)-{'page','limit'} or any(len(v)!=1 for v in q.values()): raise MediaError(400,'invalid pagination')
                page=int(q.get('page',['1'])[0]); limit=int(q.get('limit',['50'])[0])
                if not 1<=page<=1000000 or not 1<=limit<=100: raise MediaError(400,'invalid pagination')
                with database() as c:
                    c.execute('BEGIN')
                    now=time.time()
                    total=c.execute('SELECT COUNT(*) FROM trash_refs WHERE expires_at>?',(now,)).fetchone()[0]
                    rows=c.execute('SELECT id,device,hash,source,name,media_date,deleted_by,deleted_at,expires_at FROM trash_refs WHERE expires_at>? ORDER BY deleted_at DESC,id DESC LIMIT ? OFFSET ?',(now,limit,(page-1)*limit))
                    result={'items':[dict(zip(('id','device','sha256','folder','name','date','deleted_by','deleted_at','expires_at'),r)) for r in rows],'total':total,'page':page,'limit':limit}
            self.reply(200,result)
        except MediaError as e: self.reply(e.status,{'error':e.message})
        except (ValueError,TypeError,TimeoutError): self.reply(400,{'error':'invalid request'})
        except (OSError,sqlite3.Error): self.reply(500,{'error':'storage operation failed'})

    def media_get(self):
        try:
            url=urlsplit(self.path)
            with database() as c:
                auth=self.headers.get('Authorization','')
                if not auth.startswith('Bearer ') or not c.execute('SELECT 1 FROM devices WHERE token_hash=? AND revoked=0',(digest(auth[7:]),)).fetchone(): raise MediaError(401,'unauthorized')
                if url.path=='/api/gallery': return self.reply(200,gallery(c,parse_qs(url.query,keep_blank_values=True,max_num_fields=12)))
                if url.path=='/api/gallery/filters':
                    return self.reply(200,{'devices':[{'id':i,'name':n} for i,n in c.execute('SELECT DISTINCT d.id,d.name FROM devices d JOIN media_refs r ON r.device=d.id ORDER BY d.name,d.id')],'folders':[r[0] for r in c.execute('SELECT DISTINCT source FROM media_refs ORDER BY source')]})
                match=re.fullmatch(r'/api/media/([0-9a-f]{64})(?:/(thumbnail|download|stream))?',url.path)
                if not match: raise MediaError(404,'not found')
                sha,action=match.groups(); detail=media_detail(c,sha)
                if not action: return self.reply(200,detail)
                if action=='thumbnail':
                    relative=c.execute('SELECT thumbnail_path FROM media_metadata WHERE hash=?',(sha,)).fetchone()[0]
                    if not relative: raise MediaError(404,'thumbnail unavailable')
                    path=safe_path(relative,'thumbnails'); mime='image/jpeg'
                else:
                    if action=='stream' and detail['media_type']!='video': raise MediaError(415,'not a recognized video')
                    path=safe_path(c.execute('SELECT path FROM media WHERE hash=?',(sha,)).fetchone()[0],'originals')
                    mime=detail['mime_type'] or 'application/octet-stream'
            if not path.is_file(): raise MediaError(404,'file unavailable')
            with path.open('rb') as f:
                size=os.fstat(f.fileno()).st_size
                try: start,end,status=byte_range(self.headers.get('Range'),size)
                except MediaError:
                    self.send_response(416); self.send_header('Content-Range',f'bytes */{size}'); self.send_header('Content-Length','0'); self.end_headers(); return
                self.send_response(status); self.send_header('Content-Type',mime); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Accept-Ranges','bytes'); self.send_header('Content-Length',str(end-start+1))
                if status==206: self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                if action=='download': self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+quote(detail['name'],safe=''))
                self.end_headers(); f.seek(start); remaining=end-start+1
                while remaining:
                    block=f.read(min(1024**2,remaining))
                    if not block: break
                    self.wfile.write(block); remaining-=len(block)
        except MediaError as e: self.reply(e.status,{'error':e.message})
        except (ValueError,TypeError): self.reply(400,{'error':'invalid request'})
        except (BrokenPipeError,ConnectionResetError,TimeoutError): pass
        except (OSError,sqlite3.Error): self.reply(500,{'error':'storage operation failed'})

    def setup(self):
        super().setup()
        self.connection.settimeout(10)
    def reply(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, fmt, *args):
        pass  # Do not log URLs or credentials.
    def do_GET(self):
        if urlsplit(self.path).path=='/api/trash': return self.trash_request()
        if self.path.startswith(('/api/gallery','/api/media/')): return self.media_get()
        if self.path == '/api/health':
            return self.reply(200, {'status':'ok','phase':3,'schema_version':1})
        if self.path == '/api/storage':
            try:
                auth = self.headers.get('Authorization','')
                with database() as c:
                    if not auth.startswith('Bearer ') or not c.execute('SELECT 1 FROM devices WHERE token_hash=? AND revoked=0',(digest(auth[7:]),)).fetchone():
                        return self.reply(401, {'error':'unauthorized'})
                    count, stored = c.execute('SELECT COUNT(*), COALESCE(SUM(size),0) FROM media').fetchone()
                disk = shutil.disk_usage(DATA)
                return self.reply(200, dict(total_bytes=disk.total, used_bytes=disk.used, free_bytes=disk.free, reserve_bytes=RESERVE, available_backup_bytes=max(0,disk.free-RESERVE), stored_media_bytes=stored, stored_media_count=count))
            except (OSError,sqlite3.Error):
                return self.reply(500, {'error':'storage operation failed'})
        if self.path == '/api/device':
            auth = self.headers.get('Authorization','')
            with database() as c:
                row = c.execute('SELECT id,name FROM devices WHERE token_hash=? AND revoked=0',(digest(auth[7:]),)).fetchone() if auth.startswith('Bearer ') else None
            return self.reply(200, {'device_id':row[0],'name':row[1]}) if row else self.reply(401,{'error':'unauthorized'})
        self.reply(404,{'error':'not found'})
    def media_request(self):
        if not SLOTS.acquire(blocking=False): return self.reply(503,{'error':'busy; retry'})
        try:
            auth=self.headers.get('Authorization','')
            with database() as c:
                row=c.execute('SELECT id FROM devices WHERE token_hash=? AND revoked=0',(digest(auth[7:]),)).fetchone() if auth.startswith('Bearer ') else None
            if not row: raise MediaError(401,'unauthorized')
            device=row[0]
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=CHUNK: raise MediaError(400,'invalid length')
            body=self.rfile.read(length)
            if len(body)!=length: raise MediaError(400,'incomplete request')
            with MEDIA_LOCK, database() as c:
                c.execute('BEGIN IMMEDIATE')
                if not c.execute('SELECT 1 FROM devices WHERE id=? AND revoked=0',(device,)).fetchone(): raise MediaError(401,'unauthorized')
                cleanup(c)
                if self.path=='/api/uploads/start':
                    if length>16384: raise MediaError(400,'metadata too large')
                    obj=json.loads(body)
                    if not isinstance(obj,dict): raise MediaError(400,'invalid metadata')
                    result=start_upload(c,device,obj)
                else:
                    match=re.fullmatch(r'/api/uploads/([0-9a-f]{32})/(chunk|finish)',self.path)
                    if not match: raise MediaError(404,'not found')
                    uid,action=match.groups()
                    if action=='finish': result=finish_upload(c,device,uid)
                    else:
                        sha,size,*_=upload_row(c,device,uid)
                        path=DATA/'incomplete'/uid
                        offset=path.stat().st_size if path.exists() else 0
                        if int(self.headers.get('Upload-Offset','-1'))!=offset: raise MediaError(409,'offset mismatch; call start again')
                        if offset+length>size: raise MediaError(400,'chunk exceeds file size')
                        if shutil.disk_usage(DATA).free-length<RESERVE: raise MediaError(507,'insufficient storage')
                        with path.open('ab') as f:
                            try:
                                f.write(body); f.flush(); os.fsync(f.fileno())
                            except OSError:
                                f.truncate(offset); raise
                        c.execute('UPDATE uploads SET updated=? WHERE id=?',(time.time(),uid))
                        result={'offset':offset+length}
            self.reply(200,result)
        except MediaError as e: self.reply(e.status,{'error':e.message})
        except (ValueError,TypeError,TimeoutError): self.reply(400,{'error':'invalid request'})
        except (OSError,sqlite3.Error): self.reply(500,{'error':'storage operation failed'})
        finally: SLOTS.release()
    def do_POST(self):
        if self.path == '/api/device/revoke':
            try:
                auth=self.headers.get('Authorization','')
                if not auth.startswith('Bearer '): return self.reply(401,{'error':'unauthorized'})
                with database() as c:
                    result=c.execute('UPDATE devices SET revoked=1 WHERE token_hash=? AND revoked=0',(digest(auth[7:]),))
                    changed=result.rowcount
                return self.reply(200,{'revoked':True}) if changed else self.reply(401,{'error':'unauthorized'})
            except (OSError,sqlite3.Error): return self.reply(500,{'error':'storage operation failed'})

        if self.path.startswith('/api/trash/'): return self.trash_request(True)
        if self.path.startswith('/api/uploads/'): return self.media_request()
        if self.path != '/api/pair':
            return self.reply(404,{'error':'not found'})
        try:
            length = int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 4096: raise ValueError()
            obj = json.loads(self.rfile.read(length))
            code,name = obj['code'],obj['name']
            if not isinstance(code,str) or len(code)!=6 or not code.isascii() or not code.isdigit() or not isinstance(name,str) or not 0<len(name.strip())<=100: raise ValueError()
        except (ValueError,KeyError,TypeError,TimeoutError):
            return self.reply(400,{'error':'invalid request'})
        result = register(code,name.strip())
        self.reply(201,result) if result else self.reply(403,{'error':'invalid or expired pairing code'})

def main():
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['init','serve','pair','devices','revoke'])
    p.add_argument('device_id',nargs='?')
    p.add_argument('--port',type=int,default=8092)
    a=p.parse_args()
    init()
    if a.command=='serve':
        stop=threading.Event()
        with ThreadingHTTPServer(('127.0.0.1',a.port),Handler) as httpd:
            worker=threading.Thread(target=thumbnail_worker,args=(stop,),daemon=True)
            worker.start()
            cleaner=threading.Thread(target=trash_worker,args=(stop,),daemon=True)
            cleaner.start()
            try: httpd.serve_forever()
            finally: stop.set(); worker.join(); cleaner.join()
    elif a.command=='pair': pair()
    elif a.command=='devices':
        with database() as c:
            for row in c.execute('SELECT id,name,revoked FROM devices'):
                print(row[0],json.dumps(row[1]),'revoked' if row[2] else 'active')
    elif a.command=='revoke':
        if not a.device_id: p.error('device ID required')
        with database() as c:
            result=c.execute('UPDATE devices SET revoked=1 WHERE id=?',(a.device_id,))
            print('Revoked' if result.rowcount else 'Device not found')

if __name__=='__main__': main()
