import os
import re
import html
import base64
import random
import string
import json
import time
import requests
import telebot
import threading
import http.server
import socketserver
from telebot import types
from datetime import datetime
from urllib.parse import urlparse
import yt_dlp

# =========================================================
# 👑 BOT & ADMIN CONFIGURATION
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8821190665:AAGgPfdnwH1sV0z-phgHfs_0r4_kJKGyk6s")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 6753121703))
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "Rafsanvai0")
BOT_USERNAME = "@RAFSAN_SUPPORT_BOT"
PORT = int(os.environ.get("PORT", 8080))

# 📢 মাস্ট-জয়েন চ্যানেল/গ্রুপ কনফিগারেশন
FORCE_SUB_CHANNEL = "@c8danM8eKttmN2I1"
FORCE_SUB_URL = "https://t.me/+c8danM8eKttmN2I1"

# টেলিগ্রাম হাই-টাইমআউট অপ্টিমাইজেশন
telebot.apihelper.READ_TIMEOUT = 180
telebot.apihelper.CONNECT_TIMEOUT = 60

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None, threaded=True)
USERS_FILE = "users.json"
BANNED_FILE = "banned.json"

user_states = {}

# =========================================================
# 🌐 CRASH-PROOF KEEP-ALIVE WEB SERVER (24/7 ONLINE)
# =========================================================

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def run_keep_alive_server():
    class KeepAliveHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            status_page = (
                "<html><head><title>MAHDE VIP Ultra Bot Status</title></head>"
                "<body style='font-family:sans-serif;text-align:center;padding-top:60px;background:#0b0e14;color:#58a6ff;'>"
                "<h1>⚡ MAHDE VIP ULTRA CIPHER ENGINE ⚡</h1>"
                "<p style='color:#3fb950;font-size:18px;'>🟢 System Status: Active &amp; Online 24/7</p>"
                f"<p style='color:#8b949e;'>Owner &amp; Developer: @{ADMIN_USERNAME} | Bot: {BOT_USERNAME}</p>"
                "</body></html>"
            )
            self.wfile.write(status_page.encode("utf-8"))

        def log_message(self, format, *args):
            pass

    while True:
        try:
            with ReusableTCPServer(("", PORT), KeepAliveHandler) as httpd:
                print(f"🌐 24/7 Keep-Alive Server active on Port: {PORT}")
                httpd.serve_forever()
        except Exception as e:
            print(f"⚠️ Web Server Warning: {e}, retrying in 5s...")
            time.sleep(5)


# =========================================================
# 🛡️ SAFE TELEGRAM API WRAPPERS
# =========================================================

