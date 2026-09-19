# run.py - زرّك القديم بقى لحظي تلقائيا + فويس + مكالمات + رد (نسخة محمية)
import run.py as FBI
app = FBI.app
db = FBI.db

from flask_socketio import SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
import os, base64, uuid, html, time, re
from collections import defaultdict
os.makedirs('static/voices', exist_ok=True)

# ================== إضافات حماية فقط - ما بتغير شغلك ==================
# 1. قفل سحب الجلسة نهائي
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# 2. مانع سبام + سحب جلسة
msg_times = defaultdict(list)
def is_spamming(uid):
    now = time.time()
    msg_times[uid] = [t for t in msg_times[uid] if now - t < 4]
    if len(msg_times[uid]) > 5: return True
    msg_times[uid].append(now)
    return False

def safe_body_extra(t):
    t = str(t)
    # يمنع محاولات حقن تسحب الجلسة
    if re.search(r'document\.cookie|localStorage|sessionStorage|fetch\s*\(\s*["\']http|eval\s*\(|atob\s*\(', t, re.I):
        return "[محتوى محظور]"
    return t
# ================== نهاية إضافات الحماية ==================

def get_room(a,b):
    p=str(b)
    if p.startswith('g'): return f"group_{p}"
    try: return f"c_{min(int(a),int(p))}_{max(int(a),int(p))}"
    except: return f"c_{a}_{p}"

def safe_name(t): return html.escape(str(t)[:30])
from flask_login import current_user

