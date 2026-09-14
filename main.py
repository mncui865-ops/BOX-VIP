# -*- coding: utf-8 -*-
"""
FBI SUDANESE — v15.0 (Glowing Shapes Edition — No Channels)
- ✅ أشكال SVG مضيئة بدل الإيموجيات
- ✅ شارات توثيق متحركة
- ✅ إصلاح @username بجانب الاسم
- ✅ نقطة واحدة فقط (خضراء/سوداء) على الصورة
- ✅ حظر دائم فوري — يمسح كل البيانات مباشرة من الموقع ولوحة الدعم
- ❌ القنوات محذوفة نهائياً
- ✨ Toast notifications + نسخ رابط + Scroll-to-bottom
- ✨ Keyboard shortcuts + Haptic feedback
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


def utc_now(): return datetime.now(UTC_TZ).replace(tzinfo=None)
def now_utc_naive(): return utc_now()


def time_ago_sd(dt):
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
                "uploads/chats", "uploads/groups", "uploads/covers"]:
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
COVER_DIR = os.path.join(UPLOAD_DIR, "covers")
for d in (AVATAR_DIR, STATUS_DIR, CHAT_DIR, GROUP_DIR, COVER_DIR):
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
app.config["COVER_FOLDER"] = COVER_DIR
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
    if head.startswith(b"OggS"): return True
    if head.startswith(b"fLaC"): return True
    if len(head) >= 12 and head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"M4A ", b"M4B ", b"mp42", b"isom", b"iso2"): return True
    if head.startswith(b"#!AMR"): return True
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


def record_login_attempt(ip): _login_attempts[ip].append(time.time())


CODE_ALPHABET = string.ascii_uppercase + string.digits


def gen_recovery_code(): return "".join(secrets.choice(CODE_ALPHABET) for _ in range(20))
def hash_recovery_code(code): return hashlib.sha256(code.strip().upper().encode()).hexdigest()
def format_code(code):
    c = code.strip().upper()
    return "-".join(c[i:i + 4] for i in range(0, len(c), 4))


def gen_public_id(): return "".join(random.choices(string.digits, k=8))
def gen_device_token(): return secrets.token_urlsafe(32)


# ═══════════════════════════════════════════════════════════════
# ألوان التوثيق — موسّعة
# ═══════════════════════════════════════════════════════════════
VERIFY_COLORS = [
    ("#1d9bf0", "أزرق تلغرام"), ("#1877F2", "أزرق فيسبوك"),
    ("#25D366", "أخضر واتساب"), ("#FF0000", "أحمر يوتيوب"),
    ("#E4405F", "وردي إنستغرام"), ("#FFD700", "ذهبي"),
    ("#C0C0C0", "فضي"), ("#CD7F32", "برونزي"),
    ("#8B5CF6", "بنفسجي"), ("#F97316", "برتقالي"),
    ("#14B8A6", "فيروزي"), ("#EC4899", "زهري"),
    ("#EF4444", "أحمر"), ("#22C55E", "أخضر"),
    ("#EAB308", "أصفر"), ("#6366F1", "نيلي"),
    ("#06B6D4", "سماوي"), ("#84CC16", "ليموني"),
    ("#F59E0B", "عنبري"), ("#F43F5E", "وردي غامق"),
    ("#D946EF", "فوشيا"), ("#7C3AED", "بنفسجي غامق"),
    ("#0EA5E9", "سماوي فاتح"), ("#10B981", "زمردي"),
    ("#64748B", "رمادي"), ("#000000", "أسود"),
    ("#FFFFFF", "أبيض"), ("#8B0000", "أحمر داكن"),
    ("#006400", "أخضر داكن"), ("#000080", "كحلي"),
    ("#800080", "أرجواني"), ("#4B0082", "نيلي داكن"),
    ("#2F4F4F", "رمادي داكن"), ("#191970", "أزرق ليلي"),
    ("#FF69B4", "وردي فاتح"), ("#00CED1", "تركوازي"),
    ("#FF4500", "برتقالي محمر"), ("#32CD32", "أخضر ليموني"),
    ("#9370DB", "بنفسجي متوسط"), ("#FFB6C1", "وردي باهت"),
    ("#DC143C", "قرمزي"), ("#00FA9A", "أخضر ربيعي"),
    ("#FF1493", "وردي عميق"), ("#FF6B6B", "مرجاني"),
    ("#4ECDC4", "تركوازي فاتح"), ("#45B7D1", "سماوي متوسط"),
    ("#96CEB4", "أخضر فاتح"), ("#FFEAA7", "كريمي"),
    ("#DDA0DD", "برقوقي"), ("#98D8C8", "نعناعي"),
    ("#F7DC6F", "أصفر فاتح"), ("#BB8FCE", "لافندر"),
    ("#85C1E9", "أزرق فاتح"), ("#F8B500", "عسلي"),
    ("#FF7F50", "سلموني"), ("#6A5ACD", "أزرق بنفسجي"),
    ("#20B2AA", "أخضر بحري"), ("#FFB347", "برتقالي فاتح"),
    ("#87CEEB", "سماوي"), ("#F0E68C", "خاكي"),
    ("linear-gradient(45deg,#ff0000,#ff7f00,#ffff00,#00ff00,#0000ff,#4b0082,#9400d3)", "قوس قزح"),
    ("linear-gradient(45deg,#ff6b6b,#feca57)", "غروب"),
    ("linear-gradient(45deg,#0061ff,#60efff)", "محيط"),
    ("linear-gradient(45deg,#134e5e,#71b280)", "غابة"),
    ("linear-gradient(45deg,#f12711,#f5af19)", "نار"),
    ("linear-gradient(45deg,#83a4d4,#b6fbff)", "جليد"),
    ("linear-gradient(45deg,#141e30,#243b55)", "ملكي"),
    ("linear-gradient(45deg,#ff0844,#ffb199)", "حب"),
    ("linear-gradient(45deg,#360033,#0b8793)", "مجرة"),
    ("linear-gradient(45deg,#ffe259,#ffa751)", "مانجو"),
    ("linear-gradient(45deg,#eb3349,#f45c43)", "كرز"),
    ("linear-gradient(45deg,#348f50,#56b4d3)", "زمردة"),
    ("linear-gradient(45deg,#9d50bb,#6e48aa)", "جمشت"),
    ("linear-gradient(45deg,#f7971e,#ffd200)", "ذهب"),
    ("linear-gradient(45deg,#00f260,#0575e6)", "نيون"),
    ("linear-gradient(45deg,#fc466b,#3f5efb)", "أرجواني وردي"),
    ("linear-gradient(45deg,#11998e,#38ef7d)", "أخضر نيون"),
    ("linear-gradient(45deg,#fc4a1a,#f7b733)", "برتقالي ذهبي"),
    ("linear-gradient(45deg,#00b4db,#0083b0)", "أزرق عميق"),
    ("linear-gradient(45deg,#e96443,#904e95)", "بنفسجي محمر"),
]

VERIFY_ICONS = [
    "✓", "✔", "☑", "☒",
    "★", "☆", "✩", "✪", "✫", "✬", "✭", "✮", "✯", "✰",
    "✧", "✦", "⋆", "⍟", "⚝", "⭑", "⭒",
    "♛", "♔", "♕", "♚",
    "❖", "◆", "◇", "◈", "◊",
    "●", "○", "◉", "◎", "◍", "◌", "◦", "◯",
    "■", "□", "▣", "▤", "▪", "▫",
    "▲", "▼", "◀", "▶", "△", "▽", "◢", "◣", "◤", "◥",
    "❀", "✿", "❁", "❃", "❊", "❋", "✾", "✽",
    "✙", "✚", "✛", "✜", "✝", "✞", "✟", "✠", "✡",
    "☨", "☩", "☪", "☯", "☸", "☮", "☭",
    "⚕", "⚖", "⚗", "⚙", "⚛", "⚜", "♰", "♱",
    "➤", "➔", "➜", "➝", "➞", "➟", "➠", "➡", "➢", "➣",
    "➥", "➦", "➧", "➨", "➩", "➪", "➫", "➬", "➭", "➮",
    "➯", "➱", "➲", "➳", "➴", "➵", "➶", "➷", "➸", "➹",
    "❂", "❈", "❉", "❍", "❏", "❑", "❒",
    "❘", "❙", "❚", "❛", "❜", "❝", "❞", "❟", "❠", "❡",
    "❢", "❣", "❤", "❥", "❦", "❧",
    "❨", "❩", "❪", "❫", "❬", "❭", "❮", "❯", "❰", "❱",
    "❲", "❳", "❴", "❵",
    "⌘", "⌬", "⌖", "⌚", "⌛", "⏣", "⏥",
    "⏩", "⏪", "⏫", "⏬", "⏭", "⏮", "⏯", "⏰", "⏱", "⏲", "⏳",
    "⏴", "⏵", "⏶", "⏷", "⏸", "⏹", "⏺",
    "▬", "▭", "▮", "▯", "▰", "▱",
    "◐", "◑", "◒", "◓", "◔", "◕", "◖", "◗",
    "◘", "◙", "◜", "◝", "◞", "◟", "◠", "◡",
    "◧", "◨", "◩", "◪", "◫", "◬", "◭", "◮",
    "∞", "∑", "∏", "√", "∫", "≈", "≠", "≤", "≥", "±", "÷", "×",
    "$", "€", "£", "¥", "₿", "₹", "₽", "₩",
    "Ω", "Δ", "Θ", "Λ", "Ξ", "Π", "Σ", "Φ", "Ψ", "α", "β", "γ", "δ", "ε", "λ", "μ", "π", "σ", "φ", "ω",
]


# ═══════════════════════════════════════════════════════════════
# ✅ أيقونات SVG مضيئة
# ═══════════════════════════════════════════════════════════════
GLOW_ICONS = {
    "home": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    "chat": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    "groups": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/></svg>',
    "users": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "user": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "attach": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>',
    "send": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>',
    "image": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
    "video": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>',
    "audio": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
    "heart": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>',
    "thumb": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>',
    "laugh": '<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2" stroke="#000" stroke-width="1.5" fill="none" stroke-linecap="round"/><line x1="9" y1="9" x2="9.01" y2="9" stroke="#000" stroke-width="2" stroke-linecap="round"/><line x1="15" y1="9" x2="15.01" y2="9" stroke="#000" stroke-width="2" stroke-linecap="round"/></svg>',
    "wow": '<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/><circle cx="9" cy="9" r="1.5" fill="#000"/><circle cx="15" cy="9" r="1.5" fill="#000"/><circle cx="12" cy="15" r="2" fill="#000"/></svg>',
    "sad": '<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/><path d="M8 16s1.5-2 4-2 4 2 4 2" stroke="#000" stroke-width="1.5" fill="none" stroke-linecap="round"/><line x1="9" y1="9" x2="9.01" y2="9" stroke="#000" stroke-width="2" stroke-linecap="round"/><line x1="15" y1="9" x2="15.01" y2="9" stroke="#000" stroke-width="2" stroke-linecap="round"/></svg>',
    "pray": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L9 7l-4 1 3 4-1 5 5-3 5 3-1-5 3-4-4-1z"/></svg>',
    "reply": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 17 4 12 9 7"/><path d="M20 18v-2a4 4 0 0 0-4-4H4"/></svg>',
    "star": '<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    "star_outline": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    "trash": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
    "alert": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "search": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    "close": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    "plus": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    "check": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    "archive": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>',
    "mute": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>',
    "camera": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>',
    "edit": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z"/></svg>',
    "shield": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "inbox": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>',
    "eye": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>',
    "clock": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "flame": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2c-2 5-5 7-5 11a5 5 0 0 0 10 0c0-2-1-3-1-3s-1 1-2 1c0-4-2-6-2-9z"/></svg>',
    "mood": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>',
    "back": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>',
    "logout": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
    "lock": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
    "settings": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    "link": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
    "arrow_down": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>',
    "bell": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>',
}


def glow_icon(name, size=20, color="currentColor"):
    svg = GLOW_ICONS.get(name, "")
    if not svg: return ""
    return f'<span class="glow-icon" style="--glow-size:{size}px;color:{color};width:{size}px;height:{size}px">{svg}</span>'


def glow_reaction_icon(name):
    svg = GLOW_ICONS.get(name, "")
    if not svg: return ""
    return f'<span class="glow-react">{svg}</span>'


# ═══════════════════════════════════════════════════════════════
# MODELS (بدون Channel/ChannelFollower/ChannelPost/ChannelPostReaction)
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
    profile_cover = db.Column(db.String(300), default="")
    is_banned = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    verified_color = db.Column(db.String(200), default="#1d9bf0")
    verified_icon = db.Column(db.String(10), default="✓")
    created_at = db.Column(db.DateTime, default=utc_now)
    last_seen = db.Column(db.DateTime, default=utc_now)
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
    mood_text = db.Column(db.String(64), default="")
    custom_title = db.Column(db.String(32), default="")
    title_color = db.Column(db.String(20), default="#6b7280")
    chat_wallpaper = db.Column(db.String(300), default="")
    favorite_emojis = db.Column(db.String(200), default="❤️,👍,😂,😮,😢,🙏")
    default_disappear_seconds = db.Column(db.Integer, default=0)
    privacy_last_seen = db.Column(db.String(10), default="everyone")
    privacy_profile_photo = db.Column(db.String(10), default="everyone")
    privacy_about = db.Column(db.String(10), default="everyone")
    notifications_enabled = db.Column(db.Boolean, default=True)
    read_receipts = db.Column(db.Boolean, default=True)

    messages = db.relationship("Message", backref="receiver", lazy=True, foreign_keys="Message.receiver_id")
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

    @property
    def fav_emoji_list(self):
        return [e.strip() for e in (self.favorite_emojis or "").split(",") if e.strip()]


class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_agent = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=utc_now)
    last_seen = db.Column(db.DateTime, default=utc_now)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    sender_name = db.Column(db.String(64), default="مجهول")
    created_at = db.Column(db.DateTime, default=utc_now)


class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    text = db.Column(db.String(300), default="")
    caption = db.Column(db.String(300), default="")
    media = db.Column(db.String(300), default="")
    media_type = db.Column(db.String(10), default="")
    privacy = db.Column(db.String(10), default="public")
    show_viewers = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    user = db.relationship("User", backref="statuses")
    views = db.relationship("StatusView", backref="status", lazy=True, cascade="all, delete-orphan")


class StatusView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status_id = db.Column(db.Integer, db.ForeignKey("status.id"), nullable=False)
    viewer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    viewed_at = db.Column(db.DateTime, default=utc_now)
    viewer = db.relationship("User", foreign_keys=[viewer_id])
    __table_args__ = (db.UniqueConstraint("status_id", "viewer_id"),)


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    target_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    reason = db.Column(db.String(300), default="")
    created_at = db.Column(db.DateTime, default=utc_now)
    target = db.relationship("User", foreign_keys=[target_id])
    __table_args__ = (db.UniqueConstraint("reporter_id", "target_id"),)


class ChatReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    target_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    reason = db.Column(db.String(500), default="")
    status = db.Column(db.String(20), default="pending")
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
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
    created_at = db.Column(db.DateTime, default=utc_now)
    is_read = db.Column(db.Boolean, default=False)
    is_starred = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_view_once = db.Column(db.Boolean, default=False)
    viewed_once = db.Column(db.Boolean, default=False)
    edited_at = db.Column(db.DateTime, nullable=True)
    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])
    reply_to = db.relationship("ChatMessage", remote_side=[id], foreign_keys=[reply_to_id])


class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    addressee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(10), default="pending")
    created_at = db.Column(db.DateTime, default=utc_now)
    requester = db.relationship("User", foreign_keys=[requester_id])
    addressee = db.relationship("User", foreign_keys=[addressee_id])
    __table_args__ = (db.UniqueConstraint("requester_id", "addressee_id"),)


class SavedChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    peer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    pinned = db.Column(db.Boolean, default=False)
    muted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    user = db.relationship("User", foreign_keys=[user_id])
    __table_args__ = (db.UniqueConstraint("user_id", "peer_id"),)


class Block(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blocker_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    blocked_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    blocker = db.relationship("User", foreign_keys=[blocker_id])
    blocked = db.relationship("User", foreign_keys=[blocked_id])
    __table_args__ = (db.UniqueConstraint("blocker_id", "blocked_id"),)


class ArchivedChat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    peer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    user = db.relationship("User", foreign_keys=[user_id])
    peer = db.relationship("User", foreign_keys=[peer_id])
    __table_args__ = (db.UniqueConstraint("user_id", "peer_id"),)


class QuickReply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    text = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(8), unique=True, default=gen_public_id, nullable=False, index=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(300), default="")
    avatar = db.Column(db.String(300), default="")
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    is_banned = db.Column(db.Boolean, default=False)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)
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
    joined_at = db.Column(db.DateTime, default=utc_now)
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
    created_at = db.Column(db.DateTime, default=utc_now)
    sender = db.relationship("User", foreign_keys=[sender_id])
    reply_to = db.relationship("GroupMessage", remote_side=[id], foreign_keys=[reply_to_id])


class GroupReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    reason = db.Column(db.String(300), default="")
    created_at = db.Column(db.DateTime, default=utc_now)
    group = db.relationship("Group", foreign_keys=[group_id])
    __table_args__ = (db.UniqueConstraint("reporter_id", "group_id"),)


class GroupJoinRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    user = db.relationship("User", foreign_keys=[user_id])
    __table_args__ = (db.UniqueConstraint("group_id", "user_id"),)


class TypingIndicator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    peer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)
    updated_at = db.Column(db.DateTime, default=utc_now, index=True)
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
    try: db.session.commit()
    except Exception: db.session.rollback()


def get_typing_users(peer_id=None, group_id=None, exclude_user_id=None):
    cutoff = now_utc_naive() - timedelta(seconds=4)
    q = TypingIndicator.query.filter(TypingIndicator.updated_at >= cutoff)
    if peer_id is not None: q = q.filter(TypingIndicator.peer_id == peer_id)
    if group_id is not None: q = q.filter(TypingIndicator.group_id == group_id)
    if exclude_user_id: q = q.filter(TypingIndicator.user_id != exclude_user_id)
    rows = q.all()
    return [r.user for r in rows if r.user]


@login_manager.user_loader
def load_user(uid):
    try: return db.session.get(User, int(uid))
    except Exception: return None


def cleanup_expired_messages():
    now = now_utc_naive()
    expired = ChatMessage.query.filter(ChatMessage.expires_at != None, ChatMessage.expires_at <= now).all()
    for m in expired:
        if m.media:
            try: os.remove(os.path.join(app.config["CHAT_FOLDER"], m.media))
            except OSError: pass
        db.session.delete(m)
    if expired:
        try: db.session.commit()
        except Exception: db.session.rollback()
    return len(expired)


def cleanup_view_once_messages():
    viewed = ChatMessage.query.filter_by(is_view_once=True, viewed_once=True).all()
    for m in viewed:
        if m.media:
            try: os.remove(os.path.join(app.config["CHAT_FOLDER"], m.media))
            except OSError: pass
        db.session.delete(m)
    if viewed:
        try: db.session.commit()
        except Exception: db.session.rollback()
    return len(viewed)


# ═══════════════════════════════════════════════════════════════
# ✅ دالة الحظر الدائم الفوري — تمسح كل شيء من الموقع ولوحة الدعم
# ═══════════════════════════════════════════════════════════════
def process_auto_ban(user):
    """حظر دائم فوري — يمسح كل البيانات (بدون قنوات)"""
    if not user or user.is_banned: return False
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

        # حذف مشاهدات الحالات
        StatusView.query.filter_by(viewer_id=uid).delete(synchronize_session=False)
        db.session.flush()

        # حذف الحالات + مشاهداتها
        for s in Status.query.filter_by(user_id=uid).all():
            StatusView.query.filter_by(status_id=s.id).delete(synchronize_session=False)
            if s.media:
                try:
                    p = os.path.join(app.config["STATUS_FOLDER"], s.media)
                    if os.path.exists(p): os.remove(p)
                except OSError: pass
            db.session.delete(s)
        db.session.flush()

        # حذف الرسائل المجهولة
        Message.query.filter_by(receiver_id=uid).delete(synchronize_session=False)
        db.session.flush()

        # فصل الردود المرجعية في الدردشة
        ChatMessage.query.filter(ChatMessage.reply_to_id.in_(
            db.session.query(ChatMessage.id).filter(or_(ChatMessage.sender_id == uid, ChatMessage.receiver_id == uid))
        )).update({"reply_to_id": None}, synchronize_session=False)
        db.session.flush()

        # حذف رسائل الدردشة + وسائطها
        for m in ChatMessage.query.filter(or_(ChatMessage.sender_id == uid, ChatMessage.receiver_id == uid)).all():
            if m.media:
                try:
                    p = os.path.join(app.config["CHAT_FOLDER"], m.media)
                    if os.path.exists(p): os.remove(p)
                except OSError: pass
            db.session.delete(m)
        db.session.flush()

        # حذف الصداقات + الحظر + الأرشيف + الدردشات المحفوظة + الردود السريعة
        Friendship.query.filter(or_(Friendship.requester_id == uid, Friendship.addressee_id == uid)).delete(synchronize_session=False)
        Block.query.filter(or_(Block.blocker_id == uid, Block.blocked_id == uid)).delete(synchronize_session=False)
        ArchivedChat.query.filter(or_(ArchivedChat.user_id == uid, ArchivedChat.peer_id == uid)).delete(synchronize_session=False)
        SavedChat.query.filter(or_(SavedChat.user_id == uid, SavedChat.peer_id == uid)).delete(synchronize_session=False)
        QuickReply.query.filter_by(user_id=uid).delete(synchronize_session=False)
        db.session.flush()

        # حذف الأجهزة + المؤشرات + البلاغات
        Device.query.filter_by(user_id=uid).delete(synchronize_session=False)
        TypingIndicator.query.filter(or_(TypingIndicator.user_id == uid, TypingIndicator.peer_id == uid)).delete(synchronize_session=False)
        ChatReport.query.filter(or_(ChatReport.reporter_id == uid, ChatReport.target_id == uid)).delete(synchronize_session=False)
        Report.query.filter(or_(Report.reporter_id == uid, Report.target_id == uid)).delete(synchronize_session=False)
        db.session.flush()

        # فصل ردود المجموعات
        GroupMessage.query.filter(GroupMessage.reply_to_id.in_(
            db.session.query(GroupMessage.id).filter_by(sender_id=uid)
        )).update({"reply_to_id": None}, synchronize_session=False)
        GroupMessage.query.filter_by(sender_id=uid).delete(synchronize_session=False)
        GroupReport.query.filter_by(reporter_id=uid).delete(synchronize_session=False)
        GroupJoinRequest.query.filter_by(user_id=uid).delete(synchronize_session=False)
        db.session.flush()

        # نقل ملكية المجموعات أو حذفها
        for g in Group.query.filter_by(owner_id=uid).all():
            gid_local = g.id
            new_owner = GroupMember.query.filter(GroupMember.group_id == gid_local, GroupMember.user_id != uid).order_by(
                case((GroupMember.role == "admin", 0), else_=1), GroupMember.joined_at.asc()).first()
            if new_owner:
                new_owner.role = "owner"
                g.owner_id = new_owner.user_id
            else:
                for gm in GroupMessage.query.filter_by(group_id=gid_local).all():
                    if gm.media:
                        try: os.remove(os.path.join(app.config["GROUP_FOLDER"], gm.media))
                        except OSError: pass
                    db.session.delete(gm)
                if g.avatar:
                    try: os.remove(os.path.join(app.config["GROUP_FOLDER"], g.avatar))
                    except OSError: pass
                GroupReport.query.filter_by(group_id=gid_local).delete(synchronize_session=False)
                GroupJoinRequest.query.filter_by(group_id=gid_local).delete(synchronize_session=False)
                GroupMember.query.filter_by(group_id=gid_local).delete(synchronize_session=False)
                db.session.delete(g)
        db.session.flush()

        GroupMember.query.filter_by(user_id=uid).delete(synchronize_session=False)
        db.session.flush()

        # حذف الملفات الشخصية
        if user.avatar:
            try:
                p = os.path.join(app.config["AVATAR_FOLDER"], user.avatar)
                if os.path.exists(p): os.remove(p)
            except OSError: pass
            user.avatar = ""
        if user.profile_cover:
            try:
                p = os.path.join(app.config["COVER_FOLDER"], user.profile_cover)
                if os.path.exists(p): os.remove(p)
            except OSError: pass
            user.profile_cover = ""
        if user.chat_wallpaper:
            try:
                p = os.path.join(app.config["COVER_FOLDER"], user.chat_wallpaper)
                if os.path.exists(p): os.remove(p)
            except OSError: pass
            user.chat_wallpaper = ""

        # تفريغ بيانات المستخدم
        user.bio = ""
        user.nickname = ""
        user.recovery_hash = ""
        user.is_verified = False
        user.verified_color = "#1d9bf0"
        user.verified_icon = "✓"
        user.mood_text = ""
        user.custom_title = ""
        user.username = f"__b{uid:04d}"[:5]

        db.session.commit()
        print(f"[PERMANENT BAN OK] user_id={uid}")
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
    pending = User.query.filter(User.pending_username_release == True, User.username_release_at <= now).all()
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
                ("is_verified", "BOOLEAN DEFAULT FALSE"),
                ("verified_color", "VARCHAR(200) DEFAULT '#1d9bf0'"),
                ("verified_icon", "VARCHAR(10) DEFAULT '✓'"),
                ("profile_cover", "VARCHAR(300) DEFAULT ''"),
                ("mood_text", "VARCHAR(64) DEFAULT ''"),
                ("custom_title", "VARCHAR(32) DEFAULT ''"),
                ("title_color", "VARCHAR(20) DEFAULT '#6b7280'"),
                ("chat_wallpaper", "VARCHAR(300) DEFAULT ''"),
                ("favorite_emojis", "VARCHAR(200) DEFAULT '❤️,👍,😂,😮,😢,🙏'"),
                ("default_disappear_seconds", "INTEGER DEFAULT 0"),
                ("privacy_last_seen", "VARCHAR(10) DEFAULT 'everyone'"),
                ("privacy_profile_photo", "VARCHAR(10) DEFAULT 'everyone'"),
                ("privacy_about", "VARCHAR(10) DEFAULT 'everyone'"),
                ("notifications_enabled", "BOOLEAN DEFAULT TRUE"),
                ("read_receipts", "BOOLEAN DEFAULT TRUE"),
            ]:
                if col not in user_cols:
                    db.session.execute(text(f'ALTER TABLE "user" ADD COLUMN {col} {typ}'))
                    db.session.commit()
            for tbl, cols in [
                ("chat_message", [("reply_to_id", "INTEGER"), ("reaction", "VARCHAR(16) DEFAULT ''"),
                                   ("media_type", "VARCHAR(10) DEFAULT ''"), ("is_starred", "BOOLEAN DEFAULT FALSE"),
                                   ("expires_at", "TIMESTAMP"), ("is_view_once", "BOOLEAN DEFAULT FALSE"),
                                   ("viewed_once", "BOOLEAN DEFAULT FALSE"), ("edited_at", "TIMESTAMP")]),
                ("group_message", [("reply_to_id", "INTEGER"), ("reaction", "VARCHAR(16) DEFAULT ''"),
                                    ("media_type", "VARCHAR(10) DEFAULT ''"), ("is_starred", "BOOLEAN DEFAULT FALSE")]),
                ("saved_chat", [("muted", "BOOLEAN DEFAULT FALSE")]),
                ("group_member", [("muted", "BOOLEAN DEFAULT FALSE")]),
            ]:
                try: existing = [c["name"] for c in insp.get_columns(tbl)]
                except Exception: continue
                for col, typ in cols:
                    if col not in existing:
                        db.session.execute(text(f'ALTER TABLE "{tbl}" ADD COLUMN {col} {typ}'))
                        db.session.commit()
        except Exception as e:
            print(f"[init_db] warning: {e}")
            db.session.rollback()


init_db()


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════
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


def cover_url(user):
    if not user or not user.profile_cover: return ""
    return url_for("serve_upload", subpath=f"covers/{user.profile_cover}")


def group_avatar_url(g):
    if not g: return ""
    if g.avatar:
        return url_for("serve_upload", subpath=f"groups/{g.avatar}")
    return f"https://ui-avatars.com/api/?name={g.name}&background=dbeafe&color=1e40af&size=200"


def upload_url(kind, filename): return url_for("serve_upload", subpath=f"{kind}/{filename}")


def verified_html(user, large=False):
    """✅ شارة توثيق متحركة"""
    if user and getattr(user, "is_verified", False):
        color = getattr(user, "verified_color", "#1d9bf0") or "#1d9bf0"
        icon = getattr(user, "verified_icon", "✓") or "✓"
        size = "24px" if large else "18px"
        font_size = "15px" if large else "12px"
        cls = "verified-badge-lg" if large else "verified-badge-sm"
        return (f'<span class="verified-badge {cls}" title="حساب موثّق" '
                f'style="background:{color};width:{size};height:{size};'
                f'font-size:{font_size}"><span class="vb-icon">{icon}</span></span>')
    return ""


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
    db.session.add(Device(user_id=user.id, token=token, user_agent=request.headers.get("User-Agent", "")[:255]))
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
    return {r.blocked_id for r in Block.query.filter_by(blocker_id=user_id).all()}


def get_blocked_by_ids(user_id):
    return {r.blocker_id for r in Block.query.filter_by(blocked_id=user_id).all()}


def is_blocked_between(a_id, b_id):
    return Block.query.filter(or_(
        and_(Block.blocker_id == a_id, Block.blocked_id == b_id),
        and_(Block.blocker_id == b_id, Block.blocked_id == a_id))).first() is not None


def get_friends(user_id):
    rows = Friendship.query.filter(Friendship.status == "accepted",
        or_(Friendship.requester_id == user_id, Friendship.addressee_id == user_id)).all()
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


def share_link_btn_html():
    """✨ زر نسخ رابط الصفحة الحالية"""
    return ('<button class="copy-btn share-btn" onclick="shareCurrentPage(this)" '
            'title="نسخ الرابط">🔗 مشاركة</button>')


def online_status_html(user, show_text=True):
    """✅ نقطة واحدة فقط (خضراء/سوداء)"""
    if not user: return "", ""
    if user.is_online:
        dot = '<span class="status-dot online" title="متصل"></span>'
        text = '<span class="status-text online-text">متصل الآن</span>' if show_text else ''
    else:
        dot = '<span class="status-dot offline" title="غير متصل"></span>'
        text = (f'<span class="status-text offline-text">آخر ظهور {time_ago_sd(user.last_seen)}</span>'
                if show_text else '')
    return dot, text


# ═══════════════════════════════════════════════════════════════
# ROUTES الأساسية
# ═══════════════════════════════════════════════════════════════
@app.route("/uploads/<path:subpath>")
def serve_upload(subpath):
    return send_from_directory(UPLOAD_DIR, subpath)


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
      <div style="margin-bottom:10px">""" + glow_icon("alert", 56, "#dc2626") + """</div>
      <h2 style="color:#991b1b">خطأ داخلي</h2>
      <p style="color:#6b7280;margin:14px 0;font-size:14px">حدث خطأ غير متوقع.</p>
      <a class="btn btn-primary" href="/support/dashboard">رجوع للوحة الدعم</a>
    </div>""", title="خطأ"), 500