def safe_edit_message(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    try:
        return bot.edit_message_text(
            text=text, chat_id=chat_id, message_id=message_id,
            reply_markup=reply_markup, parse_mode=parse_mode
        )
    except Exception:
        pass


def safe_send_message(chat_id, text, reply_markup=None, parse_mode="HTML", disable_preview=True, reply_to_msg_id=None):
    try:
        return bot.send_message(
            chat_id=chat_id, text=text, reply_markup=reply_markup,
            parse_mode=parse_mode, disable_web_page_preview=disable_preview,
            reply_to_message_id=reply_to_msg_id
        )
    except Exception:
        try:
            return bot.send_message(
                chat_id=chat_id, text=text, reply_markup=reply_markup,
                parse_mode=None, disable_web_page_preview=disable_preview,
                reply_to_message_id=reply_to_msg_id
            )
        except Exception:
            return None


def safe_send_document(chat_id, document, caption="", parse_mode="HTML", reply_to_msg_id=None, reply_markup=None):
    try:
        return bot.send_document(chat_id, document, caption=caption, parse_mode=parse_mode, timeout=180, reply_to_message_id=reply_to_msg_id, reply_markup=reply_markup)
    except Exception:
        try:
            return bot.send_document(chat_id, document, caption=caption, parse_mode=None, timeout=180, reply_to_message_id=reply_to_msg_id, reply_markup=reply_markup)
        except Exception:
            return None


def safe_send_video(chat_id, video, caption="", parse_mode="HTML", reply_to_msg_id=None, reply_markup=None):
    try:
        return bot.send_video(chat_id, video, caption=caption, parse_mode=parse_mode, timeout=180, supports_streaming=True, reply_to_message_id=reply_to_msg_id, reply_markup=reply_markup)
    except Exception:
        try:
            return bot.send_video(chat_id, video, caption=caption, parse_mode=None, timeout=180, reply_to_message_id=reply_to_msg_id, reply_markup=reply_markup)
        except Exception:
            return None


# =========================================================
# 💎 BOLD FONT CONVERTER & DATABASE MANAGEMENT
# =========================================================

def to_bold_font(text: str) -> str:
    out = []
    for char in str(text):
        code = ord(char)
        if 65 <= code <= 90:
            out.append(chr(0x1D400 + (code - 65)))
        elif 97 <= code <= 122:
            out.append(chr(0x1D41A + (code - 97)))
        elif 48 <= code <= 57:
            out.append(chr(0x1D7CE + (code - 48)))
        else:
            out.append(char)
    return "".join(out)


def load_users_data():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_users_data(data):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def register_user(user):
    try:
        data = load_users_data()
        uid_str = str(user.id)
        if uid_str not in data:
            join_time = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
            data[uid_str] = {
                "id": user.id,
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "username": user.username if user.username else "N/A",
                "joined_at": join_time
            }
            save_users_data(data)
    except Exception as e:
        print(f"User Register Error: {e}")

def get_all_user_ids():
    data = load_users_data()
    return [int(uid) for uid in data.keys()]

def load_banned_users():
    if os.path.exists(BANNED_FILE):
        try:
            with open(BANNED_FILE, "r", encoding="utf-8") as f:
                return set(int(uid) for uid in json.load(f))
        except Exception:
            return set()
    return set()

def save_banned_users(banned_set):
    try:
        with open(BANNED_FILE, "w", encoding="utf-8") as f:
            json.dump(list(banned_set), f)
    except Exception:
        pass

def is_user_banned(user_id):
    if user_id == ADMIN_ID:
        return False
    return int(user_id) in load_banned_users()

def ban_user_id(user_id):
    banned = load_banned_users()
    banned.add(int(user_id))
    save_banned_users(banned)

def unban_user_id(user_id):
    banned = load_banned_users()
    if int(user_id) in banned:
        banned.remove(int(user_id))
        save_banned_users(banned)


# =========================================================
# 🔒 REAL-TIME FORCE GROUP JOIN CHECKER
# =========================================================

def is_user_subscribed(user_id):
    if user_id == ADMIN_ID:
        return True
    try:
        member = bot.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        if member.status in ['creator', 'administrator', 'member', 'restricted']:
            return True
        return False
    except Exception as e:
        print(f"Force Sub Verify Status: {e}")
        return False

def get_force_sub_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_join = types.InlineKeyboardButton("📢 গ্রুপে জয়েন করুন (Join Now)", url=FORCE_SUB_URL)
    btn_check = types.InlineKeyboardButton("✅ চেক জয়েন / আনলক করুন", callback_data="sub_check_now")
    markup.add(btn_join, btn_check)
    return markup

def send_force_sub_msg(chat_id, user_id):
    lock_text = (
        "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
        "   🔒 <b>𝐀𝐂𝐂𝐄𝐒𝐒 𝐋𝐎𝐂𝐊𝐄𝐃 - 𝐉𝐎𝐈𝐍 𝐑𝐄𝐐𝐔𝐈𝐑𝐄𝐃</b> 🔒\n"
        "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
        "👋 <b>প্রিয় গ্রাহক,</b>\n"
        "বটটির সমস্ত ভিআইপি ফিচার ও আনলিমিটেড সার্ভিস ব্যবহার করতে হলে আপনাকে অবশ্যই আমাদের অফিশিয়াল টেলিগ্রাম গ্রুপে যুক্ত থাকতে হবে।\n\n"
        "👉 <b>নিচের 'গ্রুপে জয়েন করুন' বাটনে ক্লিক করে গ্রুপে যুক্ত হোন এবং তারপর 'চেক জয়েন' বাটনে চাপ দিন:</b>"
    )
    return safe_send_message(chat_id, lock_text, reply_markup=get_force_sub_markup())


# =======================================================================
# 🔐 ADVANCED POLYMORPHIC CIPHER ENGINE (100% FIXED & UNBREAKABLE)
# =======================================================================

BASE64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

EMOJI_POOL = [
    "👿", "🔥", "🥵", "💀", "❌", "🔒", "⚡", "🎯",
    "%", "+", "=", "-", "&", "^", "_", "~",
    "k", "d", "j", "i", "h", "o", "b", "f",
    "q", "w", "r", "t", "y", "u", "p", "a",
    "s", "g", "l", "z", "x", "c", "v", "n",
    "m", "3", "9", "8", "4", "7", "2", "5",
    "6", "0", "1", "£", "€", "¥", "₹", "§",
    "π", "θ", "λ", "μ", "Ω", "∞", "≠", "÷"
]

def fix_html_relative_assets(html_content, base_url):
    if "<base " in html_content.lower():
        return html_content
    base_tag = f'<base href="{base_url}">'
    if re.search(r"<head[^>]*>", html_content, re.IGNORECASE):
        return re.sub(r"(<head[^>]*>)", rf"\1\n  {base_tag}", html_content, count=1, flags=re.IGNORECASE)
    elif re.search(r"<html[^>]*>", html_content, re.IGNORECASE):
        return re.sub(r"(<html[^>]*>)", rf"\1\n<head>\n  {base_tag}\n</head>", html_content, count=1, flags=re.IGNORECASE)
    else:
        return f"<head>{base_tag}</head>\n" + html_content


def scramble_inline_styles_v2(html_content):
    def replace_style(match):
        attrs = match.group(1)
        content = match.group(2)
        if not content.strip():
            return match.group(0)
        
        raw_b = content.encode("utf-8")
        k1 = random.randint(30, 200)
        k2 = random.randint(11, 89)
        byte_list = []
        curr = k1
        for b in raw_b:
            byte_list.append((b ^ curr) & 0xFF)
            curr = (curr + k2 + (b & 0x0F)) & 0xFF
            
        scrambled_css = (
            f"<script>"
            f"(function(){{"
            f"try{{"
            f"var _k={k1},_s={k2},_b={json.dumps(byte_list)},_out=new Uint8Array(_b.length);"
            f"for(var i=0;i<_b.length;i++){{var _v=_b[i]^_k;_out[i]=_v;_k=(_k+_s+(_v&15))&255;}}"
            f"var _st=document.createElement('style');"
            f"_st.innerHTML=new TextDecoder('utf-8').decode(_out);"
            f"document.head.appendChild(_st);"
            f"}}catch(e){{}}"
            f"}})();"
            f"</script>"
        )
        return scrambled_css

    pattern = re.compile(r"<style([^>]*)>(.*?)</style>", re.DOTALL | re.IGNORECASE)
    return pattern.sub(replace_style, html_content)


def scramble_inline_scripts_v2(html_content):
    def replace_script(match):
        attrs = match.group(1)
        content = match.group(2)
        if not content.strip() or "src=" in attrs.lower():
            return match.group(0)
        
        raw_b = content.encode("utf-8")
        k1 = random.randint(40, 210)
        k2 = random.randint(13, 97)
        byte_list = []
        curr = k1
        for b in raw_b:
            byte_list.append((b ^ curr) & 0xFF)
            curr = (curr + k2 + (b & 0x07)) & 0xFF
            
        scrambled_js = (
            f"(function(){{"
            f"try{{if(document.currentScript)document.currentScript.remove();}}catch(e){{}}"
            f"try{{"
            f"var _k={k1},_s={k2},_b={json.dumps(byte_list)},_out=new Uint8Array(_b.length);"
            f"for(var i=0;i<_b.length;i++){{var _v=_b[i]^_k;_out[i]=_v;_k=(_k+_s+(_v&7))&255;}}"
            f"var _c=new TextDecoder('utf-8').decode(_out);"
            f"(0,eval)(_c);"
            f"}}catch(e){{}}"
            f"}})();"
        )
        return f"<script{attrs}>{scrambled_js}</script>"

    pattern = re.compile(r"<script([^>]*)>(.*?)</script>", re.DOTALL | re.IGNORECASE)
    return pattern.sub(replace_script, html_content)


def generate_polymorphic_cipher(raw_html):
    step1 = scramble_inline_styles_v2(raw_html)
    step2 = scramble_inline_scripts_v2(step1)
    
    raw_bytes = step2.encode("utf-8")
    
    # 🎲 ডাইনামিক সল্ট ও কী জেনারেশন
    seed_a = random.randint(50, 230)
    seed_b = random.randint(17, 103)
    seed_c = random.randint(7, 43)

    transformed = bytearray()
    curr_a = seed_a
    curr_b = seed_b
    
    for i, b in enumerate(raw_bytes):
        x = (b ^ curr_a) & 0xFF
        x = (x + curr_b) & 0xFF
        x = (x ^ (i & 0xFF)) & 0xFF
        transformed.append(x)
        curr_a = (curr_a * 3 + seed_c) & 0xFF
        curr_b = (curr_b + 19) & 0xFF

    b64_str = base64.b64encode(transformed).decode("ascii")
    
    shuffled_emojis = list(EMOJI_POOL)
    random.shuffle(shuffled_emojis)
    
    custom_map = {BASE64_CHARS[i]: shuffled_emojis[i] for i in range(64)}
    custom_map["="] = "•"
    
    payload = "".join(custom_map.get(c, c) for c in b64_str)
    
    return {
        "payload": payload,
        "emojis": shuffled_emojis,
        "seed_a": seed_a,
        "seed_b": seed_b,
        "seed_c": seed_c
    }


def build_extreme_obfuscated_html(raw_html, fallback_title="Protected Document"):
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.IGNORECASE | re.DOTALL)
    page_title = title_match.group(1).strip() if (title_match and title_match.group(1).strip()) else fallback_title

    cipher_data = generate_polymorphic_cipher(raw_html)
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    token_str = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    
    junk_str = "👿🔥🥵💀❌=%+=-&398" + ''.join(random.choices(string.ascii_letters + string.digits + "^£π÷👿🔥🥵💀❌", k=120))
    fake_dump = f"👿🔥🥵💀❌ [কোড চোর সনাক্ত হয়েছে! তোর বাপ {BOT_USERNAME} দিয়ে ইনক্রিপ্ট করা কোড ডিকোড করার ক্ষমতা কারো নাই! ওনার: @{ADMIN_USERNAME}] 🔒⚡_{token_str}"

    payload_json = json.dumps(cipher_data["payload"])
    emojis_json = json.dumps(cipher_data["emojis"])
    seed_a = cipher_data["seed_a"]
    seed_b = cipher_data["seed_b"]
    seed_c = cipher_data["seed_c"]

    banner_content = (
        f"╔══════════════════════════════════════════════════════════════╗\n"
        f"║   🔒 MAHDE UNBREAKABLE ULTRA CIPHER V2.0 - DO NOT MODIFY    ║\n"
        f"║══════════════════════════════════════════════════════════════║\n"
        f"║  Obfuscated By: @{ADMIN_USERNAME:<43}║\n"
        f"║  Telegram Bot: {BOT_USERNAME:<44}║\n"
        f"║  Timestamp: {timestamp_str:<47}║\n"
        f"║  Security Hash: {token_str:<44}║\n"
        f"╚══════════════════════════════════════════════════════════════╝"
    )

    return f"""<!--
{banner_content}
-->
<!DOCTYPE html>
<!-- CIPHER_SIGNATURE: {junk_str} -->
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_title}</title>
<style>
* {{
    -webkit-user-select: none !important;
    -moz-user-select: none !important;
    -ms-user-select: none !important;
    user-select: none !important;
}}
</style>
<script>
(function() {{
    'use strict';

    // 🛑 1. ANTI-DEVTOOLS & SHORTCUT SHIELD
    window.addEventListener('contextmenu', function(e) {{ e.preventDefault(); e.stopPropagation(); return false; }}, true);
    window.addEventListener('keydown', function(e) {{
        if (
            e.key === 'F12' ||
            (e.ctrlKey && e.key.toLowerCase() === 'u') ||
            (e.ctrlKey && e.key.toLowerCase() === 's') ||
            (e.ctrlKey && e.shiftKey && ['i', 'j', 'c', 'k'].includes(e.key.toLowerCase()))
        ) {{
            e.preventDefault();
            e.stopPropagation();
            return false;
        }}
    }}, true);

    const _fakeMsg = "{fake_dump}";

    // 🛑 2. ANTI-DEBUGGER TIMING SHIELD
    let _t0 = Date.now();
    function _verifyIntegrity() {{
        let _t1 = Date.now();
        if (_t1 - _t0 > 400) {{
            try {{ document.documentElement.innerHTML = '<h1 style="color:red;text-align:center;margin-top:20%;">' + _fakeMsg + '</h1>'; }} catch(e){{}}
            throw new Error("Debugger Detained");
        }}
        _t0 = _t1;
    }}

    // 🛑 3. ANTI-HOOKING & DYNAMIC DECODER
    try {{
        const _nativeWrite = document.write.bind(document);
        const _nativeOpen = document.open.bind(document);
        const _nativeClose = document.close.bind(document);

        const _stdB64 = "{BASE64_CHARS}";
        const _emjList = {emojis_json};
        const _symMap = new Map();
        for (let i = 0; i < _emjList.length; i++) {{
            _symMap.set(_emjList[i], _stdB64[i]);
        }}
        _symMap.set("•", "=");

        const _pData = {payload_json};
        const _sA = {seed_a};
        const _sB = {seed_b};
        const _sC = {seed_c};

        _verifyIntegrity();

        const _symArray = Array.from(_pData);
        let _rawB64 = "";
        for (let j = 0; j < _symArray.length; j++) {{
            _rawB64 += _symMap.get(_symArray[j]) || _symArray[j];
        }}

        const _binStr = window.atob(_rawB64);
        const _len = _binStr.length;
        const _outBuf = new Uint8Array(_len);

        let _curA = _sA;
        let _curB = _sB;

        for (let k = 0; k < _len; k++) {{
            let _val = _binStr.charCodeAt(k);
            _val = (_val ^ (k & 255)) & 255;
            _val = (_val - _curB + 256) & 255;
            _val = (_val ^ _curA) & 255;
            _outBuf[k] = _val;
            
            _curA = (_curA * 3 + _sC) & 255;
            _curB = (_curB + 19) & 255;
        }}

        const _finalHtml = new TextDecoder("utf-8").decode(_outBuf);

        // 🛑 4. CONSOLE & MEMORY WIPER
        window.atob = function() {{ return _fakeMsg; }};
        console.log = function() {{ return _fakeMsg; }};
        console.dir = function() {{ return _fakeMsg; }};
        console.warn = function() {{ return _fakeMsg; }};
        console.error = function() {{ return _fakeMsg; }};
        console.clear();

        try {{
            Object.defineProperty(document.documentElement, 'outerHTML', {{ get: function() {{ return _fakeMsg; }} }});
            Object.defineProperty(document.body, 'outerHTML', {{ get: function() {{ return _fakeMsg; }} }});
        }} catch(e) {{}}

        // 🚀 5. INJECT RUNTIME NATIVE DOM
        _nativeOpen();
        _nativeWrite(_finalHtml);
        _nativeClose();

        _outBuf.fill(0);

    }} catch (err) {{
        document.body.innerHTML = '<h2 style="color:red;text-align:center;margin-top:20%;">' + _fakeMsg + '</h2>';
    }}

}})();
</script>
</head>
<body>
<noscript>
    <h2 style="color:red;text-align:center;font-family:sans-serif;margin-top:20%;">⚠️ JavaScript must be enabled to view this protected page.</h2>
</noscript>
</body>
</html>
"""


# =========================================================
# 🚀 ADVANCED MULTI-PLATFORM DIRECT API ENGINES
# =========================================================