CHAT_ADDON = """
<style>
#liveStatus{padding:6px 15px;height:26px;display:flex;align-items:center;gap:8px;font-size:13px;background:#111b21;position:fixed;bottom:62px;left:0;right:0;z-index:1000}
.icon-glow{width:18px;height:18px;filter:drop-shadow(0 0 6px currentColor) drop-shadow(0 0 12px currentColor);animation:glowPulse 1.2s infinite}
@keyframes glowPulse{50%{filter:drop-shadow(0 0 10px currentColor) drop-shadow(0 0 20px currentColor)}}
#vbox{position:fixed;inset:0;background:#000;display:none;z-index:9999}
#vbox video{width:100%;height:100%;object-fit:cover}
#local{width:140px;position:absolute;bottom:20px;right:20px;border-radius:12px;border:2px solid #00a884}
#voiceBar{display:flex;gap:8px;padding:8px;background:#202c33;position:fixed;bottom:0;left:0;right:0;z-index:1001;align-items:center}
.b{width:46px;height:46px;border-radius:50%;border:none;color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center}
#micBtn{background:#00a884;box-shadow:0 0 12px #00a884} #micBtn.rec{background:#ff3b30;box-shadow:0 0 12px #ff3b30;animation:pulse 1s infinite}
@keyframes pulse{50%{box-shadow:0 0 30px #ff3b30}}
.callBtn{background:#54656f}
#recT{display:none;color:#ff3b30;text-shadow:0 0 8px #ff3b30}
.reply{font-size:11px;background:rgba(0,0,0,0.4);border-right:3px solid #00a884;padding:5px 8px;margin-bottom:6px;border-radius:8px;cursor:pointer}
.m.hl{outline:2px solid #00a884;box-shadow:0 0 15px #00a884}
#replyBar{display:none;background:#182229;padding:8px 12px;border-right:4px solid #00a884;justify-content:space-between;position:fixed;bottom:62px;left:0;right:0;z-index:1002;align-items:center}
#msgContainer{padding-bottom:120px}
</style>
<div id="liveStatus"></div>
<div id="replyBar"><div id="replyText" style="font-size:12px;color:#ccc"></div><button onclick="cancelReply()" style="background:none;border:none;color:#fff;font-size:18px">X</button></div>
<div id="vbox"><video id="remote" autoplay playsinline></video><video id="local" autoplay muted playsinline></video><button onclick="endCall()" style="position:absolute;top:20px;left:20px;background:#ff3b30;border:none;padding:10px 20px;border-radius:20px;color:#fff">انهاء</button></div>
<div id="voiceBar">
<button id="micBtn" class="b" onclick="toggleVoice()">🎤</button><span id="recT">00:00 ●</span>
<button class="b callBtn" onclick="startCall('audio')">📞</button>
<button class="b callBtn" onclick="startCall('video')">🎥</button>
<span style="color:#888;font-size:12px;margin-right:auto">دوس رسالة للرد عليها</span>
</div>
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
<script>
const peerId = new URLSearchParams(location.search).get('id')||"2";
const sock = io(); sock.emit('join',{peer:peerId});
const statusEl = document.getElementById('liveStatus');
const ICONS={
typing:`<svg class="icon-glow" style="color:#00a884" viewBox="0 0 24 24" fill="currentColor"><circle cx="4" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="20" cy="12" r="2"/></svg>`,
mic:`<svg class="icon-glow" style="color:#ff3b30" viewBox="0 0 24 24" fill="currentColor"><path d="M12 14a3 3 0 003-3V5a3 3 0 00-6 0v6a3 3 0 003 3z"/></svg>`,
call:`<svg class="icon-glow" style="color:#2979ff" viewBox="0 0 24 24" fill="currentColor"><path d="M6.6 10.8a15.1 15.1 0 006.6 6.6l2.2-2.2a1 1 0 011-.25 11 11 0 003.5.56 1 1 0 011 1v3.5a1 1 0 01-1 1A19 19 0 013 4a1 1 0 011-1h3.5a1 1 0 011 1c0 1.2.19 2.4.56 3.5a1 1 0 01-.25 1L6.6 10.8z"/></svg>`
};
let replyId=null,replyBody=null;
function esc(t){const d=document.createElement('div'); d.textContent=t; return d.innerHTML;}
function goTo(id){const el=document.getElementById('msg-'+id); if(el){el.scrollIntoView({behavior:'smooth',block:'center'}); el.classList.add('hl'); setTimeout(()=>el.classList.remove('hl'),1500);}}
function setReply(id,body){replyId=id; replyBody=body; document.getElementById('replyBar').style.display='flex'; document.getElementById('replyText').textContent='رد على: '+body.substring(0,30);}
function cancelReply(){replyId=null; replyBody=null; document.getElementById('replyBar').style.display='none';}
function findOldInput(){
  return document.querySelector('input[name="message"], input[name="body"], input[name="text"], #messageInput, #msg, textarea[name="message"], input[type="text"]');
}
function findOldBtn(){
  return document.querySelector('button[type="submit"], form button, #sendBtn,.send-btn');
}
function hookOldChat(){
  const oldInp = findOldInput();
  const oldBtn = findOldBtn();
  const oldForm = document.querySelector('form');
  if(!oldInp) return;
  oldInp.addEventListener('input',()=>{sock.emit('typing',{peer:peerId}); clearTimeout(window._tOut); window._tOut=setTimeout(()=>sock.emit('stop_typing',{peer:peerId}),1200);});
  const sendNow = (e)=>{
    if(e) e.preventDefault();
    const txt = oldInp.value.trim();
    if(!txt) return;
    sock.emit('chat_msg',{peer:peerId,body:txt,reply_to_id:replyId,reply_body:replyBody});
    oldInp.value=''; cancelReply(); sock.emit('stop_typing',{peer:peerId});
  };
  if(oldForm) oldForm.addEventListener('submit', sendNow);
  if(oldBtn) oldBtn.addEventListener('click', sendNow);
  oldInp.addEventListener('keydown', (e)=>{if(e.key==='Enter' &&!e.shiftKey){e.preventDefault(); sendNow();}});
}
setTimeout(hookOldChat, 800);
setTimeout(hookOldChat, 2000);
sock.on('show_typing',d=>{statusEl.innerHTML=`${ICONS.typing} <span style="color:#00a884;text-shadow:0 0 8px #00a884">${esc(d.name)} يكتب الآن...</span>`;});
sock.on('hide_typing',()=>{statusEl.innerHTML='';});
sock.on('show_recording',d=>{statusEl.innerHTML=`${ICONS.mic} <span style="color:#ff3b30;text-shadow:0 0 8px #ff3b30">${esc(d.name)} يسجل مقطع صوتي...</span>`;});
sock.on('hide_recording',()=>{statusEl.innerHTML='';});
sock.on('show_calling',d=>{statusEl.innerHTML=`${ICONS.call} <span style="color:#2979ff;text-shadow:0 0 8px #2979ff">${esc(d.name)} يتصل بك ${d.type==='video'?'فيديو':'صوتيا'}...</span>`;});
sock.on('hide_calling',()=>{statusEl.innerHTML='';});
sock.on('new_msg',d=>{
  const box=document.getElementById('messages')||document.body;
  if(!document.getElementById('msgContainer')){const c=document.createElement('div'); c.id='msgContainer'; box.appendChild(c);}
  const container=document.getElementById('msgContainer');
  const div=document.createElement('div'); div.id='msg-'+d.mid; div.className='m'; div.style.cssText='background:#202c33;padding:10px 14px;border-radius:18px;margin:6px;max-width:70%;cursor:pointer;word-break:break-word';
  if(d.reply_body){
    const r=document.createElement('div'); r.className='reply'; r.textContent='↩ '+d.reply_body; r.onclick=(e)=>{e.stopPropagation(); goTo(d.reply_to_id);}; div.appendChild(r);
  }
  if(d.audio) div.innerHTML+=`<b>${esc(d.name)}:</b><br><audio controls src="${d.audio}"></audio>`;
  else div.innerHTML+=`<b>${esc(d.name)}:</b> ${esc(d.body)}`;
  div.addEventListener('click',()=>{if(!d.reply_body) setReply(d.mid, d.body||'[صوت]');});
  div.addEventListener('dblclick',()=>{if(d.reply_body) goTo(d.reply_to_id);});
  container.appendChild(div); window.scrollTo(0,document.body.scrollHeight);
});
let rec,ch=[],isRec=false,tI,s=0;
async function toggleVoice(){
  const b=document.getElementById('micBtn'),t=document.getElementById('recT');
  if(!isRec){
    const st=await navigator.mediaDevices.getUserMedia({audio:true});
    rec=new MediaRecorder(st); ch=[]; s=0;
    rec.ondataavailable=e=>ch.push(e.data);
    rec.onstop=()=>{const bl=new Blob(ch,{type:'audio/webm'}); const r=new FileReader(); r.readAsDataURL(bl); r.onloadend=()=>sock.emit('voice',{peer:peerId,audio:r.result,reply_to_id:replyId,reply_body:replyBody}); cancelReply(); t.style.display='none'; b.classList.remove('rec'); sock.emit('stop_recording',{peer:peerId});};
    rec.start(); isRec=true; b.classList.add('rec'); t.style.display='inline'; sock.emit('start_recording',{peer:peerId});
    tI=setInterval(()=>{s++; t.textContent=`0${Math.floor(s/60)}:${String(s%60).padStart(2,'0')} ● تسجيل`;},1000);
  }else{clearInterval(tI); rec.stop(); isRec=false;}
}
let pc,ls; const cfg={iceServers:[{urls:"stun:stun.l.google.com:19302"}]};
const HD={audio:true,video:{width:{ideal:1920},height:{ideal:1080},frameRate:{ideal:30}}};
async function startCall(type){
  document.getElementById('vbox').style.display='block';
  sock.emit('start_calling',{peer:peerId,type:type});
  ls=await navigator.mediaDevices.getUserMedia(type==='video'?HD:{audio:true});
  document.getElementById('local').srcObject=ls; pc=new RTCPeerConnection(cfg);
  ls.getTracks().forEach(x=>pc.addTrack(x,ls)); pc.ontrack=e=>document.getElementById('remote').srcObject=e.streams[0];
  pc.onicecandidate=e=>{if(e.candidate)sock.emit('ice',{peer:peerId,cand:e.candidate})};
  const o=await pc.createOffer(); await pc.setLocalDescription(o); sock.emit('call',{peer:peerId,offer:o,type:type});
}
sock.on('incall',async d=>{if(!confirm(d.name+' يتصل بك '+d.type))return; document.getElementById('vbox').style.display='block'; ls=await navigator.mediaDevices.getUserMedia(d.type==='video'?HD:{audio:true}); document.getElementById('local').srcObject=ls; pc=new RTCPeerConnection(cfg); ls.getTracks().forEach(x=>pc.addTrack(x,ls)); pc.ontrack=e=>document.getElementById('remote').srcObject=e.streams[0]; pc.onicecandidate=e=>{if(e.candidate)sock.emit('ice',{peer:d.from,cand:e.candidate})}; await pc.setRemoteDescription(d.offer); const a=await pc.createAnswer(); await pc.setLocalDescription(a); sock.emit('ans',{peer:d.from,ans:a}); statusEl.innerHTML='';});
sock.on('answered',async d=>{await pc.setRemoteDescription(d.ans); statusEl.innerHTML='';});
sock.on('ice',async d=>{try{await pc.addIceCandidate(d.cand)}catch{}});
function endCall(){if(pc)pc.close(); if(ls)ls.getTracks().forEach(t=>t.stop()); document.getElementById('vbox').style.display='none'; sock.emit('end',{peer:peerId}); statusEl.innerHTML=''; sock.emit('stop_calling',{peer:peerId});}
sock.on('ended',endCall);
</script>
"""

