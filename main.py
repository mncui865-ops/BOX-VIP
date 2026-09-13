# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════╗
║              𝙵𝙱𝙸 𝚂𝚄𝙳𝙰𝙽𝙴𝚂𝙴  —  v3.2 (Railway Ready)      ║
╠══════════════════════════════════════════════════════════╣
║  ✅ حالات + دردشة + رسائل مجهولة + أصدقاء                ║
║  ✅ بحث باليوزر أو بالـ ID                                ║
║  ✅ حالات متعددة لكل مستخدم + تنقل بينها                  ║
║  ✅ صفحة "اكتشف الأشخاص" لكل المسجلين                     ║
║  ✅ حذف صورة البروفايل                                    ║
║  ✅ نسخ اليوزر والـ ID من البروفايل                        ║
║  ✅ دعم Railway Volumes + PostgreSQL                      ║
║  ❌ زر الدعم (تم حذفه)                                    ║
╚══════════════════════════════════════════════════════════╝
"""
import os, re, uuid, random, string, secrets, hashlib, time
from datetime import datetime, timedelta, timezone
from functools import wraps
from collections import defaultdict

# ═══════════════════ التوقيت ═══════════════════
try:
    from zoneinfo import ZoneInfo
    KHARTOUM_TZ = ZoneInfo("Africa/Khartoum")
except Exception:
    KHARTOUM_TZ = timezone(timedelta(hours=2), name="SDT")

UTC_TZ = timezone.utc

def to_sd(dt):
    if dt is None: return None
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_TZ)
        return dt.astimezone(KHARTOUM_TZ)
    except Exception:
        try: return dt + timedelta(hours=2)
        except Exception: return dt

def fmt_sd(dt, fmt="%Y-%m-%d %H:%M"):
    d = to_sd(dt)
    if d is None: return "—"
    try: return d.strftime(fmt)
    except Exception: return "—"

def now_utc_naive():
    return datetime.now(UTC_TZ).replace(tzinfo=None)

# ═══════════════════ Flask ═══════════════════
from flask import (Flask, render_template_string, redirect, url_for, flash,
                   request, session, abort, make_response, send_from_directory, jsonify)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import RequestEntityTooLarge
from sqlalchemy import text, or_, and_, func
from markupsafe import Markup, escape as html_escape

# ═══════════════════ الإعدادات ═══════════════════
SITE_NAME = "𝙵𝙱𝙸 𝚂𝚄𝙳𝙰𝙽𝙴𝚂𝙴"

VOLUME_MOUNT = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "")
if VOLUME_MOUNT and os.path.isdir(VOLUME_MOUNT):
    DATA_DIR = VOLUME_MOUNT
    for sub in ["uploads", "uploads/avatars", "uploads/statuses"]:
        os.makedirs(os.path.join(DATA_DIR, sub), exist_ok=True)
else:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATA_DIR = os.environ.get("DATA_DIR") or os.path.join(BASE_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True)

UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
AVATAR_DIR = os.path.join(UPLOAD_DIR, "avatars")
STATUS_DIR = os.path.join(UPLOAD_DIR, "statuses")
for d in (AVATAR_DIR, STATUS_DIR):
    os.makedirs(d, exist_ok=True)

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///" + os.path.join(DATA_DIR, "sarhni.db")

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["AVATAR_FOLDER"] = AVATAR_DIR
app.config["STATUS_FOLDER"] = STATUS_DIR
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=365)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"

try:
    from flask_cors import CORS
    CORS(app)
except ImportError:
    pass

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ═══════════════════ الصيغ المدعومة ═══════════════════
IMAGE_EXT = {"png","jpg","jpeg","gif","webp","bmp","heic"}
VIDEO_EXT = {"mp4","webm","mov","m4v","ogg","ogv","avi","mkv","3gp","mpeg","mpg"}

IMAGE_MAGIC = [
    (b"\x89PNG\r\n\x1a\n","png"), (b"\xff\xd8\xff","jpg"),
    (b"GIF87a","gif"), (b"GIF89a","gif"),
    (b"RIFF","webp"), (b"BM","bmp"),
]

def _is_video_head(head):
    if len(head) < 12: return False
    if head[4:8] == b"ftyp": return True
    if head.startswith(b"\x1a\x45\xdf\xa3"): return True
    if head.startswith(b"OggS"): return True
    if head.startswith(b"RIFF") and len(head) >= 12 and head[8:12] == b"AVI ": return True
    if head.startswith(b"\x00\x00\x01\xba"): return True
    if head.startswith(b"\x47"): return True
    if head.startswith(b"FLV"): return True
    return False

def check_image_magic(fs):
    try:
        head = fs.stream.read(32); fs.stream.seek(0)
    except Exception: return False
    return any(head.startswith(m) for m,_ in IMAGE_MAGIC)

def check_video_magic(fs):
    try:
        head = fs.stream.read(32); fs.stream.seek(0)
    except Exception: return False
    return _is_video_head(head)

def allowed_image(fn): return "." in fn and fn.rsplit(".",1)[1].lower() in IMAGE_EXT
def allowed_video(fn): return "." in fn and fn.rsplit(".",1)[1].lower() in VIDEO_EXT

# ═══════════════════ rate limit ═══════════════════
_login_attempts = defaultdict(list)
LOGIN_WINDOW = 300
LOGIN_MAX = 8
def is_rate_limited(ip):
    now = time.time()
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < LOGIN_WINDOW]
    return len(_login_attempts[ip]) >= LOGIN_MAX
def record_login_attempt(ip): _login_attempts[ip].append(time.time())

# ═══════════════════ كود الاستعادة ═══════════════════
CODE_ALPHABET = string.ascii_uppercase + string.digits
def gen_recovery_code():
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(20))
def hash_recovery_code(code):
    return hashlib.sha256(code.strip().upper().encode()).hexdigest()
def format_code(code):
    c = code.strip().upper()
    return "-".join(c[i:i+4] for i in range(0, len(c), 4))

# ═══════════════════ النماذج ═══════════════════
def gen_public_id(): return "".join(random.choices(string.digits, k=8))
def gen_device_token(): return secrets.token_urlsafe(32)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(8), unique=True, default=gen_public_id, nullable=False)
    username = db.Column(db.String(5), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    recovery_hash = db.Column(db.String(64), default="", index=True)
    nickname = db.Column(db.String(64), default="")
    bio = db.Column(db.String(200), default="")
    avatar = db.Column(db.String(300), default="")
    is_banned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    profile_views = db.Column(db.Integer, default=0)

    messages = db.relationship("Message", backref="receiver", lazy=True,
                               foreign_keys="Message.receiver_id")
    devices = db.relationship("Device", backref="user", lazy=True,
                              cascade="all, delete-orphan")

    @property
    def nickname_ok(self):
        if not self.nickname: return False
        parts = [p for p in self.nickname.split() if len(p) >= 1]
        return 1 <= len(parts) <= 4

    @property
    def short_name(self): return self.nickname if self.nickname else self.username

    @property
    def created_at_sd(self): return fmt_sd(self.created_at)

    @property
    def last_seen_sd(self): return fmt_sd(self.last_seen)

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_agent = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    sender_name = db.Column(db.String(64), default="مجهول")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    text = db.Column(db.String(300), default="")
    caption = db.Column(db.String(300), default="")
    media = db.Column(db.String(300), default="")
    media_type = db.Column(db.String(10), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="statuses")

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    target_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    reason = db.Column(db.String(300), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    target = db.relationship("User", foreign_keys=[target_id])

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    addressee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(10), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    requester = db.relationship("User", foreign_keys=[requester_id])
    addressee = db.relationship("User", foreign_keys=[addressee_id])
    __table_args__ = (db.UniqueConstraint("requester_id", "addressee_id"),)

class SavedChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    peer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    pinned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", foreign_keys=[user_id])
    __table_args__ = (db.UniqueConstraint("user_id", "peer_id"),)

@login_manager.user_loader
def load_user(uid):
    try:
        return db.session.get(User, int(uid))
    except Exception:
        return None

def init_db():
    with app.app_context():
        db.create_all()
        try:
            insp = db.inspect(db.engine)
            user_cols = [c["name"] for c in insp.get_columns("user")]
            for col, typ in [
                ("recovery_hash","VARCHAR(64) DEFAULT ''"),
                ("nickname","VARCHAR(64) DEFAULT ''"),
                ("last_seen","TIMESTAMP"),
                ("profile_views","INTEGER DEFAULT 0"),
            ]:
                if col not in user_cols:
                    db.session.execute(text(f'ALTER TABLE "user" ADD COLUMN {col} {typ}'))
                    db.session.commit()
            status_cols = [c["name"] for c in insp.get_columns("status")]
            for col, typ in [
                ("caption","VARCHAR(300) DEFAULT ''"),
                ("media","VARCHAR(300) DEFAULT ''"),
                ("media_type","VARCHAR(10) DEFAULT ''"),
            ]:
                if col not in status_cols:
                    db.session.execute(text(f"ALTER TABLE status ADD COLUMN {col} {typ}"))
                    db.session.commit()
            for idx in [
                'CREATE INDEX IF NOT EXISTS idx_user_recovery ON "user"(recovery_hash)',
            ]:
                try:
                    db.session.execute(text(idx)); db.session.commit()
                except Exception: db.session.rollback()
        except Exception as e:
            print(f"[init_db] migration warning: {e}")
            db.session.rollback()

init_db()

# ═══════════════════ أدوات مساعدة ═══════════════════
def is_valid_username(u):
    return bool(re.match(r"^[a-zA-Z0-9_]{3,5}$", u))

def is_valid_nickname(name):
    if not name: return False
    parts = [p for p in name.strip().split() if len(p) >= 1]
    return 1 <= len(parts) <= 4

def avatar_url(user):
    if user.avatar: return url_for("serve_upload", subpath=f"avatars/{user.avatar}")
    return f"https://ui-avatars.com/api/?name={user.username}&background=e5e7eb&color=374151&size=200"

def upload_url(kind, filename):
    return url_for("serve_upload", subpath=f"{kind}/{filename}")

def cleanup_old_statuses():
    cutoff = now_utc_naive() - timedelta(hours=24)
    old = Status.query.filter(Status.created_at < cutoff).all()
    if not old: return
    for s in old:
        if s.media:
            try: os.remove(os.path.join(app.config["STATUS_FOLDER"], s.media))
            except OSError: pass
        db.session.delete(s)
    db.session.commit()

def save_device(user):
    token = gen_device_token()
    db.session.add(Device(user_id=user.id, token=token,
        user_agent=request.headers.get("User-Agent","")[:255]))
    db.session.commit()
    return token

def unread_chat_count(user_id):
    return ChatMessage.query.filter_by(receiver_id=user_id, is_read=False).count()

def get_friends(user_id):
    rows = Friendship.query.filter(Friendship.status=="accepted",
        or_(Friendship.requester_id==user_id, Friendship.addressee_id==user_id)).all()
    ids = [r.addressee_id if r.requester_id==user_id else r.requester_id for r in rows]
    if not ids: return []
    return User.query.filter(User.id.in_(ids)).all()

def get_friend_ids(user_id):
    return {u.id for u in get_friends(user_id)}

def friendship_status(a_id, b_id):
    r = Friendship.query.filter(or_(
        and_(Friendship.requester_id==a_id, Friendship.addressee_id==b_id),
        and_(Friendship.requester_id==b_id, Friendship.addressee_id==a_id))).first()
    if not r: return "none", None
    if r.status == "accepted": return "friends", r
    if r.requester_id == a_id: return "pending_out", r
    return "pending_in", r

def render_mentions(text):
    if not text:
        return Markup("")
    safe_text = html_escape(str(text))
    def repl(m):
        uname = m.group(1).lower()
        u = User.query.filter_by(username=uname).first()
        if u:
            return f'<a href="{url_for("view_profile", username=uname)}" class="mention">@{uname}</a>'
        return m.group(0)
    return Markup(re.sub(r"@([a-zA-Z0-9_]{3,5})\b", repl, safe_text))

@app.route("/uploads/<path:subpath>")
def serve_upload(subpath):
    return send_from_directory(UPLOAD_DIR, subpath)

@app.before_request
def before_each_request():
    if not current_user.is_authenticated: return
    allowed = {"set_nickname","logout","static","serve_upload","welcome"}
    if request.endpoint in allowed: return
    if not current_user.nickname_ok:
        return redirect(url_for("set_nickname"))

@app.errorhandler(413)
@app.errorhandler(RequestEntityTooLarge)
def handle_too_large(e):
    flash("حجم الملف كبير جدًا. الحد الأقصى 200 ميجابايت.","error")
    return redirect(request.referrer or url_for("feed"))

# ═══════════════════ CSS ═══════════════════
BASE_STYLE = """
<style>
:root{
  --bg:#f7f7f8;--surface:#fff;--border:#e5e7eb;--text:#111827;--muted:#6b7280;
  --accent:#111827;--accent-hover:#374151;--danger:#dc2626;--success:#16a34a;
  --blue:#2563eb;--radius:14px;
  --glow:0 0 8px rgba(59,130,246,.8), 0 0 16px rgba(59,130,246,.45);
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{
  font-family:-apple-system,'Segoe UI','Tahoma',system-ui,sans-serif;
  background:var(--bg);color:var(--text);min-height:100vh;
  display:flex;justify-content:center;padding:28px 16px 60px;line-height:1.6;
}
.container{width:100%;max-width:560px}
.brand{text-align:center;margin-bottom:26px}
.brand h1{
  font-size:28px;font-weight:800;letter-spacing:1px;line-height:1.4;
  font-family:'Segoe UI Symbol','Apple Symbols','Noto Sans Symbols 2','Arial Unicode MS',-apple-system,sans-serif;
}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:24px 22px;margin-bottom:14px;}
.card.center{text-align:center}
h2{font-size:17px;font-weight:700;text-align:center;margin-bottom:18px}
label{display:block;font-size:13px;color:var(--muted);margin:12px 0 6px;font-weight:500}
input,textarea,select{width:100%;padding:12px 14px;border-radius:10px;
  border:1px solid var(--border);background:var(--surface);color:var(--text);
  font-family:inherit;font-size:15px;transition:.15s;}