# ═══════════════════════════════════════════════════════════════
# ✅ CSS — v15.0 مع أشكال مضيئة + Toast + Scroll-to-bottom
# ═══════════════════════════════════════════════════════════════
BASE_STYLE = """
<style>
:root{--bg:#f7f7f8;--surface:#fff;--border:#e5e7eb;--text:#111827;--muted:#6b7280;
--accent:#111827;--accent-hover:#374151;--danger:#dc2626;--success:#16a34a;
--blue:#2563eb;--radius:14px;--wa-green:#075E54;--wa-light:#25D366;--wa-chat:#E5DDD5;--wa-blue:#53BDEB;}
*{box-sizing:border-box;margin:0;padding:0}html,body{height:100%}
body{font-family:-apple-system,'Segoe UI','Tahoma',system-ui,sans-serif;background:var(--bg);
color:var(--text);min-height:100vh;display:flex;justify-content:center;padding:28px 16px 60px;line-height:1.6;
transition:background .2s,color .2s;}
body.dark{--bg:#0b141a;--surface:#111b21;--border:#233138;--text:#e9edef;--muted:#8696a0;
--accent:#00a884;--accent-hover:#00c896;}
body.dark .bubble.me{background:#005c4b;color:#e9edef;}
body.dark .bubble.them{background:#202c33;color:#e9edef;}
body.dark .list-item{background:#111b21;border-color:#233138;}
body.dark .list-item:hover{background:#202c33;}
body.dark .acct-box{background:linear-gradient(135deg,#111b21,#0b141a);border-color:#233138;}
body.dark input,body.dark textarea{background:#202c33;border-color:#233138;color:#e9edef;}
body.dark .topbar{background:#111b21;border-color:#233138;}
body.dark .social-box{background:#111b21;border-color:#233138;}
.container{width:100%;max-width:560px}
.brand{text-align:center;margin-bottom:26px}
.brand h1{font-size:28px;font-weight:800;letter-spacing:1px;line-height:1.4;color:var(--wa-green);}
body.dark .brand h1{color:var(--wa-light);}
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
button:active{transform:scale(.97)}
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
.name{font-size:20px;font-weight:800;display:inline-flex;align-items:center;gap:6px;}
.username{color:var(--muted);font-size:14px;margin-top:2px}
.uid{display:inline-block;margin-top:10px;padding:4px 12px;background:var(--bg);border:1px solid var(--border);
border-radius:999px;font-size:12px;color:var(--muted);direction:ltr;}
.bio{margin-top:14px;font-size:15px;color:#374151;line-height:1.6}
body.dark .bio{color:#cbd5e1;}
.actions{margin-top:22px;display:flex;flex-direction:column;gap:8px}
.btn{display:block;padding:12px;border-radius:10px;border:1px solid var(--border);font-size:15px;font-weight:600;
text-align:center;text-decoration:none;cursor:pointer;transition:.15s;background:var(--surface);color:var(--text);}
.btn:hover{background:var(--bg);text-decoration:none}
.btn:active{transform:scale(.98)}
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

/* ✅ أيقونات SVG مضيئة */
.glow-icon{display:inline-flex;align-items:center;justify-content:center;
  filter:drop-shadow(0 0 4px currentColor) drop-shadow(0 0 8px currentColor);
  transition:.2s;vertical-align:middle;}
.glow-icon svg{width:100%;height:100%;}
.glow-icon:hover{filter:drop-shadow(0 0 6px currentColor) drop-shadow(0 0 14px currentColor);
  transform:scale(1.15);}
.glow-react{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;
  filter:drop-shadow(0 0 3px currentColor) drop-shadow(0 0 6px currentColor);
  transition:.15s;color:inherit;}
.glow-react svg{width:100%;height:100%;}
.glow-react:hover{transform:scale(1.25);}

/* ✅ Topbar */
.topbar{display:flex;justify-content:space-around;align-items:center;gap:4px;margin-bottom:14px;padding:10px 6px;
background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);}
.topbar a{display:flex;flex-direction:column;align-items:center;gap:4px;font-size:11px;color:var(--muted);
flex:1;padding:6px 2px;border-radius:8px;transition:.15s;text-decoration:none;position:relative;}
.topbar a .ic{color:var(--wa-green);transition:.2s;display:flex;}
body.dark .topbar a .ic{color:var(--wa-light);}
.topbar a:hover{background:var(--bg);color:var(--text);text-decoration:none}
.topbar a:hover .ic{transform:scale(1.15);}
.topbar a .ic .glow-icon{color:inherit;}
.badge{position:absolute;top:2px;left:8px;background:var(--wa-light);color:#fff;font-size:10px;min-width:16px;height:16px;
border-radius:999px;display:flex;align-items:center;justify-content:center;padding:0 4px;font-weight:700;}
.badge.pulse{animation:badgePulse 1.5s infinite;}
@keyframes badgePulse{0%,100%{box-shadow:0 0 0 0 rgba(37,211,102,.7);}50%{box-shadow:0 0 0 6px rgba(37,211,102,0);}}

/* ✅ شارات التوثيق */
.verified-badge{display:inline-flex;align-items:center;justify-content:center;border-radius:50%;color:#fff;
margin-right:4px;flex-shrink:0;font-weight:900;line-height:1;
box-shadow:0 0 0 2px var(--surface),0 1px 3px rgba(0,0,0,.15);
position:relative;vertical-align:middle;font-family:'Segoe UI Symbol','Apple Symbols',sans-serif;
text-shadow:0 1px 2px rgba(0,0,0,.2);
animation:verifiedPulse 2s ease-in-out infinite;}
.verified-badge::after{content:"";position:absolute;inset:0;border-radius:50%;
  box-shadow:inset 0 -2px 3px rgba(0,0,0,.15),inset 0 1px 2px rgba(255,255,255,.3);
  pointer-events:none;}
.verified-badge-lg{width:24px;height:24px;font-size:15px;}
.verified-badge-sm{width:18px;height:18px;font-size:12px;}
.vb-icon{position:relative;z-index:1;}
@keyframes verifiedPulse{
  0%,100%{transform:scale(1);filter:drop-shadow(0 0 2px currentColor);}
  50%{transform:scale(1.08);filter:drop-shadow(0 0 8px currentColor) drop-shadow(0 0 14px currentColor);}
}

/* ✅ Statuses */
.status-strip{display:flex;gap:12px;overflow-x:auto;padding-bottom:6px}
.status-item{flex:0 0 auto;text-align:center;width:72px;text-decoration:none;color:inherit}
.status-item .ring{display:inline-block;padding:2px;border-radius:50%;
background:linear-gradient(135deg,#25D366,#84cc16);position:relative;}
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
.status-actions-bottom .action-btn.add{background:rgba(37,211,102,.95)}
.status-actions-bottom .action-btn.profile{background:rgba(107,114,128,.95)}
.status-nav{position:absolute;bottom:20px;left:0;right:0;display:flex;justify-content:center;gap:10px;z-index:20;align-items:center}
.status-nav .nav-btn{background:rgba(255,255,255,.2);color:#fff;border:none;padding:8px 16px;border-radius:8px;
font-size:13px;font-weight:600;cursor:pointer;width:auto;margin:0}
.status-nav .nav-btn:hover{background:rgba(255,255,255,.35)}
.status-nav .counter{color:#fff;font-size:13px}

.empty{text-align:center;color:var(--muted);font-size:14px;padding:20px 0}
.list-item{display:flex;align-items:center;gap:10px;background:#f7f7f8;border:1px solid #e5e7eb;
border-radius:10px;padding:10px;margin-bottom:8px;text-decoration:none;color:inherit;flex-wrap:wrap;}
.list-item:hover{background:#eef0f3;text-decoration:none}
.list-item .li-name{font-weight:700}.list-item .li-sub{color:var(--muted);font-size:12px}
.list-item .li-actions{margin-right:auto;display:flex;gap:6px;align-items:center;flex-wrap:wrap}

/* ✅ Chat WhatsApp */
.chat-header{display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap}
.chat-header .pn{font-weight:800;font-size:15px}
.chat-header .pu{color:var(--muted);font-size:12px}
.chat-box{background:#E5DDD5;border:1px solid var(--border);border-radius:var(--radius);padding:16px;
height:60vh;overflow-y:auto;display:flex;flex-direction:column;gap:10px;
background-size:cover;background-position:center;position:relative;}
body.dark .chat-box{background:#0b141a;}
.bubble{max-width:75%;padding:8px 12px 6px;border-radius:8px;font-size:14.5px;line-height:1.5;word-wrap:break-word;position:relative;
box-shadow:0 1px 1px rgba(0,0,0,.08);}
.bubble.me{align-self:flex-start;background:#DCF8C6;}
.bubble.them{align-self:flex-end;background:#fff;}
.bubble .t{font-size:10px;color:#667781;margin-top:3px;display:flex;align-items:center;gap:4px;justify-content:flex-end;}
body.dark .bubble .t{color:#8696a0;}
.bubble img,.bubble video{display:block;border-radius:8px;margin-bottom:4px;max-width:100%;max-height:320px;}
.bubble-wrap{display:flex;flex-direction:column;width:100%;position:relative;}
.bubble-wrap:has(.bubble.me){align-items:flex-start}
.bubble-wrap:has(.bubble.them){align-items:flex-end}
.reply-quote{background:rgba(0,0,0,.06);border-right:3px solid #25D366;border-radius:6px;
padding:5px 9px;margin-bottom:5px;font-size:12.5px;line-height:1.4;}
.reply-quote .rq-name{font-weight:800;color:#075E54;font-size:11.5px;margin-bottom:2px}
.reply-quote .rq-body{color:#4b5563;white-space:pre-wrap;word-break:break-word}
body.dark .reply-quote .rq-body{color:#cbd5e1;}
.reaction-badge{position:absolute;bottom:-10px;background:#fff;border:1px solid var(--border);
border-radius:999px;padding:2px 8px;font-size:13px;box-shadow:0 1px 4px rgba(0,0,0,.1);line-height:1.2;z-index:2;display:inline-flex;align-items:center;}
.bubble.me .reaction-badge{left:8px}
.bubble.them .reaction-badge{right:8px}
.reply-preview{display:flex;align-items:center;gap:10px;background:#eff6ff;border:1px solid #bfdbfe;
border-radius:10px;padding:8px 12px;margin-top:8px;border-right:4px solid #25D366}
.reply-preview .rp-info{flex:1;min-width:0}
.reply-preview .rp-name{font-weight:800;color:#1e40af;font-size:12px}
.reply-preview .rp-body{color:#4b5563;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.reply-preview .rp-close{background:transparent;border:none;color:#6b7280;font-size:18px;
cursor:pointer;width:30px;height:30px;padding:0;margin:0;flex-shrink:0;border-radius:6px}

.msg-action-bar{display:none;background:#fff;border:1px solid var(--border);border-radius:12px;
padding:8px 10px;margin-top:4px;box-shadow:0 4px 14px rgba(0,0,0,.10);
position:relative;z-index:5;max-width:100%;}
body.dark .msg-action-bar{background:#202c33;}
.msg-action-bar.show{display:flex;flex-wrap:wrap;gap:4px;align-items:center;}
.msg-action-bar .emoji-quick{background:transparent;border:none;font-size:20px;cursor:pointer;
padding:4px 6px;margin:0;width:auto;border-radius:8px;transition:.12s;line-height:1;color:#25D366;}
.msg-action-bar .emoji-quick:hover{background:#eef2ff;transform:scale(1.2);}
.msg-action-bar .act-divider{width:1px;height:22px;background:var(--border);margin:0 4px;}
.msg-action-bar .act-btn{background:#f7f7f8;border:1px solid var(--border);color:var(--text);
padding:6px 12px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;margin:0;width:auto;
display:inline-flex;align-items:center;gap:4px;transition:.12s;}
body.dark .msg-action-bar .act-btn{background:#2a3942;color:#e9edef;border-color:#374955;}
.msg-action-bar .act-btn:hover{background:#eef2ff;border-color:#c7d2fe;}
.msg-action-bar .act-btn.report{background:#fef2f2;border-color:#fecaca;color:#991b1b;}
.msg-action-bar .act-btn.delete{background:#fef2f2;border-color:#fecaca;color:#991b1b;}
.msg-action-bar .act-btn.clear-react{background:#fef3c7;border-color:#fcd34d;color:#92400e;}
.msg-action-bar .act-btn.star{background:#fef9c3;border-color:#fde047;color:#854d0e;}

.bubble.clickable{cursor:pointer;}
.bubble.clickable:hover{box-shadow:0 1px 3px rgba(0,0,0,.15);}

.chat-input{display:flex;gap:8px;margin-top:10px;align-items:center}
.chat-input input:not([type="file"]){flex:1;margin:0;border-radius:24px;padding:12px 18px}
.chat-input button[type="submit"]{width:auto;padding:12px 20px;margin:0;flex-shrink:0;border-radius:24px;background:#25D366}
.chat-input button[type="submit"]:hover{background:#128C7E}
.chat-input .icon-btn{border-radius:50%;background:#25D366;color:#fff;border:none;width:44px;height:44px;margin:0;flex-shrink:0;display:flex;align-items:center;justify-content:center;}

.audio-bubble{background:rgba(0,0,0,.05);border-radius:12px;padding:8px 12px;margin-bottom:4px;
display:flex;align-items:center;gap:10px;min-width:240px;}
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
.privacy-opt input:checked ~ .pbox{border-color:var(--wa-green);background:#ecfdf5;box-shadow:0 0 0 3px rgba(37,211,102,.12)}

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
text-decoration:none;cursor:pointer;transition:.18s;border:1px solid transparent;white-space:nowrap;direction:ltr;}
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
body.dark .switch-row{background:#202c33;}
.switch-row input{position:absolute;opacity:0;pointer-events:none;width:0;height:0}
.switch-row .switch{width:44px;height:24px;background:#d1d5db;border-radius:999px;position:relative;
transition:.2s;flex-shrink:0}
.switch-row .switch::after{content:"";position:absolute;top:2px;left:2px;width:20px;height:20px;
background:#fff;border-radius:50%;transition:.2s;box-shadow:0 1px 3px rgba(0,0,0,.2)}
.switch-row input:checked ~ .switch{background:#25D366}
.switch-row input:checked ~ .switch::after{left:22px}
.role-badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:11px;font-weight:800;margin-left:6px}
.role-badge.owner{background:#fef3c7;color:#92400e;border:1px solid #fcd34d}
.role-badge.admin{background:#dbeafe;color:#1e40af;border:1px solid #93c5fd}
.role-badge.member{background:#f3f4f6;color:#6b7280;border:1px solid #e5e7eb}

.group-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px;
margin-bottom:10px;display:flex;gap:12px;align-items:center;text-decoration:none;color:inherit;transition:.15s}
.group-card:hover{border-color:#25D366;box-shadow:0 0 0 3px rgba(37,211,102,.08);text-decoration:none}
.group-card .g-avatar{width:54px;height:54px;border-radius:14px;object-fit:cover;flex-shrink:0;border:2px solid var(--border)}
.group-card .g-name{font-weight:800;font-size:16px;margin-bottom:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.group-card .g-sub{font-size:12px;color:var(--muted)}

.group-id-box{background:linear-gradient(135deg,#dbeafe,#e0e7ff);border:2px solid #93c5fd;border-radius:12px;
padding:12px 16px;margin:12px 0;display:flex;align-items:center;justify-content:space-between;gap:10px;direction:ltr}
.group-id-box .gid-label{font-size:11px;color:#1e40af;font-weight:800;text-transform:uppercase;letter-spacing:1px}
.group-id-box .gid-value{font-family:'Courier New',monospace;font-size:22px;font-weight:900;color:#1e3a8a;letter-spacing:3px}

.bulk-user-row{display:flex;align-items:center;gap:10px;background:#fff;border:1px solid var(--border);
border-radius:10px;padding:10px;margin-bottom:6px;cursor:pointer;transition:.12s}
body.dark .bulk-user-row{background:#202c33;}
.bulk-user-row:hover{background:#f7f7f8}
.bulk-user-row.selected{background:#eff6ff;border-color:#93c5fd;box-shadow:0 0 0 2px rgba(37,99,235,.12)}
.bulk-user-row input[type="checkbox"]{width:20px;height:20px;cursor:pointer;flex-shrink:0;accent-color:#25D366}

.sender-head{display:inline-flex;align-items:center;gap:6px;margin-bottom:5px;
  text-decoration:none;color:#075E54;font-weight:700;font-size:12px;
  padding:1px 6px;border-radius:8px;transition:.15s;}
body.dark .sender-head{color:#25D366;}
.sender-head:hover{background:rgba(37,211,102,.08);text-decoration:none;}
.sender-avatar{width:22px;height:22px;border-radius:50%;object-fit:cover;
  border:1.5px solid #fff;box-shadow:0 1px 2px rgba(0,0,0,.1);flex-shrink:0;}
.sender-name{font-size:12px;font-weight:700;}

/* ✅ Typing indicator بنقاط مضيئة */
.typing-indicator{display:none;align-items:center;gap:8px;
  background:#fff;border:1px solid #e5e7eb;border-radius:12px;
  padding:8px 14px;margin-top:8px;font-size:13px;color:#6b7280;
  box-shadow:0 2px 8px rgba(0,0,0,.04);}
body.dark .typing-indicator{background:#202c33;border-color:#233138;color:#8696a0;}
.typing-indicator.show{display:flex;}
.typing-indicator .typing-name{font-weight:800;color:#075E54;}
body.dark .typing-indicator .typing-name{color:#25D366;}
.typing-indicator .typing-dots{display:inline-flex;gap:3px;}
.typing-indicator .typing-dots span{width:6px;height:6px;border-radius:50%;
  background:#25D366;box-shadow:0 0 6px #25D366,0 0 12px #25D366;
  animation:typingBounce 1.2s infinite;}
.typing-indicator .typing-dots span:nth-child(2){animation-delay:.15s;}
.typing-indicator .typing-dots span:nth-child(3){animation-delay:.3s;}
@keyframes typingBounce{
  0%,60%,100%{transform:translateY(0);opacity:.4;}
  30%{transform:translateY(-5px);opacity:1;}
}

.read-tick{font-size:11px;color:#9ca3af;letter-spacing:-2px;margin-right:2px;}
.read-tick.read{color:#53BDEB;}
.chat-link{color:#075E54;font-weight:700;text-decoration:underline;word-break:break-all;}
body.dark .chat-link{color:#25D366;}
.star-badge{position:absolute;top:-6px;right:-6px;background:#fbbf24;color:#fff;
  width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:11px;box-shadow:0 1px 4px rgba(0,0,0,.2);z-index:3;}

/* ✅ Dark toggle محسّن بـ SVG */
.dark-toggle{position:fixed;top:14px;left:14px;z-index:500;background:var(--surface);
  border:1px solid var(--border);width:54px;height:30px;border-radius:999px;
  cursor:pointer;display:flex;align-items:center;padding:2px;margin:0;
  box-shadow:0 2px 8px rgba(0,0,0,.1);transition:.25s;justify-content:space-between;}
.dark-toggle:hover{transform:scale(1.05);}
.dark-toggle .circle{width:24px;height:24px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  transition:.25s;font-size:13px;line-height:1;position:absolute;top:50%;transform:translateY(-50%);}
.dark-toggle .circle.sun{background:#fff;color:#f59e0b;
  border:2px solid #fbbf24;left:2px;box-shadow:0 0 8px rgba(251,191,36,.5);}
.dark-toggle .circle.moon{background:#111827;color:#fff;
  border:2px solid #374151;right:2px;}
body.dark .dark-toggle{background:#1e293b;border-color:#334155;}

.chat-search-bar{display:flex;gap:6px;margin-bottom:8px;}
.chat-search-bar input{flex:1;margin:0;padding:8px 12px;font-size:13px;}

.chat-options{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;
  padding-top:8px;border-top:1px dashed var(--border);}
.chat-options button{background:#f7f7f8;border:1px solid var(--border);color:var(--text);
  padding:6px 12px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;
  margin:0;width:auto;display:inline-flex;align-items:center;gap:4px;}
body.dark .chat-options button{background:#202c33;border-color:#233138;color:#e9edef;}

/* ✅ نقطة واحدة فقط */
.avatar-wrap{position:relative;display:inline-block;margin-bottom:14px;}
.avatar-wrap .avatar{margin-bottom:0;display:block;}
.status-dot{position:absolute;bottom:6px;right:6px;width:20px;height:20px;border-radius:50%;
  border:3px solid var(--surface);box-shadow:0 1px 4px rgba(0,0,0,.2);z-index:3;transition:.2s;}
.status-dot.online{background:#25D366;animation:pulseOnline 2s infinite;}
.status-dot.offline{background:#6b7280;}
body.dark .status-dot.offline{background:#000;border-color:#111b21;}
@keyframes pulseOnline{
  0%,100%{box-shadow:0 0 0 3px var(--surface),0 0 0 0 rgba(37,211,102,.7);}
  50%{box-shadow:0 0 0 3px var(--surface),0 0 0 8px rgba(37,211,102,0);}
}
.status-text{font-size:12px;font-weight:700;margin-top:4px;display:inline-block;}
.status-text.online-text{color:#25D366;}
.status-text.offline-text{color:#9ca3af;font-weight:500;font-size:11.5px;}
body.dark .status-text.offline-text{color:#8696a0;}
.status-line{display:flex;flex-direction:column;align-items:center;margin-top:4px;gap:2px;}

.profile-cover-wrap{position:relative;width:calc(100% + 44px);height:180px;
  border-radius:16px 16px 0 0;overflow:hidden;margin:-24px -22px 0 -22px;
  background:linear-gradient(135deg,#667eea,#764ba2);cursor:zoom-in;}
.profile-cover-wrap.no-cover{cursor:default;}
.profile-cover-wrap img{width:100%;height:100%;object-fit:cover;display:block;}
.profile-cover-wrap .cover-edit-btn{position:absolute;bottom:10px;left:10px;
  background:rgba(0,0,0,.65);color:#fff;border:none;padding:8px 14px;border-radius:8px;
  font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px;
  width:auto;margin:0;backdrop-filter:blur(4px);transition:.15s;}
.profile-avatar-overlap{margin-top:-50px;position:relative;z-index:2;}

/* ✅ غيمة الحالة المزاجية */
.mood-cloud{position:absolute;top:-14px;right:-10px;background:#fff;
  border:2px solid #e5e7eb;border-radius:18px 18px 18px 4px;padding:4px 12px;
  font-size:11px;font-weight:700;color:#374151;box-shadow:0 3px 10px rgba(0,0,0,.12);
  z-index:6;max-width:130px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  animation:cloudFloat 3s ease-in-out infinite;pointer-events:none;}
.mood-cloud::after{content:"";position:absolute;bottom:-7px;right:14px;width:10px;height:10px;
  background:#fff;border-right:2px solid #e5e7eb;border-bottom:2px solid #e5e7eb;
  transform:rotate(45deg);}
@keyframes cloudFloat{0%,100%{transform:translateY(0);}50%{transform:translateY(-4px);}}
body.dark .mood-cloud{background:#202c33;border-color:#233138;color:#e9edef;}
body.dark .mood-cloud::after{background:#202c33;border-color:#233138;}

.custom-title{display:inline-block;padding:3px 12px;border-radius:999px;font-size:12px;
  font-weight:800;color:#fff;margin-top:6px;letter-spacing:.5px;}

.disappear-badge{display:inline-flex;align-items:center;gap:3px;font-size:10px;
  background:#fef3c7;color:#92400e;border:1px solid #fcd34d;
  padding:1px 6px;border-radius:6px;font-weight:700;margin-left:4px;}

.disappear-selector{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;
  padding:8px;background:#fffbeb;border:1px solid #fcd34d;border-radius:10px;}
.disappear-selector .dopt{background:#fff;border:2px solid #fcd34d;color:#92400e;
  padding:5px 10px;border-radius:8px;font-size:12px;font-weight:700;cursor:pointer;
  margin:0;width:auto;transition:.15s;}
.disappear-selector .dopt.active{background:#f59e0b;color:#fff;border-color:#f59e0b;}

.color-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:8px;
  max-height:400px;overflow-y:auto;padding:8px;background:#f9fafb;border-radius:10px;border:1px solid var(--border)}
body.dark .color-grid{background:#202c33;border-color:#233138;}
.color-opt{display:flex;flex-direction:column;align-items:center;gap:4px;padding:8px;
  border-radius:10px;cursor:pointer;border:2px solid transparent;transition:.15s;background:#fff}
body.dark .color-opt{background:#111b21;color:#e9edef;}
.color-opt:hover{border-color:#25D366;transform:translateY(-2px)}
.color-opt.selected{border-color:#25D366;background:#ecfdf5;box-shadow:0 0 0 3px rgba(37,211,102,.15)}
.color-preview{width:32px;height:32px;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,.2),inset 0 -2px 4px rgba(0,0,0,.1)}
.color-name{font-size:11px;font-weight:600;color:#374151;text-align:center}
body.dark .color-name{color:#cbd5e1;}
.icon-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(50px,1fr));gap:6px;
  padding:8px;background:#f9fafb;border-radius:10px;border:1px solid var(--border);
  max-height:320px;overflow-y:auto}
body.dark .icon-grid{background:#202c33;border-color:#233138;}
.icon-opt{background:#fff;border:2px solid transparent;border-radius:10px;padding:8px;
  font-size:22px;cursor:pointer;transition:.15s;width:auto;margin:0;font-family:'Segoe UI Symbol',sans-serif}
body.dark .icon-opt{background:#111b21;color:#e9edef;}
.icon-opt:hover{border-color:#25D366;transform:scale(1.1)}
.icon-opt.selected{border-color:#25D366;background:#ecfdf5}

/* ✅ Toast notifications */
.toast-container{position:fixed;top:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:10px;
  pointer-events:none;max-width:340px;}
.toast{background:#fff;border:1px solid var(--border);border-radius:12px;padding:14px 18px;
  box-shadow:0 10px 30px rgba(0,0,0,.15);display:flex;align-items:center;gap:10px;
  font-size:14px;font-weight:600;color:var(--text);pointer-events:auto;
  transform:translateX(120%);animation:toastIn .35s cubic-bezier(.4,0,.2,1) forwards;
  border-right:4px solid #25D366;}
body.dark .toast{background:#202c33;border-color:#233138;color:#e9edef;}
.toast.error{border-right-color:#dc2626;}
.toast.info{border-right-color:#2563eb;}
.toast.warning{border-right-color:#f59e0b;}
.toast.hide{animation:toastOut .35s cubic-bezier(.4,0,.2,1) forwards;}
@keyframes toastIn{to{transform:translateX(0);opacity:1;}}
@keyframes toastOut{to{transform:translateX(120%);opacity:0;}}

/* ✅ Scroll to bottom */
.scroll-bottom-btn{position:fixed;bottom:100px;right:24px;width:44px;height:44px;border-radius:50%;
  background:#25D366;color:#fff;border:none;cursor:pointer;display:none;align-items:center;justify-content:center;
  box-shadow:0 4px 14px rgba(37,211,102,.4);z-index:400;padding:0;margin:0;transition:.2s;}
.scroll-bottom-btn.show{display:flex;}
.scroll-bottom-btn:hover{transform:scale(1.1);background:#128C7E;}

/* ✅ Share button */
.share-btn{background:#25D366 !important;color:#fff !important;border-color:#25D366 !important;}
.share-btn:hover{background:#128C7E !important;}

@media (max-width:480px){
  .container{padding:0}
  .card{padding:18px 14px}
  .toast-container{right:10px;left:10px;max-width:none}
}
</style>
"""
# ═══════════════════════════════════════════════════════════════
# RENDER PAGE — HTML + JS كامل
# ═══════════════════════════════════════════════════════════════
def render_page(body, title=None, **ctx):
    t = title or SITE_NAME
    dark_class = "dark" if (current_user.is_authenticated and getattr(current_user, "dark_mode", False)) else ""
    if "user" not in ctx:
        ctx["user"] = current_user if current_user.is_authenticated else None
    return render_template_string(
        "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1,maximum-scale=1'>"
        "<title>{{ t }} — {{ site }}</title>" + BASE_STYLE + "</head><body class='" + dark_class + "'>"
        "<button class='dark-toggle' onclick='toggleDark()' title='الوضع الليلي/النهاري' id='dark-toggle'>"
        "<span class='circle sun'>☀</span><span class='circle moon'>🌙</span></button>"
        "<div class='container'><div class='brand'><h1>{{ site }}</h1></div>"
        + body + "</div>"
        "<div class='toast-container' id='toast-container'></div>"
        "<script>"
        # ─── Dark mode ───
        "function toggleDark(){document.body.classList.toggle('dark');"
        "try{fetch('/toggle-dark',{method:'POST',credentials:'same-origin'});}catch(e){}"
        "try{localStorage.setItem('dark',document.body.classList.contains('dark')?'1':'0');}catch(e){}}"
        "try{if(localStorage.getItem('dark')==='1'&&!document.body.classList.contains('dark'))document.body.classList.add('dark');}catch(e){}"
        # ─── Password toggle ───
        "function togglePw(id){var e=document.getElementById(id);if(!e)return;"
        "e.type=e.type==='password'?'text':'password';}"
        # ─── Haptic feedback ───
        "function haptic(){try{if(navigator.vibrate)navigator.vibrate(10);}catch(e){}}"
        "document.addEventListener('click',function(e){"
        "if(e.target.closest('button,.btn,.bubble'))haptic();});"
        # ─── Toast notifications ───
        "function showToast(msg,type){type=type||'success';"
        "var c=document.getElementById('toast-container');if(!c)return;"
        "var t=document.createElement('div');t.className='toast '+type;"
        "var icon=type==='error'?'⚠':type==='info'?'ℹ':type==='warning'?'!':'✓';"
        "t.innerHTML='<span style=\"font-size:18px;font-weight:900\">'+icon+'</span><span>'+msg+'</span>';"
        "c.appendChild(t);"
        "setTimeout(function(){t.classList.add('hide');"
        "setTimeout(function(){t.remove();},400);},3000);}"
        # ─── Copy text ───
        "function fallbackCopy(t){var ta=document.createElement('textarea');"
        "ta.value=t;ta.style.position='fixed';ta.style.opacity='0';"
        "document.body.appendChild(ta);ta.select();try{document.execCommand('copy');}catch(e){}"
        "document.body.removeChild(ta);}"
        "function copyText(t,b){var done=function(){if(!b)return;var o=b.textContent;"
        "b.textContent='✓ تم';b.classList.add('done');"
        "showToast('تم النسخ','success');"
        "setTimeout(function(){b.textContent=o;b.classList.remove('done');},1200);};"
        "if(navigator.clipboard&&window.isSecureContext){"
        "navigator.clipboard.writeText(t).then(done).catch(function(){fallbackCopy(t);done();});"
        "}else{fallbackCopy(t);done();}}"
        # ─── Share link ───
        "function shareCurrentPage(b){var url=window.location.href;"
        "if(navigator.share){navigator.share({url:url}).then(function(){showToast('تم المشاركة','success');})"
        ".catch(function(){copyText(url,b);});}"
        "else{copyText(url,b);}}"
        # ─── Preview functions ───
        "function previewStatusMedia(i){var f=i.files[0];if(!f)return;var u=URL.createObjectURL(f);"
        "var b=document.getElementById('status-preview');if(!b)return;"
        "if(f.type.startsWith('video')){b.innerHTML='<video style=\"max-width:100%;max-height:240px;border-radius:10px;margin-top:10px\" controls src=\"'+u+'\"></video>';}"
        "else{b.innerHTML='<img style=\"max-width:100%;max-height:240px;border-radius:10px;margin-top:10px\" src=\"'+u+'\">';}}"
        "function previewChatMedia(input){var f=input.files[0];if(!f)return;var u=URL.createObjectURL(f);"
        "var p=document.getElementById('chat-media-preview');if(!p)return;"
        "var html='';"
        "if(f.type.startsWith('video')){html='<video style=\"max-width:100%;max-height:200px;border-radius:10px\" controls src=\"'+u+'\"></video>';}"
        "else if(f.type.startsWith('audio')){html='<audio style=\"width:100%;margin-top:6px\" controls src=\"'+u+'\"></audio>';}"
        "else{html='<img style=\"max-width:100%;max-height:200px;border-radius:10px\" src=\"'+u+'\">';}"
        "html+='<button type=\"button\" class=\"copy-btn\" style=\"margin-top:6px\" onclick=\"clearChatMedia()\">إلغاء</button>';"
        "p.innerHTML=html;}"
        "function clearChatMedia(){var i=document.getElementById('chat-media-input');"
        "var p=document.getElementById('chat-media-preview');if(i)i.value='';if(p)p.innerHTML='';}"
        # ─── Status viewer ───
        "function openStatus(id){var e=document.getElementById('sv-'+id);if(e)e.style.display='flex';}"
        "function closeStatus(id){var e=document.getElementById('sv-'+id);if(e)e.style.display='none';}"
        # ─── Avatar viewer ───
        "function openAvatar(url){var el=document.getElementById('avatar-viewer');"
        "var img=document.getElementById('avatar-viewer-img');"
        "if(el&&img){img.src=url;el.style.display='flex';}}"
        "function closeAvatar(){var el=document.getElementById('avatar-viewer');if(el)el.style.display='none';}"
        # ─── Chat utilities ───
        "function scrollChat(){var b=document.getElementById('chatbox');if(b)b.scrollTop=b.scrollHeight;updateScrollBtn();}"
        "function updateScrollBtn(){var b=document.getElementById('chatbox');var btn=document.getElementById('scroll-bottom-btn');"
        "if(!b||!btn)return;"
        "var isBottom=b.scrollTop+b.clientHeight>=b.scrollHeight-40;"
        "if(isBottom)btn.classList.remove('show');else btn.classList.add('show');}"
        "function scrollToBottom(){var b=document.getElementById('chatbox');if(b){b.scrollTop=b.scrollHeight;updateScrollBtn();}}"
        "function formatCodeInput(el){el.value=el.value.toUpperCase().replace(/[^A-Z0-9]/g,'');}"
        # ─── Auto refresh chat ───
        "document.addEventListener('DOMContentLoaded',function(){scrollChat();"
        "var cb=document.getElementById('chatbox');if(cb)cb.addEventListener('scroll',updateScrollBtn);});"
        # ─── Keyboard shortcuts ───
        "document.addEventListener('keydown',function(e){"
        "if(e.key==='Escape'){closeAvatar();"
        "var sb=document.getElementById('search-bar');if(sb&&sb.style.display!=='none')sb.style.display='none';"
        "document.querySelectorAll('.msg-action-bar.show').forEach(function(b){b.classList.remove('show');});}"
        "if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){"
        "var f=document.getElementById('chat-form');if(f)f.submit();}});"
        # ─── Chat auto-refresh polling ───
        "var _chatRefreshTimer=null;"
        "function startChatAutoRefresh(url,interval){"
        "if(_chatRefreshTimer)clearInterval(_chatRefreshTimer);"
        "_chatRefreshTimer=setInterval(function(){"
        "fetch(url+(url.indexOf('?')>=0?'&':'?')+'ajax=1',{credentials:'same-origin'})"
        ".then(function(r){return r.json()}).then(function(d){"
        "if(d.html!==undefined){var b=document.getElementById('chatbox');"
        "if(b){var wasBottom=b.scrollTop+b.clientHeight>=b.scrollHeight-40;"
        "b.innerHTML=d.html;if(wasBottom)b.scrollTop=b.scrollHeight;}}"
        "if(d.unread!==undefined){var badge=document.getElementById('chat-badge-main');"
        "if(badge){if(d.unread>0){badge.textContent=d.unread;badge.style.display='flex';badge.classList.add('pulse');}"
        "else{badge.style.display='none';badge.classList.remove('pulse');}}}"
        "if(d.typing!==undefined){var ti=document.getElementById('typing-indicator');"
        "var tt=document.getElementById('typing-text');"
        "if(ti&&tt){if(d.typing){tt.innerHTML=d.typing;ti.classList.add('show');}"
        "else{ti.classList.remove('show');}}}"
        "}).catch(function(){});},interval||1500);}"
        "</script>"
        "<div class='avatar-view' id='avatar-viewer' style='display:none' onclick='closeAvatar()'>"
        "<button class='close-av' onclick='event.stopPropagation();closeAvatar()'>✕</button>"
        "<img id='avatar-viewer-img' src='' onclick='event.stopPropagation()'>"
        "</div></body></html>",
        t=t, site=SITE_NAME, **ctx)


