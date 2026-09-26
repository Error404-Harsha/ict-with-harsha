from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote
from http.cookies import SimpleCookie
import json, sqlite3, hashlib, secrets, hmac, re, sys, os, base64, smtplib, ssl, html
from io import BytesIO
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage

ROOT=Path(__file__).resolve().parent; DB=ROOT/'ict_with_harsha.db'
PROFILE={"name":"Harsha Madushan","title":"BICT (Honours) Graduate & ICT Educator","email":"harshamaduushan@gmail.com","phone":"0788523755","location":"Sri Lanka","bio":"Bachelor of Information and Communication Technology Honours (BICT) graduate from Uva Wellassa University, with professional experience at Michelin and practical experience in analytics, software and machine learning.","linkedin":"https://www.linkedin.com/in/swhmadushan"}
COURSES=[('O/L ICT Complete','Grade 6–11','Full syllabus theory, practical lessons and exam preparation.'),('A/L ICT Complete','Grade 12–13','Theory, Python, databases and structured paper practice.'),('Online ICT Classes','Online','Interactive online ICT lessons, revision, recordings and model-paper discussions.')]
def db(): c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
def password_hash(password,salt=None):
    salt=salt or secrets.token_hex(16); digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),200000).hex();return f'{salt}${digest}'
def verify(password,stored):
    try:salt,digest=stored.split('$');return hmac.compare_digest(password_hash(password,salt).split('$')[1],digest)
    except:return False
def utcnow():return datetime.now(timezone.utc)
def parse_dt(value):
    if not value:return None
    try:return datetime.fromisoformat(str(value).replace('Z','+00:00')).astimezone(timezone.utc)
    except:return None
def code_hash(email,purpose,code):return hashlib.sha256(f'{email.lower()}|{purpose}|{code}'.encode()).hexdigest()
def send_email(to,subject,body):
    host=os.getenv('ICT_SMTP_HOST','').strip();user=os.getenv('ICT_SMTP_USER','').strip();password=os.getenv('ICT_SMTP_PASSWORD','')
    sender=os.getenv('ICT_SMTP_FROM',user).strip();port=int(os.getenv('ICT_SMTP_PORT','587'));security=os.getenv('ICT_SMTP_SECURITY','starttls').lower()
    if not host or not user or not password or not sender:
      if os.getenv('ICT_EMAIL_DEBUG')=='1':print(f'EMAIL DEBUG to={to} subject={subject}\n{body}');return True
      return False
    msg=EmailMessage();msg['Subject']=subject;msg['From']=sender;msg['To']=to;msg.set_content(body)
    context=ssl.create_default_context()
    if security=='ssl':
      with smtplib.SMTP_SSL(host,port,context=context,timeout=20) as smtp:smtp.login(user,password);smtp.send_message(msg)
    else:
      with smtplib.SMTP(host,port,timeout=20) as smtp:smtp.ehlo();smtp.starttls(context=context);smtp.ehlo();smtp.login(user,password);smtp.send_message(msg)
    return True
def new_email_code(c,email,purpose,payload=''):
    c.execute('DELETE FROM email_verifications WHERE email=? AND purpose=?',(email,purpose));code=f'{secrets.randbelow(1000000):06d}'
    c.execute("INSERT INTO email_verifications(email,purpose,code_hash,payload,expires_at) VALUES(?,?,?,?,datetime('now','+10 minutes'))",(email,purpose,code_hash(email,purpose,code),payload));return code
def check_email_code(c,email,purpose,code):
    row=c.execute("SELECT * FROM email_verifications WHERE email=? AND purpose=? AND used_at IS NULL AND expires_at>datetime('now')",(email,purpose)).fetchone()
    if not row or row['attempts']>=5:return None
    if not hmac.compare_digest(row['code_hash'],code_hash(email,purpose,str(code).strip())):
      c.execute('UPDATE email_verifications SET attempts=attempts+1 WHERE id=?',(row['id'],));return None
    c.execute('UPDATE email_verifications SET used_at=CURRENT_TIMESTAMP WHERE id=?',(row['id'],));return row