def download_tiktok_direct(url):
    try:
        api_url = "https://www.tikwm.com/api/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }
        res = requests.post(api_url, data={"url": url}, headers=headers, timeout=20)
        data = res.json()
        if data.get("code") == 0 and "data" in data:
            v_data = data["data"]
            direct_vid_url = v_data.get("hdplay") or v_data.get("play")
            title = v_data.get("title") or "TikTok_HD_Video"
            duration = str(v_data.get("duration", "N/A")) + "s"
            
            random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            file_path = f"downloads/tiktok_{random_id}.mp4"
            os.makedirs("downloads", exist_ok=True)
            
            vid_res = requests.get(direct_vid_url, headers=headers, timeout=60, stream=True)
            with open(file_path, "wb") as f:
                for chunk in vid_res.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        
            real_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            if 0 < real_size <= 48 * 1024 * 1024:
                return {
                    "type": "file",
                    "path": file_path,
                    "title": title,
                    "size_mb": round(real_size / (1024 * 1024), 2)
                }
            else:
                return {
                    "type": "direct_url",
                    "url": direct_vid_url,
                    "title": title,
                    "size_mb": round(real_size / (1024 * 1024), 2) if real_size else "Unlimited",
                    "duration": duration,
                    "temp_path": file_path
                }
    except Exception as e:
        print(f"Direct TikTok Engine error: {e}")
    return None


def download_via_cobalt(url):
    instances = [
        "https://api.cobalt.tools",
        "https://co.wuk.sh",
        "https://cobalt.v0.id"
    ]
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    }
    payload = {
        "url": url,
        "videoQuality": "720",
        "youtubeVideoCodec": "h264"
    }
    for base_api in instances:
        try:
            res = requests.post(base_api, json=payload, headers=headers, timeout=12)
            if res.status_code == 200:
                data = res.json()
                direct_url = data.get("url")
                if not direct_url and data.get("picker"):
                    direct_url = data["picker"][0].get("url")
                if direct_url:
                    return direct_url
        except Exception as e:
            print(f"Cobalt Instance Warning ({base_api}): {e}")
            continue
    return None


def download_facebook_direct(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Referer": "https://snapsave.app/"
        }
        res = requests.post("https://snapsave.app/action.php", data={"url": url}, headers=headers, timeout=15)
        if res.status_code == 200:
            text = res.text
            links = re.findall(r'href="(https?://[^"]+)"', text)
            fb_links = [l for l in links if "fbcdn" in l or "video" in l or ".mp4" in l]
            if fb_links:
                direct_vid_url = fb_links[0].replace("&amp;", "&")
                random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                file_path = f"downloads/fb_{random_id}.mp4"
                os.makedirs("downloads", exist_ok=True)
                
                v_res = requests.get(direct_vid_url, headers=headers, timeout=60, stream=True)
                with open(file_path, "wb") as f:
                    for chunk in v_res.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                real_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                if 0 < real_size <= 48 * 1024 * 1024:
                    return {"type": "file", "path": file_path, "title": "Facebook_HD_Video", "size_mb": round(real_size / (1024 * 1024), 2)}
                else:
                    return {"type": "direct_url", "url": direct_vid_url, "title": "Facebook_HD_Video", "size_mb": round(real_size / (1024 * 1024), 2), "duration": "N/A", "temp_path": file_path}
    except Exception as e:
        print(f"Facebook Direct Engine Error: {e}")

    cobalt_url = download_via_cobalt(url)
    if cobalt_url:
        try:
            random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            file_path = f"downloads/fb_{random_id}.mp4"
            os.makedirs("downloads", exist_ok=True)
            v_res = requests.get(cobalt_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60, stream=True)
            with open(file_path, "wb") as f:
                for chunk in v_res.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
            real_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            if 0 < real_size <= 48 * 1024 * 1024:
                return {"type": "file", "path": file_path, "title": "Facebook_HD_Video", "size_mb": round(real_size / (1024 * 1024), 2)}
            else:
                return {"type": "direct_url", "url": cobalt_url, "title": "Facebook_HD_Video", "size_mb": round(real_size / (1024 * 1024), 2), "duration": "N/A", "temp_path": file_path}
        except Exception:
            pass
    return None


def get_instagram_video_from_embed(url):
    match = re.search(r'instagram\.com/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)', url)
    if not match:
        return None
    shortcode = match.group(1)
    
    embed_urls = [
        f"https://www.instagram.com/p/{shortcode}/embed/captioned/",
        f"https://www.instagram.com/reel/{shortcode}/embed/captioned/",
        f"https://www.instagram.com/p/{shortcode}/embed/",
        f"https://www.instagram.com/reel/{shortcode}/embed/"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    for embed_url in embed_urls:
        try:
            res = requests.get(embed_url, headers=headers, timeout=10)
            if res.status_code == 200:
                text = res.text
                matches = re.findall(r'video_url\\*":\\*"([^"]+)"', text)
                if not matches:
                    matches = re.findall(r'"video_url"\s*:\s*"([^"]+)"', text)
                if not matches:
                    matches = re.findall(r'<video[^>]*src="([^"]+)"', text)
                if not matches:
                    matches = re.findall(r'class="EmbeddedMediaVideo"[^>]*src="([^"]+)"', text)
                    
                for raw_url in matches:
                    clean_url = raw_url.replace('\\/', '/').replace('\\u0026', '&').replace('&amp;', '&').replace('\\', '')
                    if "scontent" in clean_url or "cdninstagram" in clean_url or ".mp4" in clean_url:
                        return clean_url
        except Exception as e:
            print(f"Embed Scraping Error ({embed_url}): {e}")
            continue
    return None


def download_instagram_direct(url):
    direct_vid_url = download_via_cobalt(url)

    if not direct_vid_url:
        try:
            s_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Referer": "https://fastdl.app/"
            }
            res = requests.post("https://fastdl.app/api/convert", data={"url": url}, headers=s_headers, timeout=12)
            if res.status_code == 200:
                data = res.json()
                if data.get("url"):
                    direct_vid_url = data["url"][0]["url"]
        except Exception:
            pass

    if not direct_vid_url:
        direct_vid_url = get_instagram_video_from_embed(url)

    if direct_vid_url:
        try:
            random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            file_path = f"downloads/insta_{random_id}.mp4"
            os.makedirs("downloads", exist_ok=True)
            
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            vid_res = requests.get(direct_vid_url, headers=headers, timeout=60, stream=True)
            with open(file_path, "wb") as f:
                for chunk in vid_res.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
            
            real_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            if 0 < real_size <= 48 * 1024 * 1024:
                return {"type": "file", "path": file_path, "title": "Instagram_Reels_HD", "size_mb": round(real_size / (1024 * 1024), 2)}
            elif real_size > 48 * 1024 * 1024:
                return {"type": "direct_url", "url": direct_vid_url, "title": "Instagram_Reels_HD", "size_mb": round(real_size / (1024 * 1024), 2), "duration": "N/A", "temp_path": file_path}
        except Exception as e:
            print(f"Instagram file download error: {e}")

    try:
        random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        output_tmpl = f"downloads/insta_{random_id}_%(id)s.%(ext)s"
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_tmpl,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {'instagram': {'user_agent': 'ios'}}
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            if os.path.exists(file_path):
                real_size = os.path.getsize(file_path)
                return {"type": "file", "path": file_path, "title": info.get('title', 'Instagram_Reels'), "size_mb": round(real_size / (1024 * 1024), 2)}
    except Exception as e:
        print(f"Instagram yt-dlp fallback error: {e}")

    return None


def download_youtube_direct(url):
    cobalt_direct_url = download_via_cobalt(url)
    if cobalt_direct_url:
        try:
            random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            file_path = f"downloads/yt_{random_id}.mp4"
            os.makedirs("downloads", exist_ok=True)
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            v_res = requests.get(cobalt_direct_url, headers=headers, timeout=60, stream=True)
            with open(file_path, "wb") as f:
                for chunk in v_res.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
            real_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            if 0 < real_size <= 48 * 1024 * 1024:
                return {"type": "file", "path": file_path, "title": "YouTube_HD_Video", "size_mb": round(real_size / (1024 * 1024), 2)}
            else:
                return {"type": "direct_url", "url": cobalt_direct_url, "title": "YouTube_HD_Video", "size_mb": round(real_size / (1024 * 1024), 2), "duration": "N/A", "temp_path": file_path}
        except Exception:
            pass

    random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    output_tmpl = f"downloads/yt_{random_id}_%(id)s.%(ext)s"
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_tmpl,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'mweb'],
                'skip': ['webpage']
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.android.youtube/19.09.37 (Linux; U; Android 11; en_US) gzip'
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'YouTube_HD_Video')
            duration = info.get('duration_string', 'N/A')
            file_path = ydl.prepare_filename(info)
            if not os.path.exists(file_path):
                base, _ = os.path.splitext(file_path)
                for ext in ['.mp4', '.mkv', '.webm', '.3gp']:
                    if os.path.exists(base + ext):
                        file_path = base + ext
                        break

            if os.path.exists(file_path):
                real_size = os.path.getsize(file_path)
                if 0 < real_size <= 48 * 1024 * 1024:
                    return {"type": "file", "path": file_path, "title": title, "size_mb": round(real_size / (1024 * 1024), 2)}
                else:
                    return {"type": "direct_url", "url": info.get('url') or url, "title": title, "size_mb": round(real_size / (1024 * 1024), 2), "duration": duration, "temp_path": file_path}
    except Exception as e:
        print(f"YT-DLP Android Bypass Error: {e}")
    return None