@app.route("/toggle-dark", methods=["POST"])
def toggle_dark():
    if current_user.is_authenticated:
        try:
            current_user.dark_mode = not bool(current_user.dark_mode)
            db.session.commit()
        except Exception: db.session.rollback()
    return jsonify({"ok": True})


FLASH_BLOCK = """{% with msgs=get_flashed_messages(with_categories=true) %}
{% for c,m in msgs %}<div class="flash {{c}}">{{m}}</div>{% endfor %}{% endwith %}"""


def topbar_html(chat_badge=""):
    return f"""<div class="topbar">
<a href="{url_for('feed')}"><span class="ic">{glow_icon("home",22)}</span>الحالات</a>
<a href="{url_for('chats')}"><span class="ic">{glow_icon("chat",22)}</span>الدردشات{chat_badge}</a>
<a href="{url_for('groups_list')}"><span class="ic">{glow_icon("groups",22)}</span>مجموعات</a>
<a href="{url_for('discover')}"><span class="ic">{glow_icon("users",22)}</span>أشخاص</a>
<a href="{url_for('profile_me')}"><span class="ic">{glow_icon("user",22)}</span>بروفايلي</a>
</div>"""


def badge_html():
    if current_user.is_authenticated:
        c = unread_chat_count(current_user.id)
        if c:
            return f'<span class="badge pulse" id="chat-badge-main">{c}</span>'
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
# AUTH
# ═══════════════════════════════════════════════════════════════
@app.route("/")
def index():
    if current_user.is_authenticated: return redirect(url_for("feed"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated: return redirect(url_for("feed"))
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
        while User.query.filter_by(public_id=pid).first(): pid = gen_public_id()
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
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>إنشاء حساب</h2>
    <form method="POST">
    <label>اليوزر (3-5 أحرف)</label>
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
    if not recovery: return redirect(url_for("set_nickname"))
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
      <div class="recovery-box" style="background:#fffbeb;border:2px dashed #f59e0b;border-radius:12px;padding:16px;margin:14px 0;text-align:center">
        <div style="font-size:13px;font-weight:700;color:#92400e">🔐 كود الاستعادة (20 خانة)</div>
        <div style="font-size:20px;font-weight:800;color:#92400e;letter-spacing:2px;line-height:1.8;margin:10px 0;direction:ltr;font-family:'Courier New',monospace;word-break:break-all">{{ formatted }}</div>
        <div style="font-size:12px;color:#b45309"><b>مهم جدًا:</b> هذا الكود مفتاحك الوحيد لاستعادة حسابك.</div>
        <button class="copy-btn" style="margin-top:10px" onclick="copyText('{{ recovery }}',this)">نسخ الكود</button>
      </div>
      <a class="btn btn-primary" href="{{ url_for('set_nickname') }}">فهمت، أكمل</a>
    </div>""", title="مرحبًا", recovery=recovery, formatted=formatted)


@app.route("/set-nickname", methods=["GET", "POST"])
@login_required
def set_nickname():
    if current_user.nickname_ok: return redirect(url_for("feed"))
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
    <p style="color:#6b7280;font-size:13px;text-align:center;margin-bottom:12px">من كلمة إلى 4 كلمات.</p>
    <form method="POST"><label>اللقب</label>
    <input name="nickname" maxlength="64" required placeholder="مثال: القمر الساهر">
    <button type="submit">حفظ ومتابعة</button></form></div>""", title="اللقب")


@app.route("/recover", methods=["GET", "POST"])
def recover():
    if current_user.is_authenticated: return redirect(url_for("feed"))
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper().replace("-", "").replace(" ", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        if len(code) != 20:
            flash("الكود يجب أن يكون 20 خانة.", "error"); return redirect(url_for("recover"))
        if len(new_password) < 8:
            flash("كلمة المرور الجديدة: 8 أحرف على الأقل.", "error"); return redirect(url_for("recover"))
        if new_password != confirm_password:
            flash("كلمتا المرور غير متطابقتين.", "error"); return redirect(url_for("recover"))
        user = User.query.filter_by(recovery_hash=hash_recovery_code(code)).first()
        if not user:
            flash("الكود غير صحيح.", "error"); return redirect(url_for("recover"))
        if user.is_banned or user.under_review:
            flash("هذا الحساب غير متاح.", "error"); return redirect(url_for("recover"))
        user.password_hash = generate_password_hash(new_password)
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
        flash(f"تم الدخول. أهلاً @{user.username}!", "success")
        resp = make_response(redirect(url_for("welcome")))
        resp.set_cookie("device_token", token, max_age=60*60*24*365,
                        httponly=True, samesite="Lax",
                        secure=app.config["SESSION_COOKIE_SECURE"])
        return resp
    return render_page(FLASH_BLOCK + """
    <div class="card"><h2>🔐 استعادة الحساب</h2>
    <form method="POST" onsubmit="return validateRecover()">
      <label>كود الاستعادة (20 خانة)</label>
      <input name="code" id="recovery-input" maxlength="24" required autocomplete="off"
             style="direction:ltr;font-family:'Courier New',monospace;font-size:16px;
                    letter-spacing:2px;text-align:center"
             placeholder="XXXX-XXXX-XXXX-XXXX-XXXX" oninput="formatCodeInput(this)">
      <label>كلمة المرور الجديدة</label>
      <div class="pw-wrap"><input name="new_password" id="npw" type="password" required>
      <button type="button" class="pw-toggle" onclick="togglePw('npw')">👁</button></div>
      <label>تأكيد كلمة المرور</label>
      <div class="pw-wrap"><input name="confirm_password" id="npw2" type="password" required>
      <button type="button" class="pw-toggle" onclick="togglePw('npw2')">👁</button></div>
      <button type="submit">🔓 استعادة</button>
    </form>
    <a class="link-center" href="{{ url_for('login') }}">رجوع</a>
    </div>
    <script>
    function validateRecover(){
      var v=document.getElementById('recovery-input').value.toUpperCase().replace(/[^A-Z0-9]/g,'');
      if(v.length!==20){showToast('20 خانة مطلوبة','error');return false;}
      document.getElementById('recovery-input').value=v;
      if(document.getElementById('npw').value!==document.getElementById('npw2').value){
        showToast('كلمتا المرور غير متطابقتين','error');return false;}
      return true;
    }
    </script>""", title="استعادة")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated: return redirect(url_for("feed"))
    if request.method == "POST":
        ip = request.remote_addr or "?"
        if is_rate_limited(ip):
            flash("محاولات كثيرة. انتظر 5 دقائق.", "error"); return redirect(url_for("login"))
        username = request.form.get("username", "").strip().lower().lstrip("@")
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            record_login_attempt(ip)
            flash("بيانات الدخول غير صحيحة.", "error"); return redirect(url_for("login"))
        if user.is_banned:
            return render_page(BANNED_PAGE, title="محظور", username=user.original_username or user.username)
        if user.under_review:
            return render_page(UNDER_REVIEW_PAGE, title="تحت المراجعة",
                               reason=user.review_reason or "بلاغ", started=fmt_sd(user.review_started_at))
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
    <a class="link-center" href="{url_for('register')}">ليس لديك حساب؟ سجّل</a>
    <a class="link-center" href="{url_for('recover')}" style="color:#25D366;font-weight:700">
      🔑 نسيت البيانات؟ ادخل بالكود</a>
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
  <div style="margin-bottom:10px">""" + glow_icon("alert", 64, "#dc2626") + """</div>
  <h2 style="color:#991b1b;font-size:22px;margin-bottom:14px">تم حظر حسابك</h2>
  <div style="background:#fff;border:1px solid #fecaca;border-radius:12px;
              padding:16px;text-align:right;font-size:14px;line-height:1.8;color:#7f1d1d">
    <p><b>السبب:</b> مخالفة شروط الاستخدام.</p>
    <p style="margin-top:10px"><b>ملاحظة:</b> تم مسح جميع بياناتك. يوزرك ({{ username }}) سيُحرّر بعد 24 ساعة.</p>
  </div>
  <div class="actions" style="margin-top:16px">
    <a class="btn btn-primary" href="{{ url_for('logout') }}" style="background:#dc2626">🚪 خروج</a>
    <a class="btn" href="{{ url_for('register') }}" style="background:#25D366;color:#fff">➕ حساب جديد</a>
  </div>
</div>
"""

UNDER_REVIEW_PAGE = """
<div class="card center" style="border:2px solid #fcd34d;background:#fffbeb">
  <div style="margin-bottom:10px">""" + glow_icon("clock", 64, "#f59e0b") + """</div>
  <h2 style="color:#92400e;font-size:22px;margin-bottom:14px">حسابك تحت المراجعة</h2>
  <div style="background:#fff;border:1px solid #fcd34d;border-radius:12px;
              padding:16px;text-align:right;font-size:14px;line-height:1.8;color:#78350f">
    <p><b>السبب:</b> {{ reason }}</p>
    <p style="margin-top:10px"><b>بدء المراجعة:</b> {{ started }}</p>
  </div>
  <div class="actions" style="margin-top:16px">
    <a class="btn btn-primary" href="{{ url_for('logout') }}" style="background:#f59e0b">🚪 خروج</a>
  </div>
</div>
"""


@app.before_request
def before_each_request():
    if random.random() < 0.01:
        try: release_pending_usernames()
        except Exception: pass
    if random.random() < 0.05:
        try: cleanup_expired_messages()
        except Exception: pass
    if random.random() < 0.03:
        try: cleanup_view_once_messages()
        except Exception: pass
    if not current_user.is_authenticated: return
    if random.random() < 0.1:
        try:
            current_user.last_seen = now_utc_naive()
            db.session.commit()
        except Exception: db.session.rollback()
    if random.random() < 0.05:
        try:
            token = request.cookies.get("device_token")
            if token:
                d = Device.query.filter_by(token=token, user_id=current_user.id).first()
                if d: d.last_seen = now_utc_naive(); db.session.commit()
        except Exception: db.session.rollback()
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
        "support_bulk_ban", "support_verify_user", "support_unverify_user",
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
                reason = fresh.review_reason or "بلاغ"
                started = fmt_sd(fresh.review_started_at)
                logout_user()
                return render_page(UNDER_REVIEW_PAGE, title="تحت المراجعة", reason=reason, started=started)
    allowed = {"set_nickname", "logout", "static", "serve_upload",
               "welcome", "support_login", "support_logout", "support_dashboard",
               "support_reports", "support_users", "support_groups",
               "support_ban_user", "support_unban_user",
               "support_dismiss_report", "support_ban_group",
               "support_unban_group", "support_dismiss_group_report",
               "support_user_detail", "support_chat_reports",
               "support_review_chat_report", "support_release_review",
               "support_bulk_ban", "support_verify_user", "support_unverify_user",
               "group_avatar_full", "toggle_dark",
               "chat_typing", "group_typing",
               "delete_account", "change_password",
               "edit_cover", "edit_chat_wallpaper"}
    if request.endpoint in allowed: return
    if not current_user.nickname_ok:
        return redirect(url_for("set_nickname"))


# ═══════════════════════════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════════════════════════
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
      <div class="name" style="margin-top:14px">{verified_html(user, True)} {user.short_name}</div>
      <a class="btn" href="{url_for('view_profile', username=user.username)}" style="margin-top:14px">← رجوع</a>
    </div>""", title=f"صورة {user.username}")


@app.route("/profile/cover", methods=["GET", "POST"])
@login_required
def edit_cover():
    if request.method == "POST":
        file = request.files.get("cover")
        if file and file.filename:
            if not allowed_image(file.filename) or not check_image_magic(file):
                flash("صيغة غير مدعومة.", "error"); return redirect(url_for("edit_cover"))
            if current_user.profile_cover:
                try:
                    old = os.path.join(app.config["COVER_FOLDER"], current_user.profile_cover)
                    if os.path.exists(old): os.remove(old)
                except OSError: pass
            ext = file.filename.rsplit(".", 1)[1].lower()
            fn = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(app.config["COVER_FOLDER"], fn))
            current_user.profile_cover = fn
        if request.form.get("remove_cover") == "1" and current_user.profile_cover:
            try:
                old = os.path.join(app.config["COVER_FOLDER"], current_user.profile_cover)
                if os.path.exists(old): os.remove(old)
            except OSError: pass
            current_user.profile_cover = ""
        db.session.commit()
        flash("تم تحديث الغلاف.", "success")
        return redirect(url_for("profile_me"))
    cover_preview = ""
    if current_user.profile_cover:
        cu = cover_url(current_user)
        cover_preview = f'<img src="{cu}" style="width:100%;border-radius:12px;margin-bottom:12px;max-height:200px;object-fit:cover">'
    remove_btn = ""
    if current_user.profile_cover:
        remove_btn = f"""
        <form method="POST" style="margin-top:10px">
          <input type="hidden" name="remove_cover" value="1">
          <button type="submit" class="btn btn-danger" style="width:100%"
                  onclick="return confirm('حذف الغلاف؟')">🗑 حذف الغلاف</button>
        </form>"""
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>🖼 غلاف البروفايل</h2>
    {cover_preview}
    <form method="POST" enctype="multipart/form-data">
      <label>اختر صورة الغلاف</label>
      <input type="file" name="cover" accept="image/*" required>
      <button type="submit">💾 حفظ الغلاف</button>
    </form>
    {remove_btn}
    <a class="link-center" href="{url_for('profile_me')}">رجوع</a></div>""", title="الغلاف")


@app.route("/profile/chat-wallpaper", methods=["GET", "POST"])
@login_required
def edit_chat_wallpaper():
    if request.method == "POST":
        file = request.files.get("wallpaper")
        if file and file.filename:
            if not allowed_image(file.filename) or not check_image_magic(file):
                flash("صيغة غير مدعومة.", "error"); return redirect(url_for("edit_chat_wallpaper"))
            if current_user.chat_wallpaper:
                try:
                    old = os.path.join(app.config["COVER_FOLDER"], current_user.chat_wallpaper)
                    if os.path.exists(old): os.remove(old)
                except OSError: pass
            ext = file.filename.rsplit(".", 1)[1].lower()
            fn = f"wall_{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(app.config["COVER_FOLDER"], fn))
            current_user.chat_wallpaper = fn
        if request.form.get("remove_wallpaper") == "1" and current_user.chat_wallpaper:
            try:
                old = os.path.join(app.config["COVER_FOLDER"], current_user.chat_wallpaper)
                if os.path.exists(old): os.remove(old)
            except OSError: pass
            current_user.chat_wallpaper = ""
        db.session.commit()
        flash("تم تحديث خلفية الدردشة.", "success")
        return redirect(url_for("edit_chat_wallpaper"))
    preview = ""
    if current_user.chat_wallpaper:
        wp_url = url_for("serve_upload", subpath=f"covers/{current_user.chat_wallpaper}")
        preview = f'<img src="{wp_url}" style="width:100%;border-radius:12px;margin-bottom:12px;max-height:200px;object-fit:cover">'
    remove_btn = ""
    if current_user.chat_wallpaper:
        remove_btn = f"""
        <form method="POST" style="margin-top:10px">
          <input type="hidden" name="remove_wallpaper" value="1">
          <button type="submit" class="btn btn-danger" style="width:100%"
                  onclick="return confirm('حذف الخلفية؟')">🗑 حذف الخلفية</button>
        </form>"""
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>🖼 خلفية الدردشة</h2>
    {preview}
    <form method="POST" enctype="multipart/form-data">
      <label>اختر صورة</label>
      <input type="file" name="wallpaper" accept="image/*" required>
      <button type="submit">💾 حفظ</button>
    </form>
    {remove_btn}
    <a class="link-center" href="{url_for('profile_me')}">رجوع</a></div>""", title="خلفية الدردشة")