@FBI.app.after_request
def inject(response):
    # حماية إضافية بدون ما نمسح حقنك
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.socket.io; connect-src 'self' wss: ws: https://cdn.socket.io; media-src 'self' blob:; object-src 'none'"
    if response.content_type and 'text/html' in response.content_type:
        try:
            data=response.get_data(as_text=True)
            if '</body>' in data and 'liveStatus' not in data:
                data=data.replace('</body>', CHAT_ADDON + '</body>')
                response.set_data(data)
        except: pass
    return response

@socketio.on('join')
def j(d):
    from flask_socketio import join_room
    if current_user.is_authenticated:
        join_room(get_room(current_user.id, d['peer']))

@socketio.on('chat_msg')
def chat_msg(d):
    if not current_user.is_authenticated: return
    if is_spamming(current_user.id): return
    body=html.escape(safe_body_extra(str(d.get('body',''))[:500]))
    if not body: return
    reply_body=html.escape(safe_body_extra(str(d.get('reply_body',''))[:100])) if d.get('reply_body') else None
    mid=int(time.time()*1000)
    from flask_socketio import emit
    emit('new_msg',{'mid':mid,'body':body,'name':safe_name(current_user.username),'s':current_user.id,'reply_to_id':d.get('reply_to_id'),'reply_body':reply_body}, to=get_room(current_user.id, d['peer']))