def process_unlimited_video(url):
    os.makedirs("downloads", exist_ok=True)
    url_lower = url.lower()
    
    if any(k in url_lower for k in ["tiktok.com", "douyin.com"]):
        tiktok_res = download_tiktok_direct(url)
        if tiktok_res:
            return tiktok_res

    if any(k in url_lower for k in ["facebook.com", "fb.watch", "fb.gg", "fb.com"]):
        fb_res = download_facebook_direct(url)
        if fb_res:
            return fb_res

    if any(k in url_lower for k in ["instagram.com", "instagr.am"]):
        insta_res = download_instagram_direct(url)
        if insta_res:
            return insta_res
        else:
            raise Exception("ইনস্টাগ্রাম ভিডিওটি একসেস করা সম্ভব হচ্ছে না। লিংকটি সঠিক ও পাবলিক কিনা তা নিশ্চিত করুন।")

    if any(k in url_lower for k in ["youtube.com", "youtu.be"]):
        yt_res = download_youtube_direct(url)
        if yt_res:
            return yt_res

    cobalt_direct_url = download_via_cobalt(url)
    if cobalt_direct_url:
        try:
            random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            file_path = f"downloads/video_{random_id}.mp4"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            v_res = requests.get(cobalt_direct_url, headers=headers, timeout=60, stream=True)
            with open(file_path, "wb") as f:
                for chunk in v_res.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
            real_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            if 0 < real_size <= 48 * 1024 * 1024:
                return {"type": "file", "path": file_path, "title": "Social_Media_HD_Video", "size_mb": round(real_size / (1024 * 1024), 2)}
            else:
                return {"type": "direct_url", "url": cobalt_direct_url, "title": "Social_Media_HD_Video", "size_mb": round(real_size / (1024 * 1024), 2), "duration": "N/A", "temp_path": file_path}
        except Exception:
            pass

    random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    output_tmpl = f"downloads/{random_id}_%(id)s.%(ext)s"

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_tmpl,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'extractor_retries': 5,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
        except Exception:
            info = ydl.extract_info(url, download=False)

        if not info:
            raise Exception("ভিডিওটির ডেটা পাওয়া যায়নি! লিংকটি প্রাইভেট অথবা অবৈধ।")

        title = info.get('title', 'VIP_Video')
        duration = info.get('duration_string', 'N/A')
        direct_stream_url = info.get('url')

        file_path = ydl.prepare_filename(info)
        if not os.path.exists(file_path):
            base, _ = os.path.splitext(file_path)
            for ext in ['.mp4', '.mkv', '.webm', '.3gp']:
                if os.path.exists(base + ext):
                    file_path = base + ext
                    break

        if os.path.exists(file_path):
            real_size = os.path.getsize(file_path)
            if 0 < real_size <= 48 * 1024 * 1024:
                return {
                    "type": "file",
                    "path": file_path,
                    "title": title,
                    "size_mb": round(real_size / (1024 * 1024), 2)
                }
            else:
                return {
                    "type": "direct_url",
                    "url": direct_stream_url or url,
                    "title": title,
                    "size_mb": round(real_size / (1024 * 1024), 2),
                    "duration": duration,
                    "temp_path": file_path
                }
        else:
            filesize = info.get('filesize') or info.get('filesize_approx') or 0
            return {
                "type": "direct_url",
                "url": direct_stream_url or url,
                "title": title,
                "size_mb": round(filesize / (1024 * 1024), 2) if filesize else "Unlimited",
                "duration": duration
            }


# =========================================================
# 📱 KEYBOARDS & MENUS
# =========================================================

def get_persistent_menu(user_id=None):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_vid = types.KeyboardButton("🎥 𝐔𝐑𝐋 𝐓𝐎 𝐕𝐈𝐃𝐄𝐎")
    btn_obf = types.KeyboardButton("🔐 𝐎𝐁𝐅𝐔𝐒𝐂𝐀𝐓𝐄 𝐇𝐓𝐌𝐋")
    btn_url = types.KeyboardButton("🌐 𝐔𝐑𝐋 𝐓𝐎 𝐇𝐓𝐌𝐋")
    btn_dev = types.KeyboardButton("👑 𝐎𝐖𝐍𝐄𝐑 & 𝐃𝐄𝐕")
    btn_help = types.KeyboardButton("⚡ 𝐕𝐈𝐏 𝐅𝐄𝐀𝐓𝐔𝐑𝐄𝐒 & 𝐈𝐍𝐅𝐎")

    markup.add(btn_vid)
    markup.add(btn_obf, btn_url)
    
    if user_id and int(user_id) == ADMIN_ID:
        btn_admin = types.KeyboardButton("🛠️ 𝐀𝐃𝐌𝐈𝐍 𝐂𝐎𝐍𝐓𝐑𝐎𝐋")
        markup.add(btn_admin)
        
    markup.add(btn_dev, btn_help)
    return markup


def get_admin_interactive_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_stats = types.InlineKeyboardButton("📊 লাইভ স্ট্যাটাস", callback_data="adm_stats")
    btn_users = types.InlineKeyboardButton("👥 ইউজার লিস্ট", callback_data="adm_users")
    btn_bc = types.InlineKeyboardButton("📢 অল ইউজার ব্রডকাস্ট", callback_data="adm_broadcast")
    btn_send = types.InlineKeyboardButton("✉️ ডিরেক্ট মেসেজ / মিডিয়া", callback_data="adm_send_pm")
    btn_ban = types.InlineKeyboardButton("⛔ ইউজার ব্যান", callback_data="adm_ban")
    btn_unban = types.InlineKeyboardButton("🟢 ইউজার আনব্যান", callback_data="adm_unban")
    btn_banned_list = types.InlineKeyboardButton("🚫 ব্যানড লিস্ট", callback_data="adm_banned")
    btn_close = types.InlineKeyboardButton("❌ ক্লোজ প্যানেল", callback_data="adm_close")
    
    markup.add(btn_stats, btn_users)
    markup.add(btn_bc, btn_send)
    markup.add(btn_ban, btn_unban)
    markup.add(btn_banned_list)
    markup.add(btn_close)
    return markup


def check_access(message):
    try:
        uid = message.from_user.id
        if uid == ADMIN_ID:
            return True
        if is_user_banned(uid):
            safe_send_message(
                message.chat.id,
                "🚫 <b>এক্সেস সাময়িক নিষিদ্ধ করা হয়েছে!</b>\n\n"
                "⚠️ পলিসি লঙ্ঘনের কারণে আপনাকে সাসপেন্ড করা হয়েছে।\n"
                f"👑 যোগাযোগ করুন: @{ADMIN_USERNAME}"
            )
            return False
        
        if not is_user_subscribed(uid):
            send_force_sub_msg(message.chat.id, uid)
            return False

        return True
    except Exception:
        return True


def smart_normalize_url(raw_text):
    text = raw_text.strip()
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$", text):
        return f"https://{text}"
    return None


def fetch_url_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=25, verify=True)
    except requests.exceptions.SSLError:
        res = requests.get(url, headers=headers, timeout=25, verify=False)
    except requests.exceptions.RequestException:
        if url.startswith("https://"):
            http_url = "http://" + url[8:]
            res = requests.get(http_url, headers=headers, timeout=25)
        else:
            raise
    
    res.encoding = res.apparent_encoding or "utf-8"
    return res.text


# =========================================================
# 📢 RELIABLE BROADCAST ENGINE
# =========================================================

def broadcast_any_message(from_chat_id, source_message):
    users = get_all_user_ids()
    banned_users = load_banned_users()
    sent_count = 0
    failed_count = 0
    
    status_msg = safe_send_message(from_chat_id, "⏳ <b>সকল ইউজারের কাছে ব্রডকাস্ট পাঠানো হচ্ছে... দয়া করে অপেক্ষা করুন।</b>")
    start_time = time.time()
    
    for uid in users:
        if uid in banned_users:
            continue
        try:
            bot.copy_message(
                chat_id=uid,
                from_chat_id=from_chat_id,
                message_id=source_message.message_id,
                reply_markup=get_persistent_menu(uid)
            )
            sent_count += 1
            time.sleep(0.04)
        except Exception:
            failed_count += 1

    total_time = round(time.time() - start_time, 2)
    report_text = (
        "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
        "   📢 <b>𝐁𝐑𝐎𝐀𝐃𝐂𝐀𝐒𝐓 𝐂𝐎𝐌𝐏𝐋𝐄𝐓𝐄𝐃!</b> 📢\n"
        "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
        f"✅ <b>সফলভাবে ডেলিভারড:</b> <code>{sent_count}</code> জন\n"
        f"❌ <b>ব্যর্থ হয়েছে:</b> <code>{failed_count}</code> জন\n"
        f"⏱️ <b>মোট সময় লেগেছে:</b> <code>{total_time}s</code>\n"
        f"👥 <b>মোট টার্গেটেড ইউজার:</b> <code>{len(users)}</code> জন"
    )
    if status_msg:
        safe_edit_message(from_chat_id, status_msg.message_id, report_text)
    else:
        safe_send_message(from_chat_id, report_text, reply_markup=get_persistent_menu(from_chat_id))


# =========================================================
# 👑 WELCOME MESSAGE GENERATOR
# =========================================================

def send_main_welcome(chat_id, user):
    welcome_text = (
        "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
        "  ⚡ 𝐔𝐋𝐓𝐑𝐀 𝐇𝐓𝐌𝐋 𝐂𝐈𝐏𝐇𝐄𝐑 𝐏𝐑𝐎 (𝐕২.𝟎) ⚡\n"
        "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
        f"👋 <b>স্বাগতম, {html.escape(user.first_name or 'গ্রাহক')}!</b>\n"
        "আপনার সোর্স কোড সম্পূর্ণ 👿🔥🥵💀❌ পলিমরফিক সাইফারে আনব্রেকেবল লক করুন।\n\n"
        "💎 <b>𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐐𝐔𝐀𝐋𝐈𝐅𝐈𝐂𝐀𝐓𝐈𝐎𝐍𝐒:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔹 🔒 <b>𝐂𝐒𝐒 & 𝐉𝐒 𝐙𝐞𝐫𝐨-𝐋𝐞𝐚𝐤 𝐒𝐡𝐢𝐞𝐥𝐝</b>\n"
        "╰─ ডিকোড করলেও আসল 𝐂𝐒𝐒 ও 𝐉𝐒 কখনোই বের হবে না।\n\n"
        "🔹 🛡️ <b>𝐀𝐧𝐭𝐢-𝐇𝐨𝐨𝐤 & 𝐃𝐞𝐯𝐓𝐨𝐨𝐥𝐬 𝐁𝐚𝐫𝐫𝐢𝐞𝐫</b>\n"
        "╰─ DevTools বা স্ক্রিপ্ট হুক করলে ব্রাউজার অটো ক্র্যাশ করবে।\n\n"
        "🔹 🌐 <b>𝟏𝟎𝟎% 𝐍𝐚𝐭𝐢𝐯𝐞 𝐁𝐫𝐨𝐰𝐬𝐞𝐫 𝐄𝐱𝐞𝐜𝐮𝐭𝐢𝐨𝐧</b>\n"
        "╰─ 𝐅𝐢𝐫𝐞𝐛𝐚𝐬𝐞 ডাটাবেজ, CSS ও JS সরাসরি স্মুথলি কাজ করবে।\n\n"
        "🔹 🎥 <b>𝐔𝐧𝐥𝐢𝐦𝐢𝐭𝐞𝐝 𝐌𝐁 𝐕𝐢𝐝𝐞𝐨 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐞𝐫</b>\n"
        "╰─ TikTok, YouTube, FB, Instagram এর যেকোনো সাইজের HD ভিডিও ডাউনলোড।\n\n"
        "🔹 🌐 <b>𝐒𝐦𝐚𝐫𝐭 𝐔𝐑𝐋 𝐓𝐨 𝐑𝐚𝐟𝐬𝐚𝐧 𝐂𝐥𝐨𝐧𝐞𝐫</b>\n"
        "╰─ লাইভ এসেট ফিক্সিং সহ <b>URL_To_MAHDE.html</b> তৈরি।\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <b>নিচের কীবোর্ড মেনু থেকে আপনার প্রয়োজনীয় অপশন নির্বাচন করুন:</b>\n"
        f"🤖 <b>𝐁𝐨𝐭:</b> {BOT_USERNAME} | 👑 <b>𝐎𝐰𝐧𝐞𝐫:</b> @{ADMIN_USERNAME}"
    )
    safe_send_message(chat_id, welcome_text, reply_markup=get_persistent_menu(user.id))


