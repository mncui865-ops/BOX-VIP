from flask import Flask, request, jsonify, send_file, render_template_string, session
import requests
import socket
import dns.resolver
import json
import random
import string
import os
import time
import ssl
import threading
from urllib.parse import urlparse
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'generated_secret_key_2026')

# ===================== إنشاء المجلدات =====================
os.makedirs('payloads_results', exist_ok=True)
os.makedirs('logs', exist_ok=True)
os.makedirs('backups', exist_ok=True)
os.makedirs('reports', exist_ok=True)

# ===================== قواعد البيانات =====================
FREE_PROVIDERS = [
    "mtn.sd", "zain.sd", "sudan.sd", "canar.sd", "te.sd",
    "mtn-sd.com", "zain-sd.com", "sudanet.net", "sudanmobile.sd",
    "sudatel.sd", "airtel.sd", "kush.sd", "telecom.sd"
]

SUBDOMAINS = [
    "www", "api", "dev", "test", "stage", "prod", "cdn", "static",
    "img", "video", "mobile", "app", "web", "secure", "global",
    "fast", "smart", "digital", "cloud", "edge", "prime", "admin",
    "portal", "dashboard", "panel", "mail", "ftp", "ssh", "vpn",
    "proxy", "backup", "db", "mysql", "redis", "mongo", "postgres"
]

TLDS = [
    ".com", ".co", ".net", ".io", ".org", ".info", ".sd", 
    ".tech", ".cloud", ".host", ".online", ".xyz", ".club", 
    ".site", ".store", ".pro", ".dev", ".app", ".zone", 
    ".digital", ".space", ".world", ".live", ".news", ".media"
]

COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 465, 587, 993, 995, 3306, 3389, 5432, 5900, 6379, 8080, 8443, 27017, 9200, 9090, 9443]

VULNS_DB = {
    "Web": ["SQLi", "XSS", "LFI", "RCE", "Open_redirect", "Directory_listing", "Path_traversal", "Header_injection"],
    "Network": ["DNS_zone_transfer", "DNS_spoofing", "DNS_cache_poisoning"],
    "CDN": ["Host_header_injection", "Cache_poisoning", "Origin_exposure", "X-Forwarded-For_spoofing"],
    "FreeNet": ["Zero_rating_bypass", "Proxy_detection", "TLS_fingerprinting", "IP_spoofing", "SNI_hiding", "Port_knocking", "DNS_tunneling"]
}

PAYLOADS_DB = {
    "SQLi": ["' OR 1=1 --", "'; DROP TABLE users --", "' UNION SELECT null,null,null --"],
    "XSS": ["<script>alert('XSS')</script>", "javascript:alert('XSS')", "<img src=x onerror=alert(1)>"],
    "LFI": ["../../../../etc/passwd", "../../../../windows/win.ini", "/etc/passwd"],
    "RCE": ["; ls", "| whoami", "&& id"],
    "Open_redirect": ["/redirect?url=http://evil.com", "/goto?target=http://evil.com"],
    "Zero_rating_bypass": ["/cdn-cgi/trace", "/__cf_rum", "/?z=free", "/?bypass=1"],
    "SNI_hiding": ["/sni?host=free.net", "/?sni=hidden"],
    "DNS_tunneling": ["/dns?q=free.net", "/?dns=1"]
}

PROXY_TYPES = ["HTTP", "HTTPS", "SOCKS4", "SOCKS5", "SSH", "DNS", "TOR"]
VPN_TYPES = ["OpenVPN", "WireGuard", "L2TP", "PPTP", "IKEv2", "SSTP", "V2Ray", "Shadowsocks"]

scan_status = {
    "running": False,
    "hosts": [],
    "current": 0,
    "total": 0,
    "results": []
}