@app.route("/u/<username>")
def view_profile(username):
    user = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not user or user.is_banned:
        flash("المستخدم غير موجود.", "error"); return redirect(url_for("index"))
    if not current_user.is_authenticated:
        flash("سجّل الدخول.", "error"); return redirect(url_for("login"))
    is_own = current_user.id == user.id
    friend_state = "none"
    if not is_own:
        friend_state, _ = friendship_status(current_user.id, user.id)
    is_friend = friend_state == "friends"
    i_blocked_them = user.id in get_blocked_ids(current_user.id)
    they_blocked_me = user.id in get_blocked_by_ids(current_user.id)
    if not is_own:
        try:
            view_key = f"viewed_{user.id}"
            if time.time() - session.get(view_key, 0) > 86400:
                user.profile_views = (user.profile_views or 0) + 1
                db.session.commit()
                session[view_key] = time.time()
        except Exception: db.session.rollback()
    av_url = avatar_url(user)
    dot_html, status_text_html = online_status_html(user, show_text=True)
    cu = cover_url(user)
    if cu:
        if is_own:
            cover_html = f"""<div class="profile-cover-wrap">
              <img src="{cu}" onclick="openAvatar('{cu}')">
              <button class="cover-edit-btn" onclick="window.location.href='{url_for('edit_cover')}'">🖼 تغيير</button>
            </div>"""
        else:
            cover_html = f'<div class="profile-cover-wrap"><img src="{cu}" onclick="openAvatar(\'{cu}\')"></div>'
    else:
        if is_own:
            cover_html = (f'<div class="profile-cover-wrap no-cover" style="background:linear-gradient(135deg,#667eea,#764ba2)">'
                          f'<button class="cover-edit-btn" onclick="window.location.href=\'{url_for("edit_cover")}\'">➕ غلاف</button></div>')
        else:
            cover_html = '<div class="profile-cover-wrap no-cover" style="background:linear-gradient(135deg,#667ba2,#764ba2)"></div>'
    verified_big = verified_html(user, True)
    mood_cloud = ""
    if user.mood_text:
        mood_cloud = f'<div class="mood-cloud" title="{html_escape_text(user.mood_text)}">{html_escape_text(user.mood_text)}</div>'
    title_html = ""
    if user.custom_title:
        title_html = f'<div class="custom-title" style="background:{user.title_color or "#6b7280"}">{html_escape_text(user.custom_title)}</div>'
    if is_own or is_friend:
        profile_html = f"""
        <div class="name">{verified_big} {user.short_name}</div>
        {title_html}
        <div class="status-line">{status_text_html}</div>
        <div class="acct-box" style="margin-top:12px">
          <div class="acct-row"><span class="k">USERNAME</span>
            <span class="v">@{user.username} {copy_btn_html(user.username, "نسخ", small=True)}</span></div>
          <div class="acct-row"><span class="k">ID</span>
            <span class="v">{user.public_id} {copy_btn_html(user.public_id, "نسخ", small=True)}</span></div>
          <div class="acct-row"><span class="k">NICKNAME</span>
            <span class="v" style="font-family:inherit">{user.nickname or '—'}</span></div>
          <div class="acct-row"><span class="k">JOINED (SD)</span>
            <span class="v" style="font-family:inherit">{user.created_at_sd}</span></div>
        </div>"""
        if user.bio:
            profile_html += f'<div class="bio">{user.bio}</div>'
    else:
        profile_html = f"""
        <div class="name">{verified_big} {user.short_name}</div>
        {title_html}
        <div class="status-line">{status_text_html}</div>
        <div class="privacy-note">🔒 البيانات الكاملة للأصدقاء فقط.</div>"""
    actions = ""
    if is_own:
        actions = f"""
        <a class="btn btn-primary" href="{url_for('edit_profile')}">تعديل البروفايل</a>
        <a class="btn" href="{url_for('edit_cover')}">🖼 الغلاف</a>
        <a class="btn" href="{url_for('edit_chat_wallpaper')}">🖼 خلفية الدردشة</a>
        <a class="btn" href="{url_for('edit_extras')}">✨ مميزات إضافية</a>
        <a class="btn" href="{url_for('privacy_settings')}">🔒 الخصوصية</a>
        <a class="btn" href="{url_for('quick_replies')}">⚡ ردود سريعة</a>
        <a class="btn" href="{url_for('media_gallery')}">📷 الوسائط المشتركة</a>
        <a class="btn" href="{url_for('change_password')}">تغيير كلمة المرور</a>
        <a class="btn" href="{url_for('show_recovery_code')}">كود الاستعادة</a>
        <a class="btn" href="{url_for('devices_list')}">الأجهزة</a>
        <a class="btn" href="{url_for('blocked_list')}">🚫 المحظورون</a>
        <a class="btn" href="{url_for('archived_list')}">📦 الأرشيف</a>
        <a class="btn" href="{url_for('starred_messages')}">⭐ المثبتة</a>
        <a class="btn" href="{url_for('inbox')}">📩 المجهولة</a>
        <a class="btn btn-danger" href="{url_for('delete_account')}">🗑 مسح الحساب</a>
        <a class="btn" href="{url_for('logout')}">تسجيل الخروج</a>"""
    else:
        if i_blocked_them:
            actions = '<div class="blocked-badge">🚫 حظرت هذا المستخدم</div>'
            actions += f'<a class="btn btn-danger" href="{url_for("unblock_user", username=user.username)}">✅ إلغاء الحظر</a>'
        elif they_blocked_me:
            actions = '<div class="blocked-badge">🚫 لا يمكنك التفاعل</div>'
        else:
            if friend_state == 'none':
                actions = f'<a class="btn btn-primary" href="{url_for("friend_request", username=user.username)}">➕ إضافة صديق</a>'
                actions += f'<a class="btn" href="{url_for("send_message", username=user.username)}">✉ رسالة</a>'
                actions += f'<a class="btn btn-danger" href="{url_for("block_user", username=user.username)}" onclick="return confirm(\'حظر؟\')">🚫 حظر</a>'
                actions += f'<a class="btn btn-danger" href="{url_for("report_user", username=user.username)}">إبلاغ</a>'
            elif friend_state == 'pending_out':
                actions = f'<a class="btn" href="{url_for("friends_requests")}">⏳ بانتظار الرد</a>'
            elif friend_state == 'pending_in':
                actions = f'<a class="btn btn-primary" href="{url_for("friends_requests")}">✔ اقبل</a>'
            else:
                actions = f'<a class="btn btn-primary" href="{url_for("chat_with", username=user.username)}">💬 دردشة</a>'
                actions += '<div style="text-align:center;color:#25D366;font-weight:700;margin-top:4px">✓ صديقان</div>'
                actions += f'<a class="btn" href="{url_for("send_message", username=user.username)}">✉ رسالة</a>'
                actions += f'<a class="btn btn-danger" href="{url_for("unfriend_user", username=user.username)}" onclick="return confirm(\'حذف؟\')">✂ حذف صديق</a>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card" style="padding-top:0;overflow:hidden">
      {cover_html}
      <div class="center" style="padding-top:10px">
        <div class="avatar-wrap">
          {mood_cloud}
          <img class="avatar profile-avatar-overlap" src="{av_url}" onclick="openAvatar('{av_url}')">
          {dot_html}
        </div>
        {profile_html}
        <div class="actions">{actions}</div>
      </div>
    </div>""", title=user.username)


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()
        bio = request.form.get("bio", "").strip()
        if not is_valid_nickname(nickname):
            flash("اللقب: 1-4 كلمات.", "error"); return redirect(url_for("edit_profile"))
        if len(bio) > 200:
            flash("النبذة طويلة.", "error"); return redirect(url_for("edit_profile"))
        current_user.nickname = nickname
        current_user.bio = bio
        if request.form.get("remove_avatar") == "1" and current_user.avatar:
            try:
                old_path = os.path.join(app.config["AVATAR_FOLDER"], current_user.avatar)
                if os.path.exists(old_path): os.remove(old_path)
            except OSError: pass
            current_user.avatar = ""
        file = request.files.get("avatar")
        if file and file.filename:
            if not allowed_image(file.filename) or not check_image_magic(file):
                flash("صيغة غير مدعومة.", "error"); return redirect(url_for("edit_profile"))
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
    has_avatar = bool(current_user.avatar)
    delete_btn = ('<button type="button" class="btn btn-danger" style="width:100%;margin-top:10px" '
                  'onclick="requestDeleteAvatar()">🗑 حذف الصورة</button>') if has_avatar else ''
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
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
    function requestDeleteAvatar(){{if(confirm('حذف الصورة؟')){{
    document.getElementById('remove_avatar_flag').value='1';
    document.getElementById('edit-form').submit();}}}}
    </script>""", title="تعديل")


@app.route("/profile/extras", methods=["GET", "POST"])
@login_required
def edit_extras():
    if request.method == "POST":
        current_user.mood_text = request.form.get("mood_text", "").strip()[:64]
        current_user.custom_title = request.form.get("custom_title", "").strip()[:32]
        tc = request.form.get("title_color", "#6b7280").strip()
        if tc.startswith("#") and len(tc) in (4, 7): current_user.title_color = tc
        current_user.favorite_emojis = request.form.get("favorite_emojis", "").strip()[:200]
        try:
            dsec = int(request.form.get("default_disappear_seconds", 0))
            current_user.default_disappear_seconds = max(0, min(dsec, 604800))
        except (ValueError, TypeError): pass
        db.session.commit()
        flash("تم الحفظ.", "success")
        return redirect(url_for("profile_me"))
    dsec = current_user.default_disappear_seconds or 0
    def sel(v): return "selected" if dsec == v else ""
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>✨ مميزات إضافية</h2>
    <form method="POST">
      <label>💬 الحالة المزاجية (تظهر كغيمة فوق صورتك)</label>
      <input name="mood_text" maxlength="64" value="{current_user.mood_text or ''}" placeholder="مثال: مبسوط اليوم">
      <label>🏷 لقب مخصص</label>
      <input name="custom_title" maxlength="32" value="{current_user.custom_title or ''}" placeholder="مثال: الملك">
      <label>🎨 لون اللقب</label>
      <input type="color" name="title_color" value="{current_user.title_color or '#6b7280'}"
             style="width:60px;height:44px;padding:2px;cursor:pointer">
      <label>❤️ الإيموجيات المفضلة</label>
      <input name="favorite_emojis" maxlength="200" value="{current_user.favorite_emojis or ''}" style="direction:ltr">
      <label>⏱ وقت اختفاء الرسائل الافتراضي</label>
      <select name="default_disappear_seconds" style="width:100%;padding:12px;border-radius:10px;border:1px solid var(--border);background:var(--surface);color:var(--text)">
        <option value="0" {sel(0)}>🚫 مغلق</option>
        <option value="5" {sel(5)}>⏱ 5 ثواني</option>
        <option value="60" {sel(60)}>⏱ دقيقة</option>
        <option value="3600" {sel(3600)}>⏱ ساعة</option>
        <option value="86400" {sel(86400)}>⏱ 24 ساعة</option>
        <option value="604800" {sel(604800)}>⏱ أسبوع</option>
      </select>
      <button type="submit" style="margin-top:16px">💾 حفظ</button>
    </form>
    <a class="link-center" href="{url_for('profile_me')}">رجوع</a></div>""", title="مميزات")


@app.route("/profile/privacy", methods=["GET", "POST"])
@login_required
def privacy_settings():
    if request.method == "POST":
        for k in ("privacy_last_seen", "privacy_profile_photo", "privacy_about"):
            v = request.form.get(k, "everyone")
            if v in ("everyone", "contacts", "nobody"):
                setattr(current_user, k, v)
        current_user.notifications_enabled = request.form.get("notifications_enabled") == "1"
        current_user.read_receipts = request.form.get("read_receipts") == "1"
        db.session.commit()
        flash("تم حفظ إعدادات الخصوصية.", "success")
        return redirect(url_for("privacy_settings"))
    def sel(cur, v): return "selected" if cur == v else ""
    pls, ppp, pab = current_user.privacy_last_seen or "everyone", current_user.privacy_profile_photo or "everyone", current_user.privacy_about or "everyone"
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>🔒 الخصوصية</h2>
    <form method="POST">
      <label>👁 من يرى آخر ظهوري؟</label>
      <select name="privacy_last_seen" style="width:100%;padding:12px;border-radius:10px;border:1px solid var(--border)">
        <option value="everyone" {sel(pls,'everyone')}>👥 الجميع</option>
        <option value="contacts" {sel(pls,'contacts')}>👫 الأصدقاء فقط</option>
        <option value="nobody" {sel(pls,'nobody')}>🚫 لا أحد</option>
      </select>
      <label>📷 من يرى صورتي؟</label>
      <select name="privacy_profile_photo" style="width:100%;padding:12px;border-radius:10px;border:1px solid var(--border)">
        <option value="everyone" {sel(ppp,'everyone')}>👥 الجميع</option>
        <option value="contacts" {sel(ppp,'contacts')}>👫 الأصدقاء فقط</option>
        <option value="nobody" {sel(ppp,'nobody')}>🚫 لا أحد</option>
      </select>
      <label>💬 من يرى نبذتي؟</label>
      <select name="privacy_about" style="width:100%;padding:12px;border-radius:10px;border:1px solid var(--border)">
        <option value="everyone" {sel(pab,'everyone')}>👥 الجميع</option>
        <option value="contacts" {sel(pab,'contacts')}>👫 الأصدقاء فقط</option>
        <option value="nobody" {sel(pab,'nobody')}>🚫 لا أحد</option>
      </select>
      <label class="switch-row" style="margin-top:14px">
        <span>🔔 تفعيل الإشعارات</span>
        <input type="checkbox" name="notifications_enabled" value="1" {'checked' if current_user.notifications_enabled else ''}><span class="switch"></span></label>
      <label class="switch-row">
        <span>✓✓ إظهار علامة القراءة</span>
        <input type="checkbox" name="read_receipts" value="1" {'checked' if current_user.read_receipts else ''}><span class="switch"></span></label>
      <button type="submit" style="margin-top:16px">💾 حفظ</button>
    </form>
    <a class="link-center" href="{url_for('profile_me')}">رجوع</a></div>""", title="الخصوصية")


@app.route("/profile/quick-replies", methods=["GET", "POST"])
@login_required
def quick_replies():
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        if text and len(text) <= 200:
            if QuickReply.query.filter_by(user_id=current_user.id).count() >= 20:
                flash("الحد الأقصى 20.", "error")
            else:
                db.session.add(QuickReply(user_id=current_user.id, text=text))
                db.session.commit()
                flash("تم الإضافة.", "success")
        return redirect(url_for("quick_replies"))
    replies = QuickReply.query.filter_by(user_id=current_user.id).order_by(QuickReply.created_at.desc()).all()
    rows = ""
    for r in replies:
        rows += f"""<div class="list-item" style="cursor:default">
          <div style="flex:1">💬 {html_escape_text(r.text)}</div>
          <a class="btn btn-sm btn-danger" href="{url_for('quick_reply_delete', rid=r.id)}" onclick="return confirm('حذف؟')">🗑</a>
        </div>"""
    if not rows: rows = '<p class="empty">لا ردود سريعة.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>⚡ الردود السريعة ({len(replies)}/20)</h2>
    <form method="POST" style="margin-bottom:14px">
      <div style="display:flex;gap:8px">
        <input name="text" maxlength="200" placeholder="مثال: تمام، شكراً!" required style="flex:1;margin:0">
        <button type="submit" style="width:auto;padding:12px 20px;margin:0">➕</button>
      </div>
    </form>
    {rows}
    <a class="link-center" href="{url_for('profile_me')}">رجوع</a></div>""", title="الردود السريعة")


@app.route("/profile/quick-replies/<int:rid>/delete")
@login_required
def quick_reply_delete(rid):
    r = db.session.get(QuickReply, rid)
    if r and r.user_id == current_user.id:
        db.session.delete(r); db.session.commit()
        flash("تم الحذف.", "success")
    return redirect(url_for("quick_replies"))


@app.route("/profile/media")
@login_required
def media_gallery():
    msgs = ChatMessage.query.filter(
        or_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == current_user.id),
        ChatMessage.media != ""
    ).order_by(ChatMessage.created_at.desc()).limit(200).all()
    images, videos, audios = [], [], []
    for m in msgs:
        if m.media_type == "image": images.append(m)
        elif m.media_type == "video": videos.append(m)
        elif m.media_type == "audio": audios.append(m)
    def grid(items, icon):
        if not items: return '<p class="empty">لا عناصر.</p>'
        html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(90px,1fr));gap:8px">'
        for m in items:
            url = upload_url("chats", m.media)
            if m.media_type == "image":
                html += f'<img src="{url}" loading="lazy" style="width:100%;height:90px;object-fit:cover;border-radius:10px;cursor:pointer" onclick="openAvatar(\'{url}\')">'
            elif m.media_type == "video":
                html += f'<video src="{url}" preload="metadata" controls style="width:100%;height:90px;object-fit:cover;border-radius:10px"></video>'
            else:
                html += f'<div style="background:#f3f4f6;border-radius:10px;padding:8px;text-align:center;height:90px;display:flex;align-items:center;justify-content:center">{glow_icon("audio",32,"#25D366")}</div>'
        html += '</div>'
        return html
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>📷 الوسائط المشتركة</h2>
    <div style="font-weight:800;margin-bottom:8px">🖼 الصور ({len(images)})</div>{grid(images, 'image')}
    <div style="font-weight:800;margin:14px 0 8px">🎥 الفيديوهات ({len(videos)})</div>{grid(videos, 'video')}
    <div style="font-weight:800;margin:14px 0 8px">🎵 الصوتيات ({len(audios)})</div>{grid(audios, 'audio')}
    <a class="link-center" href="{url_for('profile_me')}">رجوع</a></div>""", title="الوسائط")


@app.route("/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old = request.form.get("old", "")
        new = request.form.get("new", "")
        confirm = request.form.get("confirm", "")
        if not check_password_hash(current_user.password_hash, old):
            flash("كلمة السر الحالية خاطئة.", "error"); return redirect(url_for("change_password"))
        if len(new) < 8 or new != confirm:
            flash("تحقق من كلمة السر الجديدة.", "error"); return redirect(url_for("change_password"))
        current_user.password_hash = generate_password_hash(new)
        db.session.commit()
        flash("تم التغيير.", "success")
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
    <label>تأكيد كلمة السر</label>
    <div class="pw-wrap"><input name="confirm" id="cp3" type="password" required>
    <button type="button" class="pw-toggle" onclick="togglePw('cp3')">👁</button></div>
    <button type="submit">تغيير</button></form>
    <a class="link-center" href="{{ url_for('profile_me') }}">رجوع</a></div>""", title="كلمة المرور")


@app.route("/recovery-code", methods=["GET", "POST"])
@login_required
def show_recovery_code():
    if request.method == "POST":
        if not check_password_hash(current_user.password_hash, request.form.get("password", "")):
            flash("كلمة السر خاطئة.", "error"); return redirect(url_for("show_recovery_code"))
        new_code = gen_recovery_code()
        while User.query.filter_by(recovery_hash=hash_recovery_code(new_code)).first():
            new_code = gen_recovery_code()
        current_user.recovery_hash = hash_recovery_code(new_code)
        db.session.commit()
        return render_page("""
        <div class="card center"><h2>🔐 كود الاستعادة الجديد</h2>
        <div style="background:#fffbeb;border:2px dashed #f59e0b;border-radius:12px;padding:16px;margin:14px 0;text-align:center">
        <div style="font-size:20px;font-weight:800;color:#92400e;letter-spacing:2px;line-height:1.8;margin:10px 0;direction:ltr;font-family:'Courier New',monospace;word-break:break-all">{{ formatted }}</div>
        <button class="copy-btn" onclick="copyText('{{ code }}',this)">نسخ</button></div>
        <a class="btn btn-primary" href="{{ url_for('profile_me') }}">رجوع</a></div>""",
            title="كود جديد", formatted=format_code(new_code), code=new_code)
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
        rows += f"""<div class="device-row">
        <div style="flex:1"><div><b>جهاز</b> — {fmt_sd(d.created_at)}</div>
        <div class="ua">{d.user_agent or 'غير معروف'}</div>
        <div style="font-size:11px;color:#6b7280">آخر نشاط: {fmt_sd(d.last_seen)}</div></div>
        <a class="btn btn-sm btn-danger" href="{url_for('device_remove', did=d.id)}" onclick="return confirm('إزالة؟')">إزالة</a></div>"""
    if not rows: rows = '<p class="empty">لا أجهزة.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>الأجهزة</h2>{rows}
    <a class="link-center" href="{url_for('profile_me')}">رجوع</a></div>""", title="الأجهزة")


@app.route("/device/remove/<int:did>")
@login_required
def device_remove(did):
    d = db.session.get(Device, did)
    if not d or d.user_id != current_user.id: abort(404)
    db.session.delete(d); db.session.commit()
    flash("تم الإزالة.", "success")
    return redirect(url_for("devices_list"))


@app.route("/starred")
@login_required
def starred_messages():
    msgs = ChatMessage.query.filter(
        ChatMessage.is_starred == True,
        or_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == current_user.id)
    ).order_by(ChatMessage.created_at.desc()).limit(200).all()
    rows = ""
    for m in msgs:
        peer = m.receiver if m.sender_id == current_user.id else m.sender
        body_txt = m.body or ("📷 صورة" if m.media_type == "image" else "🎥 فيديو" if m.media_type == "video" else "🎵 أغنية" if m.media_type == "audio" else "مرفق")
        rows += f"""<div class="list-item">
          <img class="avatar-sm" src="{avatar_url(peer)}">
          <a href="{url_for('chat_with', username=peer.username)}" style="flex:1;text-decoration:none;color:inherit;min-width:0">
            <div class="li-name">★ {peer.short_name}</div>
            <div class="li-sub">{html_escape_text(body_txt[:80])} · {fmt_sd(m.created_at, '%Y-%m-%d %H:%M')}</div></a>
        </div>"""
    if not rows: rows = '<p class="empty">لا رسائل مثبتة.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>⭐ المثبتة ({len(msgs)})</h2>{rows}
    <a class="link-center" href="{url_for('profile_me')}">رجوع</a></div>""", title="المثبتة")


# ═══════════════════ FRIENDS ═══════════════════
@app.route("/friends")
@login_required
def friends_list():
    friends = get_friends(current_user.id)
    incoming = Friendship.query.filter_by(addressee_id=current_user.id, status="pending").count()
    rows = ""
    for f in friends:
        dot, _ = online_status_html(f, show_text=False)
        rows += f"""<div class="list-item">
        <div class="avatar-wrap" style="margin-bottom:0">
          <img class="avatar-sm" src="{avatar_url(f)}" onclick="openAvatar('{avatar_url(f)}')">
          {dot}
        </div>
        <a href="{url_for('view_profile', username=f.username)}" style="flex:1;text-decoration:none;color:inherit">
          <div class="li-name">{verified_html(f)}{f.short_name}</div>
          <div class="li-sub">ID: {f.public_id}</div></a>
        <div class="li-actions">
          {copy_btn_html(f.username, "يوزر", small=True)}
          {copy_btn_html(f.public_id, "ID", small=True)}
          <a class="btn btn-sm btn-primary" href="{url_for('chat_with', username=f.username)}">دردشة</a>
          <a class="btn btn-sm btn-danger" href="{url_for('unfriend_user', username=f.username)}" onclick="return confirm('حذف؟')">✂</a>
        </div></div>"""
    if not rows: rows = '<p class="empty">لا أصدقاء.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>أصدقائي ({len(friends)})</h2>
    <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
      <a class="btn btn-sm" href="{url_for('friends_requests')}">طلبات {f'({incoming})' if incoming else ''}</a>
      <a class="btn btn-sm btn-primary" href="{url_for('discover')}">👥 اكتشف</a>
    </div>{rows}</div>""", title="الأصدقاء")


@app.route("/friends/requests")
@login_required
def friends_requests():
    incoming = Friendship.query.filter_by(addressee_id=current_user.id, status="pending").all()
    outgoing = Friendship.query.filter_by(requester_id=current_user.id, status="pending").all()
    inc = ""
    for r in incoming:
        u = r.requester
        if u.id in get_blocked_ids(current_user.id) or u.id in get_blocked_by_ids(current_user.id): continue
        inc += f"""<div class="list-item">
        <img class="avatar-sm" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
        <div style="flex:1"><div class="li-name">{verified_html(u)}{u.short_name}</div>
        <div class="li-sub">ID: {u.public_id}</div></div>
        <div class="li-actions">
          {copy_btn_html(u.username, "يوزر", small=True)}
          {copy_btn_html(u.public_id, "ID", small=True)}
          <a class="btn btn-sm btn-primary" href="{url_for('friend_accept', fid=r.id)}">قبول</a>
          <a class="btn btn-sm btn-danger" href="{url_for('friend_reject', fid=r.id)}">رفض</a>
        </div></div>"""
    if not inc: inc = '<p class="empty">لا طلبات واردة.</p>'
    out = ""
    for r in outgoing:
        u = r.addressee
        out += f"""<div class="list-item">
        <img class="avatar-sm" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
        <div style="flex:1"><div class="li-name">{verified_html(u)}{u.short_name}</div>
        <div class="li-sub">ID: {u.public_id} · بانتظار</div></div>
        <div class="li-actions">
          {copy_btn_html(u.username, "يوزر", small=True)}
          {copy_btn_html(u.public_id, "ID", small=True)}
          <a class="btn btn-sm btn-danger" href="{url_for('friend_reject', fid=r.id)}">إلغاء</a>
        </div></div>"""
    if not out: out = '<p class="empty">لا طلبات مرسلة.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>طلبات واردة</h2>{inc}</div>
    <div class="card"><h2>طلبات مرسلة</h2>{out}</div>""", title="طلبات")


@app.route("/friend/request/<username>")
@login_required
def friend_request(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not target:
        flash("غير موجود.", "error"); return redirect(url_for("discover"))
    if target.id == current_user.id:
        flash("لا يمكنك إضافة نفسك.", "error"); return redirect(url_for("profile_me"))
    if target.is_banned or target.under_review:
        flash("لا يمكن الإضافة.", "error"); return redirect(url_for("discover"))
    if is_blocked_between(current_user.id, target.id):
        flash("يوجد حظر.", "error"); return redirect(url_for("view_profile", username=target.username))
    state, _ = friendship_status(current_user.id, target.id)
    if state != "none":
        flash("الطلب موجود.", "error"); return redirect(url_for("view_profile", username=target.username))
    db.session.add(Friendship(requester_id=current_user.id, addressee_id=target.id, status="pending"))
    db.session.commit()
    flash(f"تم إرسال طلب إلى @{target.username}.", "success")
    return redirect(request.referrer or url_for("view_profile", username=target.username))


@app.route("/friend/accept/<int:fid>")
@login_required
def friend_accept(fid):
    r = db.session.get(Friendship, fid)
    if not r or r.addressee_id != current_user.id: abort(404)
    r.status = "accepted"; db.session.commit()
    flash("تم القبول.", "success")
    return redirect(url_for("friends_requests"))


@app.route("/friend/reject/<int:fid>")
@login_required
def friend_reject(fid):
    r = db.session.get(Friendship, fid)
    if not r or (r.addressee_id != current_user.id and r.requester_id != current_user.id): abort(404)
    db.session.delete(r); db.session.commit()
    flash("تم الحذف.", "success")
    return redirect(url_for("friends_requests"))


@app.route("/friend/remove/<username>")
@login_required
def unfriend_user(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not target:
        flash("غير موجود.", "error"); return redirect(url_for("friends_list"))
    r = Friendship.query.filter(Friendship.status == "accepted", or_(
        and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == target.id),
        and_(Friendship.requester_id == target.id, Friendship.addressee_id == current_user.id))).first()
    if not r:
        flash("لستما صديقين.", "error"); return redirect(url_for("friends_list"))
    db.session.delete(r)
    ArchivedChat.query.filter(or_(
        and_(ArchivedChat.user_id == current_user.id, ArchivedChat.peer_id == target.id),
        and_(ArchivedChat.user_id == target.id, ArchivedChat.peer_id == current_user.id)
    )).delete(synchronize_session=False)
    db.session.commit()
    flash(f"تم حذف @{target.username}.", "success")
    return redirect(request.referrer or url_for("friends_list"))


# ═══════════════════ BLOCK ═══════════════════
@app.route("/block/<username>")
@login_required
def block_user(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not target or target.id == current_user.id:
        flash("غير ممكن.", "error"); return redirect(url_for("search"))
    if Block.query.filter_by(blocker_id=current_user.id, blocked_id=target.id).first():
        flash("محظور بالفعل.", "error"); return redirect(url_for("view_profile", username=target.username))
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
        flash("غير موجود.", "error"); return redirect(url_for("blocked_list"))
    b = Block.query.filter_by(blocker_id=current_user.id, blocked_id=target.id).first()
    if not b:
        flash("غير محظور.", "error"); return redirect(url_for("blocked_list"))
    db.session.delete(b); db.session.commit()
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
        <img class="avatar-sm" src="{avatar_url(u)}">
        <a href="{url_for('view_profile', username=u.username)}" style="flex:1;text-decoration:none;color:inherit">
          <div class="li-name">{u.short_name}</div>
          <div class="li-sub">ID: {u.public_id}</div></a>
        <div class="li-actions">
          {copy_btn_html(u.username, "يوزر", small=True)}
          {copy_btn_html(u.public_id, "ID", small=True)}
          <a class="btn btn-sm btn-primary" href="{url_for('unblock_user', username=u.username)}">✅ إلغاء</a>
        </div></div>"""
    if not html: html = '<p class="empty">لا محظورين.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>🚫 المحظورون ({len(rows)})</h2>{html}
    <a class="link-center" href="{url_for('profile_me')}">رجوع</a></div>""", title="المحظورون")


# ═══════════════════ ARCHIVE ═══════════════════
@app.route("/archive/<username>", methods=["POST"])
@login_required
def archive_chat(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not target or target.id == current_user.id:
        flash("لا يمكن.", "error"); return redirect(url_for("chats"))
    if ArchivedChat.query.filter_by(user_id=current_user.id, peer_id=target.id).first():
        flash("مؤرشفة بالفعل.", "error"); return redirect(request.referrer or url_for("chats"))
    db.session.add(ArchivedChat(user_id=current_user.id, peer_id=target.id))
    db.session.commit()
    flash(f"تم أرشفة @{target.username}.", "success")
    return redirect(request.referrer or url_for("chats"))


@app.route("/unarchive/<username>", methods=["POST"])
@login_required
def unarchive_chat(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first()
    if not target:
        flash("غير موجود.", "error"); return redirect(url_for("archived_list"))
    a = ArchivedChat.query.filter_by(user_id=current_user.id, peer_id=target.id).first()
    if not a:
        flash("غير مؤرشفة.", "error"); return redirect(url_for("archived_list"))
    db.session.delete(a); db.session.commit()
    flash(f"تم إلغاء أرشفة @{target.username}.", "success")
    return redirect(request.referrer or url_for("archived_list"))


@app.route("/archived")
@login_required
def archived_list():
    rows = ArchivedChat.query.filter_by(user_id=current_user.id).order_by(ArchivedChat.created_at.desc()).all()
    html = ""
    for a in rows:
        u = a.peer
        html += f"""<div class="list-item">
        <img class="avatar-sm" src="{avatar_url(u)}">
        <a href="{url_for('chat_with', username=u.username)}" style="flex:1;text-decoration:none;color:inherit">
          <div class="li-name">📦 {u.short_name}</div>
          <div class="li-sub">ID: {u.public_id}</div></a>
        <div class="li-actions">
          {copy_btn_html(u.username, "يوزر", small=True)}
          {copy_btn_html(u.public_id, "ID", small=True)}
          <a class="btn btn-sm btn-primary" href="{url_for('chat_with', username=u.username)}">فتح</a>
          <a class="btn btn-sm btn-danger" href="{url_for('unarchive_chat', username=u.username)}">↩</a>
        </div></div>"""
    if not html: html = '<p class="empty">الأرشيف فارغ.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>📦 الأرشيف ({len(rows)})</h2>{html}
    <a class="link-center" href="{url_for('chats')}">رجوع</a></div>""", title="الأرشيف")