def build_result_pdf(student,quiz,questions,attempt):
    try:
      from reportlab.lib import colors
      from reportlab.lib.enums import TA_CENTER
      from reportlab.lib.pagesizes import A4
      from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
      from reportlab.lib.units import mm
      from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
    except ImportError:raise RuntimeError('PDF support is not installed on the server.')
    buffer=BytesIO();styles=getSampleStyleSheet();ink=colors.HexColor('#111419');green=colors.HexColor('#3f7d20');red=colors.HexColor('#b83b32');lime=colors.HexColor('#c8ff36');muted=colors.HexColor('#687078');safe=lambda value:html.escape(str(value or ''))
    title=ParagraphStyle('ResultTitle',parent=styles['Title'],fontName='Helvetica-Bold',fontSize=23,leading=28,textColor=ink,spaceAfter=7)
    meta=ParagraphStyle('Meta',parent=styles['BodyText'],fontName='Helvetica',fontSize=8.5,leading=13,textColor=muted)
    question_style=ParagraphStyle('Question',parent=styles['Heading3'],fontName='Helvetica-Bold',fontSize=11,leading=15,textColor=ink,spaceAfter=7)
    answer_style=ParagraphStyle('Answer',parent=styles['BodyText'],fontName='Helvetica',fontSize=8.5,leading=12,textColor=ink)
    def header_footer(canvas,doc):
      canvas.saveState();canvas.setFillColor(ink);canvas.rect(0,A4[1]-18*mm,A4[0],18*mm,fill=1,stroke=0);canvas.setFillColor(lime);canvas.setFont('Helvetica-Bold',9);canvas.drawString(18*mm,A4[1]-11*mm,'ICT WITH HARSHA');canvas.setFillColor(muted);canvas.setFont('Helvetica',7);canvas.drawRightString(A4[0]-18*mm,10*mm,f'Page {doc.page}');canvas.restoreState()
    doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=27*mm,bottomMargin=18*mm,title=f"{quiz['title']} - Result")
    score=int(attempt['score']);total=int(attempt['total']);percent=round((score/total*100) if total else 0)
    story=[Paragraph('QUIZ RESULT SHEET',meta),Paragraph(safe(quiz['title']),title),Paragraph(f"Student: <b>{safe(student['name'])}</b><br/>Email: {safe(student['email'])}<br/>Programme: {safe(student['student_stream'])}<br/>Submitted: {safe(attempt['submitted_at'] or '-')}",meta),Spacer(1,6*mm)]
    summary=Table([[Paragraph('SCORE',meta),Paragraph('PERCENTAGE',meta),Paragraph('QUESTIONS',meta)],[Paragraph(f'<b>{score} / {total}</b>',styles['Heading2']),Paragraph(f'<b>{percent}%</b>',styles['Heading2']),Paragraph(f'<b>{len(questions)}</b>',styles['Heading2'])]],colWidths=[55*mm,55*mm,55*mm])
    summary.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),lime),('BACKGROUND',(0,1),(-1,-1),colors.HexColor('#f7f8f4')),('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#d9d9d5')),('INNERGRID',(0,0),(-1,-1),0.5,colors.HexColor('#d9d9d5')),('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]));story.extend([summary,Spacer(1,8*mm)])
    for index,q in enumerate(questions,1):
      selected=q.get('selected_option') or '';correct=q['correct_option'];ok=selected==correct;earned=int(q['points']) if ok else 0
      story.append(Paragraph(f"{index}. {safe(q['prompt'])}",question_style));rows=[]
      for key in ('A','B','C','D'):
       label=q['option_'+key.lower()];markers=[]
       if key==selected:markers.append('Your answer')
       if key==correct:markers.append('Correct answer')
       rows.append([key,Paragraph(safe(label),answer_style),', '.join(markers)])
      table=Table(rows,colWidths=[10*mm,115*mm,40*mm])
      style=[('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#d9d9d5')),('INNERGRID',(0,0),(-1,-1),0.5,colors.HexColor('#e7e7e2')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold')]
      for row,key in enumerate(('A','B','C','D')):
       if key==correct:style.extend([('BACKGROUND',(0,row),(-1,row),colors.HexColor('#e7f7dc')),('TEXTCOLOR',(0,row),(-1,row),green)])
       if key==selected and key!=correct:style.extend([('BACKGROUND',(0,row),(-1,row),colors.HexColor('#fde5e2')),('TEXTCOLOR',(0,row),(-1,row),red)])
      table.setStyle(TableStyle(style));story.extend([table,Paragraph(f"{'Correct' if ok else 'Incorrect'} - {earned}/{q['points']} marks",ParagraphStyle('Status',parent=meta,textColor=green if ok else red,spaceBefore=5,spaceAfter=12))])
    doc.build(story,onFirstPage=header_footer,onLaterPages=header_footer);return buffer.getvalue()
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
    CREATE TABLE IF NOT EXISTS class_sessions(id INTEGER PRIMARY KEY AUTOINCREMENT,course_type TEXT NOT NULL,title TEXT NOT NULL,session_date TEXT,time_text TEXT,location TEXT,description TEXT,visible INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS email_verifications(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT NOT NULL,purpose TEXT NOT NULL,code_hash TEXT NOT NULL,payload TEXT,expires_at TEXT NOT NULL,attempts INTEGER DEFAULT 0,used_at TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS quizzes(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,description TEXT,student_stream TEXT DEFAULT 'ALL',duration_minutes INTEGER DEFAULT 30,starts_at TEXT,ends_at TEXT,status TEXT DEFAULT 'draft',created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS quiz_questions(id INTEGER PRIMARY KEY AUTOINCREMENT,quiz_id INTEGER NOT NULL,prompt TEXT NOT NULL,option_a TEXT NOT NULL,option_b TEXT NOT NULL,option_c TEXT NOT NULL,option_d TEXT NOT NULL,correct_option TEXT NOT NULL,points INTEGER DEFAULT 1,position INTEGER DEFAULT 1,FOREIGN KEY(quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS quiz_attempts(id INTEGER PRIMARY KEY AUTOINCREMENT,quiz_id INTEGER NOT NULL,user_id INTEGER NOT NULL,started_at TEXT DEFAULT CURRENT_TIMESTAMP,submitted_at TEXT,answers_json TEXT DEFAULT '{}',score INTEGER DEFAULT 0,total INTEGER DEFAULT 0,status TEXT DEFAULT 'in_progress',UNIQUE(quiz_id,user_id),FOREIGN KEY(quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE,FOREIGN KEY(user_id) REFERENCES users(id));''')
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
    c.execute('CREATE INDEX IF NOT EXISTS idx_materials_visible_category ON materials(visible,category)');c.execute('CREATE INDEX IF NOT EXISTS idx_enquiries_created ON enquiries(created_at)');c.execute('CREATE INDEX IF NOT EXISTS idx_quizzes_stream_status ON quizzes(student_stream,status)');c.execute('CREATE INDEX IF NOT EXISTS idx_quiz_attempt_user ON quiz_attempts(user_id,quiz_id)');c.execute('CREATE INDEX IF NOT EXISTS idx_email_verification ON email_verifications(email,purpose,expires_at)');c.execute('PRAGMA optimize')

class H(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
 def end_headers(self):
  if urlparse(self.path).path.lower().endswith(('.html','.css','.js')):self.send_header('Cache-Control','no-cache, no-store, must-revalidate')
  super().end_headers()
 def reply(self,x,s=200,cookie=None):
  raw=json.dumps(x).encode();self.send_response(s);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');
  if cookie:self.send_header('Set-Cookie',cookie)
  self.end_headers();self.wfile.write(raw)
 def file_reply(self,raw,content_type,filename):
  self.send_response(200);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(raw)));self.send_header('Content-Disposition',f'attachment; filename="{filename}"');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
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
  if p=='/api/student/quizzes':
   u=self.require('student');
   if not u:return
   stream=(u['student_stream'] or 'O/L').upper()
   with db() as c:
    rows=[dict(x) for x in c.execute("""SELECT q.id,q.title,q.description,q.student_stream,q.duration_minutes,q.starts_at,q.ends_at,q.status,
      COUNT(qq.id) question_count,COALESCE(SUM(qq.points),0) total_points,qa.status attempt_status,qa.score,qa.total,qa.submitted_at
      FROM quizzes q LEFT JOIN quiz_questions qq ON qq.quiz_id=q.id LEFT JOIN quiz_attempts qa ON qa.quiz_id=q.id AND qa.user_id=?
      WHERE q.status='published' AND q.student_stream IN ('ALL',?) GROUP BY q.id ORDER BY q.starts_at IS NULL,q.starts_at,q.id DESC""",(u['id'],stream))]
   now=utcnow()
   for q in rows:
    start=parse_dt(q['starts_at']);end=parse_dt(q['ends_at']);q['availability']='upcoming' if start and now<start else ('closed' if end and now>end else 'open')
   return self.reply(rows)
  if p.startswith('/api/student/quizzes/') and p.endswith('/result.pdf'):
   u=self.require('student');
   if not u:return
   try:qid=int(p.split('/')[-2])
   except:return self.reply({'error':'Quiz result not found.'},404)
   with db() as c:
    q=c.execute("SELECT * FROM quizzes WHERE id=? AND student_stream IN ('ALL',?)",(qid,(u['student_stream'] or 'O/L').upper())).fetchone();attempt=c.execute("SELECT * FROM quiz_attempts WHERE quiz_id=? AND user_id=? AND status='submitted'",(qid,u['id'])).fetchone()
    if not q or not attempt:return self.reply({'error':'Complete the quiz before downloading its result.'},403)
    answers=json.loads(attempt['answers_json'] or '{}');questions=[dict(x) for x in c.execute('SELECT * FROM quiz_questions WHERE quiz_id=? ORDER BY position,id',(qid,))]
   for question in questions:question['selected_option']=str(answers.get(str(question['id']),'')).upper()
   try:raw=build_result_pdf(dict(u),dict(q),questions,dict(attempt))
   except RuntimeError as e:return self.reply({'error':str(e)},503)
   return self.file_reply(raw,'application/pdf',f'quiz-result-{qid}.pdf')
  if p.startswith('/api/student/quizzes/'):
   u=self.require('student');
   if not u:return
   try:qid=int(p.rsplit('/',1)[-1])
   except:return self.reply({'error':'Quiz not found.'},404)
   with db() as c:
    q=c.execute("SELECT * FROM quizzes WHERE id=? AND status='published' AND student_stream IN ('ALL',?)",(qid,(u['student_stream'] or 'O/L').upper())).fetchone()
    if not q:return self.reply({'error':'Quiz not found.'},404)
    attempt=c.execute('SELECT * FROM quiz_attempts WHERE quiz_id=? AND user_id=?',(qid,u['id'])).fetchone()
    if attempt and attempt['status']=='submitted':
     answers=json.loads(attempt['answers_json'] or '{}');questions=[dict(x) for x in c.execute('SELECT id,prompt,option_a,option_b,option_c,option_d,correct_option,points,position FROM quiz_questions WHERE quiz_id=? ORDER BY position,id',(qid,))]
     for question in questions:question['selected_option']=str(answers.get(str(question['id']),'')).upper();question['is_correct']=question['selected_option']==question['correct_option']
    else:questions=[dict(x) for x in c.execute('SELECT id,prompt,option_a,option_b,option_c,option_d,points,position FROM quiz_questions WHERE quiz_id=? ORDER BY position,id',(qid,))]
   result=dict(q);result['questions']=questions;result['attempt']=dict(attempt) if attempt else None;return self.reply(result)
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
    courses=[dict(x) for x in c.execute('SELECT * FROM courses ORDER BY id')];materials=[dict(x) for x in c.execute('SELECT * FROM materials ORDER BY id DESC')];sessions=[dict(x) for x in c.execute('SELECT * FROM class_sessions ORDER BY session_date')];subscriptions=[dict(x) for x in c.execute('SELECT * FROM subscriptions ORDER BY id DESC')];announcements=[dict(x) for x in c.execute('SELECT * FROM announcements ORDER BY id DESC')];content={x['content_key']:x['content_value'] for x in c.execute('SELECT * FROM site_content')};quizzes=[dict(x) for x in c.execute('SELECT q.*,COUNT(DISTINCT qq.id) question_count,COUNT(DISTINCT qa.id) attempt_count FROM quizzes q LEFT JOIN quiz_questions qq ON qq.quiz_id=q.id LEFT JOIN quiz_attempts qa ON qa.quiz_id=q.id GROUP BY q.id ORDER BY q.id DESC')]
   return self.reply({'students':students,'enquiries':enquiries,'courses':courses,'materials':materials,'sessions':sessions,'subscriptions':subscriptions,'announcements':announcements,'quizzes':quizzes,'content':content})
  if p.startswith('/api/admin/quizzes/'):
   if not self.require('admin'):return
   try:qid=int(p.rsplit('/',1)[-1])
   except:return self.reply({'error':'Quiz not found.'},404)
   with db() as c:
    q=c.execute('SELECT * FROM quizzes WHERE id=?',(qid,)).fetchone()
    if not q:return self.reply({'error':'Quiz not found.'},404)
    questions=[dict(x) for x in c.execute('SELECT * FROM quiz_questions WHERE quiz_id=? ORDER BY position,id',(qid,))]
    attempts=[dict(x) for x in c.execute("SELECT qa.*,u.name,u.email FROM quiz_attempts qa JOIN users u ON u.id=qa.user_id WHERE qa.quiz_id=? ORDER BY qa.id DESC",(qid,))]
   result=dict(q);result['questions']=questions;result['attempts']=attempts;return self.reply(result)
  if p=='/api/enquiries':
   if not self.require('admin'):return
   with db() as c:rows=[dict(x) for x in c.execute('SELECT * FROM enquiries ORDER BY id DESC')]
   return self.reply(rows)
  return super().do_GET()
 def do_POST(self):
  p=urlparse(self.path).path;d=self.body()
  if p=='/api/auth/register/request-code':
   stream=str(d.get('student_stream','')).upper();
   if stream not in ('O/L','A/L'):return self.reply({'error':'Select O/L or A/L as your study programme.'},400)
   if str(d.get('password',''))!=str(d.get('confirm_password','')):return self.reply({'error':'Password and confirmation password do not match.'},400)
   email=str(d.get('email','')).lower().strip()
   if not re.match(r'^[^@]+@[^@]+\.[^@]+$',email) or len(str(d.get('password','')))<8 or not str(d.get('name','')).strip():return self.reply({'error':'Enter a valid name, email and password of at least 8 characters.'},400)
   with db() as c:
    if c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone():return self.reply({'error':'An account already exists for this email.'},409)
    if c.execute("SELECT id FROM email_verifications WHERE email=? AND purpose='register' AND created_at>datetime('now','-1 minute')",(email,)).fetchone():return self.reply({'error':'Please wait one minute before requesting another code.'},429)
    payload=json.dumps({'name':str(d['name']).strip(),'email':email,'phone':str(d.get('phone','')).strip(),'student_stream':stream,'password_hash':password_hash(str(d['password']))});code=new_email_code(c,email,'register',payload)
   try:sent=send_email(email,'Your ICT with Harsha verification code',f'Your student registration verification code is {code}.\n\nThis code expires in 10 minutes. If you did not request it, ignore this email.')
   except Exception as e:print('Email error:',e);sent=False
   if not sent:
    with db() as c:c.execute("DELETE FROM email_verifications WHERE email=? AND purpose='register'",(email,))
    return self.reply({'error':'Verification email could not be sent. Please contact the teacher or try again later.'},503)
   return self.reply({'ok':True,'message':'Verification code sent. Check your inbox and spam folder.'})
  if p=='/api/auth/register/verify':
   email=str(d.get('email','')).lower().strip()
   try:
    with db() as c:
     verification=check_email_code(c,email,'register',d.get('code',''))
     if not verification:return self.reply({'error':'The verification code is incorrect or has expired.'},400)
     pending=json.loads(verification['payload']);cur=c.execute('INSERT INTO users(name,email,password_hash,role,phone,student_stream) VALUES(?,?,?,?,?,?)',(pending['name'],pending['email'],pending['password_hash'],'student',pending['phone'],pending['student_stream']));course=c.execute("SELECT id FROM courses WHERE upper(level) LIKE ? OR upper(title) LIKE ? ORDER BY id LIMIT 1",('%'+pending['student_stream']+'%','%'+pending['student_stream']+'%')).fetchone()
     if course:c.execute('INSERT OR IGNORE INTO enrollments(user_id,course_id,progress) VALUES(?,?,0)',(cur.lastrowid,course['id']))
   except sqlite3.IntegrityError:return self.reply({'error':'An account already exists for this email.'},409)
   return self.reply({'ok':True},201)
  if p=='/api/auth/register':return self.reply({'error':'Email verification is required. Request a verification code first.'},400)
  if p=='/api/auth/forgot/request-code':
   email=str(d.get('email','')).lower().strip()
   with db() as c:
    account=c.execute("SELECT id FROM users WHERE email=? AND role='student'",(email,)).fetchone()
    recent=c.execute("SELECT id FROM email_verifications WHERE email=? AND purpose='reset' AND created_at>datetime('now','-1 minute')",(email,)).fetchone() if account else None
    code=new_email_code(c,email,'reset') if account and not recent else None
   if code:
    try:send_email(email,'Reset your ICT with Harsha password',f'Your password reset verification code is {code}.\n\nThis code expires in 10 minutes. If you did not request a password reset, ignore this email.')
    except Exception as e:print('Email error:',e)
   return self.reply({'ok':True,'message':'If this student email exists, a verification code has been sent.'})
  if p=='/api/auth/forgot/reset':
   email=str(d.get('email','')).lower().strip();password=str(d.get('password',''));confirmation=str(d.get('confirm_password',''))
   if len(password)<8:return self.reply({'error':'Password must contain at least 8 characters.'},400)
   if password!=confirmation:return self.reply({'error':'Password and confirmation password do not match.'},400)
   with db() as c:
    verification=check_email_code(c,email,'reset',d.get('code',''))
    if not verification:return self.reply({'error':'The verification code is incorrect or has expired.'},400)
    changed=c.execute("UPDATE users SET password_hash=? WHERE email=? AND role='student'",(password_hash(password),email)).rowcount;c.execute('DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE email=?)',(email,))
   if not changed:return self.reply({'error':'Unable to reset this account.'},400)
   return self.reply({'ok':True,'message':'Password updated. You can now sign in.'})
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
  if p.startswith('/api/student/quizzes/') and p.endswith('/start'):
   u=self.require('student');
   if not u:return
   try:qid=int(p.split('/')[-2])
   except:return self.reply({'error':'Quiz not found.'},404)
   with db() as c:
    q=c.execute("SELECT * FROM quizzes WHERE id=? AND status='published' AND student_stream IN ('ALL',?)",(qid,(u['student_stream'] or 'O/L').upper())).fetchone()
    if not q:return self.reply({'error':'Quiz is not available for your programme.'},404)
    now=utcnow();start=parse_dt(q['starts_at']);end=parse_dt(q['ends_at'])
    if start and now<start:return self.reply({'error':'This quiz has not opened yet.'},409)
    if end and now>end:return self.reply({'error':'This quiz has already closed.'},409)
    existing=c.execute('SELECT * FROM quiz_attempts WHERE quiz_id=? AND user_id=?',(qid,u['id'])).fetchone()
    if existing and existing['status']=='submitted':return self.reply({'error':'You have already completed this quiz.'},409)
    if not existing:c.execute('INSERT INTO quiz_attempts(quiz_id,user_id) VALUES(?,?)',(qid,u['id']))
    attempt=c.execute('SELECT * FROM quiz_attempts WHERE quiz_id=? AND user_id=?',(qid,u['id'])).fetchone()
   return self.reply({'ok':True,'attempt':dict(attempt),'duration_minutes':q['duration_minutes']})
  if p.startswith('/api/student/quizzes/') and p.endswith('/submit'):
   u=self.require('student');
   if not u:return
   try:qid=int(p.split('/')[-2])
   except:return self.reply({'error':'Quiz not found.'},404)
   answers=d.get('answers',{}) if isinstance(d.get('answers',{}),dict) else {}
   with db() as c:
    q=c.execute("SELECT * FROM quizzes WHERE id=? AND status='published' AND student_stream IN ('ALL',?)",(qid,(u['student_stream'] or 'O/L').upper())).fetchone();attempt=c.execute("SELECT * FROM quiz_attempts WHERE quiz_id=? AND user_id=?",(qid,u['id'])).fetchone()
    if not q or not attempt:return self.reply({'error':'Start the quiz before submitting.'},409)
    if attempt['status']=='submitted':return self.reply({'error':'This quiz has already been submitted.'},409)
    started=parse_dt(attempt['started_at']+'Z' if '+' not in attempt['started_at'] and not attempt['started_at'].endswith('Z') else attempt['started_at']);deadline=(started+timedelta(minutes=max(1,int(q['duration_minutes'])))) if started else utcnow();end=parse_dt(q['ends_at']);deadline=min(deadline,end) if end else deadline
    questions=list(c.execute('SELECT id,correct_option,points FROM quiz_questions WHERE quiz_id=?',(qid,)));total=sum(int(x['points']) for x in questions)
    if utcnow()>deadline+timedelta(seconds=30):
     c.execute("UPDATE quiz_attempts SET answers_json='{}',score=0,total=?,status='submitted',submitted_at=CURRENT_TIMESTAMP WHERE id=?",(total,attempt['id']));return self.reply({'ok':True,'score':0,'total':total,'expired':True})
    score=sum(int(x['points']) for x in questions if str(answers.get(str(x['id']),answers.get(x['id'],''))).upper()==x['correct_option'])
    c.execute("UPDATE quiz_attempts SET answers_json=?,score=?,total=?,status='submitted',submitted_at=CURRENT_TIMESTAMP WHERE id=?",(json.dumps(answers),score,total,attempt['id']))
   return self.reply({'ok':True,'score':score,'total':total})
  if p=='/api/admin/quizzes':
   if not self.require('admin'):return
   title=str(d.get('title','')).strip();stream=str(d.get('student_stream','ALL')).upper()
   if not title:return self.reply({'error':'Quiz title is required.'},400)
   if stream not in ('ALL','O/L','A/L'):return self.reply({'error':'Select a valid student programme.'},400)
   with db() as c:cur=c.execute('INSERT INTO quizzes(title,description,student_stream,duration_minutes,starts_at,ends_at,status) VALUES(?,?,?,?,?,?,?)',(title,str(d.get('description','')).strip(),stream,max(1,int(d.get('duration_minutes',30))),d.get('starts_at') or None,d.get('ends_at') or None,'draft'))
   return self.reply({'ok':True,'id':cur.lastrowid},201)
  if p.startswith('/api/admin/quizzes/') and p.endswith('/questions'):
   if not self.require('admin'):return
   try:qid=int(p.split('/')[-2]);points=max(1,int(d.get('points',1)));position=max(1,int(d.get('position',1)))
   except:return self.reply({'error':'Invalid quiz question.'},400)
   correct=str(d.get('correct_option','')).upper()
   if correct not in ('A','B','C','D') or any(not str(d.get(k,'')).strip() for k in ('prompt','option_a','option_b','option_c','option_d')):return self.reply({'error':'Complete the question, four answers and correct answer.'},400)
   with db() as c:cur=c.execute('INSERT INTO quiz_questions(quiz_id,prompt,option_a,option_b,option_c,option_d,correct_option,points,position) VALUES(?,?,?,?,?,?,?,?,?)',(qid,str(d['prompt']).strip(),str(d['option_a']).strip(),str(d['option_b']).strip(),str(d['option_c']).strip(),str(d['option_d']).strip(),correct,points,position))
   return self.reply({'ok':True,'id':cur.lastrowid},201)
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
  if p.startswith('/api/admin/questions/'):
   if not self.require('admin'):return
   qid=p.rsplit('/',1)[-1];correct=str(d.get('correct_option','')).upper()
   if correct not in ('A','B','C','D') or any(not str(d.get(k,'')).strip() for k in ('prompt','option_a','option_b','option_c','option_d')):return self.reply({'error':'Complete every question field.'},400)
   with db() as c:c.execute('UPDATE quiz_questions SET prompt=?,option_a=?,option_b=?,option_c=?,option_d=?,correct_option=?,points=?,position=? WHERE id=?',(str(d['prompt']).strip(),str(d['option_a']).strip(),str(d['option_b']).strip(),str(d['option_c']).strip(),str(d['option_d']).strip(),correct,max(1,int(d.get('points',1))),max(1,int(d.get('position',1))),qid))
   return self.reply({'ok':True})
  if p.startswith('/api/admin/quizzes/'):
   if not self.require('admin'):return
   qid=p.rsplit('/',1)[-1];stream=str(d.get('student_stream','ALL')).upper();status=str(d.get('status','draft')).lower()
   if stream not in ('ALL','O/L','A/L') or status not in ('draft','published','closed'):return self.reply({'error':'Invalid quiz settings.'},400)
   with db() as c:
    old=c.execute('SELECT status FROM quizzes WHERE id=?',(qid,)).fetchone()
    if not old:return self.reply({'error':'Quiz not found.'},404)
    question_count=c.execute('SELECT COUNT(*) n FROM quiz_questions WHERE quiz_id=?',(qid,)).fetchone()['n']
    if status=='published' and question_count<1:return self.reply({'error':'Add at least one question before publishing.'},400)
    c.execute('UPDATE quizzes SET title=?,description=?,student_stream=?,duration_minutes=?,starts_at=?,ends_at=?,status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(str(d.get('title','')).strip(),str(d.get('description','')).strip(),stream,max(1,int(d.get('duration_minutes',30))),d.get('starts_at') or None,d.get('ends_at') or None,status,qid))
    if status=='published' and old['status']!='published':c.execute('INSERT INTO announcements(title,body,target_stream) VALUES(?,?,?)',('New quiz available: '+str(d.get('title','')).strip(),'A new timed quiz is available in your Quiz section. Open it before the closing time.',stream))
   return self.reply({'ok':True})
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
  elif p.startswith('/api/admin/questions/'):table='quiz_questions'
  elif p.startswith('/api/admin/quizzes/'):table='quizzes'
  if not table:return self.reply({'error':'Not found'},404)
  rid=p.rsplit('/',1)[-1]
  with db() as c:c.execute(f'DELETE FROM {table} WHERE id=?',(rid,))
  return self.reply({'ok':True})
if __name__=='__main__':
 port=int(sys.argv[1]) if len(sys.argv)>1 else 5500
 init();print(f'ICT with Harsha: http://127.0.0.1:{port}');ThreadingHTTPServer(('127.0.0.1',port),H).serve_forever()
