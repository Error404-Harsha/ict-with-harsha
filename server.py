from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote
from http.cookies import SimpleCookie
import json, sqlite3, hashlib, secrets, hmac, re, sys, os, base64

ROOT=Path(__file__).resolve().parent; DB=ROOT/'ict_with_harsha.db'
PROFILE={"name":"Harsha Madushan","title":"BICT (Honours) Graduate & ICT Educator","email":"harshamaduushan@gmail.com","phone":"0788523755","location":"Sri Lanka","bio":"Bachelor of Information and Communication Technology Honours (BICT) graduate from Uva Wellassa University, with professional experience at Michelin and practical experience in analytics, software and machine learning.","linkedin":"https://www.linkedin.com/in/swhmadushan"}
COURSES=[('O/L ICT Complete','Grade 6–11','Full syllabus theory, practical lessons and exam preparation.'),('A/L ICT Complete','Grade 12–13','Theory, Python, databases and structured paper practice.'),('Online ICT Classes','Online','Interactive online ICT lessons, revision, recordings and model-paper discussions.')]
def db(): c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def password_hash(password,salt=None):
    salt=salt or secrets.token_hex(16); digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),200000).hex();return f'{salt}${digest}'
def verify(password,stored):
    try:salt,digest=stored.split('$');return hmac.compare_digest(password_hash(password,salt).split('$')[1],digest)
    except:return False