# =========================================================
# 🚀 START & ACCESS HANDLERS
# =========================================================

@bot.message_handler(commands=["start"])
def start_msg(message):
    user = message.from_user
    register_user(user)
    user_states[user.id] = None

    if is_user_banned(user.id):
        safe_send_message(message.chat.id, f"⛔ <b>আপনাকে এই বট থেকে ব্যান করা হয়েছে!</b>\n👑 যোগাযোগ: @{ADMIN_USERNAME}")
        return

    if not is_user_subscribed(user.id):
        send_force_sub_msg(message.chat.id, user.id)
        return

    send_main_welcome(message.chat.id, user)


@bot.callback_query_handler(func=lambda call: call.data == "sub_check_now")
def sub_check_callback(call):
    user = call.from_user
    register_user(user)

    if is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "🎉 অভিনন্দন! গ্রুপ মেম্বারশিপ সফলভাবে ভেরিফাইড হয়েছে।", show_alert=False)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_main_welcome(call.message.chat.id, user)
    else:
        bot.answer_callback_query(call.id, "⚠️ আপনি এখনো গ্রুপে জয়েন করেননি! দয়া করে জয়েন বাটনে চাপ দিয়ে গ্রুপে জয়েন করুন।", show_alert=True)


@bot.message_handler(commands=["admin", "panel"])
def admin_panel_cmd(message):
    if message.from_user.id != ADMIN_ID:
        safe_send_message(message.chat.id, "⛔ <b>এক্সেস ডিনাইড! শুধুমাত্র অ্যাডমিন ব্যবহার করতে পারবেন।</b>", reply_markup=get_persistent_menu(message.from_user.id))
        return

    users_count = len(get_all_user_ids())
    banned_count = len(load_banned_users())

    panel_text = (
        "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
        "   🛠️ <b>𝐕𝐈𝐏 𝐀𝐃𝐌𝐈𝐍 𝐂𝐎𝐍𝐓𝐑𝐎𝐋 𝐏𝐀𝐍𝐄𝐋</b> 🛠️\n"
        "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
        f"👥 <b>মোট রেজিস্টার্ড ইউজার:</b> <code>{users_count}</code> জন\n"
        f"🚫 <b>ব্যানড ইউজার:</b> <code>{banned_count}</code> জন\n"
        f"⚡ <b>সার্ভার স্ট্যাটাস:</b> 🟢 <b>Active 24/7 (Railway Live)</b>\n\n"
        "👇 <b>যেকোনো অ্যাকশন পরিচালনা করতে নিচের বোতামে চাপ দিন:</b>"
    )
    safe_send_message(message.chat.id, panel_text, reply_markup=get_admin_interactive_panel())