# ═══════════════════ DELETE ACCOUNT ═══════════════════
@app.route("/account/delete", methods=["GET", "POST"])
@login_required
def delete_account():
    if request.method == "POST":
        if not check_password_hash(current_user.password_hash, request.form.get("password", "")):
            flash("كلمة السر خاطئة.", "error"); return redirect(url_for("delete_account"))
        if request.form.get("confirm_text", "").strip() != "DELETE":
            flash("اكتب DELETE.", "error"); return redirect(url_for("delete_account"))
        uid = current_user.id
        try:
            if current_user.avatar:
                try: os.remove(os.path.join(app.config["AVATAR_FOLDER"], current_user.avatar))
                except OSError: pass
            if current_user.profile_cover:
                try: os.remove(os.path.join(app.config["COVER_FOLDER"], current_user.profile_cover))
                except OSError: pass
            if current_user.chat_wallpaper:
                try: os.remove(os.path.join(app.config["COVER_FOLDER"], current_user.chat_wallpaper))
                except OSError: pass
            for s in Status.query.filter_by(user_id=uid).all():
                StatusView.query.filter_by(status_id=s.id).delete(synchronize_session=False)
                if s.media:
                    try: os.remove(os.path.join(app.config["STATUS_FOLDER"], s.media))
                    except OSError: pass
                db.session.delete(s)
            for m in ChatMessage.query.filter(or_(ChatMessage.sender_id == uid, ChatMessage.receiver_id == uid)).all():
                if m.media:
                    try: os.remove(os.path.join(app.config["CHAT_FOLDER"], m.media))
                    except OSError: pass
                db.session.delete(m)
            Message.query.filter_by(receiver_id=uid).delete(synchronize_session=False)
            Friendship.query.filter(or_(Friendship.requester_id == uid, Friendship.addressee_id == uid)).delete(synchronize_session=False)
            Block.query.filter(or_(Block.blocker_id == uid, Block.blocked_id == uid)).delete(synchronize_session=False)
            ArchivedChat.query.filter(or_(ArchivedChat.user_id == uid, ArchivedChat.peer_id == uid)).delete(synchronize_session=False)
            SavedChat.query.filter(or_(SavedChat.user_id == uid, SavedChat.peer_id == uid)).delete(synchronize_session=False)
            QuickReply.query.filter_by(user_id=uid).delete(synchronize_session=False)
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
            u = db.session.get(User, uid)
            db.session.delete(u)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"خطأ: {e}", "error"); return redirect(url_for("delete_account"))
        logout_user()
        resp = make_response(redirect(url_for("login")))
        resp.delete_cookie("device_token")
        flash("تم مسح حسابك.", "success")
        return resp
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + """
    <div class="card"><h2 style="color:#991b1b">🗑 مسح الحساب</h2>
    <div class="danger-zone"><p style="font-size:13px;color:#7f1d1d;line-height:1.7">
      سيتم حذف <b>كل شيء</b> نهائيًا.</p></div>
    <form method="POST" style="margin-top:14px">
      <label>كلمة السر</label>
      <div class="pw-wrap"><input name="password" id="delpw" type="password" required>
      <button type="button" class="pw-toggle" onclick="togglePw('delpw')">👁</button></div>
      <label>اكتب <b style="color:#dc2626">DELETE</b></label>
      <input name="confirm_text" placeholder="DELETE" required style="text-align:center;font-weight:800;color:#dc2626">
      <button type="submit" style="background:#dc2626" onclick="return confirm('متأكد 100%؟')">🗑 مسح</button>
    </form>
    <a class="link-center" href="{{ url_for('profile_me') }}">← إلغاء</a></div>""", title="مسح")


# ═══════════════════ DISCOVER + SEARCH ═══════════════════
@app.route("/discover")
@login_required
def discover():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    excluded = get_blocked_ids(current_user.id) | get_blocked_by_ids(current_user.id)
    query = User.query.filter(User.is_banned == False, User.under_review == False, User.id != current_user.id)
    if excluded: query = query.filter(~User.id.in_(excluded))
    if q:
        ql = q.lower().lstrip("@")
        query = query.filter(or_(User.username.ilike(f"%{ql}%"), User.public_id.ilike(f"%{ql}%")))
    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=30, error_out=False)
    my_friends = get_friend_ids(current_user.id)
    pending_out = {r.addressee_id for r in Friendship.query.filter_by(requester_id=current_user.id, status="pending").all()}
    pending_in = {r.requester_id for r in Friendship.query.filter_by(addressee_id=current_user.id, status="pending").all()}
    rows = ""
    for u in pagination.items:
        if u.id in my_friends:
            action = '<span class="btn btn-sm btn-disabled" style="color:#16a34a">✓ صديق</span>'
        elif u.id in pending_out:
            action = '<span class="btn btn-sm btn-disabled">⏳</span>'
        elif u.id in pending_in:
            action = f'<a class="btn btn-sm btn-primary" href="{url_for("friends_requests")}">✔</a>'
        else:
            action = f'<a class="btn btn-sm btn-primary" href="{url_for("friend_request", username=u.username)}">➕</a>'
        dot, _ = online_status_html(u, show_text=False)
        rows += f"""<div class="list-item" style="cursor:default">
          <div class="avatar-wrap" style="margin-bottom:0">
            <a href="{url_for('view_profile', username=u.username)}">
              <img class="avatar-sm" src="{avatar_url(u)}" onclick="event.preventDefault();event.stopPropagation();openAvatar('{avatar_url(u)}')">
            </a>
            {dot}
          </div>
          <a href="{url_for('view_profile', username=u.username)}" style="flex:1;text-decoration:none;color:inherit;min-width:0">
            <div class="li-name">{verified_html(u)}{u.short_name}</div>
            <div class="li-sub">ID: {u.public_id}</div></a>
          <div class="li-actions">
            {copy_btn_html(u.username, "يوزر", small=True)}
            {copy_btn_html(u.public_id, "ID", small=True)}
            {action}</div></div>"""
    if not rows: rows = '<p class="empty">لا نتائج.</p>'
    nav = ""
    if pagination.pages > 1:
        nav = '<div style="display:flex;gap:6px;justify-content:center;margin-top:14px;flex-wrap:wrap">'
        if pagination.has_prev:
            nav += f'<a class="btn btn-sm" href="{url_for("discover", page=pagination.prev_num, q=q)}">←</a>'
        nav += f'<span class="btn btn-sm btn-disabled">{pagination.page}/{pagination.pages}</span>'
        if pagination.has_next:
            nav += f'<a class="btn btn-sm" href="{url_for("discover", page=pagination.next_num, q=q)}">→</a>'
        nav += '</div>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>👥 اكتشف ({pagination.total})</h2>
    <form method="GET" style="display:flex;gap:8px;margin:10px 0">
      <input name="q" value="{q}" placeholder="ابحث" style="flex:1;margin:0">
      <button type="submit" style="width:auto;padding:12px 20px;margin:0">بحث</button></form>
    {rows}{nav}</div>""", title="اكتشف")


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
        if excluded: query = query.filter(~User.id.in_(excluded))
        users_results = query.limit(50).all()
    users_block = ""
    for u in users_results:
        state, _ = friendship_status(current_user.id, u.id)
        if state == "friends":
            action = '<span class="btn btn-sm btn-disabled" style="color:#16a34a">✓</span>'
        elif state == "pending_out":
            action = '<span class="btn btn-sm btn-disabled">⏳</span>'
        elif state == "pending_in":
            action = f'<a class="btn btn-sm btn-primary" href="{url_for("friends_requests")}">✔</a>'
        else:
            action = f'<a class="btn btn-sm btn-primary" href="{url_for("friend_request", username=u.username)}">➕</a>'
        users_block += f"""<div class="list-item" style="cursor:default">
        <img class="avatar-sm" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
        <a href="{url_for('view_profile', username=u.username)}" style="flex:1;text-decoration:none;color:inherit;min-width:0">
        <div class="li-name">{verified_html(u)}{u.short_name}</div>
        <div class="li-sub">ID: {u.public_id}</div></a>
        <div class="li-actions">
          {copy_btn_html(u.username, "يوزر", small=True)}
          {copy_btn_html(u.public_id, "ID", small=True)}
          {action}</div></div>"""
    if not users_block and q: users_block = '<p class="empty">لا نتائج.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>🔍 البحث</h2>
    <form method="GET" style="display:flex;gap:8px">
      <input name="q" value="{q}" placeholder="username أو ID" style="flex:1;margin:0" autofocus>
      <button type="submit" style="width:auto;padding:12px 20px;margin:0">بحث</button></form>
    <a class="link-center" href="{url_for('discover')}">👥 اكتشف الجميع</a></div>
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
        if privacy not in ("public", "friends"): privacy = "public"
        file = request.files.get("media")
        media_fn = ""; media_type = ""
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
                flash("صيغة غير مدعومة.", "error"); return redirect(url_for("post_status"))
        if not text and not media_fn:
            flash("أضف نصًا أو وسائط.", "error"); return redirect(url_for("post_status"))
        db.session.add(Status(user_id=current_user.id, text=text[:300], caption=caption[:300],
                              media=media_fn, media_type=media_type, privacy=privacy, show_viewers=show_viewers))
        db.session.commit()
        flash("تم نشر الحالة.", "success")
        return redirect(url_for("feed"))
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + """
    <div class="card"><h2>📸 حالة جديدة</h2>
    <form method="POST" enctype="multipart/form-data">
      <label>👁 من يرى الحالة؟</label>
      <div class="privacy-choice">
        <label class="privacy-opt">
          <input type="radio" name="privacy" value="public" checked>
          <div class="pbox"><span class="picon">🌍</span><span class="ptitle">عامة</span><span class="psub">للجميع</span></div>
        </label>
        <label class="privacy-opt">
          <input type="radio" name="privacy" value="friends">
          <div class="pbox"><span class="picon">👥</span><span class="ptitle">خاصة</span><span class="psub">للأصدقاء</span></div>
        </label>
      </div>
      <label>النص (اختياري)</label>
      <textarea name="text" maxlength="300" placeholder="اكتب..."></textarea>
      <label>الوسائط (صورة أو فيديو)</label>
      <input type="file" name="media" accept="image/*,video/*" onchange="previewStatusMedia(this)">
      <div id="status-preview"></div>
      <label>وصف الوسائط (اختياري)</label>
      <input name="caption" maxlength="300" placeholder="وصف...">
      <label class="switch-row" style="margin-top:14px">
        <span>👁 إظهار المشاهدين</span>
        <input type="checkbox" name="show_viewers" value="1"><span class="switch"></span></label>
      <button type="submit">نشر</button></form>
    <a class="link-center" href="{{ url_for('feed') }}">رجوع</a></div>""", title="حالة جديدة")


@app.route("/status/<int:sid>/delete")
@login_required
def delete_status(sid):
    s = db.session.get(Status, sid)
    if not s or s.user_id != current_user.id: abort(403)
    if s.media:
        try: os.remove(os.path.join(app.config["STATUS_FOLDER"], s.media))
        except OSError: pass
    StatusView.query.filter_by(status_id=s.id).delete(synchronize_session=False)
    db.session.delete(s); db.session.commit()
    flash("تم الحذف.", "success")
    return redirect(url_for("feed"))


@app.route("/status/<int:sid>/viewers")
@login_required
def status_viewers(sid):
    s = db.session.get(Status, sid)
    if not s or s.user_id != current_user.id: abort(403)
    if not s.show_viewers:
        flash("غير مفعّل.", "error"); return redirect(url_for("feed"))
    views = StatusView.query.filter_by(status_id=sid).order_by(StatusView.viewed_at.desc()).all()
    rows = ""
    for v in views:
        u = v.viewer
        rows += f"""<div class="list-item" style="cursor:default">
        <img class="avatar-sm" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
        <a href="{url_for('view_profile', username=u.username)}" style="flex:1;text-decoration:none;color:inherit">
          <div class="li-name">{verified_html(u)}{u.short_name}</div>
          <div class="li-sub">{fmt_sd(v.viewed_at, '%H:%M')}</div></a>
        <div class="li-actions">
          {copy_btn_html(u.username, "يوزر", small=True)}
          {copy_btn_html(u.public_id, "ID", small=True)}
        </div></div>"""
    if not rows: rows = '<p class="empty">لا مشاهدين.</p>'
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>👁 المشاهدون ({len(views)})</h2>{rows}
    <a class="link-center" href="{url_for('feed')}">رجوع</a></div>""", title="المشاهدون")


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
        if s.user_id in excluded: continue
        if s.user_id == current_user.id: visible.append(s)
        elif s.privacy == "public": visible.append(s)
        elif s.privacy == "friends" and s.user_id in my_friend_ids: visible.append(s)
    by_user = {}
    for s in visible: by_user.setdefault(s.user_id, []).append(s)
    for s in visible:
        if s.user_id != current_user.id and s.show_viewers:
            if not StatusView.query.filter_by(status_id=s.id, viewer_id=current_user.id).first():
                db.session.add(StatusView(status_id=s.id, viewer_id=current_user.id))
    try: db.session.commit()
    except Exception: db.session.rollback()
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
                    next_id = items[idx+1].id if idx < len(items)-1 else ''
                    media_html = (f'<video controls preload="none" src="{url}" id="vid-{s.id}" '
                                  f'data-next="{next_id}" onclick="this.play()"></video>')
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
                  <a class="sbtn del" href="{url_for('delete_status', sid=s.id)}" onclick="return confirm('حذف؟')">🗑</a>
                </div>"""
            bottom_actions = ""
            if s.user_id != current_user.id:
                state, _ = friendship_status(current_user.id, s.user_id)
                if state == "friends":
                    bottom_actions = f"""<div class="status-actions-bottom">
                      <a class="action-btn chat" href="{url_for('chat_with', username=s.user.username)}">💬 دردشة</a>
                      <a class="action-btn profile" href="{url_for('view_profile', username=s.user.username)}">👤 بروفايل</a></div>"""
                elif state == "none":
                    bottom_actions = f"""<div class="status-actions-bottom">
                      <a class="action-btn add" href="{url_for('friend_request', username=s.user.username)}">➕ إضافة</a>
                      <a class="action-btn profile" href="{url_for('view_profile', username=s.user.username)}">👤 بروفايل</a></div>"""
            nav_html = ""
            if len(items) > 1:
                prev_btn = ""
                next_btn = ""
                if idx > 0:
                    prev_btn = f'<button class="nav-btn" onclick="event.stopPropagation();closeStatus({s.id});openStatus({items[idx-1].id})">◀</button>'
                if idx < len(items) - 1:
                    next_btn = f'<button class="nav-btn" onclick="event.stopPropagation();closeStatus({s.id});openStatus({items[idx+1].id})">▶</button>'
                nav_html = f"""<div class="status-nav">{prev_btn}<span class="counter">{idx+1}/{len(items)}</span>{next_btn}</div>"""
            privacy_label = "🌍 عامة" if s.privacy == "public" else "👥 خاصة"
            status_viewers_html += f"""<div class="status-view" id="sv-{s.id}" style="display:none">
              {owner_actions}
              <button class="close" onclick="closeStatus({s.id})">✕</button>
              {media_html}
              {f'<div class="stext">{s.text}</div>' if s.text else ''}
              {f'<div class="scaption">{s.caption}</div>' if s.caption else ''}
              <div class="smeta">{verified_html(s.user)} {s.user.short_name} · {fmt_sd(s.created_at)} · {privacy_label}</div>
              {bottom_actions}
              {nav_html}
            </div>"""
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card">
      <h2 style="text-align:right;font-size:15px">الحالات (24 ساعة)</h2>
      <div class="status-strip">
        <a class="status-item" href="{url_for('post_status')}">
          <span class="ring" style="background:#e5e7eb"><img src="{avatar_url(current_user)}" style="opacity:.5"></span>
          <div class="sname">+ أضف</div></a>
        {status_strip}
      </div>
      {('<p class="empty" style="padding:10px 0">لا حالات حديثة.</p>') if not status_strip else ''}
    </div>
    {status_viewers_html}
    <script>
    document.querySelectorAll('video[id^="vid-"]').forEach(function(v){{
      v.addEventListener('ended', function(){{
        var nextId = v.getAttribute('data-next');
        var currentId = v.id.replace('vid-', '');
        closeStatus(currentId);
        if (nextId) {{
          openStatus(parseInt(nextId));
          var nextVid = document.getElementById('vid-' + nextId);
          if (nextVid) setTimeout(function(){{nextVid.play();}}, 300);
        }}
      }});
    }});
    </script>""", title="الرئيسية")
    # ═══════════════════════════════════════════════════════════════
# CHATS
# ═══════════════════════════════════════════════════════════════
@app.route("/chats")
@login_required
def chats():
    friends = get_friends(current_user.id)
    archived = ArchivedChat.query.filter_by(user_id=current_user.id).all()
    archived_ids = {a.peer_id for a in archived}
    items = []
    for f in friends:
        if f.id in archived_ids: continue
        last_msg = ChatMessage.query.filter(or_(
            and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == f.id),
            and_(ChatMessage.sender_id == f.id, ChatMessage.receiver_id == current_user.id)
        )).order_by(ChatMessage.created_at.desc()).first()
        unread = ChatMessage.query.filter_by(sender_id=f.id, receiver_id=current_user.id, is_read=False).count()
        items.append((last_msg.created_at if last_msg else f.created_at, f, last_msg, unread))
    items.sort(key=lambda x: -x[0].timestamp() if x[0] else 0)
    rows = ""
    for _, f, last_msg, unread in items:
        preview = "ابدأ الدردشة"
        time_str = ""
        if last_msg:
            if last_msg.body: preview = last_msg.body[:40]
            elif last_msg.media_type == "image": preview = "📷 صورة"
            elif last_msg.media_type == "video": preview = "🎥 فيديو"
            elif last_msg.media_type == "audio": preview = "🎵 أغنية"
            time_str = fmt_sd(last_msg.created_at, "%H:%M")
        unread_tag = f'<span class="badge pulse" style="position:static;margin-right:6px">{unread}</span>' if unread else ''
        dot, _ = online_status_html(f, show_text=False)
        rows += f"""<div class="list-item">
          <div class="avatar-wrap" style="margin-bottom:0">
            <img class="avatar-sm" src="{avatar_url(f)}" onclick="openAvatar('{avatar_url(f)}')">
            {dot}
          </div>
          <a href="{url_for('chat_with', username=f.username)}" style="flex:1;text-decoration:none;color:inherit;min-width:0">
            <div class="li-name">{verified_html(f)}{f.short_name} {unread_tag}</div>
            <div class="li-sub">{preview}</div></a>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">
            <div class="li-sub">{time_str}</div>
            <div style="display:flex;gap:4px">
              {copy_btn_html(f.username, "يوزر", small=True)}
              {copy_btn_html(f.public_id, "ID", small=True)}
              <form method="POST" action="{url_for('archive_chat', username=f.username)}" style="margin:0">
                <button type="submit" class="copy-btn" style="padding:2px 8px;font-size:11px">📦</button>
              </form>
            </div>
          </div></div>"""
    if not rows: rows = '<p class="empty">لا محادثات.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>💬 الدردشات</h2>
    <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
      <a class="btn btn-sm" href="{url_for('friends_list')}">الأصدقاء</a>
      <a class="btn btn-sm" href="{url_for('discover')}">👥 اكتشف</a>
      <a class="btn btn-sm" href="{url_for('inbox')}">📩 المجهولة</a>
      {f'<a class="btn btn-sm" href="{url_for("archived_list")}">📦 الأرشيف ({len(archived_ids)})</a>' if archived_ids else ''}
    </div>{rows}</div>""", title="الدردشات")


def render_bubble_chat(m, current_user, peer):
    cls = "me" if m.sender_id == current_user.id else "them"
    is_mine = (m.sender_id == current_user.id)
    media_html = ""
    if m.media:
        url = upload_url("chats", m.media)
        if m.media_type == "video":
            media_html = f'<video src="{url}" controls style="max-width:100%;border-radius:8px;margin-bottom:4px;max-height:320px"></video>'
        elif m.media_type == "audio":
            media_html = f'<div class="audio-bubble">{glow_icon("audio", 24, "#25D366")}<audio src="{url}" controls></audio></div>'
        else:
            media_html = f'<img src="{url}" style="max-width:100%;border-radius:8px;margin-bottom:4px;max-height:320px;cursor:pointer" onclick="event.stopPropagation();openAvatar(\'{url}\')">'
    body_html = f'<div>{linkify_text(m.body)}</div>' if m.body else ""
    tick_html = ""
    if is_mine:
        tick_html = '<span class="read-tick read">✓✓</span>' if m.is_read else '<span class="read-tick">✓</span>'
    header_html = ""
    if is_mine:
        header_html = f"""<a class="sender-head" href="{url_for('profile_me')}" onclick="event.stopPropagation()">
           <img src="{avatar_url(current_user)}" class="sender-avatar">
           <span class="sender-name">{verified_html(current_user)}{html_escape_text(current_user.short_name)}</span></a>"""
    else:
        header_html = f"""<a class="sender-head" href="{url_for('view_profile', username=peer.username)}" onclick="event.stopPropagation()">
           <img src="{avatar_url(peer)}" class="sender-avatar">
           <span class="sender-name">{verified_html(peer)}{html_escape_text(peer.short_name)}</span></a>"""
    reply_html = ""
    if m.reply_to_id:
        orig = db.session.get(ChatMessage, m.reply_to_id)
        if orig:
            orig_text = orig.body or ("📷 صورة" if orig.media_type == "image" else "🎥 فيديو" if orig.media_type == "video" else "🎵 أغنية" if orig.media_type == "audio" else "مرفق")
            orig_name = "أنت" if orig.sender_id == current_user.id else peer.short_name
            reply_html = f"""<div class="reply-quote">
              <div class="rq-name">{html_escape_text(orig_name)}</div>
              <div class="rq-body">{html_escape_text(orig_text[:120])}</div></div>"""
    # ✅ استخدم أشكال مضيئة بدل الإيموجي
    reaction_html = ""
    if m.reaction:
        icon_map = {"❤️": "heart", "👍": "thumb", "😂": "laugh", "😮": "wow", "😢": "sad", "🙏": "pray"}
        icon_name = icon_map.get(m.reaction)
        if icon_name:
            reaction_html = f'<span class="reaction-badge">{glow_reaction_icon(icon_name)}</span>'
        else:
            reaction_html = f'<span class="reaction-badge">{html_escape_text(m.reaction)}</span>'
    star_html = f'<span class="star-badge">{glow_icon("star", 12, "#fff")}</span>' if m.is_starred else ""
    disappear_badge = ""
    if m.expires_at:
        remain = (m.expires_at - now_utc_naive()).total_seconds()
        if remain > 0:
            label = f"{int(remain)}ث" if remain < 60 else f"{int(remain//60)}د" if remain < 3600 else f"{int(remain//3600)}س" if remain < 86400 else f"{int(remain//86400)}ي"
            disappear_badge = f'<span class="disappear-badge">{glow_icon("clock", 10, "#92400e")} {label}</span>'
    body_esc_js = (m.body or "").replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")[:60]
    peer_name_js = ("أنت" if is_mine else peer.short_name).replace("'", "\\'")
    delete_btn = f'<button type="button" class="act-btn delete" onclick="event.stopPropagation();deleteMsg({m.id})">{glow_icon("trash", 14, "#991b1b")} حذف</button>' if is_mine else ""
    clear_react_btn = f'<button type="button" class="act-btn clear-react" onclick="event.stopPropagation();clearReact({m.id})">{glow_icon("close", 14, "#92400e")} إزالة التفاعل</button>' if m.reaction else ""
    star_icon = glow_icon("star", 14, "#854d0e") if m.is_starred else glow_icon("star_outline", 14, "#854d0e")
    star_btn = f'<button type="button" class="act-btn star" onclick="event.stopPropagation();toggleStar({m.id})">{star_icon} {"إزالة النجمة" if m.is_starred else "تثبيت"}</button>'
    return f"""<div class="bubble-wrap">
      <div class="bubble {cls} clickable" id="msg-{m.id}" onclick="toggleMsgBar({m.id})" ondblclick="event.stopPropagation();doubleTap({m.id})">
        {header_html}{reply_html}{media_html}{body_html}
        <span class="t">{disappear_badge}{fmt_sd(m.created_at, "%H:%M")} {tick_html}</span>
        {reaction_html}{star_html}
      </div>
      <div class="msg-action-bar" id="bar-{m.id}" onclick="event.stopPropagation()">
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReact({m.id},'❤️')">{glow_reaction_icon("heart")}</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReact({m.id},'👍')">{glow_reaction_icon("thumb")}</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReact({m.id},'😂')">{glow_reaction_icon("laugh")}</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReact({m.id},'😮')">{glow_reaction_icon("wow")}</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReact({m.id},'😢')">{glow_reaction_icon("sad")}</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReact({m.id},'🙏')">{glow_reaction_icon("pray")}</button>
        <span class="act-divider"></span>
        <button type="button" class="act-btn" onclick="event.stopPropagation();setReply({m.id}, '{body_esc_js}', '{peer_name_js}')">{glow_icon("reply", 14)} رد</button>
        {star_btn}{clear_react_btn}{delete_btn}
        <button type="button" class="act-btn report" onclick="event.stopPropagation();reportChat()">{glow_icon("alert", 14, "#991b1b")} إبلاغ</button>
      </div>
    </div>"""


@app.route("/chat/<username>", methods=["GET", "POST"])
@login_required
def chat_with(username):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    if peer.id == current_user.id:
        flash("لا يمكنك محادثة نفسك.", "error"); return redirect(url_for("chats"))
    if is_blocked_between(current_user.id, peer.id):
        flash("يوجد حظر.", "error"); return redirect(url_for("chats"))
    state, _ = friendship_status(current_user.id, peer.id)
    if state != "friends":
        flash("يجب أن تكونا صديقين.", "error")
        return redirect(url_for("view_profile", username=peer.username))
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        file = request.files.get("media")
        reply_to_id = request.form.get("reply_to_id", type=int)
        disappear_sec = request.form.get("disappear_seconds", type=int) or 0
        is_view_once = request.form.get("view_once") == "1"
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
        if not body and not media_fn:
            flash("الرسالة فارغة.", "error"); return redirect(url_for("chat_with", username=peer.username))
        reply_obj = None
        if reply_to_id:
            reply_obj = ChatMessage.query.filter(
                ChatMessage.id == reply_to_id,
                or_(and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == peer.id),
                    and_(ChatMessage.sender_id == peer.id, ChatMessage.receiver_id == current_user.id))).first()
            if not reply_obj: reply_to_id = None
        expires_at = now_utc_naive() + timedelta(seconds=disappear_sec) if disappear_sec > 0 else None
        db.session.add(ChatMessage(sender_id=current_user.id, receiver_id=peer.id,
                                    body=body[:2000], media=media_fn, media_type=media_type,
                                    reply_to_id=reply_to_id if reply_obj else None,
                                    expires_at=expires_at, is_view_once=is_view_once))
        db.session.commit()
        return redirect(url_for("chat_with", username=peer.username))
    ChatMessage.query.filter_by(sender_id=peer.id, receiver_id=current_user.id, is_read=False).update({"is_read": True})
    view_once_msgs = ChatMessage.query.filter_by(sender_id=peer.id, receiver_id=current_user.id, is_view_once=True, viewed_once=False).all()
    for vm in view_once_msgs: vm.viewed_once = True
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
            typing_text = f'<span class="typing-name">{html_escape_text(typing_users[0].short_name)}</span> يكتب'
        return jsonify({"html": build_bubbles(), "unread": unread_chat_count(current_user.id), "typing": typing_text})
    bubbles = build_bubbles()
    is_archived = ArchivedChat.query.filter_by(user_id=current_user.id, peer_id=peer.id).first() is not None
    if is_archived:
        arch_action = f"""<form method="POST" action="{url_for('unarchive_chat', username=peer.username)}" style="margin:0">
          <button type="submit" class="btn btn-sm">↩ إلغاء الأرشفة</button></form>"""
    else:
        arch_action = f"""<form method="POST" action="{url_for('archive_chat', username=peer.username)}" style="margin:0">
          <button type="submit" class="btn btn-sm">📦 أرشفة</button></form>"""
    dot, status_text = online_status_html(peer, show_text=True)
    bg_style = ""
    if current_user.chat_wallpaper:
        bg_url = url_for("serve_upload", subpath=f"covers/{current_user.chat_wallpaper}")
        bg_style = f'style="background-image:url(\'{bg_url}\')"'
    peer_verified = verified_html(peer, True)
    qreps = QuickReply.query.filter_by(user_id=current_user.id).order_by(QuickReply.created_at.desc()).limit(10).all()
    qr_html = ""
    if qreps:
        qr_html = '<div class="chat-options" style="border-top:none;padding-top:4px">'
        qr_html += f'<span style="font-size:11px;color:#6b7280;margin-left:4px">{glow_icon("send",12,"#6b7280")} سريع:</span>'
        for q in qreps:
            safe = q.text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
            qr_html += f'<button type="button" onclick="fillQuick(\'{safe}\')">{html_escape_text(q.text[:20])}</button>'
        qr_html += '</div>'
    default_ds = current_user.default_disappear_seconds or 0
    def dsel(v): return 'active' if default_ds == v else ''
    disappear_html = f"""
    <div class="disappear-selector" id="disappear-selector">
      <span style="font-size:11px;color:#92400e;font-weight:700;align-self:center">{glow_icon("clock",14,"#92400e")} اختفاء:</span>
      <button type="button" class="dopt {dsel(0)}" onclick="setDisappear(0, this)">🚫</button>
      <button type="button" class="dopt {dsel(5)}" onclick="setDisappear(5, this)">5ث</button>
      <button type="button" class="dopt {dsel(60)}" onclick="setDisappear(60, this)">1د</button>
      <button type="button" class="dopt {dsel(3600)}" onclick="setDisappear(3600, this)">1س</button>
      <button type="button" class="dopt {dsel(86400)}" onclick="setDisappear(86400, this)">24س</button>
    </div>"""
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card">
      <div class="chat-header">
        <a href="{url_for('chats')}" class="btn btn-sm">{glow_icon("back",14)}</a>
        <div class="avatar-wrap" style="margin-bottom:0">
          <img class="avatar-sm" src="{avatar_url(peer)}" onclick="openAvatar('{avatar_url(peer)}')">
          {dot}
        </div>
        <div><div class="pn">{peer_verified} {peer.short_name}</div>
          <div class="pu">{status_text}</div></div>
        <div style="margin-right:auto;display:flex;gap:6px;align-items:center;flex-wrap:wrap">
          {copy_btn_html(peer.username, "يوزر", small=True)}
          {copy_btn_html(peer.public_id, "ID", small=True)}
          {share_link_btn_html()}
          {arch_action}
          <button type="button" class="btn btn-sm" onclick="toggleSearch()">{glow_icon("search",14)} بحث</button>
          <a class="btn btn-sm" href="{url_for('view_profile', username=peer.username)}">البروفايل</a>
          <button type="button" class="btn btn-sm" style="background:#fef2f2;color:#991b1b;border-color:#fecaca"
                  onclick="clearChatConfirm()">{glow_icon("trash",14,"#991b1b")} حذف</button>
        </div>
      </div>
      <div class="chat-search-bar" id="search-bar" style="display:none">
        <input type="text" id="search-input" placeholder="ابحث..." oninput="filterMessages()">
        <button type="button" class="btn btn-sm" onclick="toggleSearch()">✕</button>
      </div>
      <div class="chat-box" id="chatbox" {bg_style}>{bubbles}</div>
      <button type="button" class="scroll-bottom-btn" id="scroll-bottom-btn" onclick="scrollToBottom()">{glow_icon("arrow_down",20,"#fff")}</button>
      <div id="reply-preview" class="reply-preview" style="display:none">
        <div class="rp-info"><div class="rp-name" id="rp-name"></div><div class="rp-body" id="rp-body"></div></div>
        <button type="button" class="rp-close" onclick="cancelReply()">✕</button>
      </div>
      <div class="typing-indicator" id="typing-indicator">
        <span class="typing-dots"><span></span><span></span><span></span></span>
        <span id="typing-text"></span>
      </div>
      {qr_html}
      <form class="chat-input" method="POST" enctype="multipart/form-data" id="chat-form">
        <input type="hidden" name="reply_to_id" id="reply_to_id" value="">
        <input type="hidden" name="disappear_seconds" id="disappear_seconds" value="{default_ds}">
        <input type="file" name="media" id="chat-media-input" accept="image/*,video/*,audio/*"
               style="display:none" onchange="previewChatMedia(this)">
        <button type="button" class="icon-btn" onclick="document.getElementById('chat-media-input').click()">{glow_icon("attach",22,"#fff")}</button>
        <input name="body" id="chat-body-input" placeholder="اكتب رسالة..." autocomplete="off">
        <button type="submit">{glow_icon("send",20,"#fff")}</button>
      </form>
      <div id="chat-media-preview" style="margin-top:8px"></div>
      {disappear_html}
      <label class="switch-row" style="margin-top:8px">
        <span>🔥 إرسال كعرض مرة واحدة</span>
        <input type="checkbox" name="view_once" id="view_once_cb" value="1" form="chat-form"><span class="switch"></span></label>
      <div class="chat-options">
        <button type="button" onclick="muteChat()">{glow_icon("mute",14)} كتم الإشعارات</button>
      </div>
    </div>
    <script>
    startChatAutoRefresh('{url_for("chat_with", username=peer.username)}', 1500);
    (function(){{
      var inp = document.getElementById('chat-body-input');
      var lastSent = 0;
      if(inp){{
        inp.addEventListener('input', function(){{
          var now = Date.now();
          if(now - lastSent > 2000){{
            lastSent = now;
            fetch('{url_for("chat_typing", username=peer.username)}', {{method:'POST', credentials:'same-origin', headers: {{'Content-Type':'application/json'}}}}).catch(function(){{}});
          }}
        }});
      }}
    }})();
    function setDisappear(sec, btn){{
      document.getElementById('disappear_seconds').value = sec;
      document.querySelectorAll('#disappear-selector .dopt').forEach(function(b){{b.classList.remove('active');}});
      btn.classList.add('active');
    }}
    function fillQuick(txt){{
      var inp=document.getElementById('chat-body-input');
      if(inp){{inp.value=txt;inp.focus();}}
    }}
    function toggleSearch(){{
      var b = document.getElementById('search-bar');
      if(!b) return;
      b.style.display = b.style.display === 'none' ? 'flex' : 'none';
      if(b.style.display === 'flex') document.getElementById('search-input').focus();
      else {{ document.getElementById('search-input').value=''; filterMessages(); }}
    }}
    function filterMessages(){{
      var q = (document.getElementById('search-input').value || '').toLowerCase().trim();
      document.querySelectorAll('.bubble').forEach(function(b){{
        if(!q){{ b.style.opacity='1'; return; }}
        var txt = (b.textContent || '').toLowerCase();
        b.style.opacity = txt.indexOf(q) >= 0 ? '1' : '0.25';
      }});
    }}
    function clearChatConfirm(){{
      if(!confirm('🧹 حذف كل المحادثة؟\\nلا يمكن التراجع!')) return;
      fetch('/chat/{peer.username}/clear', {{method:'POST', credentials:'same-origin'}})
        .then(function(r){{return r.json()}}).then(function(d){{
          if(d.ok){{ showToast('تم حذف المحادثة','success'); location.reload(); }}
          else showToast('تعذّر','error');
        }}).catch(function(){{showToast('خطأ','error');}});
    }}
    function muteChat(){{
      fetch('/chat/{peer.username}/mute', {{method:'POST', credentials:'same-origin'}})
        .then(function(r){{return r.json()}}).then(function(d){{
          if(d.ok) showToast(d.muted ? '🔕 تم الكتم' : '🔔 تم التفعيل','success');
        }}).catch(function(){{}});
    }}
    function doubleTap(mid){{ quickReact(mid, '❤️'); }}
    function toggleStar(mid){{
      fetch('/chat/{peer.username}/star/' + mid, {{method:'POST', credentials:'same-origin'}})
        .then(function(r){{return r.json()}}).then(function(d){{if(d.ok) location.reload();}}).catch(function(){{}});
    }}
    function toggleMsgBar(mid){{
      var bar=document.getElementById('bar-'+mid);
      if(!bar)return;
      var isOpen=bar.classList.contains('show');
      document.querySelectorAll('.msg-action-bar.show').forEach(function(b){{b.classList.remove('show');}});
      if(!isOpen)bar.classList.add('show');
    }}
    function quickReact(mid,emoji){{
      fetch('{url_for("chat_react", username=peer.username)}', {{
        method:'POST', headers:{{'Content-Type':'application/json'}}, credentials:'same-origin',
        body: JSON.stringify({{message_id: parseInt(mid), reaction: emoji}})
      }}).then(function(r){{return r.json()}}).then(function(d){{if(d.ok) location.reload();}}).catch(function(){{}});
    }}
    function clearReact(mid){{
      if(!confirm('إزالة التفاعل؟')) return;
      fetch('/chat/{peer.username}/clear-reaction/' + mid, {{method:'POST', credentials:'same-origin'}})
        .then(function(r){{return r.json()}}).then(function(d){{if(d.ok) location.reload();}}).catch(function(){{}});
    }}
    function deleteMsg(mid){{
      if(!confirm('🗑 حذف الرسالة؟')) return;
      fetch('/chat/{peer.username}/delete/' + mid, {{method:'POST', credentials:'same-origin'}})
        .then(function(r){{return r.json()}}).then(function(d){{
          if(d.ok){{ showToast('تم الحذف','success'); location.reload(); }}
          else showToast('تعذّر','error');
        }}).catch(function(){{}});
    }}
    function reportChat(){{
      if(!confirm('🚨 إبلاغ؟')) return;
      var reason=prompt('السبب:','');
      if(reason===null) return;
      fetch('{url_for("chat_report", username=peer.username)}', {{
        method:'POST', headers:{{'Content-Type':'application/json'}}, credentials:'same-origin',
        body: JSON.stringify({{reason: reason||'بدون سبب'}})
      }}).then(function(r){{return r.json()}}).then(function(d){{
        if(d.ok) showToast('✅ تم الإرسال','success');
        else showToast('⚠️ '+(d.error||'خطأ'),'error');
      }}).catch(function(){{}});
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
    </script>
    """, title=f"@{peer.username}")


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
    if not mid: return jsonify({"ok": False}), 400
    m = ChatMessage.query.filter(ChatMessage.id == int(mid),
        or_(and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == peer.id),
            and_(ChatMessage.sender_id == peer.id, ChatMessage.receiver_id == current_user.id))).first()
    if not m: return jsonify({"ok": False}), 404
    m.reaction = "" if m.reaction == emoji else emoji
    db.session.commit()
    return jsonify({"ok": True, "reaction": m.reaction})