def init():
  with db() as c:
    c.executescript('''CREATE TABLE IF NOT EXISTS profile(id INTEGER PRIMARY KEY CHECK(id=1),name TEXT,title TEXT,email TEXT,phone TEXT,location TEXT,bio TEXT,linkedin TEXT,photo_path TEXT DEFAULT 'assets/harsha-profile.jpg',updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS enquiries(id INTEGER PRIMARY KEY AUTOINCREMENT,student_name TEXT NOT NULL,phone TEXT NOT NULL,email TEXT,class_name TEXT NOT NULL,message TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('admin','student')),phone TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER NOT NULL,expires_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,level TEXT,description TEXT,active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS enrollments(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,course_id INTEGER NOT NULL,progress INTEGER DEFAULT 0,status TEXT DEFAULT 'active',UNIQUE(user_id,course_id));
    CREATE TABLE IF NOT EXISTS learning_resources(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,course_id INTEGER,type TEXT,url TEXT,description TEXT);
    CREATE TABLE IF NOT EXISTS announcements(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,body TEXT NOT NULL,target_stream TEXT DEFAULT 'ALL',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS notification_reads(user_id INTEGER NOT NULL,announcement_id INTEGER NOT NULL,read_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(user_id,announcement_id));''')
    c.executescript('''CREATE TABLE IF NOT EXISTS materials(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,filename TEXT NOT NULL UNIQUE,category TEXT DEFAULT 'A/L ICT',description TEXT,visible INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS subscriptions(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS site_content(content_key TEXT PRIMARY KEY,content_value TEXT NOT NULL,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS class_sessions(id INTEGER PRIMARY KEY AUTOINCREMENT,course_type TEXT NOT NULL,title TEXT NOT NULL,session_date TEXT,time_text TEXT,location TEXT,description TEXT,visible INTEGER DEFAULT 1);''')
    columns=[x['name'] for x in c.execute('PRAGMA table_info(users)')]
    if 'username' not in columns:c.execute('ALTER TABLE users ADD COLUMN username TEXT')
    if 'active' not in columns:c.execute('ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1')
    if 'student_stream' not in columns:c.execute("ALTER TABLE users ADD COLUMN student_stream TEXT DEFAULT 'O/L'")
    if 'profile_photo' not in columns:c.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT")
    profile_columns=[x['name'] for x in c.execute('PRAGMA table_info(profile)')]
    if 'photo_path' not in profile_columns:c.execute("ALTER TABLE profile ADD COLUMN photo_path TEXT DEFAULT 'assets/harsha-profile.jpg'")
    announcement_columns=[x['name'] for x in c.execute('PRAGMA table_info(announcements)')]
    if 'target_stream' not in announcement_columns:c.execute("ALTER TABLE announcements ADD COLUMN target_stream TEXT DEFAULT 'ALL'")
    if not c.execute('SELECT id FROM profile WHERE id=1').fetchone():c.execute('INSERT INTO profile(id,name,title,email,phone,location,bio,linkedin) VALUES(1,:name,:title,:email,:phone,:location,:bio,:linkedin)',PROFILE)
    else:c.execute('UPDATE profile SET title=?,bio=?,email=?,phone=? WHERE id=1', (PROFILE['title'],PROFILE['bio'],PROFILE['email'],PROFILE['phone']))
    if not c.execute('SELECT id FROM users WHERE email=?',('admin@ictwithharsha.lk',)).fetchone():c.execute('INSERT INTO users(name,email,password_hash,role,phone) VALUES(?,?,?,?,?)',('Harsha Madushan','admin@ictwithharsha.lk',password_hash('Harsha@2026'),'admin','+94 77 000 0000'))
    if not c.execute('SELECT id FROM users WHERE email=?',('student@example.com',)).fetchone():c.execute('INSERT INTO users(name,email,password_hash,role,phone) VALUES(?,?,?,?,?)',('Nethmi Perera','student@example.com',password_hash('Student@2026'),'student','0771234567'))
    c.execute("UPDATE users SET username='harsha' WHERE email='admin@ictwithharsha.lk'")
    c.execute("UPDATE users SET username=COALESCE(username,'student') WHERE email='student@example.com'")
    c.execute("UPDATE users SET active=1 WHERE email='student@example.com'")
    c.execute("UPDATE users SET student_stream=COALESCE(student_stream,'O/L') WHERE role='student'")
    if not c.execute('SELECT id FROM courses').fetchone():c.executemany('INSERT INTO courses(title,level,description) VALUES(?,?,?)',COURSES)
    student=c.execute('SELECT id FROM users WHERE email=?',('student@example.com',)).fetchone();course=c.execute('SELECT id FROM courses ORDER BY id LIMIT 1').fetchone();c.execute('INSERT OR IGNORE INTO enrollments(user_id,course_id,progress) VALUES(?,?,?)',(student['id'],course['id'],35))
    if not c.execute('SELECT id FROM learning_resources').fetchone():c.execute('INSERT INTO learning_resources(title,course_id,type,url,description) VALUES(?,?,?,?,?)',('ICT Syllabus Checklist',course['id'],'PDF','#','Track every lesson before your examination.'))
    if not c.execute('SELECT id FROM announcements').fetchone():c.execute('INSERT INTO announcements(title,body) VALUES(?,?)',('Welcome to ICT with Harsha','Your student portal is ready. Check your course and learning resources.'))
    defaults={'about_intro':'Your teacher is a Bachelor of Information and Communication Technology Honours (BICT) graduate from Uva Wellassa University, with professional experience at Michelin and practical experience in analytics, software development and machine learning.','study_letter':'Receive one practical ICT lesson, revision tip or new learning resource each month.'}
    for k,v in defaults.items():c.execute('INSERT OR IGNORE INTO site_content(content_key,content_value) VALUES(?,?)',(k,v))
    c.execute("UPDATE courses SET level='Grade 6–11' WHERE title='O/L ICT Complete' AND level IN ('Grade 10–11','Grade 10-11')")
    c.execute("UPDATE courses SET title='Online ICT Classes',description='Interactive online ICT lessons, revision, recordings and model-paper discussions.' WHERE title='Online Revision'")
    c.execute("UPDATE site_content SET content_value=? WHERE content_key='about_intro' AND content_value LIKE 'Harsha Madushan is a BICT graduate%'",(defaults['about_intro'],))
    c.execute("DELETE FROM site_content WHERE content_key='linkedin_followers'")
    resource_dir=ROOT/'assets'/'resources'
    if resource_dir.exists():
     for f in resource_dir.glob('*.pdf'):
      title=f.stem.replace('_',' ').replace('  ',' ').strip().title(); category='A/L ICT'; low=f.name.lower()
      if 'network' in low:category='Networking'
      elif 'logic' in low:category='Logic Gates'
      elif 'number' in low:category='Number Systems'
      elif 'os'==f.stem.lower():category='Operating Systems'
      elif 'syllabus' in low or 'learning outcomes' in low or '_lo' in low:category='Learning Outcomes'
      c.execute('INSERT OR IGNORE INTO materials(title,filename,category,description) VALUES(?,?,?,?)',(title,f.name,category,'Teacher-provided ICT lesson material for student review.'))
    if not c.execute('SELECT id FROM class_sessions').fetchone():c.executemany('INSERT INTO class_sessions(course_type,title,session_date,time_text,location,description) VALUES(?,?,?,?,?,?)',[('O/L','O/L ICT Theory','2026-08-15','2.00 PM - 4.00 PM','Colombo / Online','Weekly theory and practical class.'),('A/L','A/L ICT Complete Theory','2026-08-15','4.30 PM - 7.00 PM','Colombo / Online','Advanced Level ICT syllabus coverage.'),('A/L','Paper Discussion','2026-08-19','7.00 PM - 9.00 PM','Online','Past-paper and model-paper discussion.')])
    c.execute('CREATE INDEX IF NOT EXISTS idx_materials_visible_category ON materials(visible,category)');c.execute('CREATE INDEX IF NOT EXISTS idx_enquiries_created ON enquiries(created_at)');c.execute('PRAGMA optimize')