input:focus,textarea:focus{outline:none;border-color:var(--accent);
  box-shadow:0 0 0 3px rgba(17,24,39,.08);}
textarea{resize:vertical;min-height:80px}
button{width:100%;padding:12px;border:none;border-radius:10px;background:var(--accent);
  color:#fff;cursor:pointer;font-size:15px;font-weight:600;margin-top:14px;transition:.15s;}
button:hover{background:var(--accent-hover)}
a{color:var(--text);text-decoration:none}
a:hover{text-decoration:underline}
a.link-center{display:block;text-align:center;margin-top:14px;font-size:14px;color:var(--muted)}
a.link-center:hover{color:var(--text);text-decoration:none}
.pw-wrap{position:relative}
.pw-wrap input{padding-left:46px}
.pw-toggle{position:absolute;left:8px;top:50%;transform:translateY(-50%);
  background:none;border:none;color:var(--accent);font-size:18px;cursor:pointer;
  width:36px;height:36px;padding:0;margin:0;display:flex;align-items:center;
  justify-content:center;border-radius:8px;}
.avatar{width:96px;height:96px;border-radius:50%;object-fit:cover;
  border:2px solid var(--border);margin-bottom:14px;cursor:pointer;transition:.15s;}
.avatar:hover{border-color:var(--blue);box-shadow:0 0 0 4px rgba(37,99,235,.15)}
.avatar-sm{width:40px;height:40px;border-radius:50%;object-fit:cover;cursor:pointer;}
.avatar-sm:hover{box-shadow:0 0 0 2px var(--blue)}
.name{font-size:20px;font-weight:800}
.username{color:var(--muted);font-size:14px;margin-top:2px}
.uid{display:inline-block;margin-top:10px;padding:4px 12px;background:var(--bg);
  border:1px solid var(--border);border-radius:999px;font-size:12px;
  color:var(--muted);direction:ltr;}
.bio{margin-top:14px;font-size:15px;color:#374151;line-height:1.6}
.actions{margin-top:22px;display:flex;flex-direction:column;gap:10px}
.btn{display:block;padding:12px;border-radius:10px;border:1px solid var(--border);
  font-size:15px;font-weight:600;text-align:center;text-decoration:none;cursor:pointer;
  transition:.15s;background:var(--surface);color:var(--text);}
.btn:hover{background:var(--bg);text-decoration:none}
.btn-primary{background:var(--accent);color:#fff;border-color:var(--accent)}
.btn-primary:hover{background:var(--accent-hover);border-color:var(--accent-hover)}
.btn-danger{color:var(--danger);border-color:#fecaca;background:#fef2f2}
.btn-danger:hover{background:#fee2e2}
.btn-disabled{background:#e5e7eb;color:#9ca3af;cursor:not-allowed;border-color:#d1d5db}
.btn-disabled:hover{background:#e5e7eb;text-decoration:none}
.btn-sm{padding:8px 12px;font-size:13px;width:auto;display:inline-block;margin:0}
.flash{padding:11px 14px;border-radius:10px;margin-bottom:12px;font-size:14px;border:1px solid}
.success{background:#f0fdf4;color:#166534;border-color:#bbf7d0}
.error{background:#fef2f2;color:#991b1b;border-color:#fecaca}
.info{background:#eff6ff;color:#1e40af;border-color:#bfdbfe}
.footer{text-align:center;margin-top:20px;color:var(--muted);font-size:12px;
  font-family:'Segoe UI Symbol','Apple Symbols','Noto Sans Symbols 2',sans-serif;}
.topbar{display:flex;justify-content:space-around;align-items:center;gap:4px;
  margin-bottom:14px;padding:10px 6px;background:var(--surface);
  border:1px solid var(--border);border-radius:var(--radius);}
.topbar a{display:flex;flex-direction:column;align-items:center;gap:3px;
  font-size:11px;color:var(--muted);flex:1;padding:6px 2px;border-radius:8px;
  transition:.15s;text-decoration:none;position:relative;}
.topbar a .ic{font-size:20px;line-height:1;color:var(--blue);
  text-shadow:var(--glow);transition:.2s;}
.topbar a:hover{background:var(--bg);color:var(--text);text-decoration:none}
.topbar a:hover .ic{transform:scale(1.1)}
.badge{position:absolute;top:2px;left:8px;background:#dc2626;color:#fff;
  font-size:10px;min-width:16px;height:16px;border-radius:999px;display:flex;
  align-items:center;justify-content:center;padding:0 4px;}
.acct-box{background:linear-gradient(135deg,#eef2ff,#f5f3ff);border:1px solid #c7d2fe;
  border-radius:12px;padding:14px;margin-bottom:14px;direction:ltr;text-align:left;}
.acct-row{display:flex;justify-content:space-between;align-items:center;
  padding:6px 0;font-size:14px;}
.acct-row .k{color:#6b7280;font-size:12px;text-transform:uppercase;letter-spacing:.5px}
.acct-row .v{font-family:monospace;font-weight:700;color:#1e3a8a;font-size:13px;
  display:flex;align-items:center;gap:6px}
.copy-btn{background:#fff;border:1px solid #c7d2fe;color:#3730a3;padding:4px 10px;
  border-radius:8px;font-size:12px;cursor:pointer;margin:0;width:auto;
  font-weight:600;transition:.15s;}
.copy-btn:hover{background:#eef2ff}
.copy-btn.done{background:#dcfce7;border-color:#86efac;color:#166534}
.recovery-box{background:#fffbeb;border:2px dashed #f59e0b;border-radius:12px;
  padding:16px;margin:14px 0;text-align:center;}
.recovery-box .code{font-size:20px;font-weight:800;color:#92400e;letter-spacing:2px;
  line-height:1.8;margin:10px 0;direction:ltr;font-family:'Courier New',monospace;
  word-break:break-all;}
.recovery-box .warn{font-size:12px;color:#b45309}
.status-strip{display:flex;gap:12px;overflow-x:auto;padding-bottom:6px}
.status-item{flex:0 0 auto;text-align:center;width:72px;text-decoration:none;color:inherit}
.status-item .ring{display:inline-block;padding:2px;border-radius:50%;
  background:linear-gradient(135deg,#16a34a,#84cc16);position:relative;}
.status-item img{width:60px;height:60px;border-radius:50%;object-fit:cover;
  border:2px solid #fff;display:block;}
.status-item .sname{font-size:11px;color:var(--muted);margin-top:4px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.status-item .vid-tag{position:absolute;bottom:0;right:0;background:rgba(0,0,0,.7);
  color:#fff;font-size:9px;padding:1px 5px;border-radius:8px;border:2px solid #fff;
  font-weight:700;}
.status-item .count-badge{position:absolute;top:-2px;left:-2px;background:#dc2626;
  color:#fff;font-size:10px;min-width:18px;height:18px;border-radius:999px;
  display:flex;align-items:center;justify-content:center;border:2px solid #fff;
  font-weight:700;}
.status-view{position:fixed;inset:0;background:#000;z-index:1000;display:flex;
  flex-direction:column;align-items:center;justify-content:center;padding:20px;
  overflow-y:auto;}
.status-view img,.status-view video{max-width:100%;max-height:65vh;border-radius:12px;
  object-fit:contain;}
.status-view .stext{color:#fff;font-size:20px;text-align:center;margin-top:16px;
  max-width:600px;line-height:1.6;}
.status-view .scaption{color:#e5e7eb;font-size:15px;text-align:center;margin-top:10px;
  max-width:600px;line-height:1.5;font-style:italic;}
.status-view .smeta{color:#9ca3af;font-size:13px;margin-top:12px;text-align:center}
.status-view .close{position:absolute;top:16px;left:16px;color:#fff;font-size:22px;
  background:rgba(255,255,255,.12);border:none;width:40px;height:40px;border-radius:50%;
  cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;margin:0;}
.status-owner-actions{position:absolute;top:16px;right:16px;display:flex;gap:8px;z-index:10}
.status-owner-actions .sbtn{display:inline-flex;align-items:center;gap:4px;
  padding:8px 14px;border-radius:8px;font-size:13px;font-weight:600;
  text-decoration:none;cursor:pointer;border:none;transition:.15s;width:auto;margin:0;color:#fff}
.status-owner-actions .sbtn.edit{background:rgba(37,99,235,.9)}
.status-owner-actions .sbtn.edit:hover{background:rgba(37,99,235,1);text-decoration:none}
.status-owner-actions .sbtn.del{background:rgba(220,38,38,.9)}
.status-owner-actions .sbtn.del:hover{background:rgba(220,38,38,1);text-decoration:none}
.status-nav{position:absolute;bottom:20px;left:0;right:0;display:flex;
  justify-content:center;gap:10px;z-index:20;align-items:center}
.status-nav .nav-btn{background:rgba(255,255,255,.2);color:#fff;border:none;
  padding:8px 16px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;
  width:auto;margin:0}
.status-nav .nav-btn:hover{background:rgba(255,255,255,.35)}
.status-nav .counter{color:#fff;font-size:13px}
.composer{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius);padding:14px;margin-bottom:14px;}
.composer textarea{border:none;background:transparent;min-height:70px;
  font-size:15px;padding:6px 2px;resize:vertical;}
.composer textarea:focus{box-shadow:none}
.composer-bar{display:flex;justify-content:space-between;align-items:center;
  gap:8px;margin-top:6px;flex-wrap:wrap;}
.composer-icons{display:flex;gap:6px}
.icon-btn{background:var(--bg);border:1px solid var(--border);color:var(--text);
  width:36px;height:36px;border-radius:9px;font-size:17px;cursor:pointer;
  display:flex;align-items:center;justify-content:center;transition:.15s;
  padding:0;margin:0;}
.icon-btn:hover{background:#eef0f3}
.mention{color:var(--blue);font-weight:700;background:#eff6ff;
  padding:1px 6px;border-radius:6px;text-decoration:none}
.mention:hover{background:#dbeafe;text-decoration:none}
.empty{text-align:center;color:var(--muted);font-size:14px;padding:20px 0}
.list-item{display:flex;align-items:center;gap:10px;background:#f7f7f8;
  border:1px solid #e5e7eb;border-radius:10px;padding:10px;
  margin-bottom:8px;text-decoration:none;color:inherit;}
.list-item:hover{background:#eef0f3;text-decoration:none}
.list-item .li-name{font-weight:700}
.list-item .li-sub{color:var(--muted);font-size:12px}
.list-item .li-actions{margin-right:auto;display:flex;gap:6px;align-items:center}
.chat-header{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.chat-box{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius);padding:16px;height:60vh;overflow-y:auto;
  display:flex;flex-direction:column;gap:10px;}
.bubble{max-width:75%;padding:10px 14px;border-radius:14px;font-size:15px;
  line-height:1.5;word-wrap:break-word;}
.bubble.me{align-self:flex-start;background:#eef2ff;border:1px solid #c7d2fe}
.bubble.them{align-self:flex-end;background:var(--bg);border:1px solid var(--border)}
.bubble .t{font-size:10px;color:var(--muted);margin-top:4px;display:block}
.chat-input{display:flex;gap:8px;margin-top:10px}
.chat-input input{flex:1;margin:0}
.chat-input button{width:auto;padding:12px 20px;margin:0}
.msg{background:var(--bg);border:1px solid var(--border);border-radius:12px;
  padding:14px;margin-bottom:10px;}
.msg .meta{font-size:12px;color:var(--muted);margin-bottom:6px}
.msg .body{font-size:15px;line-height:1.5;white-space:pre-wrap}
.privacy-note{background:#fef3c7;border:1px solid #fcd34d;color:#78350f;
  border-radius:10px;padding:10px 14px;font-size:13px;margin-bottom:14px;}
.device-row{display:flex;justify-content:space-between;align-items:center;
  background:var(--bg);border:1px solid var(--border);border-radius:10px;
  padding:10px 12px;margin-bottom:8px;font-size:13px;}
.device-row .ua{color:var(--muted);font-size:11px;max-width:280px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.avatar-view{position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:2000;
  display:flex;align-items:center;justify-content:center;padding:20px;}
.avatar-view img{max-width:95vw;max-height:90vh;border-radius:12px;
  object-fit:contain;box-shadow:0 0 40px rgba(255,255,255,.15);}
.avatar-view .close-av{position:absolute;top:20px;right:20px;color:#fff;font-size:24px;
  background:rgba(255,255,255,.15);border:none;width:44px;height:44px;
  border-radius:50%;cursor:pointer;display:flex;align-items:center;
  justify-content:center;padding:0;margin:0;}
.avatar-view .close-av:hover{background:rgba(255,255,255,.3)}
.social-box{
  background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius);padding:16px;margin-bottom:14px;text-align:center;
}
.social-box h3{
  font-size:14px;font-weight:700;color:var(--muted);
  margin-bottom:12px;letter-spacing:.5px;
}
.social-btns{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.social-btn{
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  flex:1;min-width:130px;padding:11px 16px;border-radius:10px;
  font-size:14px;font-weight:700;text-decoration:none;cursor:pointer;
  transition:.18s;border:1px solid transparent;
}
.social-btn:hover{transform:translateY(-2px);text-decoration:none}
.social-btn svg{width:20px;height:20px;flex-shrink:0}
.social-btn.tg{background:#229ED9;color:#fff}
.social-btn.tg:hover{background:#1c87ba;color:#fff}
.social-btn.fb{background:#1877F2;color:#fff}
.social-btn.fb:hover{background:#1461c9;color:#fff}
.social-user{
  font-size:12px;color:var(--muted);margin-top:6px;
  direction:ltr;font-family:'Courier New',monospace;font-weight:700;
}
</style>
"""

def render_page(body, title=None, **ctx):
    t = title or SITE_NAME
    return render_template_string(
        "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>{{ t }} — {{ site }}</title>" + BASE_STYLE + "</head><body><div class='container'>"
        "<div class='brand'><h1>{{ site }}</h1></div>"
        + body + "</div>"
        "<script>"
        "function togglePw(id){var e=document.getElementById(id);if(!e)return;"
        "e.type=e.type==='password'?'text':'password';}"
        "function previewStatusMedia(i){var f=i.files[0];if(!f)return;var u=URL.createObjectURL(f);"
        "var b=document.getElementById('status-preview');if(!b)return;"
        "if(f.type.startsWith('video')){b.innerHTML='<video style=\"max-width:100%;max-height:240px;border-radius:10px;margin-top:10px\" controls src=\"'+u+'\"></video>';}"
        "else{b.innerHTML='<img style=\"max-width:100%;max-height:240px;border-radius:10px;margin-top:10px\" src=\"'+u+'\">';}}"
        "function openStatus(id){document.getElementById('sv-'+id).style.display='flex';}"
        "function closeStatus(id){document.getElementById('sv-'+id).style.display='none';}"
        "function openAvatar(url){var el=document.getElementById('avatar-viewer');"
        "var img=document.getElementById('avatar-viewer-img');"
        "if(el&&img){img.src=url;el.style.display='flex';}}"
        "function closeAvatar(){var el=document.getElementById('avatar-viewer');"
        "if(el)el.style.display='none';}"
        "function fallbackCopy(t){var ta=document.createElement('textarea');"
        "ta.value=t;ta.style.position='fixed';ta.style.opacity='0';"
        "document.body.appendChild(ta);ta.select();try{document.execCommand('copy');}catch(e){}"
        "document.body.removeChild(ta);}"
        "function copyText(t,b){var done=function(){if(!b)return;var o=b.textContent;"
        "b.textContent='\u2713 \u062a\u0645';b.classList.add('done');"
        "setTimeout(function(){b.textContent=o;b.classList.remove('done');},1200);};"
        "if(navigator.clipboard&&window.isSecureContext){"
        "navigator.clipboard.writeText(t).then(done).catch(function(){fallbackCopy(t);done();});"
        "}else{fallbackCopy(t);done();}}"
        "function scrollChat(){var b=document.getElementById('chatbox');if(b)b.scrollTop=b.scrollHeight;}"
        "function formatCodeInput(el){el.value=el.value.toUpperCase().replace(/[^A-Z0-9]/g,'');}"
        "document.addEventListener('DOMContentLoaded',scrollChat);"
        "document.addEventListener('keydown',function(e){if(e.key==='Escape')closeAvatar();});"
        "</script>"
        "<div class='avatar-view' id='avatar-viewer' style='display:none' onclick='closeAvatar()'>"
        "<button class='close-av' onclick='event.stopPropagation();closeAvatar()'>✕</button>"
        "<img id='avatar-viewer-img' src='' onclick='event.stopPropagation()'>"
        "</div>"
        "</body></html>",
        t=t, site=SITE_NAME, **ctx)

FLASH_BLOCK = """{% with msgs=get_flashed_messages(with_categories=true) %}
{% for c,m in msgs %}<div class="flash {{c}}">{{m}}</div>{% endfor %}{% endwith %}"""

def topbar_html(chat_badge=""):
    return f"""<div class="topbar">
<a href="{url_for('feed')}"><span class="ic">⌂</span>الرئيسية</a>
<a href="{url_for('discover')}"><span class="ic">👥</span>أشخاص</a>
<a href="{url_for('search')}"><span class="ic">⌕</span>بحث</a>
<a href="{url_for('chats')}"><span class="ic">◈</span>الدردشات{chat_badge}</a>
<a href="{url_for('friends_list')}"><span class="ic">♡</span>الأصدقاء</a>
<a href="{url_for('profile_me')}"><span class="ic">☺</span>بروفايلي</a>
</div>"""

def badge_html():
    if current_user.is_authenticated:
        c = unread_chat_count(current_user.id)
        if c: return f'<span class="badge">{c}</span>'
    return ''

# ═══════════════════ المصادقة ═══════════════════
@app.route("/")
def index():
    if current_user.is_authenticated: return redirect(url_for("feed"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET","POST"])
def register():
    if current_user.is_authenticated: return redirect(url_for("feed"))
    if request.method == "POST":
        username = request.form.get("username","").strip().lower().lstrip("@")
        password = request.form.get("password","")
        confirm = request.form.get("confirm","")
        if not is_valid_username(username):
            flash("اليوزر: 3 إلى 5 أحرف إنجليزية/أرقام/_ فقط.","error")
            return redirect(url_for("register"))
        if len(password) < 8:
            flash("كلمة المرور 8 أحرف على الأقل.","error")
            return redirect(url_for("register"))
        if password != confirm:
            flash("كلمتا المرور غير متطابقتين.","error")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash("اليوزر محجوز، جرّب غيره.","error")
            return redirect(url_for("register"))
        pid = gen_public_id()
        while User.query.filter_by(public_id=pid).first():
            pid = gen_public_id()
        recovery = gen_recovery_code()
        while User.query.filter_by(recovery_hash=hash_recovery_code(recovery)).first():
            recovery = gen_recovery_code()
        user = User(username=username, public_id=pid,
                    password_hash=generate_password_hash(password),
                    recovery_hash=hash_recovery_code(recovery))
        db.session.add(user); db.session.commit()
        token = save_device(user)
        login_user(user, remember=True)
        session.permanent = True
        session["show_recovery"] = recovery
        resp = make_response(redirect(url_for("welcome")))
        resp.set_cookie("device_token", token, max_age=60*60*24*365,
                        httponly=True, samesite="Lax",
                        secure=app.config["SESSION_COOKIE_SECURE"])
        return resp
    return render_page(FLASH_BLOCK + """
    <div class="card"><h2>إنشاء حساب</h2>
    <form method="POST">
    <label>اليوزر (3-5 أحرف إنجليزية — بدون @)</label>
    <input name="username" maxlength="5" placeholder="username" required
           pattern="[a-zA-Z0-9_]{3,5}" autocomplete="off">
    <label>كلمة المرور (8+)</label>
    <div class="pw-wrap">
      <input name="password" id="pw1" type="password" required>
      <button type="button" class="pw-toggle" onclick="togglePw('pw1')">👁</button>
    </div>
    <label>تأكيد كلمة المرور</label>
    <div class="pw-wrap">
      <input name="confirm" id="pw2" type="password" required>
      <button type="button" class="pw-toggle" onclick="togglePw('pw2')">👁</button>
    </div>
    <button type="submit">تسجيل</button></form>
    <a class="link-center" href="{{ url_for('login') }}">لديك حساب؟ سجّل الدخول</a>
    <a class="link-center" href="{{ url_for('recover') }}">عندك كود استعادة؟ ادخل مباشرة</a>
    </div>""", title="تسجيل")

@app.route("/welcome")
@login_required
def welcome():
    recovery = session.pop("show_recovery", None)
    if not recovery: return redirect(url_for("set_nickname"))
    formatted = format_code(recovery)
    return render_page("""
    <div class="card center">
      <h2>🎉 أهلاً بك</h2>
      <p style="color:#6b7280;font-size:13px;margin-bottom:12px">
        احفظ هذا الكود. لن يظهر مرة أخرى.</p>
      <div class="acct-box">
        <div class="acct-row"><span class="k">USERNAME</span>
          <span class="v">@{{ user.username }}
          <button class="copy-btn" onclick="copyText('{{ user.username }}',this)">نسخ</button></span></div>
        <div class="acct-row"><span class="k">ID</span>
          <span class="v">{{ user.public_id }}
          <button class="copy-btn" onclick="copyText('{{ user.public_id }}',this)">نسخ</button></span></div>
      </div>
      <div class="recovery-box">
        <div style="font-size:13px;font-weight:700;color:#92400e">🔐 كود الاستعادة (20 خانة)</div>
        <div class="code">{{ formatted }}</div>
        <div class="warn"><b>مهم جدًا:</b> هذا الكود هو مفتاحك الوحيد لاستعادة حسابك.</div>
        <button class="copy-btn" style="margin-top:10px"
                onclick="copyText('{{ recovery }}',this)">نسخ الكود</button>
      </div>
      <a class="btn btn-primary" href="{{ url_for('set_nickname') }}">فهمت، أكمل</a>
    </div>""", title="مرحبًا", user=current_user, recovery=recovery, formatted=formatted)

@app.route("/set-nickname", methods=["GET","POST"])
@login_required
def set_nickname():
    if current_user.nickname_ok: return redirect(url_for("feed"))
    if request.method == "POST":
        nickname = request.form.get("nickname","").strip()
        if not is_valid_nickname(nickname):
            flash("اللقب: من كلمة إلى 4 كلمات.","error")
            return redirect(url_for("set_nickname"))
        current_user.nickname = nickname
        db.session.commit()
        flash("تم حفظ اللقب. أهلاً بك!","success")
        return redirect(url_for("feed"))
    return render_page(FLASH_BLOCK + """
    <div class="card">
      <h2>اختر لقبك</h2>
      <p style="color:#6b7280;font-size:13px;text-align:center;margin-bottom:12px">
        من كلمة واحدة إلى 4 كلمات.</p>
      <form method="POST">
      <label>اللقب</label>
      <input name="nickname" maxlength="64" required placeholder="مثال: القمر الساهر">
      <button type="submit">حفظ ومتابعة</button></form>
    </div>""", title="اللقب")

@app.route("/recover", methods=["GET","POST"])
def recover():
    if current_user.is_authenticated: return redirect(url_for("feed"))
    if request.method == "POST":
        code = request.form.get("code","").strip().upper().replace("-","").replace(" ","")
        if len(code) != 20:
            flash("الكود يجب أن يكون 20 خانة.","error")
            return redirect(url_for("recover"))
        h = hash_recovery_code(code)
        user = User.query.filter_by(recovery_hash=h).first()
        if not user:
            flash("الكود غير صحيح أو مستخدم من قبل.","error")
            return redirect(url_for("recover"))
        if user.is_banned:
            flash("هذا الحساب محظور.","error")
            return redirect(url_for("recover"))
        new_code = gen_recovery_code()
        while User.query.filter_by(recovery_hash=hash_recovery_code(new_code)).first():
            new_code = gen_recovery_code()
        user.recovery_hash = hash_recovery_code(new_code)
        user.last_seen = now_utc_naive()
        db.session.commit()
        token = save_device(user)
        login_user(user, remember=True)
        session.permanent = True
        session["show_recovery"] = new_code
        flash(f"تم الدخول. أهلاً @{user.username}! كودك الجديد أدناه.","success")
        resp = make_response(redirect(url_for("welcome")))
        resp.set_cookie("device_token", token, max_age=60*60*24*365,
                        httponly=True, samesite="Lax",
                        secure=app.config["SESSION_COOKIE_SECURE"])
        return resp
    return render_page(FLASH_BLOCK + """
    <div class="card">
      <h2>🔐 استعادة الحساب بالكود</h2>
      <p style="color:#6b7280;font-size:13px;text-align:center;margin-bottom:16px">
        الصق كود الاستعادة (20 خانة).</p>
      <form method="POST" onsubmit="return validateCode()">
        <label>كود الاستعادة</label>
        <input name="code" id="recovery-input" maxlength="24"
               required autocomplete="off" autofocus
               style="direction:ltr;font-family:'Courier New',monospace;
                      font-size:16px;letter-spacing:2px;text-align:center"
               placeholder="XXXX-XXXX-XXXX-XXXX-XXXX"
               oninput="formatCodeInput(this)">
        <button type="submit">🔓 استعادة ودخول</button>
      </form>
      <a class="link-center" href="{{ url_for('login') }}">رجوع لتسجيل الدخول</a>
    </div>
    <script>
      function validateCode(){
        var v=document.getElementById('recovery-input').value
              .toUpperCase().replace(/[^A-Z0-9]/g,'');
        if(v.length!==20){alert('الكود يجب أن يكون 20 خانة (حاليًا: '+v.length+')');return false;}
        document.getElementById('recovery-input').value=v;
        return true;
      }
    </script>""", title="استعادة")

@app.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated: return redirect(url_for("feed"))
    if request.method == "POST":
        ip = request.remote_addr or "?"
        if is_rate_limited(ip):
            flash("محاولات كثيرة. انتظر 5 دقائق.","error")
            return redirect(url_for("login"))
        username = request.form.get("username","").strip().lower().lstrip("@")
        password = request.form.get("password","")
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            record_login_attempt(ip)
            flash("بيانات الدخول غير صحيحة.","error"); return redirect(url_for("login"))
        if user.is_banned:
            flash("حسابك محظور.","error"); return redirect(url_for("login"))
        user.last_seen = now_utc_naive()
        token = save_device(user)
        db.session.commit()
        login_user(user, remember=True)
        session.permanent = True
        resp = make_response(redirect(url_for("feed")))
        resp.set_cookie("device_token", token, max_age=60*60*24*365,
                        httponly=True, samesite="Lax",
                        secure=app.config["SESSION_COOKIE_SECURE"])
        return resp
    return render_page(FLASH_BLOCK + """
    <div class="card"><h2>تسجيل الدخول</h2>
    <form method="POST">
    <label>اليوزر</label>
    <input name="username" placeholder="username" required autocomplete="off">
    <label>كلمة المرور</label>
    <div class="pw-wrap">
      <input name="password" id="pw" type="password" required>
      <button type="button" class="pw-toggle" onclick="togglePw('pw')">👁</button>
    </div>
    <button type="submit">دخول</button></form>
    <a class="link-center" href="{{ url_for('register') }}">ليس لديك حساب؟ سجّل الآن</a>
    <a class="link-center" href="{{ url_for('recover') }}" style="color:#2563eb;font-weight:700">
      🔑 نسيت اليوزر أو كلمة السر؟ ادخل بالكود
    </a>
    </div>

    <div class="social-box">
      <h3>تواصل معنا</h3>
      <div class="social-btns">
        <a class="social-btn tg" href="https://t.me/MRDPY" target="_blank" rel="noopener">
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/>
          </svg>
          تلغرام
        </a>
        <a class="social-btn fb" href="https://www.facebook.com/profile.php?id=61579274721625" target="_blank" rel="noopener">
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M22 12.06C22 6.5 17.52 2 12 2S2 6.5 2 12.06c0 5.02 3.66 9.18 8.44 9.94v-7.03H7.9v-2.91h2.54V9.85c0-2.51 1.49-3.9 3.77-3.9 1.09 0 2.24.2 2.24.2v2.47h-1.26c-1.24 0-1.63.78-1.63 1.57v1.87h2.78l-.44 2.91h-2.34V22c4.78-.76 8.44-4.92 8.44-9.94z"/>
          </svg>
          فيسبوك
        </a>
      </div>
      <div class="social-user">@MRDPY</div>
    </div>
    """, title="دخول")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    resp = make_response(redirect(url_for("login")))
    resp.delete_cookie("device_token")
    return resp

# ═══════════════════ البروفايل ═══════════════════
@app.route("/profile/me")
@login_required
def profile_me():
    return redirect(url_for("view_profile", username=current_user.username))

@app.route("/u/<username>/avatar")
def view_avatar_full(username):
    user = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not user or not user.avatar: abort(404)
    return render_page(f"""
    <div class="card center">
      <img src="{url_for('serve_upload', subpath='avatars/' + user.avatar)}"
           style="max-width:100%;border-radius:14px;object-fit:contain;max-height:80vh">
      <div class="name" style="margin-top:14px">{user.short_name}</div>
      <div class="username">@{user.username}</div>
      <a class="btn" href="{url_for('view_profile', username=user.username)}"
         style="margin-top:14px">← رجوع للبروفايل</a>
    </div>""", title=f"صورة {user.username}")

@app.route("/u/<username>")
def view_profile(username):
    user = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not user or user.is_banned:
        flash("المستخدم غير موجود.","error"); return redirect(url_for("index"))
    if not current_user.is_authenticated:
        flash("سجّل الدخول لعرض البروفايل.","error"); return redirect(url_for("login"))

    is_own = current_user.id == user.id
    friend_state, _ = ("none", None)
    if not is_own:
        friend_state, _ = friendship_status(current_user.id, user.id)
    is_friend = friend_state == "friends"

    if not is_own:
        try:
            user.profile_views = (user.profile_views or 0) + 1
            db.session.commit()
        except Exception: db.session.rollback()

    badge = badge_html()
    av_url = avatar_url(user)

    joined_str = "—"; last_seen_str = "—"
    try: joined_str = user.created_at_sd
    except Exception: pass
    try: last_seen_str = user.last_seen_sd
    except Exception: pass

    if is_own or is_friend:
        profile_html = f"""
        <div class="name">{user.short_name}</div>
        <div class="username">@{user.username}</div>
        <div class="uid">ID: {user.public_id}</div>

        <div class="acct-box" style="margin-top:12px">
          <div class="acct-row">
            <span class="k">USERNAME</span>
            <span class="v">@{user.username}
              <button class="copy-btn"
                      onclick="copyText('{user.username}', this)">نسخ</button>
            </span>
          </div>
          <div class="acct-row">
            <span class="k">ID</span>
            <span class="v">{user.public_id}
              <button class="copy-btn"
                      onclick="copyText('{user.public_id}', this)">نسخ</button>
            </span>
          </div>
          <div class="acct-row">
            <span class="k">NICKNAME</span>
            <span class="v" style="font-family:inherit">{user.nickname or '—'}</span>
          </div>
          <div class="acct-row">
            <span class="k">JOINED (SD)</span>
            <span class="v" style="font-family:inherit">{joined_str}</span>
          </div>
          <div class="acct-row">
            <span class="k">LAST SEEN (SD)</span>
            <span class="v" style="font-family:inherit">{last_seen_str}</span>
          </div>
          <div class="acct-row">
            <span class="k">VIEWS</span>
            <span class="v">{user.profile_views or 0}</span>
          </div>
        </div>
        <div style="display:flex;gap:8px;justify-content:center;margin-top:10px;flex-wrap:wrap">
          <button class="copy-btn" style="padding:8px 14px"
                  onclick="copyText('@{user.username}', this)">📋 نسخ اليوزر</button>
          <button class="copy-btn" style="padding:8px 14px"
                  onclick="copyText('{user.public_id}', this)">📋 نسخ الـ ID</button>
          <button class="copy-btn" style="padding:8px 14px"
                  onclick="copyText('@{user.username} | ID: {user.public_id}', this)">📋 نسخ الكل</button>
        </div>"""
        if user.bio: profile_html += f'<div class="bio">{user.bio}</div>'
    else:
        profile_html = f"""
        <div class="name">@{user.username}</div>
        <div class="uid">ID: {user.public_id}</div>
        <div class="privacy-note">🔒 البيانات الكاملة تظهر للأصدقاء فقط.</div>
        <div style="display:flex;gap:8px;justify-content:center;margin-top:10px;flex-wrap:wrap">
          <button class="copy-btn" style="padding:8px 14px"
                  onclick="copyText('@{user.username}', this)">📋 نسخ اليوزر</button>
          <button class="copy-btn" style="padding:8px 14px"
                  onclick="copyText('{user.public_id}', this)">📋 نسخ الـ ID</button>
        </div>"""
        if user.bio: profile_html += f'<div class="bio">{user.bio}</div>'

    actions = ""
    if is_own:
        actions = f"""
        <a class="btn btn-primary" href="{url_for('edit_profile')}">تعديل البروفايل</a>
        <a class="btn" href="{url_for('discover')}">👥 اكتشف أشخاصًا</a>
        <a class="btn" href="{url_for('change_password')}">تغيير كلمة المرور</a>
        <a class="btn" href="{url_for('show_recovery_code')}">عرض كود الاستعادة</a>
        <a class="btn" href="{url_for('devices_list')}">الأجهزة المتصلة</a>
        <a class="btn" href="{url_for('post_status')}">أضف حالة</a>
        <a class="btn" href="{url_for('inbox')}">الرسائل المجهولة</a>
        <a class="btn" href="{url_for('logout')}">تسجيل الخروج</a>"""
    else:
        actions = f'<a class="btn btn-primary" href="{url_for("chat_with", username=user.username)}">◈ ابدأ الدردشة</a>'
        if friend_state == 'none':
            actions += f'<a class="btn" href="{url_for("friend_request", username=user.username)}">➕ إضافة صديق</a>'
        elif friend_state == 'pending_out':
            actions += f'<a class="btn" href="{url_for("friends_requests")}">⏳ طلب معلّق</a>'
        elif friend_state == 'pending_in':
            actions += f'<a class="btn btn-primary" href="{url_for("friends_requests")}">✔ اقبل طلب الصداقة</a>'
        else:
            actions += '<div style="text-align:center;color:#16a34a;font-weight:700;margin-top:8px">✓ أنتما صديقان</div>'
        actions += f'<a class="btn" href="{url_for("send_message", username=user.username)}">✉ رسالة مجهولة</a>'
        actions += f'<a class="btn btn-danger" href="{url_for("report_user", username=user.username)}">إبلاغ</a>'

    return render_page(FLASH_BLOCK + topbar_html(badge) + f"""
    <div class="card center">
      <img class="avatar" src="{av_url}" alt="avatar"
           onclick="openAvatar('{av_url}')" title="اضغط لعرض الصورة كاملة">
      <div style="font-size:11px;color:#9ca3af;margin-bottom:8px">🔍 اضغط على الصورة لعرضها كاملة</div>
      {profile_html}
      <div class="actions">{actions}</div>
    </div>""", title=user.username)

@app.route("/profile/edit", methods=["GET","POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        nickname = request.form.get("nickname","").strip()
        bio = request.form.get("bio","").strip()
        if not is_valid_nickname(nickname):
            flash("اللقب: من كلمة إلى 4 كلمات.","error"); return redirect(url_for("edit_profile"))
        if len(bio) > 200:
            flash("النبذة طويلة جدًا.","error"); return redirect(url_for("edit_profile"))
        current_user.nickname = nickname
        current_user.bio = bio

        remove_avatar = request.form.get("remove_avatar") == "1"
        if remove_avatar and current_user.avatar:
            try:
                old_path = os.path.join(app.config["AVATAR_FOLDER"], current_user.avatar)
                if os.path.exists(old_path):
                    os.remove(old_path)
            except OSError:
                pass
            current_user.avatar = ""

        file = request.files.get("avatar")
        if file and file.filename:
            if not allowed_image(file.filename) or not check_image_magic(file):
                flash("صيغة الصورة غير مدعومة أو الملف ليس صورة.","error")
                return redirect(url_for("edit_profile"))
            if current_user.avatar:
                try:
                    old_path = os.path.join(app.config["AVATAR_FOLDER"], current_user.avatar)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                except OSError:
                    pass
            ext = file.filename.rsplit(".",1)[1].lower()
            fn = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(app.config["AVATAR_FOLDER"], fn))
            current_user.avatar = fn
        db.session.commit()
        flash("تم التحديث.","success")
        return redirect(url_for("profile_me"))

    badge = badge_html()
    has_avatar = bool(current_user.avatar)
    delete_btn = ('<button type="button" class="btn btn-danger" style="width:100%;margin-top:10px" '
                  'onclick="requestDeleteAvatar()">🗑 حذف الصورة الحالية</button>') if has_avatar else ''
    return render_page(FLASH_BLOCK + topbar_html(badge) + f"""
    <div class="card"><h2>تعديل البروفايل</h2>
    <form method="POST" enctype="multipart/form-data" id="edit-form">
      <div style="text-align:center;margin-bottom:14px">
        <img id="avatar-preview" src="{avatar_url(current_user)}"
             class="avatar" style="cursor:default"
             onclick="openAvatar(this.src)">
        <div style="font-size:11px;color:#9ca3af;margin-top:-6px">
          اضغط على الصورة لعرضها كاملة
        </div>
      </div>

      <label>اللقب (1-4 كلمات)</label>
      <input name="nickname" value="{current_user.nickname or ''}" maxlength="64" required>

      <label>نبذة عنك</label>
      <textarea name="bio" maxlength="200">{current_user.bio or ''}</textarea>

      <label>صورة البروفايل</label>
      <input type="file" name="avatar" accept="image/*"
             onchange="previewAvatar(this)">

      {delete_btn}
      <input type="hidden" name="remove_avatar" id="remove_avatar_flag" value="0">

      <button type="submit" style="margin-top:14px">حفظ</button>
    </form>
    <a class="link-center" href="{url_for('profile_me')}">رجوع</a>
    </div>

    <script>
      function previewAvatar(input){{
        var f = input.files[0];
        if(!f) return;
        var u = URL.createObjectURL(f);
        document.getElementById('avatar-preview').src = u;
      }}
      function requestDeleteAvatar(){{
        if(confirm('هل أنت متأكد من حذف صورة البروفايل؟')){
          document.getElementById('remove_avatar_flag').value = '1';
          document.getElementById('edit-form').submit();
        }}
      }}
    </script>
    """, title="تعديل")

@app.route("/profile/avatar/delete", methods=["POST"])
@login_required
def delete_avatar():
    if current_user.avatar:
        try:
            old_path = os.path.join(app.config["AVATAR_FOLDER"], current_user.avatar)
            if os.path.exists(old_path):
                os.remove(old_path)
        except OSError:
            pass
        current_user.avatar = ""
        db.session.commit()
        flash("تم حذف صورة البروفايل.", "success")
    else:
        flash("لا توجد صورة لحذفها.", "error")
    return redirect(url_for("edit_profile"))

@app.route("/password", methods=["GET","POST"])
@login_required
def change_password():
    if request.method == "POST":
        old = request.form.get("old","")
        new = request.form.get("new","")
        confirm = request.form.get("confirm","")
        if not check_password_hash(current_user.password_hash, old):
            flash("كلمة السر الحالية خاطئة.","error"); return redirect(url_for("change_password"))
        if len(new) < 8 or new != confirm:
            flash("تحقق من كلمة السر الجديدة.","error"); return redirect(url_for("change_password"))
        current_user.password_hash = generate_password_hash(new)
        db.session.commit()
        flash("تم تغيير كلمة المرور.","success")
        return redirect(url_for("profile_me"))
    return render_page(FLASH_BLOCK + """
    <div class="card"><h2>تغيير كلمة المرور</h2>
    <form method="POST">
    <label>كلمة السر الحالية</label>
    <div class="pw-wrap">
      <input name="old" id="cp1" type="password" required>
      <button type="button" class="pw-toggle" onclick="togglePw('cp1')">👁</button>
    </div>
    <label>كلمة السر الجديدة</label>
    <div class="pw-wrap">
      <input name="new" id="cp2" type="password" required>
      <button type="button" class="pw-toggle" onclick="togglePw('cp2')">👁</button>
    </div>
    <label>تأكيد كلمة السر الجديدة</label>
    <div class="pw-wrap">
      <input name="confirm" id="cp3" type="password" required>
      <button type="button" class="pw-toggle" onclick="togglePw('cp3')">👁</button>
    </div>
    <button type="submit">تغيير</button></form>
    <a class="link-center" href="{{ url_for('profile_me') }}">رجوع</a>
    </div>""", title="كلمة المرور")

@app.route("/recovery-code", methods=["GET","POST"])
@login_required
def show_recovery_code():
    if request.method == "POST":
        password = request.form.get("password","")
        if not check_password_hash(current_user.password_hash, password):
            flash("كلمة السر خاطئة.","error"); return redirect(url_for("show_recovery_code"))
        new_code = gen_recovery_code()
        while User.query.filter_by(recovery_hash=hash_recovery_code(new_code)).first():
            new_code = gen_recovery_code()
        current_user.recovery_hash = hash_recovery_code(new_code)
        db.session.commit()
        return render_page("""
        <div class="card center">
          <h2>🔐 كود الاستعادة الجديد</h2>
          <p style="color:#6b7280;font-size:13px;margin-bottom:12px">
            احفظه الآن. لن يظهر مرة أخرى.</p>
          <div class="recovery-box">
            <div class="code">{{ formatted }}</div>
            <button class="copy-btn" onclick="copyText('{{ code }}',this)">نسخ الكود</button>
          </div>
          <a class="btn btn-primary" href="{{ url_for('profile_me') }}">رجوع للبروفايل</a>
        </div>""", title="كود جديد", formatted=format_code(new_code), code=new_code)
    return render_page(FLASH_BLOCK + """
    <div class="card">
      <h2>🔐 عرض كود الاستعادة</h2>
      <div class="privacy-note">
        ⚠️ سيتم توليد كود جديد وإبطال القديم.
      </div>
      <form method="POST">
      <label>كلمة السر</label>
      <div class="pw-wrap">
        <input name="password" id="rcpw" type="password" required>
        <button type="button" class="pw-toggle" onclick="togglePw('rcpw')">👁</button>
      </div>
      <button type="submit">توليد كود جديد</button></form>
      <a class="link-center" href="{{ url_for('profile_me') }}">رجوع</a>
    </div>""", title="كود الاستعادة")

@app.route("/devices")
@login_required
def devices_list():
    devices = Device.query.filter_by(user_id=current_user.id)\
                          .order_by(Device.created_at.desc()).all()
    rows = ""
    for d in devices:
        ua = d.user_agent or "غير معروف"
        created = fmt_sd(d.created_at)
        rows += f"""<div class="device-row">
        <div><div><b>جهاز</b> — {created} (SD)</div>
        <div class="ua">{ua}</div></div>
        <a class="btn btn-sm btn-danger"
           href="{url_for('device_remove', did=d.id)}"
           onclick="return confirm('إزالة هذا الجهاز؟')">إزالة</a>
        </div>"""
    if not rows: rows = '<p class="empty">لا أجهزة مسجلة.</p>'
    badge = badge_html()
    return render_page(FLASH_BLOCK + topbar_html(badge) + f"""
    <div class="card">
      <h2>الأجهزة المتصلة</h2>
      {rows}
      <a class="link-center" href="{url_for('profile_me')}">رجوع</a>
    </div>""", title="الأجهزة")

@app.route("/device/remove/<int:did>")
@login_required
def device_remove(did):
    d = Device.query.get_or_404(did)
    if d.user_id != current_user.id: abort(404)
    db.session.delete(d); db.session.commit()
    flash("تم إزالة الجهاز.","success")
    return redirect(url_for("devices_list"))

# ═══════════════════ الأصدقاء ═══════════════════
@app.route("/friends")
@login_required
def friends_list():
    friends = get_friends(current_user.id)
    badge = badge_html()
    incoming = Friendship.query.filter_by(addressee_id=current_user.id, status="pending").count()
    rows = ""
    for f in friends:
        rows += f"""<a class="list-item" href="{url_for('view_profile', username=f.username)}">
        <img class="avatar-sm" src="{avatar_url(f)}" onclick="event.preventDefault();event.stopPropagation();openAvatar('{avatar_url(f)}')">
        <div><div class="li-name">{f.short_name}</div>
        <div class="li-sub">@{f.username}</div></div>
        <div class="li-actions">
          <a class="btn btn-sm btn-primary" href="{url_for('chat_with', username=f.username)}">دردشة</a>
        </div></a>"""
    if not rows:
        rows = '<p class="empty">لا أصدقاء بعد. ابحث عن أشخاص وأضفهم.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge) + f"""
    <div class="card">
      <h2>أصدقائي ({len(friends)})</h2>
      <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
        <a class="btn btn-sm" href="{url_for('friends_requests')}">طلبات الصداقة {f'({incoming})' if incoming else ''}</a>
        <a class="btn btn-sm btn-primary" href="{url_for('discover')}">👥 اكتشف</a>
        <a class="btn btn-sm" href="{url_for('search')}">🔍 بحث</a>
      </div>
      {rows}
    </div>""", title="الأصدقاء")

@app.route("/friends/requests")
@login_required
def friends_requests():
    incoming = Friendship.query.filter_by(addressee_id=current_user.id, status="pending").all()
    outgoing = Friendship.query.filter_by(requester_id=current_user.id, status="pending").all()
    badge = badge_html()
    inc = ""
    for r in incoming:
        u = r.requester
        inc += f"""<div class="list-item">
        <img class="avatar-sm" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
        <div><div class="li-name">{u.short_name}</div>
        <div class="li-sub">@{u.username}</div></div>
        <div class="li-actions">
          <a class="btn btn-sm btn-primary" href="{url_for('friend_accept', fid=r.id)}">قبول</a>
          <a class="btn btn-sm btn-danger" href="{url_for('friend_reject', fid=r.id)}">رفض</a>
        </div></div>"""
    if not inc: inc = '<p class="empty">لا طلبات واردة.</p>'
    out = ""
    for r in outgoing:
        u = r.addressee
        out += f"""<div class="list-item">
        <img class="avatar-sm" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
        <div><div class="li-name">{u.short_name}</div>
        <div class="li-sub">بانتظار الرد</div></div>
        <div class="li-actions">
          <a class="btn btn-sm btn-danger" href="{url_for('friend_reject', fid=r.id)}">إلغاء</a>
        </div></div>"""
    if not out: out = '<p class="empty">لا طلبات مرسلة.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge) + f"""
    <div class="card"><h2>طلبات واردة</h2>{inc}</div>
    <div class="card"><h2>طلبات مرسلة</h2>{out}</div>""", title="طلبات الصداقة")

@app.route("/friend/request/<username>")
@login_required
def friend_request(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not target or target.id == current_user.id:
        flash("لا يمكن إضافة هذا المستخدم.","error"); return redirect(url_for("search"))
    state, _ = friendship_status(current_user.id, target.id)
    if state != "none":
        flash("الطلب موجود بالفعل.","error"); return redirect(url_for("view_profile", username=target.username))
    db.session.add(Friendship(requester_id=current_user.id, addressee_id=target.id, status="pending"))
    db.session.commit()
    flash(f"تم إرسال طلب صداقة إلى @{target.username}.","success")
    return redirect(request.referrer or url_for("view_profile", username=target.username))

@app.route("/friend/accept/<int:fid>")
@login_required
def friend_accept(fid):
    r = Friendship.query.get_or_404(fid)
    if r.addressee_id != current_user.id: abort(404)
    r.status = "accepted"; db.session.commit()
    flash("تم قبول الصداقة.","success")
    return redirect(url_for("friends_requests"))

@app.route("/friend/reject/<int:fid>")
@login_required
def friend_reject(fid):
    r = Friendship.query.get_or_404(fid)
    if r.addressee_id != current_user.id and r.requester_id != current_user.id: abort(404)
    db.session.delete(r); db.session.commit()
    flash("تم الحذف.","success")
    return redirect(url_for("friends_requests"))

# ═══════════════════ اكتشف الأشخاص ═══════════════════
@app.route("/discover")
@login_required
def discover():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 30

    query = User.query.filter(
        User.is_banned == False,
        User.id != current_user.id
    )
    if q:
        ql = q.lower().lstrip("@")
        query = query.filter(or_(
            User.username.ilike(f"%{ql}%"),
            User.public_id.ilike(f"%{ql}%")
        ))
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    my_friends = get_friend_ids(current_user.id)
    pending_out = {r.addressee_id for r in Friendship.query.filter_by(
        requester_id=current_user.id, status="pending").all()}
    pending_in = {r.requester_id for r in Friendship.query.filter_by(
        addressee_id=current_user.id, status="pending").all()}

    rows = ""
    for u in pagination.items:
        if u.id in my_friends:
            action = '<span class="btn btn-sm btn-disabled" style="color:#16a34a">✓ صديق</span>'
        elif u.id in pending_out:
            action = '<span class="btn btn-sm btn-disabled">⏳ معلّق</span>'
        elif u.id in pending_in:
            action = f'<a class="btn btn-sm btn-primary" href="{url_for("friends_requests")}">✔ اقبل</a>'
        else:
            action = f'<a class="btn btn-sm btn-primary" href="{url_for("friend_request", username=u.username)}">➕ إضافة</a>'

        rows += f"""<div class="list-item" style="cursor:default">
          <a href="{url_for('view_profile', username=u.username)}"
             style="display:flex;align-items:center;gap:10px;flex:1;text-decoration:none;color:inherit">
            <img class="avatar-sm" src="{avatar_url(u)}"
                 onclick="event.preventDefault();event.stopPropagation();openAvatar('{avatar_url(u)}')">
            <div style="flex:1">
              <div class="li-name">{u.short_name}</div>
              <div class="li-sub">@{u.username} · ID: {u.public_id}</div>
            </div>
          </a>
          <div class="li-actions">
            <button class="copy-btn" style="padding:4px 8px;font-size:11px"
                    onclick="copyText('{u.public_id}', this)">ID</button>
            {action}
          </div>
        </div>"""

    if not rows:
        rows = '<p class="empty">لا نتائج.</p>'

    nav = ""
    if pagination.pages > 1:
        nav = '<div style="display:flex;gap:6px;justify-content:center;margin-top:14px;flex-wrap:wrap">'
        if pagination.has_prev:
            nav += f'<a class="btn btn-sm" href="{url_for("discover", page=pagination.prev_num, q=q)}">← السابق</a>'
        nav += f'<span class="btn btn-sm btn-disabled">صفحة {pagination.page} من {pagination.pages}</span>'
        if pagination.has_next:
            nav += f'<a class="btn btn-sm" href="{url_for("discover", page=pagination.next_num, q=q)}">التالي →</a>'
        nav += '</div>'

    badge = badge_html()
    return render_page(FLASH_BLOCK + topbar_html(badge) + f"""
    <div class="card">
      <h2>👥 اكتشف الأشخاص ({pagination.total})</h2>
      <form method="GET" style="display:flex;gap:8px;margin:10px 0">
        <input name="q" value="{q}" placeholder="ابحث بيوزر أو ID"
               style="flex:1;margin:0">
        <button type="submit" style="width:auto;padding:12px 20px;margin:0">بحث</button>
      </form>
      <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
        <a class="btn btn-sm" href="{url_for('friends_list')}">أصدقائي</a>
        <a class="btn btn-sm" href="{url_for('friends_requests')}">الطلبات</a>
        <a class="btn btn-sm" href="{url_for('search')}">🔍 بحث متقدم</a>
      </div>
      {rows}
      {nav}
    </div>""", title="اكتشف الأشخاص")

# ═══════════════════ البحث ═══════════════════
@app.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    users_results = []
    if q:
        ql = q.lower().lstrip("@")
        users_results = User.query.filter(
            or_(
                User.username.ilike(f"%{ql}%"),
                User.public_id.ilike(f"%{ql}%")
            ),
            User.is_banned == False,
            User.id != current_user.id
        ).limit(50).all()

    badge = badge_html()
    users_block = ""
    for u in users_results:
        state, _ = friendship_status(current_user.id, u.id)
        if state == "friends":
            action = '<span class="btn btn-sm btn-disabled" style="color:#16a34a">✓ صديق</span>'
        elif state == "pending_out":
            action = '<span class="btn btn-sm btn-disabled">⏳ معلّق</span>'
        elif state == "pending_in":
            action = f'<a class="btn btn-sm btn-primary" href="{url_for("friends_requests")}">✔ اقبل</a>'
        else:
            action = f'<a class="btn btn-sm btn-primary" href="{url_for("friend_request", username=u.username)}">➕ إضافة</a>'

        users_block += f"""<a class="list-item" href="{url_for('view_profile', username=u.username)}">
        <img class="avatar-sm" src="{avatar_url(u)}"
             onclick="event.preventDefault();event.stopPropagation();openAvatar('{avatar_url(u)}')">
        <div><div class="li-name">{u.short_name}</div>
        <div class="li-sub">@{u.username} · ID: {u.public_id}</div></div>
        <div class="li-actions">{action}</div></a>"""
    if not users_block and q:
        users_block = '<p class="empty">لا نتائج.</p>'

    return render_page(FLASH_BLOCK + topbar_html(badge) + f"""
    <div class="card">
      <h2>🔍 البحث</h2>
      <p style="color:#6b7280;font-size:12px;text-align:center;margin-bottom:8px">
        ابحث باليوزر أو بالـ ID (8 أرقام)</p>
      <form method="GET" style="display:flex;gap:8px">
        <input name="q" value="{q}" placeholder="username أو 12345678"
               style="flex:1;margin:0" autofocus>
        <button type="submit" style="width:auto;padding:12px 20px;margin:0">بحث</button>
      </form>
      <a class="link-center" href="{url_for('discover')}">👥 أو تصفح كل الأشخاص</a>
    </div>
    {('<div class="card"><h2>النتائج (' + str(len(users_results)) + ')</h2>' + users_block + '</div>') if q else ''}
    """, title="بحث")

# ═══════════════════ الحالات ═══════════════════
@app.route("/status/new", methods=["GET", "POST"])
@login_required
def post_status():
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        caption = request.form.get("caption", "").strip()
        file = request.files.get("media")
        media_fn = ""
        media_type = ""
        if file and file.filename:
            fn_low = file.filename.lower()
            if allowed_video(fn_low) and check_video_magic(file):
                ext = fn_low.rsplit(".", 1)[1]
                media_fn = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(app.config["STATUS_FOLDER"], media_fn))
                media_type = "video"
            elif allowed_image(fn_low) and check_image_magic(file):
                ext = fn_low.rsplit(".", 1)[1]
                media_fn = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(app.config["STATUS_FOLDER"], media_fn))
                media_type = "image"
            else:
                flash("صيغة الملف غير مدعومة.", "error")
                return redirect(url_for("post_status"))
        if not text and not media_fn:
            flash("أضف نصًا أو وسائط.", "error")
            return redirect(url_for("post_status"))
        db.session.add(Status(user_id=current_user.id, text=text[:300],
                              caption=caption[:300], media=media_fn,
                              media_type=media_type))
        db.session.commit()
        flash("تم نشر الحالة. تنتهي تلقائيًا بعد 24 ساعة.", "success")
        return redirect(url_for("feed"))
    badge = badge_html()
    return render_page(FLASH_BLOCK + topbar_html(badge) + """
    <div class="card"><h2>📸 حالة جديدة</h2>
    <form method="POST" enctype="multipart/form-data">
      <label>النص (اختياري)</label>
      <textarea name="text" maxlength="300" placeholder="اكتب شيئًا..."></textarea>
      <label>الوسائط (صورة أو فيديو)</label>
      <input type="file" name="media" accept="image/*,video/*"
             onchange="previewStatusMedia(this)">
      <div id="status-preview"></div>
      <label>وصف الوسائط (اختياري)</label>
      <input name="caption" maxlength="300" placeholder="وصف مختصر...">
      <button type="submit">نشر الحالة</button>
    </form>
    <a class="link-center" href="{{ url_for('feed') }}">رجوع</a>
    </div>""", title="حالة جديدة")

@app.route("/status/<int:sid>/edit", methods=["GET", "POST"])
@login_required
def edit_status(sid):
    s = Status.query.get_or_404(sid)
    if s.user_id != current_user.id:
        abort(403)
    if request.method == "POST":
        s.text = request.form.get("text", "").strip()[:300]
        s.caption = request.form.get("caption", "").strip()[:300]
        db.session.commit()
        flash("تم تعديل الحالة.", "success")
        return redirect(url_for("feed"))
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>✏️ تعديل الحالة</h2>
    <form method="POST">
      <label>النص</label>
      <textarea name="text" maxlength="300">{s.text}</textarea>
      <label>الوصف</label>
      <input name="caption" maxlength="300" value="{s.caption}">
      <button type="submit">حفظ</button>
    </form>
    <a class="link-center" href="{url_for('feed')}">رجوع</a>
    </div>""", title="تعديل حالة")

@app.route("/status/<int:sid>/delete")
@login_required
def delete_status(sid):
    s = Status.query.get_or_404(sid)
    if s.user_id != current_user.id:
        abort(403)
    if s.media:
        try:
            os.remove(os.path.join(app.config["STATUS_FOLDER"], s.media))
        except OSError:
            pass
    db.session.delete(s)
    db.session.commit()
    flash("تم حذف الحالة.", "success")
    return redirect(url_for("feed"))

# ═══════════════════ الصفحة الرئيسية ═══════════════════
@app.route("/feed")
@login_required
def feed():
    cleanup_old_statuses()
    badge = badge_html()
    cutoff = now_utc_naive() - timedelta(hours=24)

    statuses = Status.query.filter(Status.created_at >= cutoff)\
        .order_by(Status.created_at.desc()).all()

    by_user = {}
    for s in statuses:
        by_user.setdefault(s.user_id, []).append(s)

    status_strip = ""
    for uid, items in by_user.items():
        u = items[0].user
        av = avatar_url(u)
        count = len(items)
        tag = '<span class="vid-tag">▶</span>' if any(i.media_type == "video" for i in items) else ""
        count_badge = (f'<span class="count-badge">{count}</span>'
                       if count > 1 else "")
        first_id = items[0].id
        status_strip += f"""<a class="status-item" href="javascript:void(0)"
            onclick="openStatus({first_id})">
          <span class="ring">{count_badge}<img src="{av}">{tag}</span>
          <div class="sname">{u.short_name}</div>
        </a>"""

    status_viewers = ""
    for uid, items in by_user.items():
        for idx, s in enumerate(items):
            media_html = ""
            if s.media:
                url = upload_url("statuses", s.media)
                if s.media_type == "video":
                    media_html = f'<video controls src="{url}" autoplay></video>'
                else:
                    media_html = f'<img src="{url}">'

            owner_actions = ""
            if s.user_id == current_user.id:
                owner_actions = f"""<div class="status-owner-actions">
                  <a class="sbtn edit" href="{url_for('edit_status', sid=s.id)}">✏️ تعديل</a>
                  <a class="sbtn del" href="{url_for('delete_status', sid=s.id)}"
                     onclick="return confirm('حذف الحالة؟')">🗑 حذف</a>
                </div>"""

            nav_html = ""
            if len(items) > 1:
                prev_btn = ""
                next_btn = ""
                if idx > 0:
                    prev_btn = (f'<button class="nav-btn" '
                                f'onclick="event.stopPropagation();closeStatus({s.id});openStatus({items[idx-1].id})">◀ السابق</button>')
                if idx < len(items) - 1:
                    next_btn = (f'<button class="nav-btn" '
                                f'onclick="event.stopPropagation();closeStatus({s.id});openStatus({items[idx+1].id})">التالي ▶</button>')
                nav_html = f"""<div class="status-nav">
                  {prev_btn}<span class="counter">{idx+1} / {len(items)}</span>{next_btn}
                </div>"""

            status_viewers += f"""<div class="status-view" id="sv-{s.id}" style="display:none">
              {owner_actions}
              <button class="close" onclick="closeStatus({s.id})">✕</button>
              {media_html}
              {f'<div class="stext">{s.text}</div>' if s.text else ''}
              {f'<div class="scaption">{s.caption}</div>' if s.caption else ''}
              <div class="smeta">{s.user.short_name} · {fmt_sd(s.created_at)}</div>
              {nav_html}
            </div>"""

    return render_page(FLASH_BLOCK + topbar_html(badge) + f"""
    <div class="card">
      <h2 style="text-align:right;font-size:15px">الحالات (24 ساعة)</h2>
      <div class="status-strip">
        <a class="status-item" href="{url_for('post_status')}">
          <span class="ring" style="background:#e5e7eb">
            <img src="{avatar_url(current_user)}" style="opacity:.5">
          </span>
          <div class="sname">+ أضف</div>
        </a>
        {status_strip}
      </div>
      {('<p class="empty" style="padding:10px 0">لا حالات حديثة.</p>') if not status_strip else ''}
    </div>
    {status_viewers}
    """, title="الرئيسية")

# ═══════════════════ الدردشة ═══════════════════
@app.route("/chats")
@login_required
def chats():
    badge = badge_html()
    friends = get_friends(current_user.id)
    saved = SavedChat.query.filter_by(user_id=current_user.id).all()
    saved_ids = {s.peer_id for s in saved}

    rows = ""
    for f in friends:
        last_msg = ChatMessage.query.filter(
            or_(
                and_(ChatMessage.sender_id == current_user.id,
                     ChatMessage.receiver_id == f.id),
                and_(ChatMessage.sender_id == f.id,
                     ChatMessage.receiver_id == current_user.id)
            )
        ).order_by(ChatMessage.created_at.desc()).first()
        unread = ChatMessage.query.filter_by(
            sender_id=f.id, receiver_id=current_user.id, is_read=False).count()
        preview = "ابدأ الدردشة"
        time_str = ""
        if last_msg:
            preview = last_msg.body[:40]
            time_str = fmt_sd(last_msg.created_at, "%H:%M")
        pin_tag = "📌 " if f.id in saved_ids else ""
        unread_tag = (f'<span class="badge" style="position:static;margin-right:6px">{unread}</span>'
                      if unread else '')
        rows += f"""<a class="list-item" href="{url_for('chat_with', username=f.username)}">
          <img class="avatar-sm" src="{avatar_url(f)}">
          <div style="flex:1">
            <div class="li-name">{pin_tag}{f.short_name} {unread_tag}</div>
            <div class="li-sub">{preview}</div>
          </div>
          <div class="li-sub">{time_str}</div>
        </a>"""
    if not rows:
        rows = '<p class="empty">لا محادثات. أضف أصدقاء لبدء الدردشة.</p>'

    return render_page(FLASH_BLOCK + topbar_html(badge) + f"""
    <div class="card">
      <h2>◈ الدردشات</h2>
      <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
        <a class="btn btn-sm" href="{url_for('friends_list')}">الأصدقاء</a>
        <a class="btn btn-sm" href="{url_for('discover')}">👥 اكتشف</a>
        <a class="btn btn-sm" href="{url_for('inbox')}">📩 المجهولة</a>
      </div>
      {rows}
    </div>""", title="الدردشات")

@app.route("/chat/<username>", methods=["GET", "POST"])
@login_required
def chat_with(username):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    if peer.id == current_user.id:
        flash("لا يمكنك محادثة نفسك.", "error")
        return redirect(url_for("chats"))
    state, _ = friendship_status(current_user.id, peer.id)
    if state != "friends":
        flash("يجب أن تكونا صديقين لبدء الدردشة.", "error")
        return redirect(url_for("view_profile", username=peer.username))

    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if body:
            db.session.add(ChatMessage(sender_id=current_user.id,
                                       receiver_id=peer.id, body=body[:2000]))
            db.session.commit()
        return redirect(url_for("chat_with", username=peer.username))

    ChatMessage.query.filter_by(sender_id=peer.id,
                                receiver_id=current_user.id,
                                is_read=False).update({"is_read": True})
    db.session.commit()

    msgs = ChatMessage.query.filter(
        or_(
            and_(ChatMessage.sender_id == current_user.id,
                 ChatMessage.receiver_id == peer.id),
            and_(ChatMessage.sender_id == peer.id,
                 ChatMessage.receiver_id == current_user.id)
        )
    ).order_by(ChatMessage.created_at.asc()).limit(500).all()

    bubbles = ""
    for m in msgs:
        cls = "me" if m.sender_id == current_user.id else "them"
        bubbles += f"""<div class="bubble {cls}">{m.body}
          <span class="t">{fmt_sd(m.created_at, "%H:%M")}</span></div>"""

    badge = badge_html()
    return render_page(FLASH_BLOCK + topbar_html(badge) + f"""
    <div class="card">
      <div class="chat-header">
        <a href="{url_for('chats')}" class="btn btn-sm">←</a>
        <img class="avatar-sm" src="{avatar_url(peer)}"
             onclick="openAvatar('{avatar_url(peer)}')">
        <div><div class="pn">{peer.short_name}</div>
        <div class="pu">@{peer.username}</div></div>
        <a class="btn btn-sm" style="margin-right:auto"
           href="{url_for('view_profile', username=peer.username)}">البروفايل</a>
      </div>
      <div class="chat-box" id="chatbox">{bubbles}</div>
      <form class="chat-input" method="POST">
        <input name="body" placeholder="اكتب رسالة..." required autocomplete="off">
        <button type="submit">إرسال</button>
      </form>
    </div>""", title=f"دردشة @{peer.username}")

# ═══════════════════ الرسائل المجهولة + الإبلاغ ═══════════════════
@app.route("/message/<username>", methods=["GET", "POST"])
@login_required
def send_message(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    if target.id == current_user.id:
        flash("لا يمكنك إرسال رسالة لنفسك.", "error")
        return redirect(url_for("profile_me"))
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        sender = request.form.get("sender_name", "").strip() or "مجهول"
        if not body:
            flash("الرسالة فارغة.", "error")
            return redirect(url_for("send_message", username=target.username))
        db.session.add(Message(receiver_id=target.id, body=body[:2000],
                               sender_name=sender[:64]))
        db.session.commit()
        flash("تم إرسال الرسالة بنجاح ✓", "success")
        return redirect(url_for("view_profile", username=target.username))
    return render_page(FLASH_BLOCK + f"""
    <div class="card">
      <h2>✉ رسالة مجهولة لـ @{target.username}</h2>
      <div class="privacy-note">🔒 لن يعرف المرسل هويتك إلا إذا كتبتها.</div>
      <form method="POST">
        <label>اسمك (اختياري)</label>
        <input name="sender_name" maxlength="64" placeholder="اتركه فارغًا للمجهول">
        <label>الرسالة</label>
        <textarea name="body" maxlength="2000" required
                  placeholder="اكتب رسالتك..."></textarea>
        <button type="submit">إرسال</button>
      </form>
      <a class="link-center" href="{url_for('view_profile', username=target.username)}">رجوع</a>
    </div>""", title="رسالة مجهولة")

@app.route("/inbox")
@login_required
def inbox():
    messages = Message.query.filter_by(receiver_id=current_user.id)\
        .order_by(Message.created_at.desc()).all()
    badge = badge_html()
    rows = ""
    for m in messages:
        rows += f"""<div class="msg">
          <div class="meta">من: {m.sender_name} · {fmt_sd(m.created_at)}</div>
          <div class="body">{m.body}</div>
        </div>"""
    if not rows:
        rows = '<p class="empty">لا رسائل مجهولة.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge) + f"""
    <div class="card">
      <h2>📩 الرسائل المجهولة</h2>
      {rows}
      <a class="link-center" href="{url_for('profile_me')}">رجوع</a>
    </div>""", title="الرسائل المجهولة")

@app.route("/report/<username>", methods=["GET", "POST"])
@login_required
def report_user(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    if target.id == current_user.id:
        flash("لا يمكنك إبلاغ نفسك.", "error")
        return redirect(url_for("profile_me"))
    if request.method == "POST":
        reason = request.form.get("reason", "").strip()
        db.session.add(Report(reporter_id=current_user.id,
                              target_id=target.id, reason=reason[:300]))
        db.session.commit()
        flash("تم إرسال الإبلاغ. شكرًا لك.", "success")
        return redirect(url_for("view_profile", username=target.username))
    return render_page(FLASH_BLOCK + f"""
    <div class="card">
      <h2>🚨 إبلاغ عن @{target.username}</h2>
      <form method="POST">
        <label>سبب الإبلاغ</label>
        <textarea name="reason" maxlength="300" required
                  placeholder="اشرح سبب الإبلاغ..."></textarea>
        <button type="submit">إرسال الإبلاغ</button>
      </form>
      <a class="link-center" href="{url_for('view_profile', username=target.username)}">رجوع</a>
    </div>""", title="إبلاغ")

# ═══════════════════ نقطة النهاية ═══════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
