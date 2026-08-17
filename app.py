from flask import Flask, render_template_string, send_from_directory, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import json, os, requests

app = Flask(__name__)
CONFIG_FILE = 'config.json'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TELEGRAM_TOKEN = os.environ.get('8613059695:AAHFV4oP7_24UGkBFr5CwrDu9W8rzFb2T3w') # حطه في Environment Variables في Render
ADMIN_ID = int(os.environ.get('ADMIN_ID', '7093004518')) # حط ايديك في Environment Variables
IMGBB_API_KEY = os.environ.get('IMGBB_KEY', "3fd6caa2e26d2b535c568e6616891b46")
RENDER_URL = os.environ.get('RENDER_URL') # https://site-name.onrender.com

DEFAULT_CONFIG = {
    "site_title": "تيم الشبح السوداني للانترنت المجاني",
    "site_image": "",
    "whatsapp_buttons": [{"name": "قروب واتساب", "link": "https://chat.whatsapp.com/XXXXXX"}],
    "apps": [],
    "videos": [],
    "images": [],
    "files": []
}

def load_config():
    if not os.path.exists(CONFIG_FILE) or os.path.getsize(CONFIG_FILE) < 5:
        save_config(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for key in DEFAULT_CONFIG:
                if key not in data: data[key] = DEFAULT_CONFIG[key]
            return data
    except:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

def save_config(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def upload_to_imgbb(file):
    url = "https://api.imgbb.com/1/upload"
    payload = {"key": IMGBB_API_KEY}
    files = {"image": (file.filename, file.read())}
    try:
        r = requests.post(url, data=payload, files=files, timeout=30)
        if r.json().get('success'): return r.json()['data']['url']
    except: pass
    return ''

def whatsapp_fix(url):
    if not url: return "#"
    if "chat.whatsapp.com" in url: return url.replace("https://chat.whatsapp.com/", "whatsapp://chat.whatsapp.com/")
    if "t.me" in url: return url.replace("https://t.me/", "tg://resolve?domain=")
    return url

# ========== الموقع ==========
@app.route('/')
def home():
    config = load_config()
    site_img = f'<img src="{config["site_image"]}" class="site-logo">' if config['site_image'] else ''
    wa_btns = "".join([f'<a href="{whatsapp_fix(b["link"])}" target="_blank" class="btn btn-whatsapp">💬 {b["name"]}</a>' for b in config['whatsapp_buttons']])
    apps_btns = "".join([f'<a href="/download/{a["file"]}" class="btn">⬇ {a["name"]}</a>' for a in config['apps']])
    vids_html = "".join([f'<div class="media-box"><h4>{v["title"]}</h4><video controls src="{v["link"]}"></video></div>' for v in config['videos']])
    imgs_html = "".join([f'<div class="media-box"><h4>{i["title"]}</h4><img src="{i["link"]}"></div>' for i in config['images']])
    files_btns = "".join([f'<a href="/download/{f["file"]}" class="btn btn-file">📁 {f["name"]}</a>' for f in config['files']])

    HTML = f"""<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config['site_title']}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@700&display=swap');
        body {{font-family: 'Cairo'; background: linear-gradient(135deg, #0f172a, #1e3a8a, #000); color: white; text-align: center; padding: 30px 20px;}}
     .container {{ max-width: 900px; margin: auto; }}
        h1 {{ font-size: 2.5em; background: linear-gradient(90deg, #22c55e, #3b82f6, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
     .site-logo {{ max-width: 200px; border-radius: 20px; margin: 20px auto; box-shadow: 0 0 20px #22c55e;}}
     .android-badge {{ background: #22c55e; padding: 5px 15px; border-radius: 20px; font-size: 14px; display: inline-block; margin-bottom: 20px; }}
     .btn {{display: flex; align-items: center; justify-content: center; gap: 10px; background: linear-gradient(90deg, #22c55e, #16a34a); color: white; padding: 15px 25px; border-radius: 12px; text-decoration: none; font-size: 18px; margin: 10px 0; font-weight: bold;}}
     .btn-whatsapp {{ background: linear-gradient(90deg, #25D366, #128C7E); }}
     .btn-file {{ background: linear-gradient(90deg, #f59e0b, #d97706); }}
     .section {{ background: rgba(30,41,59,0.8); padding:20px; border-radius:15px; margin:25px 0; border:1px solid #3b82f6}}
     .media-box {{margin:15px 0}}.media-box img,.media-box video {{width:100%; border-radius:10px; margin-top:10px}}
     .ghost-text {{ margin-top: 40px; font-size: 22px; font-weight: bold; background: linear-gradient(90deg, #22c55e, #3b82f6, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    </style></head>
    <body><div class="container">
        {site_img}
        <h1>{config['site_title']}</h1>
        <div class="android-badge">يدعم أندرويد Android 5.0+</div>
        <div class="section"><h2>💬 قروبات التواصل</h2>{wa_btns if wa_btns else '<p>لا توجد قروبات</p>'}</div>
        <div class="section"><h2>📱 التطبيقات</h2>{apps_btns if apps_btns else '<p>لا توجد تطبيقات</p>'}</div>
        <div class="section"><h2>📁 ملفات</h2>{files_btns if files_btns else '<p>لا توجد ملفات</p>'}</div>
        <div class="section"><h2>🎥 فيديوهات الشرح</h2>{vids_html if vids_html else '<p>لا توجد فيديوهات</p>'}</div>
        <div class="section"><h2>🖼 صور</h2>{imgs_html if imgs_html else '<p>لا توجد صور</p>'}</div>
        <div class="ghost-text">👻 تيم الشبح السوداني للانترنت المجاني 👻</div>
    </div></body></html>"""
    return render_template_string(HTML)

@app.route('/download/<path:filename>')
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# ========== البوت Webhook ==========
application = Application.builder().token(TELEGRAM_TOKEN).build()
user_state = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    keyboard = [
        [InlineKeyboardButton("📝 تغيير العنوان", callback_data='settitle')],
        [InlineKeyboardButton("🖼 تغيير الصورة", callback_data='setimage')],
        [InlineKeyboardButton("💬 إدارة أزرار الواتساب", callback_data='wa_menu')],
        [InlineKeyboardButton("📱 رفع تطبيق", callback_data='addapp')],
        [InlineKeyboardButton("📁 رفع ملف", callback_data='addfile')],
        [InlineKeyboardButton("🎥 رفع فيديو", callback_data='addvid')],
        [InlineKeyboardButton("🖼 رفع صورة", callback_data='addimg')],
        [InlineKeyboardButton("🗑 حذف عنصر", callback_data='del_menu')],
    ]
    await update.message.reply_text("مرحبا بيك في تحكم الشبح 👻", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    data = query.data; user_id = query.from_user.id; config = load_config()
    # نفس اكواد الازرار الفاتت... مختصرة عشان المساحة
    if data == 'settitle': user_state[user_id] = 'settitle'; await query.edit_message_text("ارسل العنوان الجديد")
    elif data == 'wa_menu':
        kb = [[InlineKeyboardButton("➕ اضافة زر واتساب", callback_data='addwa')]]
        for i,b in enumerate(config['whatsapp_buttons']): kb.append([InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f'delwa_{i}')])
        await query.edit_message_text("إدارة أزرار الواتساب:", reply_markup=InlineKeyboardMarkup(kb))
    elif data.startswith('delwa_'): i = int(data.split('_')[1]); config['whatsapp_buttons'].pop(i); save_config(config); await query.edit_message_text("تم المسح ✅")
    #... باقي الازرار نفس الكود الفات

async def webhook_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    action = user_state.get(update.effective_user.id)
    config = load_config()
    if action == 'settitle': config['site_title'] = update.message.text; save_config(config); await update.message.reply_text("تم ✅")
    #... باقي المعالجة نفس الكود الفات
    user_state[update.effective_user.id] = None

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(MessageHandler(filters.ALL, webhook_handler))

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
async def webhook():
    await application.process_update(Update.de_json(request.get_json(force=True), application.bot))
    return "ok"

@app.route("/setwebhook")
async def set_webhook():
    await application.bot.set_webhook(f"{RENDER_URL}/{TELEGRAM_TOKEN}")
    return "Webhook set"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