class H(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
 def end_headers(self):
  if urlparse(self.path).path.lower().endswith(('.html','.css','.js')):self.send_header('Cache-Control','no-cache, no-store, must-revalidate')
  super().end_headers()
 def reply(self,x,s=200,cookie=None):
  raw=json.dumps(x).encode();self.send_response(s);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');
  if cookie:self.send_header('Set-Cookie',cookie)
  self.end_headers();self.wfile.write(raw)
 def redirect(self,location):
  self.send_response(302);self.send_header('Location',location);self.send_header('Cache-Control','no-store');self.end_headers()
 def body(self):
  try:return json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
  except:return {}
 def user(self):
  cookies=SimpleCookie(self.headers.get('Cookie'));token=cookies.get('session')
  if not token:return None
  with db() as c:return c.execute("SELECT u.id,u.name,u.email,u.role,u.phone,u.student_stream,u.profile_photo FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires_at>datetime('now')",(token.value,)).fetchone()
 def require(self,role=None):
  u=self.user()
  if not u:self.reply({'error':'Please log in.'},401);return None
  if role and u['role']!=role:self.reply({'error':'Access denied.'},403);return None
  return u
 def do_GET(self):
  p=urlparse(self.path).path
  if p=='/about.html':
   u=self.user()
   if u and u['role']=='student':return self.redirect('/student-about.html')
  if p=='/api/profile':
   with db() as c:r=c.execute('SELECT name,title,email,phone,location,bio,linkedin,photo_path,updated_at FROM profile WHERE id=1').fetchone()
   result=dict(r);result['photo_url']=result.get('photo_path') or 'assets/harsha-profile.jpg';return self.reply(result)
  if p=='/api/public/content':
   with db() as c:
    content={x['content_key']:x['content_value'] for x in c.execute('SELECT * FROM site_content')};materials=[dict(x) for x in c.execute('SELECT id,title,filename,category,description FROM materials WHERE visible=1 ORDER BY category,title')];sessions=[dict(x) for x in c.execute('SELECT * FROM class_sessions WHERE visible=1 ORDER BY session_date')];courses=[dict(x) for x in c.execute('SELECT * FROM courses WHERE active=1 ORDER BY id')]
   return self.reply({'content':content,'materials':materials,'sessions':sessions,'courses':courses})
  if p=='/api/auth/me':
   u=self.user();return self.reply(dict(u) if u else {'user':None})
  if p=='/api/student/dashboard':
   u=self.require('student');
   if not u:return
   with db() as c:
    courses=[dict(x) for x in c.execute('SELECT c.id,c.title,c.level,c.description,e.progress,e.status FROM enrollments e JOIN courses c ON c.id=e.course_id WHERE e.user_id=?',(u['id'],))]
    stream=u['student_stream'] or 'O/L'; resources=[dict(x) for x in c.execute("SELECT id,title,'PDF' AS type,'assets/resources/'||filename AS url,description,category FROM materials WHERE visible=1 AND upper(category) LIKE ? ORDER BY title",('%'+stream.upper()+'%',))]
    notes=[dict(x) for x in c.execute("SELECT a.*,CASE WHEN nr.user_id IS NULL THEN 0 ELSE 1 END AS is_read FROM announcements a LEFT JOIN notification_reads nr ON nr.announcement_id=a.id AND nr.user_id=? WHERE a.target_stream IN ('ALL',?) ORDER BY a.id DESC",(u['id'],stream))]
    sessions=[dict(x) for x in c.execute("SELECT * FROM class_sessions WHERE visible=1 AND upper(course_type) LIKE ? ORDER BY session_date",('%'+stream.upper()+'%',))]
   return self.reply({'user':dict(u),'courses':courses,'resources':resources,'announcements':notes,'sessions':sessions,'unread_notifications':sum(1 for n in notes if not n['is_read'])})
  if p=='/api/student/profile':
   u=self.require('student');
   if not u:return
   return self.reply(dict(u))
  if p.startswith('/assets/resources/'):
   u=self.user()
   if not u:return self.redirect('/student-login.html')
   if u['role']!='student':return self.reply({'error':'Student login is required to download this resource.'},403)
   filename=Path(unquote(p.rsplit('/',1)[-1])).name
   with db() as c:item=c.execute('SELECT category FROM materials WHERE filename=? AND visible=1',(filename,)).fetchone()
   if not item:return self.reply({'error':'Resource not found.'},404)
   if (u['student_stream'] or '').upper() not in item['category'].upper():return self.reply({'error':'This resource belongs to another study programme.'},403)
   return super().do_GET()
  if p=='/api/admin/dashboard':
   if not self.require('admin'):return
   with db() as c:
    students=[dict(x) for x in c.execute("SELECT id,name,email,phone,student_stream,active,created_at FROM users WHERE role='student' ORDER BY id DESC")]
    enquiries=[dict(x) for x in c.execute('SELECT * FROM enquiries ORDER BY id DESC')]
    courses=[dict(x) for x in c.execute('SELECT * FROM courses ORDER BY id')];materials=[dict(x) for x in c.execute('SELECT * FROM materials ORDER BY id DESC')];sessions=[dict(x) for x in c.execute('SELECT * FROM class_sessions ORDER BY session_date')];subscriptions=[dict(x) for x in c.execute('SELECT * FROM subscriptions ORDER BY id DESC')];announcements=[dict(x) for x in c.execute('SELECT * FROM announcements ORDER BY id DESC')];content={x['content_key']:x['content_value'] for x in c.execute('SELECT * FROM site_content')}
   return self.reply({'students':students,'enquiries':enquiries,'courses':courses,'materials':materials,'sessions':sessions,'subscriptions':subscriptions,'announcements':announcements,'content':content})
  if p=='/api/enquiries':
   if not self.require('admin'):return
   with db() as c:rows=[dict(x) for x in c.execute('SELECT * FROM enquiries ORDER BY id DESC')]
   return self.reply(rows)
  return super().do_GET()
 def do_POST(self):
  p=urlparse(self.path).path;d=self.body()
  if p=='/api/auth/register':
   stream=str(d.get('student_stream','')).upper();
   if stream not in ('O/L','A/L'):return self.reply({'error':'Select O/L or A/L as your study programme.'},400)
   if str(d.get('password',''))!=str(d.get('confirm_password','')):return self.reply({'error':'Password and confirmation password do not match.'},400)
   if not re.match(r'^[^@]+@[^@]+\.[^@]+$',str(d.get('email',''))) or len(str(d.get('password','')))<8 or not d.get('name'):return self.reply({'error':'Enter a valid name, email and password of at least 8 characters.'},400)
   try:
    with db() as c:
     cur=c.execute('INSERT INTO users(name,email,password_hash,role,phone,student_stream) VALUES(?,?,?,?,?,?)',(d['name'].strip(),d['email'].lower().strip(),password_hash(d['password']),'student',d.get('phone','').strip(),stream));course=c.execute("SELECT id FROM courses WHERE upper(level) LIKE ? OR upper(title) LIKE ? ORDER BY id LIMIT 1",('%'+stream+'%','%'+stream+'%')).fetchone()
     if course:c.execute('INSERT OR IGNORE INTO enrollments(user_id,course_id,progress) VALUES(?,?,0)',(cur.lastrowid,course['id']))
   except sqlite3.IntegrityError:return self.reply({'error':'An account already exists for this email.'},409)
   return self.reply({'ok':True},201)
  if p=='/api/auth/login':
   identifier=str(d.get('identifier',d.get('email',''))).lower().strip();required=d.get('portal')
   with db() as c:u=c.execute('SELECT * FROM users WHERE lower(username)=? AND role=?',(identifier,'admin')).fetchone() if required=='admin' else c.execute('SELECT * FROM users WHERE lower(email)=? AND role=?',(identifier,'student')).fetchone()
   if not u or not verify(str(d.get('password','')),u['password_hash']):return self.reply({'error':'Incorrect username or password.' if required=='admin' else 'Incorrect email or password.'},401)
   if not u['active']:return self.reply({'error':'This account is inactive. Contact Harsha.'},403)
   if required=='admin' and u['role']!='admin':return self.reply({'error':'This account does not have administrator access.'},403)
   if required=='student' and u['role']!='student':return self.reply({'error':'Use the private administrator login.'},403)
   token=secrets.token_urlsafe(32)
   with db() as c:c.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,datetime('now','+7 days'))",(token,u['id']))
   return self.reply({'ok':True,'role':u['role']},cookie=f'session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800')
  if p.startswith('/api/student/notifications/') and p.endswith('/read'):
   u=self.require('student');
   if not u:return
   aid=p.split('/')[-2]
   with db() as c:c.execute('INSERT OR IGNORE INTO notification_reads(user_id,announcement_id) VALUES(?,?)',(u['id'],aid))
   return self.reply({'ok':True})
  if p=='/api/admin/announcements':
   if not self.require('admin'):return
   target=str(d.get('target_stream','ALL')).upper()
   if target not in ('ALL','O/L','A/L'):return self.reply({'error':'Invalid notification audience.'},400)
   with db() as c:cur=c.execute('INSERT INTO announcements(title,body,target_stream) VALUES(?,?,?)',(str(d.get('title','')).strip(),str(d.get('body','')).strip(),target))
   return self.reply({'ok':True,'id':cur.lastrowid},201)
  if p in ('/api/profile/photo','/api/student/profile/photo'):
   role='admin' if p=='/api/profile/photo' else 'student';u=self.require(role)
   if not u:return
   try:raw=base64.b64decode(d.get('data',''),validate=True)
   except:return self.reply({'error':'Invalid image data.'},400)
   if len(raw)>5*1024*1024:return self.reply({'error':'Photo must be smaller than 5 MB.'},400)
   mime=str(d.get('mime','')).lower();extensions={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'};valid={'image/jpeg':raw.startswith(b'\xff\xd8\xff'),'image/png':raw.startswith(b'\x89PNG\r\n\x1a\n'),'image/webp':raw.startswith(b'RIFF') and raw[8:12]==b'WEBP'}
   if mime not in extensions or not valid.get(mime):return self.reply({'error':'Upload a valid JPG, PNG or WebP image.'},400)
   folder=ROOT/'assets'/'profile-photos';folder.mkdir(exist_ok=True);filename=('teacher' if role=='admin' else f'student-{u["id"]}')+extensions[mime];(folder/filename).write_bytes(raw);relative='assets/profile-photos/'+filename
   with db() as c:
    if role=='admin':c.execute('UPDATE profile SET photo_path=?,updated_at=CURRENT_TIMESTAMP WHERE id=1',(relative,))
    else:c.execute('UPDATE users SET profile_photo=? WHERE id=?',(relative,u['id']))
   return self.reply({'ok':True,'photo_url':relative})
  if p=='/api/auth/logout':
   cookies=SimpleCookie(self.headers.get('Cookie'));token=cookies.get('session')
   if token:
    with db() as c:c.execute('DELETE FROM sessions WHERE token=?',(token.value,))
   return self.reply({'ok':True},cookie='session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0')
  if p=='/api/enquiries':
   if not d.get('student_name') or not d.get('phone') or not d.get('class_name'):return self.reply({'error':'Name, phone and class are required.'},400)
   clean={k:str(d.get(k,'')).strip() for k in ('student_name','phone','email','class_name','message')}
   with db() as c:cur=c.execute('INSERT INTO enquiries(student_name,phone,email,class_name,message) VALUES(:student_name,:phone,:email,:class_name,:message)',clean)
   return self.reply({'ok':True,'id':cur.lastrowid},201)
  if p=='/api/subscriptions':
   email=str(d.get('email','')).strip().lower()
   if not re.match(r'^[^@]+@[^@]+\.[^@]+$',email):return self.reply({'error':'Enter a valid email address.'},400)
   with db() as c:c.execute('INSERT OR IGNORE INTO subscriptions(email) VALUES(?)',(email,))
   return self.reply({'ok':True},201)
  if p=='/api/admin/materials':
   if not self.require('admin'):return
   with db() as c:cur=c.execute('INSERT INTO materials(title,filename,category,description) VALUES(?,?,?,?)',(d.get('title','New Resource'),d.get('filename',''),d.get('category','ICT'),d.get('description','')))
   return self.reply({'ok':True,'id':cur.lastrowid},201)
  if p=='/api/admin/upload':
   if not self.require('admin'):return
   filename=Path(str(d.get('filename','resource.pdf'))).name
   if not filename.lower().endswith('.pdf'):return self.reply({'error':'Only PDF files are allowed.'},400)
   try:raw=base64.b64decode(d.get('data',''),validate=True)
   except:return self.reply({'error':'Invalid file data.'},400)
   if not raw.startswith(b'%PDF') or len(raw)>20*1024*1024:return self.reply({'error':'Invalid PDF or file exceeds 20 MB.'},400)
   (ROOT/'assets'/'resources'/filename).write_bytes(raw)
   with db() as c:cur=c.execute('INSERT OR REPLACE INTO materials(title,filename,category,description,visible) VALUES(?,?,?,?,1)',(d.get('title',Path(filename).stem),filename,d.get('category','ICT'),d.get('description','Teacher-provided lesson resource.')))
   return self.reply({'ok':True,'id':cur.lastrowid},201)
  if p=='/api/admin/sessions':
   if not self.require('admin'):return
   with db() as c:cur=c.execute('INSERT INTO class_sessions(course_type,title,session_date,time_text,location,description) VALUES(?,?,?,?,?,?)',(d.get('course_type','A/L'),d.get('title','Class'),d.get('session_date',''),d.get('time_text',''),d.get('location',''),d.get('description','')))
   return self.reply({'ok':True,'id':cur.lastrowid},201)
  return self.reply({'error':'Not found'},404)
 def do_PUT(self):
  p=urlparse(self.path).path;d=self.body()
  if p=='/api/profile':
   if not self.require('admin'):return
   fields=('name','title','email','phone','location','bio','linkedin')
   if any(not str(d.get(k,'')).strip() for k in fields):return self.reply({'error':'Complete every field.'},400)
   clean={k:str(d[k]).strip() for k in fields}
   with db() as c:c.execute('UPDATE profile SET name=:name,title=:title,email=:email,phone=:phone,location=:location,bio=:bio,linkedin=:linkedin,updated_at=CURRENT_TIMESTAMP WHERE id=1',clean)
   return self.reply({'ok':True})
  if p=='/api/student/profile':
   u=self.require('student');
   if not u:return
   name=str(d.get('name','')).strip();phone=str(d.get('phone','')).strip()
   if not name:return self.reply({'error':'Your name is required.'},400)
   with db() as c:c.execute("UPDATE users SET name=?,phone=? WHERE id=? AND role='student'",(name,phone,u['id']))
   return self.reply({'ok':True})
  if p.startswith('/api/admin/progress/'):
   if not self.require('admin'):return
   eid=p.rsplit('/',1)[-1];value=max(0,min(100,int(d.get('progress',0))))
   with db() as c:c.execute('UPDATE enrollments SET progress=? WHERE id=?',(value,eid))
   return self.reply({'ok':True})
  if p.startswith('/api/admin/students/'):
   if not self.require('admin'):return
   uid=p.rsplit('/',1)[-1];active=1 if d.get('active') else 0
   with db() as c:c.execute("UPDATE users SET active=? WHERE id=? AND role='student'",(active,uid))
   return self.reply({'ok':True,'active':active})
  if p.startswith('/api/admin/materials/'):
   if not self.require('admin'):return
   mid=p.rsplit('/',1)[-1]
   with db() as c:c.execute('UPDATE materials SET title=?,category=?,description=?,visible=? WHERE id=?',(d.get('title',''),d.get('category','ICT'),d.get('description',''),1 if d.get('visible',True) else 0,mid))
   return self.reply({'ok':True})
  if p.startswith('/api/admin/courses/'):
   if not self.require('admin'):return
   cid=p.rsplit('/',1)[-1]
   with db() as c:c.execute('UPDATE courses SET title=?,level=?,description=?,active=? WHERE id=?',(d.get('title',''),d.get('level',''),d.get('description',''),1 if d.get('active',True) else 0,cid))
   return self.reply({'ok':True})
  if p.startswith('/api/admin/sessions/'):
   if not self.require('admin'):return
   sid=p.rsplit('/',1)[-1]
   with db() as c:c.execute('UPDATE class_sessions SET course_type=?,title=?,session_date=?,time_text=?,location=?,description=?,visible=? WHERE id=?',(d.get('course_type',''),d.get('title',''),d.get('session_date',''),d.get('time_text',''),d.get('location',''),d.get('description',''),1 if d.get('visible',True) else 0,sid))
   return self.reply({'ok':True})
  if p=='/api/admin/content':
   if not self.require('admin'):return
   with db() as c:
    for k,v in d.items():c.execute('INSERT INTO site_content(content_key,content_value) VALUES(?,?) ON CONFLICT(content_key) DO UPDATE SET content_value=excluded.content_value,updated_at=CURRENT_TIMESTAMP',(k,str(v)))
   return self.reply({'ok':True})
  return self.reply({'error':'Not found'},404)
 def do_DELETE(self):
  p=urlparse(self.path).path
  if not self.require('admin'):return
  table=None
  if p.startswith('/api/admin/materials/'):table='materials'
  elif p.startswith('/api/admin/sessions/'):table='class_sessions'
  elif p.startswith('/api/admin/enquiries/'):table='enquiries'
  elif p.startswith('/api/admin/announcements/'):table='announcements'
  if not table:return self.reply({'error':'Not found'},404)
  rid=p.rsplit('/',1)[-1]
  with db() as c:c.execute(f'DELETE FROM {table} WHERE id=?',(rid,))
  return self.reply({'ok':True})
if __name__=='__main__':
 port=int(sys.argv[1]) if len(sys.argv)>1 else 5500
 init();print(f'ICT with Harsha: http://127.0.0.1:{port}');ThreadingHTTPServer(('127.0.0.1',port),H).serve_forever()
