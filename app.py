# web_controller_render.py - نسخة معدلة بالكامل لـ Render
import os, sys, json, sqlite3, subprocess, psutil, signal, time, threading, secrets, hashlib, shutil, tempfile, urllib.parse, base64, zlib, gzip, bz2, lzma, marshal, pickle, codecs, re
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, session, jsonify, send_file, abort
from flask_socketio import SocketIO, emit
import logging

# ========== CONFIG ==========
# Render يعطي المنفذ تلقائياً
PORT = int(os.environ.get("PORT", 5000))
HOST = '0.0.0.0'
PASSWORD = os.environ.get("WEB_PASSWORD", "H@ck3rEx0s#2026$Secure!")
DB = os.environ.get("DATABASE_URL", "bots.db")  # لو استخدمت PostgreSQL غيرها
BOTS_DIR = "bots"
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "7093004518,7762880539").split(",")]
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 50 * 1024 * 1024))
MAX_DECODE_DAILY = int(os.environ.get("MAX_DECODE_DAILY", 100))
ALLOWED_PORTS = range(5001, 5100)

# ========== DATABASE ==========
# استخدام SQLite أو PostgreSQL حسب البيئة
if DB.startswith("postgres"):
    import psycopg2
    conn = psycopg2.connect(DB)
    cur = conn.cursor()