@app.route("/chat/<username>/clear-reaction/<int:mid>", methods=["POST"])
@login_required
def chat_clear_reaction(username, mid):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    m = ChatMessage.query.filter(ChatMessage.id == mid,
        or_(and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == peer.id),
            and_(ChatMessage.sender_id == peer.id, ChatMessage.receiver_id == current_user.id))).first()
    if not m: return jsonify({"ok": False}), 404
    m.reaction = ""
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/chat/<username>/delete/<int:mid>", methods=["POST"])
@login_required
def chat_delete_message(username, mid):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    m = db.session.get(ChatMessage, mid)
    if not m: return jsonify({"ok": False}), 404
    if not ((m.sender_id == current_user.id and m.receiver_id == peer.id) or
            (m.sender_id == peer.id and m.receiver_id == current_user.id)):
        return jsonify({"ok": False}), 403
    if m.media:
        try: os.remove(os.path.join(app.config["CHAT_FOLDER"], m.media))
        except OSError: pass
    ChatMessage.query.filter_by(reply_to_id=mid).update({"reply_to_id": None}, synchronize_session=False)
    db.session.delete(m); db.session.commit()
    return jsonify({"ok": True})


@app.route("/chat/<username>/star/<int:mid>", methods=["POST"])
@login_required
def chat_star_message(username, mid):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    m = ChatMessage.query.filter(ChatMessage.id == mid,
        or_(and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == peer.id),
            and_(ChatMessage.sender_id == peer.id, ChatMessage.receiver_id == current_user.id))).first()
    if not m: return jsonify({"ok": False}), 404
    m.is_starred = not bool(m.is_starred)
    db.session.commit()
    return jsonify({"ok": True, "starred": m.is_starred})


@app.route("/chat/<username>/mute", methods=["POST"])
@login_required
def chat_mute(username):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    saved = SavedChat.query.filter_by(user_id=current_user.id, peer_id=peer.id).first()
    if not saved:
        saved = SavedChat(user_id=current_user.id, peer_id=peer.id, muted=True)
        db.session.add(saved)
    else:
        saved.muted = not bool(saved.muted)
    db.session.commit()
    return jsonify({"ok": True, "muted": saved.muted})


@app.route("/chat/<username>/clear", methods=["POST"])
@login_required
def chat_clear(username):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    msgs = ChatMessage.query.filter(or_(
        and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == peer.id),
        and_(ChatMessage.sender_id == peer.id, ChatMessage.receiver_id == current_user.id))).all()
    for m in msgs:
        if m.media:
            try: os.remove(os.path.join(app.config["CHAT_FOLDER"], m.media))
            except OSError: pass
        db.session.delete(m)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/chat/<username>/report", methods=["POST"])
@login_required
def chat_report(username):
    peer = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    if peer.id == current_user.id: return jsonify({"ok": False, "error": "لا يمكنك إبلاغ نفسك"}), 400
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip()[:500]
    existing = ChatReport.query.filter_by(reporter_id=current_user.id, target_id=peer.id).first()
    if existing and existing.status == "pending":
        return jsonify({"ok": False, "error": "لديك بلاغ قيد المراجعة"}), 400
    if existing:
        existing.reason = reason; existing.status = "pending"; existing.created_at = now_utc_naive()
    else:
        db.session.add(ChatReport(reporter_id=current_user.id, target_id=peer.id, reason=reason or "بدون سبب", status="pending"))
    peer.reports_count = (peer.reports_count or 0) + 1
    peer.under_review = True
    peer.review_reason = f"بلاغ من @{current_user.username}: {reason[:200] or 'بدون سبب'}"
    peer.review_started_at = now_utc_naive()
    db.session.commit()
    return jsonify({"ok": True, "message": "تم الإرسال"})


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
        my_html += f"""<div class="group-card">
          <img class="g-avatar" src="{group_avatar_url(g)}">
          <a href="{url_for('group_chat', gid=g.id)}" style="flex:1;text-decoration:none;color:inherit;min-width:0">
            <div class="g-name"><span class="role-badge {role}">{role_label}</span>{g.name}</div>
            <div class="g-sub">ID: {g.public_id} · {GroupMember.query.filter_by(group_id=g.id).count()} عضو</div>
          </a>
          <div style="display:flex;flex-direction:column;gap:4px">
            {copy_btn_html(g.public_id, "ID", small=True)}
            <a class="btn btn-sm" href="{url_for('group_view', gid=g.id)}">عرض</a>
          </div></div>"""
    if not my_html: my_html = '<p class="empty">لا مجموعات.</p>'
    all_html = ""
    my_ids = {m.id for m in my_groups}
    for g in all_groups:
        if g.id in my_ids: continue
        all_html += f"""<div class="group-card">
          <img class="g-avatar" src="{group_avatar_url(g)}">
          <a href="{url_for('group_view', gid=g.id)}" style="flex:1;text-decoration:none;color:inherit;min-width:0">
            <div class="g-name">{g.name}</div>
            <div class="g-sub">ID: {g.public_id}</div>
          </a>
          <div style="display:flex;flex-direction:column;gap:4px">
            {copy_btn_html(g.public_id, "ID", small=True)}
            <a class="btn btn-sm" href="{url_for('group_view', gid=g.id)}">عرض</a>
          </div></div>"""
    if not all_html: all_html = '<p class="empty">لا مجموعات أخرى.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>◉ مجموعاتي</h2>
    <a class="btn btn-sm btn-primary" href="{url_for('group_create')}" style="margin-bottom:12px">➕ إنشاء</a>
    {my_html}</div>
    <div class="card"><h2>🔍 بحث</h2>
    <form method="GET" style="display:flex;gap:8px;margin-bottom:12px">
      <input name="q" value="{q}" placeholder="اسم أو ID" style="flex:1;margin:0">
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
            flash("2-64 حرف.", "error"); return redirect(url_for("group_create"))
        pid = gen_public_id()
        while Group.query.filter_by(public_id=pid).first(): pid = gen_public_id()
        g = Group(name=name, description=description[:300], public_id=pid, owner_id=current_user.id, is_public=is_public)
        db.session.add(g); db.session.flush()
        file = request.files.get("avatar")
        if file and file.filename:
            if allowed_image(file.filename) and check_image_magic(file):
                ext = file.filename.rsplit(".", 1)[1].lower()
                avatar_fn = f"g_{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(app.config["GROUP_FOLDER"], avatar_fn))
                g.avatar = avatar_fn
        db.session.add(GroupMember(group_id=g.id, user_id=current_user.id, role="owner"))
        db.session.commit()
        flash(f"تم الإنشاء. ID: {g.public_id}", "success")
        return redirect(url_for("group_chat", gid=g.id))
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>➕ إنشاء مجموعة</h2>
    <form method="POST" enctype="multipart/form-data">
      <label>الاسم (2-64)</label>
      <input name="name" maxlength="64" required>
      <label>الوصف</label>
      <textarea name="description" maxlength="300"></textarea>
      <label>صورة</label>
      <input type="file" name="avatar" accept="image/*">
      <label class="switch-row" style="margin-top:14px">
        <span>🌍 مجموعة عامة</span>
        <input type="checkbox" name="is_public" value="1"><span class="switch"></span></label>
      <button type="submit">إنشاء</button></form>
    <a class="link-center" href="{url_for('groups_list')}">رجوع</a></div>""", title="إنشاء")


@app.route("/group/<int:gid>/avatar")
def group_avatar_full(gid):
    g = db.session.get(Group, gid)
    if not g: abort(404)
    if not g.avatar:
        flash("لا صورة.", "error")
        if current_user.is_authenticated: return redirect(url_for("group_view", gid=gid))
        return redirect(url_for("login"))
    img_url = url_for("serve_upload", subpath=f"groups/{g.avatar}")
    is_admin = current_user.is_authenticated and is_group_admin_or_owner(gid, current_user.id)
    edit_btn = f'<a class="btn btn-primary" href="{url_for("group_edit", gid=gid)}">✏️ تعديل</a>' if is_admin else ''
    back_link = url_for("group_view", gid=gid) if current_user.is_authenticated else url_for("login")
    return render_page(f"""
    <div class="card center">
      <img src="{img_url}" style="max-width:100%;border-radius:14px;max-height:80vh">
      <div class="name" style="margin-top:14px">{g.name}</div>
      <div class="uid">ID: {g.public_id} {copy_btn_html(g.public_id, "نسخ", small=True)}</div>
      <div class="actions" style="margin-top:14px">{edit_btn}<a class="btn" href="{back_link}">← رجوع</a></div>
    </div>""", title=f"{g.name}")


@app.route("/group/<int:gid>")
@login_required
def group_view(gid):
    g = db.session.get(Group, gid)
    if not g: abort(404)
    if g.is_banned:
        flash("محظورة.", "error"); return redirect(url_for("groups_list"))
    member = get_group_member(gid, current_user.id)
    members = GroupMember.query.filter_by(group_id=gid).all()
    is_member = member is not None
    is_admin = member and member.role in ("owner", "admin")
    is_owner = member and member.role == "owner"
    members_html = ""
    for m in members:
        u = m.user
        role_label = {"owner": "مالك", "admin": "مشرف", "member": "عضو"}.get(m.role, "عضو")
        actions = ""
        if is_owner and m.user_id != current_user.id:
            if m.role == "member": actions += f'<a class="btn btn-sm btn-primary" href="{url_for("group_promote", gid=gid, uid=u.id)}">⬆</a> '
            elif m.role == "admin": actions += f'<a class="btn btn-sm" href="{url_for("group_demote", gid=gid, uid=u.id)}">⬇</a> '
            actions += f'<a class="btn btn-sm btn-danger" href="{url_for("group_kick", gid=gid, uid=u.id)}" onclick="return confirm(\'طرد؟\')">🚫</a>'
        elif is_admin and not is_owner and m.role == "member":
            actions += f'<a class="btn btn-sm btn-danger" href="{url_for("group_kick", gid=gid, uid=u.id)}" onclick="return confirm(\'طرد؟\')">🚫</a>'
        dot, _ = online_status_html(u, show_text=False)
        members_html += f"""<div class="list-item" style="cursor:default">
          <div class="avatar-wrap" style="margin-bottom:0">
            <img class="avatar-sm" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">{dot}
          </div>
          <a href="{url_for('view_profile', username=u.username)}" style="flex:1;text-decoration:none;color:inherit;min-width:0">
            <div class="li-name"><span class="role-badge {m.role}">{role_label}</span>{verified_html(u)}{u.short_name}</div>
            <div class="li-sub">ID: {u.public_id}</div></a>
          <div class="li-actions">
            {copy_btn_html(u.username, "يوزر", small=True)}
            {copy_btn_html(u.public_id, "ID", small=True)}
            {actions}</div></div>"""
    admin_controls = ""
    if is_admin:
        pending_count = GroupJoinRequest.query.filter_by(group_id=gid).count()
        admin_controls = f"""<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;justify-content:center">
          <a class="btn btn-sm btn-primary" href="{url_for('group_edit', gid=gid)}">✏️ تعديل</a>
          <a class="btn btn-sm" href="{url_for('group_chat', gid=gid)}">💬 فتح</a>
          <a class="btn btn-sm" href="{url_for('group_requests', gid=gid)}" style="background:#f59e0b;color:#fff;border-color:#f59e0b">
            📥 طلبات ({pending_count})</a>
        </div>"""
    if is_owner:
        admin_controls += f"""<div style="margin-top:10px">
          <a class="btn btn-sm btn-danger" href="{url_for('group_delete', gid=gid)}" onclick="return confirm('⚠️ حذف نهائي؟')" style="width:100%">🗑 حذف</a></div>"""
    if not is_member:
        existing_req = GroupJoinRequest.query.filter_by(group_id=gid, user_id=current_user.id).first()
        if existing_req:
            join_btn = '<div class="btn btn-disabled">⏳ قيد المراجعة</div>'
        elif g.is_public:
            join_btn = f'<a class="btn btn-primary" href="{url_for("group_join", gid=gid)}">➕ انضم</a>'
        else:
            join_btn = f'<a class="btn btn-primary" href="{url_for("group_join", gid=gid)}">📥 طلب انضمام</a>'
    else:
        join_btn = f'<a class="btn btn-primary" href="{url_for("group_chat", gid=gid)}">💬 فتح المحادثة</a>'
        if not is_owner:
            join_btn += f'<a class="btn btn-danger" href="{url_for("group_leave", gid=gid)}" onclick="return confirm(\'مغادرة؟\')">🚪 مغادرة</a>'
    if g.avatar:
        avatar_html = f'<img class="avatar group-avatar-clickable" src="{group_avatar_url(g)}" style="border-radius:20px;width:100px;height:100px" onclick="window.location.href=\'{url_for("group_avatar_full", gid=gid)}\'">'
    else:
        avatar_html = f'<img class="avatar" src="{group_avatar_url(g)}" style="border-radius:20px;width:100px;height:100px;cursor:default">'
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
        {len(members)} عضو · {'🌍 عامة' if g.is_public else '🔒 خاصة'}
      </div>
      <div class="actions">{join_btn}</div>
      {admin_controls}
    </div>
    <div class="card"><h2>الأعضاء ({len(members)})</h2>{members_html}</div>""", title=g.name)


@app.route("/group/<int:gid>/edit", methods=["GET", "POST"])
@login_required
def group_edit(gid):
    g = db.session.get(Group, gid)
    if not g: abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role not in ("owner", "admin"):
        flash("ليس لديك صلاحية.", "error"); return redirect(url_for("group_view", gid=gid))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        is_public = request.form.get("is_public") == "1"
        if len(name) < 2 or len(name) > 64:
            flash("2-64 حرف.", "error"); return redirect(url_for("group_edit", gid=gid))
        g.name = name; g.description = description[:300]; g.is_public = is_public
        file = request.files.get("avatar")
        if file and file.filename:
            if allowed_image(file.filename) and check_image_magic(file):
                if g.avatar:
                    try: os.remove(os.path.join(app.config["GROUP_FOLDER"], g.avatar))
                    except OSError: pass
                ext = file.filename.rsplit(".", 1)[1].lower()
                fn = f"g_{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(app.config["GROUP_FOLDER"], fn))
                g.avatar = fn
        if request.form.get("remove_avatar") == "1" and g.avatar:
            try: os.remove(os.path.join(app.config["GROUP_FOLDER"], g.avatar))
            except OSError: pass
            g.avatar = ""
        db.session.commit()
        flash("تم التحديث.", "success")
        return redirect(url_for("group_view", gid=gid))
    is_public_checked = "checked" if g.is_public else ""
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>✏️ تعديل</h2>
    <div style="text-align:center;margin-bottom:14px">
      <img src="{group_avatar_url(g)}" class="avatar" style="border-radius:20px;width:100px;height:100px;cursor:default">
    </div>
    <form method="POST" enctype="multipart/form-data">
      <label>الاسم</label>
      <input name="name" value="{g.name}" maxlength="64" required>
      <label>الوصف</label>
      <textarea name="description" maxlength="300">{g.description}</textarea>
      <label>تغيير الصورة</label>
      <input type="file" name="avatar" accept="image/*">
      <label class="switch-row" style="margin-top:12px">
        <span>🗑 حذف الصورة الحالية</span>
        <input type="checkbox" name="remove_avatar" value="1"><span class="switch"></span></label>
      <label class="switch-row" style="margin-top:8px">
        <span>🌍 مجموعة عامة</span>
        <input type="checkbox" name="is_public" value="1" {is_public_checked}><span class="switch"></span></label>
      <button type="submit">حفظ</button></form>
    <a class="link-center" href="{url_for('group_view', gid=gid)}">رجوع</a></div>""", title="تعديل")


@app.route("/group/<int:gid>/join")
@login_required
def group_join(gid):
    g = db.session.get(Group, gid)
    if not g: abort(404)
    if g.is_banned:
        flash("محظورة.", "error"); return redirect(url_for("groups_list"))
    if get_group_member(gid, current_user.id):
        flash("عضو بالفعل.", "error"); return redirect(url_for("group_view", gid=gid))
    existing = GroupJoinRequest.query.filter_by(group_id=gid, user_id=current_user.id).first()
    if existing:
        flash("قيد المراجعة.", "info"); return redirect(url_for("group_view", gid=gid))
    if g.is_public:
        db.session.add(GroupMember(group_id=gid, user_id=current_user.id, role="member"))
        db.session.commit()
        flash(f"انضممت إلى {g.name}.", "success")
        return redirect(url_for("group_chat", gid=gid))
    db.session.add(GroupJoinRequest(group_id=gid, user_id=current_user.id))
    db.session.commit()
    flash(f"تم إرسال طلب.", "success")
    return redirect(url_for("group_view", gid=gid))


@app.route("/group/<int:gid>/requests")
@login_required
def group_requests(gid):
    g = db.session.get(Group, gid)
    if not g: abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role not in ("owner", "admin"):
        flash("ليس لديك صلاحية.", "error"); return redirect(url_for("group_view", gid=gid))
    reqs = GroupJoinRequest.query.filter_by(group_id=gid).order_by(GroupJoinRequest.created_at.desc()).all()
    rows = ""
    for r in reqs:
        u = r.user
        rows += f"""<div class="list-item" style="cursor:default">
          <img class="avatar-sm" src="{avatar_url(u)}">
          <a href="{url_for('view_profile', username=u.username)}" style="flex:1;text-decoration:none;color:inherit">
            <div class="li-name">{verified_html(u)}{u.short_name}</div>
            <div class="li-sub">ID: {u.public_id}</div></a>
          <div class="li-actions">
            {copy_btn_html(u.username, "يوزر", small=True)}
            {copy_btn_html(u.public_id, "ID", small=True)}
            <a class="btn btn-sm btn-primary" href="{url_for('group_accept_request', gid=gid, rid=r.id)}">✅</a>
            <a class="btn btn-sm btn-danger" href="{url_for('group_reject_request', gid=gid, rid=r.id)}">✖</a>
          </div></div>"""
    if not rows: rows = '<p class="empty">لا طلبات.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>📥 طلبات ({len(reqs)})</h2>{rows}
    <a class="link-center" href="{url_for('group_view', gid=gid)}">رجوع</a></div>""", title="طلبات")