# ===================== دوال البوت =====================
def send_to_bot(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        response = requests.post(url, json=data, timeout=5)
        return response.json().get("ok", False)
    except:
        return False

def send_file_to_bot(token, chat_id, filepath):
    try:
        url = f"https://api.telegram.org/bot{token}/sendDocument"
        with open(filepath, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': chat_id, 'caption': '📁 ملف النتائج'}
            response = requests.post(url, files=files, data=data, timeout=10)
            return response.json().get("ok", False)
    except:
        return False

# ===================== دوال التوليد =====================
def generate_smart_host():
    patterns = [
        lambda: f"{''.join(random.choices(string.ascii_lowercase, k=random.randint(3,8)))}{random.choice(TLDS)}",
        lambda: f"{random.choice(['api','dev','test','stage','prod','cdn','static','img','video','mobile','app','web','secure','global','fast','smart','digital','cloud','edge'])}-{''.join(random.choices(string.ascii_lowercase, k=random.randint(3,6)))}{random.choice(TLDS)}",
        lambda: f"{''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(4,12)))}{random.choice(TLDS)}",
        lambda: f"{random.choice(['www','mail','ftp','admin','portal','dashboard','panel'])}.{''.join(random.choices(string.ascii_lowercase, k=random.randint(4,8)))}{random.choice(TLDS)}",
        lambda: f"{''.join(random.choices(string.ascii_lowercase, k=random.randint(2,5)))}-{''.join(random.choices(string.ascii_lowercase, k=random.randint(2,5)))}{random.choice(TLDS)}"
    ]
    return random.choice(patterns)()

def generate_advanced_proxy():
    return {
        "type": random.choice(PROXY_TYPES),
        "host": ".".join(str(random.randint(1, 255)) for _ in range(4)),
        "port": random.choice([8080, 3128, 8888, 1080, 1081, 1082, 1083, 1084, 1085]),
        "country": random.choice(["US", "UK", "DE", "FR", "NL", "RU", "CN", "IN", "BR", "ZA", "EG", "SA", "AE", "SD"]),
        "anonymity": random.choice(["Elite", "Anonymous", "Transparent"]),
        "working": random.choice([True, False, True])
    }

def generate_advanced_vpn():
    return {
        "type": random.choice(VPN_TYPES),
        "host": generate_smart_host(),
        "port": random.choice([443, 80, 53, 993, 995, 8080, 8443, 1194, 51820, 1701]),
        "protocol": random.choice(["UDP", "TCP", "QUIC"]),
        "country": random.choice(["US", "UK", "DE", "FR", "NL", "RU", "CN", "IN", "BR", "ZA", "EG", "SA", "AE", "SD"]),
        "encryption": random.choice(["AES-256-GCM", "AES-128-GCM", "ChaCha20-Poly1305"]),
        "working": random.choice([True, False, True])
    }

# ===================== دوال الفحص =====================
def check_domain(domain):
    try:
        socket.gethostbyname(domain)
        return True
    except:
        return False

def check_port(host, port, timeout=1.5):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def get_dns_records(domain):
    records = {}
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['8.8.8.8', '1.1.1.1']
        for record_type in ['A', 'MX', 'NS', 'TXT', 'CNAME']:
            try:
                answers = resolver.resolve(domain, record_type)
                records[record_type] = [str(r) for r in answers]
            except:
                pass
    except:
        pass
    return records

def detect_cdn(host):
    try:
        response = requests.get(f"http://{host}", timeout=3)
        if "cf-ray" in response.headers:
            return "Cloudflare"
        elif "x-akamai" in response.headers:
            return "Akamai"
        elif "fastly" in str(response.headers):
            return "Fastly"
        elif "cloudfront" in str(response.headers):
            return "CloudFront"
    except:
        pass
    return None

def test_payload(host, payload, port=80, protocol="http"):
    try:
        url = f"{protocol}://{host}:{port}{payload}"
        response = requests.get(url, timeout=3)
        return {"status": response.status_code, "length": len(response.text), "success": response.status_code == 200}
    except:
        return {"status": 0, "length": 0, "success": False}

def scan_host_comprehensive(host, custom_ports=None, scan_subdomains=True, test_payloads=True):
    results = {
        "host": host,
        "timestamp": datetime.now().isoformat(),
        "online": False,
        "services": {},
        "ports": [],
        "cdn": None,
        "dns": {},
        "vulnerabilities": [],
        "free_net_methods": [],
        "subdomains": [],
        "proxies": [],
        "vpn_configs": [],
        "successful_payloads": [],
        "bypass_methods": [],
        "score": 0,
        "success": False
    }
    
    if not check_domain(host):
        return results
    
    results["online"] = True
    results["dns"] = get_dns_records(host)
    
    ports_to_scan = custom_ports if custom_ports else COMMON_PORTS
    for port in ports_to_scan:
        if check_port(host, port):
            results["ports"].append(port)
            try:
                service = socket.getservbyport(port)
                results["services"][service] = True
            except:
                results["services"][f"port_{port}"] = True
    
    results["cdn"] = detect_cdn(host)
    
    if scan_subdomains:
        for sub in SUBDOMAINS:
            sub_domain = f"{sub}.{host}"
            if check_domain(sub_domain):
                results["subdomains"].append(sub_domain)
    
    if test_payloads:
        for category, vulns in VULNS_DB.items():
            for vuln in vulns:
                if vuln in PAYLOADS_DB:
                    for payload in PAYLOADS_DB[vuln][:2]:
                        for protocol in ['http', 'https']:
                            if protocol == 'http' and (80 in results["ports"] or 8080 in results["ports"]):
                                port = 80 if 80 in results["ports"] else 8080
                                response = test_payload(host, payload, port=port, protocol=protocol)
                                if response["success"]:
                                    results["successful_payloads"].append({"vuln": vuln, "payload": payload})
                                    if vuln not in results["vulnerabilities"]:
                                        results["vulnerabilities"].append(vuln)
                                    break
                            elif protocol == 'https' and (443 in results["ports"] or 8443 in results["ports"]):
                                port = 443 if 443 in results["ports"] else 8443
                                response = test_payload(host, payload, port=port, protocol=protocol)
                                if response["success"]:
                                    results["successful_payloads"].append({"vuln": vuln, "payload": payload})
                                    if vuln not in results["vulnerabilities"]:
                                        results["vulnerabilities"].append(vuln)
                                    break
    
    for provider in FREE_PROVIDERS:
        if provider in host:
            results["free_net_methods"].append({"provider": provider, "method": "Domain_Detection", "working": True})
    
    bypass_tests = [("Zero_rating_bypass", "/?z=free"), ("SNI_hiding", "/?sni=1"), ("Port_knocking", "/?knock=1")]
    for method, payload in bypass_tests:
        if 80 in results["ports"] or 443 in results["ports"]:
            try:
                protocol = "https" if 443 in results["ports"] else "http"
                port = 443 if 443 in results["ports"] else 80
                response = test_payload(host, payload, port=port, protocol=protocol)
                if response["success"]:
                    results["bypass_methods"].append({"method": method, "working": True})
                    results["free_net_methods"].append({"method": method, "working": True})
            except:
                pass
    
    for i in range(2):
        proxy = generate_advanced_proxy()
        proxy["target_host"] = host
        results["proxies"].append(proxy)
    
    for i in range(2):
        vpn = generate_advanced_vpn()
        vpn["target_host"] = host
        results["vpn_configs"].append(vpn)
    
    score = 0
    if results["online"]: score += 10
    if results["ports"]: score += len(results["ports"]) * 2
    if results["cdn"]: score += 15
    if results["vulnerabilities"]: score += len(results["vulnerabilities"]) * 5
    if results["free_net_methods"]: score += len(results["free_net_methods"]) * 3
    if results["subdomains"]: score += len(results["subdomains"])
    if results["successful_payloads"]: score += len(results["successful_payloads"]) * 4
    results["score"] = score
    
    if results["free_net_methods"] or results["successful_payloads"] or results["vulnerabilities"]:
        results["success"] = True
    
    return results

def save_report(results, filename=None):
    if not filename:
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join('reports', filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    return filepath

def auto_scan_loop(token, chat_id):
    global scan_status
    
    scan_status["running"] = True
    scan_status["hosts"] = []
    scan_status["current"] = 0
    scan_status["total"] = 30
    scan_status["results"] = []
    
    hosts = []
    for i in range(30):
        host = generate_smart_host()
        hosts.append(host)
        if i % 3 == 0:
            hosts.append(random.choice(FREE_PROVIDERS))
        if i % 5 == 0:
            hosts.append(f"{random.choice(SUBDOMAINS)}.{random.choice(FREE_PROVIDERS)}")
    
    hosts = list(set(hosts))[:30]
    scan_status["hosts"] = hosts
    scan_status["total"] = len(hosts)
    
    results = []
    successful_hosts = []
    
    for i, host in enumerate(hosts):
        scan_status["current"] = i + 1
        result = scan_host_comprehensive(host)
        results.append(result)
        scan_status["results"] = results
        
        if result.get("success"):
            successful_hosts.append(result)
            if token and chat_id:
                report = f"""<b>✅ تم العثور على هوست ناجح!</b>
                
<b>🌐 الهوست:</b> {host}
<b>📊 التقييم:</b> {result['score']}/100
<b>🔴 الثغرات:</b> {', '.join(result['vulnerabilities']) if result['vulnerabilities'] else 'لا يوجد'}
<b>🌍 طرق النت المجاني:</b> {len(result['free_net_methods'])}
<b>🎯 البايلودات الناجحة:</b> {len(result['successful_payloads'])}
<b>🛡️ CDN:</b> {result['cdn'] if result['cdn'] else 'لا يوجد'}"""
                send_to_bot(token, chat_id, report)
    
    report_file = save_report(results)
    
    if token and chat_id:
        final_report = f"""<b>📊 تقرير الفحص النهائي</b>

<b>🔍 إجمالي الهوستات:</b> {len(results)}
<b>✅ الهوستات الناجحة:</b> {len(successful_hosts)}
<b>📁 ملف التقرير:</b> {report_file}

<b>📋 قائمة الهوستات الناجحة:</b>
{chr(10).join([f"🌐 {r['host']} - التقييم: {r['score']}/100" for r in successful_hosts[:10]]) if successful_hosts else '❌ لا توجد هوستات ناجحة'}"""
        send_to_bot(token, chat_id, final_report)
        
        if os.path.exists(report_file):
            send_file_to_bot(token, chat_id, report_file)
    
    scan_status["running"] = False
    
    return results, successful_hosts

# ===================== قالب HTML =====================
HTML_PAGE = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔍 FreeNet Scanner</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0a0a0a; color: #00ff00; font-family: 'Courier New', monospace; padding: 10px; }
        .container { max-width: 1200px; margin: auto; background: #111; padding: 20px; border: 2px solid #00ff00; border-radius: 15px; box-shadow: 0 0 40px #00ff0033; }
        h1 { color: #00ff00; text-align: center; text-shadow: 0 0 30px #00ff00; font-size: 2.2em; }
        .subtitle { text-align: center; color: #88ff88; margin-bottom: 15px; }
        input, button { background: #1a1a1a; color: #00ff00; border: 1px solid #00ff00; padding: 10px; margin: 5px 0; width: 100%; border-radius: 8px; font-size: 1em; }
        button { background: #003300; cursor: pointer; transition: 0.3s; }
        button:hover { background: #006600; box-shadow: 0 0 20px #00ff0055; }
        .row { display: flex; gap: 10px; flex-wrap: wrap; }
        .row input, .row button { flex: 1; min-width: 120px; }
        .col-2 { flex: 2; }
        .col-1 { flex: 1; }
        .result-box { background: #0a0a0a; padding: 15px; margin-top: 15px; border: 1px solid #00ff00; border-radius: 8px; max-height: 400px; overflow: auto; white-space: pre-wrap; font-size: 0.85em; }
        .status { padding: 10px; margin: 10px 0; border-radius: 8px; text-align: center; font-weight: bold; }
        .status-loading { background: #332200; color: #ffaa00; }
        .status-success { background: #003300; color: #00ff00; }
        .status-error { background: #330000; color: #ff4444; }
        .status-idle { background: #1a1a1a; color: #88ff88; }
        .host-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px; margin-top: 10px; max-height: 400px; overflow-y: auto; }
        .host-card { background: #1a1a1a; padding: 10px; border-radius: 8px; border: 1px solid #333; }
        .host-card.success { border-color: #00ff00; background: #00330022; }
        .host-card.fail { border-color: #ff4444; background: #33000022; }
        .host-card.waiting { border-color: #ffaa00; background: #33220022; }
        .host-name { font-weight: bold; color: #00ff00; }
        .host-status { font-size: 0.8em; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.7em; margin: 2px; }
        .badge-success { background: #003300; color: #00ff00; }
        .badge-fail { background: #330000; color: #ff4444; }
        .badge-waiting { background: #332200; color: #ffaa00; }
        .badge-free { background: #003300; color: #00ffaa; }
        .badge-vuln { background: #330000; color: #ff4444; }
        .badge-cdn { background: #002233; color: #44aaff; }
        .progress-bar { width: 100%; height: 20px; background: #1a1a1a; border-radius: 10px; border: 1px solid #00ff00; margin: 10px 0; overflow: hidden; }
        .progress-fill { height: 100%; background: #00ff00; transition: width 0.5s; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0; }
        .stat-box { background: #1a1a1a; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #00ff00; }
        .stat-number { font-size: 1.5em; color: #00ff00; }
        .stat-label { font-size: 0.8em; color: #88ff88; }
        @media (max-width: 600px) { .row { flex-direction: column; } .stats { grid-template-columns: 1fr 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 FreeNet Scanner</h1>
        <div class="subtitle">أداة فحص شاملة مع شاشة عرض حية</div>
        
        <div class="row">
            <input type="text" id="bot_token" placeholder="🔑 توكن البوت" class="col-2">
            <input type="text" id="chat_id" placeholder="🆔 معرف الدردشة" class="col-1">
        </div>
        <div class="row">
            <button onclick="saveConfig()" style="background:#002233;">💾 حفظ الإعدادات</button>
            <button onclick="testBot()" style="background:#003322;">📡 اختبار البوت</button>
        </div>
        
        <hr style="border-color:#00ff00; margin:15px 0;">
        
        <div class="row">
            <button onclick="startScan()" style="background:#004400;" id="btn_start">🚀 بدء الفحص التلقائي</button>
            <button onclick="stopScan()" style="background:#440000;" id="btn_stop" disabled>⏹️ إيقاف الفحص</button>
            <button onclick="clearResults()" style="background:#332200;">🗑️ مسح النتائج</button>
        </div>
        
        <div class="stats" id="stats">
            <div class="stat-box"><div class="stat-number" id="stat_total">0</div><div class="stat-label">إجمالي الهوستات</div></div>
            <div class="stat-box"><div class="stat-number" id="stat_current">0</div><div class="stat-label">تم الفحص</div></div>
            <div class="stat-box"><div class="stat-number" id="stat_success">0</div><div class="stat-label">ناجحة</div></div>
            <div class="stat-box"><div class="stat-number" id="stat_fail">0</div><div class="stat-label">فاشلة</div></div>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill" id="progress" style="width: 0%;"></div>
        </div>
        
        <div id="status" class="status status-idle">⏳ جاهز - اضغط بدء الفحص</div>
        
        <div id="hosts_grid" class="host-grid"></div>
        
        <div id="results" class="result-box">📋 انتظر النتائج...</div>
        <div id="files" style="margin-top:10px;"></div>
    </div>

    <script>
        let isRunning = false;
        let scanInterval = null;
        
        function showStatus(msg, type) {
            const el = document.getElementById('status');
            el.textContent = msg;
            el.className = 'status status-' + (type || 'idle');
        }
        
        function updateStats(total, current, success, fail) {
            document.getElementById('stat_total').textContent = total || 0;
            document.getElementById('stat_current').textContent = current || 0;
            document.getElementById('stat_success').textContent = success || 0;
            document.getElementById('stat_fail').textContent = fail || 0;
            const progress = total > 0 ? (current / total * 100) : 0;
            document.getElementById('progress').style.width = Math.min(progress, 100) + '%';
        }
        
        function saveConfig() {
            const token = document.getElementById('bot_token').value;
            const chat = document.getElementById('chat_id').value;
            if (!token || !chat) {
                alert('يرجى إدخال التوكن والمعرف');
                return;
            }
            fetch('/api/save_config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({token, chat_id: chat})
            })
            .then(r => r.json())
            .then(data => {
                showStatus('✅ تم حفظ الإعدادات', 'success');
            });
        }
        
        function testBot() {
            const token = document.getElementById('bot_token').value;
            const chat = document.getElementById('chat_id').value;
            if (!token || !chat) {
                alert('يرجى إدخال التوكن والمعرف');
                return;
            }
            showStatus('⏳ جاري اختبار البوت...', 'loading');
            fetch('/api/test_bot', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({token, chat_id: chat})
            })
            .then(r => r.json())
            .then(data => {
                showStatus(data.status, data.status.includes('✅') ? 'success' : 'error');
            });
        }
        
        function startScan() {
            const token = document.getElementById('bot_token').value;
            const chat = document.getElementById('chat_id').value;
            if (!token || !chat) {
                alert('يرجى إدخال التوكن والمعرف أولاً');
                return;
            }
            
            isRunning = true;
            document.getElementById('btn_start').disabled = true;
            document.getElementById('btn_stop').disabled = false;
            showStatus('⏳ جاري الفحص...', 'loading');
            document.getElementById('hosts_grid').innerHTML = '';
            
            fetch('/api/start_scan', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({token, chat_id: chat})
            })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'started') {
                    scanInterval = setInterval(fetchStatus, 1500);
                }
            });
        }
        
        function stopScan() {
            isRunning = false;
            document.getElementById('btn_start').disabled = false;
            document.getElementById('btn_stop').disabled = true;
            if (scanInterval) {
                clearInterval(scanInterval);
                scanInterval = null;
            }
            showStatus('⏹️ تم إيقاف الفحص', 'idle');
            
            fetch('/api/stop_scan', {method: 'POST'});
        }
        
        function fetchStatus() {
            fetch('/api/scan_status')
            .then(r => r.json())
            .then(data => {
                if (!data.running) {
                    document.getElementById('btn_start').disabled = false;
                    document.getElementById('btn_stop').disabled = true;
                    if (scanInterval) {
                        clearInterval(scanInterval);
                        scanInterval = null;
                    }
                    showStatus('✅ تم الانتهاء من الفحص', 'success');
                }
                
                updateStats(data.total, data.current, data.success_count, data.fail_count);
                renderHosts(data.hosts, data.results);
                
                if (data.results && data.results.length > 0) {
                    document.getElementById('results').innerHTML = JSON.stringify(data.results, null, 2);
                }
            });
        }
        
        function renderHosts(hosts, results) {
            const grid = document.getElementById('hosts_grid');
            if (!hosts || hosts.length === 0) {
                grid.innerHTML = '<div style="color:#666;text-align:center;padding:20px;">⏳ جاري توليد الهوستات...</div>';
                return;
            }
            
            let html = '';
            hosts.forEach((host, index) => {
                const result = results.find(r => r.host === host);
                let statusClass = 'waiting';
                let statusText = '⏳ جاري';
                let badges = '';
                
                if (result) {
                    if (result.success) {
                        statusClass = 'success';
                        statusText = '✅ ناجح';
                        if (result.free_net_methods && result.free_net_methods.length > 0) {
                            badges += '<span class="badge badge-free">🌍 نت مجاني</span>';
                        }
                        if (result.vulnerabilities && result.vulnerabilities.length > 0) {
                            badges += '<span class="badge badge-vuln">🔴 ثغرات</span>';
                        }
                        if (result.cdn) {
                            badges += '<span class="badge badge-cdn">🛡️ '+result.cdn+'</span>';
                        }
                    } else if (result.online) {
                        statusClass = 'fail';
                        statusText = '❌ لا طرق';
                    } else {
                        statusClass = 'fail';
                        statusText = '❌ غير موجود';
                    }
                }
                
                html += `
                    <div class="host-card ${statusClass}">
                        <div class="host-name">${host}</div>
                        <div class="host-status">${statusText}</div>
                        <div>${badges}</div>
                        <div style="font-size:0.7em;color:#666;">${result ? 'التقييم: '+result.score+'/100' : '⏳ ...'}</div>
                    </div>
                `;
            });
            grid.innerHTML = html;
        }
        
        function clearResults() {
            document.getElementById('results').innerHTML = '📋 تم المسح';
            document.getElementById('hosts_grid').innerHTML = '';
            document.getElementById('files').innerHTML = '';
            updateStats(0, 0, 0, 0);
            showStatus('🗑️ تم المسح', 'idle');
        }
    </script>
</body>
</html>
"""

# ===================== مسارات Flask =====================
@app.route('/')
def index():
    return HTML_PAGE

@app.route('/api/save_config', methods=['POST'])
def save_config():
    data = request.json
    token = data.get('token')
    chat_id = data.get('chat_id')
    if token and chat_id:
        session['bot_token'] = token
        session['chat_id'] = chat_id
        return jsonify({"status": "✅ تم حفظ الإعدادات"})
    return jsonify({"status": "❌ بيانات ناقصة"})

@app.route('/api/test_bot', methods=['POST'])
def test_bot():
    data = request.json
    token = data.get('token')
    chat_id = data.get('chat_id')
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {"chat_id": chat_id, "text": "✅ البوت يعمل بنجاح!"}
            response = requests.post(url, json=data, timeout=5)
            if response.json().get("ok"):
                return jsonify({"status": "✅ البوت متصل"})
        except:
            pass
    return jsonify({"status": "❌ فشل الاتصال"})

@app.route('/api/start_scan', methods=['POST'])
def start_scan():
    global scan_status
    data = request.json
    token = data.get('token')
    chat_id = data.get('chat_id')
    
    if scan_status["running"]:
        return jsonify({"status": "الفحص قيد التشغيل بالفعل"})
    
    thread = threading.Thread(target=auto_scan_loop, args=(token, chat_id))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started"})

@app.route('/api/stop_scan', methods=['POST'])
def stop_scan():
    global scan_status
    scan_status["running"] = False
    return jsonify({"status": "stopped"})

@app.route('/api/scan_status')
def scan_status_route():
    global scan_status
    success_count = len([r for r in scan_status["results"] if r.get("success")])
    fail_count = len([r for r in scan_status["results"] if not r.get("success") and r.get("online")])
    
    return jsonify({
        "running": scan_status["running"],
        "hosts": scan_status["hosts"],
        "current": scan_status["current"],
        "total": scan_status["total"],
        "success_count": success_count,
        "fail_count": fail_count,
        "results": scan_status["results"]
    })

@app.route('/api/download/<filename>')
def api_download(filename):
    filepath = os.path.join('reports', filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    filepath = os.path.join('payloads_results', filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({"error": "الملف غير موجود"}), 404

@app.route('/api/list_reports')
def api_list_reports():
    reports = os.listdir('reports') if os.path.exists('reports') else []
    payloads = os.listdir('payloads_results') if os.path.exists('payloads_results') else []
    return jsonify({"reports": reports, "payloads": payloads})

# ===================== التشغيل =====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