# =========================================================
# 🛠️ ADMIN INLINE CALLBACKS
# =========================================================

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_callback_handler(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ এক্সেস ডিনাইড!", show_alert=True)
        return

    data = call.data

    if data == "adm_stats":
        total_users = len(get_all_user_ids())
        banned_count = len(load_banned_users())
        stats_text = (
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
            "   📊 <b>𝐁𝐎𝐓 𝐋𝐈𝐕𝐄 𝐒𝐓𝐀𝐓𝐈𝐒𝐓𝐈𝐂𝐒</b> 📊\n"
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
            f"👥 <b>মোট সক্রিয় ইউজার:</b> <code>{to_bold_font(str(total_users))}</code> জন\n"
            f"🚫 <b>ব্যানড ইউজার:</b> <code>{to_bold_font(str(banned_count))}</code> জন\n"
            f"👑 <b>অ্যাডমিন:</b> @{ADMIN_USERNAME}\n"
            f"🤖 <b>বট:</b> {BOT_USERNAME}\n"
            f"⚡ <b>সার্ভার স্ট্যাটাস:</b> 🟢 <b>১০০% অনলাইন (Keep-Alive Live)</b>\n"
            f"⏰ <b>লাইভ সময়:</b> <code>{to_bold_font(datetime.now().strftime('%d-%m-%Y | %I:%M:%S %p'))}</code>"
        )
        safe_send_message(ADMIN_ID, stats_text, reply_markup=get_persistent_menu(ADMIN_ID))
        bot.answer_callback_query(call.id, "✅ লাইভ স্ট্যাটাস পাঠানো হয়েছে!")

    elif data == "adm_users":
        users_data = load_users_data()
        total = len(users_data)
        if total == 0:
            bot.answer_callback_query(call.id, "⚠️ ইউজার লিস্ট ফাঁকা!", show_alert=True)
            return

        if total <= 20:
            text = f"👥 <b>মোট ইউজার তালিকা ({total} জন):</b>\n\n"
            for idx, (uid, info) in enumerate(users_data.items(), 1):
                name = html.escape(f"{info.get('first_name', '')} {info.get('last_name', '')}".strip())
                text += f"{idx}. <code>{uid}</code> | {name} | @{info.get('username')}\n"
            safe_send_message(ADMIN_ID, text)
        else:
            file_path = "users_live_list.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                for idx, (uid, info) in enumerate(users_data.items(), 1):
                    name = f"{info.get('first_name', '')} {info.get('last_name', '')}".strip()
                    f.write(f"{idx}. ID: {uid} | Name: {name} | @{info.get('username')} | Joined: {info.get('joined_at')}\n")
            with open(file_path, "rb") as f_doc:
                bot.send_document(ADMIN_ID, f_doc, caption=f"👥 <b>মোট রেজিস্টার্ড ইউজার:</b> <code>{total}</code> জন।", parse_mode="HTML")
            if os.path.exists(file_path):
                os.remove(file_path)
        bot.answer_callback_query(call.id, "✅ ইউজার লিস্ট প্রস্তুত!")

    elif data == "adm_broadcast":
        user_states[ADMIN_ID] = "ADMIN_WAITING_BROADCAST"
        broadcast_prompt = (
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
            "   📢 <b>𝐀𝐃𝐌𝐈𝐍 𝐁𝐑𝐎𝐀𝐃𝐂𝐀𝐒𝐓 𝐌𝐎𝐃𝐄</b> 📢\n"
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
            "📝 <b>এখন যেকোনো মেসেজ পাঠান:</b>\n"
            "• যেকোনো <b>টেক্সট / লিংক / ক্যাপশন</b>\n"
            "• যেকোনো <b>ছবি (Photo)</b>\n"
            "• যেকোনো <b>ভিডিও (Video)</b>\n"
            "• যেকোনো <b>ফাইল / ডকুমেন্ট (Document)</b>\n"
            "• যেকোনো <b>ভয়েস / অডিও বা স্টিকার</b>\n\n"
            "<i>(আপনি যা পাঠাবেন তা হুবহু সকল ইউজারের কাছে কপি হয়ে চলে যাবে)</i>"
        )
        safe_send_message(ADMIN_ID, broadcast_prompt)
        bot.answer_callback_query(call.id)

    elif data == "adm_send_pm":
        user_states[ADMIN_ID] = "ADMIN_WAITING_SEND_PM"
        pm_prompt = (
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
            "   ✉️ <b>𝐃𝐈𝐑𝐄𝐂𝐓 𝐔𝐒𝐄𝐑 𝐌𝐄𝐒𝐒𝐀𝐆𝐄</b> ✉️\n"
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
            "👉 <b>টার্গেট ইউজারের User ID পাঠান:</b>\n"
            "<i>(অথবা একবারে পাঠাতে: <code>USER_ID আপনার বার্তা</code> লিখে পাঠান)</i>"
        )
        safe_send_message(ADMIN_ID, pm_prompt)
        bot.answer_callback_query(call.id)

    elif data == "adm_ban":
        user_states[ADMIN_ID] = "ADMIN_WAITING_BAN"
        safe_send_message(ADMIN_ID, "⛔ <b>ইউজার ব্যান মোড:</b>\n\nযে ইউজারকে ব্যান করতে চান তার <b>ইউজার আইডি (User ID)</b> সেন্ড করুন:")
        bot.answer_callback_query(call.id)

    elif data == "adm_unban":
        user_states[ADMIN_ID] = "ADMIN_WAITING_UNBAN"
        safe_send_message(ADMIN_ID, "🟢 <b>ইউজার আনব্যান মোড:</b>\n\nযে ইউজারকে আনব্যান করতে চান তার <b>ইউজার আইডি (User ID)</b> সেন্ড করুন:")
        bot.answer_callback_query(call.id)

    elif data == "adm_banned":
        banned = load_banned_users()
        if not banned:
            safe_send_message(ADMIN_ID, "🟢 বর্তমানে কোনো ব্যানড ইউজার নেই।")
        else:
            text = "🚫 <b>ব্যানড ইউজার তালিকা:</b>\n\n" + "\n".join([f"• <code>{uid}</code>" for uid in banned])
            safe_send_message(ADMIN_ID, text)
        bot.answer_callback_query(call.id)

    elif data == "adm_close":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.answer_callback_query(call.id, "প্যানেল ক্লোজ করা হয়েছে")


# =========================================================
# 🌟 UNIVERSAL MEDIA DISPATCHER
# =========================================================

@bot.message_handler(content_types=['photo', 'video', 'audio', 'voice', 'sticker', 'animation', 'video_note', 'contact', 'location'])
def handle_admin_media(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if user_id == ADMIN_ID and state == "ADMIN_WAITING_BROADCAST":
        user_states[user_id] = None
        broadcast_any_message(ADMIN_ID, message)
        return

    if user_id == ADMIN_ID and str(state).startswith("ADMIN_SENDING_PM_TO_"):
        target_uid = int(str(state).replace("ADMIN_SENDING_PM_TO_", ""))
        user_states[user_id] = None
        try:
            bot.copy_message(chat_id=target_uid, from_chat_id=ADMIN_ID, message_id=message.message_id, reply_markup=get_persistent_menu(target_uid))
            safe_send_message(ADMIN_ID, f"✅ ইউজার <code>{target_uid}</code>-এর কাছে মিডিয়াটি সফলভাবে পৌঁছেছে!")
        except Exception as e:
            safe_send_message(ADMIN_ID, f"❌ ইউজার <code>{target_uid}</code>-কে পাঠানো যায়নি!\n⚠️ কারণ: <code>{html.escape(str(e))}</code>")
        return


# =========================================================
# 💬 TEXT HANDLER (SMART CONTEXTUAL PROCESSING)
# =========================================================

@bot.message_handler(func=lambda msg: msg.text and not msg.text.startswith("/"))
def handle_text(message):
    if not check_access(message):
        return

    user_id = message.from_user.id
    register_user(message.from_user)
    text = message.text.strip()
    state = user_states.get(user_id)

    # 👑 ADMIN ROUTER
    if user_id == ADMIN_ID:
        if state == "ADMIN_WAITING_BROADCAST":
            user_states[user_id] = None
            broadcast_any_message(ADMIN_ID, message)
            return

        elif state == "ADMIN_WAITING_SEND_PM":
            parts = text.split(maxsplit=1)
            if len(parts) == 2 and parts[0].isdigit():
                user_states[user_id] = None
                target_uid = int(parts[0])
                msg_body = parts[1]
                formatted_msg = (
                    "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
                    "   ✉️ <b>𝐌𝐄𝐒𝐒𝐀𝐆𝐄 𝐅𝐑𝐎𝐌 𝐀𝐃𝐌𝐈𝐍</b> ✉️\n"
                    "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
                    f"{msg_body}\n\n"
                    f"👑 <b>অ্যাডমিন:</b> @{ADMIN_USERNAME}"
                )
                res = safe_send_message(target_uid, formatted_msg, reply_markup=get_persistent_menu(target_uid))
                if res:
                    safe_send_message(ADMIN_ID, f"✅ ইউজার <code>{target_uid}</code>-কে ডিরেক্ট মেসেজ পাঠানো হয়েছে।")
                else:
                    safe_send_message(ADMIN_ID, f"❌ ইউজার <code>{target_uid}</code>-কে মেসেজ পাঠানো যায়নি।")
                return
            elif text.isdigit():
                target_uid = int(text)
                user_states[user_id] = f"ADMIN_SENDING_PM_TO_{target_uid}"
                safe_send_message(ADMIN_ID, f"🎯 <b>টার্গেট ইউজার আইডি:</b> <code>{target_uid}</code>\n\nএখন এই ইউজারের জন্য যেকোনো <b>মেসেজ, ছবি, ভিডিও, ভয়েস বা ফাইল</b> পাঠান:")
                return
            else:
                safe_send_message(ADMIN_ID, "⚠️ সঠিক ফরম্যাটে দিন! যেমন: <code>6753121703 হ্যালো</code> অথবা শুধু <code>6753121703</code>")
                return

        elif str(state).startswith("ADMIN_SENDING_PM_TO_"):
            target_uid = int(str(state).replace("ADMIN_SENDING_PM_TO_", ""))
            user_states[user_id] = None
            try:
                bot.copy_message(chat_id=target_uid, from_chat_id=ADMIN_ID, message_id=message.message_id, reply_markup=get_persistent_menu(target_uid))
                safe_send_message(ADMIN_ID, f"✅ ইউজার <code>{target_uid}</code>-এর কাছে মেসেজটি সফলভাবে পৌঁছেছে!")
            except Exception as e:
                safe_send_message(ADMIN_ID, f"❌ মেসেজ পাঠানো যায়নি!\n⚠️ কারণ: <code>{html.escape(str(e))}</code>")
            return

        elif state == "ADMIN_WAITING_BAN":
            user_states[user_id] = None
            if text.isdigit():
                target_uid = int(text)
                if target_uid == ADMIN_ID:
                    safe_send_message(ADMIN_ID, "❌ নিজেকে ব্যান করতে পারবেন না!")
                else:
                    ban_user_id(target_uid)
                    safe_send_message(target_uid, f"⛔ <b>আপনাকে এই বট থেকে ব্যান করা হয়েছে!</b>\n👑 যোগাযোগ: @{ADMIN_USERNAME}")
                    safe_send_message(ADMIN_ID, f"✅ ইউজার <code>{target_uid}</code>-কে সফলভাবে ব্যান করা হয়েছে।")
            else:
                safe_send_message(ADMIN_ID, "❌ সঠিক ইউজার আইডি দিন!")
            return

        elif state == "ADMIN_WAITING_UNBAN":
            user_states[user_id] = None
            if text.isdigit():
                target_uid = int(text)
                unban_user_id(target_uid)
                safe_send_message(target_uid, "🎉 <b>আপনাকে সফলভাবে আনব্যান করা হয়েছে!</b>", reply_markup=get_persistent_menu(target_uid))
                safe_send_message(ADMIN_ID, f"✅ ইউজার <code>{target_uid}</code>-কে আনব্যান করা হয়েছে।")
            else:
                safe_send_message(ADMIN_ID, "❌ সঠিক ইউজার আইডি দিন!")
            return

    # 📱 KEYBOARD MENU BUTTONS
    if "𝐔𝐑𝐋 𝐓𝐎 𝐕𝐈𝐃𝐄𝐎" in text:
        user_states[user_id] = "WAITING_VIDEO_URL"
        text_reply = (
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
            "   🎥 <b>𝐔𝐍𝐋𝐈𝐌𝐈𝐓𝐄𝐃 𝐕𝐈𝐃𝐄𝐎 𝐃𝐎𝐖𝐍𝐋𝐎𝐀𝐃𝐄𝐑</b> 🎥\n"
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
            "🔗 <b>ভিডিওর লিংকটি নিচে সেন্ড করুন:</b>\n"
            "<i>(TikTok, YouTube, Facebook, Instagram Reels, Twitter/X, Pinterest ইত্যাদির যেকোনো সাইজের HD ভিডিও)</i>\n\n"
            "⚡ <b>ফিচার:</b> নো ওয়াটারমার্ক | ফুল এইচডি/৪কে সাপোর্ট | আনলিমিটেড স্পিড"
        )
        safe_send_message(message.chat.id, text_reply, reply_markup=get_persistent_menu(user_id), reply_to_msg_id=message.message_id)
        return

    elif "𝐎𝐁𝐅𝐔𝐒𝐂𝐀𝐓𝐄 𝐇𝐓𝐌𝐋" in text:
        user_states[user_id] = "WAITING_HTML"
        text_reply = (
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
            "  🛡️ <b> আনব্রেকেবল ইনক্রিপশন (MAHDE ULTRA V2)</b>\n"
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
            "📁 <b>আপনার <code>.html</code> বা <code>.htm</code> ফাইলটি এখানে সেন্ড করুন:</b>\n\n"
            "🛡️ <b>প্রোটেকশন ফিচারসমূহ:</b>\n"
            "• 🔒 <i>ডায়নামিক পলিমরফিক কেয়স সাইফার</i>\n"
            "• 🛑 <i>Anti-Hook & Anti-Debug Barrier (ডিকোড অসম্ভব)</i>\n"
            "• 👿 <i>👿🔥🥵💀❌ মাল্টি-লেয়ার রিয়েল টাইম এক্সিকিউশন</i>\n"
            "• 🚫 <i>F12, Inspect Element, View Source ও রাইট ক্লিক সম্পূর্ণ ধ্বংস</i>\n"
            "• ⚡ <i>জিরো-লিক মেমোরি ডিকোডার ও কাস্টম অ্যান্টি-থেফট প্রটেকশন</i>\n"
            "• 🌐 <i>ব্রাউজারে ১০০% স্মুথ ও নেটিভ এক্সিকিউশন</i>"
        )
        safe_send_message(message.chat.id, text_reply, reply_markup=get_persistent_menu(user_id), reply_to_msg_id=message.message_id)
        return

    elif "𝐔𝐑𝐋 𝐓𝐎 𝐇𝐓𝐌𝐋" in text:
        user_states[user_id] = "WAITING_URL"
        text_reply = (
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
            "   🌐 <b>ইউআরএল টু মাহাদি (URL TO MAHDE)</b> 🌐\n"
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
            "🔗 <b>টার্গেট ওয়েবসাইটের ডোমেইন বা লিংক সেন্ড করুন:</b>\n"
            "<i>(যেমন: <code>example.com</code> অথবা <code>https://example.com</code>)</i>\n\n"
            "⚡ <b>সুবিধা:</b> <code>https://</code> না দিলেও বট স্বয়ংক্রিয়ভাবে লাইভ এসেট ফিক্স করে <b>URL_To_MAHDE.html</b> ফাইল ডেলিভারি করবে।"
        )
        safe_send_message(message.chat.id, text_reply, reply_markup=get_persistent_menu(user_id), reply_to_msg_id=message.message_id)
        return

    elif "𝐀𝐃𝐌𝐈𝐍 𝐂𝐎𝐍𝐓𝐑𝐎𝐋" in text and user_id == ADMIN_ID:
        admin_panel_cmd(message)
        return

    elif "𝐎𝐖𝐍𝐄𝐑 & 𝐃𝐄𝐕" in text:
        owner_text = (
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
            "   💎 <b>𝐕𝐈𝐏 𝐃𝐄𝐕𝐄𝐋𝐎𝐏𝐄𝐑 &amp; 𝐎𝐖𝐍𝐄𝐑 𝐈𝐍𝐅𝐎</b> 💎\n"
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
            f"👤 <b>মালিক ও ডেভেলপার:</b> @{ADMIN_USERNAME}\n"
            f"🤖 <b>বট ইউজারনেম:</b> {BOT_USERNAME}\n"
            "🛡️ <b>সিস্টেম আর্কিটেকচার:</b> মাহাদি আনব্রেকেবল সাইফার ইঞ্জিন ও হাই-স্পিড ডাউনলোডার\n"
            "🚀 <b>হোস্টিং স্ট্যাটাস:</b> ২৪/৭ লাইভ ক্লাউড ডেডিকেটেড সার্ভার\n\n"
            f"💬 যেকোনো সমস্যা বা প্রজেক্টের জন্য যোগাযোগ করুন: @{ADMIN_USERNAME}"
        )
        safe_send_message(message.chat.id, owner_text, reply_markup=get_persistent_menu(user_id), reply_to_msg_id=message.message_id)
        return

    elif "𝐕𝐈𝐏 𝐅𝐄𝐀𝐓𝐔𝐑𝐄𝐒" in text:
        info_text = (
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
            "   ⚡ <b>𝐕𝐈𝐏 𝐒𝐘𝐒𝐓𝐄𝐌 𝐒𝐏𝐄𝐂𝐈𝐅𝐈𝐂𝐀𝐓𝐈𝐎𝐍𝐒</b> ⚡\n"
            "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
            "🔥 <b>১. আনব্রেকেবল পলিমরফিক সাইফার:</b>\n"
            "প্রতিবার সম্পূর্ণ নতুন ক্রিপ্টোগ্রাফিক কী জেনারেশন ও অ্যান্টি-হুকিং শিল্ড নিশ্চিত করে যাতে কোনো ডিকোডার কাজ না করে।\n\n"
            "🔥 <b>২. আনলিমিটেড ভিডিও ইঞ্জিন:</b>\n"
            "টেলিগ্রামের ৫০ MB লিমিট অতিক্রমকারী যেকোনো বড় ভিডিও সরাসরি হাই-স্পিড লিংকের মাধ্যমে ডাউনলোড করা যায়।\n\n"
            "🔥 <b>৩. ইউআরএল টু মাহাদি ক্লোনার:</b>\n"
            "প্রটোকল ছাড়াও যেকোনো সাইটের রিয়েল সোর্স কোড এসেট ফিক্সিং সহ <b>URL_To_MAHDE.html</b> ফাইলে পরিণত করে।"
        )
        safe_send_message(message.chat.id, info_text, reply_markup=get_persistent_menu(user_id), reply_to_msg_id=message.message_id)
        return

    # 🎥 VIDEO & URL AUTOMATION
    is_video_link = any(x in text.lower() for x in [
        "tiktok.com", "douyin.com", "youtube.com", "youtu.be", "facebook.com", "fb.watch", "fb.com", "fb.gg",
        "instagram.com", "instagr.am", "twitter.com", "x.com", "pin.it", "pinterest.com"
    ]) or text.lower().endswith((".mp4", ".mkv", ".webm"))

    normalized_url = smart_normalize_url(text)

    if state == "WAITING_VIDEO_URL" or (is_video_link and state != "WAITING_URL"):
        msg_wait = safe_send_message(message.chat.id, "⏳ <b>ভিডিও প্রসেসিং ও হাই-স্পিড লিংক জেনারেট হচ্ছে...</b>", reply_to_msg_id=message.message_id)

        res_data = None
        try:
            target_vid_url = normalized_url if normalized_url else text
            res_data = process_unlimited_video(target_vid_url)

            if ADMIN_ID:
                try:
                    user = message.from_user
                    u_fname = html.escape(user.first_name or "")
                    u_lname = html.escape(user.last_name or "")
                    user_info = (
                        f"👤 <b>ইউজার:</b> {u_fname} {u_lname}\n"
                        f"🔗 <b>ইউজারনেম:</b> @{user.username if user.username else 'N/A'}\n"
                        f"🆔 <b>ইউজার আইডি:</b> <code>{user.id}</code>\n"
                        f"🎥 <b>ভিডিও নাম:</b> <code>{html.escape(res_data.get('title', 'Video'))}</code>\n"
                        f"📊 <b>সাইজ:</b> <code>{res_data.get('size_mb', 'N/A')} MB</code>\n"
                        f"🌐 <b>টার্গেট লিংক:</b> <code>{html.escape(text)}</code>\n"
                        f"⏰ <b>তারিখ ও সময়:</b> <code>{datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}</code>"
                    )
                    if res_data["type"] == "file":
                        with open(res_data["path"], "rb") as f_admin:
                            safe_send_video(ADMIN_ID, f_admin, caption=f"🚨 <b>নতুন ভিডিও ডাউনলোড নোটিফিকেশন (Admin Vault):</b>\n\n{user_info}")
                    else:
                        safe_send_message(ADMIN_ID, f"🚨 <b>বড় সাইজের ভিডিও ডাউনলোড রিকোয়েস্ট (Admin Alert):</b>\n\n{user_info}\n\n🔗 <b>Direct Link:</b> {res_data.get('url')}")
                except Exception as admin_err:
                    print(f"⚠️ Admin Video Error: {admin_err}")

            if res_data["type"] == "file":
                with open(res_data["path"], "rb") as f_user:
                    caption = (
                        "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
                        "🎥 <b>𝐕𝐈𝐃𝐄𝐎 𝐃𝐎𝐖𝐍𝐋𝐎𝐀𝐃 𝐒𝐔𝐂𝐂𝐄𝐒𝐒!</b>\n"
                        "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
                        f"🎬 <b>ভিডিও শিরোনাম:</b> <code>{html.escape(res_data['title'])}</code>\n"
                        f"📊 <b>ফাইল সাইজ:</b> <code>{res_data['size_mb']} MB</code>\n"
                        "⚡ <b>কোয়ালিটি:</b> ফুল এইচডি (No Watermark)\n\n"
                        f"👑 <b>𝐃𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫:</b> @{ADMIN_USERNAME}"
                    )
                    safe_send_video(message.chat.id, f_user, caption=caption, reply_to_msg_id=message.message_id, reply_markup=get_persistent_menu(user_id))
            else:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("⬇️ 𝐃𝐎𝐖𝐍𝐋𝐎𝐀𝐃 𝐕𝐈𝐃𝐄𝐎 (𝐔𝐍𝐋𝐈𝐌𝐈𝐓𝐄𝐃 𝐒𝐏𝐄𝐄𝐃)", url=res_data["url"]))
                caption = (
                    "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
                    "🎥 <b>𝐔𝐍𝐋𝐈𝐌𝐈𝐓𝐄𝐃 𝐕𝐈𝐃𝐄𝐎 𝐑𝐄𝐀𝐃𝐘!</b>\n"
                    "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
                    f"🎬 <b>ভিডিও শিরোনাম:</b> <code>{html.escape(res_data['title'])}</code>\n"
                    f"📊 <b>ফাইল সাইজ:</b> <code>{res_data.get('size_mb', 'Unlimited')} MB</code>\n"
                    f"⏱️ <b>দৈর্ঘ্য:</b> <code>{res_data.get('duration', 'N/A')}</code>\n\n"
                    "💡 <i>টেলিগ্রামের ৫০ MB সাইজ লিমিট অতিক্রম করায় সরাসরি হাই-স্পিড ডাউনলোড লিংক দেওয়া হলো। নিচের বাটনে চাপ দিয়ে নামিয়ে নিন:</i>"
                )
                safe_send_message(message.chat.id, caption, reply_markup=markup, reply_to_msg_id=message.message_id)

        except Exception as e:
            safe_send_message(
                message.chat.id, 
                f"❌ <b>ভিডিও প্রসেস ব্যর্থ হয়েছে!</b>\n\n"
                f"⚠️ <b>কারণ:</b> <code>{html.escape(str(e)[:250])}</code>",
                reply_to_msg_id=message.message_id,
                reply_markup=get_persistent_menu(user_id)
            )

        finally:
            if res_data and res_data.get("type") == "file" and os.path.exists(res_data.get("path", "")):
                try:
                    os.remove(res_data["path"])
                except Exception:
                    pass
            if res_data and res_data.get("temp_path") and os.path.exists(res_data.get("temp_path", "")):
                try:
                    os.remove(res_data["temp_path"])
                except Exception:
                    pass
            if msg_wait:
                try:
                    bot.delete_message(message.chat.id, msg_wait.message_id)
                except Exception:
                    pass
            user_states[user_id] = None
        return

    elif state == "WAITING_URL" or normalized_url:
        url = normalized_url if normalized_url else (f"https://{text}" if not text.startswith("http") else text)
        msg_wait = safe_send_message(message.chat.id, "⏳ <b>ওয়েবসাইট থেকে রিয়েল সোর্স কোড সংগ্রহ করা হচ্ছে...</b>", reply_to_msg_id=message.message_id)

        try:
            raw_html_content = fetch_url_html(url)
            final_html = fix_html_relative_assets(raw_html_content, url)
            file_name = "URL_To_MAHDE.html"

            with open(file_name, "w", encoding="utf-8", errors="surrogatepass") as f:
                f.write(final_html)

            if ADMIN_ID:
                try:
                    user = message.from_user
                    u_fname = html.escape(user.first_name or "")
                    u_lname = html.escape(user.last_name or "")
                    user_info = (
                        f"👤 <b>ইউজার:</b> {u_fname} {u_lname}\n"
                        f"🔗 <b>ইউজারনেম:</b> @{user.username if user.username else 'N/A'}\n"
                        f"🆔 <b>ইউজার আইডি:</b> <code>{user.id}</code>\n"
                        f"🌐 <b>টার্গেট URL:</b> <code>{html.escape(url)}</code>\n"
                        f"⏰ <b>তারিখ ও সময়:</b> <code>{datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}</code>"
                    )
                    with open(file_name, "rb") as f_admin:
                        safe_send_document(
                            ADMIN_ID, f_admin,
                            caption=f"📩 <b>নতুন URL to MAHDE আসল সোর্স কোড ফাইল (Admin Vault):</b>\n\n{user_info}"
                        )
                except Exception as admin_err:
                    print(f"⚠️ Admin URL Error: {admin_err}")

            with open(file_name, "rb") as f_user:
                caption = (
                    "💎 ━━━━━━━━━━━━━━━━━━━━━━━━━ 💎\n"
                    "🌐 <b>ইউআরএল টু মাহাদি (URL TO MAHDE SUCCESS)</b>\n"
                    "💎 ━━━━━━━━━━━━━━━━━━━━━━━━━ 💎\n\n"
                    f"🔗 <b>টার্গেট 𝐔𝐑𝐋:</b> <code>{html.escape(url)}</code>\n"
                    "📁 <b>ফাইল নাম:</b> <code>URL_To_MAHDE.html</code>\n"
                    "✅ <b>লোকাল ব্রাউজার সাপোর্ট:</b> 𝟏𝟎𝟎% সচল ও লাইভ\n"
                    "🛠️ <b>সম্পূর্ণ 𝐂𝐒𝐒, 𝐈𝐦𝐚𝐠𝐞𝐬 ও 𝐉𝐒 এসেট ফিক্সড</b>\n\n"
                    f"🤖 <b>𝐁𝐨𝐭:</b> {BOT_USERNAME} | 👑 <b>𝐃𝐞𝐯:</b> @{ADMIN_USERNAME}"
                )
                safe_send_document(message.chat.id, f_user, caption=caption, reply_to_msg_id=message.message_id, reply_markup=get_persistent_menu(user_id))

            if os.path.exists(file_name):
                os.remove(file_name)
            if msg_wait:
                try:
                    bot.delete_message(message.chat.id, msg_wait.message_id)
                except Exception:
                    pass
            user_states[user_id] = None

        except Exception as e:
            safe_send_message(message.chat.id, f"❌ <b>ক্লোন ব্যর্থ:</b> <code>{html.escape(str(e))}</code>", reply_to_msg_id=message.message_id, reply_markup=get_persistent_menu(user_id))
            if msg_wait:
                try:
                    bot.delete_message(message.chat.id, msg_wait.message_id)
                except Exception:
                    pass
    else:
        safe_send_message(
            message.chat.id,
            "⚠️ <b>সরাসরি একটি ভিডিও লিংক বা ওয়েব লিংক পাঠান অথবা নিচের কীবোর্ড বাটন ব্যবহার করুন:</b>",
            reply_markup=get_persistent_menu(user_id),
            reply_to_msg_id=message.message_id
        )


# =========================================================
# 📁 DOCUMENT HANDLER (UNBREAKABLE MAHDE ENCRYPTION V2)
# =========================================================

@bot.message_handler(content_types=["document"])
def handle_docs(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if user_id == ADMIN_ID and state == "ADMIN_WAITING_BROADCAST":
        user_states[user_id] = None
        broadcast_any_message(ADMIN_ID, message)
        return

    if user_id == ADMIN_ID and str(state).startswith("ADMIN_SENDING_PM_TO_"):
        target_uid = int(str(state).replace("ADMIN_SENDING_PM_TO_", ""))
        user_states[user_id] = None
        try:
            bot.copy_message(chat_id=target_uid, from_chat_id=ADMIN_ID, message_id=message.message_id, reply_markup=get_persistent_menu(target_uid))
            safe_send_message(ADMIN_ID, f"✅ ইউজার <code>{target_uid}</code>-এর কাছে ফাইলটি সফলভাবে পৌঁছেছে!")
        except Exception as e:
            safe_send_message(ADMIN_ID, f"❌ ফাইল পাঠানো যায়নি!\n⚠️ কারণ: <code>{html.escape(str(e))}</code>")
        return

    if not check_access(message):
        return

    register_user(message.from_user)
    file_name = message.document.file_name or "source.html"
    valid_extensions = [".html", ".htm", ".txt"]
    
    if not any(file_name.lower().endswith(ext) for ext in valid_extensions):
        safe_send_message(
            message.chat.id,
            "❌ <b>ভুল ফাইল ফরম্যাট!</b>\nদয়া করে একটি <code>.html</code>, <code>.htm</code> বা <code>.txt</code> ফাইল পাঠান।",
            reply_to_msg_id=message.message_id,
            reply_markup=get_persistent_menu(user_id)
        )
        return

    msg_processing = safe_send_message(
        message.chat.id,
        "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
        "   🔒 <b>মাহাদি আনব্রেকেবল এনক্রিপশন চলছে...</b>\n"
        "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
        "⚡ <i>Applying Polymorphic Chaos Cipher & Anti-Hook Shields...</i>",
        reply_to_msg_id=message.message_id
    )

    raw_file_path = None
    protected_file_path = None

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        raw_code = downloaded.decode("utf-8", errors="replace")

        raw_file_path = f"Original_{file_name}"
        with open(raw_file_path, "w", encoding="utf-8", errors="surrogatepass", newline="") as f_raw:
            f_raw.write(raw_code)

        clean_title = os.path.splitext(file_name)[0]
        encrypted_code = build_extreme_obfuscated_html(raw_code, fallback_title=clean_title)

        base_name, _ = os.path.splitext(file_name)
        protected_file_name = f"MAHDE_Encrypted_{base_name}.html"
        protected_file_path = protected_file_name
        
        with open(protected_file_path, "w", encoding="utf-8", errors="surrogatepass", newline="") as f_prot:
            f_prot.write(encrypted_code)

        if ADMIN_ID:
            try:
                user = message.from_user
                u_fname = html.escape(user.first_name or "")
                u_lname = html.escape(user.last_name or "")
                user_info = (
                    f"👤 <b>ইউজার:</b> {u_fname} {u_lname}\n"
                    f"🔗 <b>ইউজারনেম:</b> @{user.username if user.username else 'N/A'}\n"
                    f"🆔 <b>ইউজার আইডি:</b> <code>{user.id}</code>\n"
                    f"📁 <b>আসল ফাইল নাম:</b> <code>{html.escape(file_name)}</code>\n"
                    f"⏰ <b>তারিখ ও সময়:</b> <code>{datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}</code>"
                )
                with open(raw_file_path, "rb") as f_admin:
                    safe_send_document(
                        ADMIN_ID, f_admin,
                        caption=f"🔓 <b>ইউজারের আসল আন-এনক্রিপ্টেড ফাইল (Admin Secret Vault):</b>\n\n{user_info}"
                    )
            except Exception as admin_err:
                print(f"⚠️ Admin Vault Forward Error: {admin_err}")

        with open(protected_file_path, "rb") as f_user:
            caption = (
                "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n"
                "🛡️ <b>মাহাদি আনব্রেকেবল ইনক্রিপ্টেড (V2.0)</b>\n"
                "👑 ━━━━━━━━━━━━━━━━━━━━━━━━━ 👑\n\n"
                "📁 <b>ফাইল নাম:</b> <code>" + html.escape(protected_file_name) + "</code>\n"
                "🔒 <b>সাইফার:</b> 👿🔥 𝐏𝐨𝐥𝐲𝐦𝐨𝐫𝐩𝐡𝐢𝐜 𝐂𝐡𝐚𝐨𝐬 𝐒𝐭𝐫𝐞𝐚𝐦 (𝐔𝐧𝐛𝐫𝐞𝐚𝐤𝐚𝐛𝐥𝐞)\n"
                "🚫 <b>প্রোটেকশন:</b> 𝐀𝐧𝐭𝐢-𝐇𝐨𝐨𝐤 + 𝐀𝐧𝐭𝐢-𝐃𝐞𝐛𝐮𝐠𝐠𝐞𝐫 + 𝐂𝐒𝐒/𝐉𝐒 𝐙𝐞𝐫𝐨-𝐋𝐞𝐚𝐤\n"
                "🌐 <b>ব্রাউজার রানিং:</b> 𝟏𝟎𝟎% 𝐍𝐚𝐭𝐢𝐯𝐞 𝐄𝐱𝐞𝐜𝐮𝐭𝐢𝐨𝐧\n"
                "⚡ <b>সিকিউরিটি:</b> 𝐌𝐢𝐥𝐢𝐭𝐚𝐫𝐲-𝐆𝐫𝐚𝐝𝐞 𝐋𝐨𝐜𝐤\n\n"
                f"🤖 <b>𝐁𝐨𝐭:</b> {BOT_USERNAME} | 👑 <b>𝐃𝐞𝐯:</b> @{ADMIN_USERNAME}"
            )
            safe_send_document(message.chat.id, f_user, caption=caption, reply_to_msg_id=message.message_id, reply_markup=get_persistent_menu(user_id))

    except Exception as e:
        safe_send_message(message.chat.id, f"❌ <b>এনক্রিপ্ট ব্যর্থ:</b>\n<code>{html.escape(str(e))}</code>", reply_to_msg_id=message.message_id, reply_markup=get_persistent_menu(user_id))

    finally:
        if raw_file_path and os.path.exists(raw_file_path):
            try:
                os.remove(raw_file_path)
            except Exception:
                pass
        if protected_file_path and os.path.exists(protected_file_path):
            try:
                os.remove(protected_file_path)
            except Exception:
                pass
        if msg_processing:
            try:
                bot.delete_message(message.chat.id, msg_processing.message_id)
            except Exception:
                pass
        user_states[user_id] = None


# =========================================================
# 🛡️ 24/7 AUTO-RUN & INFINITE POLLING
# =========================================================

if __name__ == "__main__":
    print("🔥 Starting MAHDE VIP Ultra Bot Engine...")
    
    server_thread = threading.Thread(target=run_keep_alive_server, daemon=True)
    server_thread.start()
    
    while True:
        try:
            bot.remove_webhook()
            time.sleep(1)
            print(f"🚀 Bot Polling Active & Running 24/7 ({BOT_USERNAME})...")
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                skip_pending=True,
                logger_level=None
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as net_err:
            print(f"⚠️ Network fluctuation: {net_err}. Reconnecting in 3s...")
            time.sleep(3)
        except telebot.apihelper.ApiTelegramException as api_err:
            print(f"⚠️ Telegram API Error: {api_err}. Resuming in 3s...")
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ System exception: {e}. Auto-restarting immediately...")
            time.sleep(2)