@socketio.on('voice')
def voice(d):
    if not current_user.is_authenticated: return
    if is_spamming(current_user.id): return
    try:
        raw = str(d.get('audio',''))
        if ',' not in raw: return
        header, b64 = raw.split(',',1)
        if 'audio' not in header and 'webm' not in header and 'ogg' not in header: return
        if len(b64)>6000000: return
        decoded = base64.b64decode(b64)
        # حماية رفع ملغوم
        if b'<?php' in decoded or b'<script' in decoded[:200].lower():
            print(f"🚨 محاولة رفع خبيث من {current_user.id}")
            return
        fn=f"{uuid.uuid4().hex}.webm"; p=os.path.join('static/voices',fn)
        with open(p,'wb') as f: f.write(decoded)
        from flask_socketio import emit
        mid=int(time.time()*1000)
        reply_body=html.escape(safe_body_extra(str(d.get('reply_body',''))[:100])) if d.get('reply_body') else None
        emit('new_msg',{'mid':mid,'audio':f"/{p}",'name':safe_name(current_user.username),'reply_to_id':d.get('reply_to_id'),'reply_body':reply_body}, to=get_room(current_user.id, d['peer']))
    except: pass

@socketio.on('typing')
def t(d):
    from flask_socketio import emit
    if not current_user.is_authenticated: return
    emit('show_typing',{'name':safe_name(current_user.username)}, to=get_room(current_user.id,d['peer']), include_self=False)
@socketio.on('stop_typing')
def st(d):
    from flask_socketio import emit
    if not current_user.is_authenticated: return
    emit('hide_typing',{}, to=get_room(current_user.id,d['peer']), include_self=False)
@socketio.on('start_recording')
def sr(d):
    from flask_socketio import emit
    if not current_user.is_authenticated: return
    emit('show_recording',{'name':safe_name(current_user.username)}, to=get_room(current_user.id,d['peer']), include_self=False)
@socketio.on('stop_recording')
def strp(d):
    from flask_socketio import emit
    if not current_user.is_authenticated: return
    emit('hide_recording',{}, to=get_room(current_user.id,d['peer']), include_self=False)
@socketio.on('start_calling')
def sc(d):
    from flask_socketio import emit
    if not current_user.is_authenticated: return
    emit('show_calling',{'name':safe_name(current_user.username),'type':d.get('type','audio')}, to=get_room(current_user.id,d['peer']), include_self=False)
@socketio.on('stop_calling')
def ssc(d):
    from flask_socketio import emit
    if not current_user.is_authenticated: return
    emit('hide_calling',{}, to=get_room(current_user.id,d['peer']), include_self=False)

@socketio.on('call')
def call(d):
    from flask_socketio import emit
    if not current_user.is_authenticated: return
    if str(d.get('peer')) == str(current_user.id): return
    emit('incall',{'from':current_user.id,'name':safe_name(current_user.username),'offer':d['offer'],'type':d['type']}, to=get_room(current_user.id,d['peer']), include_self=False)
@socketio.on('ans')
def ans(d):
    from flask_socketio import emit
    if not current_user.is_authenticated: return
    emit('answered',{'ans':d['ans']}, to=get_room(current_user.id,d['peer']), include_self=False)
@socketio.on('ice')
def ice(d):
    from flask_socketio import emit
    if not current_user.is_authenticated: return
    emit('ice',{'cand':d['cand']}, to=get_room(current_user.id,d['peer']), include_self=False)
@socketio.on('end')
def end(d):
    from flask_socketio import emit
    if not current_user.is_authenticated: return
    emit('ended',{}, to=get_room(current_user.id,d['peer']))
    emit('hide_calling',{}, to=get_room(current_user.id,d['peer']))

if __name__=='__main__':
    with app.app_context(): db.create_all()
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