@app.route("/group/<int:gid>/request/<int:rid>/accept")
@login_required
def group_accept_request(gid, rid):
    g = db.session.get(Group, gid)
    if not g: abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role not in ("owner", "admin"): abort(403)
    r = db.session.get(GroupJoinRequest, rid)
    if not r or r.group_id != gid: abort(404)
    if not get_group_member(gid, r.user_id):
        db.session.add(GroupMember(group_id=gid, user_id=r.user_id, role="member"))
    db.session.delete(r); db.session.commit()
    flash("تم القبول.", "success")
    return redirect(url_for("group_requests", gid=gid))


@app.route("/group/<int:gid>/request/<int:rid>/reject")
@login_required
def group_reject_request(gid, rid):
    g = db.session.get(Group, gid)
    if not g: abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role not in ("owner", "admin"): abort(403)
    r = db.session.get(GroupJoinRequest, rid)
    if not r or r.group_id != gid: abort(404)
    db.session.delete(r); db.session.commit()
    flash("تم الرفض.", "success")
    return redirect(url_for("group_requests", gid=gid))


@app.route("/group/<int:gid>/leave")
@login_required
def group_leave(gid):
    g = db.session.get(Group, gid)
    if not g: abort(404)
    m = get_group_member(gid, current_user.id)
    if not m:
        flash("لست عضوًا.", "error"); return redirect(url_for("groups_list"))
    if m.role == "owner":
        new_owner = GroupMember.query.filter_by(group_id=gid, role="admin").order_by(GroupMember.joined_at.asc()).first()
        if not new_owner:
            new_owner = GroupMember.query.filter(GroupMember.group_id == gid, GroupMember.user_id != current_user.id).order_by(GroupMember.joined_at.asc()).first()
        if new_owner:
            new_owner.role = "owner"
            g.owner_id = new_owner.user_id
            db.session.delete(m); db.session.commit()
            flash("تم نقل الملكية.", "success")
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
            db.session.delete(g); db.session.commit()
            flash("تم حذف القروب.", "success")
            return redirect(url_for("groups_list"))
    db.session.delete(m); db.session.commit()
    flash("غادرت.", "success")
    return redirect(url_for("groups_list"))


@app.route("/group/<int:gid>/kick/<int:uid>")
@login_required
def group_kick(gid, uid):
    g = db.session.get(Group, gid)
    if not g: abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role not in ("owner", "admin"):
        flash("ليس لديك صلاحية.", "error"); return redirect(url_for("group_view", gid=gid))
    target = get_group_member(gid, uid)
    if not target:
        flash("غير موجود.", "error"); return redirect(url_for("group_view", gid=gid))
    if target.role == "owner":
        flash("لا يمكن طرد المالك.", "error"); return redirect(url_for("group_view", gid=gid))
    if me.role == "admin" and target.role == "admin":
        flash("لا يمكن طرد مشرف.", "error"); return redirect(url_for("group_view", gid=gid))
    db.session.delete(target); db.session.commit()
    flash("تم الطرد.", "success")
    return redirect(url_for("group_view", gid=gid))


@app.route("/group/<int:gid>/promote/<int:uid>")
@login_required
def group_promote(gid, uid):
    g = db.session.get(Group, gid)
    if not g: abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role != "owner":
        flash("فقط المالك.", "error"); return redirect(url_for("group_view", gid=gid))
    target = get_group_member(gid, uid)
    if not target:
        flash("غير موجود.", "error"); return redirect(url_for("group_view", gid=gid))
    target.role = "admin"; db.session.commit()
    flash("تم الترقية.", "success")
    return redirect(url_for("group_view", gid=gid))


@app.route("/group/<int:gid>/demote/<int:uid>")
@login_required
def group_demote(gid, uid):
    g = db.session.get(Group, gid)
    if not g: abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role != "owner":
        flash("فقط المالك.", "error"); return redirect(url_for("group_view", gid=gid))
    target = get_group_member(gid, uid)
    if not target or target.role != "admin":
        flash("ليس مشرفاً.", "error"); return redirect(url_for("group_view", gid=gid))
    target.role = "member"; db.session.commit()
    flash("تم التخفيض.", "success")
    return redirect(url_for("group_view", gid=gid))


@app.route("/group/<int:gid>/add", methods=["POST"])
@login_required
def group_add_member(gid):
    g = db.session.get(Group, gid)
    if not g: abort(404)
    me = get_group_member(gid, current_user.id)
    if not me or me.role not in ("owner", "admin"):
        flash("ليس لديك صلاحية.", "error"); return redirect(url_for("group_chat", gid=gid))
    username = request.form.get("username", "").strip().lower().lstrip("@")
    target = User.query.filter_by(username=username).first()
    if not target:
        flash("غير موجود.", "error"); return redirect(url_for("group_chat", gid=gid))
    if target.is_banned or target.under_review:
        flash("لا يمكن الإضافة.", "error"); return redirect(url_for("group_chat", gid=gid))
    if get_group_member(gid, target.id):
        flash("عضو بالفعل.", "error"); return redirect(url_for("group_chat", gid=gid))
    GroupJoinRequest.query.filter_by(group_id=gid, user_id=target.id).delete()
    db.session.add(GroupMember(group_id=gid, user_id=target.id, role="member"))
    db.session.commit()
    flash(f"تم إضافة @{target.username}.", "success")
    return redirect(url_for("group_chat", gid=gid))


@app.route("/group/<int:gid>/delete")
@login_required
def group_delete(gid):
    g = db.session.get(Group, gid)
    if not g: abort(404)
    if g.owner_id != current_user.id:
        flash("فقط المالك.", "error"); return redirect(url_for("group_view", gid=gid))
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
    db.session.delete(g); db.session.commit()
    flash("تم الحذف.", "success")
    return redirect(url_for("groups_list"))


def render_group_bubble(m, current_user):
    cls = "me" if m.sender_id == current_user.id else "them"
    is_mine = (m.sender_id == current_user.id)
    sender = m.sender
    media_html = ""
    if m.media:
        url = upload_url("groups", m.media)
        if m.media_type == "video":
            media_html = f'<video src="{url}" controls style="max-width:100%;border-radius:8px;margin-bottom:4px;max-height:320px"></video>'
        elif m.media_type == "audio":
            media_html = f'<div class="audio-bubble">{glow_icon("audio",24,"#25D366")}<audio src="{url}" controls></audio></div>'
        else:
            media_html = f'<img src="{url}" style="max-width:100%;border-radius:8px;margin-bottom:4px;max-height:320px;cursor:pointer" onclick="event.stopPropagation();openAvatar(\'{url}\')">'
    body_html = f'<div>{linkify_text(m.body)}</div>' if m.body else ""
    header_html = ""
    if is_mine:
        header_html = f"""<a class="sender-head" href="{url_for('profile_me')}" onclick="event.stopPropagation()">
           <img src="{avatar_url(current_user)}" class="sender-avatar">
           <span class="sender-name">{verified_html(current_user)}{html_escape_text(current_user.short_name)}</span></a>"""
    elif sender:
        header_html = f"""<a class="sender-head" href="{url_for('view_profile', username=sender.username)}" onclick="event.stopPropagation()">
           <img src="{avatar_url(sender)}" class="sender-avatar">
           <span class="sender-name">{verified_html(sender)}{html_escape_text(sender.short_name)}</span></a>"""
    reply_html = ""
    if m.reply_to_id:
        orig = db.session.get(GroupMessage, m.reply_to_id)
        if orig:
            orig_text = orig.body or ("📷" if orig.media_type == "image" else "🎥" if orig.media_type == "video" else "🎵" if orig.media_type == "audio" else "مرفق")
            orig_name = "أنت" if orig.sender_id == current_user.id else (orig.sender.short_name if orig.sender else "?")
            reply_html = f'<div class="reply-quote"><div class="rq-name">{html_escape_text(orig_name)}</div><div class="rq-body">{html_escape_text(orig_text[:120])}</div></div>'
    reaction_html = ""
    if m.reaction:
        icon_map = {"❤️": "heart", "👍": "thumb", "😂": "laugh", "😮": "wow", "😢": "sad", "🙏": "pray"}
        icon_name = icon_map.get(m.reaction)
        if icon_name:
            reaction_html = f'<span class="reaction-badge">{glow_reaction_icon(icon_name)}</span>'
        else:
            reaction_html = f'<span class="reaction-badge">{html_escape_text(m.reaction)}</span>'
    body_esc_js = (m.body or "").replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")[:60]
    sender_name_js = ("أنت" if is_mine else (sender.short_name if sender else "?")).replace("'", "\\'")
    delete_btn = f'<button type="button" class="act-btn delete" onclick="event.stopPropagation();deleteMsgG({m.id})">{glow_icon("trash",14,"#991b1b")} حذف</button>' if is_mine else ""
    clear_react_btn = f'<button type="button" class="act-btn clear-react" onclick="event.stopPropagation();clearReactG({m.id})">{glow_icon("close",14,"#92400e")}</button>' if m.reaction else ""
    return f"""<div class="bubble-wrap">
      <div class="bubble {cls} clickable" id="gmsg-{m.id}" onclick="toggleMsgBarG({m.id})" ondblclick="event.stopPropagation();doubleTapG({m.id})">
        {header_html}{reply_html}{media_html}{body_html}
        <span class="t">{fmt_sd(m.created_at, "%H:%M")}</span>
        {reaction_html}
      </div>
      <div class="msg-action-bar" id="gbar-{m.id}" onclick="event.stopPropagation()">
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReactG({m.id},'❤️')">{glow_reaction_icon("heart")}</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReactG({m.id},'👍')">{glow_reaction_icon("thumb")}</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReactG({m.id},'😂')">{glow_reaction_icon("laugh")}</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReactG({m.id},'😮')">{glow_reaction_icon("wow")}</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReactG({m.id},'😢')">{glow_reaction_icon("sad")}</button>
        <button type="button" class="emoji-quick" onclick="event.stopPropagation();quickReactG({m.id},'🙏')">{glow_reaction_icon("pray")}</button>
        <span class="act-divider"></span>
        <button type="button" class="act-btn" onclick="event.stopPropagation();setReplyG({m.id}, '{body_esc_js}', '{sender_name_js}')">{glow_icon("reply",14)} رد</button>
        {clear_react_btn}{delete_btn}
      </div>
    </div>"""


@app.route("/group/<int:gid>/typing", methods=["POST"])
@login_required
def group_typing(gid):
    g = db.session.get(Group, gid)
    if not g: return jsonify({"ok": False}), 404
    me = get_group_member(gid, current_user.id)
    if not me: return jsonify({"ok": False}), 403
    set_typing(current_user.id, peer_id=None, group_id=gid)
    return jsonify({"ok": True})


@app.route("/group/<int:gid>/chat", methods=["GET", "POST"])
@login_required
def group_chat(gid):
    g = db.session.get(Group, gid)
    if not g: abort(404)
    if g.is_banned:
        flash("محظورة.", "error"); return redirect(url_for("groups_list"))
    me = get_group_member(gid, current_user.id)
    if not me:
        flash("يجب أن تكون عضواً.", "error"); return redirect(url_for("group_view", gid=gid))
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
            if not reply_obj: reply_to_id = None
        if body or media_fn:
            db.session.add(GroupMessage(group_id=gid, sender_id=current_user.id, body=body[:2000],
                                         media=media_fn, media_type=media_type,
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
            if len(typing_users) == 1: typing_text = f'<span class="typing-name">{names[0]}</span> يكتب'
            elif len(typing_users) == 2: typing_text = f'<span class="typing-name">{names[0]}</span> و <span class="typing-name">{names[1]}</span> يكتبان'
            else: typing_text = f'<span class="typing-name">{names[0]}</span> و{len(typing_users)-1} آخرين'
        return jsonify({"html": build_group_bubbles(), "unread": 0, "typing": typing_text})
    bubbles = build_group_bubbles()
    member_count = GroupMember.query.filter_by(group_id=gid).count()
    is_admin = me.role in ("owner", "admin")
    is_owner = me.role == "owner"
    pending_count = GroupJoinRequest.query.filter_by(group_id=gid).count()
    header_links = f'<a class="btn btn-sm" href="{url_for("group_view", gid=gid)}">👥 ({member_count})</a>'
    if is_admin:
        header_links += f'<a class="btn btn-sm" href="{url_for("group_requests", gid=gid)}" style="background:#f59e0b;color:#fff;border-color:#f59e0b">📥 ({pending_count})</a>'
    if not is_owner:
        header_links += f'<a class="btn btn-sm btn-danger" href="{url_for("group_leave", gid=gid)}" onclick="return confirm(\'مغادرة؟\')">🚪</a>'
    add_form = ""
    if is_admin:
        add_form = f"""<form method="POST" action="{url_for('group_add_member', gid=gid)}" style="display:flex;gap:6px;margin-top:8px">
          <input name="username" placeholder="أضف باليوزر" style="flex:1;margin:0">
          <button type="submit" class="btn btn-sm btn-primary" style="margin:0">➕</button></form>"""
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card">
      <div class="chat-header">
        <a href="{url_for('groups_list')}" class="btn btn-sm">{glow_icon("back",14)}</a>
        <img class="avatar-sm" src="{group_avatar_url(g)}" style="border-radius:12px">
        <div><div class="pn">{g.name}</div>
          <div class="pu">ID: {g.public_id} {copy_btn_html(g.public_id, "ID", small=True)}</div></div>
        <div style="margin-right:auto;display:flex;gap:6px;flex-wrap:wrap">{header_links}</div>
      </div>
      {add_form}
      <div class="chat-search-bar" id="search-bar" style="display:none;margin-top:8px">
        <input type="text" id="search-input" placeholder="ابحث..." oninput="filterMessages()">
        <button type="button" class="btn btn-sm" onclick="toggleSearch()">✕</button>
      </div>
      <div class="chat-box" id="chatbox" style="margin-top:10px">{bubbles}</div>
      <button type="button" class="scroll-bottom-btn" id="scroll-bottom-btn" onclick="scrollToBottom()">{glow_icon("arrow_down",20,"#fff")}</button>
      <div id="reply-preview" class="reply-preview" style="display:none">
        <div class="rp-info"><div class="rp-name" id="rp-name"></div><div class="rp-body" id="rp-body"></div></div>
        <button type="button" class="rp-close" onclick="cancelReply()">✕</button>
      </div>
      <div class="typing-indicator" id="typing-indicator">
        <span class="typing-dots"><span></span><span></span><span></span></span>
        <span id="typing-text"></span>
      </div>
      <form class="chat-input" method="POST" enctype="multipart/form-data">
        <input type="hidden" name="reply_to_id" id="reply_to_id" value="">
        <input type="file" name="media" id="chat-media-input" accept="image/*,video/*,audio/*" style="display:none" onchange="previewChatMedia(this)">
        <button type="button" class="icon-btn" onclick="document.getElementById('chat-media-input').click()">{glow_icon("attach",22,"#fff")}</button>
        <input name="body" id="group-body-input" placeholder="اكتب رسالة..." autocomplete="off">
        <button type="submit">{glow_icon("send",20,"#fff")}</button>
      </form>
      <div id="chat-media-preview" style="margin-top:8px"></div>
      <div class="chat-options">
        <button type="button" onclick="toggleSearch()">{glow_icon("search",14)} بحث</button>
      </div>
    </div>
    <script>
    startChatAutoRefresh('{url_for("group_chat", gid=gid)}', 1500);
    (function(){{
      var inp = document.getElementById('group-body-input');
      var lastSent = 0;
      if(inp){{
        inp.addEventListener('input', function(){{
          var now = Date.now();
          if(now - lastSent > 2000){{
            lastSent = now;
            fetch('{url_for("group_typing", gid=gid)}', {{method:'POST', credentials:'same-origin', headers: {{'Content-Type':'application/json'}}}}).catch(function(){{}});
          }}
        }});
      }}
    }})();
    function toggleSearch(){{
      var b = document.getElementById('search-bar');
      b.style.display = b.style.display === 'none' ? 'flex' : 'none';
      if(b.style.display === 'flex') document.getElementById('search-input').focus();
      else {{ document.getElementById('search-input').value=''; filterMessages(); }}
    }}
    function filterMessages(){{
      var q = (document.getElementById('search-input').value || '').toLowerCase().trim();
      document.querySelectorAll('.bubble').forEach(function(b){{
        if(!q){{ b.style.opacity='1'; return; }}
        b.style.opacity = (b.textContent||'').toLowerCase().indexOf(q) >= 0 ? '1' : '0.25';
      }});
    }}
    function toggleMsgBarG(mid){{
      var bar=document.getElementById('gbar-'+mid);
      if(!bar)return;
      var isOpen=bar.classList.contains('show');
      document.querySelectorAll('.msg-action-bar.show').forEach(function(b){{b.classList.remove('show');}});
      if(!isOpen)bar.classList.add('show');
    }}
    function quickReactG(mid,emoji){{
      fetch('{url_for("group_react", gid=gid)}', {{
        method:'POST', headers:{{'Content-Type':'application/json'}}, credentials:'same-origin',
        body: JSON.stringify({{message_id: parseInt(mid), reaction: emoji}})
      }}).then(function(r){{return r.json()}}).then(function(d){{if(d.ok) location.reload();}}).catch(function(){{}});
    }}
    function clearReactG(mid){{
      if(!confirm('إزالة التفاعل؟')) return;
      fetch('/group/{gid}/clear-reaction/' + mid, {{method:'POST', credentials:'same-origin'}})
        .then(function(r){{return r.json()}}).then(function(d){{if(d.ok) location.reload();}}).catch(function(){{}});
    }}
    function deleteMsgG(mid){{
      if(!confirm('🗑 حذف؟')) return;
      fetch('/group/{gid}/delete-msg/' + mid, {{method:'POST', credentials:'same-origin'}})
        .then(function(r){{return r.json()}}).then(function(d){{
          if(d.ok){{ showToast('تم الحذف','success'); location.reload(); }}
          else showToast('تعذّر','error');
        }}).catch(function(){{}});
    }}
    function setReplyG(mid, body, name){{
      document.getElementById('reply_to_id').value=mid;
      document.getElementById('rp-name').textContent=name;
      document.getElementById('rp-body').textContent=body||'📎';
      document.getElementById('reply-preview').style.display='flex';
      var inp=document.getElementById('group-body-input');
      if(inp)inp.focus();
      document.querySelectorAll('.msg-action-bar.show').forEach(function(b){{b.classList.remove('show');}});
    }}
    function cancelReply(){{
      document.getElementById('reply_to_id').value='';
      document.getElementById('reply-preview').style.display='none';
    }}
    function doubleTapG(mid){{ quickReactG(mid, '❤️'); }}
    document.addEventListener('click',function(e){{
      if(!e.target.closest('.bubble') && !e.target.closest('.msg-action-bar')){{
        document.querySelectorAll('.msg-action-bar.show').forEach(function(b){{b.classList.remove('show');}});
      }}
    }});
    </script>""", title=g.name)


@app.route("/group/<int:gid>/react", methods=["POST"])
@login_required
def group_react(gid):
    g = db.session.get(Group, gid)
    if not g: return jsonify({"ok": False}), 404
    me = get_group_member(gid, current_user.id)
    if not me: return jsonify({"ok": False}), 403
    data = request.get_json(silent=True) or {}
    mid = data.get("message_id")
    emoji = (data.get("reaction") or "").strip()[:8]
    if not mid: return jsonify({"ok": False}), 400
    m = GroupMessage.query.filter_by(id=int(mid), group_id=gid).first()
    if not m: return jsonify({"ok": False}), 404
    m.reaction = "" if m.reaction == emoji else emoji
    db.session.commit()
    return jsonify({"ok": True, "reaction": m.reaction})


@app.route("/group/<int:gid>/clear-reaction/<int:mid>", methods=["POST"])
@login_required
def group_clear_reaction(gid, mid):
    me = get_group_member(gid, current_user.id)
    if not me: return jsonify({"ok": False}), 403
    m = GroupMessage.query.filter_by(id=mid, group_id=gid).first()
    if not m: return jsonify({"ok": False}), 404
    m.reaction = ""; db.session.commit()
    return jsonify({"ok": True})


@app.route("/group/<int:gid>/delete-msg/<int:mid>", methods=["POST"])
@login_required
def group_delete_message(gid, mid):
    me = get_group_member(gid, current_user.id)
    if not me: return jsonify({"ok": False}), 403
    m = GroupMessage.query.filter_by(id=mid, group_id=gid).first()
    if not m: return jsonify({"ok": False}), 404
    is_admin = me.role in ("owner", "admin")
    if m.sender_id != current_user.id and not is_admin:
        return jsonify({"ok": False}), 403
    if m.media:
        try: os.remove(os.path.join(app.config["GROUP_FOLDER"], m.media))
        except OSError: pass
    GroupMessage.query.filter_by(reply_to_id=mid).update({"reply_to_id": None}, synchronize_session=False)
    db.session.delete(m); db.session.commit()
    return jsonify({"ok": True})
    # ═══════════════════════════════════════════════════════════════
# ANONYMOUS + REPORTS
# ═══════════════════════════════════════════════════════════════
@app.route("/message/<username>", methods=["GET", "POST"])
@login_required
def send_message(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    if target.id == current_user.id:
        flash("لا يمكنك إرسال رسالة لنفسك.", "error"); return redirect(url_for("profile_me"))
    if is_blocked_between(current_user.id, target.id):
        flash("يوجد حظر.", "error"); return redirect(url_for("view_profile", username=target.username))
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        sender = request.form.get("sender_name", "").strip() or "مجهول"
        if not body:
            flash("فارغة.", "error"); return redirect(url_for("send_message", username=target.username))
        db.session.add(Message(receiver_id=target.id, body=body[:2000], sender_name=sender[:64]))
        db.session.commit()
        flash("تم الإرسال ✓", "success")
        return redirect(url_for("view_profile", username=target.username))
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>✉ رسالة لـ @{target.username}</h2>
    <div class="privacy-note">🔒 لن يعرف المرسل.</div>
    <form method="POST">
      <label>اسمك (اختياري)</label>
      <input name="sender_name" maxlength="64" placeholder="اتركه فارغًا">
      <label>الرسالة</label>
      <textarea name="body" maxlength="2000" required></textarea>
      <button type="submit">إرسال</button></form>
    <a class="link-center" href="{url_for('view_profile', username=target.username)}">رجوع</a></div>""", title="رسالة")


@app.route("/inbox")
@login_required
def inbox():
    messages = Message.query.filter_by(receiver_id=current_user.id).order_by(Message.created_at.desc()).all()
    rows = ""
    for m in messages:
        rows += f"""<div class="msg"><div class="meta">من: {html_escape_text(m.sender_name)} · {fmt_sd(m.created_at)}</div>
        <div class="body">{html_escape_text(m.body)}</div></div>"""
    if not rows: rows = '<p class="empty">لا رسائل.</p>'
    return render_page(FLASH_BLOCK + topbar_html(badge_html()) + f"""
    <div class="card"><h2>📩 المجهولة</h2>{rows}
    <a class="link-center" href="{url_for('profile_me')}">رجوع</a></div>""", title="المجهولة")


@app.route("/report/<username>", methods=["GET", "POST"])
@login_required
def report_user(username):
    target = User.query.filter_by(username=username.lower().lstrip("@")).first_or_404()
    if target.id == current_user.id:
        flash("لا يمكنك إبلاغ نفسك.", "error"); return redirect(url_for("profile_me"))
    if request.method == "POST":
        reason = request.form.get("reason", "").strip()
        if Report.query.filter_by(reporter_id=current_user.id, target_id=target.id).first():
            flash("أبلغت مسبقًا.", "error"); return redirect(url_for("view_profile", username=target.username))
        db.session.add(Report(reporter_id=current_user.id, target_id=target.id, reason=reason[:300]))
        target.reports_count = (target.reports_count or 0) + 1
        db.session.commit()
        flash("تم الإرسال.", "success")
        return redirect(url_for("view_profile", username=target.username))
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>🚨 إبلاغ عن @{target.username}</h2>
    <form method="POST"><label>السبب</label>
    <textarea name="reason" maxlength="300" required></textarea>
    <button type="submit">إرسال</button></form>
    <a class="link-center" href="{url_for('view_profile', username=target.username)}">رجوع</a></div>""", title="إبلاغ")


# ═══════════════════════════════════════════════════════════════
# SUPPORT PANEL
# ═══════════════════════════════════════════════════════════════
def support_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("support_authed"): return redirect(url_for("support_login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/support", methods=["GET", "POST"])
def support_login():
    if request.method == "POST":
        if request.form.get("password", "") == SUPPORT_PASSWORD:
            session["support_authed"] = True
            session.permanent = True
            flash("مرحبًا.", "success")
            return redirect(url_for("support_dashboard"))
        flash("كلمة السر خاطئة.", "error"); return redirect(url_for("support_login"))
    return render_page(FLASH_BLOCK + """
    <div class="card"><h2>🛡 لوحة الدعم</h2>
    <form method="POST"><label>كلمة سر الدعم</label>
    <div class="pw-wrap"><input name="password" id="supw" type="password" required autofocus>
    <button type="button" class="pw-toggle" onclick="togglePw('supw')">👁</button></div>
    <button type="submit">دخول</button></form>
    <a class="link-center" href="{{ url_for('login') }}">رجوع</a></div>""", title="الدعم")


@app.route("/support/logout")
def support_logout():
    session.pop("support_authed", None)
    flash("تم الخروج.", "success")
    return redirect(url_for("login"))


@app.route("/support/dashboard")
@support_required
def support_dashboard():
    users_count = User.query.count()
    banned_count = User.query.filter_by(is_banned=True).count()
    review_count = User.query.filter_by(under_review=True).count()
    verified_count = User.query.filter_by(is_verified=True).count()
    groups_count = Group.query.count()
    banned_groups = Group.query.filter_by(is_banned=True).count()
    reports_count = Report.query.count()
    group_reports = GroupReport.query.count()
    chat_reports_pending = ChatReport.query.filter_by(status="pending").count()
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>🛡 لوحة الدعم</h2>
    <div class="acct-box">
      <div class="acct-row"><span class="k">المستخدمون</span><span class="v">{users_count}</span></div>
      <div class="acct-row"><span class="k">الموثّقون</span><span class="v" style="color:#1d9bf0">{verified_count}</span></div>
      <div class="acct-row"><span class="k">المحظورون (دائم)</span><span class="v">{banned_count}</span></div>
      <div class="acct-row"><span class="k">تحت المراجعة</span><span class="v" style="color:#f59e0b">{review_count}</span></div>
      <div class="acct-row"><span class="k">المجموعات</span><span class="v">{groups_count}</span></div>
      <div class="acct-row"><span class="k">مجموعات محظورة</span><span class="v">{banned_groups}</span></div>
      <div class="acct-row"><span class="k">بلاغات مستخدمين</span><span class="v">{reports_count}</span></div>
      <div class="acct-row"><span class="k">بلاغات مجموعات</span><span class="v">{group_reports}</span></div>
      <div class="acct-row"><span class="k">بلاغات دردشة (معلّقة)</span><span class="v" style="color:#f59e0b">{chat_reports_pending}</span></div>
    </div>
    <div class="actions">
      <a class="btn btn-primary" href="{url_for('support_chat_reports')}">💬 بلاغات الدردشة ({chat_reports_pending})</a>
      <a class="btn btn-primary" href="{url_for('support_reports')}">📋 كل البلاغات</a>
      <a class="btn" href="{url_for('support_bulk_ban')}">🚫 حظر جماعي</a>
      <a class="btn" href="{url_for('support_users')}">👥 المستخدمون</a>
      <a class="btn" href="{url_for('support_groups')}">◉ المجموعات</a>
      <a class="btn btn-danger" href="{url_for('support_logout')}">خروج</a>
    </div></div>""", title="لوحة الدعم")