else:
    conn = sqlite3.connect(DB, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")

# إنشاء الجداول
cur.execute("""
CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    token TEXT,
    port INTEGER UNIQUE,
    status TEXT DEFAULT 'stopped',
    pid INTEGER,
    start_time TEXT,
    admins TEXT,
    channels TEXT,
    max_file_size INTEGER DEFAULT 5242880,
    max_decode_daily INTEGER DEFAULT 20,
    points_per_decode INTEGER DEFAULT 1
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS bot_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id INTEGER,
    log_type TEXT,
    message TEXT,
    timestamp TEXT
)
""")

conn.commit()

# ========== FLASK APP ==========
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['SESSION_TYPE'] = 'filesystem'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ========== HELPER FUNCTIONS ==========
def get_bots():
    if DB.startswith("postgres"):
        cur.execute("SELECT * FROM bots ORDER BY id DESC")
    else:
        cur.execute("SELECT * FROM bots ORDER BY id DESC")
    return cur.fetchall()

def get_bot_by_id(bid):
    cur.execute("SELECT * FROM bots WHERE id=?", (bid,))
    return cur.fetchone()

def get_bot_by_port(port):
    cur.execute("SELECT * FROM bots WHERE port=?", (port,))
    return cur.fetchone()

def generate_bot_code(token, port, name, admins, channels, max_file_size, max_decode_daily, points_per_decode):
    """توليد كود البوت مع التوكن المدخل من المستخدم"""
    admins_str = json.dumps(admins) if isinstance(admins, list) else admins
    channels_str = json.dumps(channels) if isinstance(channels, list) else channels
    
    return f'''
# bot_{name}.py - تم إنشاؤه بواسطة لوحة التحكم
import os, sys, base64, urllib.parse, codecs, sqlite3, zlib, gzip, bz2, lzma, marshal, pickle, json, hashlib, re, time, struct, ast, io, random, string, tempfile, zipfile, tarfile
from datetime import datetime, timedelta
from Crypto.Cipher import AES, DES, DES3, ARC4, Blowfish, ChaCha20
from Crypto.Util.Padding import unpad
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import threading, secrets, logging

# ========== BOT CONFIG ==========
TOKEN = "{token}"
PORT = {port}
ADMIN_IDS = {admins_str}
CHANNELS = {channels_str}
MAX_FILE_SIZE = {max_file_size}
MAX_DECODE_DAILY = {max_decode_daily}
POINTS_PER_DECODE = {points_per_decode}
DB = "bot_{name}.db"

# ========== DATABASE ==========
conn = sqlite3.connect(DB, check_same_thread=False)
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, referred_by INTEGER, join_date TEXT, decodes_today INTEGER DEFAULT 0, last_decode_date TEXT)""")
cur.execute("""CREATE TABLE IF NOT EXISTS pending_file(user_id INTEGER PRIMARY KEY, file_id TEXT, file_type TEXT, timestamp TEXT)""")
cur.execute("""CREATE TABLE IF NOT EXISTS decodes(user_id INTEGER, method TEXT, timestamp TEXT, success INTEGER, file_hash TEXT)""")
conn.commit()

def get_points(uid):
    cur.execute("SELECT points FROM users WHERE user_id=?", (uid,))
    res = cur.fetchone()
    return res[0] if res else 0

def add_points(uid, pts):
    cur.execute("INSERT INTO users(user_id, points) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET points=points+?", (uid, pts, pts))
    conn.commit()

def can_decode_today(uid):
    cur.execute("SELECT decodes_today, last_decode_date FROM users WHERE user_id=?", (uid,))
    res = cur.fetchone()
    if not res:
        cur.execute("INSERT INTO users(user_id, decodes_today, last_decode_date) VALUES(?,0,?)", (uid, datetime.now().date().isoformat()))
        conn.commit()
        return True
    today = datetime.now().date().isoformat()
    if res[1] != today:
        cur.execute("UPDATE users SET decodes_today=0, last_decode_date=? WHERE user_id=?", (today, uid))
        conn.commit()
        return True
    return res[0] < MAX_DECODE_DAILY

def increment_decode(uid):
    cur.execute("UPDATE users SET decodes_today=decodes_today+1 WHERE user_id=?", (uid,))
    conn.commit()

async def check_sub(user_id, context):
    for chat in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

# ========== DECODING ENGINES ==========
def decode_base64(data):
    try:
        if isinstance(data, str):
            data = re.sub(r'[\\s\\n\\r]', '', data)
            padding = len(data) % 4
            if padding:
                data += '=' * (4 - padding)
        return base64.b64decode(data).decode('utf-8', errors='ignore')
    except:
        return None

def decode_base32(data):
    try:
        if isinstance(data, str):
            data = data.upper().replace(' ', '').replace('\\n', '')
        return base64.b32decode(data).decode('utf-8', errors='ignore')
    except:
        return None

def decode_hex(data):
    try:
        if isinstance(data, str):
            data = data.replace(' ', '').replace('\\n', '').replace('0x', '')
        return bytes.fromhex(data).decode('utf-8', errors='ignore')
    except:
        return None

def decode_rot13(data):
    try:
        if isinstance(data, bytes):
            data = data.decode('utf-8', errors='ignore')
        return codecs.decode(data, 'rot_13')
    except:
        return None

def decode_url(data):
    try:
        if isinstance(data, bytes):
            data = data.decode('utf-8', errors='ignore')
        return urllib.parse.unquote_plus(data)
    except:
        return None

def decode_zlib(data):
    try:
        if isinstance(data, str):
            data = base64.b64decode(data)
        return zlib.decompress(data).decode('utf-8', errors='ignore')
    except:
        try:
            return zlib.decompress(data, wbits=-15).decode('utf-8', errors='ignore')
        except:
            return None

def decode_gzip(data):
    try:
        if isinstance(data, str):
            data = base64.b64decode(data)
        return gzip.decompress(data).decode('utf-8', errors='ignore')
    except:
        return None

def decode_bzip2(data):
    try:
        if isinstance(data, str):
            data = base64.b64decode(data)
        return bz2.decompress(data).decode('utf-8', errors='ignore')
    except:
        return None

def decode_lzma(data):
    try:
        import lzma
        if isinstance(data, str):
            data = base64.b64decode(data)
        return lzma.decompress(data).decode('utf-8', errors='ignore')
    except:
        return None

def decode_xor(data):
    keys = [0x5A, 0xFF, 0xAA, 0x55, 0x11, 0x22, 0x33, 0x44, 0x66, 0x77, 0x88, 0x99]
    for key in keys:
        try:
            if isinstance(data, str):
                data = data.encode('latin-1')
            decoded = bytes([b ^ key for b in data])
            text = decoded.decode('utf-8', errors='ignore')
            if len(text) > 10 and any(c.isalnum() for c in text[:50]):
                return text
        except:
            continue
    return None

def decode_marshal(data):
    try:
        if isinstance(data, str):
            data = base64.b64decode(data)
        obj = marshal.loads(data)
        return str(obj)
    except:
        return None

def decode_pickle(data):
    try:
        if isinstance(data, str):
            data = base64.b64decode(data)
        obj = pickle.loads(data)
        return str(obj)
    except:
        return None

def decode_json(data):
    try:
        if isinstance(data, bytes):
            data = data.decode('utf-8', errors='ignore')
        obj = json.loads(data)
        return json.dumps(obj, indent=2)
    except:
        return None

def decode_yaml(data):
    try:
        import yaml
        if isinstance(data, bytes):
            data = data.decode('utf-8', errors='ignore')
        obj = yaml.safe_load(data)
        return yaml.dump(obj)
    except:
        return None

def decode_xml(data):
    try:
        import xml.etree.ElementTree as ET
        if isinstance(data, bytes):
            data = data.decode('utf-8', errors='ignore')
        root = ET.fromstring(data)
        return ET.tostring(root, encoding='unicode')
    except:
        return None

def decode_jwt(data):
    try:
        import jwt
        if isinstance(data, str):
            return jwt.decode(data, options={{'verify_signature': False}}, algorithms=['HS256', 'RS256', 'ES256'])
        return None
    except:
        return None

def decode_any(data):
    """محاولة كل طرق الفك"""
    decoders = [
        decode_base64, decode_base32, decode_hex, decode_rot13,
        decode_url, decode_zlib, decode_gzip, decode_bzip2,
        decode_lzma, decode_xor, decode_marshal, decode_pickle,
        decode_json, decode_yaml, decode_xml, decode_jwt
    ]
    
    for decoder in decoders:
        try:
            result = decoder(data)
            if result and result != data and len(str(result)) > 5:
                return result
        except:
            continue
    return None

def auto_decode(data, max_depth=10):
    """فك تلقائي متسلسل"""
    results = []
    depth = 0
    
    while depth < max_depth:
        decoded = False
        layer_results = []
        
        decoders = [
            ('Base64', decode_base64), ('Base32', decode_base32),
            ('Hex', decode_hex), ('ROT13', decode_rot13),
            ('URL', decode_url), ('Zlib', decode_zlib),
            ('Gzip', decode_gzip), ('Bzip2', decode_bzip2),
            ('LZMA', decode_lzma), ('XOR', decode_xor),
            ('Marshal', decode_marshal), ('Pickle', decode_pickle),
            ('JSON', decode_json), ('YAML', decode_yaml),
            ('XML', decode_xml), ('JWT', decode_jwt)
        ]
        
        for name, decoder in decoders:
            try:
                result = decoder(data)
                if result and result != data and len(str(result)) > 5:
                    if 'import' in str(result)[:200] or 'def ' in str(result)[:200] or 'class ' in str(result)[:200]:
                        results.append({{
                            'layer': depth,
                            'method': name,
                            'result': result,
                            'is_python': True
                        }})
                        return results
                    layer_results.append((name, result))
                    decoded = True
            except:
                continue
        
        if not decoded:
            break
        
        best = max(layer_results, key=lambda x: len(str(x[1])))
        results.append({{
            'layer': depth,
            'method': best[0],
            'result': best[1],
            'is_python': False
        }})
        data = best[1]
        depth += 1
    
    return results

# ========== BOT HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args
    now = datetime.now().isoformat()
    
    cur.execute("INSERT INTO users(user_id, join_date) VALUES(?,?) ON CONFLICT(user_id) DO NOTHING", (uid, now))
    conn.commit()
    
    if not await check_sub(uid, context):
        keyboard = []
        for channel in CHANNELS:
            keyboard.append([InlineKeyboardButton(f"📢 {{channel}}", url=f"https://t.me/{{channel.replace('@','')}}")])
        keyboard.append([InlineKeyboardButton("✅ تحقق", callback_data="check_sub")])
        await update.message.reply_text("🔒 اشترك في القنوات أولاً", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    points = get_points(uid)
    keyboard = [
        [InlineKeyboardButton("🔓 فك تلقائي", callback_data="auto"),
         InlineKeyboardButton("💎 نقاطي", callback_data="points")],
        [InlineKeyboardButton("🛒 شراء نقاط", callback_data="shop"),
         InlineKeyboardButton("🏆 المتصدرين", callback_data="top")],
        [InlineKeyboardButton("👥 رابط دعوة", callback_data="ref")]
    ]
    if uid in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")])
    
    await update.message.reply_text(
        f"مرحباً {{update.effective_user.first_name}} 🌹\\n"
        f"نقاطك: {{points}}\\n"
        f"الحد اليومي: {{MAX_DECODE_DAILY}}\\n\\n"
        f"📤 أرسل ملف أو نص للفك",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if not await check_sub(uid, context):
        await update.message.reply_text("❌ اشترك أولاً")
        return
    
    if update.message.document and update.message.document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(f"❌ حجم الملف كبير (الحد {{MAX_FILE_SIZE//1024//1024}}MB)")
        return
    
    if not can_decode_today(uid):
        await update.message.reply_text(f"❌ تجاوزت الحد اليومي ({{MAX_DECODE_DAILY}})")
        return
    
    msg = await update.message.reply_text("⏳ جاري الفك...")
    
    try:
        if update.message.document:
            file = await update.message.document.get_file()
            data = await file.download_as_bytearray()
        elif update.message.text:
            data = update.message.text.encode()
        else:
            await msg.edit_text("❌ أرسل ملف أو نص")
            return
        
        layers = auto_decode(data)
        
        if not layers:
            await msg.edit_text("❌ لم أتمكن من فك التشفير")
            return
        
        result_text = "🔓 **نتائج الفك المتسلسل:**\\n\\n"
        for layer in layers:
            if layer.get('is_python'):
                result_text += f"✅ **كود بايثون مكشوف!**\\n```python\\n{{layer['result'][:2000]}}\\n```"
                break
            result_text += f"📌 **الطبقة {{layer['layer']+1}}:** {{layer['method']}}\\n```\\n{{str(layer['result'])[:500]}}\\n```\\n\\n"
        
        increment_decode(uid)
        await msg.edit_text(result_text[:4000], parse_mode='Markdown')
        
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {{str(e)[:200]}}")

# ========== RUN BOT ==========
if __name__ == "__main__":
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
    
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CallbackQueryHandler(button_handler))
    app_bot.add_handler(MessageHandler(filters.Document.ALL | filters.TEXT & ~filters.COMMAND, handle_file))
    print(f"✅ Bot {{name}} running on port {{port}}")
    app_bot.run_polling(allowed_updates=Update.ALL_TYPES)
'''

def start_bot_process(bid, port, token, name, admins, channels, max_file_size, max_decode_daily, points_per_decode):
    """تشغيل بوت جديد مع التوكن المدخل"""
    try:
        os.makedirs(BOTS_DIR, exist_ok=True)
        bot_file = f"{BOTS_DIR}/bot_{bid}.py"
        
        code = generate_bot_code(
            token, port, name, 
            admins or [7093004518, 7762880539],
            channels or ["@Zero_free_Online", "@GOOD_HAMASAT", "@ZERO_MAX_COOL"],
            max_file_size or 5242880,
            max_decode_daily or 20,
            points_per_decode or 1
        )
        
        with open(bot_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        proc = subprocess.Popen(
            [sys.executable, bot_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=BOTS_DIR
        )
        
        cur.execute("""
            UPDATE bots 
            SET status='running', pid=?, start_time=? 
            WHERE id=?
        """, (proc.pid, datetime.now().isoformat(), bid))
        conn.commit()
        
        cur.execute("INSERT INTO bot_logs(bot_id, log_type, message, timestamp) VALUES(?,?,?,?)",
                   (bid, 'info', f'Bot started on port {port}', datetime.now().isoformat()))
        conn.commit()
        
        return proc.pid
    except Exception as e:
        cur.execute("INSERT INTO bot_logs(bot_id, log_type, message, timestamp) VALUES(?,?,?,?)",
                   (bid, 'error', f'Failed to start: {str(e)}', datetime.now().isoformat()))
        conn.commit()
        return None

def stop_bot_process(bid, pid):
    """إيقاف بوت"""
    try:
        if pid:
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
        cur.execute("UPDATE bots SET status='stopped', pid=NULL WHERE id=?", (bid,))
        conn.commit()
        cur.execute("INSERT INTO bot_logs(bot_id, log_type, message, timestamp) VALUES(?,?,?,?)",
                   (bid, 'info', 'Bot stopped', datetime.now().isoformat()))
        conn.commit()
        return True
    except:
        return False

# ========== WEB ROUTES ==========
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect('/login')
    bots = get_bots()
    return render_template('dashboard.html', bots=bots, port=PORT)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == PASSWORD:
            session['logged_in'] = True
            session.permanent = True
            return redirect('/')
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>🔐 Admin Login</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Segoe UI',Arial;background:linear-gradient(135deg,#0d1117,#161b22);color:#fff;display:flex;justify-content:center;align-items:center;height:100vh}
        .login{background:#161b22;padding:50px;border-radius:15px;border:1px solid #30363d;width:350px;max-width:90%}
        .login h2{color:#58a6ff;text-align:center;margin-bottom:10px}
        .login p{color:#8b949e;text-align:center;margin-bottom:30px}
        input{width:100%;padding:12px;margin:10px 0;background:#0d1117;border:1px solid #30363d;color:#fff;border-radius:8px;font-size:14px}
        input:focus{outline:none;border-color:#58a6ff}
        button{width:100%;padding:12px;background:#238636;border:none;color:#fff;border-radius:8px;font-size:16px;cursor:pointer;transition:0.3s}
        button:hover{background:#2ea043}
        .version{color:#8b949e;font-size:12px;text-align:center;margin-top:15px}
    </style>
    </head>
    <body>
    <div class="login">
        <h2>🔐 لوحة التحكم</h2>
        <p>Decoder Bot Manager</p>
        <form method=post>
            <input type=password name=password placeholder="كلمة السر" required autofocus>
            <button type=submit>🚀 دخول</button>
        </form>
        <div class="version">v3.0 - Render Ready</div>
    </div>
    </body></html>
    '''

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/login')

@app.route('/api/bots', methods=['GET'])
def api_bots():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    bots = get_bots()
    return jsonify([{
        'id': b[0], 'name': b[1], 'token': b[2][:20] + '...' if b[2] else 'None',
        'port': b[3], 'status': b[4], 'pid': b[5],
        'start_time': b[6]
    } for b in bots])

@app.route('/api/bots', methods=['POST'])
def api_create_bot():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    name = data.get('name')
    token = data.get('token')
    port = data.get('port')
    admins = data.get('admins', [7093004518, 7762880539])
    channels = data.get('channels', ["@Zero_free_Online", "@GOOD_HAMASAT", "@ZERO_MAX_COOL"])
    max_file_size = data.get('max_file_size', 5242880)
    max_decode_daily = data.get('max_decode_daily', 20)
    points_per_decode = data.get('points_per_decode', 1)
    
    if not name or not token or not port:
        return jsonify({'error': 'Missing name, token or port'}), 400
    
    if port not in ALLOWED_PORTS:
        return jsonify({'error': f'Port must be between {ALLOWED_PORTS.start}-{ALLOWED_PORTS.stop-1}'}), 400
    
    cur.execute("SELECT id FROM bots WHERE name=? OR port=?", (name, port))
    if cur.fetchone():
        return jsonify({'error': 'Name or port already exists'}), 400
    
    cur.execute("""
        INSERT INTO bots (name, token, port, status, admins, channels, max_file_size, max_decode_daily, points_per_decode)
        VALUES (?, ?, ?, 'stopped', ?, ?, ?, ?, ?)
    """, (name, token, port, json.dumps(admins), json.dumps(channels), max_file_size, max_decode_daily, points_per_decode))
    conn.commit()
    bid = cur.lastrowid
    
    return jsonify({'success': True, 'id': bid})

@app.route('/api/bots/<int:bid>/start', methods=['POST'])
def api_start_bot(bid):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    bot = get_bot_by_id(bid)
    if not bot:
        return jsonify({'error': 'Bot not found'}), 404
    
    if bot[4] == 'running':
        return jsonify({'error': 'Bot already running'}), 400
    
    token = bot[2]
    port = bot[3]
    name = bot[1]
    admins = json.loads(bot[7]) if bot[7] else [7093004518, 7762880539]
    channels = json.loads(bot[8]) if bot[8] else ["@Zero_free_Online", "@GOOD_HAMASAT", "@ZERO_MAX_COOL"]
    max_file_size = bot[9] or 5242880
    max_decode_daily = bot[10] or 20
    points_per_decode = bot[11] or 1
    
    pid = start_bot_process(bid, port, token, name, admins, channels, max_file_size, max_decode_daily, points_per_decode)
    if pid:
        return jsonify({'success': True, 'pid': pid})
    return jsonify({'error': 'Failed to start'}), 500

@app.route('/api/bots/<int:bid>/stop', methods=['POST'])
def api_stop_bot(bid):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    bot = get_bot_by_id(bid)
    if not bot:
        return jsonify({'error': 'Bot not found'}), 404
    
    if bot[4] == 'stopped':
        return jsonify({'error': 'Bot already stopped'}), 400
    
    if stop_bot_process(bid, bot[5]):
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to stop'}), 500

@app.route('/api/bots/<int:bid>/delete', methods=['DELETE'])
def api_delete_bot(bid):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    bot = get_bot_by_id(bid)
    if not bot:
        return jsonify({'error': 'Bot not found'}), 404
    
    if bot[4] == 'running':
        stop_bot_process(bid, bot[5])
    
    cur.execute("DELETE FROM bots WHERE id=?", (bid,))
    conn.commit()
    
    bot_file = f"{BOTS_DIR}/bot_{bid}.py"
    if os.path.exists(bot_file):
        os.remove(bot_file)
    
    return jsonify({'success': True})

@app.route('/api/bots/<int:bid>/logs', methods=['GET'])
def api_bot_logs(bid):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    cur.execute("SELECT * FROM bot_logs WHERE bot_id=? ORDER BY id DESC LIMIT 50", (bid,))
    logs = cur.fetchall()
    return jsonify([{
        'id': l[0], 'type': l[2], 'message': l[3], 'timestamp': l[4]
    } for l in logs])

@app.route('/api/settings', methods=['GET'])
def api_settings():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({
        'ports': list(ALLOWED_PORTS),
        'max_file_size': 50,
        'max_decode_daily': 100
    })

@app.route('/api/status')
def api_status():
    bots = get_bots()
    return jsonify({
        'uptime': time.time() - start_time,
        'total_bots': len(bots),
        'running_bots': len([b for b in bots if b[4] == 'running']),
        'stopped_bots': len([b for b in bots if b[4] == 'stopped'])
    })

# ========== TEMPLATE ==========
os.makedirs('templates', exist_ok=True)

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>🤖 Bot Control Panel</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Segoe UI',Arial;background:#0d1117;color:#c9d1d9;padding:20px}
        .container{max-width:1400px;margin:0 auto}
        .header{background:linear-gradient(135deg,#161b22,#1c2333);padding:25px;border-radius:15px;border:1px solid #30363d;margin-bottom:25px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap}
        .header h1{color:#58a6ff}
        .header .port-info{color:#8b949e;font-size:13px}
        .stats{display:flex;gap:30px;flex-wrap:wrap}
        .stat-item{text-align:center}
        .stat-item .num{font-size:28px;font-weight:bold;color:#f0f6fc}
        .stat-item .label{font-size:12px;color:#8b949e}
        .card{background:#161b22;padding:20px;border-radius:12px;border:1px solid #30363d;margin-bottom:20px}
        .card h3{color:#58a6ff;margin-bottom:15px}
        .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:20px}
        .bot-card{background:#0d1117;padding:20px;border-radius:10px;border:1px solid #30363d;transition:all 0.3s}
        .bot-card:hover{transform:translateY(-3px);border-color:#58a6ff}
        .bot-card .name{font-size:18px;font-weight:bold;color:#f0f6fc}
        .bot-card .port{color:#8b949e;font-size:13px}
        .status{display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:bold}
        .status.running{background:#238636;color:#fff}
        .status.stopped{background:#da3633;color:#fff}
        .btn{padding:8px 16px;border:none;border-radius:6px;cursor:pointer;font-size:13px;transition:all 0.3s;margin:3px}
        .btn:hover{transform:scale(1.05)}
        .btn-start{background:#238636;color:#fff}
        .btn-start:hover{background:#2ea043}
        .btn-stop{background:#da3633;color:#fff}
        .btn-stop:hover{background:#f85149}
        .btn-delete{background:#8b949e;color:#fff}
        .btn-delete:hover{background:#6e7681}
        .btn-primary{background:#1f6feb;color:#fff}
        .btn-primary:hover{background:#388bfd}
        .btn-success{background:#238636;color:#fff}
        .btn-success:hover{background:#2ea043}
        .form-group{margin:10px 0}
        .form-group label{display:block;margin-bottom:5px;color:#8b949e;font-size:13px}
        .form-group input,.form-group select{width:100%;padding:10px;background:#0d1117;border:1px solid #30363d;color:#fff;border-radius:6px}
        .form-group input:focus,.form-group select:focus{outline:none;border-color:#58a6ff}
        .modal{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);z-index:1000;justify-content:center;align-items:center}
        .modal-content{background:#161b22;padding:30px;border-radius:15px;width:550px;max-width:95%;border:1px solid #30363d;max-height:90vh;overflow-y:auto}
        .modal-content h2{color:#58a6ff;margin-bottom:20px}
        .modal-close{float:right;background:none;border:none;color:#8b949e;font-size:24px;cursor:pointer}
        .alert{display:none;padding:12px;border-radius:8px;margin:10px 0}
        .alert-success{background:#23863633;border:1px solid #238636;color:#3fb950}
        .alert-error{background:#da363333;border:1px solid #da3633;color:#f85149}
        .flex{display:flex;gap:10px;flex-wrap:wrap}
        .token-hidden{color:#58a6ff;font-family:monospace}
        .logs{background:#0d1117;padding:10px;border-radius:6px;max-height:150px;overflow-y:auto;font-size:12px;font-family:monospace}
        .log-info{color:#58a6ff}
        .log-error{color:#f85149}
        .log-success{color:#3fb950}
        .render-badge{background:#1f6feb;color:#fff;padding:3px 12px;border-radius:20px;font-size:11px}
        @media(max-width:768px){.header{flex-direction:column;gap:15px}.grid{grid-template-columns:1fr}}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <h1>🤖 Bot Control Panel</h1>
            <small style="color:#8b949e">إدارة البوتات المتعددة - Render Ready</small>
            <div style="margin-top:5px">
                <span class="render-badge">🚀 Render.com</span>
                <span class="render-badge" style="background:#238636">🟢 PORT: {{ port }}</span>
            </div>
        </div>
        <div class="stats">
            <div class="stat-item"><div class="num" id="totalBots">0</div><div class="label">إجمالي البوتات</div></div>
            <div class="stat-item"><div class="num" id="runningBots">0</div><div class="label">قيد التشغيل</div></div>
            <div class="stat-item"><div class="num" id="stoppedBots">0</div><div class="label">متوقفة</div></div>
        </div>
    </div>

    <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">
            <h3>📋 البوتات</h3>
            <button class="btn btn-primary" onclick="openModal()">➕ إضافة بوت</button>
        </div>
        <div id="alert" class="alert"></div>
        <div class="grid" id="botsGrid"></div>
    </div>
</div>

<!-- Modal إضافة بوت -->
<div id="modal" class="modal">
    <div class="modal-content">
        <button class="modal-close" onclick="closeModal()">✕</button>
        <h2>➕ إضافة بوت جديد</h2>
        <div style="color:#8b949e;font-size:13px;margin-bottom:15px">
            ⚠️ أدخل توكن البوت الذي حصلت عليه من @BotFather
        </div>
        <form id="botForm">
            <div class="form-group">
                <label>اسم البوت</label>
                <input type="text" id="botName" placeholder="مثال: decoder_v1" required>
            </div>
            <div class="form-group">
                <label>🔑 توكن البوت (من BotFather)</label>
                <input type="text" id="botToken" placeholder="123456:ABCdef..." required>
            </div>
            <div class="form-group">
                <label>المنفذ (PORT)</label>
                <input type="number" id="botPort" placeholder="5001-5099" required min="5001" max="5099">
            </div>
            <div class="form-group">
                <label>حجم الملف الأقصى (MB)</label>
                <input type="number" id="maxFileSize" value="5" min="1" max="50">
            </div>
            <div class="form-group">
                <label>الحد اليومي للفك</label>
                <input type="number" id="maxDecodeDaily" value="20" min="1" max="100">
            </div>
            <button type="submit" class="btn btn-primary" style="width:100%;padding:12px">🚀 إنشاء البوت</button>
        </form>
    </div>
</div>

<!-- Modal السجلات -->
<div id="logModal" class="modal">
    <div class="modal-content">
        <button class="modal-close" onclick="closeLogModal()">✕</button>
        <h2>📜 سجلات البوت</h2>
        <div id="logsContainer" class="logs"></div>
    </div>
</div>

<script>
    // ========== FUNCTIONS ==========
    async function loadBots() {
        try {
            const res = await fetch('/api/bots');
            const bots = await res.json();
            const grid = document.getElementById('botsGrid');
            grid.innerHTML = '';
            
            let total = 0, running = 0, stopped = 0;
            
            bots.forEach(bot => {
                total++;
                if (bot.status === 'running') running++;
                else stopped++;
                
                const card = document.createElement('div');
                card.className = 'bot-card';
                card.innerHTML = `
                    <div class="flex" style="justify-content:space-between;align-items:center">
                        <div>
                            <div class="name">${bot.name}</div>
                            <div class="port">🔌 Port: ${bot.port} | 🆔 ${bot.id}</div>
                        </div>
                        <span class="status ${bot.status}">${bot.status === 'running' ? '● نشط' : '● متوقف'}</span>
                    </div>
                    <div style="margin:10px 0;font-size:12px;color:#8b949e">
                        🔑 توكن: <span class="token-hidden">${bot.token}</span>
                        ${bot.pid ? '| PID: '+bot.pid : ''}
                        ${bot.start_time ? '| بدأ: '+new Date(bot.start_time).toLocaleString() : ''}
                    </div>
                    <div class="flex">
                        ${bot.status === 'stopped' ? 
                            `<button class="btn btn-start" onclick="startBot(${bot.id})">▶ تشغيل</button>` :
                            `<button class="btn btn-stop" onclick="stopBot(${bot.id})">⏹ إيقاف</button>`
                        }
                        <button class="btn btn-success" onclick="viewLogs(${bot.id})">📜 سجلات</button>
                        <button class="btn btn-delete" onclick="deleteBot(${bot.id})">🗑 حذف</button>
                    </div>
                `;
                grid.appendChild(card);
            });
            
            document.getElementById('totalBots').textContent = total;
            document.getElementById('runningBots').textContent = running;
            document.getElementById('stoppedBots').textContent = stopped;
        } catch(e) {
            showAlert('خطأ في تحميل البوتات', 'error');
        }
    }

    async function startBot(id) {
        try {
            const res = await fetch(`/api/bots/${id}/start`, {method: 'POST'});
            const data = await res.json();
            if (data.success) {
                showAlert('✅ تم تشغيل البوت', 'success');
                loadBots();
            } else {
                showAlert('❌ '+data.error, 'error');
            }
        } catch(e) {
            showAlert('❌ فشل التشغيل', 'error');
        }
    }

    async function stopBot(id) {
        try {
            const res = await fetch(`/api/bots/${id}/stop`, {method: 'POST'});
            const data = await res.json();
            if (data.success) {
                showAlert('✅ تم إيقاف البوت', 'success');
                loadBots();
            } else {
                showAlert('❌ '+data.error, 'error');
            }
        } catch(e) {
            showAlert('❌ فشل الإيقاف', 'error');
        }
    }

    async function deleteBot(id) {
        if (!confirm('⚠️ هل أنت متأكد من حذف هذا البوت؟')) return;
        try {
            const res = await fetch(`/api/bots/${id}/delete`, {method: 'DELETE'});
            const data = await res.json();
            if (data.success) {
                showAlert('✅ تم حذف البوت', 'success');
                loadBots();
            } else {
                showAlert('❌ '+data.error, 'error');
            }
        } catch(e) {
            showAlert('❌ فشل الحذف', 'error');
        }
    }

    async function viewLogs(id) {
        try {
            const res = await fetch(`/api/bots/${id}/logs`);
            const logs = await res.json();
            const container = document.getElementById('logsContainer');
            container.innerHTML = logs.length ? logs.map(l => 
                `<div class="log-${l.type}">[${l.timestamp}] ${l.message}</div>`
            ).join('') : '<div style="color:#8b949e">لا توجد سجلات</div>';
            document.getElementById('logModal').style.display = 'flex';
        } catch(e) {
            showAlert('❌ فشل تحميل السجلات', 'error');
        }
    }

    function openModal() {
        document.getElementById('modal').style.display = 'flex';
        document.getElementById('botForm').reset();
    }

    function closeModal() {
        document.getElementById('modal').style.display = 'none';
    }

    function closeLogModal() {
        document.getElementById('logModal').style.display = 'none';
    }

    function showAlert(msg, type) {
        const alert = document.getElementById('alert');
        alert.style.display = 'block';
        alert.className = 'alert alert-'+type;
        alert.textContent = msg;
        setTimeout(() => { alert.style.display = 'none'; }, 5000);
    }

    // ========== FORM HANDLER ==========
    document.getElementById('botForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('botName').value;
        const token = document.getElementById('botToken').value;
        const port = parseInt(document.getElementById('botPort').value);
        const max_file_size = parseInt(document.getElementById('maxFileSize').value) * 1024 * 1024;
        const max_decode_daily = parseInt(document.getElementById('maxDecodeDaily').value);
        
        if (!token || token.length < 10) {
            showAlert('❌ توكن غير صحيح', 'error');
            return;
        }
        
        try {
            const res = await fetch('/api/bots', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, token, port, max_file_size, max_decode_daily})
            });
            const data = await res.json();
            if (data.success) {
                showAlert('✅ تم إنشاء البوت', 'success');
                closeModal();
                loadBots();
            } else {
                showAlert('❌ '+data.error, 'error');
            }
        } catch(e) {
            showAlert('❌ فشل الإنشاء', 'error');
        }
    });

    // ========== AUTO REFRESH ==========
    loadBots();
    setInterval(loadBots, 15000);

    window.onclick = function(e) {
        if (e.target === document.getElementById('modal')) closeModal();
        if (e.target === document.getElementById('logModal')) closeLogModal();
    }
</script>
</body>
</html>
''')

# ========== STARTUP ==========
start_time = time.time()

if __name__ == '__main__':
    os.makedirs(BOTS_DIR, exist_ok=True)
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║     🔐 Legendary Bot Control Panel - Render Ready          ║
╠══════════════════════════════════════════════════════════════╣
║  🌐 URL: http://{HOST}:{PORT}                              ║
║  🔑 Password: {PASSWORD}                                   ║
║  📂 Bots Dir: {BOTS_DIR}                                  ║
║  📊 Allowed Ports: {ALLOWED_PORTS.start}-{ALLOWED_PORTS.stop-1} ║
║  🚀 Port: {PORT} (من Render)                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    socketio.run(app, host=HOST, port=PORT, debug=False, allow_unsafe_werkzeug=True)
