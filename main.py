# -*- coding: utf-8 -*-
"""
FBI SUDANESE — v9.0 (WhatsApp Killer Edition)
- ✅ بروفايل المرسل بجانب كل رسالة (فردي + جماعي) + قابل للنقر
- ✅ مؤشر "يكتب..." في الفردي والجماعي
- ✅ زر حذف الرسائل + إزالة التفاعل
- ✅ إرسال الأغاني (mp3, m4a, wav, flac...)
- ✅ تحديث تلقائي كل ثانية
- ✅ حظر جماعي متعدد
- ✅ شاشة بداية بصورة قابلة للرفع/الحذف
- ✅ علامة صح ✓✓ للرسائل المقروءة
- ✅ رد سريع بإيموجي (Double Tap)
- ✅ تثبيت الرسائل المهمة
- ✅ بحث داخل المحادثة
- ✅ مؤشر "آخر ظهور"
- ✅ معاينة الروابط تلقائياً
- ✅ وضع ليلي/نهاري
- ✅ مسح المحادثة (فردي/جماعي)
- ✅ كتم الإشعارات
- ✅ حفظ الرسائل (Star)
"""
import os, re, uuid, random, string, secrets, hashlib, time, traceback
from datetime import datetime, timedelta, timezone
from functools import wraps
from collections import defaultdict

try:
    from zoneinfo import ZoneInfo
    KHARTOUM_TZ = ZoneInfo("Africa/Khartoum")
except Exception:
    KHARTOUM_TZ = timezone(timedelta(hours=2), name="SDT")
UTC_TZ = timezone.utc


def to_sd(dt):
    if dt is None: return None
    try:
        if dt.tzinfo is None: dt = dt.replace(tzinfo=UTC_TZ)
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


def time_ago_sd(dt):
    """آخر ظهور بصيغة مقروءة"""
    if not dt: return "غير معروف"
    d = to_sd(dt)
    if not d: return "غير معروف"
    now = datetime.now(KHARTOUM_TZ)
    diff = (now - d).total_seconds()
    if diff < 60: return "الآن"
    if diff < 3600: return f"منذ {int(diff//60)} دقيقة"
    if diff < 86400: return f"منذ {int(diff//3600)} ساعة"
    if diff < 604800: return f"منذ {int(diff//86400)} يوم"
    return fmt_sd(dt, "%Y-%m-%d")


from flask import (Flask, render_template_string, redirect, url_for, flash,
                   request, session, abort, make_response, send_from_directory, jsonify)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import RequestEntityTooLarge
from sqlalchemy import text, or_, and_, func, case

SITE_NAME = "𝙵𝙱𝙸 𝚂𝚄𝙳𝙰𝙽𝙴𝚂𝙴"
SUPPORT_PASSWORD = "$#ZAQWSCX$DERTGV@BHYTVNMJ@UIO$MLOPIGSGHEH8BEB8EV8S#GSUWBJSIS8H38BSI8EHUEBDNSKOS9S3UVDBDJH37"

FACEBOOK_URL = "https://www.facebook.com/profile.php?id=100084033551388"
TELEGRAM_URL = "https://t.me/Zero_Vib"
TELEGRAM_HANDLE = "@Zero_Vib"
FACEBOOK_URL_2 = "https://www.facebook.com/profile.php?id=61579274721625"
TELEGRAM_URL_2 = "https://t.me/MRDPY"
TELEGRAM_HANDLE_2 = "@MRDPY"

VOLUME_MOUNT = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "")
if VOLUME_MOUNT and os.path.isdir(VOLUME_MOUNT):
    DATA_DIR = VOLUME_MOUNT
    for sub in ["uploads", "uploads/avatars", "uploads/statuses",
                "uploads/chats", "uploads/groups", "uploads/splash"]:
        os.makedirs(os.path.join(DATA_DIR, sub), exist_ok=True)
else:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATA_DIR = os.environ.get("DATA_DIR") or os.path.join(BASE_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True)

UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
AVATAR_DIR = os.path.join(UPLOAD_DIR, "avatars")
STATUS_DIR = os.path.join(UPLOAD_DIR, "statuses")
CHAT_DIR = os.path.join(UPLOAD_DIR, "chats")
GROUP_DIR = os.path.join(UPLOAD_DIR, "groups")
SPLASH_DIR = os.path.join(UPLOAD_DIR, "splash")
for d in (AVATAR_DIR, STATUS_DIR, CHAT_DIR, GROUP_DIR, SPLASH_DIR):
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
app.config["CHAT_FOLDER"] = CHAT_DIR
app.config["GROUP_FOLDER"] = GROUP_DIR
app.config["SPLASH_FOLDER"] = SPLASH_DIR
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

AUTO_BAN_THRESHOLD = 200
USERNAME_RELEASE_HOURS = 24

IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "heic"}
VIDEO_EXT = {"mp4", "webm", "mov", "m4v", "ogg", "ogv", "avi", "mkv", "3gp", "mpeg", "mpg"}
AUDIO_EXT = {"mp3", "m4a", "wav", "aac", "ogg", "oga", "opus", "flac", "amr", "3gp", "weba"}

IMAGE_MAGIC = [
    (b"\x89PNG\r\n\x1a\n", "png"), (b"\xff\xd8\xff", "jpg"),
    (b"GIF87a", "gif"), (b"GIF89a", "gif"),
    (b"RIFF", "webp"), (b"BM", "bmp"),
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
    return any(head.startswith(m) for m, _ in IMAGE_MAGIC)


def check_video_magic(fs):
    try:
        head = fs.stream.read(32); fs.stream.seek(0)
    except Exception: return False
    return _is_video_head(head)


def check_audio_magic(fs):
    try:
        head = fs.stream.read(64); fs.stream.seek(0)
    except Exception:
        return False
    if head.startswith(b"ID3") or head.startswith(b"\xff\xfb") or head.startswith(b"\xff\xf3") or head.startswith(b"\xff\xf2"):
        return True
    if head.startswith(b"RIFF") and len(head) >= 12 and head[8:12] == b"WAVE":
        return True
    if head.startswith(b"OggS"):
        return True
    if head.startswith(b"fLaC"):
        return True
    if len(head) >= 12 and head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"M4A ", b"M4B ", b"mp42", b"isom", b"iso2"):
            return True
    if head.startswith(b"#!AMR"):
        return True
    return False


def allowed_image(fn): return "." in fn and fn.rsplit(".", 1)[1].lower() in IMAGE_EXT
def allowed_video(fn): return "." in fn and fn.rsplit(".", 1)[1].lower() in VIDEO_EXT
def allowed_audio(fn): return "." in fn and fn.rsplit(".", 1)[1].lower() in AUDIO_EXT


_login_attempts = defaultdict(list)
LOGIN_WINDOW = 300
LOGIN_MAX = 8


def is_rate_limited(ip):
    now = time.time()
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < LOGIN_WINDOW]
    return len(_login_attempts[ip]) >= LOGIN_MAX


def record_login_attempt(ip):
    _login_attempts[ip].append(time.time())


CODE_ALPHABET = string.ascii_uppercase + string.digits


def gen_recovery_code(): return "".join(secrets.choice(CODE_ALPHABET) for _ in range(20))
def hash_recovery_code(code): return hashlib.sha256(code.strip().upper().encode()).hexdigest()
def format_code(code):
    c = code.strip().upper()
    return "-".join(c[i:i + 4] for i in range(0, len(c), 4))


def gen_public_id(): return "".join(random.choices(string.digits, k=8))
def gen_device_token(): return secrets.token_urlsafe(32)


def is_url(text):
    if not text: return False
    return bool(re.match(r'^https?://', text.strip()))


def extract_first_url(text):
    if not text: return None
    m = re.search(r'https?://[^\s]+', text)
    return m.group(0) if m else None


# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════
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
    reports_count = db.Column(db.Integer, default=0)
    auto_banned_at = db.Column(db.DateTime, nullable=True)
    original_username = db.Column(db.String(5), default="")
    pending_username_release = db.Column(db.Boolean, default=False)
    username_release_at = db.Column(db.DateTime, nullable=True)
    under_review = db.Column(db.Boolean, default=False)
    review_reason = db.Column(db.String(300), default="")
    review_started_at = db.Column(db.DateTime, nullable=True)
    dark_mode = db.Column(db.Boolean, default=False)

    messages = db.relationship("Message", backref="receiver", lazy=True,
                               foreign_keys="Message.receiver_id")
    devices = db.relationship("Device", backref="user", lazy=True, cascade="all, delete-orphan")

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

    @property
    def is_online(self):
        if not self.last_seen: return False
        return (now_utc_naive() - self.last_seen).total_seconds() < 120


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
    privacy = db.Column(db.String(10), default="public")
    show_viewers = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="statuses")
    views = db.relationship("StatusView", backref="status", lazy=True, cascade="all, delete-orphan")


class StatusView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status_id = db.Column(db.Integer, db.ForeignKey("status.id"), nullable=False)
    viewer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    viewer = db.relationship("User", foreign_keys=[viewer_id])
    __table_args__ = (db.UniqueConstraint("status_id", "viewer_id"),)


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    target_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    reason = db.Column(db.String(300), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    target = db.relationship("User", foreign_keys=[target_id])
    __table_args__ = (db.UniqueConstraint("reporter_id", "target_id"),)


class ChatReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    target_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    reason = db.Column(db.String(500), default="")
    status = db.Column(db.String(20), default="pending")
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reporter = db.relationship("User", foreign_keys=[reporter_id])
    target = db.relationship("User", foreign_keys=[target_id])


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False, default="")
    media = db.Column(db.String(300), default="")
    media_type = db.Column(db.String(10), default="")
    reply_to_id = db.Column(db.Integer, db.ForeignKey("chat_message.id"), nullable=True)
    reaction = db.Column(db.String(16), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    is_starred = db.Column(db.Boolean, default=False)
    edited_at = db.Column(db.DateTime, nullable=True)
    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])
    reply_to = db.relationship("ChatMessage", remote_side=[id], foreign_keys=[reply_to_id])


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
    muted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", foreign_keys=[user_id])
    __table_args__ = (db.UniqueConstraint("user_id", "peer_id"),)


class Block(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blocker_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    blocked_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    blocker = db.relationship("User", foreign_keys=[blocker_id])
    blocked = db.relationship("User", foreign_keys=[blocked_id])
    __table_args__ = (db.UniqueConstraint("blocker_id", "blocked_id"),)


class ArchivedChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    peer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", foreign_keys=[user_id])
    peer = db.relationship("User", foreign_keys=[peer_id])
    __table_args__ = (db.UniqueConstraint("user_id", "peer_id"),)


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(8), unique=True, default=gen_public_id, nullable=False, index=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(300), default="")
    avatar = db.Column(db.String(300), default="")
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    is_banned = db.Column(db.Boolean, default=False)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner = db.relationship("User", foreign_keys=[owner_id])
    members = db.relationship("GroupMember", backref="group", lazy=True, cascade="all, delete-orphan")
    messages = db.relationship("GroupMessage", backref="group", lazy=True, cascade="all, delete-orphan")
    join_requests = db.relationship("GroupJoinRequest", backref="group", lazy=True, cascade="all, delete-orphan")


class GroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role = db.Column(db.String(10), default="member")
    muted = db.Column(db.Boolean, default=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", foreign_keys=[user_id])
    __table_args__ = (db.UniqueConstraint("group_id", "user_id"),)


class GroupMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False, default="")
    media = db.Column(db.String(300), default="")
    media_type = db.Column(db.String(10), default="")
    reply_to_id = db.Column(db.Integer, db.ForeignKey("group_message.id"), nullable=True)
    reaction = db.Column(db.String(16), default="")
    is_starred = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sender = db.relationship("User", foreign_keys=[sender_id])
    reply_to = db.relationship("GroupMessage", remote_side=[id], foreign_keys=[reply_to_id])


class GroupReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    reason = db.Column(db.String(300), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    group = db.relationship("Group", foreign_keys=[group_id])
    __table_args__ = (db.UniqueConstraint("reporter_id", "group_id"),)


class GroupJoinRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", foreign_keys=[user_id])
    __table_args__ = (db.UniqueConstraint("group_id", "user_id"),)


class SiteSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    splash_enabled = db.Column(db.Boolean, default=False)
    splash_title = db.Column(db.String(120), default="")
    splash_subtitle = db.Column(db.String(200), default="")
    splash_image = db.Column(db.String(300), default="")
    splash_bg_color = db.Column(db.String(20), default="#0f172a")
    splash_text_color = db.Column(db.String(20), default="#ffffff")
    splash_button_text = db.Column(db.String(60), default="دخول")
    splash_duration = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_site_settings():
    s = SiteSettings.query.first()
    if not s:
        s = SiteSettings()
        db.session.add(s)
        db.session.commit()
    return s


class TypingIndicator(db.Model):
    """مؤشر الكتابة"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    peer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user = db.relationship("User", foreign_keys=[user_id])


def set_typing(user_id, peer_id=None, group_id=None):
    now = now_utc_naive()
    cutoff = now - timedelta(seconds=5)
    try:
        TypingIndicator.query.filter(TypingIndicator.updated_at < cutoff).delete(synchronize_session=False)
    except Exception:
        db.session.rollback()
    existing = TypingIndicator.query.filter_by(user_id=user_id, peer_id=peer_id, group_id=group_id).first()
    if existing:
        existing.updated_at = now
    else:
        db.session.add(TypingIndicator(user_id=user_id, peer_id=peer_id, group_id=group_id, updated_at=now))
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def get_typing_users(peer_id=None, group_id=None, exclude_user_id=None):
    cutoff = now_utc_naive() - timedelta(seconds=4)
    q = TypingIndicator.query.filter(TypingIndicator.updated_at >= cutoff)
    if peer_id is not None:
        q = q.filter(TypingIndicator.peer_id == peer_id)
    if group_id is not None:
        q = q.filter(TypingIndicator.group_id == group_id)
    if exclude_user_id:
        q = q.filter(TypingIndicator.user_id != exclude_user_id)
    rows = q.all()
    return [r.user for r in rows if r.user]


@login_manager.user_loader
def load_user(uid):
    try: return db.session.get(User, int(uid))
    except Exception: return None


# ═══════════════════════════════════════════════════════════════
# process_auto_ban
# ═══════════════════════════════════════════════════════════════
def process_auto_ban(user):
    if not user or user.is_banned:
        return False
    try:
        uid = user.id
        user.original_username = user.username
        user.pending_username_release = True
        user.username_release_at = now_utc_naive() + timedelta(hours=USERNAME_RELEASE_HOURS)
        user.is_banned = True
        user.under_review = False
        user.review_reason = ""
        user.review_started_at = None
        user.auto_banned_at = now_utc_naive()
        db.session.flush()

        StatusView.query.filter_by(viewer_id=uid).delete(synchronize_session=False)
        db.session.flush()

        statuses = Status.query.filter_by(user_id=uid).all()
        for s in statuses:
            StatusView.query.filter_by(status_id=s.id).delete(synchronize_session=False)
            if s.media:
                try:
                    p = os.path.join(app.config["STATUS_FOLDER"], s.media)
                    if os.path.exists(p): os.remove(p)
                except OSError: pass
            db.session.delete(s)
        db.session.flush()

        Message.query.filter_by(receiver_id=uid).delete(synchronize_session=False)
        db.session.flush()

        ChatMessage.query.filter(
            ChatMessage.reply_to_id.in_(
                db.session.query(ChatMessage.id).filter(
                    or_(ChatMessage.sender_id == uid, ChatMessage.receiver_id == uid)
                )
            )
        ).update({"reply_to_id": None}, synchronize_session=False)
        db.session.flush()

        chat_msgs = ChatMessage.query.filter(
            or_(ChatMessage.sender_id == uid, ChatMessage.receiver_id == uid)
        ).all()
        for m in chat_msgs:
            if m.media:
                try:
                    p = os.path.join(app.config["CHAT_FOLDER"], m.media)
                    if os.path.exists(p): os.remove(p)
                except OSError: pass
            db.session.delete(m)
        db.session.flush()

        Friendship.query.filter(
            or_(Friendship.requester_id == uid, Friendship.addressee_id == uid)
        ).delete(synchronize_session=False)
        db.session.flush()

        Block.query.filter(
            or_(Block.blocker_id == uid, Block.blocked_id == uid)
        ).delete(synchronize_session=False)
        db.session.flush()

        ArchivedChat.query.filter(
            or_(ArchivedChat.user_id == uid, ArchivedChat.peer_id == uid)
        ).delete(synchronize_session=False)
        db.session.flush()

        SavedChat.query.filter(
            or_(SavedChat.user_id == uid, SavedChat.peer_id == uid)
        ).delete(synchronize_session=False)
        db.session.flush()

        Device.query.filter_by(user_id=uid).delete(synchronize_session=False)
        db.session.flush()

        TypingIndicator.query.filter(
            or_(TypingIndicator.user_id == uid, TypingIndicator.peer_id == uid)
        ).delete(synchronize_session=False)
        db.session.flush()

        ChatReport.query.filter(
            or_(ChatReport.reporter_id == uid, ChatReport.target_id == uid)
        ).delete(synchronize_session=False)
        db.session.flush()

        Report.query.filter(
            or_(Report.reporter_id == uid, Report.target_id == uid)
        ).delete(synchronize_session=False)
        db.session.flush()

        GroupMessage.query.filter(
            GroupMessage.reply_to_id.in_(
                db.session.query(GroupMessage.id).filter_by(sender_id=uid)
            )
        ).update({"reply_to_id": None}, synchronize_session=False)
        db.session.flush()

        GroupMessage.query.filter_by(sender_id=uid).delete(synchronize_session=False)
        db.session.flush()

        GroupReport.query.filter_by(reporter_id=uid).delete(synchronize_session=False)
        db.session.flush()

        GroupJoinRequest.query.filter_by(user_id=uid).delete(synchronize_session=False)
        db.session.flush()

        owned_groups = Group.query.filter_by(owner_id=uid).all()
        for g in owned_groups:
            gid_local = g.id
            new_owner = GroupMember.query.filter(
                GroupMember.group_id == gid_local,
                GroupMember.user_id != uid
            ).order_by(
                case((GroupMember.role == "admin", 0), else_=1),
                GroupMember.joined_at.asc()
            ).first()
            if new_owner:
                new_owner.role = "owner"
                g.owner_id = new_owner.user_id
            else:
                for gm in GroupMessage.query.filter_by(group_id=gid_local).all():
                    if gm.media:
                        try:
                            p = os.path.join(app.config["GROUP_FOLDER"], gm.media)
                            if os.path.exists(p): os.remove(p)
                        except OSError: pass
                    db.session.delete(gm)
                if g.avatar:
                    try:
                        p = os.path.join(app.config["GROUP_FOLDER"], g.avatar)
                        if os.path.exists(p): os.remove(p)
                    except OSError: pass
                GroupReport.query.filter_by(group_id=gid_local).delete(synchronize_session=False)
                GroupJoinRequest.query.filter_by(group_id=gid_local).delete(synchronize_session=False)
                GroupMember.query.filter_by(group_id=gid_local).delete(synchronize_session=False)
                db.session.delete(g)
        db.session.flush()

        GroupMember.query.filter_by(user_id=uid).delete(synchronize_session=False)
        db.session.flush()

        if user.avatar:
            try:
                p = os.path.join(app.config["AVATAR_FOLDER"], user.avatar)
                if os.path.exists(p): os.remove(p)
            except OSError: pass
            user.avatar = ""

        user.bio = ""
        user.nickname = ""
        user.recovery_hash = ""
        user.username = f"__b{uid:04d}"[:5]

        db.session.commit()
        print(f"[BAN OK] user_id={uid}")
        return True

    except Exception as e:
        db.session.rollback()
        print(f"[process_auto_ban ERROR] user_id={user.id if user else '?'}: {e}")
        traceback.print_exc()
        try:
            u2 = db.session.get(User, user.id)
            if u2:
                u2.is_banned = True
                u2.under_review = False
                u2.original_username = u2.username
                u2.username = f"__b{u2.id:04d}"[:5]
                db.session.commit()
                return True
        except Exception:
            db.session.rollback()
        return False


def release_pending_usernames():
    now = now_utc_naive()
    pending = User.query.filter(User.pending_username_release == True,
                                User.username_release_at <= now).all()
    for u in pending:
        u.pending_username_release = False
        u.username_release_at = None
    if pending: db.session.commit()


def init_db():
    with app.app_context():
        db.create_all()
        try:
            insp = db.inspect(db.engine)
            user_cols = [c["name"] for c in insp.get_columns("user")]
            for col, typ in [
                ("recovery_hash", "VARCHAR(64) DEFAULT ''"),
                ("nickname", "VARCHAR(64) DEFAULT ''"),
                ("last_seen", "TIMESTAMP"),
                ("profile_views", "INTEGER DEFAULT 0"),
                ("reports_count", "INTEGER DEFAULT 0"),
                ("auto_banned_at", "TIMESTAMP"),
                ("original_username", "VARCHAR(5) DEFAULT ''"),
                ("pending_username_release", "BOOLEAN DEFAULT FALSE"),
                ("username_release_at", "TIMESTAMP"),
                ("under_review", "BOOLEAN DEFAULT FALSE"),
                ("review_reason", "VARCHAR(300) DEFAULT ''"),
                ("review_started_at", "TIMESTAMP"),
                ("dark_mode", "BOOLEAN DEFAULT FALSE"),
            ]:
                if col not in user_cols:
                    db.session.execute(text(f'ALTER TABLE "user" ADD COLUMN {col} {typ}'))
                    db.session.commit()
            group_cols = [c["name"] for c in insp.get_columns("group")]
            if "is_public" not in group_cols:
                db.session.execute(text('ALTER TABLE "group" ADD COLUMN is_public BOOLEAN DEFAULT FALSE'))
                db.session.commit()
            status_cols = [c["name"] for c in insp.get_columns("status")]
            if "privacy" not in status_cols:
                db.session.execute(text("ALTER TABLE \"status\" ADD COLUMN privacy VARCHAR(10) DEFAULT 'public'"))
                db.session.commit()
            for tbl, cols in [
                ("chat_message", [("reply_to_id", "INTEGER"), ("reaction", "VARCHAR(16) DEFAULT ''"),
                                   ("media_type", "VARCHAR(10) DEFAULT ''"), ("is_starred", "BOOLEAN DEFAULT FALSE"),
                                   ("edited_at", "TIMESTAMP")]),
                ("group_message", [("reply_to_id", "INTEGER"), ("reaction", "VARCHAR(16) DEFAULT ''"),
                                    ("media_type", "VARCHAR(10) DEFAULT ''"), ("is_starred", "BOOLEAN DEFAULT FALSE")]),
                ("saved_chat", [("muted", "BOOLEAN DEFAULT FALSE")]),
                ("group_member", [("muted", "BOOLEAN DEFAULT FALSE")]),
            ]:
                try:
                    existing = [c["name"] for c in insp.get_columns(tbl)]
                except Exception:
                    continue
                for col, typ in cols:
                    if col not in existing:
                        db.session.execute(text(f'ALTER TABLE "{tbl}" ADD COLUMN {col} {typ}'))
                        db.session.commit()
            # typing_indicator
            try:
                insp.get_columns("typing_indicator")
            except Exception:
                db.session.execute(text("""
                    CREATE TABLE IF NOT EXISTS typing_indicator (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        peer_id INTEGER,
                        group_id INTEGER,
                        updated_at TIMESTAMP
                    )
                """))
                db.session.commit()
        except Exception as e:
            print(f"[init_db] migration warning: {e}")
            db.session.rollback()


init_db()


def is_valid_username(u): return bool(re.match(r"^[a-zA-Z0-9_]{3,5}$", u))


def is_valid_nickname(name):
    if not name: return False
    parts = [p for p in name.strip().split() if len(p) >= 1]
    return 1 <= len(parts) <= 4


def avatar_url(user):
    if not user: return ""
    if user.avatar:
        return url_for("serve_upload", subpath=f"avatars/{user.avatar}")
    return f"https://ui-avatars.com/api/?name={user.username}&background=e5e7eb&color=374151&size=200"


def group_avatar_url(g):
    if not g: return ""
    if g.avatar:
        return url_for("serve_upload", subpath=f"groups/{g.avatar}")
    return f"https://ui-avatars.com/api/?name={g.name}&background=dbeafe&color=1e40af&size=200"


def upload_url(kind, filename): return url_for("serve_upload", subpath=f"{kind}/{filename}")


def cleanup_old_statuses():
    cutoff = now_utc_naive() - timedelta(hours=24)
    old = Status.query.filter(Status.created_at < cutoff).all()
    if not old: return
    for s in old:
        if s.media:
            try: os.remove(os.path.join(app.config["STATUS_FOLDER"], s.media))
            except OSError: pass
        StatusView.query.filter_by(status_id=s.id).delete(synchronize_session=False)
        db.session.delete(s)
    db.session.commit()


def save_device(user):
    token = gen_device_token()
    db.session.add(Device(user_id=user.id, token=token,
                          user_agent=request.headers.get("User-Agent", "")[:255]))
    db.session.commit()
    return token


def unread_chat_count(user_id):
    blocked_ids = get_blocked_ids(user_id)
    blocked_by_ids = get_blocked_by_ids(user_id)
    excluded = blocked_ids | blocked_by_ids
    q = ChatMessage.query.filter_by(receiver_id=user_id, is_read=False)
    if excluded: q = q.filter(~ChatMessage.sender_id.in_(excluded))
    return q.count()


def get_blocked_ids(user_id):
    rows = Block.query.filter_by(blocker_id=user_id).all()
    return {r.blocked_id for r in rows}


def get_blocked_by_ids(user_id):
    rows = Block.query.filter_by(blocked_id=user_id).all()
    return {r.blocker_id for r in rows}


def is_blocked_between(a_id, b_id):
    return Block.query.filter(or_(
        and_(Block.blocker_id == a_id, Block.blocked_id == b_id),
        and_(Block.blocker_id == b_id, Block.blocked_id == a_id))).first() is not None


def get_friends(user_id):
    rows = Friendship.query.filter(Friendship.status == "accepted",
        or_(Friendship.requester_id == user_id,
            Friendship.addressee_id == user_id)).all()
    ids = [r.addressee_id if r.requester_id == user_id else r.requester_id for r in rows]
    if not ids: return []
    excluded = get_blocked_ids(user_id) | get_blocked_by_ids(user_id)
    ids = [i for i in ids if i not in excluded]
    if not ids: return []
    return User.query.filter(User.id.in_(ids)).all()


def get_friend_ids(user_id): return {u.id for u in get_friends(user_id)}


def friendship_status(a_id, b_id):
    r = Friendship.query.filter(or_(
        and_(Friendship.requester_id == a_id, Friendship.addressee_id == b_id),
        and_(Friendship.requester_id == b_id, Friendship.addressee_id == a_id))).first()
    if not r: return "none", None
    if r.status == "accepted": return "friends", r
    if r.requester_id == a_id: return "pending_out", r
    return "pending_in", r


def get_group_member(gid, uid):
    return GroupMember.query.filter_by(group_id=gid, user_id=uid).first()


def is_group_admin_or_owner(gid, uid):
    m = get_group_member(gid, uid)
    return m and m.role in ("owner", "admin")


def html_escape_text(t):
    if t is None: return ""
    return (str(t).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))


def linkify_text(text):
    """يحول الروابط إلى قابلة للنقر"""
    if not text: return ""
    escaped = html_escape_text(text)
    url_re = re.compile(r'(https?://[^\s<]+)')
    def repl(m):
        url = m.group(1)
        return f'<a href="{url}" target="_blank" rel="noopener" class="chat-link">{url}</a>'
    return url_re.sub(repl, escaped)


def copy_btn_html(text, label="نسخ", small=False):
    safe = str(text).replace("\\", "\\\\").replace("'", "\\'")
    size_style = "padding:2px 8px;font-size:10px" if small else "padding:3px 9px;font-size:11px"
    return (f'<button class="copy-btn" style="{size_style};margin-right:4px" '
            f'onclick="copyText(\'{safe}\', this)" title="نسخ {label}">{label}</button>')


@app.route("/uploads/<path:subpath>")
def serve_upload(subpath):
    return send_from_directory(UPLOAD_DIR, subpath)


# ═══════════════════ Splash ═══════════════════
@app.route("/splash-continue", methods=["POST"])
def splash_continue():
    session["splash_seen"] = True
    return jsonify({"ok": True})


@app.before_request
def splash_gate():
    try:
        if request.endpoint in ("static", "serve_upload", "splash_view", "splash_continue",
                                 "support_login", "support_logout", "support_dashboard",
                                 "support_splash", "support_splash_save", "support_splash_upload",
                                 "support_splash_delete"):
            return None
        if request.path.startswith("/support") or request.path.startswith("/uploads"):
            return None
        s = SiteSettings.query.first()
        if s and s.splash_enabled and not session.get("splash_seen"):
            return redirect(url_for("splash_view"))
    except Exception:
        pass
    return None


@app.route("/splash")
def splash_view():
    s = get_site_settings()
    if not s.splash_enabled:
        session["splash_seen"] = True
        return redirect(url_for("index"))
    if session.get("splash_seen"):
        return redirect(url_for("index"))
    img_html = ""
    if s.splash_image:
        img_url = url_for("serve_upload", subpath=f"splash/{s.splash_image}")
        img_html = f'<img src="{img_url}" style="max-width:280px;max-height:280px;border-radius:24px;margin-bottom:28px;object-fit:cover;box-shadow:0 20px 60px rgba(0,0,0,.5)">'
    auto_script = ""
    if s.splash_duration and s.splash_duration > 0:
        auto_script = f'<script>setTimeout(function(){{document.getElementById("splash-form").submit();}},{s.splash_duration*1000});</script>'
    return render_template_string(f"""<!DOCTYPE html>
<html lang="ar" dir="rtl"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{SITE_NAME}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,'Segoe UI',Tahoma,sans-serif;background:{s.splash_bg_color};color:{s.splash_text_color};
min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;text-align:center}}
.box{{max-width:440px;width:100%}}
h1{{font-size:30px;font-weight:900;letter-spacing:2px;margin-bottom:14px;
background:linear-gradient(135deg,{s.splash_text_color},#93c5fd);-webkit-background-clip:text;
-webkit-text-fill-color:transparent;background-clip:text}}
.sub{{font-size:16px;line-height:1.7;opacity:.85;margin-bottom:32px}}
.btn{{display:inline-block;padding:16px 60px;border-radius:14px;background:{s.splash_text_color};
color:{s.splash_bg_color};font-size:17px;font-weight:800;border:none;cursor:pointer;
transition:.2s;font-family:inherit;letter-spacing:1px}}
.btn:hover{{transform:translateY(-3px);box-shadow:0 12px 40px rgba(255,255,255,.25)}}
.logo{{font-size:80px;margin-bottom:16px}}
</style></head><body>
<div class="box">
  <div class="logo">🛡</div>
  {img_html}
  <h1>{s.splash_title or SITE_NAME}</h1>
  {f'<div class="sub">{s.splash_subtitle}</div>' if s.splash_subtitle else ''}
  <form method="POST" action="/splash-continue" id="splash-form">
    <button type="submit" class="btn">{s.splash_button_text or 'دخول'}</button>
  </form>
</div>
{auto_script}
</body></html>""")


@app.errorhandler(413)
@app.errorhandler(RequestEntityTooLarge)
def handle_too_large(e):
    flash("حجم الملف كبير جداً. الحد الأقصى 200 ميجابايت.", "error")
    return redirect(request.referrer or url_for("feed"))


@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return render_page("""
    <div class="card center">
      <div style="font-size:56px;margin-bottom:10px">⚠️</div>
      <h2 style="color:#991b1b">خطأ داخلي</h2>
      <p style="color:#6b7280;margin:14px 0;font-size:14px">حدث خطأ غير متوقع.</p>
      <a class="btn btn-primary" href="/support/dashboard">رجوع للوحة الدعم</a>
    </div>""", title="خطأ"), 500


BASE_STYLE = """
<style>
:root{--bg:#f7f7f8;--surface:#fff;--border:#e5e7eb;--text:#111827;--muted:#6b7280;
--accent:#111827;--accent-hover:#374151;--danger:#dc2626;--success:#16a34a;
--blue:#2563eb;--radius:14px;--glow:0 0 8px rgba(59,130,246,.8),0 0 16px rgba(59,130,246,.45);}
*{box-sizing:border-box;margin:0;padding:0}html,body{height:100%}
body{font-family:-apple-system,'Segoe UI','Tahoma',system-ui,sans-serif;background:var(--bg);
color:var(--text);min-height:100vh;display:flex;justify-content:center;padding:28px 16px 60px;line-height:1.6;
transition:background .2s,color .2s;}
body.dark{--bg:#0f172a;--surface:#1e293b;--border:#334155;--text:#f1f5f9;--muted:#94a3b8;
--accent:#3b82f6;--accent-hover:#60a5fa;}
body.dark .bubble.me{background:#1e3a8a;border-color:#1e40af;color:#fff;}
body.dark .bubble.them{background:#334155;border-color:#475569;color:#f1f5f9;}
body.dark .list-item{background:#1e293b;border-color:#334155;}
body.dark .list-item:hover{background:#334155;}
body.dark .acct-box{background:linear-gradient(135deg,#1e293b,#312e81);border-color:#4338ca;}
body.dark input,body.dark textarea{background:#1e293b;border-color:#334155;color:#f1f5f9;}
body.dark .topbar{background:#1e293b;border-color:#334155;}
body.dark .social-box{background:#1e293b;border-color:#334155;}
.container{width:100%;max-width:560px}
.brand{text-align:center;margin-bottom:26px}
.brand h1{font-size:28px;font-weight:800;letter-spacing:1px;line-height:1.4;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:24px 22px;margin-bottom:14px;}
.card.center{text-align:center}
h2{font-size:17px;font-weight:700;text-align:center;margin-bottom:18px}
label{display:block;font-size:13px;color:var(--muted);margin:12px 0 6px;font-weight:500}
input,textarea,select{width:100%;padding:12px 14px;border-radius:10px;border:1px solid var(--border);
background:var(--surface);color:var(--text);font-family:inherit;font-size:15px;transition:.15s;}
input:focus,textarea:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(17,24,39,.08);}
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
background:none;border:none;color:var(--accent);font-size:18px;cursor:pointer;width:36px;height:36px;padding:0;margin:0;
display:flex;align-items:center;justify-content:center;border-radius:8px;}
.avatar{width:96px;height:96px;border-radius:50%;object-fit:cover;border:2px solid var(--border);
margin-bottom:14px;cursor:pointer;transition:.15s;}
.avatar:hover{border-color:var(--blue);box-shadow:0 0 0 4px rgba(37,99,235,.15)}
.avatar-sm{width:40px;height:40px;border-radius:50%;object-fit:cover;cursor:pointer;}
.avatar-sm:hover{box-shadow:0 0 0 2px var(--blue)}
.name{font-size:20px;font-weight:800}
.username{color:var(--muted);font-size:14px;margin-top:2px}
.uid{display:inline-block;margin-top:10px;padding:4px 12px;background:var(--bg);border:1px solid var(--border);
border-radius:999px;font-size:12px;color:var(--muted);direction:ltr;}
.bio{margin-top:14px;font-size:15px;color:#374151;line-height:1.6}
.actions{margin-top:22px;display:flex;flex-direction:column;gap:8px}
.btn{display:block;padding:12px;border-radius:10px;border:1px solid var(--border);font-size:15px;font-weight:600;
text-align:center;text-decoration:none;cursor:pointer;transition:.15s;background:var(--surface);color:var(--text);}
.btn:hover{background:var(--bg);text-decoration:none}
.btn-primary{background:var(--accent);color:#fff;border-color:var(--accent);}
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
.topbar{display:flex;justify-content:space-around;align-items:center;gap:4px;margin-bottom:14px;padding:10px 6px;
background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);}
.topbar a{display:flex;flex-direction:column;align-items:center;gap:3px;font-size:11px;color:var(--muted);
flex:1;padding:6px 2px;border-radius:8px;transition:.15s;text-decoration:none;position:relative;}
.topbar a .ic{font-size:20px;line-height:1;color:var(--blue);text-shadow:var(--glow);transition:.2s;}
.topbar a:hover{background:var(--bg);color:var(--text);text-decoration:none}
.topbar a:hover .ic{transform:scale(1.1)}
.badge{position:absolute;top:2px;left:8px;background:#dc2626;color:#fff;font-size:10px;min-width:16px;height:16px;
border-radius:999px;display:flex;align-items:center;justify-content:center;padding:0 4px;}
.acct-box{background:linear-gradient(135deg,#eef2ff,#f5f3ff);border:1px solid #c7d2fe;border-radius:12px;
padding:14px;margin-bottom:14px;direction:ltr;text-align:left;}
.acct-row{display:flex;justify-content:space-between;align-items:center;padding:6px 0;font-size:14px;gap:8px}
.acct-row .k{color:#6b7280;font-size:12px;text-transform:uppercase;letter-spacing:.5px;flex-shrink:0}
.acct-row .v{font-family:monospace;font-weight:700;color:#1e3a8a;font-size:13px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.copy-btn{background:#fff;border:1px solid #c7d2fe;color:#3730a3;padding:4px 10px;border-radius:8px;
font-size:12px;cursor:pointer;margin:0;width:auto;font-weight:600;transition:.15s;display:inline-block;line-height:1.4;}
.copy-btn:hover{background:#eef2ff}
.copy-btn.done{background:#dcfce7;border-color:#86efac;color:#166534}
.recovery-box{background:#fffbeb;border:2px dashed #f59e0b;border-radius:12px;padding:16px;margin:14px 0;text-align:center;}
.recovery-box .code{font-size:20px;font-weight:800;color:#92400e;letter-spacing:2px;line-height:1.8;margin:10px 0;
direction:ltr;font-family:'Courier New',monospace;word-break:break-all;}
.recovery-box .warn{font-size:12px;color:#b45309}
.status-strip{display:flex;gap:12px;overflow-x:auto;padding-bottom:6px}
.status-item{flex:0 0 auto;text-align:center;width:72px;text-decoration:none;color:inherit}
.status-item .ring{display:inline-block;padding:2px;border-radius:50%;
background:linear-gradient(135deg,#16a34a,#84cc16);position:relative;}
.status-item.private .ring{background:linear-gradient(135deg,#f59e0b,#fbbf24);}
.status-item img{width:60px;height:60px;border-radius:50%;object-fit:cover;border:2px solid #fff;display:block;}
.status-item .sname{font-size:11px;color:var(--muted);margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.status-item .vid-tag{position:absolute;bottom:0;right:0;background:rgba(0,0,0,.7);color:#fff;font-size:9px;
padding:1px 5px;border-radius:8px;border:2px solid #fff;font-weight:700;}
.status-item .count-badge{position:absolute;top:-2px;left:-2px;background:#dc2626;color:#fff;font-size:10px;
min-width:18px;height:18px;border-radius:999px;display:flex;align-items:center;justify-content:center;
border:2px solid #fff;font-weight:700;}
.status-item .priv-tag{position:absolute;bottom:0;left:0;background:rgba(245,158,11,.95);color:#fff;font-size:9px;
padding:1px 5px;border-radius:8px;border:2px solid #fff;font-weight:700;}
.status-view{position:fixed;inset:0;background:#000;z-index:1000;display:flex;flex-direction:column;
align-items:center;justify-content:center;padding:20px;overflow-y:auto;}
.status-view img,.status-view video{max-width:100%;max-height:60vh;border-radius:12px;object-fit:contain;}
.status-view .stext{color:#fff;font-size:20px;text-align:center;margin-top:16px;max-width:600px;line-height:1.6;}
.status-view .scaption{color:#e5e7eb;font-size:15px;text-align:center;margin-top:10px;max-width:600px;
line-height:1.5;font-style:italic;}
.status-view .smeta{color:#9ca3af;font-size:13px;margin-top:12px;text-align:center}
.status-view .close{position:absolute;top:16px;left:16px;color:#fff;font-size:22px;background:rgba(255,255,255,.12);
border:none;width:40px;height:40px;border-radius:50%;cursor:pointer;display:flex;align-items:center;
justify-content:center;padding:0;margin:0;}
.status-owner-actions{position:absolute;top:16px;right:16px;display:flex;gap:8px;z-index:10}
.status-owner-actions .sbtn{display:inline-flex;align-items:center;gap:4px;padding:8px 14px;border-radius:8px;
font-size:13px;font-weight:600;text-decoration:none;cursor:pointer;border:none;transition:.15s;width:auto;margin:0;color:#fff}
.status-owner-actions .sbtn.edit{background:rgba(37,99,235,.9)}
.status-owner-actions .sbtn.del{background:rgba(220,38,38,.9)}
.status-owner-actions .sbtn.viewers{background:rgba(22,163,74,.9)}
.status-actions-bottom{display:flex;gap:10px;justify-content:center;margin-top:16px;flex-wrap:wrap;z-index:15;position:relative}
.status-actions-bottom .action-btn{display:inline-flex;align-items:center;gap:6px;padding:10px 20px;
border-radius:10px;font-size:14px;font-weight:700;text-decoration:none;cursor:pointer;transition:.15s;color:#fff;border:none}
.status-actions-bottom .action-btn.chat{background:rgba(37,99,235,.95)}
.status-actions-bottom .action-btn.chat:hover{background:#2563eb;transform:translateY(-2px);text-decoration:none;color:#fff}
.status-actions-bottom .action-btn.add{background:rgba(22,163,74,.95)}
.status-actions-bottom .action-btn.add:hover{background:#16a34a;transform:translateY(-2px);text-decoration:none;color:#fff}
.status-actions-bottom .action-btn.profile{background:rgba(107,114,128,.95)}
.status-actions-bottom .action-btn.profile:hover{background:#6b7280;transform:translateY(-2px);text-decoration:none;color:#fff}
.status-nav{position:absolute;bottom:20px;left:0;right:0;display:flex;justify-content:center;gap:10px;z-index:20;align-items:center}
.status-nav .nav-btn{background:rgba(255,255,255,.2);color:#fff;border:none;padding:8px 16px;border-radius:8px;
font-size:13px;font-weight:600;cursor:pointer;width:auto;margin:0}
.status-nav .nav-btn:hover{background:rgba(255,255,255,.35)}
.status-nav .counter{color:#fff;font-size:13px}
.icon-btn{background:var(--bg);border:1px solid var(--border);color:var(--text);width:36px;height:36px;
border-radius:9px;font-size:17px;cursor:pointer;display:flex;align-items:center;justify-content:center;
transition:.15s;padding:0;margin:0;flex-shrink:0;}
.icon-btn:hover{background:#eef0f3}
.mention{color:var(--blue);font-weight:700;background:#eff6ff;padding:1px 6px;border-radius:6px;text-decoration:none}
.empty{text-align:center;color:var(--muted);font-size:14px;padding:20px 0}
.list-item{display:flex;align-items:center;gap:10px;background:#f7f7f8;border:1px solid #e5e7eb;
border-radius:10px;padding:10px;margin-bottom:8px;text-decoration:none;color:inherit;flex-wrap:wrap;}
.list-item:hover{background:#eef0f3;text-decoration:none}
.list-item .li-name{font-weight:700}.list-item .li-sub{color:var(--muted);font-size:12px}
.list-item .li-actions{margin-right:auto;display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.chat-header{display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap}
.chat-header .pn{font-weight:800;font-size:15px}
.chat-header .pu{color:var(--muted);font-size:12px}
.online-dot{display:inline-block;width:10px;height:10px;border-radius:50%;background:#22c55e;
margin-right:4px;box-shadow:0 0 0 2px var(--surface);animation:pulseOnline 2s infinite;}
@keyframes pulseOnline{0%,100%{box-shadow:0 0 0 2px var(--surface),0 0 0 0 rgba(34,197,94,.6);}
50%{box-shadow:0 0 0 2px var(--surface),0 0 0 6px rgba(34,197,94,0);}}
.chat-box{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px;
height:60vh;overflow-y:auto;display:flex;flex-direction:column;gap:10px;}
.bubble{max-width:75%;padding:10px 14px;border-radius:14px;font-size:15px;line-height:1.5;word-wrap:break-word;position:relative;}
.bubble.me{align-self:flex-start;background:#eef2ff;border:1px solid #c7d2fe}
.bubble.them{align-self:flex-end;background:var(--bg);border:1px solid var(--border)}
.bubble .t{font-size:10px;color:var(--muted);margin-top:4px;display:flex;align-items:center;gap:4px;justify-content:flex-end;}
.bubble img,.bubble video{display:block;border-radius:10px;margin-bottom:4px;max-width:100%;max-height:320px;}
.bubble-wrap{display:flex;flex-direction:column;width:100%;position:relative;}
.bubble-wrap:has(.bubble.me){align-items:flex-start}
.bubble-wrap:has(.bubble.them){align-items:flex-end}
.reply-quote{background:rgba(0,0,0,.06);border-right:3px solid #2563eb;border-radius:8px;
padding:6px 10px;margin-bottom:6px;font-size:13px;line-height:1.4;}
.reply-quote .rq-name{font-weight:800;color:#2563eb;font-size:12px;margin-bottom:2px}
.reply-quote .rq-body{color:#4b5563;white-space:pre-wrap;word-break:break-word}
.reaction-badge{position:absolute;bottom:-10px;background:#fff;border:1px solid var(--border);
border-radius:999px;padding:2px 8px;font-size:14px;box-shadow:0 1px 4px rgba(0,0,0,.1);line-height:1.2;z-index:2}
.bubble.me .reaction-badge{left:8px}
.bubble.them .reaction-badge{right:8px}
.reply-preview{display:flex;align-items:center;gap:10px;background:#eff6ff;border:1px solid #bfdbfe;
border-radius:10px;padding:8px 12px;margin-top:8px;border-right:4px solid #2563eb}
.reply-preview .rp-info{flex:1;min-width:0}
.reply-preview .rp-name{font-weight:800;color:#1e40af;font-size:12px}
.reply-preview .rp-body{color:#4b5563;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.reply-preview .rp-close{background:transparent;border:none;color:#6b7280;font-size:18px;
cursor:pointer;width:30px;height:30px;padding:0;margin:0;flex-shrink:0;border-radius:6px}
.reply-preview .rp-close:hover{background:#dbeafe}
.emoji-picker{background:#fff;border:1px solid var(--border);border-radius:12px;padding:10px;
margin-top:8px;max-height:180px;overflow-y:auto;box-shadow:0 4px 14px rgba(0,0,0,.08)}
.emoji-picker #emoji-grid,.emoji-picker #emoji-grid-g{display:grid;grid-template-columns:repeat(auto-fill,minmax(36px,1fr));gap:4px}
.emoji-item{background:transparent;border:none;font-size:22px;cursor:pointer;padding:4px;margin:0;
width:auto;border-radius:8px;transition:.1s;line-height:1}
.emoji-item:hover{background:#eef2ff;transform:scale(1.15)}
.msg-action-bar{display:none;background:#fff;border:1px solid var(--border);border-radius:12px;
padding:8px 10px;margin-top:4px;box-shadow:0 4px 14px rgba(0,0,0,.10);animation:slideDown .18s ease-out;
position:relative;z-index:5;max-width:100%;}
.msg-action-bar.show{display:flex;flex-wrap:wrap;gap:4px;align-items:center;}
.msg-action-bar .emoji-quick{background:transparent;border:none;font-size:20px;cursor:pointer;
padding:4px 6px;margin:0;width:auto;border-radius:8px;transition:.12s;line-height:1;}
.msg-action-bar .emoji-quick:hover{background:#eef2ff;transform:scale(1.2);}
.msg-action-bar .act-divider{width:1px;height:22px;background:var(--border);margin:0 4px;}
.msg-action-bar .act-btn{background:#f7f7f8;border:1px solid var(--border);color:var(--text);
padding:6px 12px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;margin:0;width:auto;
display:inline-flex;align-items:center;gap:4px;transition:.12s;}
.msg-action-bar .act-btn:hover{background:#eef2ff;border-color:#c7d2fe;}
.msg-action-bar .act-btn.report{background:#fef2f2;border-color:#fecaca;color:#991b1b;}
.msg-action-bar .act-btn.report:hover{background:#fee2e2;}
.msg-action-bar .act-btn.delete{background:#fef2f2;border-color:#fecaca;color:#991b1b;}
.msg-action-bar .act-btn.delete:hover{background:#fee2e2;}
.msg-action-bar .act-btn.clear-react{background:#fef3c7;border-color:#fcd34d;color:#92400e;}
.msg-action-bar .act-btn.clear-react:hover{background:#fde68a;}
.msg-action-bar .act-btn.all-emojis{background:#eff6ff;border-color:#bfdbfe;color:#1e40af;}
.msg-action-bar .act-btn.star{background:#fef9c3;border-color:#fde047;color:#854d0e;}
.bubble.clickable{cursor:pointer;}
.bubble.clickable:hover{box-shadow:0 0 0 2px rgba(37,99,235,.15);}
@keyframes slideDown{from{opacity:0;transform:translateY(-4px);}to{opacity:1;transform:translateY(0);}}
.chat-input{display:flex;gap:8px;margin-top:10px;align-items:center}
.chat-input input:not([type="file"]){flex:1;margin:0}
.chat-input button[type="submit"]{width:auto;padding:12px 20px;margin:0;flex-shrink:0}
.audio-bubble{background:#f3f4f6;border-radius:12px;padding:10px 14px;margin-bottom:6px;
display:flex;align-items:center;gap:10px;min-width:240px;}
.audio-bubble .music-icon{font-size:26px}
.audio-bubble audio{flex:1;height:38px}
.msg{background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:14px;margin-bottom:10px;}
.msg .meta{font-size:12px;color:var(--muted);margin-bottom:6px}
.msg .body{font-size:15px;line-height:1.5;white-space:pre-wrap}
.privacy-note{background:#fef3c7;border:1px solid #fcd34d;color:#78350f;border-radius:10px;
padding:10px 14px;font-size:13px;margin-bottom:14px;}
.privacy-choice{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:6px;}
.privacy-opt{position:relative;display:block;cursor:pointer;}
.privacy-opt input{position:absolute;opacity:0;pointer-events:none;width:0;height:0}
.privacy-opt .pbox{border:2px solid var(--border);border-radius:12px;padding:12px;text-align:center;
transition:.15s;background:#fff;}
.privacy-opt .pbox .picon{font-size:26px;display:block;margin-bottom:4px}
.privacy-opt .pbox .ptitle{font-weight:800;font-size:14px;display:block;color:var(--text)}
.privacy-opt .pbox .psub{font-size:11px;color:var(--muted);display:block;margin-top:2px}
.privacy-opt input:checked ~ .pbox{border-color:var(--blue);background:#eff6ff;box-shadow:0 0 0 3px rgba(37,99,235,.12)}
.privacy-opt input:checked ~ .pbox .ptitle{color:#1e40af}
.device-row{display:flex;justify-content:space-between;align-items:center;background:var(--bg);
border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin-bottom:8px;font-size:13px;}
.device-row .ua{font-size:11px;color:var(--muted);direction:ltr;text-align:left;max-width:220px;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.avatar-view{position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:2000;display:flex;align-items:center;
justify-content:center;padding:20px;}
.avatar-view img{max-width:95vw;max-height:90vh;border-radius:12px;object-fit:contain;
box-shadow:0 0 40px rgba(255,255,255,.15);}
.avatar-view .close-av{position:absolute;top:20px;right:20px;color:#fff;font-size:24px;
background:rgba(255,255,255,.15);border:none;width:44px;height:44px;border-radius:50%;cursor:pointer;
display:flex;align-items:center;justify-content:center;padding:0;margin:0;}
.social-box{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
padding:16px;margin-bottom:14px;text-align:center;}
.social-box h3{font-size:14px;font-weight:700;color:var(--muted);margin-bottom:12px;
letter-spacing:.5px;text-transform:uppercase;}
.social-btns{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
.social-btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;width:100%;
padding:12px 10px;border-radius:10px;font-size:13px;font-weight:700;
font-family:'Segoe UI',Tahoma,sans-serif;text-decoration:none;cursor:pointer;transition:.18s;
border:1px solid transparent;white-space:nowrap;direction:ltr;}
.social-btn:hover{transform:translateY(-2px);text-decoration:none;box-shadow:0 4px 12px rgba(0,0,0,.15);}
.social-btn svg{width:18px;height:18px;flex-shrink:0;}
.social-btn.tg{background:#229ED9;color:#fff}
.social-btn.tg2{background:#0088cc;color:#fff}
.social-btn.fb{background:#1877F2;color:#fff}
.social-btn.fb2{background:#0d65d9;color:#fff}
.blocked-badge{background:#fee2e2;color:#991b1b;font-size:11px;padding:2px 8px;border-radius:999px;
font-weight:700;border:1px solid #fecaca;display:inline-block}
.danger-zone{border:2px dashed #fecaca;border-radius:12px;padding:16px;margin-top:14px;background:#fef2f2;}
.switch-row{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 14px;
background:#f9fafb;border:1px solid var(--border);border-radius:10px;cursor:pointer;font-size:14px;
font-weight:600;color:var(--text);margin-top:6px;position:relative;user-select:none}
.switch-row input{position:absolute;opacity:0;pointer-events:none;width:0;height:0}
.switch-row .switch{width:44px;height:24px;background:#d1d5db;border-radius:999px;position:relative;
transition:.2s;flex-shrink:0}
.switch-row .switch::after{content:"";position:absolute;top:2px;left:2px;width:20px;height:20px;
background:#fff;border-radius:50%;transition:.2s;box-shadow:0 1px 3px rgba(0,0,0,.2)}
.switch-row input:checked ~ .switch{background:var(--blue)}
.switch-row input:checked ~ .switch::after{left:22px}
.role-badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:11px;font-weight:800;margin-left:6px}
.role-badge.owner{background:#fef3c7;color:#92400e;border:1px solid #fcd34d}
.role-badge.admin{background:#dbeafe;color:#1e40af;border:1px solid #93c5fd}
.role-badge.member{background:#f3f4f6;color:#6b7280;border:1px solid #e5e7eb}
.group-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px;
margin-bottom:10px;display:flex;gap:12px;align-items:center;text-decoration:none;color:inherit;transition:.15s}
.group-card:hover{border-color:var(--blue);box-shadow:0 0 0 3px rgba(37,99,235,.08);text-decoration:none}
.group-card .g-avatar{width:54px;height:54px;border-radius:14px;object-fit:cover;flex-shrink:0;border:2px solid var(--border)}
.group-card .g-name{font-weight:800;font-size:16px;margin-bottom:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.group-card .g-sub{font-size:12px;color:var(--muted)}
.group-id-box{background:linear-gradient(135deg,#dbeafe,#e0e7ff);border:2px solid #93c5fd;border-radius:12px;
padding:12px 16px;margin:12px 0;display:flex;align-items:center;justify-content:space-between;gap:10px;direction:ltr}
.group-id-box .gid-label{font-size:11px;color:#1e40af;font-weight:800;text-transform:uppercase;letter-spacing:1px}
.group-id-box .gid-value{font-family:'Courier New',monospace;font-size:22px;font-weight:900;color:#1e3a8a;letter-spacing:3px}
.group-avatar-clickable{cursor:zoom-in;transition:.15s}
.group-avatar-clickable:hover{transform:scale(1.04);box-shadow:0 0 0 4px rgba(37,99,235,.2)}
.bulk-user-row{display:flex;align-items:center;gap:10px;background:#fff;border:1px solid var(--border);
border-radius:10px;padding:10px;margin-bottom:6px;cursor:pointer;transition:.12s}
.bulk-user-row:hover{background:#f7f7f8}
.bulk-user-row.selected{background:#eff6ff;border-color:#93c5fd;box-shadow:0 0 0 2px rgba(37,99,235,.12)}
.bulk-user-row input[type="checkbox"]{width:20px;height:20px;cursor:pointer;flex-shrink:0;accent-color:#2563eb}
.bulk-user-row label{flex:1;cursor:pointer;margin:0;display:flex;align-items:center;gap:10px}
.bulk-user-row .bu-name{font-weight:700;color:var(--text);font-size:14px}
.bulk-user-row .bu-sub{font-size:11px;color:var(--muted)}
.splash-preview{max-width:280px;border-radius:20px;border:2px solid var(--border);
box-shadow:0 10px 40px rgba(0,0,0,.15);margin:14px auto;display:block;}

/* صورة المرسل بجانب الرسالة */
.sender-head{display:inline-flex;align-items:center;gap:6px;margin-bottom:6px;
  text-decoration:none;color:#2563eb;font-weight:700;font-size:12px;
  padding:2px 6px;border-radius:8px;transition:.15s;}
.sender-head:hover{background:rgba(37,99,235,.08);text-decoration:none;color:#1e40af;}
.sender-avatar{width:24px;height:24px;border-radius:50%;object-fit:cover;
  border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.1);flex-shrink:0;}
.sender-name{font-size:12px;font-weight:700;}

/* مؤشر الكتابة */
.typing-indicator{display:none;align-items:center;gap:8px;
  background:#fff;border:1px solid #e5e7eb;border-radius:12px;
  padding:8px 14px;margin-top:8px;font-size:13px;color:#6b7280;
  box-shadow:0 2px 8px rgba(0,0,0,.04);}
.typing-indicator.show{display:flex;}
.typing-indicator .typing-name{font-weight:800;color:#2563eb;}
.typing-indicator .typing-dots{display:inline-flex;gap:3px;}
.typing-indicator .typing-dots span{width:6px;height:6px;border-radius:50%;
  background:#2563eb;animation:typingBounce 1.2s infinite;}
.typing-indicator .typing-dots span:nth-child(2){animation-delay:.15s;}
.typing-indicator .typing-dots span:nth-child(3){animation-delay:.3s;}
@keyframes typingBounce{
  0%,60%,100%{transform:translateY(0);opacity:.4;}
  30%{transform:translateY(-5px);opacity:1;}
}

/* علامة الصح */
.read-tick{font-size:11px;color:#9ca3af;letter-spacing:-2px;}
.read-tick.read{color:#3b82f6;}

/* الروابط */
.chat-link{color:#2563eb;font-weight:700;text-decoration:underline;word-break:break-all;}

/* نجمة التثبيت */
.star-badge{position:absolute;top:-6px;right:-6px;background:#fbbf24;color:#fff;
  width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:11px;box-shadow:0 1px 4px rgba(0,0,0,.2);z-index:3;}

/* زر الوضع الليلي */
.dark-toggle{position:fixed;top:14px;left:14px;z-index:500;background:var(--surface);
  border:1px solid var(--border);width:42px;height:42px;border-radius:50%;font-size:18px;
  cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;margin:0;
  box-shadow:0 2px 8px rgba(0,0,0,.1);transition:.15s;}
.dark-toggle:hover{transform:scale(1.08);}

/* شريط البحث في المحادثة */
.chat-search-bar{display:flex;gap:6px;margin-bottom:8px;}
.chat-search-bar input{flex:1;margin:0;padding:8px 12px;font-size:13px;}

/* خيارات إضافية */
.chat-options{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;
  padding-top:8px;border-top:1px dashed var(--border);}
.chat-options button{background:#f7f7f8;border:1px solid var(--border);color:var(--text);
  padding:6px 12px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;
  margin:0;width:auto;display:inline-flex;align-items:center;gap:4px;}
.chat-options button:hover{background:#eef2ff;}

/* معاينة الرابط */
.link-preview{background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;
  padding:10px 12px;margin-bottom:6px;font-size:13px;}
.link-preview .lp-title{font-weight:800;color:#0369a1;margin-bottom:2px;}
.link-preview .lp-url{color:#0284c7;font-size:11px;word-break:break-all;}
</style>
"""


def render_page(body, title=None, **ctx):
    t = title or SITE_NAME
    dark_class = "dark" if (current_user.is_authenticated and getattr(current_user, "dark_mode", False)) else ""
    return render_template_string(
        "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>{{ t }} — {{ site }}</title>" + BASE_STYLE + "</head><body class='" + dark_class + "'>"
        "<button class='dark-toggle' onclick='toggleDark()' title='الوضع الليلي' id='dark-toggle'>🌙</button>"
        "<div class='container'>"
        "<div class='brand'><h1>{{ site }}</h1></div>"
        + body + "</div>"
        "<script>"
        "function toggleDark(){document.body.classList.toggle('dark');"
        "try{fetch('/toggle-dark',{method:'POST',credentials:'same-origin'});}catch(e){}"
        "try{localStorage.setItem('dark',document.body.classList.contains('dark')?'1':'0');}catch(e){}}"
        "try{if(localStorage.getItem('dark')==='1'&&!document.body.classList.contains('dark'))document.body.classList.add('dark');}catch(e){}"
        "function togglePw(id){var e=document.getElementById(id);if(!e)return;"
        "e.type=e.type==='password'?'text':'password';}"
        "function previewStatusMedia(i){var f=i.files[0];if(!f)return;var u=URL.createObjectURL(f);"
        "var b=document.getElementById('status-preview');if(!b)return;"
        "if(f.type.startsWith('video')){b.innerHTML='<video style=\"max-width:100%;max-height:240px;border-radius:10px;margin-top:10px\" controls src=\"'+u+'\"></video>';}"
        "else if(f.type.startsWith('audio')){b.innerHTML='<audio style=\"width:100%;margin-top:10px\" controls src=\"'+u+'\"></audio>';}"
        "else{b.innerHTML='<img style=\"max-width:100%;max-height:240px;border-radius:10px;margin-top:10px\" src=\"'+u+'\">';}}"
        "function previewChatMedia(input){var f=input.files[0];if(!f)return;var u=URL.createObjectURL(f);"
        "var p=document.getElementById('chat-media-preview');if(!p)return;"
        "var html='';"
        "if(f.type.startsWith('video')){html='<video style=\"max-width:100%;max-height:200px;border-radius:10px\" controls src=\"'+u+'\"></video>';}"
        "else if(f.type.startsWith('audio')){html='<audio style=\"width:100%;margin-top:6px\" controls src=\"'+u+'\"></audio>';}"
        "else{html='<img style=\"max-width:100%;max-height:200px;border-radius:10px\" src=\"'+u+'\">';}"
        "html+='<button type=\"button\" class=\"copy-btn\" style=\"margin-top:6px\" onclick=\"clearChatMedia()\">إلغاء المرفق</button>';"
        "p.innerHTML=html;}"
        "function clearChatMedia(){var i=document.getElementById('chat-media-input');"
        "var p=document.getElementById('chat-media-preview');if(i)i.value='';if(p)p.innerHTML='';}"
        "function openStatus(id){var e=document.getElementById('sv-'+id);if(e)e.style.display='flex';}"
        "function closeStatus(id){var e=document.getElementById('sv-'+id);if(e)e.style.display='none';}"
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
        "b.textContent='\\u2713 \\u062a\\u0645';b.classList.add('done');"
        "setTimeout(function(){b.textContent=o;b.classList.remove('done');},1200);};"
        "if(navigator.clipboard&&window.isSecureContext){"
        "navigator.clipboard.writeText(t).then(done).catch(function(){fallbackCopy(t);done();});"
        "}else{fallbackCopy(t);done();}}"
        "function scrollChat(){var b=document.getElementById('chatbox');if(b)b.scrollTop=b.scrollHeight;}"
        "function formatCodeInput(el){el.value=el.value.toUpperCase().replace(/[^A-Z0-9]/g,'');}"
        "document.addEventListener('DOMContentLoaded',scrollChat);"
        "document.addEventListener('keydown',function(e){if(e.key==='Escape')closeAvatar();});"
        "var _chatRefreshTimer=null;"
        "function startChatAutoRefresh(url,interval){"
        "if(_chatRefreshTimer)clearInterval(_chatRefreshTimer);"
        "_chatRefreshTimer=setInterval(function(){"
        "var replyBox=document.getElementById('reply-preview');"
        "if(replyBox&&replyBox.style.display==='flex')return;"
        "var active=document.activeElement;"
        "if(active&&active.tagName==='INPUT'&&(active.id==='chat-body-input'||active.id==='group-body-input'))return;"
        "var openBar=document.querySelector('.msg-action-bar.show');if(openBar)return;"
        "fetch(url+'?ajax=1',{credentials:'same-origin'})"
        ".then(function(r){return r.json()}).then(function(d){"
        "if(d.html!==undefined){var b=document.getElementById('chatbox');"
        "if(b){var wasBottom=b.scrollTop+b.clientHeight>=b.scrollHeight-30;"
        "b.innerHTML=d.html;if(wasBottom)b.scrollTop=b.scrollHeight;}}"
        "if(d.unread!==undefined){var badge=document.getElementById('chat-badge-main');"
        "if(badge){if(d.unread>0){badge.textContent=d.unread;badge.style.display='flex';}"
        "else{badge.style.display='none';}}}"
        "if(d.typing!==undefined){var ti=document.getElementById('typing-indicator');"
        "var tt=document.getElementById('typing-text');"
        "if(ti&&tt){if(d.typing){tt.innerHTML=d.typing;ti.classList.add('show');}"
        "else{ti.classList.remove('show');}}}"
        "}).catch(function(){});},interval||1000);}"
        "</script>"
        "<div class='avatar-view' id='avatar-viewer' style='display:none' onclick='closeAvatar()'>"
        "<button class='close-av' onclick='event.stopPropagation();closeAvatar()'>✕</button>"
        "<img id='avatar-viewer-img' src='' onclick='event.stopPropagation()'>"
        "</div>"
        "</body></html>",
        t=t, site=SITE_NAME, **ctx)


@app.route("/toggle-dark", methods=["POST"])
def toggle_dark():
    if current_user.is_authenticated:
        try:
            current_user.dark_mode = not bool(current_user.dark_mode)
            db.session.commit()
        except Exception:
            db.session.rollback()
    return jsonify({"ok": True})


FLASH_BLOCK = """{% with msgs=get_flashed_messages(with_categories=true) %}
{% for c,m in msgs %}<div class="flash {{c}}">{{m}}</div>{% endfor %}{% endwith %}"""


def topbar_html(chat_badge=""):
    return f"""<div class="topbar">
<a href="{url_for('feed')}"><span class="ic">⌂</span>الرئيسية</a>
<a href="{url_for('discover')}"><span class="ic">⌕</span>أشخاص</a>
<a href="{url_for('search')}"><span class="ic">⌘</span>بحث</a>
<a href="{url_for('chats')}"><span class="ic">◈</span>الدردشات{chat_badge}</a>
<a href="{url_for('groups_list')}"><span class="ic">◉</span>مجموعات</a>
<a href="{url_for('friends_list')}"><span class="ic">♡</span>الأصدقاء</a>
<a href="{url_for('profile_me')}"><span class="ic">☺</span>بروفايلي</a>
</div>"""


def badge_html():
    if current_user.is_authenticated:
        c = unread_chat_count(current_user.id)
        if c:
            return f'<span class="badge" id="chat-badge-main">{c}</span>'
    return '<span class="badge" id="chat-badge-main" style="display:none">0</span>'


def social_box_html():
    return f"""<div class="social-box">
  <h3>Contact Us</h3>
  <div class="social-btns">
    <a class="social-btn tg" href="{TELEGRAM_URL}" target="_blank" rel="noopener">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>
      Telegram {TELEGRAM_HANDLE}
    </a>
    <a class="social-btn tg2" href="{TELEGRAM_URL_2}" target="_blank" rel="noopener">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>
      Telegram {TELEGRAM_HANDLE_2}
    </a>
    <a class="social-btn fb" href="{FACEBOOK_URL}" target="_blank" rel="noopener">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M22 12.06C22 6.5 17.52 2 12 2S2 6.5 2 12.06c0 5.02 3.66 9.18 8.44 9.94v-7.03H7.9v-2.91h2.54V9.85c0-2.51 1.49-3.9 3.77-3.9 1.09 0 2.24.2 2.24.2v2.47h-1.26c-1.24 0-1.63.78-1.63 1.57v1.87h2.78l-.44 2.91h-2.34V22c4.78-.76 8.44-4.92 8.44-9.94z"/></svg>
      Facebook
    </a>
    <a class="social-btn fb2" href="{FACEBOOK_URL_2}" target="_blank" rel="noopener">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M22 12.06C22 6.5 17.52 2 12 2S2 6.5 2 12.06c0 5.02 3.66 9.18 8.44 9.94v-7.03H7.9v-2.91h2.54V9.85c0-2.51 1.49-3.9 3.77-3.9 1.09 0 2.24.2 2.24.2v2.47h-1.26c-1.24 0-1.63.78-1.63 1.57v1.87h2.78l-.44 2.91h-2.34V22c4.78-.76 8.44-4.92 8.44-9.94z"/></svg>
      Facebook
    </a>
  </div>
</div>"""


# ═══════════════════════════════════════════════════════════════
# AUTH ROUTES
# ═══════════════════════════════════════════════════════════════
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("feed"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("feed"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower().lstrip("@")
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not is_valid_username(username):
            flash("اليوزر: 3 إلى 5 أحرف إنجليزية/أرقام/_ فقط.", "error")
            return redirect(url_for("register"))
        if len(password) < 8:
            flash("كلمة المرور 8 أحرف على الأقل.", "error")
            return redirect(url_for("register"))
        if password != confirm:
            flash("كلمتا المرور غير متطابقتين.", "error")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash("اليوزر محجوز، جرّب غيره.", "error")
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
        db.session.add(user)
        db.session.commit()
        token = save_device(user)
        login_user(user, remember=True)
        session.permanent = True
        session["show_recovery"] = recovery
        resp = make_response(redirect(url_for("welcome")))
        resp.set_cookie("device_token", token, max_age=60*60*24*365,
                        httponly=True, samesite="Lax",
                        secure=app.config["SESSION_COOKIE_SECURE"])
        return resp
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>إنشاء حساب</h2>
    <form method="POST">
    <label>اليوزر (3-5 أحرف إنجليزية — بدون @)</label>
    <input name="username" maxlength="5" placeholder="username" required
           pattern="[a-zA-Z0-9_]{{3,5}}" autocomplete="off">
    <label>كلمة المرور (8+)</label>
    <div class="pw-wrap"><input name="password" id="pw1" type="password" required>
    <button type="button" class="pw-toggle" onclick="togglePw('pw1')">👁</button></div>
    <label>تأكيد كلمة المرور</label>
    <div class="pw-wrap"><input name="confirm" id="pw2" type="password" required>
    <button type="button" class="pw-toggle" onclick="togglePw('pw2')">👁</button></div>
    <button type="submit">تسجيل</button></form>
    <a class="link-center" href="{url_for('login')}">لديك حساب؟ سجّل الدخول</a>
    <a class="link-center" href="{url_for('recover')}">عندك كود استعادة؟ ادخل مباشرة</a>
    </div>""" + social_box_html(), title="تسجيل")


@app.route("/welcome")
@login_required
def welcome():
    recovery = session.pop("show_recovery", None)
    if not recovery:
        return redirect(url_for("set_nickname"))
    formatted = format_code(recovery)
    return render_page("""
    <div class="card center">
      <h2>🎉 أهلاً بك</h2>
      <p style="color:#6b7280;font-size:13px;margin-bottom:12px">احفظ هذا الكود. لن يظهر مرة أخرى.</p>
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
        <button class="copy-btn" style="margin-top:10px" onclick="copyText('{{ recovery }}',this)">نسخ الكود</button>
      </div>
      <a class="btn btn-primary" href="{{ url_for('set_nickname') }}">فهمت، أكمل</a>
    </div>""", title="مرحبًا", user=current_user, recovery=recovery, formatted=formatted)


@app.route("/set-nickname", methods=["GET", "POST"])
@login_required
def set_nickname():
    if current_user.nickname_ok:
        return redirect(url_for("feed"))
    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()
        if not is_valid_nickname(nickname):
            flash("اللقب: من كلمة إلى 4 كلمات.", "error")
            return redirect(url_for("set_nickname"))
        current_user.nickname = nickname
        db.session.commit()
        flash("تم حفظ اللقب. أهلاً بك!", "success")
        return redirect(url_for("feed"))
    return render_page(FLASH_BLOCK + """
    <div class="card"><h2>اختر لقبك</h2>
    <p style="color:#6b7280;font-size:13px;text-align:center;margin-bottom:12px">من كلمة واحدة إلى 4 كلمات.</p>
    <form method="POST"><label>اللقب</label>
    <input name="nickname" maxlength="64" required placeholder="مثال: القمر الساهر">
    <button type="submit">حفظ ومتابعة</button></form></div>""", title="اللقب")


@app.route("/recover", methods=["GET", "POST"])
def recover():
    if current_user.is_authenticated:
        return redirect(url_for("feed"))
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper().replace("-", "").replace(" ", "")
        if len(code) != 20:
            flash("الكود يجب أن يكون 20 خانة.", "error")
            return redirect(url_for("recover"))
        h = hash_recovery_code(code)
        user = User.query.filter_by(recovery_hash=h).first()
        if not user:
            flash("الكود غير صحيح أو مستخدم من قبل.", "error")
            return redirect(url_for("recover"))
        if user.is_banned:
            flash("هذا الحساب محظور.", "error")
            return redirect(url_for("recover"))
        if user.under_review:
            flash("هذا الحساب تحت المراجعة حالياً.", "error")
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
        flash(f"تم الدخول. أهلاً @{user.username}! كودك الجديد أدناه.", "success")
        resp = make_response(redirect(url_for("welcome")))
        resp.set_cookie("device_token", token, max_age=60*60*24*365,
                        httponly=True, samesite="Lax",
                        secure=app.config["SESSION_COOKIE_SECURE"])
        return resp
    return render_page(FLASH_BLOCK + """
    <div class="card"><h2>🔐 استعادة الحساب بالكود</h2>
    <p style="color:#6b7280;font-size:13px;text-align:center;margin-bottom:16px">الصق كود الاستعادة (20 خانة).</p>
    <form method="POST" onsubmit="return validateCode()">
      <label>كود الاستعادة</label>
      <input name="code" id="recovery-input" maxlength="24" required autocomplete="off" autofocus
             style="direction:ltr;font-family:'Courier New',monospace;font-size:16px;
                    letter-spacing:2px;text-align:center"
             placeholder="XXXX-XXXX-XXXX-XXXX-XXXX" oninput="formatCodeInput(this)">
      <button type="submit">🔓 استعادة ودخول</button>
    </form>
    <a class="link-center" href="{{ url_for('login') }}">رجوع لتسجيل الدخول</a>
    </div>
    <script>
    function validateCode(){
      var v=document.getElementById('recovery-input').value.toUpperCase().replace(/[^A-Z0-9]/g,'');
      if(v.length!==20){alert('الكود يجب أن يكون 20 خانة (حاليًا: '+v.length+')');return false;}
      document.getElementById('recovery-input').value=v;return true;}
    </script>""", title="استعادة")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("feed"))
    if request.method == "POST":
        ip = request.remote_addr or "?"
        if is_rate_limited(ip):
            flash("محاولات كثيرة. انتظر 5 دقائق.", "error")
            return redirect(url_for("login"))
        username = request.form.get("username", "").strip().lower().lstrip("@")
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            record_login_attempt(ip)
            flash("بيانات الدخول غير صحيحة.", "error")
            return redirect(url_for("login"))
        if user.is_banned:
            return render_page(BANNED_PAGE, title="محظور",
                               username=user.original_username or user.username)
        if user.under_review:
            return render_page(UNDER_REVIEW_PAGE, title="تحت المراجعة",
                               reason=user.review_reason or "بلاغ عن محادثة",
                               started=fmt_sd(user.review_started_at))
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
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>تسجيل الدخول</h2>
    <form method="POST">
    <label>اليوزر</label>
    <input name="username" placeholder="username" required autocomplete="off">
    <label>كلمة المرور</label>
    <div class="pw-wrap"><input name="password" id="pw" type="password" required>
    <button type="button" class="pw-toggle" onclick="togglePw('pw')">👁</button></div>
    <button type="submit">دخول</button></form>
    <a class="link-center" href="{url_for('register')}">ليس لديك حساب؟ سجّل الآن</a>
    <a class="link-center" href="{url_for('recover')}" style="color:#2563eb;font-weight:700">
      🔑 نسيت اليوزر أو كلمة السر؟ ادخل بالكود</a>
    </div>""" + social_box_html(), title="دخول")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    resp = make_response(redirect(url_for("login")))
    resp.delete_cookie("device_token")
    return resp


BANNED_PAGE = """
<div class="card center" style="border:2px solid #fecaca;background:#fef2f2">
  <div style="font-size:64px;margin-bottom:10px">🚫</div>
  <h2 style="color:#991b1b;font-size:22px;margin-bottom:14px">تم حظر حسابك</h2>
  <div style="background:#fff;border:1px solid #fecaca;border-radius:12px;
              padding:16px;text-align:right;font-size:14px;line-height:1.8;color:#7f1d1d">
    <p><b>السبب:</b> تم حظر حسابك بسبب مخالفة شروط الاستخدام.</p>
    <p style="margin-top:10px"><b>ما تم حذفه:</b></p>
    <ul style="margin:6px 18px;font-size:13px">
      <li>جميع حالاتك ووسائطك</li>
      <li>جميع رسائلك ومحادثاتك</li>
      <li>صداقاتك وبياناتك الشخصية</li>
    </ul>
    <p style="margin-top:10px"><b>ملاحظة:</b> سيتم تحرير يوزرك ({{ username }}) تلقائياً بعد 24 ساعة.</p>
  </div>
  <div class="actions" style="margin-top:16px">
    <a class="btn btn-primary" href="{{ url_for('logout') }}"
       style="background:#dc2626;border-color:#dc2626">🚪 تسجيل الخروج</a>
    <a class="btn" href="{{ url_for('register') }}"
       style="background:#16a34a;border-color:#16a34a;color:#fff">➕ إنشاء حساب جديد</a>
  </div>
</div>
"""

UNDER_REVIEW_PAGE = """
<div class="card center" style="border:2px solid #fcd34d;background:#fffbeb">
  <div style="font-size:64px;margin-bottom:10px">⏳</div>
  <h2 style="color:#92400e;font-size:22px;margin-bottom:14px">حسابك تحت المراجعة</h2>
  <div style="background:#fff;border:1px solid #fcd34d;border-radius:12px;
              padding:16px;text-align:right;font-size:14px;line-height:1.8;color:#78350f">
    <p><b>السبب:</b> {{ reason }}</p>
    <p style="margin-top:10px"><b>وقت بدء المراجعة:</b> {{ started }}</p>
  </div>
  <div class="actions" style="margin-top:16px">
    <a class="btn btn-primary" href="{{ url_for('logout') }}"
       style="background:#f59e0b;border-color:#f59e0b;color:#fff">🚪 تسجيل الخروج</a>
  </div>
</div>
"""


@app.before_request
def before_each_request():
    if random.random() < 0.01:
        try: release_pending_usernames()
        except Exception: pass
    if not current_user.is_authenticated: return
    # تحديث آخر ظهور
    if random.random() < 0.1:
        try:
            current_user.last_seen = now_utc_naive()
            db.session.commit()
        except Exception:
            db.session.rollback()
    allowed_special = {
        "static", "serve_upload", "logout",
        "register", "login", "recover", "welcome",
        "support_login", "support_logout", "support_dashboard",
        "support_reports", "support_users", "support_groups",
        "support_ban_user", "support_unban_user",
        "support_dismiss_report", "support_ban_group",
        "support_unban_group", "support_dismiss_group_report",
        "support_user_detail", "support_chat_reports",
        "support_review_chat_report", "support_release_review",
        "support_bulk_ban", "support_bulk_ban_process",
        "support_splash", "support_splash_save",
        "support_splash_upload", "support_splash_delete",
        "splash_view", "splash_continue",
        "group_avatar_full", "toggle_dark",
        "chat_typing", "group_typing",
    }
    if request.endpoint not in allowed_special:
        try: fresh = db.session.get(User, int(current_user.id))
        except Exception: fresh = None
        if fresh:
            if fresh.is_banned:
                uname = fresh.original_username or fresh.username
                logout_user()
                return render_page(BANNED_PAGE, title="محظور", username=uname)
            if fresh.under_review:
                reason = fresh.review_reason or "بلاغ عن محادثة"
                started = fmt_sd(fresh.review_started_at)
                logout_user()
                return render_page(UNDER_REVIEW_PAGE, title="تحت المراجعة",
                                   reason=reason, started=started)
    allowed = {"set_nickname", "logout", "static", "serve_upload",
               "welcome", "support_login", "support_logout",
               "support_dashboard", "support_reports", "support_users",
               "support_groups", "support_ban_user", "support_unban_user",
               "support_dismiss_report", "support_ban_group",
               "support_unban_group", "support_dismiss_group_report",
               "support_user_detail", "support_chat_reports",
               "support_review_chat_report", "support_release_review",
               "support_bulk_ban", "support_bulk_ban_process",
               "support_splash", "support_splash_save",
               "support_splash_upload", "support_splash_delete",
               "splash_view", "splash_continue",
               "group_avatar_full", "toggle_dark",
               "chat_typing", "group_typing",
               "delete_account", "change_password"}
    if request.endpoint in allowed: return
    if not current_user.nickname_ok:
        return redirect(url_for("set_nickname"))


# ═══════════════════════════════════════════════════════════════
# PROFILE + FRIENDS + BLOCK + ARCHIVE
# ═══════════════════════════════════════════════════════════════
@app.route("/profile/me")
@login_required
def profile_me():
    return redirect(url_for("view_profile", username=current_user.username))


@app.route("/u/<username>/avatar")
def view_avatar_full(username):
    user = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not user or not user.avatar:
        abort(404)
    return render_page(f"""
    <div class="card center">
      <img src="{url_for('serve_upload', subpath='avatars/' + user.avatar)}"
           style="max-width:100%;border-radius:14px;object-fit:contain;max-height:80vh">
      <div class="name" style="margin-top:14px">{user.short_name}</div>
      <div class="username">@{user.username}</div>
      <a class="btn" href="{url_for('view_profile', username=user.username)}" style="margin-top:14px">← رجوع</a>
    </div>""", title=f"صورة {user.username}")


@app.route("/u/<username>")
def view_profile(username):
    user = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not user or user.is_banned:
        flash("المستخدم غير موجود.", "error")
        return redirect(url_for("index"))
    if not current_user.is_authenticated:
        flash("سجّل الدخول لعرض البروفايل.", "error")
        return redirect(url_for("login"))
    is_own = current_user.id == user.id
    friend_state, _ = ("none", None)
    if not is_own:
        friend_state, _ = friendship_status(current_user.id, user.id)
    is_friend = friend_state == "friends"
    i_blocked_them = user.id in get_blocked_ids(current_user.id)
    they_blocked_me = user.id in get_blocked_by_ids(current_user.id)
    if not is_own:
        try:
            view_key = f"viewed_{user.id}"
            last_view = session.get(view_key, 0)
            now_ts = time.time()
            if now_ts - last_view > 86400:
                user.profile_views = (user.profile_views or 0) + 1
                db.session.commit()
                session[view_key] = now_ts
        except Exception:
            db.session.rollback()
    badge = badge_html()
    av_url = avatar_url(user)
    joined_str = "—"; last_seen_str = "—"
    try: joined_str = user.created_at_sd
    except Exception: pass
    try: last_seen_str = time_ago_sd(user.last_seen)
    except Exception: pass
    online_badge = ""
    if user.is_online:
        online_badge = '<span class="online-dot"></span><span style="color:#22c55e;font-size:12px;font-weight:700">متصل الآن</span>'
    else:
        online_badge = f'<span style="color:#9ca3af;font-size:12px">آخر ظهور: {last_seen_str}</span>'
    if is_own or is_friend:
        profile_html = f"""
        <div class="name">{user.short_name}</div>
        <div class="username">@{user.username}</div>
        <div style="margin-top:6px">{online_badge}</div>
        <div class="uid">ID: {user.public_id}</div>
        <div class="acct-box" style="margin-top:12px">
          <div class="acct-row"><span class="k">USERNAME</span>
            <span class="v">@{user.username}
              {copy_btn_html(user.username, "نسخ", small=True)}
            </span></div>
          <div class="acct-row"><span class="k">ID</span>
            <span class="v">{user.public_id}
              {copy_btn_html(user.public_id, "نسخ", small=True)}
            </span></div>
          <div class="acct-row"><span class="k">NICKNAME</span>
            <span class="v" style="font-family:inherit">{user.nickname or '—'}</span></div>
          <div class="acct-row"><span class="k">JOINED (SD)</span>
            <span class="v" style="font-family:inherit">{joined_str}</span></div>
          <div class="acct-row"><span class="k">VIEWS</span>
            <span class="v">{user.profile_views or 0}</span></div>
        </div>"""
        if user.bio:
            profile_html += f'<div class="bio">{user.bio}</div>'
    else:
        profile_html = f"""
        <div class="name">@{user.username}</div>
        <div style="margin-top:6px">{online_badge}</div>
        <div class="uid">ID: {user.public_id} {copy_btn_html(user.public_id, "نسخ", small=True)}</div>
        <div class="privacy-note">🔒 البيانات الكاملة تظهر للأصدقاء فقط.</div>"""
        if user.bio:
            profile_html += f'<div class="bio">{user.bio}</div>'
    actions = ""
    if is_own:
        actions = f"""
        <a class="btn btn-primary" href="{url_for('edit_profile')}">تعديل البروفايل</a>
        <a class="btn" href="{url_for('discover')}">👥 اكتشف أشخاصًا</a>
        <a class="btn" href="{url_for('change_password')}">تغيير كلمة المرور</a>
        <a class="btn" href="{url_for('show_recovery_code')}">عرض كود الاستعادة</a>
        <a class="btn" href="{url_for('devices_list')}">الأجهزة المتصلة</a>
        <a class="btn" href="{url_for('blocked_list')}">🚫 المحظورون</a>
        <a class="btn" href="{url_for('archived_list')}">📦 الأرشيف</a>
        <a class="btn" href="{url_for('post_status')}">أضف حالة</a>
        <a class="btn" href="{url_for('inbox')}">الرسائل المجهولة</a>
        <a class="btn btn-danger" href="{url_for('delete_account')}">🗑 مسح الحساب نهائيًا</a>
        <a class="btn" href="{url_for('logout')}">تسجيل الخروج</a>"""
    else:
        if i_blocked_them:
            actions = '<div class="blocked-badge" style="margin-bottom:10px">🚫 أنت حظرت هذا المستخدم</div>'
            actions += f'<a class="btn btn-danger" href="{url_for("unblock_user", username=user.username)}">✅ إلغاء الحظر</a>'
        elif they_blocked_me:
            actions = '<div class="blocked-badge" style="margin-bottom:10px">🚫 لا يمكنك التفاعل مع هذا المستخدم</div>'
        else:
            if friend_state == 'none':
                actions = f'<a class="btn btn-primary" href="{url_for("friend_request", username=user.username)}">➕ إضافة صديق</a>'
                actions += f'<a class="btn" href="{url_for("send_message", username=user.username)}">✉ رسالة مجهولة</a>'
                actions += f'<a class="btn btn-danger" href="{url_for("block_user", username=user.username)}" onclick="return confirm(\'حظر هذا المستخدم؟\')">🚫 حظر</a>'
                actions += f'<a class="btn btn-danger" href="{url_for("report_user", username=user.username)}">إبلاغ</a>'
            elif friend_state == 'pending_out':
                actions = f'<a class="btn" href="{url_for("friends_requests")}">⏳ طلب معلّق — بانتظار الرد</a>'
                actions += f'<a class="btn" href="{url_for("send_message", username=user.username)}">✉ رسالة مجهولة</a>'
            elif friend_state == 'pending_in':
                actions = f'<a class="btn btn-primary" href="{url_for("friends_requests")}">✔ اقبل طلب الصداقة</a>'
                actions += f'<a class="btn" href="{url_for("send_message", username=user.username)}">✉ رسالة مجهولة</a>'
            else:
                actions = f'<a class="btn btn-primary" href="{url_for("chat_with", username=user.username)}">◈ ابدأ الدردشة</a>'
                actions += '<div style="text-align:center;color:#16a34a;font-weight:700;margin-top:4px">✓ أنتما صديقان</div>'
                actions += f'<a class="btn" href="{url_for("send_message", username=user.username)}">✉ رسالة مجهولة</a>'
                actions += f'<a class="btn btn-danger" href="{url_for("unfriend_user", username=user.username)}" onclick="return confirm(\'حذف هذا الصديق؟\')">✂ حذف صديق</a>'
    return render_page(FLASH_BLOCK + topbar_html(badge) + f"""
    <div class="card center">
      <img class="avatar" src="{av_url}" onclick="openAvatar('{av_url}')">
      <div style="font-size:11px;color:#9ca3af;margin-bottom:8px">🔍 اضغط على الصورة لعرضها كاملة</div>
      {profile_html}
      <div class="actions">{actions}</div>
    </div>""", title=user.username)


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()
        bio = request.form.get("bio", "").strip()
        if not is_valid_nickname(nickname):
            flash("اللقب: من كلمة إلى 4 كلمات.", "error")
            return redirect(url_for("edit_profile"))
        if len(bio) > 200:
            flash("النبذة طويلة جدًا.", "error")
            return redirect(url_for("edit_profile"))
        current_user.nickname = nickname
        current_user.bio = bio
        remove_avatar = request.form.get("remove_avatar") == "1"
        if remove_avatar and current_user.avatar:
            try:
                old_path = os.path.join(app.config["AVATAR_FOLDER"], current_user.avatar)
                if os.path.exists(old_path): os.remove(old_path)
            except OSError: pass
            current_user.avatar = ""
        file = request.files.get("avatar")
        if file and file.filename:
            if not allowed_image(file.filename) or not check_image_magic(file):
                flash("صيغة الصورة غير مدعومة.", "error")
                return redirect(url_for("edit_profile"))
            if current_user.avatar:
                try:
                    old_path = os.path.join(app.config["AVATAR_FOLDER"], current_user.avatar)
                    if os.path.exists(old_path): os.remove(old_path)
                except OSError: pass
            ext = file.filename.rsplit(".", 1)[1].lower()
            fn = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(app.config["AVATAR_FOLDER"], fn))
            current_user.avatar = fn
        db.session.commit()
        flash("تم التحديث.", "success")
        return redirect(url_for("profile_me"))
    badge = badge_html()
    has_avatar = bool(current_user.avatar)
    delete_btn = ('<button type="button" class="btn btn-danger" style="width:100%;margin-top:10px" '
                  'onclick="requestDeleteAvatar()">🗑 حذف الصورة الحالية</button>') if has_avatar else ''
    return render_page(FLASH_BLOCK + topbar_html(badge) + f"""
    <div class="card"><h2>تعديل البروفايل</h2>
    <form method="POST" enctype="multipart/form-data" id="edit-form">
      <div style="text-align:center;margin-bottom:14px">
        <img id="avatar-preview" src="{avatar_url(current_user)}" class="avatar" style="cursor:default" onclick="openAvatar(this.src)">
      </div>
      <label>اللقب (1-4 كلمات)</label>
      <input name="nickname" value="{current_user.nickname or ''}" maxlength="64" required>
      <label>نبذة عنك</label>
      <textarea name="bio" maxlength="200">{current_user.bio or ''}</textarea>
      <label>صورة البروفايل</label>
      <input type="file" name="avatar" accept="image/*" onchange="previewAvatar(this)">
      {delete_btn}
      <input type="hidden" name="remove_avatar" id="remove_avatar_flag" value="0">
      <button type="submit" style="margin-top:14px">حفظ</button>
    </form>
    <a class="link-center" href="{url_for('profile_me')}">رجوع</a>
    </div>
    <script>
    function previewAvatar(input){{var f=input.files[0];if(!f)return;var u=URL.createObjectURL(f);
    document.getElementById('avatar-preview').src=u;}}
    function requestDeleteAvatar(){{if(confirm('حذف صورة البروفايل؟')){{
    document.getElementById('remove_avatar_flag').value='1';
    document.getElementById('edit-form').submit();}}}}
    </script>""", title="تعديل")


@app.route("/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old = request.form.get("old", "")
        new = request.form.get("new", "")
        confirm = request.form.get("confirm", "")
        if not check_password_hash(current_user.password_hash, old):
            flash("كلمة السر الحالية خاطئة.", "error")
            return redirect(url_for("change_password"))
        if len(new) < 8 or new != confirm:
            flash("تحقق من كلمة السر الجديدة.", "error")
            return redirect(url_for("change_password"))
        current_user.password_hash = generate_password_hash(new)
        db.session.commit()
        flash("تم تغيير كلمة المرور.", "success")
        return redirect(url_for("profile_me"))
    return render_page(FLASH_BLOCK + """
    <div class="card"><h2>تغيير كلمة المرور</h2>
    <form method="POST">
    <label>كلمة السر الحالية</label>
    <div class="pw-wrap"><input name="old" id="cp1" type="password" required>
    <button type="button" class="pw-toggle" onclick="togglePw('cp1')">👁</button></div>
    <label>كلمة السر الجديدة</label>
    <div class="pw-wrap"><input name="new" id="cp2" type="password" required>
    <button type="button" class="pw-toggle" onclick="togglePw('cp2')">👁</button></div>
    <label>تأكيد كلمة السر الجديدة</label>
    <div class="pw-wrap"><input name="confirm" id="cp3" type="password" required>
    <button type="button" class="pw-toggle" onclick="togglePw('cp3')">👁</button></div>
    <button type="submit">تغيير</button></form>
    <a class="link-center" href="{{ url_for('profile_me') }}">رجوع</a></div>""", title="كلمة المرور")


@app.route("/recovery-code", methods=["GET", "POST"])
@login_required
def show_recovery_code():
    if request.method == "POST":
        password = request.form.get("password", "")
        if not check_password_hash(current_user.password_hash, password):
            flash("كلمة السر خاطئة.", "error")
            return redirect(url_for("show_recovery_code"))
        new_code = gen_recovery_code()
        while User.query.filter_by(recovery_hash=hash_recovery_code(new_code)).first():
            new_code = gen_recovery_code()
        current_user.recovery_hash = hash_recovery_code(new_code)
        db.session.commit()
        return render_page("""
        <div class="card center"><h2>🔐 كود الاستعادة الجديد</h2>
        <div class="recovery-box"><div class="code">{{ formatted }}</div>
        <button class="copy-btn" onclick="copyText('{{ code }}',this)">نسخ الكود</button></div>
        <a class="btn btn-primary" href="{{ url_for('profile_me') }}">رجوع للبروفايل</a>
        </div>""", title="كود جديد", formatted=format_code(new_code), code=new_code)
    return render_page(FLASH_BLOCK + """
    <div class="card"><h2>🔐 عرض كود الاستعادة</h2>
    <div class="privacy-note">⚠️ سيتم توليد كود جديد وإبطال القديم.</div>
    <form method="POST"><label>كلمة السر</label>
    <div class="pw-wrap"><input name="password" id="rcpw" type="password" required>
    <button type="button" class="pw-toggle" onclick="togglePw('rcpw')">👁</button></div>
    <button type="submit">توليد كود جديد</button></form>
    <a class="link-center" href="{{ url_for('profile_me') }}">رجوع</a></div>""", title="كود الاستعادة")


@app.route("/devices")
@login_required
def devices_list():
    devices = Device.query.filter_by(user_id=current_user.id).order_by(Device.created_at.desc()).all()
    rows = ""
    for d in devices:
        ua = d.user_agent or "غير معروف"
        created = fmt_sd(d.created_at)
        rows += f"""<div class="device-row">
        <div style="flex:1"><div><b>جهاز</b> — {created} (SD)</div>
        <div class="ua">{ua}</div></div>
        <a class="btn btn-sm btn-danger" href="{url_for('device_remove', did=d.id)}"
           onclick="return confirm('إزالة هذا الجهاز؟')">إزالة</a></div>"""
    if not rows:
        rows = '<p class="empty">لا أجهزة مسجلة.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>الأجهزة المتصلة</h2>{rows}
    <a class="link-center" href="{url_for('profile_me')}">رجوع</a></div>""", title="الأجهزة")


@app.route("/device/remove/<int:did>")
@login_required
def device_remove(did):
    d = db.session.get(Device, did)
    if not d or d.user_id != current_user.id:
        abort(404)
    db.session.delete(d)
    db.session.commit()
    flash("تم إزالة الجهاز.", "success")
    return redirect(url_for("devices_list"))


# ═══════════════════ FRIENDS ═══════════════════
@app.route("/friends")
@login_required
def friends_list():
    friends = get_friends(current_user.id)
    incoming = Friendship.query.filter_by(addressee_id=current_user.id, status="pending").count()
    rows = ""
    for f in friends:
        online = '<span class="online-dot"></span>' if f.is_online else ''
        rows += f"""<div class="list-item">
        <img class="avatar-sm" src="{avatar_url(f)}" onclick="openAvatar('{avatar_url(f)}')">
        <a href="{url_for('view_profile', username=f.username)}" style="flex:1;text-decoration:none;color:inherit">
          <div class="li-name">{online}{f.short_name}</div>
          <div class="li-sub">@{f.username} · ID: {f.public_id}</div></a>
        <div class="li-actions">
          {copy_btn_html(f.username, "يوزر", small=True)}
          {copy_btn_html(f.public_id, "ID", small=True)}
          <a class="btn btn-sm btn-primary" href="{url_for('chat_with', username=f.username)}">دردشة</a>
          <a class="btn btn-sm btn-danger" href="{url_for('unfriend_user', username=f.username)}"
             onclick="return confirm('حذف هذا الصديق؟')">✂</a>
        </div></div>"""
    if not rows:
        rows = '<p class="empty">لا أصدقاء بعد.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>أصدقائي ({len(friends)})</h2>
    <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
      <a class="btn btn-sm" href="{url_for('friends_requests')}">طلبات الصداقة {f'({incoming})' if incoming else ''}</a>
      <a class="btn btn-sm btn-primary" href="{url_for('discover')}">👥 اكتشف</a>
      <a class="btn btn-sm" href="{url_for('search')}">🔍 بحث</a>
    </div>{rows}</div>""", title="الأصدقاء")


@app.route("/friends/requests")
@login_required
def friends_requests():
    incoming = Friendship.query.filter_by(addressee_id=current_user.id, status="pending").all()
    outgoing = Friendship.query.filter_by(requester_id=current_user.id, status="pending").all()
    inc = ""
    for r in incoming:
        u = r.requester
        if u.id in get_blocked_ids(current_user.id) or u.id in get_blocked_by_ids(current_user.id):
            continue
        inc += f"""<div class="list-item">
        <img class="avatar-sm" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
        <div style="flex:1"><div class="li-name">{u.short_name}</div>
        <div class="li-sub">@{u.username} · ID: {u.public_id}</div></div>
        <div class="li-actions">
          {copy_btn_html(u.username, "يوزر", small=True)}
          {copy_btn_html(u.public_id, "ID", small=True)}
          <a class="btn btn-sm btn-primary" href="{url_for('friend_accept', fid=r.id)}">قبول</a>
          <a class="btn btn-sm btn-danger" href="{url_for('friend_reject', fid=r.id)}">رفض</a>
        </div></div>"""
    if not inc:
        inc = '<p class="empty">لا طلبات واردة.</p>'
    out = ""
    for r in outgoing:
        u = r.addressee
        out += f"""<div class="list-item">
        <img class="avatar-sm" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
        <div style="flex:1"><div class="li-name">{u.short_name}</div>
        <div class="li-sub">@{u.username} · ID: {u.public_id} · بانتظار الرد</div></div>
        <div class="li-actions">
          {copy_btn_html(u.username, "يوزر", small=True)}
          {copy_btn_html(u.public_id, "ID", small=True)}
          <a class="btn btn-sm btn-danger" href="{url_for('friend_reject', fid=r.id)}">إلغاء</a>
        </div></div>"""
    if not out:
        out = '<p class="empty">لا طلبات مرسلة.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>طلبات واردة</h2>{inc}</div>
    <div class="card"><h2>طلبات مرسلة</h2>{out}</div>""", title="طلبات الصداقة")


@app.route("/friend/request/<username>")
@login_required
def friend_request(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not target:
        flash("المستخدم غير موجود.", "error")
        return redirect(url_for("discover"))
    if target.id == current_user.id:
        flash("لا يمكنك إضافة نفسك.", "error")
        return redirect(url_for("profile_me"))
    if target.is_banned or target.under_review:
        flash("لا يمكن إضافة هذا المستخدم.", "error")
        return redirect(url_for("discover"))
    if is_blocked_between(current_user.id, target.id):
        flash("لا يمكن إرسال طلب صداقة (يوجد حظر).", "error")
        return redirect(url_for("view_profile", username=target.username))
    state, _ = friendship_status(current_user.id, target.id)
    if state != "none":
        flash("الطلب موجود بالفعل.", "error")
        return redirect(url_for("view_profile", username=target.username))
    db.session.add(Friendship(requester_id=current_user.id, addressee_id=target.id, status="pending"))
    db.session.commit()
    flash(f"تم إرسال طلب صداقة إلى @{target.username}.", "success")
    return redirect(request.referrer or url_for("view_profile", username=target.username))


@app.route("/friend/accept/<int:fid>")
@login_required
def friend_accept(fid):
    r = db.session.get(Friendship, fid)
    if not r or r.addressee_id != current_user.id:
        abort(404)
    r.status = "accepted"
    db.session.commit()
    flash("تم قبول الصداقة.", "success")
    return redirect(url_for("friends_requests"))


@app.route("/friend/reject/<int:fid>")
@login_required
def friend_reject(fid):
    r = db.session.get(Friendship, fid)
    if not r or (r.addressee_id != current_user.id and r.requester_id != current_user.id):
        abort(404)
    db.session.delete(r)
    db.session.commit()
    flash("تم الحذف.", "success")
    return redirect(url_for("friends_requests"))


@app.route("/friend/remove/<username>")
@login_required
def unfriend_user(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not target:
        flash("المستخدم غير موجود.", "error")
        return redirect(url_for("friends_list"))
    r = Friendship.query.filter(Friendship.status == "accepted", or_(
        and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == target.id),
        and_(Friendship.requester_id == target.id, Friendship.addressee_id == current_user.id))).first()
    if not r:
        flash("لستما صديقين.", "error")
        return redirect(url_for("friends_list"))
    db.session.delete(r)
    ArchivedChat.query.filter(or_(
        and_(ArchivedChat.user_id == current_user.id, ArchivedChat.peer_id == target.id),
        and_(ArchivedChat.user_id == target.id, ArchivedChat.peer_id == current_user.id)
    )).delete(synchronize_session=False)
    db.session.commit()
    flash(f"تم حذف @{target.username} من الأصدقاء.", "success")
    return redirect(request.referrer or url_for("friends_list"))


# ═══════════════════ BLOCK ═══════════════════
@app.route("/block/<username>")
@login_required
def block_user(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not target or target.id == current_user.id:
        flash("لا يمكن حظر هذا المستخدم.", "error")
        return redirect(url_for("search"))
    existing = Block.query.filter_by(blocker_id=current_user.id, blocked_id=target.id).first()
    if existing:
        flash("هذا المستخدم محظور بالفعل.", "error")
        return redirect(url_for("view_profile", username=target.username))
    db.session.add(Block(blocker_id=current_user.id, blocked_id=target.id))
    Friendship.query.filter(or_(
        and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == target.id),
        and_(Friendship.requester_id == target.id, Friendship.addressee_id == current_user.id)
    )).delete(synchronize_session=False)
    db.session.commit()
    flash(f"تم حظر @{target.username}.", "success")
    return redirect(url_for("view_profile", username=target.username))


@app.route("/unblock/<username>")
@login_required
def unblock_user(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not target:
        flash("المستخدم غير موجود.", "error")
        return redirect(url_for("blocked_list"))
    b = Block.query.filter_by(blocker_id=current_user.id, blocked_id=target.id).first()
    if not b:
        flash("هذا المستخدم غير محظور.", "error")
        return redirect(url_for("blocked_list"))
    db.session.delete(b)
    db.session.commit()
    flash(f"تم إلغاء حظر @{target.username}.", "success")
    return redirect(request.referrer or url_for("blocked_list"))


@app.route("/blocked")
@login_required
def blocked_list():
    rows = Block.query.filter_by(blocker_id=current_user.id).order_by(Block.created_at.desc()).all()
    html = ""
    for b in rows:
        u = b.blocked
        html += f"""<div class="list-item">
        <img class="avatar-sm" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
        <a href="{url_for('view_profile', username=u.username)}" style="flex:1;text-decoration:none;color:inherit">
          <div class="li-name">{u.short_name}</div>
          <div class="li-sub">@{u.username} · ID: {u.public_id} · حظر في {fmt_sd(b.created_at, '%Y-%m-%d')}</div></a>
        <div class="li-actions">
          {copy_btn_html(u.username, "يوزر", small=True)}
          {copy_btn_html(u.public_id, "ID", small=True)}
          <a class="btn btn-sm btn-primary" href="{url_for('unblock_user', username=u.username)}"
             onclick="return confirm('إلغاء حظر هذا المستخدم؟')">✅ إلغاء</a>
        </div></div>"""
    if not html:
        html = '<p class="empty">لا مستخدمين محظورين.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>🚫 المحظورون ({len(rows)})</h2>{html}
    <a class="link-center" href="{url_for('profile_me')}">رجوع</a></div>""", title="المحظورون")


# ═══════════════════ ARCHIVE ═══════════════════
@app.route("/archive/<username>", methods=["POST"])
@login_required
def archive_chat(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not target or target.id == current_user.id:
        flash("لا يمكن أرشفة هذه المحادثة.", "error")
        return redirect(url_for("chats"))
    existing = ArchivedChat.query.filter_by(user_id=current_user.id, peer_id=target.id).first()
    if existing:
        flash("المحادثة مؤرشفة بالفعل.", "error")
        return redirect(request.referrer or url_for("chats"))
    db.session.add(ArchivedChat(user_id=current_user.id, peer_id=target.id))
    db.session.commit()
    flash(f"تم أرشفة محادثة @{target.username}.", "success")
    return redirect(request.referrer or url_for("chats"))


@app.route("/unarchive/<username>", methods=["POST"])
@login_required
def unarchive_chat(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not target:
        flash("المستخدم غير موجود.", "error")
        return redirect(url_for("archived_list"))
    a = ArchivedChat.query.filter_by(user_id=current_user.id, peer_id=target.id).first()
    if not a:
        flash("المحادثة غير مؤرشفة.", "error")
        return redirect(url_for("archived_list"))
    db.session.delete(a)
    db.session.commit()
    flash(f"تم إلغاء أرشفة محادثة @{target.username}.", "success")
    return redirect(request.referrer or url_for("archived_list"))


@app.route("/archived")
@login_required
def archived_list():
    rows = ArchivedChat.query.filter_by(user_id=current_user.id).order_by(ArchivedChat.created_at.desc()).all()
    html = ""
    for a in rows:
        u = a.peer
        html += f"""<div class="list-item">
        <img class="avatar-sm" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
        <a href="{url_for('chat_with', username=u.username)}" style="flex:1;text-decoration:none;color:inherit">
          <div class="li-name">📦 {u.short_name}</div>
          <div class="li-sub">@{u.username} · ID: {u.public_id}</div></a>
        <div class="li-actions">
          {copy_btn_html(u.username, "يوزر", small=True)}
          {copy_btn_html(u.public_id, "ID", small=True)}
          <a class="btn btn-sm btn-primary" href="{url_for('chat_with', username=u.username)}">فتح</a>
          <a class="btn btn-sm btn-danger" href="{url_for('unarchive_chat', username=u.username)}">↩</a>
        </div></div>"""
    if not html:
        html = '<p class="empty">الأرشيف فارغ.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>📦 المحادثات المؤرشفة ({len(rows)})</h2>{html}
    <a class="link-center" href="{url_for('chats')}">← رجوع للدردشات</a></div>""", title="الأرشيف")


# ═══════════════════ DELETE ACCOUNT ═══════════════════
@app.route("/account/delete", methods=["GET", "POST"])
@login_required
def delete_account():
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_text = request.form.get("confirm_text", "").strip()
        if not check_password_hash(current_user.password_hash, password):
            flash("كلمة السر خاطئة.", "error")
            return redirect(url_for("delete_account"))
        if confirm_text != "DELETE":
            flash("اكتب كلمة DELETE للتأكيد.", "error")
            return redirect(url_for("delete_account"))
        uid = current_user.id
        try:
            if current_user.avatar:
                try:
                    p = os.path.join(app.config["AVATAR_FOLDER"], current_user.avatar)
                    if os.path.exists(p): os.remove(p)
                except OSError: pass
            for s in Status.query.filter_by(user_id=uid).all():
                StatusView.query.filter_by(status_id=s.id).delete(synchronize_session=False)
                if s.media:
                    try:
                        p = os.path.join(app.config["STATUS_FOLDER"], s.media)
                        if os.path.exists(p): os.remove(p)
                    except OSError: pass
                db.session.delete(s)
            for m in ChatMessage.query.filter(or_(ChatMessage.sender_id == uid, ChatMessage.receiver_id == uid)).all():
                if m.media:
                    try:
                        p = os.path.join(app.config["CHAT_FOLDER"], m.media)
                        if os.path.exists(p): os.remove(p)
                    except OSError: pass
                db.session.delete(m)
            Message.query.filter_by(receiver_id=uid).delete(synchronize_session=False)
            Friendship.query.filter(or_(Friendship.requester_id == uid, Friendship.addressee_id == uid)).delete(synchronize_session=False)
            Block.query.filter(or_(Block.blocker_id == uid, Block.blocked_id == uid)).delete(synchronize_session=False)
            ArchivedChat.query.filter(or_(ArchivedChat.user_id == uid, ArchivedChat.peer_id == uid)).delete(synchronize_session=False)
            SavedChat.query.filter(or_(SavedChat.user_id == uid, SavedChat.peer_id == uid)).delete(synchronize_session=False)
            Device.query.filter_by(user_id=uid).delete(synchronize_session=False)
            Report.query.filter(or_(Report.reporter_id == uid, Report.target_id == uid)).delete(synchronize_session=False)
            ChatReport.query.filter(or_(ChatReport.reporter_id == uid, ChatReport.target_id == uid)).delete(synchronize_session=False)
            StatusView.query.filter_by(viewer_id=uid).delete(synchronize_session=False)
            GroupMember.query.filter_by(user_id=uid).delete(synchronize_session=False)
            GroupMessage.query.filter_by(sender_id=uid).delete(synchronize_session=False)
            GroupReport.query.filter_by(reporter_id=uid).delete(synchronize_session=False)
            GroupJoinRequest.query.filter_by(user_id=uid).delete(synchronize_session=False)
            TypingIndicator.query.filter(or_(TypingIndicator.user_id == uid, TypingIndicator.peer_id == uid)).delete(synchronize_session=False)
            for g in Group.query.filter_by(owner_id=uid).all():
                for m in GroupMessage.query.filter_by(group_id=g.id).all():
                    if m.media:
                        try: os.remove(os.path.join(app.config["GROUP_FOLDER"], m.media))
                        except OSError: pass
                    db.session.delete(m)
                if g.avatar:
                    try: os.remove(os.path.join(app.config["GROUP_FOLDER"], g.avatar))
                    except OSError: pass
                GroupMember.query.filter_by(group_id=g.id).delete(synchronize_session=False)
                GroupReport.query.filter_by(group_id=g.id).delete(synchronize_session=False)
                GroupJoinRequest.query.filter_by(group_id=g.id).delete(synchronize_session=False)
                db.session.delete(g)
            user = db.session.get(User, uid)
            db.session.delete(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"حدث خطأ: {e}", "error")
            return redirect(url_for("delete_account"))
        logout_user()
        resp = make_response(redirect(url_for("login")))
        resp.delete_cookie("device_token")
        flash("تم مسح حسابك بالكامل.", "success")
        return resp
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + """
    <div class="card"><h2 style="color:#991b1b">🗑 مسح الحساب نهائيًا</h2>
    <div class="danger-zone"><h3>⚠️ تحذير خطير</h3>
    <p style="font-size:13px;color:#7f1d1d;line-height:1.7">
      سيتم حذف <b>كل شيء</b> نهائيًا.</p></div>
    <form method="POST" style="margin-top:14px">
      <label>كلمة السر</label>
      <div class="pw-wrap"><input name="password" id="delpw" type="password" required>
      <button type="button" class="pw-toggle" onclick="togglePw('delpw')">👁</button></div>
      <label>اكتب كلمة <b style="color:#dc2626">DELETE</b> للتأكيد</label>
      <input name="confirm_text" placeholder="DELETE" required style="text-align:center;font-weight:800;color:#dc2626">
      <button type="submit" style="background:#dc2626" onclick="return confirm('هل أنت متأكد 100%؟ لا يمكن التراجع!')">
        🗑 مسح الحساب نهائيًا</button>
    </form>
    <a class="link-center" href="{{ url_for('profile_me') }}">← إلغاء والرجوع</a></div>""", title="مسح الحساب")


# ═══════════════════ DISCOVER + SEARCH ═══════════════════
@app.route("/discover")
@login_required
def discover():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 30
    excluded = get_blocked_ids(current_user.id) | get_blocked_by_ids(current_user.id)
    query = User.query.filter(User.is_banned == False, User.under_review == False, User.id != current_user.id)
    if excluded:
        query = query.filter(~User.id.in_(excluded))
    if q:
        ql = q.lower().lstrip("@")
        query = query.filter(or_(User.username.ilike(f"%{ql}%"), User.public_id.ilike(f"%{ql}%")))
    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    my_friends = get_friend_ids(current_user.id)
    pending_out = {r.addressee_id for r in Friendship.query.filter_by(requester_id=current_user.id, status="pending").all()}
    pending_in = {r.requester_id for r in Friendship.query.filter_by(addressee_id=current_user.id, status="pending").all()}
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
        online = '<span class="online-dot"></span>' if u.is_online else ''
        rows += f"""<div class="list-item" style="cursor:default">
          <a href="{url_for('view_profile', username=u.username)}" style="display:flex;align-items:center;gap:10px;flex:1;text-decoration:none;color:inherit;min-width:0">
            <img class="avatar-sm" src="{avatar_url(u)}" onclick="event.preventDefault();event.stopPropagation();openAvatar('{avatar_url(u)}')">
            <div style="flex:1;min-width:0"><div class="li-name">{online}{u.short_name}</div>
            <div class="li-sub">@{u.username} · ID: {u.public_id}</div></div></a>
          <div class="li-actions">
            {copy_btn_html(u.username, "يوزر", small=True)}
            {copy_btn_html(u.public_id, "ID", small=True)}
            {action}</div></div>"""
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
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>👥 اكتشف الأشخاص ({pagination.total})</h2>
    <form method="GET" style="display:flex;gap:8px;margin:10px 0">
      <input name="q" value="{q}" placeholder="ابحث بيوزر أو ID" style="flex:1;margin:0">
      <button type="submit" style="width:auto;padding:12px 20px;margin:0">بحث</button></form>
    {rows}{nav}</div>""", title="اكتشف الأشخاص")


@app.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    users_results = []
    if q:
        ql = q.lower().lstrip("@")
        excluded = get_blocked_ids(current_user.id) | get_blocked_by_ids(current_user.id)
        query = User.query.filter(or_(User.username.ilike(f"%{ql}%"), User.public_id.ilike(f"%{ql}%")),
                                  User.is_banned == False, User.under_review == False, User.id != current_user.id)
        if excluded:
            query = query.filter(~User.id.in_(excluded))
        users_results = query.limit(50).all()
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
        online = '<span class="online-dot"></span>' if u.is_online else ''
        users_block += f"""<div class="list-item" style="cursor:default">
        <img class="avatar-sm" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
        <a href="{url_for('view_profile', username=u.username)}" style="flex:1;text-decoration:none;color:inherit;min-width:0">
        <div class="li-name">{online}{u.short_name}</div>
        <div class="li-sub">@{u.username} · ID: {u.public_id}</div></a>
        <div class="li-actions">
          {copy_btn_html(u.username, "يوزر", small=True)}
          {copy_btn_html(u.public_id, "ID", small=True)}
          {action}
        </div></div>"""
    if not users_block and q:
        users_block = '<p class="empty">لا نتائج.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>🔍 البحث</h2>
    <form method="GET" style="display:flex;gap:8px">
      <input name="q" value="{q}" placeholder="username أو 12345678" style="flex:1;margin:0" autofocus>
      <button type="submit" style="width:auto;padding:12px 20px;margin:0">بحث</button></form>
    <a class="link-center" href="{url_for('discover')}">👥 أو تصفح كل الأشخاص</a></div>
    {('<div class="card"><h2>النتائج (' + str(len(users_results)) + ')</h2>' + users_block + '</div>') if q else ''}
    """, title="بحث")


# ═══════════════════════════════════════════════════════════════
# STATUSES
# ═══════════════════════════════════════════════════════════════
@app.route("/status/new", methods=["GET", "POST"])
@login_required
def post_status():
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        caption = request.form.get("caption", "").strip()
        show_viewers = request.form.get("show_viewers") == "1"
        privacy = request.form.get("privacy", "public").strip().lower()
        if privacy not in ("public", "friends"):
            privacy = "public"
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
        db.session.add(Status(user_id=current_user.id, text=text[:300], caption=caption[:300],
                              media=media_fn, media_type=media_type, privacy=privacy,
                              show_viewers=show_viewers))
        db.session.commit()
        label = "عامة 🌍" if privacy == "public" else "خاصة (للأصدقاء) 👥"
        flash(f"تم نشر الحالة ({label}).", "success")
        return redirect(url_for("feed"))
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + """
    <div class="card"><h2>📸 حالة جديدة</h2>
    <div class="privacy-note" style="background:#dbeafe;border-color:#93c5fd;color:#1e40af">
      اختر خصوصية الحالة قبل النشر.</div>
    <form method="POST" enctype="multipart/form-data">
      <label>👁 من يرى الحالة؟</label>
      <div class="privacy-choice">
        <label class="privacy-opt">
          <input type="radio" name="privacy" value="public" checked>
          <div class="pbox">
            <span class="picon">🌍</span>
            <span class="ptitle">عامة</span>
            <span class="psub">يراها جميع المستخدمين</span>
          </div>
        </label>
        <label class="privacy-opt">
          <input type="radio" name="privacy" value="friends">
          <div class="pbox">
            <span class="picon">👥</span>
            <span class="ptitle">خاصة</span>
            <span class="psub">يراها أصدقاؤك فقط</span>
          </div>
        </label>
      </div>
      <label>النص (اختياري)</label>
      <textarea name="text" maxlength="300" placeholder="اكتب شيئًا..."></textarea>
      <label>الوسائط (صورة أو فيديو)</label>
      <input type="file" name="media" accept="image/*,video/*" onchange="previewStatusMedia(this)">
      <div id="status-preview"></div>
      <label>وصف الوسائط (اختياري)</label>
      <input name="caption" maxlength="300" placeholder="وصف مختصر...">
      <label class="switch-row" style="margin-top:14px">
        <span>👁 إظهار المشاهدين لصاحب الحالة</span>
        <input type="checkbox" name="show_viewers" value="1"><span class="switch"></span></label>
      <button type="submit">نشر الحالة</button></form>
    <a class="link-center" href="{{ url_for('feed') }}">رجوع</a></div>""", title="حالة جديدة")


@app.route("/status/<int:sid>/edit", methods=["GET", "POST"])
@login_required
def edit_status(sid):
    s = db.session.get(Status, sid)
    if not s or s.user_id != current_user.id:
        abort(403)
    if request.method == "POST":
        s.text = request.form.get("text", "").strip()[:300]
        s.caption = request.form.get("caption", "").strip()[:300]
        s.show_viewers = request.form.get("show_viewers") == "1"
        new_privacy = request.form.get("privacy", "public").strip().lower()
        if new_privacy in ("public", "friends"):
            s.privacy = new_privacy
        db.session.commit()
        flash("تم تعديل الحالة.", "success")
        return redirect(url_for("feed"))
    checked_sv = "checked" if s.show_viewers else ""
    pub_checked = "checked" if s.privacy == "public" else ""
    fr_checked = "checked" if s.privacy == "friends" else ""
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>✏️ تعديل الحالة</h2>
    <form method="POST">
      <label>👁 من يرى الحالة؟</label>
      <div class="privacy-choice">
        <label class="privacy-opt">
          <input type="radio" name="privacy" value="public" {pub_checked}>
          <div class="pbox">
            <span class="picon">🌍</span>
            <span class="ptitle">عامة</span>
            <span class="psub">يراها جميع المستخدمين</span>
          </div>
        </label>
        <label class="privacy-opt">
          <input type="radio" name="privacy" value="friends" {fr_checked}>
          <div class="pbox">
            <span class="picon">👥</span>
            <span class="ptitle">خاصة</span>
            <span class="psub">يراها أصدقاؤك فقط</span>
          </div>
        </label>
      </div>
      <label>النص</label><textarea name="text" maxlength="300">{s.text}</textarea>
      <label>الوصف</label><input name="caption" maxlength="300" value="{s.caption}">
      <label class="switch-row" style="margin-top:14px">
        <span>👁 إظهار المشاهدين لصاحب الحالة</span>
        <input type="checkbox" name="show_viewers" value="1" {checked_sv}><span class="switch"></span></label>
      <button type="submit">حفظ</button></form>
    <a class="link-center" href="{url_for('feed')}">رجوع</a></div>""", title="تعديل حالة")


@app.route("/status/<int:sid>/delete")
@login_required
def delete_status(sid):
    s = db.session.get(Status, sid)
    if not s or s.user_id != current_user.id:
        abort(403)
    if s.media:
        try: os.remove(os.path.join(app.config["STATUS_FOLDER"], s.media))
        except OSError: pass
    StatusView.query.filter_by(status_id=s.id).delete(synchronize_session=False)
    db.session.delete(s)
    db.session.commit()
    flash("تم حذف الحالة.", "success")
    return redirect(url_for("feed"))


@app.route("/status/<int:sid>/viewers")
@login_required
def status_viewers(sid):
    s = db.session.get(Status, sid)
    if not s or s.user_id != current_user.id:
        abort(403)
    if not s.show_viewers:
        flash("لم تفعّل خيار عرض المشاهدين.", "error")
        return redirect(url_for("feed"))
    views = StatusView.query.filter_by(status_id=sid).order_by(StatusView.viewed_at.desc()).all()
    rows = ""
    for v in views:
        u = v.viewer
        rows += f"""<div class="list-item" style="cursor:default">
        <img class="avatar-sm" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
        <a href="{url_for('view_profile', username=u.username)}" style="flex:1;text-decoration:none;color:inherit">
          <div class="li-name">{u.short_name}</div>
          <div class="li-sub">@{u.username} · ID: {u.public_id} · {fmt_sd(v.viewed_at, '%H:%M')}</div></a>
        <div class="li-actions">
          {copy_btn_html(u.username, "يوزر", small=True)}
          {copy_btn_html(u.public_id, "ID", small=True)}
        </div></div>"""
    if not rows:
        rows = '<p class="empty">لا أحد شاهد حالتك بعد.</p>'
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>👁 مشاهدو الحالة ({len(views)})</h2>{rows}
    <a class="link-center" href="{url_for('feed')}">← رجوع للحالات</a></div>""", title="مشاهدو الحالة")


@app.route("/feed")
@login_required
def feed():
    cleanup_old_statuses()
    cutoff = now_utc_naive() - timedelta(hours=24)
    excluded = get_blocked_ids(current_user.id) | get_blocked_by_ids(current_user.id)
    my_friend_ids = get_friend_ids(current_user.id)
    all_statuses = Status.query.filter(Status.created_at >= cutoff).order_by(Status.created_at.desc()).all()
    visible = []
    for s in all_statuses:
        if s.user_id in excluded:
            continue
        if s.user_id == current_user.id:
            visible.append(s)
        elif s.privacy == "public":
            visible.append(s)
        elif s.privacy == "friends" and s.user_id in my_friend_ids:
            visible.append(s)
    statuses = visible
    by_user = {}
    for s in statuses:
        by_user.setdefault(s.user_id, []).append(s)
    for s in statuses:
        if s.user_id == current_user.id:
            continue
        if s.show_viewers:
            exists = StatusView.query.filter_by(status_id=s.id, viewer_id=current_user.id).first()
            if not exists:
                db.session.add(StatusView(status_id=s.id, viewer_id=current_user.id))
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    status_strip = ""
    for uid, items in by_user.items():
        u = items[0].user
        av = avatar_url(u)
        count = len(items)
        is_private_group = any(i.privacy == "friends" for i in items)
        tag = '<span class="vid-tag">▶</span>' if any(i.media_type == "video" for i in items) else ""
        priv_tag = '<span class="priv-tag">👥</span>' if is_private_group else ""
        count_badge = f'<span class="count-badge">{count}</span>' if count > 1 else ""
        first_id = items[0].id
        item_cls = "status-item private" if is_private_group else "status-item"
        status_strip += f"""<a class="{item_cls}" href="javascript:void(0)" onclick="openStatus({first_id})">
          <span class="ring">{count_badge}<img src="{av}">{tag}{priv_tag}</span>
          <div class="sname">{u.short_name}</div></a>"""
    status_viewers_html = ""
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
                viewers_btn = ""
                if s.show_viewers:
                    vcount = StatusView.query.filter_by(status_id=s.id).count()
                    viewers_btn = f'<a class="sbtn viewers" href="{url_for("status_viewers", sid=s.id)}">👁 {vcount}</a>'
                owner_actions = f"""<div class="status-owner-actions">
                  {viewers_btn}
                  <a class="sbtn edit" href="{url_for('edit_status', sid=s.id)}">✏️</a>
                  <a class="sbtn del" href="{url_for('delete_status', sid=s.id)}" onclick="return confirm('حذف الحالة؟')">🗑</a>
                </div>"""
            bottom_actions = ""
            if s.user_id != current_user.id:
                state, _ = friendship_status(current_user.id, s.user_id)
                if state == "friends":
                    bottom_actions = f"""<div class="status-actions-bottom">
                      <a class="action-btn chat" href="{url_for('chat_with', username=s.user.username)}">◈ دردشة مباشرة</a>
                      <a class="action-btn profile" href="{url_for('view_profile', username=s.user.username)}">👤 البروفايل</a></div>"""
                elif state == "none":
                    bottom_actions = f"""<div class="status-actions-bottom">
                      <a class="action-btn add" href="{url_for('friend_request', username=s.user.username)}">➕ إضافة صديق</a>
                      <a class="action-btn profile" href="{url_for('view_profile', username=s.user.username)}">👤 البروفايل</a></div>"""
                elif state == "pending_in":
                    bottom_actions = f"""<div class="status-actions-bottom">
                      <a class="action-btn add" href="{url_for('friends_requests')}">✔ اقبل الصداقة</a>
                      <a class="action-btn profile" href="{url_for('view_profile', username=s.user.username)}">👤 البروفايل</a></div>"""
                else:
                    bottom_actions = f"""<div class="status-actions-bottom">
                      <a class="action-btn profile" href="{url_for('view_profile', username=s.user.username)}">👤 البروفايل</a></div>"""
            nav_html = ""
            if len(items) > 1:
                prev_btn = ""
                next_btn = ""
                if idx > 0:
                    prev_btn = f'<button class="nav-btn" onclick="event.stopPropagation();closeStatus({s.id});openStatus({items[idx-1].id})">◀ السابق</button>'
                if idx < len(items) - 1:
                    next_btn = f'<button class="nav-btn" onclick="event.stopPropagation();closeStatus({s.id});openStatus({items[idx+1].id})">التالي ▶</button>'
                nav_html = f"""<div class="status-nav">
                  {prev_btn}<span class="counter">{idx+1} / {len(items)}</span>{next_btn}</div>"""
            privacy_label = "🌍 عامة" if s.privacy == "public" else "👥 خاصة (أصدقاء)"
            status_viewers_html += f"""<div class="status-view" id="sv-{s.id}" style="display:none">
              {owner_actions}
              <button class="close" onclick="closeStatus({s.id})">✕</button>
              {media_html}
              {f'<div class="stext">{s.text}</div>' if s.text else ''}
              {f'<div class="scaption">{s.caption}</div>' if s.caption else ''}
              <div class="smeta">{s.user.short_name} · {fmt_sd(s.created_at)} · {privacy_label}</div>
              {bottom_actions}
              {nav_html}
            </div>"""
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card">
      <h2 style="text-align:right;font-size:15px">الحالات (24 ساعة)</h2>
      <div style="font-size:11px;color:#6b7280;margin-bottom:8px">
        🌍 عامة = للجميع &nbsp;·&nbsp; 👥 خاصة = للأصدقاء فقط
      </div>
      <div class="status-strip">
        <a class="status-item" href="{url_for('post_status')}">
          <span class="ring" style="background:#e5e7eb"><img src="{avatar_url(current_user)}" style="opacity:.5"></span>
          <div class="sname">+ أضف</div></a>
        {status_strip}
      </div>
      {('<p class="empty" style="padding:10px 0">لا حالات حديثة.</p>') if not status_strip else ''}
    </div>
    {status_viewers_html}""", title="الرئيسية")


# ═══════════════════════════════════════════════════════════════
# CHATS — الفردية
# ═══════════════════════════════════════════════════════════════
@app.route("/chats")
@login_required
def chats():
    badge = badge_html()
    friends = get_friends(current_user.id)
    archived = ArchivedChat.query.filter_by(user_id=current_user.id).all()
    archived_ids = {a.peer_id for a in archived}
    # ترتيب: المثبت أولاً ثم الأحدث
    items = []
    for f in friends:
        if f.id in archived_ids:
            continue
        last_msg = ChatMessage.query.filter(or_(
            and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == f.id),
            and_(ChatMessage.sender_id == f.id, ChatMessage.receiver_id == current_user.id)
        )).order_by(ChatMessage.created_at.desc()).first()
        unread = ChatMessage.query.filter_by(sender_id=f.id, receiver_id=current_user.id, is_read=False).count()
        saved = SavedChat.query.filter_by(user_id=current_user.id, peer_id=f.id).first()
        pinned = bool(saved and saved.pinned)
        muted = bool(saved and saved.muted)
        items.append((pinned, last_msg.created_at if last_msg else f.created_at, f, last_msg, unread, muted))
    items.sort(key=lambda x: (not x[0], -(x[1].timestamp() if x[1] else 0)))
    rows = ""
    for pinned, _, f, last_msg, unread, muted in items:
        preview = "ابدأ الدردشة"
        time_str = ""
        if last_msg:
            if last_msg.body:
                preview = last_msg.body[:40]
            elif last_msg.media_type == "image":
                preview = "📷 صورة"
            elif last_msg.media_type == "video":
                preview = "🎥 فيديو"
            elif last_msg.media_type == "audio":
                preview = "🎵 أغنية"
            time_str = fmt_sd(last_msg.created_at, "%H:%M")
        unread_tag = f'<span class="badge" style="position:static;margin-right:6px">{unread}</span>' if unread else ''
        pin_icon = '📌 ' if pinned else ''
        mute_icon = '🔕 ' if muted else ''
        online = '<span class="online-dot"></span>' if f.is_online else ''
        rows += f"""<div class="list-item">
          <img class="avatar-sm" src="{avatar_url(f)}" onclick="openAvatar('{avatar_url(f)}')">
          <a href="{url_for('chat_with', username=f.username)}" style="flex:1;text-decoration:none;color:inherit;min-width:0">
            <div class="li-name">{pin_icon}{mute_icon}{online}{f.short_name} {unread_tag}</div>
            <div class="li-sub">{preview}</div></a>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">
            <div class="li-sub">{time_str}</div>
            <div style="display:flex;gap:4px">
              {copy_btn_html(f.username, "يوزر", small=True)}
              {copy_btn_html(f.public_id, "ID", small=True)}
              <form method="POST" action="{url_for('archive_chat', username=f.username)}" style="margin:0">
                <button type="submit" class="copy-btn" style="padding:2px 8px;font-size:11px" title="أرشفة">📦</button>
              </form>
            </div>
          </div></div>"""
    if not rows:
        rows = '<p class="empty">لا محادثات. أضف أصدقاء لبدء الدردشة.</p>'
    archived_count = len(archived_ids)
    archive_link = f'<a class="btn btn-sm" href="{url_for("archived_list")}">📦 الأرشيف ({archived_count})</a>' if archived_count else ''
    return render_page(FLASH_BLOCK + topbar_html(badge) + f"""
    <div class="card"><h2>◈ الدردشات</h2>
    <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
      <a class="btn btn-sm" href="{url_for('friends_list')}">الأصدقاء</a>
      <a class="btn btn-sm" href="{url_for('discover')}">👥 اكتشف</a>
      <a class="btn btn-sm" href="{url_for('inbox')}">📩 المجهولة</a>
      {archive_link}
    </div>{rows}</div>""", title="الدردشات")


def render_bubble_chat(m, current_user, peer):
    cls = "me" if m.sender_id == current_user.id else "them"
    is_mine = (m.sender_id == current_user.id)
    media_html = ""
    if m.media:
        url = upload_url("chats", m.media)
        if m.media_type == "video":
            media_html = f'<video src="{url}" controls style="max-width:100%;border-radius:10px;margin-bottom:6px;max-height:320px"></video>'
        elif m.media_type == "audio":
            media_html = (f'<div class="audio-bubble"><span class="music-icon">🎵</span>'
                          f'<audio src="{url}" controls></audio></div>')
        else:
            img_onclick = f"openAvatar('{url}')"
            media_html = (f'<img src="{url}" style="max-width:100%;border-radius:10px;'
                          f'margin-bottom:6px;max-height:320px;cursor:pointer" '
                          f'onclick="event.stopPropagation();{img_onclick}">')
    # روابط قابلة للنقر
    body_html = f'<div>{linkify_text(m.body)}</div>' if m.body else ""
    # علامة الصح
    tick_html = ""
    if is_mine:
        tick_html = '<span class="read-tick read">✓✓</span>' if m.is_read else '<span class="read-tick">✓</span>'
    # صورة المرسل (للرسائل الواردة فقط في الفردي)
    header_html = ""
    if not is_mine:
        peer_avatar = avatar_url(peer)
        header_html = f"""<a class="sender-head" href="{url_for('view_profile', username=peer.username)}" 
           onclick="event.stopPropagation()">
           <img src="{peer_avatar}" class="sender-avatar">
           <span class="sender-name">{html_escape_text(peer.short_name)}</span>
        </a>"""
    reply_html = ""
    if m.reply_to_id:
        orig = db.session.get(ChatMessage, m.reply_to_id)
        if orig:
            if orig.body:
                orig_text = orig.body
            elif orig.media_type == "image":
                orig_text = "📷 صورة"
            elif orig.media_type == "video":
                orig_text = "🎥 فيديو"
            elif orig.media_type == "audio":
                orig_text = "🎵 أغنية"
            else:
                orig_text = "مرفق"
            orig_name = "أنت" if orig.sender_id == current_user.id else peer.short_name
            reply_html = f"""<div class="reply-quote">
              <div class="rq-name">{html_escape_text(orig_name)}</div>
              <div class="rq-body">{html_escape_text(orig_text[:120])}</div></div>"""
    reaction_html = ""
    if m.reaction:
        reaction_html = f'<span class="reaction-badge">{html_escape_text(m.reaction)}</span>'
    star_html = ""
    if m.is_starred:
        star_html = '<span class="star-badge">★</span>'
    body_esc_js = (m.body or "").replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")[:60]
    peer_name_js = "أنت" if is_mine else peer.short_name
    peer_name_js = peer_name_js.replace("'", "\\'")
    delete_btn = ""
    if is_mine:
        delete_btn = (f'<button type="button" class="act-btn delete" '
                      f'onclick="event.stopPropagation();deleteMsg({m.id})">🗑 حذف</button>')
    clear_react_btn = ""
    if m.reaction:
        clear_react_btn = (f'<button type="button" class="act-btn clear-react" '
                           f'onclick="event.stopPropagation();clearReact({m.id})">✖ إزالة التفاعل</button>')
    star_btn = (f'<button type="button" class="act-btn star" '
                f'onclick="event.stopPropagation();toggleStar({m.id})">'
                f'{"★ إزالة النجمة" if m.is_starred else "☆ تثبيت"}</button>')
    return f"""<div class="bubble-wrap">
      <div class="bubble {cls} clickable" id="msg-{m.id}" onclick="toggleMsgBar({m.id})" ondblclick="event.stopPropagation();doubleTap({m.id})">
        {header_html}{reply_html}{media_html}{body_html}
        <span class="t">{fmt_sd(m.created_at, "%H:%M")} {tick_html}</span>
        {reaction_html}{star_html}
      </div>
      <div class="msg-action-bar" id="bar-{m.id}" onclick="event.stopPropagation()">
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReact({m.id},'❤️')">❤️</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReact({m.id},'👍')">👍</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReact({m.id},'😂')">😂</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReact({m.id},'😮')">😮</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReact({m.id},'😢')">😢</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReact({m.id},'🙏')">🙏</button>
        <span class="act-divider"></span>
        <button type="button" class="act-btn all-emojis" onclick="event.stopPropagation();openEmojiPicker({m.id})">😊 المزيد</button>
        <button type="button" class="act-btn" onclick="event.stopPropagation();setReply({m.id}, '{body_esc_js}', '{peer_name_js}')">↩ رد</button>
        {star_btn}
        {clear_react_btn}
        {delete_btn}
        <button type="button" class="act-btn report" onclick="event.stopPropagation();reportChat()">🚨 إبلاغ</button>
      </div>
    </div>"""


@app.route("/chat/<username>", methods=["GET", "POST"])
@login_required
def chat_with(username):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    if peer.id == current_user.id:
        flash("لا يمكنك محادثة نفسك.", "error")
        return redirect(url_for("chats"))
    if is_blocked_between(current_user.id, peer.id):
        flash("لا يمكن إتمام العملية (يوجد حظر).", "error")
        return redirect(url_for("chats"))
    state, _ = friendship_status(current_user.id, peer.id)
    if state != "friends":
        flash("يجب أن تكونا صديقين لبدء الدردشة.", "error")
        return redirect(url_for("view_profile", username=peer.username))
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        file = request.files.get("media")
        reply_to_id = request.form.get("reply_to_id", type=int)
        media_fn = ""; media_type = ""
        if file and file.filename:
            fn_low = file.filename.lower()
            if allowed_video(fn_low) and check_video_magic(file):
                ext = fn_low.rsplit(".", 1)[1]
                media_fn = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(app.config["CHAT_FOLDER"], media_fn))
                media_type = "video"
            elif allowed_image(fn_low) and check_image_magic(file):
                ext = fn_low.rsplit(".", 1)[1]
                media_fn = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(app.config["CHAT_FOLDER"], media_fn))
                media_type = "image"
            elif allowed_audio(fn_low) and check_audio_magic(file):
                ext = fn_low.rsplit(".", 1)[1]
                media_fn = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(app.config["CHAT_FOLDER"], media_fn))
                media_type = "audio"
            else:
                flash("صيغة الملف غير مدعومة.", "error")
                return redirect(url_for("chat_with", username=peer.username))
        if not body and not media_fn:
            flash("الرسالة فارغة.", "error")
            return redirect(url_for("chat_with", username=peer.username))
        reply_obj = None
        if reply_to_id:
            reply_obj = ChatMessage.query.filter(
                ChatMessage.id == reply_to_id,
                or_(
                    and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == peer.id),
                    and_(ChatMessage.sender_id == peer.id, ChatMessage.receiver_id == current_user.id)
                )).first()
            if not reply_obj:
                reply_to_id = None
        db.session.add(ChatMessage(sender_id=current_user.id, receiver_id=peer.id,
                                    body=body[:2000], media=media_fn, media_type=media_type,
                                    reply_to_id=reply_to_id if reply_obj else None))
        db.session.commit()
        return redirect(url_for("chat_with", username=peer.username))
    ChatMessage.query.filter_by(sender_id=peer.id, receiver_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    msgs = ChatMessage.query.filter(or_(
        and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == peer.id),
        and_(ChatMessage.sender_id == peer.id, ChatMessage.receiver_id == current_user.id)
    )).order_by(ChatMessage.created_at.asc()).limit(500).all()
    def build_bubbles():
        return "".join(render_bubble_chat(m, current_user, peer) for m in msgs)
    if request.args.get("ajax") == "1":
        typing_users = get_typing_users(peer_id=current_user.id, exclude_user_id=current_user.id)
        typing_users = [u for u in typing_users if u.id == peer.id]
        typing_text = ""
        if typing_users:
            u = typing_users[0]
            typing_text = f'<span class="typing-name">{html_escape_text(u.short_name)}</span> يكتب'
        return jsonify({
            "html": build_bubbles(),
            "unread": unread_chat_count(current_user.id),
            "typing": typing_text
        })
    bubbles = build_bubbles()
    is_archived = ArchivedChat.query.filter_by(user_id=current_user.id, peer_id=peer.id).first() is not None
    if is_archived:
        arch_action = f"""<form method="POST" action="{url_for('unarchive_chat', username=peer.username)}" style="margin:0">
          <button type="submit" class="btn btn-sm">↩ إلغاء الأرشفة</button></form>"""
    else:
        arch_action = f"""<form method="POST" action="{url_for('archive_chat', username=peer.username)}" style="margin:0">
          <button type="submit" class="btn btn-sm">📦 أرشفة</button></form>"""
    online_status = ""
    if peer.is_online:
        online_status = '<span class="online-dot"></span><span style="color:#22c55e;font-size:11px;font-weight:700">متصل</span>'
    else:
        online_status = f'<span style="color:#9ca3af;font-size:11px">آخر ظهور: {time_ago_sd(peer.last_seen)}</span>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card">
      <div class="chat-header">
        <a href="{url_for('chats')}" class="btn btn-sm">←</a>
        <img class="avatar-sm" src="{avatar_url(peer)}" onclick="openAvatar('{avatar_url(peer)}')">
        <div><div class="pn">{peer.short_name}</div>
          <div class="pu">{online_status}</div></div>
        <div style="margin-right:auto;display:flex;gap:6px;align-items:center;flex-wrap:wrap">
          {copy_btn_html(peer.username, "يوزر", small=True)}
          {copy_btn_html(peer.public_id, "ID", small=True)}
          {arch_action}
          <button type="button" class="btn btn-sm" onclick="toggleSearch()">🔍 بحث</button>
          <a class="btn btn-sm" href="{url_for('view_profile', username=peer.username)}">البروفايل</a>
        </div>
      </div>
      <div class="chat-search-bar" id="search-bar" style="display:none">
        <input type="text" id="search-input" placeholder="ابحث في المحادثة..." oninput="filterMessages()">
        <button type="button" class="btn btn-sm" onclick="toggleSearch()">✕</button>
      </div>
      <div class="chat-box" id="chatbox">{bubbles}</div>
      <div id="reply-preview" class="reply-preview" style="display:none">
        <div class="rp-info">
          <div class="rp-name" id="rp-name"></div>
          <div class="rp-body" id="rp-body"></div>
        </div>
        <button type="button" class="rp-close" onclick="cancelReply()">✕</button>
      </div>
      <div class="typing-indicator" id="typing-indicator">
        <span class="typing-dots"><span></span><span></span><span></span></span>
        <span id="typing-text"></span>
      </div>
      <div id="emoji-picker" class="emoji-picker" style="display:none">
        <div id="emoji-grid"></div>
      </div>
      <form class="chat-input" method="POST" enctype="multipart/form-data" id="chat-form">
        <input type="hidden" name="reply_to_id" id="reply_to_id" value="">
        <input type="file" name="media" id="chat-media-input" accept="image/*,video/*,audio/*"
               style="display:none" onchange="previewChatMedia(this)">
        <button type="button" class="icon-btn" onclick="document.getElementById('chat-media-input').click()" title="إرفاق">📎</button>
        <button type="button" class="icon-btn" onclick="toggleEmojiQuick()" title="إيموجي">😊</button>
        <input name="body" id="chat-body-input" placeholder="اكتب رسالة..." autocomplete="off">
        <button type="submit">إرسال</button>
      </form>
      <div id="chat-media-preview" style="margin-top:8px"></div>
      <div class="chat-options">
        <button type="button" onclick="clearChatConfirm()">🧹 مسح المحادثة</button>
      </div>
    </div>
    {emoji_script(url_for('chat_react', username=peer.username), url_for('chat_report', username=peer.username))}
    <script>
    startChatAutoRefresh('{url_for("chat_with", username=peer.username)}', 1000);
    (function(){{
      var inp = document.getElementById('chat-body-input');
      var lastSent = 0;
      if(inp){{
        inp.addEventListener('input', function(){{
          var now = Date.now();
          if(now - lastSent > 2000){{
            lastSent = now;
            fetch('{url_for("chat_typing", username=peer.username)}', {{
              method: 'POST', credentials: 'same-origin',
              headers: {{'Content-Type':'application/json'}}
            }}).catch(function(){{}});
          }}
        }});
      }}
    }})();
    function toggleSearch(){{
      var b = document.getElementById('search-bar');
      if(!b) return;
      b.style.display = b.style.display === 'none' ? 'flex' : 'none';
      if(b.style.display === 'flex') document.getElementById('search-input').focus();
      else {{ document.getElementById('search-input').value=''; filterMessages(); }}
    }}
    function filterMessages(){{
      var q = (document.getElementById('search-input').value || '').toLowerCase().trim();
      var bubbles = document.querySelectorAll('.bubble');
      bubbles.forEach(function(b){{
        if(!q){{ b.style.opacity='1'; b.style.display=''; return; }}
        var txt = (b.textContent || '').toLowerCase();
        b.style.opacity = txt.indexOf(q) >= 0 ? '1' : '0.25';
      }});
    }}
    function clearChatConfirm(){{
      if(!confirm('🧹 هل أنت متأكد من مسح كل المحادثة؟\\nلا يمكن التراجع!')) return;
      fetch('/chat/{peer.username}/clear', {{
        method:'POST', credentials:'same-origin',
        headers: {{'Content-Type':'application/json'}}
      }}).then(function(r){{return r.json()}}).then(function(d){{
        if(d.ok) location.reload(); else alert('تعذّر المسح');
      }}).catch(function(){{alert('خطأ');}});
    }}
    function doubleTap(mid){{
      quickReact(mid, '❤️');
    }}
    function toggleStar(mid){{
      fetch('/chat/{peer.username}/star/' + mid, {{
        method:'POST', credentials:'same-origin',
        headers: {{'Content-Type':'application/json'}}
      }}).then(function(r){{return r.json()}}).then(function(d){{
        if(d.ok) location.reload();
      }}).catch(function(){{}});
    }}
    </script>
    """, title=f"دردشة @{peer.username}")


@app.route("/chat/<username>/typing", methods=["POST"])
@login_required
def chat_typing(username):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    set_typing(current_user.id, peer_id=peer.id, group_id=None)
    return jsonify({"ok": True})


@app.route("/chat/<username>/react", methods=["POST"])
@login_required
def chat_react(username):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    if is_blocked_between(current_user.id, peer.id):
        return jsonify({"ok": False, "error": "blocked"}), 403
    data = request.get_json(silent=True) or {}
    mid = data.get("message_id")
    emoji = (data.get("reaction") or "").strip()[:8]
    if not mid:
        return jsonify({"ok": False, "error": "no_mid"}), 400
    m = ChatMessage.query.filter(
        ChatMessage.id == int(mid),
        or_(
            and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == peer.id),
            and_(ChatMessage.sender_id == peer.id, ChatMessage.receiver_id == current_user.id)
        )).first()
    if not m:
        return jsonify({"ok": False, "error": "not_found"}), 404
    m.reaction = "" if m.reaction == emoji else emoji
    db.session.commit()
    return jsonify({"ok": True, "reaction": m.reaction})


@app.route("/chat/<username>/clear-reaction/<int:mid>", methods=["POST"])
@login_required
def chat_clear_reaction(username, mid):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    m = ChatMessage.query.filter(
        ChatMessage.id == mid,
        or_(
            and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == peer.id),
            and_(ChatMessage.sender_id == peer.id, ChatMessage.receiver_id == current_user.id)
        )).first()
    if not m:
        return jsonify({"ok": False, "error": "not_found"}), 404
    m.reaction = ""
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/chat/<username>/delete/<int:mid>", methods=["POST"])
@login_required
def chat_delete_message(username, mid):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    m = db.session.get(ChatMessage, mid)
    if not m:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if not ((m.sender_id == current_user.id and m.receiver_id == peer.id) or            (m.sender_id == peer.id and m.receiver_id == current_user.id)):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    if m.media:
        try:
            p = os.path.join(app.config["CHAT_FOLDER"], m.media)
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass
    ChatMessage.query.filter_by(reply_to_id=mid).update({"reply_to_id": None}, synchronize_session=False)
    db.session.delete(m)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/chat/<username>/star/<int:mid>", methods=["POST"])
@login_required
def chat_star_message(username, mid):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    m = ChatMessage.query.filter(
        ChatMessage.id == mid,
        or_(
            and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == peer.id),
            and_(ChatMessage.sender_id == peer.id, ChatMessage.receiver_id == current_user.id)
        )).first()
    if not m:
        return jsonify({"ok": False, "error": "not_found"}), 404
    m.is_starred = not bool(m.is_starred)
    db.session.commit()
    return jsonify({"ok": True, "starred": m.is_starred})


@app.route("/chat/<username>/clear", methods=["POST"])
@login_required
def chat_clear(username):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    msgs = ChatMessage.query.filter(or_(
        and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == peer.id),
        and_(ChatMessage.sender_id == peer.id, ChatMessage.receiver_id == current_user.id)
    )).all()
    for m in msgs:
        if m.media:
            try:
                p = os.path.join(app.config["CHAT_FOLDER"], m.media)
                if os.path.exists(p): os.remove(p)
            except OSError: pass
        db.session.delete(m)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/chat/<username>/report", methods=["POST"])
@login_required
def chat_report(username):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    if peer.id == current_user.id:
        return jsonify({"ok": False, "error": "لا يمكنك إبلاغ نفسك"}), 400
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip()[:500]
    existing = ChatReport.query.filter_by(
        reporter_id=current_user.id, target_id=peer.id).first()
    if existing:
        if existing.status == "pending":
            return jsonify({"ok": False, "error": "لديك بلاغ قيد المراجعة بالفعل"}), 400
        existing.reason = reason
        existing.status = "pending"
        existing.created_at = now_utc_naive()
        existing.resolved_at = None
    else:
        db.session.add(ChatReport(
            reporter_id=current_user.id,
            target_id=peer.id,
            reason=reason or "بدون سبب",
            status="pending"))
    peer.reports_count = (peer.reports_count or 0) + 1
    peer.under_review = True
    peer.review_reason = f"بلاغ من @{current_user.username}: {reason[:200] or 'بدون سبب'}"
    peer.review_started_at = now_utc_naive()
    db.session.commit()
    return jsonify({"ok": True, "message": "تم إرسال الإبلاغ"})


def emoji_script(react_url, report_url):
    base = react_url.rsplit("/react", 1)[0]
    return f"""<script>
var ALL_EMOJIS = "😀 😃 😄 😁 😆 😅 😂 🤣 😊 😇 🙂 😉 😍 🥰 😘 😗 😙 😚 😋 😛 😝 😜 🤪 🤨 🧐 🤓 😎 🥳 😏 😒 😞 😔 😟 😕 🙁 😣 😖 😫 😩 🥺 😢 😭 😤 😠 😡 🤬 🤯 😳 🥵 🥶 😱 😨 😰 😥 😓 🤗 🤔 🤭 🤫 🤥 😶 😐 😑 😬 🙄 😯 😦 😧 😮 😲 🥱 😴 🤤 😪 😵 🤐 🥴 🤢 🤮 🤧 😷 🤒 🤕 🤑 🤠 😈 👿 👻 💀 👽 🤖 💩 🔥 💯 ❤️ 🧡 💛 💚 💙 💜 🖤 🤍 🤎 💔 💕 💞 💓 💗 💖 💘 💝 👍 👎 👌 ✌️ 🤞 🤟 🤘 👊 ✊ 🤛 🤜 👏 🙌 👐 🤲 🤝 🙏 ✍️ 💅 💪 🦾 👀 🧠 👶 🧒 👦 👧 🧑 👨 👩 🧓 👴 👵 🙈 🙉 🙊 💋 💌 💐 🌹 🎁 🎉 🎊 🎈 ⚡ ✨ ⭐ 🌟 💫 🌈 ☀️ 🌙 🍕 🍔 🍟 🌮 🍿 🍎 🍓 🍉 ☕ 🍵 🍺 🍷 🏆 🥇 🥈 🥉 ⚽ 🏀 🎮 🎯 🎵 🎶 🚀 ✈️ 🚗 🏠 🐶 🐱 🦁 🐯 🐼 🦊 🐻".split(" ");
function buildEmojiGrid(){{
  var g=document.getElementById('emoji-grid');
  if(!g||g.dataset.built)return;
  g.dataset.built='1';
  g.innerHTML=ALL_EMOJIS.map(function(e){{
    return '<button type="button" class="emoji-item" data-emoji="'+e+'" onclick="sendReaction(this.dataset.emoji)">'+e+'</button>';
  }}).join('');
}}
function openEmojiPicker(mid){{
  buildEmojiGrid();
  var p=document.getElementById('emoji-picker');
  p.dataset.target=mid;
  p.style.display='block';
  document.querySelectorAll('.msg-action-bar.show').forEach(function(b){{b.classList.remove('show');}});
}}
function toggleEmojiQuick(){{
  var p=document.getElementById('emoji-picker');
  if(p.style.display==='block'){{p.style.display='none';return;}}
  buildEmojiGrid();
  p.dataset.target='';
  p.style.display='block';
}}
function toggleMsgBar(mid){{
  var bar=document.getElementById('bar-'+mid);
  if(!bar)return;
  var isOpen=bar.classList.contains('show');
  document.querySelectorAll('.msg-action-bar.show').forEach(function(b){{b.classList.remove('show');}});
  var p=document.getElementById('emoji-picker');
  if(p)p.style.display='none';
  if(!isOpen)bar.classList.add('show');
}}
function quickReact(mid,emoji){{
  var p=document.getElementById('emoji-picker');
  p.dataset.target=mid;
  sendReaction(emoji);
}}
function sendReaction(emoji){{
  var p=document.getElementById('emoji-picker');
  var mid=p.dataset.target;
  if(!mid){{p.style.display='none';return;}}
  fetch('{react_url}',{{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    credentials:'same-origin',
    body:JSON.stringify({{message_id:parseInt(mid),reaction:emoji}})
  }}).then(function(r){{return r.json()}}).then(function(d){{
    if(d.ok){{p.style.display='none';location.reload();}}
  }}).catch(function(){{}});
}}
function clearReact(mid){{
  if(!confirm('إزالة التفاعل من هذه الرسالة؟')) return;
  fetch('{base}/clear-reaction/'+mid,{{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    credentials:'same-origin'
  }}).then(function(r){{return r.json()}}).then(function(d){{
    if(d.ok) location.reload();
    else alert('تعذّر إزالة التفاعل');
  }}).catch(function(){{alert('خطأ في الاتصال');}});
}}
function deleteMsg(mid){{
  if(!confirm('🗑 هل أنت متأكد من حذف هذه الرسالة؟\\nلا يمكن التراجع.')) return;
  fetch('{base}/delete/'+mid,{{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    credentials:'same-origin'
  }}).then(function(r){{return r.json()}}).then(function(d){{
    if(d.ok) location.reload();
    else alert('تعذّر حذف الرسالة');
  }}).catch(function(){{alert('خطأ في الاتصال');}});
}}
function reportChat(){{
  if(!confirm('🚨 هل أنت متأكد من إبلاغ فريق الدعم؟')) return;
  var reason=prompt('اكتب سبب الإبلاغ (اختياري):','');
  if(reason===null) return;
  fetch('{report_url}',{{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    credentials:'same-origin',
    body:JSON.stringify({{reason:reason||'بدون سبب'}})
  }}).then(function(r){{return r.json()}}).then(function(d){{
    if(d.ok){{
      alert('✅ تم إرسال الإبلاغ.');
    }}else{{
      alert('⚠️ '+(d.error||'تعذّر إرسال الإبلاغ'));
    }}
  }}).catch(function(){{alert('⚠️ خطأ في الاتصال');}});
}}
function setReply(mid, body, name){{
  document.getElementById('reply_to_id').value=mid;
  document.getElementById('rp-name').textContent=name;
  document.getElementById('rp-body').textContent=body||'📎 مرفق';
  document.getElementById('reply-preview').style.display='flex';
  var inp=document.getElementById('chat-body-input');
  if(inp)inp.focus();
  document.querySelectorAll('.msg-action-bar.show').forEach(function(b){{b.classList.remove('show');}});
}}
function cancelReply(){{
  document.getElementById('reply_to_id').value='';
  document.getElementById('reply-preview').style.display='none';
}}
document.addEventListener('click',function(e){{
  if(!e.target.closest('.bubble') && !e.target.closest('.msg-action-bar')){{
    document.querySelectorAll('.msg-action-bar.show').forEach(function(b){{b.classList.remove('show');}});
  }}
}});
</script>"""


# ═══════════════════════════════════════════════════════════════
# GROUPS
# ═══════════════════════════════════════════════════════════════
@app.route("/groups")
@login_required
def groups_list():
    q = request.args.get("q", "").strip()
    my_groups = db.session.query(Group).join(GroupMember).filter(
        GroupMember.user_id == current_user.id, Group.is_banned == False
    ).order_by(Group.created_at.desc()).all()
    query = Group.query.filter(Group.is_banned == False)
    if q:
        ql = q.lower().lstrip("@")
        query = query.filter(or_(Group.name.ilike(f"%{ql}%"), Group.public_id.ilike(f"%{ql}%")))
    all_groups = query.order_by(Group.created_at.desc()).limit(50).all()
    my_html = ""
    for g in my_groups:
        member = get_group_member(g.id, current_user.id)
        role = member.role if member else "member"
        role_label = {"owner": "مالك", "admin": "مشرف", "member": "عضو"}.get(role, "عضو")
        role_cls = {"owner": "owner", "admin": "admin", "member": "member"}.get(role, "member")
        my_html += f"""<div class="group-card">
          <img class="g-avatar" src="{group_avatar_url(g)}">
          <a href="{url_for('group_chat', gid=g.id)}" style="flex:1;text-decoration:none;color:inherit;min-width:0">
            <div class="g-name"><span class="role-badge {role_cls}">{role_label}</span>{g.name}</div>
            <div class="g-sub">ID: {g.public_id} · {GroupMember.query.filter_by(group_id=g.id).count()} عضو</div>
          </a>
          <div style="display:flex;flex-direction:column;gap:4px">
            {copy_btn_html(g.public_id, "ID", small=True)}
            <a class="btn btn-sm" href="{url_for('group_view', gid=g.id)}">عرض</a>
          </div></div>"""
    if not my_html:
        my_html = '<p class="empty">لا مجموعات. أنشئ واحدة!</p>'
    all_html = ""
    my_ids = {m.id for m in my_groups}
    for g in all_groups:
        if g.id in my_ids:
            continue
        all_html += f"""<div class="group-card">
          <img class="g-avatar" src="{group_avatar_url(g)}">
          <a href="{url_for('group_view', gid=g.id)}" style="flex:1;text-decoration:none;color:inherit;min-width:0">
            <div class="g-name">{g.name}</div>
            <div class="g-sub">ID: {g.public_id} · {GroupMember.query.filter_by(group_id=g.id).count()} عضو</div>
          </a>
          <div style="display:flex;flex-direction:column;gap:4px">
            {copy_btn_html(g.public_id, "ID", small=True)}
            <a class="btn btn-sm" href="{url_for('group_view', gid=g.id)}">عرض</a>
          </div></div>"""
    if not all_html:
        all_html = '<p class="empty">لا مجموعات أخرى.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>◉ مجموعاتي</h2>
    <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
      <a class="btn btn-sm btn-primary" href="{url_for('group_create')}">➕ إنشاء مجموعة</a>
    </div>{my_html}</div>
    <div class="card"><h2>🔍 بحث في المجموعات</h2>
    <form method="GET" style="display:flex;gap:8px;margin-bottom:12px">
      <input name="q" value="{q}" placeholder="اسم المجموعة أو ID" style="flex:1;margin:0">
      <button type="submit" style="width:auto;padding:12px 20px;margin:0">بحث</button></form>
    {all_html}</div>""", title="المجموعات")


@app.route("/group/create", methods=["GET", "POST"])
@login_required
def group_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        is_public = request.form.get("is_public") == "1"
        if len(name) < 2 or len(name) > 64:
            flash("اسم المجموعة: 2-64 حرف.", "error")
            return redirect(url_for("group_create"))
        if len(description) > 300:
            flash("الوصف طويل جداً.", "error")
            return redirect(url_for("group_create"))
        pid = gen_public_id()
        while Group.query.filter_by(public_id=pid).first():
            pid = gen_public_id()
        g = Group(name=name, description=description, public_id=pid,
                  owner_id=current_user.id, is_public=is_public)
        db.session.add(g)
        db.session.flush()
        file = request.files.get("avatar")
        if file and file.filename:
            if allowed_image(file.filename) and check_image_magic(file):
                ext = file.filename.rsplit(".", 1)[1].lower()
                avatar_fn = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(app.config["GROUP_FOLDER"], avatar_fn))
                g.avatar = avatar_fn
        db.session.add(GroupMember(group_id=g.id, user_id=current_user.id, role="owner"))
        db.session.commit()
        flash(f"تم إنشاء المجموعة. ID: {g.public_id}", "success")
        return redirect(url_for("group_chat", gid=g.id))
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>➕ إنشاء مجموعة</h2>
    <form method="POST" enctype="multipart/form-data">
      <label>اسم المجموعة (2-64 حرف)</label>
      <input name="name" maxlength="64" required placeholder="مثال: أصدقاء السودان">
      <label>الوصف (اختياري)</label>
      <textarea name="description" maxlength="300" placeholder="وصف المجموعة..."></textarea>
      <label>صورة المجموعة (اختياري)</label>
      <input type="file" name="avatar" accept="image/*">
      <label class="switch-row" style="margin-top:14px">
        <span>🌍 مجموعة عامة (انضمام مباشر بدون موافقة)</span>
        <input type="checkbox" name="is_public" value="1"><span class="switch"></span></label>
      <div style="font-size:12px;color:#6b7280;margin-top:6px">
        إن لم تفعّل هذا الخيار، سيتم إرسال طلبات انضمام تحتاج موافقتك.</div>
      <button type="submit">إنشاء</button></form>
    <a class="link-center" href="{url_for('groups_list')}">رجوع</a></div>""", title="إنشاء مجموعة")


@app.route("/group/<int:gid>/avatar")
def group_avatar_full(gid):
    g = db.session.get(Group, gid)
    if not g:
        abort(404)
    if not g.avatar:
        flash("لا توجد صورة.", "error")
        if current_user.is_authenticated:
            return redirect(url_for("group_view", gid=gid))
        return redirect(url_for("login"))
    img_url = url_for("serve_upload", subpath=f"groups/{g.avatar}")
    is_admin = current_user.is_authenticated and is_group_admin_or_owner(gid, current_user.id)
    edit_btn = f'<a class="btn btn-primary" href="{url_for("group_edit", gid=gid)}">✏️ تعديل المجموعة</a>' if is_admin else ''
    back_link = url_for("group_view", gid=gid) if current_user.is_authenticated else url_for("login")
    return render_page(f"""
    <div class="card center">
      <img src="{img_url}" style="max-width:100%;border-radius:14px;object-fit:contain;max-height:80vh">
      <div class="name" style="margin-top:14px">{g.name}</div>
      <div class="username">ID: {g.public_id} {copy_btn_html(g.public_id, "نسخ", small=True)}</div>
      <div class="actions" style="margin-top:14px">
        {edit_btn}
        <a class="btn" href="{back_link}">← رجوع</a>
      </div>
    </div>""", title=f"صورة {g.name}")


@app.route("/group/<int:gid>")
@login_required
def group_view(gid):
    g = db.session.get(Group, gid)
    if not g:
        abort(404)
    if g.is_banned:
        flash("هذه المجموعة محظورة.", "error")
        return redirect(url_for("groups_list"))
    member = get_group_member(gid, current_user.id)
    members = GroupMember.query.filter_by(group_id=gid).all()
    is_member = member is not None
    is_admin = member and member.role in ("owner", "admin")
    is_owner = member and member.role == "owner"
    members_html = ""
    for m in members:
        u = m.user
        role_label = {"owner": "مالك", "admin": "مشرف", "member": "عضو"}.get(m.role, "عضو")
        role_cls = {"owner": "owner", "admin": "admin", "member": "member"}.get(m.role, "member")
        actions = ""
        if is_owner and m.user_id != current_user.id:
            if m.role == "member":
                actions += f'<a class="btn btn-sm btn-primary" href="{url_for("group_promote", gid=gid, uid=u.id)}">⬆ مشرف</a> '
            elif m.role == "admin":
                actions += f'<a class="btn btn-sm" href="{url_for("group_demote", gid=gid, uid=u.id)}">⬇ عضو</a> '
            actions += f'<a class="btn btn-sm btn-danger" href="{url_for("group_kick", gid=gid, uid=u.id)}" onclick="return confirm(\'طرد هذا العضو؟\')">🚫 طرد</a>'
        elif is_admin and not is_owner and m.user_id != current_user.id and m.role == "member":
            actions += f'<a class="btn btn-sm btn-danger" href="{url_for("group_kick", gid=gid, uid=u.id)}" onclick="return confirm(\'طرد هذا العضو؟\')">🚫 طرد</a>'
        online = '<span class="online-dot"></span>' if u.is_online else ''
        members_html += f"""<div class="list-item" style="cursor:default">
          <img class="avatar-sm" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
          <a href="{url_for('view_profile', username=u.username)}" style="flex:1;text-decoration:none;color:inherit;min-width:0">
            <div class="li-name">{online}<span class="role-badge {role_cls}">{role_label}</span>{u.short_name}</div>
            <div class="li-sub">@{u.username} · ID: {u.public_id}</div></a>
          <div class="li-actions">
            {copy_btn_html(u.username, "يوزر", small=True)}
            {copy_btn_html(u.public_id, "ID", small=True)}
            {actions}</div></div>"""
    admin_controls = ""
    if is_admin:
        pending_count = GroupJoinRequest.query.filter_by(group_id=gid).count()
        admin_controls = f"""<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;justify-content:center">
          <a class="btn btn-sm btn-primary" href="{url_for('group_edit', gid=gid)}">✏️ تعديل المجموعة</a>
          <a class="btn btn-sm" href="{url_for('group_chat', gid=gid)}">◈ فتح المحادثة</a>
          <a class="btn btn-sm" href="{url_for('group_requests', gid=gid)}"
             style="background:#f59e0b;color:#fff;border-color:#f59e0b">
            📥 طلبات الانضمام ({pending_count})
          </a>
        </div>"""
    if is_owner:
        admin_controls += f"""<div style="margin-top:10px">
          <a class="btn btn-sm btn-danger" href="{url_for('group_delete', gid=gid)}"
             onclick="return confirm('⚠️ هل أنت متأكد من حذف المجموعة نهائياً؟')"
             style="width:100%">🗑 حذف المجموعة نهائياً</a></div>"""
    if not is_member:
        existing_req = GroupJoinRequest.query.filter_by(group_id=gid, user_id=current_user.id).first()
        if existing_req:
            join_btn = '<div class="btn btn-disabled" style="cursor:default">⏳ طلبك قيد المراجعة</div>'
        elif g.is_public:
            join_btn = f'<a class="btn btn-primary" href="{url_for("group_join", gid=gid)}">➕ انضم للمجموعة</a>'
        else:
            join_btn = f'<a class="btn btn-primary" href="{url_for("group_join", gid=gid)}">📥 طلب الانضمام</a>'
    else:
        join_btn = f'<a class="btn btn-primary" href="{url_for("group_chat", gid=gid)}">◈ فتح المحادثة</a>'
        if not is_owner:
            join_btn += f'<a class="btn btn-danger" href="{url_for("group_leave", gid=gid)}" onclick="return confirm(\'مغادرة المجموعة؟\')">🚪 مغادرة المجموعة</a>'
    if g.avatar:
        avatar_html = (f'<img class="avatar group-avatar-clickable" src="{group_avatar_url(g)}" '
                       f'style="border-radius:20px;width:100px;height:100px" '
                       f'onclick="window.location.href=\'{url_for("group_avatar_full", gid=gid)}\'">')
    else:
        avatar_html = (f'<img class="avatar" src="{group_avatar_url(g)}" '
                       f'style="border-radius:20px;width:100px;height:100px;cursor:default">')
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card center">
      {avatar_html}
      <div class="name" style="margin-top:10px">{g.name}</div>
      <div class="group-id-box">
        <span class="gid-label">Group ID</span>
        <span class="gid-value">{g.public_id}</span>
        <button class="copy-btn" onclick="copyText('{g.public_id}', this)">نسخ</button>
      </div>
      {f'<div class="bio">{g.description}</div>' if g.description else ''}
      <div style="color:#6b7280;font-size:13px;margin-top:8px">
        {len(members)} عضو · أنشئت {fmt_sd(g.created_at, '%Y-%m-%d')}
        {' · 🌍 عامة' if g.is_public else ' · 🔒 خاصة'}
      </div>
      <div class="actions">{join_btn}</div>
      {admin_controls}
    </div>
    <div class="card"><h2>الأعضاء ({len(members)})</h2>{members_html}</div>""", title=g.name)


@app.route("/group/<int:gid>/edit", methods=["GET", "POST"])
@login_required
def group_edit(gid):
    g = db.session.get(Group, gid)
    if not g:
        abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role not in ("owner", "admin"):
        flash("ليس لديك صلاحية.", "error")
        return redirect(url_for("group_view", gid=gid))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        is_public = request.form.get("is_public") == "1"
        if len(name) < 2 or len(name) > 64:
            flash("اسم المجموعة: 2-64 حرف.", "error")
            return redirect(url_for("group_edit", gid=gid))
        if len(description) > 300:
            flash("الوصف طويل جداً.", "error")
            return redirect(url_for("group_edit", gid=gid))
        g.name = name
        g.description = description
        g.is_public = is_public
        file = request.files.get("avatar")
        if file and file.filename:
            if allowed_image(file.filename) and check_image_magic(file):
                if g.avatar:
                    try: os.remove(os.path.join(app.config["GROUP_FOLDER"], g.avatar))
                    except OSError: pass
                ext = file.filename.rsplit(".", 1)[1].lower()
                fn = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(app.config["GROUP_FOLDER"], fn))
                g.avatar = fn
        if request.form.get("remove_avatar") == "1" and g.avatar:
            try: os.remove(os.path.join(app.config["GROUP_FOLDER"], g.avatar))
            except OSError: pass
            g.avatar = ""
        db.session.commit()
        flash("تم تحديث المجموعة.", "success")
        return redirect(url_for("group_view", gid=gid))
    is_public_checked = "checked" if g.is_public else ""
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>✏️ تعديل المجموعة</h2>
    <div style="text-align:center;margin-bottom:14px">
      <img src="{group_avatar_url(g)}" class="avatar" style="border-radius:20px;width:100px;height:100px;cursor:default">
    </div>
    <form method="POST" enctype="multipart/form-data">
      <label>اسم المجموعة</label>
      <input name="name" value="{g.name}" maxlength="64" required>
      <label>الوصف</label>
      <textarea name="description" maxlength="300">{g.description}</textarea>
      <label>تغيير الصورة</label>
      <input type="file" name="avatar" accept="image/*">
      <label class="switch-row" style="margin-top:12px">
        <span>🗑 حذف الصورة الحالية</span>
        <input type="checkbox" name="remove_avatar" value="1"><span class="switch"></span></label>
      <label class="switch-row" style="margin-top:8px">
        <span>🌍 مجموعة عامة (انضمام مباشر)</span>
        <input type="checkbox" name="is_public" value="1" {is_public_checked}><span class="switch"></span></label>
      <button type="submit">حفظ التعديلات</button></form>
    <a class="link-center" href="{url_for('group_view', gid=gid)}">رجوع</a></div>""", title="تعديل المجموعة")


@app.route("/group/<int:gid>/join")
@login_required
def group_join(gid):
    g = db.session.get(Group, gid)
    if not g:
        abort(404)
    if g.is_banned:
        flash("هذه المجموعة محظورة.", "error")
        return redirect(url_for("groups_list"))
    if get_group_member(gid, current_user.id):
        flash("أنت عضو بالفعل.", "error")
        return redirect(url_for("group_view", gid=gid))
    existing = GroupJoinRequest.query.filter_by(group_id=gid, user_id=current_user.id).first()
    if existing:
        flash("طلبك قيد المراجعة.", "info")
        return redirect(url_for("group_view", gid=gid))
    if g.is_public:
        db.session.add(GroupMember(group_id=gid, user_id=current_user.id, role="member"))
        db.session.commit()
        flash(f"انضممت إلى {g.name}.", "success")
        return redirect(url_for("group_chat", gid=gid))
    db.session.add(GroupJoinRequest(group_id=gid, user_id=current_user.id))
    db.session.commit()
    flash(f"تم إرسال طلب الانضمام إلى {g.name}.", "success")
    return redirect(url_for("group_view", gid=gid))


@app.route("/group/<int:gid>/requests")
@login_required
def group_requests(gid):
    g = db.session.get(Group, gid)
    if not g:
        abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role not in ("owner", "admin"):
        flash("ليس لديك صلاحية.", "error")
        return redirect(url_for("group_view", gid=gid))
    reqs = GroupJoinRequest.query.filter_by(group_id=gid).order_by(
        GroupJoinRequest.created_at.desc()).all()
    rows = ""
    for r in reqs:
        u = r.user
        rows += f"""<div class="list-item" style="cursor:default">
          <img class="avatar-sm" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
          <a href="{url_for('view_profile', username=u.username)}" style="flex:1;text-decoration:none;color:inherit">
            <div class="li-name">{u.short_name}</div>
            <div class="li-sub">@{u.username} · ID: {u.public_id} · {fmt_sd(r.created_at)}</div></a>
          <div class="li-actions">
            {copy_btn_html(u.username, "يوزر", small=True)}
            {copy_btn_html(u.public_id, "ID", small=True)}
            <a class="btn btn-sm btn-primary" href="{url_for('group_accept_request', gid=gid, rid=r.id)}">✅ قبول</a>
            <a class="btn btn-sm btn-danger" href="{url_for('group_reject_request', gid=gid, rid=r.id)}">✖ رفض</a>
          </div></div>"""
    if not rows:
        rows = '<p class="empty">لا طلبات انضمام.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>📥 طلبات الانضمام ({len(reqs)})</h2>{rows}
    <a class="link-center" href="{url_for('group_view', gid=gid)}">← رجوع</a></div>""", title="طلبات الانضمام")


@app.route("/group/<int:gid>/request/<int:rid>/accept")
@login_required
def group_accept_request(gid, rid):
    g = db.session.get(Group, gid)
    if not g:
        abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role not in ("owner", "admin"):
        abort(403)
    r = db.session.get(GroupJoinRequest, rid)
    if not r or r.group_id != gid:
        abort(404)
    uid = r.user_id
    uname = r.user.username if r.user else "?"
    if not get_group_member(gid, uid):
        db.session.add(GroupMember(group_id=gid, user_id=uid, role="member"))
    db.session.delete(r)
    db.session.commit()
    flash(f"تم قبول @{uname}.", "success")
    return redirect(url_for("group_requests", gid=gid))


@app.route("/group/<int:gid>/request/<int:rid>/reject")
@login_required
def group_reject_request(gid, rid):
    g = db.session.get(Group, gid)
    if not g:
        abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role not in ("owner", "admin"):
        abort(403)
    r = db.session.get(GroupJoinRequest, rid)
    if not r or r.group_id != gid:
        abort(404)
    db.session.delete(r)
    db.session.commit()
    flash("تم رفض الطلب.", "success")
    return redirect(url_for("group_requests", gid=gid))


@app.route("/group/<int:gid>/leave")
@login_required
def group_leave(gid):
    g = db.session.get(Group, gid)
    if not g:
        abort(404)
    m = get_group_member(gid, current_user.id)
    if not m:
        flash("لست عضوًا.", "error")
        return redirect(url_for("groups_list"))
    if m.role == "owner":
        new_owner = GroupMember.query.filter_by(
            group_id=gid, role="admin"
        ).order_by(GroupMember.joined_at.asc()).first()
        if not new_owner:
            new_owner = GroupMember.query.filter(
                GroupMember.group_id == gid,
                GroupMember.user_id != current_user.id
            ).order_by(GroupMember.joined_at.asc()).first()
        if new_owner:
            new_owner.role = "owner"
            g.owner_id = new_owner.user_id
            db.session.delete(m)
            db.session.commit()
            flash(f"غادرت المجموعة. تم نقل الملكية إلى @{new_owner.user.username}.", "success")
            return redirect(url_for("groups_list"))
        else:
            if g.avatar:
                try: os.remove(os.path.join(app.config["GROUP_FOLDER"], g.avatar))
                except OSError: pass
            for msg in GroupMessage.query.filter_by(group_id=gid).all():
                if msg.media:
                    try: os.remove(os.path.join(app.config["GROUP_FOLDER"], msg.media))
                    except OSError: pass
                db.session.delete(msg)
            GroupMember.query.filter_by(group_id=gid).delete(synchronize_session=False)
            GroupReport.query.filter_by(group_id=gid).delete(synchronize_session=False)
            GroupJoinRequest.query.filter_by(group_id=gid).delete(synchronize_session=False)
            db.session.delete(g)
            db.session.commit()
            flash("غادرت المجموعة الأخيرة، تم حذف القروب.", "success")
            return redirect(url_for("groups_list"))
    db.session.delete(m)
    db.session.commit()
    flash(f"غادرت {g.name}.", "success")
    return redirect(url_for("groups_list"))


@app.route("/group/<int:gid>/kick/<int:uid>")
@login_required
def group_kick(gid, uid):
    g = db.session.get(Group, gid)
    if not g:
        abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role not in ("owner", "admin"):
        flash("ليس لديك صلاحية.", "error")
        return redirect(url_for("group_view", gid=gid))
    target = get_group_member(gid, uid)
    if not target:
        flash("العضو غير موجود.", "error")
        return redirect(url_for("group_view", gid=gid))
    if target.role == "owner":
        flash("لا يمكن طرد المالك.", "error")
        return redirect(url_for("group_view", gid=gid))
    if me.role == "admin" and target.role == "admin":
        flash("لا يمكن للمشرف طرد مشرف آخر.", "error")
        return redirect(url_for("group_view", gid=gid))
    db.session.delete(target)
    db.session.commit()
    flash("تم طرد العضو.", "success")
    return redirect(url_for("group_view", gid=gid))


@app.route("/group/<int:gid>/promote/<int:uid>")
@login_required
def group_promote(gid, uid):
    g = db.session.get(Group, gid)
    if not g:
        abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role != "owner":
        flash("فقط المالك يمكنه ترقية المشرفين.", "error")
        return redirect(url_for("group_view", gid=gid))
    target = get_group_member(gid, uid)
    if not target:
        flash("العضو غير موجود.", "error")
        return redirect(url_for("group_view", gid=gid))
    target.role = "admin"
    db.session.commit()
    flash("تم ترقية العضو إلى مشرف.", "success")
    return redirect(url_for("group_view", gid=gid))


@app.route("/group/<int:gid>/demote/<int:uid>")
@login_required
def group_demote(gid, uid):
    g = db.session.get(Group, gid)
    if not g:
        abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role != "owner":
        flash("فقط المالك يمكنه تخفيض المشرفين.", "error")
        return redirect(url_for("group_view", gid=gid))
    target = get_group_member(gid, uid)
    if not target or target.role != "admin":
        flash("ليس مشرفاً.", "error")
        return redirect(url_for("group_view", gid=gid))
    target.role = "member"
    db.session.commit()
    flash("تم تخفيض المشرف إلى عضو.", "success")
    return redirect(url_for("group_view", gid=gid))


@app.route("/group/<int:gid>/add", methods=["POST"])
@login_required
def group_add_member(gid):
    g = db.session.get(Group, gid)
    if not g:
        abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role not in ("owner", "admin"):
        flash("ليس لديك صلاحية.", "error")
        return redirect(url_for("group_chat", gid=gid))
    username = request.form.get("username", "").strip().lower().lstrip("@")
    target = User.query.filter_by(username=username).first()
    if not target:
        flash("المستخدم غير موجود.", "error")
        return redirect(url_for("group_chat", gid=gid))
    if target.is_banned or target.under_review:
        flash("لا يمكن إضافة هذا المستخدم.", "error")
        return redirect(url_for("group_chat", gid=gid))
    if get_group_member(gid, target.id):
        flash("المستخدم عضو بالفعل.", "error")
        return redirect(url_for("group_chat", gid=gid))
    GroupJoinRequest.query.filter_by(group_id=gid, user_id=target.id).delete()
    db.session.add(GroupMember(group_id=gid, user_id=target.id, role="member"))
    db.session.commit()
    flash(f"تم إضافة @{target.username}.", "success")
    return redirect(url_for("group_chat", gid=gid))


@app.route("/group/<int:gid>/delete")
@login_required
def group_delete(gid):
    g = db.session.get(Group, gid)
    if not g:
        abort(404)
    if g.owner_id != current_user.id:
        flash("فقط المالك يمكنه حذف المجموعة.", "error")
        return redirect(url_for("group_view", gid=gid))
    for m in GroupMessage.query.filter_by(group_id=gid).all():
        if m.media:
            try: os.remove(os.path.join(app.config["GROUP_FOLDER"], m.media))
            except OSError: pass
        db.session.delete(m)
    if g.avatar:
        try: os.remove(os.path.join(app.config["GROUP_FOLDER"], g.avatar))
        except OSError: pass
    GroupMember.query.filter_by(group_id=gid).delete(synchronize_session=False)
    GroupReport.query.filter_by(group_id=gid).delete(synchronize_session=False)
    GroupJoinRequest.query.filter_by(group_id=gid).delete(synchronize_session=False)
    db.session.delete(g)
    db.session.commit()
    flash("تم حذف المجموعة.", "success")
    return redirect(url_for("groups_list"))


def render_group_bubble(m, current_user):
    cls = "me" if m.sender_id == current_user.id else "them"
    is_mine = (m.sender_id == current_user.id)
    sender = m.sender
    sender_name = sender.short_name if sender else "?"
    sender_avatar = avatar_url(sender) if sender else ""
    sender_username = sender.username if sender else ""
    media_html = ""
    if m.media:
        url = upload_url("groups", m.media)
        if m.media_type == "video":
            media_html = f'<video src="{url}" controls style="max-width:100%;border-radius:10px;margin-bottom:6px;max-height:320px"></video>'
        elif m.media_type == "audio":
            media_html = (f'<div class="audio-bubble"><span class="music-icon">🎵</span>'
                          f'<audio src="{url}" controls></audio></div>')
        else:
            img_onclick = f"openAvatar('{url}')"
            media_html = (f'<img src="{url}" style="max-width:100%;border-radius:10px;'
                          f'margin-bottom:6px;max-height:320px;cursor:pointer" '
                          f'onclick="event.stopPropagation();{img_onclick}">')
    body_html = f'<div>{linkify_text(m.body)}</div>' if m.body else ""
    # صورة + اسم المرسل (قابل للنقر)
    header_html = ""
    if not is_mine and sender:
        header_html = f"""<a class="sender-head" href="{url_for('view_profile', username=sender_username)}" 
           onclick="event.stopPropagation()">
           <img src="{sender_avatar}" class="sender-avatar">
           <span class="sender-name">{html_escape_text(sender_name)}</span>
        </a>"""
    reply_html = ""
    if m.reply_to_id:
        orig = db.session.get(GroupMessage, m.reply_to_id)
        if orig:
            if orig.body:
                orig_text = orig.body
            elif orig.media_type == "image":
                orig_text = "📷 صورة"
            elif orig.media_type == "video":
                orig_text = "🎥 فيديو"
            elif orig.media_type == "audio":
                orig_text = "🎵 أغنية"
            else:
                orig_text = "مرفق"
            orig_name = "أنت" if orig.sender_id == current_user.id else (orig.sender.short_name if orig.sender else "?")
            reply_html = f"""<div class="reply-quote">
              <div class="rq-name">{html_escape_text(orig_name)}</div>
              <div class="rq-body">{html_escape_text(orig_text[:120])}</div></div>"""
    reaction_html = ""
    if m.reaction:
        reaction_html = f'<span class="reaction-badge">{html_escape_text(m.reaction)}</span>'
    star_html = ""
    if m.is_starred:
        star_html = '<span class="star-badge">★</span>'
    body_esc_js = (m.body or "").replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")[:60]
    sender_name_js = ("أنت" if is_mine else sender_name).replace("'", "\\'")
    delete_btn = ""
    if is_mine:
        delete_btn = (f'<button type="button" class="act-btn delete" '
                      f'onclick="event.stopPropagation();deleteMsgG({m.id})">🗑 حذف</button>')
    clear_react_btn = ""
    if m.reaction:
        clear_react_btn = (f'<button type="button" class="act-btn clear-react" '
                           f'onclick="event.stopPropagation();clearReactG({m.id})">✖ إزالة التفاعل</button>')
    return f"""<div class="bubble-wrap">
      <div class="bubble {cls} clickable" id="gmsg-{m.id}" onclick="toggleMsgBarG({m.id})" ondblclick="event.stopPropagation();doubleTapG({m.id})">
        {header_html}{reply_html}{media_html}{body_html}
        <span class="t">{fmt_sd(m.created_at, "%H:%M")}</span>
        {reaction_html}{star_html}
      </div>
      <div class="msg-action-bar" id="gbar-{m.id}" onclick="event.stopPropagation()">
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReactG({m.id},'❤️')">❤️</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReactG({m.id},'👍')">👍</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReactG({m.id},'😂')">😂</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReactG({m.id},'😮')">😮</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReactG({m.id},'😢')">😢</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReactG({m.id},'🙏')">🙏</button>
        <span class="act-divider"></span>
        <button type="button" class="act-btn all-emojis" onclick="event.stopPropagation();openEmojiPickerG({m.id})">😊 المزيد</button>
        <button type="button" class="act-btn" onclick="event.stopPropagation();setReplyG({m.id}, '{body_esc_js}', '{sender_name_js}')">↩ رد</button>
        {clear_react_btn}
        {delete_btn}
      </div>
    </div>"""


def emoji_script_group(react_url):
    base = react_url.rsplit("/react", 1)[0]
    return f"""<script>
var ALL_EMOJIS_G = "😀 😃 😄 😁 😆 😅 😂 🤣 😊 😇 🙂 😉 😍 🥰 😘 😗 😙 😚 😋 😛 😝 😜 🤪 🤨 🧐 🤓 😎 🥳 😏 😒 😞 😔 😟 😕 🙁 😣 😖 😫 😩 🥺 😢 😭 😤 😠 😡 🤬 🤯 😳 🥵 🥶 😱 😨 😰 😥 😓 🤗 🤔 🤭 🤫 🤥 😶 😐 😑 😬 🙄 😯 😦 😧 😮 😲 🥱 😴 🤤 😪 😵 🤐 🥴 🤢 🤮 🤧 😷 🤒 🤕 🤑 🤠 😈 👿 👻 💀 👽 🤖 💩 🔥 💯 ❤️ 🧡 💛 💚 💙 💜 🖤 🤍 🤎 💔 💕 💞 💓 💗 💖 💘 💝 👍 👎 👌 ✌️ 🤞 🤟 🤘 👊 ✊ 🤛 🤜 👏 🙌 👐 🤲 🤝 🙏 ✍️ 💅 💪 🦾 👀 🧠 👶 🧒 👦 👧 🧑 👨 👩 🧓 👴 👵 🙈 🙉 🙊 💋 💌 💐 🌹 🎁 🎉 🎊 🎈 ⚡ ✨ ⭐ 🌟 💫 🌈 ☀️ 🌙 🍕 🍔 🍟 🌮 🍿 🍎 🍓 🍉 ☕ 🍵 🍺 🍷 🏆 🥇 🥈 🥉 ⚽ 🏀 🎮 🎯 🎵 🎶 🚀 ✈️ 🚗 🏠 🐶 🐱 🦁 🐯 🐼 🦊 🐻".split(" ");
function buildEmojiGridG(){{
  var g=document.getElementById('emoji-grid-g');
  if(!g||g.dataset.built)return;
  g.dataset.built='1';
  g.innerHTML=ALL_EMOJIS_G.map(function(e){{
    return '<button type="button" class="emoji-item" data-emoji="'+e+'" onclick="sendReactionG(this.dataset.emoji)">'+e+'</button>';
  }}).join('');
}}
function openEmojiPickerG(mid){{
  buildEmojiGridG();
  var p=document.getElementById('emoji-picker-g');
  p.dataset.target=mid;
  p.style.display='block';
  document.querySelectorAll('.msg-action-bar.show').forEach(function(b){{b.classList.remove('show');}});
}}
function toggleEmojiQuickG(){{
  var p=document.getElementById('emoji-picker-g');
  if(p.style.display==='block'){{p.style.display='none';return;}}
  buildEmojiGridG();
  p.dataset.target='';
  p.style.display='block';
}}
function toggleMsgBarG(mid){{
  var bar=document.getElementById('gbar-'+mid);
  if(!bar)return;
  var isOpen=bar.classList.contains('show');
  document.querySelectorAll('.msg-action-bar.show').forEach(function(b){{b.classList.remove('show');}});
  var p=document.getElementById('emoji-picker-g');
  if(p)p.style.display='none';
  if(!isOpen)bar.classList.add('show');
}}
function quickReactG(mid,emoji){{
  var p=document.getElementById('emoji-picker-g');
  p.dataset.target=mid;
  sendReactionG(emoji);
}}
function sendReactionG(emoji){{
  var p=document.getElementById('emoji-picker-g');
  var mid=p.dataset.target;
  if(!mid){{p.style.display='none';return;}}
  fetch('{react_url}',{{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    credentials:'same-origin',
    body:JSON.stringify({{message_id:parseInt(mid),reaction:emoji}})
  }}).then(function(r){{return r.json()}}).then(function(d){{
    if(d.ok){{p.style.display='none';location.reload();}}
  }}).catch(function(){{}});
}}
function clearReactG(mid){{
  if(!confirm('إزالة التفاعل من هذه الرسالة؟')) return;
  fetch('{base}/clear-reaction/'+mid,{{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    credentials:'same-origin'
  }}).then(function(r){{return r.json()}}).then(function(d){{
    if(d.ok) location.reload();
    else alert('تعذّر إزالة التفاعل');
  }}).catch(function(){{alert('خطأ في الاتصال');}});
}}
function deleteMsgG(mid){{
  if(!confirm('🗑 هل أنت متأكد من حذف هذه الرسالة؟\\nلا يمكن التراجع.')) return;
  fetch('{base}/delete-msg/'+mid,{{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    credentials:'same-origin'
  }}).then(function(r){{return r.json()}}).then(function(d){{
    if(d.ok) location.reload();
    else alert('تعذّر حذف الرسالة');
  }}).catch(function(){{alert('خطأ في الاتصال');}});
}}
function setReplyG(mid, body, name){{
  document.getElementById('reply_to_id').value=mid;
  document.getElementById('rp-name').textContent=name;
  document.getElementById('rp-body').textContent=body||'📎 مرفق';
  document.getElementById('reply-preview').style.display='flex';
  var inp=document.getElementById('group-body-input');
  if(inp)inp.focus();
  document.querySelectorAll('.msg-action-bar.show').forEach(function(b){{b.classList.remove('show');}});
}}
function cancelReply(){{
  document.getElementById('reply_to_id').value='';
  document.getElementById('reply-preview').style.display='none';
}}
function doubleTapG(mid){{
  quickReactG(mid, '❤️');
}}
document.addEventListener('click',function(e){{
  if(!e.target.closest('.bubble') && !e.target.closest('.msg-action-bar')){{
    document.querySelectorAll('.msg-action-bar.show').forEach(function(b){{b.classList.remove('show');}});
  }}
}});
</script>"""


@app.route("/group/<int:gid>/typing", methods=["POST"])
@login_required
def group_typing(gid):
    g = db.session.get(Group, gid)
    if not g:
        return jsonify({"ok": False}), 404
    me = get_group_member(gid, current_user.id)
    if not me:
        return jsonify({"ok": False}), 403
    set_typing(current_user.id, peer_id=None, group_id=gid)
    return jsonify({"ok": True})


@app.route("/group/<int:gid>/chat", methods=["GET", "POST"])
@login_required
def group_chat(gid):
    g = db.session.get(Group, gid)
    if not g:
        abort(404)
    if g.is_banned:
        flash("هذه المجموعة محظورة.", "error")
        return redirect(url_for("groups_list"))
    me = get_group_member(gid, current_user.id)
    if not me:
        flash("يجب أن تكون عضواً.", "error")
        return redirect(url_for("group_view", gid=gid))
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        file = request.files.get("media")
        reply_to_id = request.form.get("reply_to_id", type=int)
        media_fn = ""; media_type = ""
        if file and file.filename:
            fn_low = file.filename.lower()
            if allowed_video(fn_low) and check_video_magic(file):
                ext = fn_low.rsplit(".", 1)[1]
                media_fn = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(app.config["GROUP_FOLDER"], media_fn))
                media_type = "video"
            elif allowed_image(fn_low) and check_image_magic(file):
                ext = fn_low.rsplit(".", 1)[1]
                media_fn = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(app.config["GROUP_FOLDER"], media_fn))
                media_type = "image"
            elif allowed_audio(fn_low) and check_audio_magic(file):
                ext = fn_low.rsplit(".", 1)[1]
                media_fn = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(app.config["GROUP_FOLDER"], media_fn))
                media_type = "audio"
        reply_obj = None
        if reply_to_id:
            reply_obj = GroupMessage.query.filter_by(id=reply_to_id, group_id=gid).first()
            if not reply_obj:
                reply_to_id = None
        if body or media_fn:
            db.session.add(GroupMessage(group_id=gid, sender_id=current_user.id,
                                         body=body[:2000], media=media_fn, media_type=media_type,
                                         reply_to_id=reply_to_id if reply_obj else None))
            db.session.commit()
        return redirect(url_for("group_chat", gid=gid))
    msgs = GroupMessage.query.filter_by(group_id=gid).order_by(GroupMessage.created_at.asc()).limit(500).all()
    def build_group_bubbles():
        return "".join(render_group_bubble(m, current_user) for m in msgs)
    if request.args.get("ajax") == "1":
        typing_users = get_typing_users(group_id=gid, exclude_user_id=current_user.id)
        typing_text = ""
        if typing_users:
            names = [html_escape_text(u.short_name) for u in typing_users[:3]]
            if len(typing_users) == 1:
                typing_text = f'<span class="typing-name">{names[0]}</span> يكتب'
            elif len(typing_users) == 2:
                typing_text = f'<span class="typing-name">{names[0]}</span> و <span class="typing-name">{names[1]}</span> يكتبان'
            else:
                typing_text = f'<span class="typing-name">{names[0]}</span> و{len(typing_users)-1} آخرين يكتبون'
        return jsonify({"html": build_group_bubbles(), "unread": 0, "typing": typing_text})
    bubbles = build_group_bubbles()
    member_count = GroupMember.query.filter_by(group_id=gid).count()
    is_admin = me.role in ("owner", "admin")
    is_owner = me.role == "owner"
    pending_count = GroupJoinRequest.query.filter_by(group_id=gid).count()
    header_links = f'<a class="btn btn-sm" href="{url_for("group_view", gid=gid)}">👥 الأعضاء ({member_count})</a>'
    if is_admin:
        header_links += f'<a class="btn btn-sm" href="{url_for("group_requests", gid=gid)}" style="background:#f59e0b;color:#fff;border-color:#f59e0b">📥 ({pending_count})</a>'
    if not is_owner:
        header_links += f'<a class="btn btn-sm btn-danger" href="{url_for("group_leave", gid=gid)}" onclick="return confirm(\'🚪 هل أنت متأكد من مغادرة المجموعة؟\')">🚪 مغادرة</a>'
    add_form = ""
    if is_admin:
        add_form = f"""<form method="POST" action="{url_for('group_add_member', gid=gid)}" style="display:flex;gap:6px;margin-top:8px">
          <input name="username" placeholder="أضف باليوزر (بدون @)" style="flex:1;margin:0">
          <button type="submit" class="btn btn-sm btn-primary" style="margin:0">➕ إضافة</button></form>"""
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card">
      <div class="chat-header">
        <a href="{url_for('groups_list')}" class="btn btn-sm">←</a>
        <img class="avatar-sm" src="{group_avatar_url(g)}" style="border-radius:12px">
        <div><div class="pn">{g.name}</div>
          <div class="pu">ID: {g.public_id}
            {copy_btn_html(g.public_id, "ID", small=True)}
          </div></div>
        <div style="margin-right:auto;display:flex;gap:6px;flex-wrap:wrap">{header_links}</div>
      </div>
      {add_form}
      <div class="chat-search-bar" id="search-bar" style="display:none;margin-top:8px">
        <input type="text" id="search-input" placeholder="ابحث في المحادثة..." oninput="filterMessages()">
        <button type="button" class="btn btn-sm" onclick="toggleSearch()">✕</button>
      </div>
      <div class="chat-box" id="chatbox" style="margin-top:10px">{bubbles}</div>
      <div id="reply-preview" class="reply-preview" style="display:none">
        <div class="rp-info">
          <div class="rp-name" id="rp-name"></div>
          <div class="rp-body" id="rp-body"></div>
        </div>
        <button type="button" class="rp-close" onclick="cancelReply()">✕</button>
      </div>
      <div class="typing-indicator" id="typing-indicator">
        <span class="typing-dots"><span></span><span></span><span></span></span>
        <span id="typing-text"></span>
      </div>
      <div id="emoji-picker-g" class="emoji-picker" style="display:none">
        <div id="emoji-grid-g"></div>
      </div>
      <form class="chat-input" method="POST" enctype="multipart/form-data">
        <input type="hidden" name="reply_to_id" id="reply_to_id" value="">
        <input type="file" name="media" id="chat-media-input" accept="image/*,video/*,audio/*"
               style="display:none" onchange="previewChatMedia(this)">
        <button type="button" class="icon-btn" onclick="document.getElementById('chat-media-input').click()" title="إرفاق">📎</button>
        <button type="button" class="icon-btn" onclick="toggleEmojiQuickG()" title="إيموجي">😊</button>
        <input name="body" id="group-body-input" placeholder="اكتب رسالة..." autocomplete="off">
        <button type="submit">إرسال</button>
      </form>
      <div id="chat-media-preview" style="margin-top:8px"></div>
      <div class="chat-options">
        <button type="button" onclick="toggleSearch()">🔍 بحث</button>
      </div>
    </div>
    {emoji_script_group(url_for('group_react', gid=gid))}
    <script>
    startChatAutoRefresh('{url_for("group_chat", gid=gid)}', 1000);
    (function(){{
      var inp = document.getElementById('group-body-input');
      var lastSent = 0;
      if(inp){{
        inp.addEventListener('input', function(){{
          var now = Date.now();
          if(now - lastSent > 2000){{
            lastSent = now;
            fetch('{url_for("group_typing", gid=gid)}', {{
              method: 'POST', credentials: 'same-origin',
              headers: {{'Content-Type':'application/json'}}
            }}).catch(function(){{}});
          }}
        }});
      }}
    }})();
    function toggleSearch(){{
      var b = document.getElementById('search-bar');
      if(!b) return;
      b.style.display = b.style.display === 'none' ? 'flex' : 'none';
      if(b.style.display === 'flex') document.getElementById('search-input').focus();
      else {{ document.getElementById('search-input').value=''; filterMessages(); }}
    }}
    function filterMessages(){{
      var q = (document.getElementById('search-input').value || '').toLowerCase().trim();
      var bubbles = document.querySelectorAll('.bubble');
      bubbles.forEach(function(b){{
        if(!q){{ b.style.opacity='1'; return; }}
        var txt = (b.textContent || '').toLowerCase();
        b.style.opacity = txt.indexOf(q) >= 0 ? '1' : '0.25';
      }});
    }}
    </script>
    """, title=g.name)


@app.route("/group/<int:gid>/react", methods=["POST"])
@login_required
def group_react(gid):
    g = db.session.get(Group, gid)
    if not g:
        return jsonify({"ok": False, "error": "not_found"}), 404
    me = get_group_member(gid, current_user.id)
    if not me:
        return jsonify({"ok": False, "error": "not_member"}), 403
    data = request.get_json(silent=True) or {}
    mid = data.get("message_id")
    emoji = (data.get("reaction") or "").strip()[:8]
    if not mid:
        return jsonify({"ok": False, "error": "no_mid"}), 400
    m = GroupMessage.query.filter_by(id=int(mid), group_id=gid).first()
    if not m:
        return jsonify({"ok": False, "error": "not_found"}), 404
    m.reaction = "" if m.reaction == emoji else emoji
    db.session.commit()
    return jsonify({"ok": True, "reaction": m.reaction})


@app.route("/group/<int:gid>/clear-reaction/<int:mid>", methods=["POST"])
@login_required
def group_clear_reaction(gid, mid):
    me = get_group_member(gid, current_user.id)
    if not me:
        return jsonify({"ok": False, "error": "not_member"}), 403
    m = GroupMessage.query.filter_by(id=mid, group_id=gid).first()
    if not m:
        return jsonify({"ok": False, "error": "not_found"}), 404
    m.reaction = ""
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/group/<int:gid>/delete-msg/<int:mid>", methods=["POST"])
@login_required
def group_delete_message(gid, mid):
    me = get_group_member(gid, current_user.id)
    if not me:
        return jsonify({"ok": False, "error": "not_member"}), 403
    m = GroupMessage.query.filter_by(id=mid, group_id=gid).first()
    if not m:
        return jsonify({"ok": False, "error": "not_found"}), 404
    is_admin = me.role in ("owner", "admin")
    if m.sender_id != current_user.id and not is_admin:
        return jsonify({"ok": False, "error": "forbidden"}), 403
    if m.media:
        try:
            p = os.path.join(app.config["GROUP_FOLDER"], m.media)
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass
    GroupMessage.query.filter_by(reply_to_id=mid).update({"reply_to_id": None}, synchronize_session=False)
    db.session.delete(m)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/group/<int:gid>/report", methods=["GET", "POST"])
@login_required
def group_report(gid):
    g = db.session.get(Group, gid)
    if not g:
        abort(404)
    if g.owner_id == current_user.id:
        flash("لا يمكنك إبلاغ مجموعتك.", "error")
        return redirect(url_for("group_view", gid=gid))
    if request.method == "POST":
        reason = request.form.get("reason", "").strip()
        existing = GroupReport.query.filter_by(reporter_id=current_user.id, group_id=gid).first()
        if existing:
            flash("أبلغت عن هذه المجموعة مسبقاً.", "error")
            return redirect(url_for("group_view", gid=gid))
        db.session.add(GroupReport(reporter_id=current_user.id, group_id=gid, reason=reason[:300]))
        db.session.commit()
        flash("تم إرسال الإبلاغ.", "success")
        return redirect(url_for("group_view", gid=gid))
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>🚨 إبلاغ عن مجموعة {g.name}</h2>
    <form method="POST"><label>سبب الإبلاغ</label>
    <textarea name="reason" maxlength="300" required placeholder="اشرح السبب..."></textarea>
    <button type="submit">إرسال الإبلاغ</button></form>
    <a class="link-center" href="{url_for('group_view', gid=gid)}">رجوع</a></div>""", title="إبلاغ")


# ═══════════════════════════════════════════════════════════════
# ANONYMOUS MESSAGES + REPORTS
# ═══════════════════════════════════════════════════════════════
@app.route("/message/<username>", methods=["GET", "POST"])
@login_required
def send_message(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    if target.id == current_user.id:
        flash("لا يمكنك إرسال رسالة لنفسك.", "error")
        return redirect(url_for("profile_me"))
    if is_blocked_between(current_user.id, target.id):
        flash("لا يمكن إرسال رسالة (يوجد حظر).", "error")
        return redirect(url_for("view_profile", username=target.username))
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        sender = request.form.get("sender_name", "").strip() or "مجهول"
        if not body:
            flash("الرسالة فارغة.", "error")
            return redirect(url_for("send_message", username=target.username))
        db.session.add(Message(receiver_id=target.id, body=body[:2000], sender_name=sender[:64]))
        db.session.commit()
        flash("تم إرسال الرسالة ✓", "success")
        return redirect(url_for("view_profile", username=target.username))
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>✉ رسالة مجهولة لـ @{target.username}</h2>
    <div class="privacy-note">🔒 لن يعرف المرسل هويتك إلا إذا كتبتها.</div>
    <form method="POST">
      <label>اسمك (اختياري)</label>
      <input name="sender_name" maxlength="64" placeholder="اتركه فارغًا للمجهول">
      <label>الرسالة</label>
      <textarea name="body" maxlength="2000" required placeholder="اكتب رسالتك..."></textarea>
      <button type="submit">إرسال</button></form>
    <a class="link-center" href="{url_for('view_profile', username=target.username)}">رجوع</a></div>""", title="رسالة مجهولة")


@app.route("/inbox")
@login_required
def inbox():
    messages = Message.query.filter_by(receiver_id=current_user.id).order_by(Message.created_at.desc()).all()
    rows = ""
    for m in messages:
        rows += f"""<div class="msg"><div class="meta">من: {m.sender_name} · {fmt_sd(m.created_at)}</div>
        <div class="body">{m.body}</div></div>"""
    if not rows:
        rows = '<p class="empty">لا رسائل مجهولة.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>📩 الرسائل المجهولة</h2>{rows}
    <a class="link-center" href="{url_for('profile_me')}">رجوع</a></div>""", title="الرسائل المجهولة")


@app.route("/report/<username>", methods=["GET", "POST"])
@login_required
def report_user(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    if target.id == current_user.id:
        flash("لا يمكنك إبلاغ نفسك.", "error")
        return redirect(url_for("profile_me"))
    if request.method == "POST":
        reason = request.form.get("reason", "").strip()
        existing = Report.query.filter_by(reporter_id=current_user.id, target_id=target.id).first()
        if existing:
            flash("أبلغت عن هذا المستخدم مسبقًا.", "error")
            return redirect(url_for("view_profile", username=target.username))
        db.session.add(Report(reporter_id=current_user.id, target_id=target.id, reason=reason[:300]))
        target.reports_count = (target.reports_count or 0) + 1
        db.session.commit()
        flash("تم إرسال الإبلاغ.", "success")
        return redirect(url_for("view_profile", username=target.username))
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>🚨 إبلاغ عن @{target.username}</h2>
    <div class="privacy-note">⚠️ البلاغات تُراجع يدوياً من فريق الدعم.</div>
    <form method="POST"><label>سبب الإبلاغ</label>
    <textarea name="reason" maxlength="300" required placeholder="اشرح سبب الإبلاغ..."></textarea>
    <button type="submit">إرسال الإبلاغ</button></form>
    <a class="link-center" href="{url_for('view_profile', username=target.username)}">رجوع</a></div>""", title="إبلاغ")


# ═══════════════════════════════════════════════════════════════
# SUPPORT PANEL
# ═══════════════════════════════════════════════════════════════
def support_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("support_authed"):
            return redirect(url_for("support_login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/support", methods=["GET", "POST"])
def support_login():
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if pwd == SUPPORT_PASSWORD:
            session["support_authed"] = True
            session.permanent = True
            flash("تم الدخول إلى لوحة الدعم.", "success")
            return redirect(url_for("support_dashboard"))
        flash("كلمة السر خاطئة.", "error")
        return redirect(url_for("support_login"))
    return render_page(FLASH_BLOCK + """
    <div class="card"><h2>🛡 لوحة الدعم</h2>
    <div class="privacy-note">🔒 هذه الصفحة محمية. أدخل كلمة سر الدعم.</div>
    <form method="POST"><label>كلمة سر الدعم</label>
    <div class="pw-wrap"><input name="password" id="supw" type="password" required autofocus>
    <button type="button" class="pw-toggle" onclick="togglePw('supw')">👁</button></div>
    <button type="submit">دخول</button></form>
    <a class="link-center" href="{{ url_for('login') }}">رجوع</a></div>""", title="الدعم")


@app.route("/support/logout")
def support_logout():
    session.pop("support_authed", None)
    flash("تم الخروج من لوحة الدعم.", "success")
    return redirect(url_for("login"))


@app.route("/support/dashboard")
@support_required
def support_dashboard():
    users_count = User.query.count()
    banned_count = User.query.filter_by(is_banned=True).count()
    review_count = User.query.filter_by(under_review=True).count()
    groups_count = Group.query.count()
    banned_groups = Group.query.filter_by(is_banned=True).count()
    reports_count = Report.query.count()
    group_reports = GroupReport.query.count()
    chat_reports_pending = ChatReport.query.filter_by(status="pending").count()
    chat_reports_total = ChatReport.query.count()
    total_reports = reports_count + group_reports
    s = get_site_settings()
    splash_status = "🟢 مُفعّلة" if s.splash_enabled else "⚪ متوقفة"
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>🛡 لوحة الدعم</h2>
    <div class="acct-box">
      <div class="acct-row"><span class="k">المستخدمون</span><span class="v">{users_count}</span></div>
      <div class="acct-row"><span class="k">المحظورون</span><span class="v">{banned_count}</span></div>
      <div class="acct-row"><span class="k">تحت المراجعة</span>
        <span class="v" style="color:#f59e0b;font-weight:800">{review_count}</span></div>
      <div class="acct-row"><span class="k">المجموعات</span><span class="v">{groups_count}</span></div>
      <div class="acct-row"><span class="k">مجموعات محظورة</span><span class="v">{banned_groups}</span></div>
      <div class="acct-row"><span class="k">بلاغات المستخدمين</span><span class="v">{reports_count}</span></div>
      <div class="acct-row"><span class="k">بلاغات المجموعات</span><span class="v">{group_reports}</span></div>
      <div class="acct-row"><span class="k">بلاغات الدردشة (معلّقة)</span>
        <span class="v" style="color:#f59e0b;font-weight:800">{chat_reports_pending}</span></div>
      <div class="acct-row"><span class="k">شاشة البداية</span>
        <span class="v" style="font-family:inherit">{splash_status}</span></div>
      <div class="acct-row" style="border-top:2px solid #c7d2fe;margin-top:6px;padding-top:10px">
        <span class="k" style="font-weight:800;color:#1e3a8a">إجمالي البلاغات</span>
        <span class="v" style="font-size:16px;color:#dc2626">{total_reports + chat_reports_total}</span></div>
    </div>
    <div class="actions">
      <a class="btn btn-primary" href="{url_for('support_chat_reports')}">
        💬 مراجعة بلاغات الدردشة ({chat_reports_pending} معلّق)
      </a>
      <a class="btn btn-primary" href="{url_for('support_reports')}">📋 كل البلاغات ({total_reports})</a>
      <a class="btn" href="{url_for('support_bulk_ban')}">🚫 حظر جماعي (متعدد)</a>
      <a class="btn" href="{url_for('support_splash')}">🎬 إعدادات شاشة البداية</a>
      <a class="btn" href="{url_for('support_users')}">👥 إدارة المستخدمين</a>
      <a class="btn" href="{url_for('support_groups')}">◉ إدارة المجموعات</a>
      <a class="btn btn-danger" href="{url_for('support_logout')}">تسجيل الخروج</a>
    </div></div>""", title="لوحة الدعم")


@app.route("/support/splash", methods=["GET", "POST"])
@support_required
def support_splash():
    s = get_site_settings()
    if request.method == "POST":
        s.splash_enabled = request.form.get("splash_enabled") == "1"
        s.splash_title = request.form.get("splash_title", "").strip()[:120]
        s.splash_subtitle = request.form.get("splash_subtitle", "").strip()[:200]
        s.splash_bg_color = request.form.get("splash_bg_color", "#0f172a").strip()[:20] or "#0f172a"
        s.splash_text_color = request.form.get("splash_text_color", "#ffffff").strip()[:20] or "#ffffff"
        s.splash_button_text = request.form.get("splash_button_text", "دخول").strip()[:60] or "دخول"
        try:
            s.splash_duration = int(request.form.get("splash_duration", "0") or 0)
        except ValueError:
            s.splash_duration = 0
        s.updated_at = now_utc_naive()
        db.session.commit()
        flash("تم حفظ إعدادات شاشة البداية.", "success")
        return redirect(url_for("support_splash"))
    preview_img = ""
    if s.splash_image:
        img_url = url_for("serve_upload", subpath=f"splash/{s.splash_image}")
        preview_img = f'<img class="splash-preview" src="{img_url}">'
        delete_btn = f"""
        <form method="POST" action="{url_for('support_splash_delete')}" style="margin-top:8px"
              onsubmit="return confirm('🗑 حذف صورة الشاشة الافتتاحية؟')">
          <button type="submit" class="btn btn-danger" style="width:100%">🗑 حذف الصورة الحالية</button>
        </form>"""
    else:
        preview_img = '<p class="empty" style="margin:14px 0">لا توجد صورة بعد.</p>'
        delete_btn = ""
    enabled_checked = "checked" if s.splash_enabled else ""
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>🎬 إعدادات شاشة البداية</h2>
    <div class="privacy-note">
      شاشة البداية تظهر لكل زائر جديد قبل دخول الموقع. يضغط زر الدخول ليتابع.
    </div>
    <form method="POST">
      <label class="switch-row">
        <span>🟢 تفعيل شاشة البداية</span>
        <input type="checkbox" name="splash_enabled" value="1" {enabled_checked}><span class="switch"></span></label>
      <label>العنوان الرئيسي</label>
      <input name="splash_title" value="{s.splash_title}" maxlength="120"
             placeholder="مرحباً بك في FBI SUDANESE">
      <label>الوصف الفرعي</label>
      <input name="splash_subtitle" value="{s.splash_subtitle}" maxlength="200"
             placeholder="منصة آمنة للتواصل والدردشة">
      <label>لون الخلفية</label>
      <input type="color" name="splash_bg_color" value="{s.splash_bg_color}" style="height:50px">
      <label>لون النص</label>
      <input type="color" name="splash_text_color" value="{s.splash_text_color}" style="height:50px">
      <label>نص الزر</label>
      <input name="splash_button_text" value="{s.splash_button_text}" maxlength="60"
             placeholder="دخول">
      <label>مدة الانتقال التلقائي (ثوان — 0 = يدوي)</label>
      <input type="number" name="splash_duration" value="{s.splash_duration}" min="0" max="60">
      <button type="submit" style="margin-top:16px">💾 حفظ الإعدادات</button>
    </form>
    <hr style="margin:20px 0;border:none;border-top:1px solid #e5e7eb">
    <h3 style="font-size:15px;font-weight:800;margin-bottom:8px">🖼 صورة الشاشة الافتتاحية</h3>
    {preview_img}
    {delete_btn}
    <form method="POST" action="{url_for('support_splash_upload')}" enctype="multipart/form-data" style="margin-top:8px">
      <label>رفع صورة جديدة</label>
      <input type="file" name="splash_image" accept="image/*" required>
      <button type="submit" class="btn btn-primary" style="margin-top:10px">📤 رفع الصورة</button>
    </form>
    <div style="display:flex;gap:8px;margin-top:14px;flex-wrap:wrap">
      <a class="btn btn-sm" href="{url_for('splash_view')}" target="_blank">👁 معاينة الشاشة</a>
      <a class="btn btn-sm" href="{url_for('support_dashboard')}">← رجوع للوحة</a>
    </div>
    </div>""", title="شاشة البداية")


@app.route("/support/splash/upload", methods=["POST"])
@support_required
def support_splash_upload():
    file = request.files.get("splash_image")
    if not file or not file.filename:
        flash("لم تختر صورة.", "error")
        return redirect(url_for("support_splash"))
    if not allowed_image(file.filename) or not check_image_magic(file):
        flash("صيغة الصورة غير مدعومة.", "error")
        return redirect(url_for("support_splash"))
    s = get_site_settings()
    if s.splash_image:
        try:
            old = os.path.join(app.config["SPLASH_FOLDER"], s.splash_image)
            if os.path.exists(old): os.remove(old)
        except OSError:
            pass
    ext = file.filename.rsplit(".", 1)[1].lower()
    fn = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(app.config["SPLASH_FOLDER"], fn))
    s.splash_image = fn
    s.updated_at = now_utc_naive()
    db.session.commit()
    flash("تم رفع الصورة.", "success")
    return redirect(url_for("support_splash"))


@app.route("/support/splash/delete", methods=["POST"])
@support_required
def support_splash_delete():
    s = get_site_settings()
    if s.splash_image:
        try:
            p = os.path.join(app.config["SPLASH_FOLDER"], s.splash_image)
            if os.path.exists(p): os.remove(p)
        except OSError:
            pass
        s.splash_image = ""
        s.updated_at = now_utc_naive()
        db.session.commit()
        flash("تم حذف صورة الشاشة الافتتاحية.", "success")
    else:
        flash("لا توجد صورة لحذفها.", "info")
    return redirect(url_for("support_splash"))


@app.route("/support/bulk-ban", methods=["GET", "POST"])
@support_required
def support_bulk_ban():
    if request.method == "POST":
        ids_str = request.form.get("user_ids", "").strip()
        note = request.form.get("admin_note", "").strip()[:300]
        if not ids_str:
            flash("لم تحدد أي مستخدم.", "error")
            return redirect(url_for("support_bulk_ban"))
        try:
            ids = [int(x) for x in re.split(r"[,\s]+", ids_str) if x.strip().isdigit()]
        except Exception:
            flash("قائمة IDs غير صالحة.", "error")
            return redirect(url_for("support_bulk_ban"))
        ids = list(set(ids))
        if not ids:
            flash("لا يوجد IDs صالحة.", "error")
            return redirect(url_for("support_bulk_ban"))
        success, fail = 0, 0
        logs = []
        for uid in ids:
            u = db.session.get(User, uid)
            if not u:
                fail += 1
                logs.append(f"❌ ID {uid}: غير موجود")
                continue
            if u.is_banned:
                fail += 1
                logs.append(f"⚠️ @{u.username}: محظور مسبقاً")
                continue
            uname = u.username
            ok = process_auto_ban(u)
            if ok:
                success += 1
                logs.append(f"🚫 @{uname}: محظور")
            else:
                fail += 1
                logs.append(f"❌ @{uname}: فشل الحظر")
        flash(f"تم الحظر الجماعي: {success} نجح، {fail} فشل.", "success")
        session["bulk_ban_logs"] = logs[-30:]
        return redirect(url_for("support_bulk_ban"))
    q = request.args.get("q", "").strip()
    query = User.query.filter(User.is_banned == False)
    if q:
        ql = q.lower().lstrip("@")
        query = query.filter(or_(User.username.ilike(f"%{ql}%"), User.public_id.ilike(f"%{ql}%")))
    users = query.order_by(User.created_at.desc()).limit(200).all()
    rows = ""
    for u in users:
        rows += f"""<label class="bulk-user-row" id="row-{u.id}">
          <input type="checkbox" value="{u.id}" onchange="toggleUser({u.id}, this)">
          <label style="flex:1;margin:0">
            <img class="avatar-sm" src="{avatar_url(u)}">
            <div style="flex:1;min-width:0">
              <div class="bu-name">{u.short_name}</div>
              <div class="bu-sub">@{u.username} · ID: {u.public_id} · بلاغات: {u.reports_count or 0}</div>
            </div>
          </label>
        </label>"""
    if not rows:
        rows = '<p class="empty">لا نتائج.</p>'
    logs_html = ""
    logs = session.pop("bulk_ban_logs", None)
    if logs:
        logs_html = '<div class="privacy-note" style="background:#f0fdf4;border-color:#bbf7d0;color:#166534;direction:ltr;text-align:left">'
        for line in logs:
            logs_html += f'<div>{line}</div>'
        logs_html += '</div>'
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>🚫 حظر جماعي متعدد</h2>
    <div class="privacy-note">
      حدد عدة مستخدمين لحظرهم دفعة واحدة. سيتم حذف كل بياناتهم.
    </div>
    <form method="GET" style="display:flex;gap:8px;margin-bottom:12px">
      <input name="q" value="{q}" placeholder="بحث بيوزر أو ID" style="flex:1;margin:0">
      <button type="submit" style="width:auto;padding:12px 20px;margin:0">بحث</button></form>
    <div style="max-height:50vh;overflow-y:auto;padding:4px;background:#f7f7f8;border-radius:10px;border:1px solid var(--border)">
      {rows}
    </div>
    <form method="POST" style="margin-top:16px" onsubmit="return confirmBulk()">
      <label>المستخدمون المحددون (IDs)</label>
      <textarea name="user_ids" id="user_ids" rows="3" placeholder="مثال: 1, 2, 5, 8"
                style="direction:ltr;font-family:monospace;font-size:13px"></textarea>
      <label>ملاحظة إدارية (اختياري)</label>
      <input name="admin_note" maxlength="300" placeholder="سبب الحظر الجماعي...">
      <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:12px;margin-top:10px">
        <div style="font-size:13px;font-weight:700;color:#991b1b">
          ⚠️ سيتم حظر <span id="count-display">0</span> مستخدم وحذف كل بياناتهم نهائياً!
        </div>
      </div>
      <button type="submit" class="btn btn-danger" style="margin-top:14px;width:100%;background:#dc2626;color:#fff">
        🚫 تنفيذ الحظر الجماعي
      </button>
    </form>
    {logs_html}
    <div style="display:flex;gap:8px;margin-top:14px;flex-wrap:wrap">
      <a class="btn btn-sm" href="{url_for('support_dashboard')}">← رجوع للوحة</a>
      <a class="btn btn-sm" href="{url_for('support_users')}">👥 إدارة المستخدمين</a>
    </div>
    </div>
    <script>
    function toggleUser(uid, cb){{
      var row = document.getElementById('row-' + uid);
      if (row) row.classList.toggle('selected', cb.checked);
      updateIds();
    }}
    function updateIds(){{
      var cbs = document.querySelectorAll('.bulk-user-row input[type="checkbox"]:checked');
      var ids = [];
      cbs.forEach(function(c){{ids.push(c.value);}});
      var ta = document.getElementById('user_ids');
      var manual = ta.dataset.manual === '1' ? ta.value : '';
      if (manual && !cbs.length) {{
        var cnt = (manual.match(/\\d+/g) || []).length;
        document.getElementById('count-display').textContent = cnt;
        return;
      }}
      ta.value = ids.join(', ');
      ta.dataset.manual = '0';
      document.getElementById('count-display').textContent = ids.length;
    }}
    document.getElementById('user_ids').addEventListener('input', function(){{
      this.dataset.manual = '1';
      var cnt = (this.value.match(/\\d+/g) || []).length;
      document.getElementById('count-display').textContent = cnt;
    }});
    function confirmBulk(){{
      var ta = document.getElementById('user_ids');
      var cnt = (ta.value.match(/\\d+/g) || []).length;
      if (cnt === 0) {{ alert('لم تحدد أي مستخدم.'); return false; }}
      return confirm('🚫 سيتم حظر ' + cnt + ' مستخدم نهائياً وحذف كل بياناتهم.\\nهل أنت متأكد؟');
    }}
    </script>""", title="حظر جماعي")


@app.route("/support/chat-reports")
@support_required
def support_chat_reports():
    reports = ChatReport.query.order_by(ChatReport.created_at.desc()).all()
    rows = ""
    for r in reports:
        rep = r.reporter
        tgt = r.target
        if not tgt:
            continue
        status_map = {
            "pending": '<span class="blocked-badge" style="background:#fef3c7;color:#92400e;border-color:#fcd34d">⏳ قيد المراجعة</span>',
            "upheld": '<span class="blocked-badge" style="background:#fee2e2;color:#991b1b">🚫 مؤيَّد — الحساب محظور</span>',
            "dismissed": '<span class="blocked-badge" style="background:#dcfce7;color:#166534;border-color:#86efac">✅ مرفوض</span>',
        }
        status_badge = status_map.get(r.status, r.status)
        target_state = ""
        if tgt.is_banned:
            target_state = '<span class="blocked-badge">محظور</span>'
        elif tgt.under_review:
            target_state = '<span class="blocked-badge" style="background:#fef3c7;color:#92400e;border-color:#fcd34d">⏳ تحت المراجعة</span>'
        actions = ""
        if r.status == "pending":
            upheld_url = url_for('support_review_chat_report', rid=r.id, decision='upheld')
            dismissed_url = url_for('support_review_chat_report', rid=r.id, decision='dismissed')
            actions = f"""
            <a class="btn btn-sm btn-danger" href="{upheld_url}"
               onclick="return confirm('🚫 تأييد البلاغ → حظر الحساب نهائياً؟')">🚫 تأييد + حظر</a>
            <a class="btn btn-sm btn-primary" href="{dismissed_url}"
               onclick="return confirm('✅ رفض البلاغ → إرجاع الحساب؟')">✅ رفض + إرجاع</a>"""
        elif r.status == "upheld":
            undo_url = url_for('support_review_chat_report', rid=r.id, decision='dismissed')
            actions = f'<a class="btn btn-sm" href="{undo_url}">↩ إعادة النظر</a>'
        else:
            undo_url = url_for('support_review_chat_report', rid=r.id, decision='upheld')
            actions = f'<a class="btn btn-sm" href="{undo_url}">↩ إعادة النظر</a>'
        reporter_html = "مجهول"
        if rep:
            reporter_html = f"""<a href="{url_for('support_user_detail', uid=rep.id)}" style="color:#2563eb;font-weight:700">@{rep.username}</a>
            <span style="color:#6b7280">(ID: {rep.public_id})</span>"""
        rows += f"""<div class="list-item" style="cursor:default;flex-wrap:wrap;border-right:4px solid #f59e0b">
          <img class="avatar-sm" src="{avatar_url(tgt)}" onclick="openAvatar('{avatar_url(tgt)}')">
          <div style="flex:1;min-width:240px">
            <div class="li-name">🎯 @{tgt.username} {target_state} {status_badge}</div>
            <div class="li-sub">ID: {tgt.public_id} · بلاغات: {tgt.reports_count or 0}</div>
            <div class="li-sub" style="margin-top:4px">🪪 المُبلِّغ: {reporter_html}</div>
            <div style="font-size:13px;margin-top:6px;color:#374151;background:#fef3c7;border-radius:6px;padding:6px 10px">
              💬 {html_escape_text(r.reason) or 'بدون سبب'}</div>
          </div>
          <div class="li-actions" style="flex-direction:column;gap:4px">
            <a class="btn btn-sm" href="{url_for('support_user_detail', uid=tgt.id)}">👁 فحص</a>
            {actions}
          </div></div>"""
    if not rows:
        rows = '<p class="empty">لا بلاغات دردشة. 🎉</p>'
    pending = ChatReport.query.filter_by(status="pending").count()
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>💬 بلاغات الدردشة ({len(reports)}) — معلّقة: {pending}</h2>
    {rows}
    <a class="link-center" href="{url_for('support_dashboard')}">← رجوع للوحة</a></div>""", title="بلاغات الدردشة")


@app.route("/support/chat-reports/<int:rid>/<decision>")
@support_required
def support_review_chat_report(rid, decision):
    r = db.session.get(ChatReport, rid)
    if not r:
        flash("البلاغ غير موجود.", "error")
        return redirect(url_for("support_chat_reports"))
    if decision not in ("upheld", "dismissed"):
        flash("قرار غير صالح.", "error")
        return redirect(url_for("support_chat_reports"))
    tgt = db.session.get(User, r.target_id)
    if not tgt:
        flash("المستخدم غير موجود.", "error")
        return redirect(url_for("support_chat_reports"))
    if decision == "upheld":
        r.status = "upheld"
        r.resolved_at = now_utc_naive()
        db.session.commit()
        process_auto_ban(tgt)
        flash(f"🚫 تم تأييد البلاغ وحظر @{tgt.original_username or tgt.username}.", "success")
    else:
        r.status = "dismissed"
        r.resolved_at = now_utc_naive()
        tgt.under_review = False
        tgt.review_reason = ""
        tgt.review_started_at = None
        db.session.commit()
        flash(f"✅ تم رفض البلاغ وإرجاع الحساب @{tgt.username}.", "success")
    return redirect(url_for("support_chat_reports"))


@app.route("/support/user/<int:uid>")
@support_required
def support_user_detail(uid):
    u = db.session.get(User, uid)
    if not u:
        flash("المستخدم غير موجود.", "error")
        return redirect(url_for("support_users"))
    reports_against = Report.query.filter_by(target_id=uid).order_by(Report.created_at.desc()).all()
    reports_by_me = Report.query.filter_by(reporter_id=uid).order_by(Report.created_at.desc()).all()
    chat_reports_against = ChatReport.query.filter_by(target_id=uid).order_by(ChatReport.created_at.desc()).all()
    statuses_count = Status.query.filter_by(user_id=uid).count()
    chat_sent = ChatMessage.query.filter_by(sender_id=uid).count()
    chat_received = ChatMessage.query.filter_by(receiver_id=uid).count()
    friends_count = Friendship.query.filter(
        Friendship.status == "accepted",
        or_(Friendship.requester_id == uid, Friendship.addressee_id == uid)).count()
    groups_owned = Group.query.filter_by(owner_id=uid).count()
    groups_member = GroupMember.query.filter_by(user_id=uid).count()
    msgs_inbox = Message.query.filter_by(receiver_id=uid).count()
    devices_count = Device.query.filter_by(user_id=uid).count()

    if u.is_banned:
        status_badge = '<span class="blocked-badge">🚫 محظور</span>'
    elif u.under_review:
        status_badge = '<span class="blocked-badge" style="background:#fef3c7;color:#92400e;border-color:#fcd34d">⏳ تحت المراجعة</span>'
    else:
        status_badge = '<span style="color:#16a34a;font-weight:700">✅ نشط</span>'

    reports_against_html = ""
    if reports_against:
        for r in reports_against:
            rep = db.session.get(User, r.reporter_id) if r.reporter_id else None
            reporter_txt = f'@{rep.username}' if rep else 'مجهول'
            reports_against_html += f"""<div class="msg">
              <div class="meta">🪪 المُبلِّغ: <b>{reporter_txt}</b> · {fmt_sd(r.created_at)}</div>
              <div class="body">💬 {html_escape_text(r.reason) or 'بدون سبب'}</div>
            </div>"""
    else:
        reports_against_html = '<p class="empty">لا بلاغات ضد هذا الحساب.</p>'

    reports_by_html = ""
    if reports_by_me:
        for r in reports_by_me:
            tgt = db.session.get(User, r.target_id)
            target_txt = f'@{tgt.username}' if tgt else 'مستخدم محذوف'
            reports_by_html += f"""<div class="msg">
              <div class="meta">🎯 أبلغ عن: <b>{target_txt}</b> · {fmt_sd(r.created_at)}</div>
              <div class="body">💬 {html_escape_text(r.reason) or 'بدون سبب'}</div>
            </div>"""
    else:
        reports_by_html = '<p class="empty">لم يرسل بلاغات.</p>'

    chat_reports_html = ""
    for cr in chat_reports_against:
        rep = cr.reporter
        status_map = {
            "pending": '⏳ قيد المراجعة',
            "upheld": '🚫 مؤيَّد',
            "dismissed": '✅ مرفوض',
        }
        sb = status_map.get(cr.status, cr.status)
        chat_reports_html += f"""<div class="msg">
          <div class="meta">🪪 من: <b>@{rep.username if rep else 'مجهول'}</b> · {fmt_sd(cr.created_at)} {sb}</div>
          <div class="body">💬 {html_escape_text(cr.reason) or 'بدون سبب'}</div>
        </div>"""
    if not chat_reports_html:
        chat_reports_html = '<p class="empty">لا بلاغات دردشة ضد هذا الحساب.</p>'

    ban_btn = ""
    if u.is_banned:
        ban_btn = f'<a class="btn btn-primary" href="{url_for("support_unban_user", uid=u.id)}">✅ إلغاء الحظر</a>'
    else:
        ban_btn = (f'<a class="btn btn-danger" href="{url_for("support_ban_user", uid=u.id)}" '
                   f'onclick="return confirm(\'حظر هذا المستخدم؟\')">🚫 حظر نهائي</a>')

    release_review_btn = ""
    if u.under_review:
        release_review_btn = (f'<a class="btn btn-primary" href="{url_for("support_release_review", uid=u.id)}" '
                              f'onclick="return confirm(\'رفع تعليق المراجعة؟\')">✅ رفع المراجعة</a>')

    return render_page(FLASH_BLOCK + f"""
    <div class="card center">
      <img class="avatar" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
      <div class="name">{u.short_name}</div>
      <div class="username">@{u.username}</div>
      <div class="uid">ID: {u.public_id} {copy_btn_html(u.public_id, "نسخ", small=True)}</div>
      <div style="margin-top:8px">{status_badge}</div>
      {f'<div class="privacy-note" style="margin-top:10px">⏳ السبب: {html_escape_text(u.review_reason)}</div>' if u.under_review else ''}
      <div class="acct-box" style="margin-top:12px">
        <div class="acct-row"><span class="k">USERNAME</span><span class="v">@{u.username} {copy_btn_html(u.username, "نسخ", small=True)}</span></div>
        <div class="acct-row"><span class="k">ID</span><span class="v">{u.public_id} {copy_btn_html(u.public_id, "نسخ", small=True)}</span></div>
        <div class="acct-row"><span class="k">NICKNAME</span><span class="v" style="font-family:inherit">{u.nickname or '—'}</span></div>
        <div class="acct-row"><span class="k">JOINED (SD)</span><span class="v" style="font-family:inherit">{fmt_sd(u.created_at)}</span></div>
        <div class="acct-row"><span class="k">LAST SEEN (SD)</span><span class="v" style="font-family:inherit">{fmt_sd(u.last_seen)}</span></div>
        <div class="acct-row"><span class="k">REPORTS</span><span class="v" style="color:#dc2626;font-weight:800">{u.reports_count or 0}</span></div>
      </div>
      <div class="actions">
        <a class="btn" href="{url_for('view_profile', username=u.username)}">👤 فتح البروفايل</a>
        {release_review_btn}
        {ban_btn}
        <a class="btn" href="{url_for('support_users')}">← رجوع</a>
      </div>
    </div>
    <div class="card"><h2>📊 النشاط</h2>
    <div class="acct-box" style="direction:rtl;text-align:right">
      <div class="acct-row"><span class="k">الحالات</span><span class="v" style="font-family:inherit">{statuses_count}</span></div>
      <div class="acct-row"><span class="k">رسائل دردشة</span><span class="v" style="font-family:inherit">{chat_sent}</span></div>
      <div class="acct-row"><span class="k">الأصدقاء</span><span class="v" style="font-family:inherit">{friends_count}</span></div>
      <div class="acct-row"><span class="k">مجموعات يملكها</span><span class="v" style="font-family:inherit">{groups_owned}</span></div>
      <div class="acct-row"><span class="k">مجموعات عضو</span><span class="v" style="font-family:inherit">{groups_member}</span></div>
      <div class="acct-row"><span class="k">الأجهزة</span><span class="v" style="font-family:inherit">{devices_count}</span></div>
    </div></div>
    <div class="card"><h2>💬 بلاغات الدردشة ({len(chat_reports_against)})</h2>{chat_reports_html}</div>
    <div class="card"><h2>🚨 البلاغات العادية ({len(reports_against)})</h2>{reports_against_html}</div>
    <div class="card"><h2>📤 أرسل ({len(reports_by_me)})</h2>{reports_by_html}</div>
    """, title=f"تفاصيل @{u.username}")


@app.route("/support/release-review/<int:uid>")
@support_required
def support_release_review(uid):
    u = db.session.get(User, uid)
    if not u:
        flash("المستخدم غير موجود.", "error")
        return redirect(url_for("support_users"))
    u.under_review = False
    u.review_reason = ""
    u.review_started_at = None
    db.session.commit()
    flash(f"✅ تم رفع تعليق المراجعة عن @{u.username}.", "success")
    return redirect(request.referrer or url_for("support_users"))


@app.route("/support/reports")
@support_required
def support_reports():
    filter_type = request.args.get("type", "all")
    user_reports = []
    if filter_type in ("all", "users"):
        user_reports = Report.query.order_by(Report.created_at.desc()).all()
    group_reports = []
    if filter_type in ("all", "groups"):
        group_reports = GroupReport.query.order_by(GroupReport.created_at.desc()).all()
    total = len(user_reports) + len(group_reports)
    users_html = ""
    if filter_type in ("all", "users"):
        if user_reports:
            users_html += f"""<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;
                padding:10px 14px;margin-bottom:12px;font-weight:800;color:#1e40af;font-size:14px">
                👤 بلاغات المستخدمين ({len(user_reports)})</div>"""
            for r in user_reports:
                reporter = db.session.get(User, r.reporter_id) if r.reporter_id else None
                target = db.session.get(User, r.target_id)
                if not target:
                    continue
                target_status = '<span class="blocked-badge">محظور</span>' if target.is_banned else ""
                target_ban_btn = (f'<a class="btn btn-sm btn-primary" href="{url_for("support_unban_user", uid=target.id)}">✅ إلغاء حظر الهدف</a>'
                                  if target.is_banned else
                                  f'<a class="btn btn-sm btn-danger" href="{url_for("support_ban_user", uid=target.id)}" onclick="return confirm(\'حظر الهدف؟\')">🚫 حظر الهدف</a>')
                users_html += f"""<div class="list-item" style="cursor:default;flex-wrap:wrap;border-right:4px solid #2563eb">
                  <img class="avatar-sm" src="{avatar_url(target)}">
                  <div style="flex:1;min-width:200px">
                    <div class="li-name">🎯 @{target.username} {target_status}</div>
                    <div class="li-sub">المُبلِّغ: {('@' + reporter.username) if reporter else 'مجهول'} · {fmt_sd(r.created_at)}</div>
                    <div style="font-size:13px;margin-top:6px;color:#374151;background:#fef3c7;border-radius:6px;padding:6px 10px">
                      💬 {html_escape_text(r.reason) or 'بدون سبب'}</div>
                  </div>
                  <div class="li-actions" style="flex-direction:column;gap:4px">
                    <a class="btn btn-sm" href="{url_for('support_user_detail', uid=target.id)}">👁 فحص</a>
                    {target_ban_btn}
                    <a class="btn btn-sm" href="{url_for('support_dismiss_report', rid=r.id)}">✖ تجاهل</a>
                  </div></div>"""
    groups_html = ""
    if filter_type in ("all", "groups"):
        if group_reports:
            groups_html += f"""<div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:10px;
                padding:10px 14px;margin-bottom:12px;font-weight:800;color:#92400e;font-size:14px">
                ◉ بلاغات المجموعات ({len(group_reports)})</div>"""
            for r in group_reports:
                reporter = db.session.get(User, r.reporter_id) if r.reporter_id else None
                g = db.session.get(Group, r.group_id)
                if not g:
                    continue
                group_status = '<span class="blocked-badge">محظورة</span>' if g.is_banned else ""
                if g.is_banned:
                    ban_btn = f'<a class="btn btn-sm btn-primary" href="{url_for("support_unban_group", gid=g.id)}">✅ إلغاء</a>'
                else:
                    ban_btn = f'<a class="btn btn-sm btn-danger" href="{url_for("support_ban_group", gid=g.id)}">🚫 حظر</a>'
                groups_html += f"""<div class="list-item" style="cursor:default;flex-wrap:wrap;border-right:4px solid #f59e0b">
                  <img class="avatar-sm" src="{group_avatar_url(g)}" style="border-radius:12px">
                  <div style="flex:1;min-width:200px">
                    <div class="li-name">◉ {g.name} {group_status}</div>
                    <div class="li-sub">المُبلِّغ: {('@' + reporter.username) if reporter else 'مجهول'} · {fmt_sd(r.created_at)}</div>
                    <div style="font-size:13px;margin-top:6px;background:#fef3c7;border-radius:6px;padding:6px 10px">
                      💬 {html_escape_text(r.reason) or 'بدون سبب'}</div>
                  </div>
                  <div class="li-actions" style="flex-direction:column;gap:4px">
                    <a class="btn btn-sm" href="{url_for('group_view', gid=g.id)}">◉ عرض</a>
                    {ban_btn}
                    <a class="btn btn-sm" href="{url_for('support_dismiss_group_report', rid=r.id)}">✖ تجاهل</a>
                  </div></div>"""
    def filt_btn(key, label, count):
        active = filter_type == key
        style = "background:#111827;color:#fff;border-color:#111827" if active else "background:#fff;color:#374151"
        return f'<a class="btn btn-sm" href="{url_for("support_reports", type=key)}" style="{style};font-weight:700">{label} ({count})</a>'
    user_count = Report.query.count()
    group_count = GroupReport.query.count()
    filter_bar = f"""<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px">
      {filt_btn('all', '📋 الكل', user_count + group_count)}
      {filt_btn('users', '👤 مستخدمين', user_count)}
      {filt_btn('groups', '◉ مجموعات', group_count)}</div>"""
    if filter_type == "all":
        body_content = users_html + groups_html
        if not body_content:
            body_content = '<p class="empty">لا بلاغات.</p>'
    elif filter_type == "users":
        body_content = users_html or '<p class="empty">لا بلاغات مستخدمين.</p>'
    else:
        body_content = groups_html or '<p class="empty">لا بلاغات مجموعات.</p>'
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>📋 كل البلاغات ({total})</h2>
    {filter_bar}{body_content}
    <a class="link-center" href="{url_for('support_dashboard')}">← رجوع</a></div>""", title="البلاغات")


@app.route("/support/ban-user/<int:uid>")
@support_required
def support_ban_user(uid):
    u = db.session.get(User, uid)
    if not u:
        flash("المستخدم غير موجود.", "error")
        return redirect(url_for("support_users"))
    if u.is_banned:
        flash(f"@{u.username} محظور بالفعل.", "info")
        return redirect(request.referrer or url_for("support_reports"))
    saved_username = u.username
    ok = process_auto_ban(u)
    if ok:
        flash(f"🚫 تم حظر @{saved_username} وحذف كل بياناته.", "success")
    else:
        flash(f"⚠️ فشل حظر @{saved_username}.", "error")
    return redirect(request.referrer or url_for("support_reports"))


@app.route("/support/unban-user/<int:uid>")
@support_required
def support_unban_user(uid):
    u = db.session.get(User, uid)
    if not u:
        flash("المستخدم غير موجود.", "error")
        return redirect(url_for("support_users"))
    u.is_banned = False
    u.pending_username_release = False
    u.username_release_at = None
    u.under_review = False
    u.review_reason = ""
    u.review_started_at = None
    if u.original_username and not User.query.filter_by(username=u.original_username).first():
        u.username = u.original_username
    db.session.commit()
    flash(f"✅ تم إلغاء حظر @{u.username}.", "success")
    return redirect(request.referrer or url_for("support_users"))


@app.route("/support/dismiss-report/<int:rid>")
@support_required
def support_dismiss_report(rid):
    r = db.session.get(Report, rid)
    if not r:
        flash("البلاغ غير موجود.", "error")
        return redirect(url_for("support_reports"))
    target = db.session.get(User, r.target_id)
    if target:
        target.reports_count = max(0, (target.reports_count or 0) - 1)
    db.session.delete(r)
    db.session.commit()
    flash("تم تجاهل البلاغ.", "success")
    return redirect(request.referrer or url_for("support_reports"))


@app.route("/support/ban-group/<int:gid>")
@support_required
def support_ban_group(gid):
    g = db.session.get(Group, gid)
    if not g:
        flash("المجموعة غير موجودة.", "error")
        return redirect(url_for("support_groups"))
    g.is_banned = True
    db.session.commit()
    flash(f"تم حظر المجموعة {g.name}.", "success")
    return redirect(request.referrer or url_for("support_reports"))


@app.route("/support/unban-group/<int:gid>")
@support_required
def support_unban_group(gid):
    g = db.session.get(Group, gid)
    if not g:
        flash("المجموعة غير موجودة.", "error")
        return redirect(url_for("support_groups"))
    g.is_banned = False
    db.session.commit()
    flash(f"تم إلغاء حظر المجموعة {g.name}.", "success")
    return redirect(request.referrer or url_for("support_groups"))


@app.route("/support/dismiss-group-report/<int:rid>")
@support_required
def support_dismiss_group_report(rid):
    r = db.session.get(GroupReport, rid)
    if not r:
        flash("البلاغ غير موجود.", "error")
        return redirect(url_for("support_reports"))
    db.session.delete(r)
    db.session.commit()
    flash("تم تجاهل البلاغ.", "success")
    return redirect(request.referrer or url_for("support_reports"))


@app.route("/support/users")
@support_required
def support_users():
    q = request.args.get("q", "").strip()
    query = User.query
    if q:
        ql = q.lower().lstrip("@")
        query = query.filter(or_(User.username.ilike(f"%{ql}%"), User.public_id.ilike(f"%{ql}%")))
    users = query.order_by(User.created_at.desc()).limit(100).all()
    rows = ""
    for u in users:
        if u.is_banned:
            status = '<span class="blocked-badge">محظور</span>'
        elif u.under_review:
            status = '<span class="blocked-badge" style="background:#fef3c7;color:#92400e;border-color:#fcd34d">⏳ مراجعة</span>'
        else:
            status = '<span style="color:#16a34a">نشط</span>'
        if u.is_banned:
            action = f'<a class="btn btn-sm btn-primary" href="{url_for("support_unban_user", uid=u.id)}">✅ إلغاء</a>'
        else:
            action = f'<a class="btn btn-sm btn-danger" href="{url_for("support_ban_user", uid=u.id)}" onclick="return confirm(\'حظر؟\')">🚫 حظر</a>'
        rows += f"""<div class="list-item" style="cursor:default">
          <img class="avatar-sm" src="{avatar_url(u)}">
          <div style="flex:1;min-width:0">
            <div class="li-name">{u.short_name} {status}</div>
            <div class="li-sub">@{u.username} · ID: {u.public_id} · بلاغات: {u.reports_count or 0}</div>
          </div>
          <div class="li-actions">
            {copy_btn_html(u.username, "يوزر", small=True)}
            {copy_btn_html(u.public_id, "ID", small=True)}
            <a class="btn btn-sm" href="{url_for('support_user_detail', uid=u.id)}">👁</a>
            {action}
          </div></div>"""
    if not rows:
        rows = '<p class="empty">لا نتائج.</p>'
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>👥 إدارة المستخدمين</h2>
    <form method="GET" style="display:flex;gap:8px;margin-bottom:12px">
      <input name="q" value="{q}" placeholder="بحث" style="flex:1;margin:0">
      <button type="submit" style="width:auto;padding:12px 20px;margin:0">بحث</button></form>
    {rows}
    <a class="link-center" href="{url_for('support_dashboard')}">← رجوع</a></div>""", title="إدارة المستخدمين")


@app.route("/support/groups")
@support_required
def support_groups():
    q = request.args.get("q", "").strip()
    query = Group.query
    if q:
        ql = q.lower().lstrip("@")
        query = query.filter(or_(Group.name.ilike(f"%{ql}%"), Group.public_id.ilike(f"%{ql}%")))
    groups = query.order_by(Group.created_at.desc()).limit(100).all()
    rows = ""
    for g in groups:
        status = '<span class="blocked-badge">محظورة</span>' if g.is_banned else '<span style="color:#16a34a">نشطة</span>'
        if g.is_banned:
            action = f'<a class="btn btn-sm btn-primary" href="{url_for("support_unban_group", gid=g.id)}">✅</a>'
        else:
            action = f'<a class="btn btn-sm btn-danger" href="{url_for("support_ban_group", gid=g.id)}">🚫</a>'
        rows += f"""<div class="list-item" style="cursor:default">
          <img class="avatar-sm" src="{group_avatar_url(g)}" style="border-radius:12px">
          <div style="flex:1;min-width:0">
            <div class="li-name">{g.name} {status}</div>
            <div class="li-sub">ID: {g.public_id} · {GroupMember.query.filter_by(group_id=g.id).count()} عضو</div>
          </div>
          <div class="li-actions">
            {copy_btn_html(g.public_id, "ID", small=True)}
            <a class="btn btn-sm" href="{url_for('group_view', gid=g.id)}">عرض</a>
            {action}
          </div></div>"""
    if not rows:
        rows = '<p class="empty">لا نتائج.</p>'
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>◉ إدارة المجموعات</h2>
    <form method="GET" style="display:flex;gap:8px;margin-bottom:12px">
      <input name="q" value="{q}" placeholder="بحث" style="flex:1;margin:0">
      <button type="submit" style="width:auto;padding:12px 20px;margin:0">بحث</button></form>
    {rows}
    <a class="link-center" href="{url_for('support_dashboard')}">← رجوع</a></div>""", title="إدارة المجموعات")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