@app.route("/support/bulk-ban", methods=["GET", "POST"])
@support_required
def support_bulk_ban():
    if request.method == "POST":
        ids_str = request.form.get("user_ids", "").strip()
        if not ids_str:
            flash("لم تحدد أي مستخدم.", "error"); return redirect(url_for("support_bulk_ban"))
        try: ids = [int(x) for x in re.split(r"[,\s]+", ids_str) if x.strip().isdigit()]
        except Exception:
            flash("قائمة غير صالحة.", "error"); return redirect(url_for("support_bulk_ban"))
        ids = list(set(ids))
        success, fail = 0, 0
        logs = []
        for uid in ids:
            u = db.session.get(User, uid)
            if not u:
                fail += 1; logs.append(f"❌ ID {uid}: غير موجود"); continue
            if u.is_banned:
                fail += 1; logs.append(f"⚠️ @{u.username}: محظور مسبقاً"); continue
            uname = u.username
            if process_auto_ban(u):
                success += 1; logs.append(f"🚫 @{uname} — تم الحظر الدائم + مسح البيانات")
            else:
                fail += 1; logs.append(f"❌ @{uname}")
        flash(f"تم: {success} نجح، {fail} فشل.", "success")
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
          <img class="avatar-sm" src="{avatar_url(u)}">
          <div style="flex:1;min-width:0">
            <div style="font-weight:700">{verified_html(u)}{u.short_name}</div>
            <div style="font-size:11px;color:#6b7280">ID: {u.public_id} · بلاغات: {u.reports_count or 0}</div>
          </div></label>"""
    if not rows: rows = '<p class="empty">لا نتائج.</p>'
    logs_html = ""
    logs = session.pop("bulk_ban_logs", None)
    if logs:
        logs_html = '<div class="privacy-note" style="background:#f0fdf4;border-color:#bbf7d0;color:#166534;direction:ltr;text-align:left">'
        for line in logs: logs_html += f'<div>{line}</div>'
        logs_html += '</div>'
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>🚫 حظر جماعي دائم</h2>
    <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:12px;margin-bottom:12px">
      <div style="font-size:13px;font-weight:700;color:#991b1b">
        ⚠️ الحظر الدائم يمسح كل بيانات المستخدم فوراً (رسائل، حالات، صور، أصدقاء، مجموعات)
      </div>
    </div>
    <form method="GET" style="display:flex;gap:8px;margin-bottom:12px">
      <input name="q" value="{q}" placeholder="بحث" style="flex:1;margin:0">
      <button type="submit" style="width:auto;padding:12px 20px;margin:0">بحث</button></form>
    <div style="max-height:50vh;overflow-y:auto;padding:4px;background:#f7f7f8;border-radius:10px;border:1px solid var(--border)">
      {rows}
    </div>
    <form method="POST" style="margin-top:16px" onsubmit="return confirmBulk()">
      <label>IDs المحددة</label>
      <textarea name="user_ids" id="user_ids" rows="3" style="direction:ltr;font-family:monospace"></textarea>
      <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:12px;margin-top:10px">
        <div style="font-size:13px;font-weight:700;color:#991b1b">
          ⚠️ سيتم حظر <span id="count-display">0</span> مستخدم بشكل دائم!
        </div>
      </div>
      <button type="submit" class="btn btn-danger" style="margin-top:14px;background:#dc2626;color:#fff">🚫 تنفيذ الحظر الدائم</button>
    </form>
    {logs_html}
    <a class="link-center" href="{url_for('support_dashboard')}">← رجوع</a>
    </div>
    <script>
    function toggleUser(uid, cb){{
      document.getElementById('row-'+uid).classList.toggle('selected', cb.checked);
      updateIds();
    }}
    function updateIds(){{
      var ids = [];
      document.querySelectorAll('.bulk-user-row input:checked').forEach(function(c){{ids.push(c.value);}});
      document.getElementById('user_ids').value = ids.join(', ');
      document.getElementById('count-display').textContent = ids.length;
    }}
    document.getElementById('user_ids').addEventListener('input', function(){{
      var cnt = (this.value.match(/\\d+/g) || []).length;
      document.getElementById('count-display').textContent = cnt;
    }});
    function confirmBulk(){{
      var cnt = (document.getElementById('user_ids').value.match(/\\d+/g) || []).length;
      if (cnt === 0) {{ showToast('لم تحدد أي مستخدم','error'); return false; }}
      return confirm('🚫 سيتم حظر ' + cnt + ' مستخدم بشكل دائم وحذف كل بياناتهم.\\nهل أنت متأكد؟');
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
        if not tgt: continue
        status_map = {"pending": '⏳ قيد المراجعة', "upheld": '🚫 مؤيَّد', "dismissed": '✅ مرفوض'}
        status_badge = status_map.get(r.status, r.status)
        target_state = ""
        if tgt.is_banned: target_state = '<span class="blocked-badge">محظور</span>'
        elif tgt.under_review: target_state = '<span class="blocked-badge" style="background:#fef3c7">⏳</span>'
        actions = ""
        if r.status == "pending":
            actions = f"""<a class="btn btn-sm btn-danger" href="{url_for('support_review_chat_report', rid=r.id, decision='upheld')}" onclick="return confirm('تأييد + حظر دائم؟ سيتم مسح كل بياناته.')">🚫 تأييد + حظر</a>
            <a class="btn btn-sm btn-primary" href="{url_for('support_review_chat_report', rid=r.id, decision='dismissed')}" onclick="return confirm('رفض + إرجاع؟')">✅ رفض</a>"""
        else:
            undo = 'dismissed' if r.status == 'upheld' else 'upheld'
            actions = f'<a class="btn btn-sm" href="{url_for("support_review_chat_report", rid=r.id, decision=undo)}">↩ إعادة</a>'
        reporter_html = f'@{rep.username}' if rep else 'مجهول'
        rows += f"""<div class="list-item" style="cursor:default;flex-wrap:wrap;border-right:4px solid #f59e0b">
          <img class="avatar-sm" src="{avatar_url(tgt)}">
          <div style="flex:1;min-width:240px">
            <div class="li-name">🎯 @{tgt.username} {target_state} {status_badge}</div>
            <div class="li-sub">ID: {tgt.public_id} · بلاغات: {tgt.reports_count or 0}</div>
            <div class="li-sub">🪪 المُبلِّغ: {reporter_html}</div>
            <div style="font-size:13px;margin-top:6px;color:#374151;background:#fef3c7;border-radius:6px;padding:6px 10px">
              💬 {html_escape_text(r.reason) or 'بدون سبب'}</div>
          </div>
          <div class="li-actions" style="flex-direction:column;gap:4px">
            <a class="btn btn-sm" href="{url_for('support_user_detail', uid=tgt.id)}">👁 فحص</a>
            {actions}
          </div></div>"""
    if not rows: rows = '<p class="empty">لا بلاغات. 🎉</p>'
    pending = ChatReport.query.filter_by(status="pending").count()
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>💬 بلاغات الدردشة ({len(reports)}) — معلّقة: {pending}</h2>
    {rows}
    <a class="link-center" href="{url_for('support_dashboard')}">← رجوع</a></div>""", title="بلاغات الدردشة")


@app.route("/support/chat-reports/<int:rid>/<decision>")
@support_required
def support_review_chat_report(rid, decision):
    r = db.session.get(ChatReport, rid)
    if not r:
        flash("غير موجود.", "error"); return redirect(url_for("support_chat_reports"))
    if decision not in ("upheld", "dismissed"):
        flash("قرار غير صالح.", "error"); return redirect(url_for("support_chat_reports"))
    tgt = db.session.get(User, r.target_id)
    if not tgt:
        flash("المستخدم غير موجود.", "error"); return redirect(url_for("support_chat_reports"))
    if decision == "upheld":
        r.status = "upheld"; r.resolved_at = now_utc_naive()
        db.session.commit()
        # ✅ حظر دائم فوري — يمسح كل شيء
        process_auto_ban(tgt)
        flash("🚫 تم الحظر الدائم + مسح كل البيانات.", "success")
    else:
        r.status = "dismissed"; r.resolved_at = now_utc_naive()
        tgt.under_review = False; tgt.review_reason = ""; tgt.review_started_at = None
        db.session.commit()
        flash(f"✅ تم الإرجاع.", "success")
    return redirect(url_for("support_chat_reports"))


@app.route("/support/user/<int:uid>")
@support_required
def support_user_detail(uid):
    u = db.session.get(User, uid)
    if not u:
        flash("غير موجود.", "error"); return redirect(url_for("support_users"))
    reports_against = Report.query.filter_by(target_id=uid).order_by(Report.created_at.desc()).all()
    chat_reports_against = ChatReport.query.filter_by(target_id=uid).order_by(ChatReport.created_at.desc()).all()
    statuses_count = Status.query.filter_by(user_id=uid).count()
    chat_sent = ChatMessage.query.filter_by(sender_id=uid).count()
    friends_count = Friendship.query.filter(Friendship.status == "accepted",
        or_(Friendship.requester_id == uid, Friendship.addressee_id == uid)).count()
    if u.is_banned: status_badge = '<span class="blocked-badge">🚫 محظور دائم</span>'
    elif u.under_review: status_badge = '<span class="blocked-badge" style="background:#fef3c7">⏳ مراجعة</span>'
    else: status_badge = '<span style="color:#16a34a;font-weight:700">✅ نشط</span>'
    if u.is_verified: status_badge += ' ' + verified_html(u, True)
    reports_html = ""
    for r in reports_against:
        rep = db.session.get(User, r.reporter_id) if r.reporter_id else None
        reporter_txt = f'@{rep.username}' if rep else 'مجهول'
        reports_html += f"""<div class="msg"><div class="meta">🪪 {reporter_txt} · {fmt_sd(r.created_at)}</div>
        <div class="body">💬 {html_escape_text(r.reason) or 'بدون سبب'}</div></div>"""
    if not reports_html: reports_html = '<p class="empty">لا بلاغات.</p>'
    chat_reports_html = ""
    for cr in chat_reports_against:
        rep = cr.reporter
        status_map = {"pending": '⏳', "upheld": '🚫', "dismissed": '✅'}
        sb = status_map.get(cr.status, '')
        chat_reports_html += f"""<div class="msg"><div class="meta">🪪 {('@'+rep.username) if rep else 'مجهول'} · {fmt_sd(cr.created_at)} {sb}</div>
        <div class="body">💬 {html_escape_text(cr.reason) or 'بدون سبب'}</div></div>"""
    if not chat_reports_html: chat_reports_html = '<p class="empty">لا بلاغات دردشة.</p>'
    verify_btn = (f'<a class="btn" href="{url_for("support_unverify_user", uid=u.id)}" onclick="return confirm(\'إلغاء؟\')">✖ إلغاء التوثيق</a>'
                  if u.is_verified else
                  f'<a class="btn btn-primary" href="{url_for("support_verify_user", uid=u.id)}">✓ توثيق</a>')
    release_btn = (f'<a class="btn btn-primary" href="{url_for("support_release_review", uid=u.id)}" onclick="return confirm(\'رفع؟\')">✅ رفع المراجعة</a>'
                   if u.under_review else '')
    ban_btn = (f'<a class="btn btn-primary" href="{url_for("support_unban_user", uid=u.id)}">✅ إلغاء حظر</a>'
               if u.is_banned else
               f'<a class="btn btn-danger" href="{url_for("support_ban_user", uid=u.id)}" onclick="return confirm(\'🚫 حظر دائم + مسح كل البيانات؟\')">🚫 حظر دائم</a>')
    return render_page(FLASH_BLOCK + f"""
    <div class="card center">
      <div class="avatar-wrap">
        <img class="avatar" src="{avatar_url(u)}" onclick="openAvatar('{avatar_url(u)}')">
        {online_status_html(u, show_text=False)[0]}
      </div>
      <div class="name">{verified_html(u, True)} {u.short_name}</div>
      <div style="margin-top:8px">{status_badge}</div>
      {f'<div class="privacy-note">⏳ {html_escape_text(u.review_reason)}</div>' if u.under_review else ''}
      <div class="acct-box" style="margin-top:12px">
        <div class="acct-row"><span class="k">USERNAME</span><span class="v">@{u.username} {copy_btn_html(u.username, "نسخ", small=True)}</span></div>
        <div class="acct-row"><span class="k">ID</span><span class="v">{u.public_id} {copy_btn_html(u.public_id, "نسخ", small=True)}</span></div>
        <div class="acct-row"><span class="k">JOINED</span><span class="v" style="font-family:inherit">{fmt_sd(u.created_at)}</span></div>
        <div class="acct-row"><span class="k">REPORTS</span><span class="v" style="color:#dc2626">{u.reports_count or 0}</span></div>
      </div>
      <div class="actions">
        <a class="btn" href="{url_for('view_profile', username=u.username)}">👤 بروفايل</a>
        {verify_btn}
        {release_btn}
        {ban_btn}
        <a class="btn" href="{url_for('support_users')}">← رجوع</a>
      </div>
    </div>
    <div class="card"><h2>📊 النشاط</h2>
    <div class="acct-box" style="direction:rtl;text-align:right">
      <div class="acct-row"><span class="k">الحالات</span><span class="v" style="font-family:inherit">{statuses_count}</span></div>
      <div class="acct-row"><span class="k">رسائل دردشة</span><span class="v" style="font-family:inherit">{chat_sent}</span></div>
      <div class="acct-row"><span class="k">الأصدقاء</span><span class="v" style="font-family:inherit">{friends_count}</span></div>
    </div></div>
    <div class="card"><h2>💬 بلاغات الدردشة ({len(chat_reports_against)})</h2>{chat_reports_html}</div>
    <div class="card"><h2>🚨 البلاغات ({len(reports_against)})</h2>{reports_html}</div>""", title=f"@{u.username}")


@app.route("/support/verify-user/<int:uid>", methods=["GET", "POST"])
@support_required
def support_verify_user(uid):
    u = db.session.get(User, uid)
    if not u:
        flash("غير موجود.", "error"); return redirect(url_for("support_users"))
    if request.method == "POST":
        action = request.form.get("action", "verify")
        if action == "unverify":
            u.is_verified = False; db.session.commit()
            flash(f"تم إلغاء توثيق @{u.username}.", "success")
            return redirect(url_for("support_user_detail", uid=uid))
        color = request.form.get("verified_color", "#1d9bf0").strip()
        icon = request.form.get("verified_icon", "✓").strip()[:4] or "✓"
        if not (color.startswith("#") or color.startswith("linear-gradient")):
            color = "#1d9bf0"
        u.is_verified = True
        u.verified_color = color[:200]
        u.verified_icon = icon
        db.session.commit()
        flash(f"✅ تم توثيق @{u.username}.", "success")
        return redirect(url_for("support_user_detail", uid=uid))
    current_color = u.verified_color or "#1d9bf0"
    current_icon = u.verified_icon or "✓"
    colors_html = ""
    for val, name in VERIFY_COLORS:
        selected = "selected" if val == current_color else ""
        colors_html += f"""
        <label class="color-opt {selected}" onclick="selectColor('{val}', this)">
          <span class="color-preview" style="background:{val}"></span>
          <span class="color-name">{name}</span>
        </label>"""
    icons_html = ""
    for ic in VERIFY_ICONS:
        sel = "selected" if ic == current_icon else ""
        icons_html += f'<button type="button" class="icon-opt {sel}" onclick="selectIcon(\'{ic}\', this)">{ic}</button>'
    verify_status = ""
    if u.is_verified:
        verify_status = f"""
        <div class="privacy-note" style="background:#dcfce7;border-color:#86efac;color:#166534">
          ✅ <b>موثّق حالياً</b> {verified_html(u, True)}
        </div>"""
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>✓ توثيق @{u.username}</h2>
    {verify_status}
    <div style="text-align:center;margin:14px 0">
      <img class="avatar" src="{avatar_url(u)}" style="cursor:default">
      <div class="name" style="justify-content:center">{u.short_name} <span id="live-preview" class="verified-badge verified-badge-lg" style="background:{current_color}"><span class="vb-icon">{current_icon}</span></span></div>
    </div>
    <form method="POST" id="verify-form">
      <input type="hidden" name="action" value="verify">
      <label>🎨 لون التوثيق</label>
      <div class="color-grid">{colors_html}</div>
      <input type="hidden" name="verified_color" id="verified_color" value="{current_color}">
      <label style="margin-top:16px">🎨 لون مخصص</label>
      <div style="display:flex;gap:8px">
        <input type="color" id="custom-color" value="{current_color if current_color.startswith('#') else '#1d9bf0'}"
               style="width:60px;height:44px;padding:2px;cursor:pointer" onchange="applyCustomColor(this.value)">
        <input type="text" id="custom-color-text" value="{current_color}" style="flex:1;direction:ltr"
               oninput="document.getElementById('verified_color').value=this.value;updatePreview(this.value)">
      </div>
      <label style="margin-top:16px">⭐ اختر الشكل</label>
      <div class="icon-grid">{icons_html}</div>
      <input type="hidden" name="verified_icon" id="verified_icon" value="{current_icon}">
      <button type="submit" style="margin-top:16px;background:#25D366">✓ توثيق</button>
    </form>
    {f'<form method="POST" style="margin-top:8px"><input type="hidden" name="action" value="unverify"><button type="submit" class="btn btn-danger" style="width:100%">✖ إلغاء</button></form>' if u.is_verified else ''}
    <a class="link-center" href="{url_for('support_user_detail', uid=uid)}">← رجوع</a>
    </div>
    <script>
    function selectColor(color, el){{
      document.querySelectorAll('.color-opt').forEach(function(c){{c.classList.remove('selected');}});
      el.classList.add('selected');
      document.getElementById('verified_color').value = color;
      document.getElementById('custom-color-text').value = color;
      updatePreview(color);
    }}
    function selectIcon(icon, el){{
      document.querySelectorAll('.icon-opt').forEach(function(c){{c.classList.remove('selected');}});
      el.classList.add('selected');
      document.getElementById('verified_icon').value = icon;
      document.getElementById('live-preview').innerHTML = '<span class="vb-icon">'+icon+'</span>';
    }}
    function applyCustomColor(color){{
      document.getElementById('verified_color').value = color;
      document.getElementById('custom-color-text').value = color;
      updatePreview(color);
    }}
    function updatePreview(color){{
      document.getElementById('live-preview').style.background = color;
    }}
    </script>""", title=f"توثيق @{u.username}")


@app.route("/support/unverify/<int:uid>")
@support_required
def support_unverify_user(uid):
    u = db.session.get(User, uid)
    if not u:
        flash("غير موجود.", "error"); return redirect(url_for("support_users"))
    u.is_verified = False; db.session.commit()
    flash(f"تم إلغاء توثيق @{u.username}.", "success")
    return redirect(request.referrer or url_for("support_users"))


@app.route("/support/release-review/<int:uid>")
@support_required
def support_release_review(uid):
    u = db.session.get(User, uid)
    if not u:
        flash("غير موجود.", "error"); return redirect(url_for("support_users"))
    u.under_review = False; u.review_reason = ""; u.review_started_at = None
    db.session.commit()
    flash(f"✅ تم الرفع.", "success")
    return redirect(request.referrer or url_for("support_users"))


@app.route("/support/reports")
@support_required
def support_reports():
    filter_type = request.args.get("type", "all")
    user_reports = Report.query.order_by(Report.created_at.desc()).all() if filter_type in ("all", "users") else []
    group_reports = GroupReport.query.order_by(GroupReport.created_at.desc()).all() if filter_type in ("all", "groups") else []
    users_html = ""
    if filter_type in ("all", "users") and user_reports:
        users_html += f'<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:10px 14px;margin-bottom:12px;font-weight:800;color:#1e40af">👤 مستخدمين ({len(user_reports)})</div>'
        for r in user_reports:
            reporter = db.session.get(User, r.reporter_id) if r.reporter_id else None
            target = db.session.get(User, r.target_id)
            if not target: continue
            target_ban_btn = (f'<a class="btn btn-sm btn-primary" href="{url_for("support_unban_user", uid=target.id)}">✅ إلغاء حظر</a>'
                              if target.is_banned else
                              f'<a class="btn btn-sm btn-danger" href="{url_for("support_ban_user", uid=target.id)}" onclick="return confirm(\'🚫 حظر دائم + مسح كل البيانات؟\')">🚫 حظر دائم</a>')
            users_html += f"""<div class="list-item" style="cursor:default;flex-wrap:wrap;border-right:4px solid #2563eb">
              <img class="avatar-sm" src="{avatar_url(target)}">
              <div style="flex:1;min-width:200px">
                <div class="li-name">🎯 @{target.username} {'<span class="blocked-badge">محظور</span>' if target.is_banned else ''}</div>
                <div class="li-sub">🪪 {('@'+reporter.username) if reporter else 'مجهول'} · {fmt_sd(r.created_at)}</div>
                <div style="font-size:13px;margin-top:6px;background:#fef3c7;border-radius:6px;padding:6px 10px">
                  💬 {html_escape_text(r.reason) or 'بدون سبب'}</div>
              </div>
              <div class="li-actions" style="flex-direction:column;gap:4px">
                <a class="btn btn-sm" href="{url_for('support_user_detail', uid=target.id)}">👁</a>
                {target_ban_btn}
                <a class="btn btn-sm" href="{url_for('support_dismiss_report', rid=r.id)}">✖</a>
              </div></div>"""
    groups_html = ""
    if filter_type in ("all", "groups") and group_reports:
        groups_html += f'<div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:10px;padding:10px 14px;margin-bottom:12px;font-weight:800;color:#92400e">◉ مجموعات ({len(group_reports)})</div>'
        for r in group_reports:
            reporter = db.session.get(User, r.reporter_id) if r.reporter_id else None
            g = db.session.get(Group, r.group_id)
            if not g: continue
            ban_btn = (f'<a class="btn btn-sm btn-primary" href="{url_for("support_unban_group", gid=g.id)}">✅</a>'
                       if g.is_banned else
                       f'<a class="btn btn-sm btn-danger" href="{url_for("support_ban_group", gid=g.id)}">🚫</a>')
            groups_html += f"""<div class="list-item" style="cursor:default;border-right:4px solid #f59e0b">
              <img class="avatar-sm" src="{group_avatar_url(g)}" style="border-radius:12px">
              <div style="flex:1"><div class="li-name">◉ {g.name}</div>
              <div class="li-sub">🪪 {('@'+reporter.username) if reporter else 'مجهول'} · {fmt_sd(r.created_at)}</div>
              <div style="font-size:13px;margin-top:6px;background:#fef3c7;border-radius:6px;padding:6px 10px">
                💬 {html_escape_text(r.reason) or 'بدون سبب'}</div></div>
              <div class="li-actions" style="flex-direction:column;gap:4px">
                <a class="btn btn-sm" href="{url_for('group_view', gid=g.id)}">◉</a>
                {ban_btn}
                <a class="btn btn-sm" href="{url_for('support_dismiss_group_report', rid=r.id)}">✖</a>
              </div></div>"""
    def filt_btn(key, label, count):
        active = filter_type == key
        style = "background:#111827;color:#fff;border-color:#111827" if active else ""
        return f'<a class="btn btn-sm" href="{url_for("support_reports", type=key)}" style="{style}">{label} ({count})</a>'
    user_count = Report.query.count()
    group_count = GroupReport.query.count()
    filter_bar = f"""<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px">
      {filt_btn('all', '📋 الكل', user_count + group_count)}
      {filt_btn('users', '👤', user_count)}
      {filt_btn('groups', '◉', group_count)}</div>"""
    if filter_type == "all": body = users_html + groups_html
    elif filter_type == "users": body = users_html
    else: body = groups_html
    if not body: body = '<p class="empty">لا بلاغات.</p>'
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>📋 البلاغات</h2>{filter_bar}{body}
    <a class="link-center" href="{url_for('support_dashboard')}">← رجوع</a></div>""", title="البلاغات")


@app.route("/support/ban-user/<int:uid>")
@support_required
def support_ban_user(uid):
    u = db.session.get(User, uid)
    if not u:
        flash("غير موجود.", "error"); return redirect(url_for("support_users"))
    if u.is_banned:
        flash("محظور بالفعل.", "info"); return redirect(request.referrer or url_for("support_reports"))
    saved = u.username
    # ✅ حظر دائم فوري — يمسح كل شيء
    if process_auto_ban(u):
        flash(f"🚫 تم الحظر الدائم لـ @{saved}. كل بياناته مسحت.", "success")
    else:
        flash(f"⚠️ فشل.", "error")
    return redirect(request.referrer or url_for("support_reports"))


@app.route("/support/unban-user/<int:uid>")
@support_required
def support_unban_user(uid):
    u = db.session.get(User, uid)
    if not u:
        flash("غير موجود.", "error"); return redirect(url_for("support_users"))
    u.is_banned = False; u.pending_username_release = False; u.username_release_at = None
    u.under_review = False; u.review_reason = ""; u.review_started_at = None
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
        flash("غير موجود.", "error"); return redirect(url_for("support_reports"))
    target = db.session.get(User, r.target_id)
    if target: target.reports_count = max(0, (target.reports_count or 0) - 1)
    db.session.delete(r); db.session.commit()
    flash("تم التجاهل.", "success")
    return redirect(request.referrer or url_for("support_reports"))


@app.route("/support/ban-group/<int:gid>")
@support_required
def support_ban_group(gid):
    g = db.session.get(Group, gid)
    if not g:
        flash("غير موجود.", "error"); return redirect(url_for("support_groups"))
    g.is_banned = True; db.session.commit()
    flash(f"تم حظر {g.name}.", "success")
    return redirect(request.referrer or url_for("support_reports"))


@app.route("/support/unban-group/<int:gid>")
@support_required
def support_unban_group(gid):
    g = db.session.get(Group, gid)
    if not g:
        flash("غير موجود.", "error"); return redirect(url_for("support_groups"))
    g.is_banned = False; db.session.commit()
    flash(f"تم إلغاء حظر {g.name}.", "success")
    return redirect(request.referrer or url_for("support_groups"))


@app.route("/support/dismiss-group-report/<int:rid>")
@support_required
def support_dismiss_group_report(rid):
    r = db.session.get(GroupReport, rid)
    if not r:
        flash("غير موجود.", "error"); return redirect(url_for("support_reports"))
    db.session.delete(r); db.session.commit()
    flash("تم التجاهل.", "success")
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
        if u.is_banned: status = '<span class="blocked-badge">محظور</span>'
        elif u.under_review: status = '<span class="blocked-badge" style="background:#fef3c7">⏳</span>'
        else: status = '<span style="color:#16a34a">نشط</span>'
        action = (f'<a class="btn btn-sm btn-primary" href="{url_for("support_unban_user", uid=u.id)}">✅</a>'
                  if u.is_banned else
                  f'<a class="btn btn-sm btn-danger" href="{url_for("support_ban_user", uid=u.id)}" onclick="return confirm(\'🚫 حظر دائم + مسح كل البيانات؟\')">🚫</a>')
        verify_btn = (f'<a class="btn btn-sm" href="{url_for("support_verify_user", uid=u.id)}">🎨</a>'
                      if u.is_verified else
                      f'<a class="btn btn-sm btn-primary" href="{url_for("support_verify_user", uid=u.id)}">✓</a>')
        rows += f"""<div class="list-item" style="cursor:default">
          <img class="avatar-sm" src="{avatar_url(u)}">
          <div style="flex:1;min-width:0">
            <div class="li-name">{verified_html(u)}{u.short_name} {status}</div>
            <div class="li-sub">ID: {u.public_id} · بلاغات: {u.reports_count or 0}</div>
          </div>
          <div class="li-actions">
            {copy_btn_html(u.username, "يوزر", small=True)}
            {copy_btn_html(u.public_id, "ID", small=True)}
            <a class="btn btn-sm" href="{url_for('support_user_detail', uid=u.id)}">👁</a>
            {verify_btn}{action}
          </div></div>"""
    if not rows: rows = '<p class="empty">لا نتائج.</p>'
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>👥 المستخدمون</h2>
    <form method="GET" style="display:flex;gap:8px;margin-bottom:12px">
      <input name="q" value="{q}" placeholder="بحث" style="flex:1;margin:0">
      <button type="submit" style="width:auto;padding:12px 20px;margin:0">بحث</button></form>
    {rows}
    <a class="link-center" href="{url_for('support_dashboard')}">← رجوع</a></div>""", title="المستخدمون")


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
        action = (f'<a class="btn btn-sm btn-primary" href="{url_for("support_unban_group", gid=g.id)}">✅</a>'
                  if g.is_banned else
                  f'<a class="btn btn-sm btn-danger" href="{url_for("support_ban_group", gid=g.id)}">🚫</a>')
        rows += f"""<div class="list-item" style="cursor:default">
          <img class="avatar-sm" src="{group_avatar_url(g)}" style="border-radius:12px">
          <div style="flex:1"><div class="li-name">{g.name} {status}</div>
          <div class="li-sub">ID: {g.public_id}</div></div>
          <div class="li-actions">
            {copy_btn_html(g.public_id, "ID", small=True)}
            <a class="btn btn-sm" href="{url_for('group_view', gid=g.id)}">عرض</a>
            {action}</div></div>"""
    if not rows: rows = '<p class="empty">لا نتائج.</p>'
    return render_page(FLASH_BLOCK + f"""
    <div class="card"><h2>◉ المجموعات</h2>
    <form method="GET" style="display:flex;gap:8px;margin-bottom:12px">
      <input name="q" value="{q}" placeholder="بحث" style="flex:1;margin:0">
      <button type="submit" style="width:auto;padding:12px 20px;margin:0">بحث</button></form>
    {rows}
    <a class="link-center" href="{url_for('support_dashboard')}">← رجوع</a></div>""", title="المجموعات")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
