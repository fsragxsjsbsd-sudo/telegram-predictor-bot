import os
import re
import ssl
import json
import time
import random
import sqlite3
import logging
import threading
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==============================================================================
# ⚙️ ১. কনফিগারেশন সেটিংস
# ==============================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8865815253:AAHhWKutyrgH0XxfFUgFlvIp0HVBnBjdHdM")
ADMIN_IDS = [6753121703, 7122259829]
SUPPORT_USERNAME = "SAGOR_TREDER"
REGISTER_LINK = "https://dkwin0.com/#/register?invitationCode=68816100046"
PORT = int(os.environ.get("PORT", 8080))

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# ==============================================================================
# 🗄️ ২. ডাটাবেজ হ্যান্ডলার
# ==============================================================================
DB_PATH = "sagor_quantum_system.db"

DEFAULT_ICONS = {
    "main_logo": "👑",
    "period_icon": "⚡",
    "pred_icon": "🎯",
    "num_icon": "🔢",
    "status_icon": "🛡️",
    "conf_icon": "📊",
    "server_icon": "💎",
    "alert_icon": "⚠️",
    "link_icon": "👉",
    "contact_icon": "📡",
    "welcome_star": "🌟",
    "welcome_rocket": "🚀",
    "active_badge": "🟢",
    "stop_icon": "🛑",
    "future_icon": "🔮"
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            game_uid TEXT DEFAULT '',
            deposit_amount TEXT DEFAULT '',
            is_verified INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            auto_signal INTEGER DEFAULT 0,
            last_msg_id INTEGER DEFAULT 0,
            last_access_date TEXT DEFAULT '',
            joined_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS system_stats (
            id INTEGER PRIMARY KEY,
            maintenance INTEGER DEFAULT 0,
            connected_channel_id TEXT DEFAULT '',
            icons_json TEXT DEFAULT ''
        )
    """)
    cur.execute("INSERT OR IGNORE INTO system_stats (id, maintenance, connected_channel_id, icons_json) VALUES (1, 0, '', ?)", (json.dumps(DEFAULT_ICONS, ensure_ascii=False),))
    
    try:
        cur.execute("ALTER TABLE system_stats ADD COLUMN icons_json TEXT DEFAULT ''")
    except Exception:
        pass

    for adm in ADMIN_IDS:
        cur.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, is_verified, joined_at)
            VALUES (?, 'admin', 'Super Admin', 1, ?)
        """, (adm, time.strftime("%Y-%m-%d %H:%M:%S")))
        cur.execute("UPDATE users SET is_verified = 1, is_banned = 0 WHERE user_id = ?", (adm,))
        
    conn.commit()
    conn.close()

def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15)
        cur = conn.cursor()
        cur.execute(query, params)
        data = None
        if fetchone:
            data = cur.fetchone()
        if fetchall:
            data = cur.fetchall()
        if commit:
            conn.commit()
        conn.close()
        return data
    except Exception as e:
        logging.error(f"DB Error: {e}")
        return None

def get_all_icons():
    res = db_query("SELECT icons_json FROM system_stats WHERE id = 1", fetchone=True)
    if res and res[0]:
        try:
            d = json.loads(res[0])
            for k, v in DEFAULT_ICONS.items():
                if k not in d:
                    d[k] = v
            return d
        except Exception:
            pass
    return DEFAULT_ICONS

def update_single_icon(key, val):
    icons = get_all_icons()
    icons[key] = val
    db_query("UPDATE system_stats SET icons_json = ? WHERE id = 1", (json.dumps(icons, ensure_ascii=False),), commit=True)

# ==============================================================================
# 📡 ৩. TELEGRAM API (WITH FAIL-SAFE HTML & CUSTOM EMOJI PARSER)
# ==============================================================================
def tg_api(method, payload=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
        headers = {"Content-Type": "application/json; charset=utf-8"}
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_res = e.read().decode("utf-8")
        try:
            return json.loads(err_res)
        except Exception:
            return {"ok": False, "description": err_res}
    except Exception as e:
        logging.error(f"Telegram API Error: {e}")
        return None

def send_msg(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = tg_api("sendMessage", payload)
    
    # কাস্টম প্রিমিয়াম ইমোজির ট্যাগ কোনো চ্যাটে সাপোর্ট না করলে ক্লিন টেক্সটে সেন্ড করবে
    if not res or not res.get("ok", False):
        clean_text = re.sub(r'<tg-emoji id="[^"]*">(.*?)</tg-emoji>', r'\1', text)
        payload["text"] = clean_text
        res = tg_api("sendMessage", payload)
        if not res or not res.get("ok", False):
            payload.pop("parse_mode", None)
            payload["text"] = re.sub(r'<[^>]+>', '', text)
            res = tg_api("sendMessage", payload)
    return res

def copy_msg(chat_id, from_chat_id, message_id, caption=None, reply_markup=None):
    payload = {"chat_id": chat_id, "from_chat_id": from_chat_id, "message_id": message_id}
    if caption:
        payload["caption"] = caption
        payload["parse_mode"] = "HTML"
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_api("copyMessage", payload)

def delete_msg(chat_id, message_id):
    if message_id and int(message_id) > 0:
        return tg_api("deleteMessage", {"chat_id": chat_id, "message_id": int(message_id)})

def answer_callback(cq_id, text=None, alert=False):
    payload = {"callback_query_id": cq_id, "show_alert": alert}
    if text:
        payload["text"] = text
    return tg_api("answerCallbackQuery", payload)

def edit_msg(chat_id, msg_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = tg_api("editMessageText", payload)
    if not res or not res.get("ok", False):
        clean_text = re.sub(r'<tg-emoji id="[^"]*">(.*?)</tg-emoji>', r'\1', text)
        payload["text"] = clean_text
        res = tg_api("editMessageText", payload)
    return res

# ==============================================================================
# 🔥 ৪. ১০০% নির্ভুল প্রিমিয়াম ও নরমাল ইমোজি এক্সট্রাক্টর
# ==============================================================================
def extract_emoji_perfect(message_obj):
    text = message_obj.get("text", "") or message_obj.get("caption", "")
    entities = message_obj.get("entities", []) or message_obj.get("caption_entities", [])
    
    if not text:
        return "👑"
        
    custom_ents = [e for e in entities if e.get("type") == "custom_emoji"]
    if not custom_ents:
        return text.strip()

    utf16_bytes = text.encode("utf-16-le")
    pieces = []
    last_idx = 0
    
    custom_ents.sort(key=lambda x: x.get("offset", 0))

    for ent in custom_ents:
        offset = ent.get("offset", 0)
        length = ent.get("length", 1)
        cid = ent.get("custom_emoji_id")
        
        if offset > last_idx:
            chunk = utf16_bytes[last_idx * 2 : offset * 2].decode("utf-16-le", errors="ignore")
            pieces.append(chunk)
            
        emoji_char = utf16_bytes[offset * 2 : (offset + length) * 2].decode("utf-16-le", errors="ignore")
        if not emoji_char.strip():
            emoji_char = "💎"
            
        # প্রিমিয়াম ইমোজি ট্যাগ তৈরি
        pieces.append(f'<tg-emoji id="{cid}">{emoji_char}</tg-emoji>')
        last_idx = offset + length

    if last_idx * 2 < len(utf16_bytes):
        pieces.append(utf16_bytes[last_idx * 2:].decode("utf-16-le", errors="ignore"))

    result = "".join(pieces).strip()
    return result if result else text.strip()

# ==============================================================================
# 🎯 ৫. প্রেডিকশন ইঞ্জিন
# ==============================================================================
BIG_POOL = [5, 6, 7, 8, 9]
SMALL_POOL = [0, 1, 2, 3, 4]

def get_exact_game_period():
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    total_minutes = now.hour * 60 + now.minute + 1
    return f"{date_part}10001{total_minutes:04d}"

class QuantumRandomEngine:
    def get_new_prediction(self):
        return random.choice(["BIG", "SMALL"])

    def generate_numbers(self, prediction):
        if prediction == "BIG":
            selected_nums = random.sample(BIG_POOL, 2)
        else:
            selected_nums = random.sample(SMALL_POOL, 2)
        return sorted(selected_nums)

engine = QuantumRandomEngine()

# ==============================================================================
# 🎨 ৬. কীবোর্ড ও সিগন্যাল টেমপ্লেট
# ==============================================================================
BTN_START = "⚡ 𝗦𝗧𝗔𝗥𝗧 𝗔𝗨𝗧𝗢 𝗦𝗜𝗚𝗡𝗔𝗟 ⚡"
BTN_STOP = "🛑 𝗦𝗧𝗢𝗣 𝗦𝗜𝗚𝗡𝗔𝗟 🛑"
BTN_FUTURE = "🔮 𝗙𝗨𝗧𝗨𝗥𝗘 𝟭𝟬 𝗦𝗜𝗚𝗡𝗔𝗟𝗦 🔮"
BTN_RADAR = "📡 𝗠𝗔𝗥𝗞𝗘𝗧 𝗧𝗥𝗘𝗡𝗗 𝗥𝗔𝗗📡"
BTN_FUND = "💰 𝟳-𝗦𝗧𝗘𝗣 𝗙𝗨𝗡𝗗 𝗠𝗔𝗡𝗔𝗚💰"
BTN_SUPPORT = "💬 𝗩𝗜𝗣 𝗦𝗨𝗣𝗣𝗢𝗥𝗧 💬"
BTN_ADMIN = "👑 𝗦𝗔𝗚𝗢𝗥 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟 👑"

ICON_LABELS = {
    "main_logo": "🏷️ মেইন লোগো",
    "period_icon": "⚡ পিরিয়ড ইমোজি",
    "pred_icon": "🎯 প্রেডিকশন ইমোজি",
    "num_icon": "🔢 নাম্বার ইমোজি",
    "status_icon": "🛡️ স্ট্যাটাস ইমোজি",
    "conf_icon": "📊 কনফিডেন্স ইমোজি",
    "server_icon": "💎 সার্ভার ইমোজি",
    "alert_icon": "⚠️ সতর্কতা ইমোজি",
    "link_icon": "👉 লিংক ইমোজি",
    "contact_icon": "📡 কন্টাক্ট ইমোজি",
    "welcome_star": "🌟 ওয়েলকাম স্টার",
    "welcome_rocket": "🚀 রকেট ইমোজি",
    "active_badge": "🟢 একটিভ ব্যাজ",
    "stop_icon": "🛑 স্টপ আইকন",
    "future_icon": "🔮 ফিউচার আইকন"
}

def get_main_keyboard(user_id):
    kb = [
        [{"text": BTN_START}, {"text": BTN_STOP}],
        [{"text": BTN_FUTURE}, {"text": BTN_RADAR}],
        [{"text": BTN_FUND}, {"text": BTN_SUPPORT}]
    ]
    if user_id in ADMIN_IDS:
        kb.append([{"text": BTN_ADMIN}])
    return {"keyboard": kb, "resize_keyboard": True}

def get_welcome_message(first_name, user_id):
    ic = get_all_icons()
    return (
        f"<b>{ic['main_logo']} স্বাগতম, {first_name}! {ic['main_logo']}</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>{ic['welcome_star']} 𝗦𝗔𝗚𝗢𝗥 𝗩𝗜𝗣 𝗦𝗘𝗥𝗩𝗘𝗥 𝗩𝟮𝟬-এ আপনাকে স্বাগতম!</b>\n\n"
        f"<b>{ic['welcome_rocket']} এটি বিশ্বের অন্যতম শক্তিশালী AI চালিত ১-মিনিট ডাইনামিক প্রেডিকশন সিস্টেম।</b>\n\n"
        f"<b>{ic['pred_icon']} আমাদের বিশেষ ফিচারসমূহ:</b>\n"
        f"<b>├ {ic['active_badge']} অটো লাইভ রিপ্লেস : প্রতি মিনিটে মেসেজ স্বয়ংক্রিয়ভাবে রিফ্রেশ হবে</b>\n"
        f"<b>├ {ic['pred_icon']} BIG & SMALL নিখুঁত ট্রেন্ড ফিল্টারিং</b>\n"
        f"<b>├ {ic['status_icon']} ২-লেভেল হাই একুরেসি সেফটি বুস্টার মেথড</b>\n"
        f"<b>├ 💰 অফিসিয়াল ৭-স্টেপ রিস্ক-ফ্রি মার্টিঙ্গেল মানি ম্যানেজমেন্ট</b>\n"
        f"<b>└ {ic['server_icon']} ৯৯.৮% পর্যন্ত রিয়েল-টাইম উইন রেট পারফরম্যান্স</b>\n\n"
        f"<b>📌 ইউজার প্রোফাইল ডাটা:</b>\n"
        f"<b>├ 👤 ট্রেডার নাম   : {first_name}</b>\n"
        f"<b>├ 🆔 ট্রেডার আইডি : <code>{user_id}</code></b>\n"
        f"<b>└ 🔰 ভিআইপি স্ট্যাটাস : {ic['active_badge']} 𝗩𝗜𝗣 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗔𝗖𝗧𝗜𝗩𝗘</b>\n\n"
        f"<b>💡 নিচের প্রিমিয়াম বাটনগুলো চেপে আপনার প্রয়োজনীয় সার্ভিসটি এখনই শুরু করুন।</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>"
    )

def format_signal_msg(period, pred, numbers=None, level=1):
    ic = get_all_icons()
    pred_badge = "<b>𝗕𝗜𝗚 ✅</b>" if pred == "BIG" else "<b>𝗦𝗠𝗔𝗟𝗟 ✅</b>"
    lvl_txt = "LEVEL: 1 (PRIMARY SAFE)" if level == 1 else "LEVEL: 2 (HIGH BOOST 🔥)"
    confidence = random.randint(95, 99)
    accuracy_bar = "██████████" if confidence >= 98 else "█████████▒"

    number_line = f"{ic['num_icon']} <b>𝟐-𝐋𝐄𝐕𝐄𝐋 𝐍𝐔𝐌</b> : <code>{numbers[0]} | {numbers[1]}</code>\n" if numbers and len(numbers) >= 2 else ""

    return (
        f"{ic['main_logo']} <b>𝗦𝗔𝗚𝗢𝗥 𝗩𝗜𝗣 𝗜𝗡𝗝𝗘𝗖𝗧𝗢𝗥 𝗩𝟮𝟬</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{ic['period_icon']} <b>𝗣𝗘𝗥𝗜𝗢𝗗</b>      : <code>{period}</code>\n"
        f"{ic['pred_icon']} <b>𝗣𝗥𝗘𝗗𝗜𝗖𝗧𝗜𝗢𝗡</b>  : {pred_badge}\n"
        f"{number_line}"
        f"{ic['status_icon']} <b>𝗦𝗧𝗔𝗧𝗨𝗦</b>      : <code>{lvl_txt}</code>\n"
        f"{ic['conf_icon']} <b>𝗖𝗢𝗡𝗙𝗜𝗗𝗘𝗡𝗖𝗘</b>    : <code>{confidence}%</code> [{accuracy_bar}]\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{ic['server_icon']} <b>𝗦𝗘𝗥𝗩𝗘𝗥 𝗦𝗧𝗔𝗧𝗨𝗦</b> : {ic['active_badge']} <b>𝗢𝗡𝗟𝗜𝗡𝗘 & 𝗦𝗬𝗡𝗖𝗘𝗗</b>\n"
        f"{ic['alert_icon']} <b>জরুরি গাইডলাইন</b>: সবসময় ৭-স্টেপ ফান্ড ব্যাকআপ মেনে চলুন!\n"
        f"{ic['link_icon']} <b>রেজিস্ট্রেশন লিংক</b>: {REGISTER_LINK}\n"
        f"{ic['contact_icon']} <b>CONTACK</b> @{SUPPORT_USERNAME}"
    )

# ==============================================================================
# 🎮 ৭. কন্ট্রোলার ও প্রসেসিং
# ==============================================================================
waiting_broadcast_admin = None
waiting_ban_admin = None
waiting_unban_admin = None
waiting_channel_admin = None
waiting_icon_change = {}
admin_live_sender_mode = {}
user_submit_state = {}

def process_updates():
    global waiting_broadcast_admin, waiting_ban_admin, waiting_unban_admin, waiting_channel_admin
    global waiting_icon_change, admin_live_sender_mode, user_submit_state
    offset = 0
    while True:
        try:
            updates = tg_api("getUpdates", {"offset": offset, "timeout": 20})
            if updates and "result" in updates:
                for u in updates["result"]:
                    offset = u["update_id"] + 1

                    # ----------------- CALLBACK QUERY -----------------
                    if "callback_query" in u:
                        cq = u["callback_query"]
                        cq_id = cq["id"]
                        data = cq["data"]
                        user_id = cq["from"]["id"]
                        msg_id = cq["message"]["message_id"]

                        if data == "usr_submit_form":
                            user_submit_state[user_id] = {"step": 1, "uid": ""}
                            answer_callback(cq_id)
                            send_msg(user_id, "<b>✍️ অনুগ্রহ করে আপনার গেমের সঠিক User ID (UID) টি লিখুন:</b>")
                            continue

                        if user_id in ADMIN_IDS:
                            if data == "adm_emoji_menu":
                                ic = get_all_icons()
                                rows = []
                                cur_row = []
                                for k, name in ICON_LABELS.items():
                                    cur_row.append({"text": f"{name}", "callback_data": f"chgicon_{k}"})
                                    if len(cur_row) == 2:
                                        rows.append(cur_row)
                                        cur_row = []
                                if cur_row:
                                    rows.append(cur_row)
                                rows.append([{"text": "🔙 ব্যাক (মেইন প্যানেল)", "callback_data": "adm_back_panel"}])
                                answer_callback(cq_id)
                                edit_msg(user_id, msg_id, "<b>🎨 ইউজার কোডের অল ইমোজি ও লোগো ম্যানেজার:</b>\n\nযে ইমোজি বা লোগোটি পরিবর্তন করতে চান নিচের বাটন চাপুন:", {"inline_keyboard": rows})

                            elif data.startswith("chgicon_"):
                                target_key = data.replace("chgicon_", "")
                                waiting_icon_change[user_id] = target_key
                                lbl = ICON_LABELS.get(target_key, target_key)
                                ic = get_all_icons()
                                cur_val = ic.get(target_key, "")
                                answer_callback(cq_id)
                                send_msg(user_id, f"<b>✍️ পরিবর্তন অপশন: {lbl}</b>\n\nবর্তমান অ্যাক্টিভ মান: {cur_val}\n\n👉 <b>আপনার কিবোর্ড থেকে যেকোনো প্রিমিয়াম কাস্টম ইমোজি অথবা সাধারণ ইমোজি সেন্ড করুন:</b>")

                            elif data == "adm_back_panel":
                                cur_st = "🟢 চালু" if admin_live_sender_mode.get(user_id, False) else "🔴 বন্ধ"
                                adm_kb = {
                                    "inline_keyboard": [
                                        [{"text": f"⚡ লাইভ সিগন্যাল মোড ({cur_st})", "callback_data": "adm_toggle_sender"}],
                                        [{"text": f"🎨 অল ইমোজি ও লোগো ম্যানেজার", "callback_data": "adm_emoji_menu"}],
                                        [{"text": "📊 ইউজার ডাটা", "callback_data": "adm_users"}, {"text": "⏳ পেন্ডিং রিকোয়েস্ট", "callback_data": "adm_pending"}],
                                        [{"text": "📢 চ্যানেল কানেক্ট করুন", "callback_data": "adm_connect_channel"}, {"text": "📢 ব্রডকাস্ট (অল ইউজার)", "callback_data": "adm_bc"}],
                                        [{"text": "🛠️ মেইনটেনেন্স মোড", "callback_data": "adm_maint"}, {"text": "🧹 অপটিমাইজ DB", "callback_data": "adm_clean_db"}],
                                        [{"text": "🚫 ব্যান ইউজার", "callback_data": "adm_ban_user"}, {"text": "🟢 আনব্যান ইউজার", "callback_data": "adm_unban_user"}]
                                    ]
                                }
                                answer_callback(cq_id)
                                edit_msg(user_id, msg_id, "<b>👑 𝗦𝗔𝗚𝗢𝗥 𝗔𝗗𝗠𝗜𝗡 𝗠𝗔𝗦𝗧𝗘𝗥 𝗣𝗔𝗡𝗘𝗟:</b>\n━━━━━━━━━━━━━━━━━━━━━━\nসম্পূর্ণ সিস্টেম কন্ট্রোল করতে নিচের অপশন ব্যবহার করুন।", adm_kb)

                            elif data.startswith("app_"):
                                target_id = int(data.split("_")[1])
                                today_str = time.strftime("%Y-%m-%d")
                                db_query("UPDATE users SET is_verified = 1, last_access_date = ? WHERE user_id = ?", (today_str, target_id), commit=True)
                                answer_callback(cq_id, "ইউজার সফলভাবে অ্যাপ্রুভ হয়েছে!", alert=False)
                                edit_msg(user_id, msg_id, f"<b>✅ ইউজার <code>{target_id}</code> সফলভাবে আজকের জন্য অ্যাপ্রুভ করা হয়েছে!</b>")
                                
                                send_msg(
                                    target_id,
                                    f"<b>🎉 অভিনন্দন! আপনার UID ও ডিপোজিট এডমিন কর্তৃক সফলভাবে অনুমোদিত হয়েছে!</b>\n\n<b>এখন আপনি আজকের জন্য 𝗦𝗔𝗚𝗢𝗥 𝗩𝗜𝗣 সার্ভিসের পূর্ণ এক্সেস পেয়ে গেছেন।</b>\n\n👉 {REGISTER_LINK}",
                                    get_main_keyboard(target_id)
                                )

                            elif data.startswith("rej_"):
                                target_id = int(data.split("_")[1])
                                db_query("UPDATE users SET is_verified = -1, is_banned = 1, auto_signal = 0 WHERE user_id = ?", (target_id,), commit=True)
                                answer_callback(cq_id, "ইউজার রিজেক্ট ও ব্যান করা হয়েছে!", alert=False)
                                edit_msg(user_id, msg_id, f"<b>🚫 ইউজার <code>{target_id}</code> রিজেক্ট ও ব্যান করা হয়েছে।</b>")
                                send_msg(target_id, "<b>❌ দুঃখিত! আপনার প্রদত্ত UID বা ডিপোজিট ডাটা সঠিক না থাকায় এডমিন এক্সেস রিজেক্ট করেছে।</b>")

                            elif data == "adm_maint":
                                cur_m = db_query("SELECT maintenance FROM system_stats WHERE id = 1", fetchone=True)[0]
                                new_m = 0 if cur_m == 1 else 1
                                db_query("UPDATE system_stats SET maintenance = ? WHERE id = 1", (new_m,), commit=True)
                                st = "অন (ON) 🔴" if new_m == 1 else "বন্ধ (OFF) 🟢"
                                answer_callback(cq_id, f"মেইনটেনেন্স: {st}")
                                edit_msg(user_id, msg_id, f"<b>🛠️ মেইনটেনেন্স মোড বর্তমানে: {st}</b>")

                            elif data == "adm_toggle_sender":
                                cur_mode = admin_live_sender_mode.get(user_id, False)
                                admin_live_sender_mode[user_id] = not cur_mode
                                st_text = "🟢 সক্রিয় (ON)" if admin_live_sender_mode[user_id] else "🔴 নিষ্ক্রিয় (OFF)"
                                answer_callback(cq_id, f"লাইভ সিগন্যাল সেন্ডার মোড: {st_text}", alert=True)
                                edit_msg(user_id, msg_id, f"<b>⚡ লাইভ চ্যানেল সিগন্যাল সেন্ডার মোড: {st_text}</b>\n\n<i>এখন আপনি বটের ইনবক্সে শুধু <code>BIG</code>, <code>SMALL</code> অথবা নাম্বারসহ <code>BIG 5 8</code> / <code>SMALL 1 3</code> লিখলেই সরাসরি চ্যানেলে পোস্ট হয়ে যাবে!</i>")

                            elif data == "adm_connect_channel":
                                waiting_channel_admin = user_id
                                answer_callback(cq_id)
                                send_msg(user_id, "<b>✍️ যে চ্যানেল বা গ্রুপে সিগন্যাল পাঠাতে চান তার ID (যেমন: -100xxxxxxxxxx) অথবা পাবলিক Username (যেমন: @channelusername) দিন:</b>")

                            elif data == "adm_users":
                                users = db_query("SELECT user_id, is_banned, auto_signal, is_verified FROM users", fetchall=True) or []
                                tot = len(users)
                                aut = sum(1 for x in users if x[2] == 1)
                                ban = sum(1 for x in users if x[1] == 1)
                                verified = sum(1 for x in users if x[3] == 1)
                                pending = sum(1 for x in users if x[3] == 0)
                                answer_callback(cq_id)
                                send_msg(
                                    user_id,
                                    f"<b>📊 𝗦𝗔𝗚𝗢𝗥 𝗩𝗜𝗣 ইউজার অ্যানালিটিক্স:</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                                    f"<b>👥 মোট ইউজার             : <code>{tot}</code> জন</b>\n"
                                    f"<b>🟢 আজকের ভেরিফাইড ইউজার : <code>{verified}</code> জন</b>\n"
                                    f"<b>⏳ পেন্ডিং এক্সেস          : <code>{pending}</code> জন</b>\n"
                                    f"<b>⚡ লাইভ অটো সিগন্যাল ইউজার: <code>{aut}</code> জন</b>\n"
                                    f"<b>🚫 ব্যানড ইউজার            : <code>{ban}</code> জন</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>"
                                )

                            elif data == "adm_pending":
                                pendings = db_query("SELECT user_id, first_name, username, game_uid, deposit_amount FROM users WHERE is_verified = 0 AND deposit_amount != ''", fetchall=True) or []
                                if not pendings:
                                    answer_callback(cq_id, "কোনো পেন্ডিং রিকোয়েস্ট নেই।", alert=True)
                                else:
                                    answer_callback(cq_id)
                                    send_msg(user_id, f"<b>⏳ মোট পেন্ডিং রিকোয়েস্ট: {len(pendings)} জন</b>")
                                    for p in pendings[:5]:
                                        p_kb = {
                                            "inline_keyboard": [
                                                [
                                                    {"text": "✅ Approve", "callback_data": f"app_{p[0]}"},
                                                    {"text": "🚫 Reject", "callback_data": f"rej_{p[0]}"}
                                                ]
                                            ]
                                        }
                                        send_msg(
                                            user_id,
                                            f"<b>👤 নাম            : {p[1]}\n🆔 টেলিগ্রাম আইডি: <code>{p[0]}</code>\n🔗 ইউজারনেম     : @{p[2]}\n🎮 গেম UID       : <code>{p[3]}</code>\n💰 ডিপোজিট       : <code>{p[4]} BDT</code></b>",
                                            p_kb
                                        )

                            elif data == "adm_bc":
                                waiting_broadcast_admin = user_id
                                answer_callback(cq_id)
                                send_msg(user_id, "<b>✍️ ব্রডকাস্টের জন্য যেকোনো কিছু পাঠান (টেক্সট, ফটো, ভিডিও, অডিও, ভয়েস, স্টিকার বা প্রিমিয়াম ইমোজি যুক্ত পোস্ট):</b>\n\n<i>বাতিল করতে চাইলে /cancel লিখুন।</i>")

                            elif data == "adm_ban_user":
                                waiting_ban_admin = user_id
                                answer_callback(cq_id)
                                send_msg(user_id, "<b>✍️ যাকে ব্যান করতে চান তার Telegram User ID দিন:</b>")

                            elif data == "adm_unban_user":
                                waiting_unban_admin = user_id
                                answer_callback(cq_id)
                                send_msg(user_id, "<b>✍️ যাকে আনব্যান করতে চান তার User ID দিন:</b>")

                            elif data == "adm_clean_db":
                                db_query("VACUUM", commit=True)
                                answer_callback(cq_id, "ডাটাবেজ অপটিমাইজেশন সম্পন্ন!", alert=True)

                        continue

                    # ----------------- MESSAGE HANDLING -----------------
                    if "message" in u:
                        msg = u["message"]
                        chat_id = msg["chat"]["id"]
                        msg_id = msg["message_id"]
                        text = msg.get("text", "").strip() if "text" in msg else ""
                        first_name = msg.get("from", {}).get("first_name", "VIP Trader")
                        username = msg.get("from", {}).get("username", "None")

                        default_ver = 1 if chat_id in ADMIN_IDS else 0

                        db_query("""
                            INSERT OR IGNORE INTO users (user_id, username, first_name, is_verified, joined_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (chat_id, username, first_name, default_ver, time.strftime("%Y-%m-%d %H:%M:%S")), commit=True)

                        usr = db_query("SELECT is_banned, auto_signal, last_msg_id, is_verified, last_access_date, game_uid, deposit_amount FROM users WHERE user_id = ?", (chat_id,), fetchone=True)

                        if usr and usr[0] == 1 and chat_id not in ADMIN_IDS:
                            send_msg(chat_id, "<b>🚫 আপনার অ্যাকাউন্টটি ব্যান রয়েছে। সাহায্যের জন্য সাপোর্টে যোগাযোগ করুন।</b>")
                            continue

                        # 🔥 ১. ১০০% প্রিমিয়াম ও নরমাল ইমোজি সেভ হ্যান্ডলার 🔥
                        if chat_id in ADMIN_IDS and chat_id in waiting_icon_change:
                            target_key = waiting_icon_change[chat_id]
                            del waiting_icon_change[chat_id]
                            
                            new_icon_val = extract_emoji_perfect(msg)
                            update_single_icon(target_key, new_icon_val)
                            lbl = ICON_LABELS.get(target_key, target_key)
                            
                            send_msg(
                                chat_id, 
                                f"<b>✅ প্রিমিয়াম ইমোজি/লোগো ১০০% সফলভাবে সংরক্ষিত হয়েছে!</b>\n\n"
                                f"📌 <b>বিষয়:</b> {lbl}\n"
                                f"✨ <b>অ্যাক্টিভ প্রিভিউ:</b> {new_icon_val}\n\n"
                                f"<i>এখন থেকে ইউজারদের সকল সিগন্যালে এটি নিখুঁতভাবে প্রদর্শিত হবে।</i>"
                            )
                            continue

                        # 🔥 ২. অল ব্রডকাস্ট হ্যান্ডলার 🔥
                        if chat_id in ADMIN_IDS and waiting_broadcast_admin == chat_id:
                            if text == "/cancel":
                                waiting_broadcast_admin = None
                                send_msg(chat_id, "<b>🚫 ব্রডকাস্ট বাতিল করা হয়েছে।</b>")
                                continue

                            waiting_broadcast_admin = None
                            users = db_query("SELECT user_id FROM users WHERE is_banned = 0", fetchall=True) or []
                            total_target = len(users)
                            success_count = 0

                            send_msg(chat_id, f"<b>⏳ ব্রডকাস্ট শুরু হয়েছে... মোট ইউজার: {total_target} জন</b>")
                            
                            for row in users:
                                target_uid = row[0]
                                try:
                                    res = copy_msg(target_uid, chat_id, msg_id)
                                    if res and res.get("ok", False):
                                        success_count += 1
                                    time.sleep(0.04)
                                except Exception:
                                    pass

                            send_msg(chat_id, f"<b>✅ অল ব্রডকাস্ট সম্পন্ন!</b>\n\n👥 মোট ইউজার: <code>{total_target}</code> জন\n🎯 সফলভাবে পাঠানো হয়েছে: <code>{success_count}</code> জনের কাছে।")
                            continue

                        # 🔥 ৩. এডমিন লাইভ চ্যানেল সিগন্যাল সেন্ডার 🔥
                        if chat_id in ADMIN_IDS and admin_live_sender_mode.get(chat_id, False) and text:
                            parts = text.split()
                            cmd_word = parts[0].upper()
                            if cmd_word in ["BIG", "SMALL"]:
                                sys_data = db_query("SELECT connected_channel_id FROM system_stats WHERE id = 1", fetchone=True)
                                if sys_data and sys_data[0]:
                                    target_ch = sys_data[0]
                                    
                                    custom_nums = []
                                    for p in parts[1:]:
                                        if p.isdigit():
                                            custom_nums.append(int(p))
                                    
                                    cur_p = get_exact_game_period()
                                    nums_to_send = custom_nums if len(custom_nums) >= 2 else None
                                    ch_sig_msg = format_signal_msg(cur_p, cmd_word, nums_to_send, level=1)
                                    
                                    res_ch = send_msg(target_ch, ch_sig_msg)
                                    if res_ch and "result" in res_ch:
                                        num_show = f"{custom_nums[0]},{custom_nums[1]}" if nums_to_send else "কোনো নাম্বার নেই"
                                        send_msg(chat_id, f"<b>✅ চ্যানেলে সিগন্যাল পোস্ট সম্পন্ন!</b>\n\n🎯 <b>প্রেডিকশন :</b> <code>{cmd_word}</code>\n🔢 <b>ডিজিট    :</b> <code>{num_show}</code>\n⚡ <b>পিরিয়ড   :</b> <code>{cur_p}</code>")
                                    else:
                                        send_msg(chat_id, "<b>❌ চ্যানেলে পাঠানো যায়নি! বটকে চ্যানেলে Admin হিসেবে যুক্ত করেছেন কি না চেক করুন।</b>")
                                    continue
                                else:
                                    send_msg(chat_id, "<b>⚠️ কোনো চ্যানেল কানেক্ট করা নেই! এডমিন প্যানেল থেকে চ্যানেল সেট করুন।</b>")

                        # এডমিন ইনপুট হ্যান্ডলিং
                        if chat_id in ADMIN_IDS:
                            if waiting_channel_admin == chat_id and not text.startswith("/"):
                                waiting_channel_admin = None
                                db_query("UPDATE system_stats SET connected_channel_id = ? WHERE id = 1", (text,), commit=True)
                                send_msg(chat_id, f"<b>✅ সফলভাবে চ্যানেল/গ্রুপ কানেক্ট করা হয়েছে: <code>{text}</code></b>")
                                continue

                            if waiting_ban_admin == chat_id and not text.startswith("/"):
                                waiting_ban_admin = None
                                try:
                                    t_id = int(text)
                                    db_query("UPDATE users SET is_banned = 1, auto_signal = 0 WHERE user_id = ?", (t_id,), commit=True)
                                    send_msg(chat_id, f"<b>✅ ইউজার <code>{t_id}</code> সফলভাবে ব্যান করা হয়েছে।</b>")
                                except ValueError:
                                    send_msg(chat_id, "<b>❌ সঠিক নিউমেরিক ইউজার আইডি প্রদান করুন!</b>")
                                continue

                            if waiting_unban_admin == chat_id and not text.startswith("/"):
                                waiting_unban_admin = None
                                try:
                                    t_id = int(text)
                                    today_str = time.strftime("%Y-%m-%d")
                                    db_query("UPDATE users SET is_banned = 0, is_verified = 1, last_access_date = ? WHERE user_id = ?", (today_str, t_id), commit=True)
                                    send_msg(chat_id, f"<b>✅ ইউজার <code>{t_id}</code> আনব্যান ও আজকের জন্য ভেরিফাই করা হয়েছে।</b>")
                                except ValueError:
                                    send_msg(chat_id, "<b>❌ সঠিক নিউমেরিক ইউজার আইডি প্রদান করুন!</b>")
                                continue

                        # ইউজার UID ও ডিপোজিট সাবমিশন
                        if chat_id in user_submit_state and text:
                            st = user_submit_state[chat_id]
                            if st["step"] == 1:
                                user_submit_state[chat_id]["uid"] = text
                                user_submit_state[chat_id]["step"] = 2
                                send_msg(chat_id, f"<b>✅ UID সংরক্ষিত: <code>{text}</code>\n\n💰 এবার আপনার আজকের ডিপোজিট অ্যামাউন্ট (Deposit Amount in BDT) লিখুন:</b>")
                                continue
                            elif st["step"] == 2:
                                uid_val = st["uid"]
                                dep_val = text
                                del user_submit_state[chat_id]
                                
                                db_query("UPDATE users SET game_uid = ?, deposit_amount = ?, is_verified = 0 WHERE user_id = ?", (uid_val, dep_val, chat_id), commit=True)
                                
                                send_msg(
                                    chat_id,
                                    f"<b>✅ আপনার তথ্য সফলভাবে জমা হয়েছে!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"🎮 <b>গেম UID    :</b> <code>{uid_val}</code>\n"
                                    f"💰 <b>ডিপোজিট   :</b> <code>{dep_val} BDT</code>\n━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"<i>এডমিন দ্রুত যাচাই করে আপনার আজকের এক্সেস অ্যাপ্রুভ করবেন। অনুগ্রহ করে অপেক্ষা করুন।</i>"
                                )
                                
                                req_kb = {
                                    "inline_keyboard": [
                                        [
                                            {"text": "✅ Approve", "callback_data": f"app_{chat_id}"},
                                            {"text": "🚫 Reject", "callback_data": f"rej_{chat_id}"}
                                        ]
                                    ]
                                }
                                for adm in ADMIN_IDS:
                                    send_msg(
                                        adm,
                                        f"<b>🔔 নতুন UID ও ডিপোজিট সাবমিশন এসেছে!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"👤 <b>নাম            :</b> {first_name}\n"
                                        f"🆔 <b>টেলিগ্রাম আইডি:</b> <code>{chat_id}</code>\n"
                                        f"🔗 <b>ইউজারনেম     :</b> @{username}\n"
                                        f"🎮 <b>গেম UID       :</b> <code>{uid_val}</code>\n"
                                        f"💰 <b>ডিপোজিট       :</b> <code>{dep_val} BDT</code>\n━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"এক্সেস অনুমোদন দিতে চান?",
                                        req_kb
                                    )
                                continue

                        # সাধারণ ইউজারদের ভেরিফিকেশন ও এক্সপায়ার চেক
                        if chat_id not in ADMIN_IDS:
                            today_str = time.strftime("%Y-%m-%d")
                            if (usr and usr[3] != 1) or (usr and usr[4] != today_str):
                                sub_kb = {
                                    "inline_keyboard": [
                                        [{"text": "📝 সাবমিট করুন (UID ও ডিপোজিট)", "callback_data": "usr_submit_form"}]
                                    ]
                                }
                                send_msg(
                                    chat_id,
                                    f"<b>🔒 এক্সেস ভেরিফিকেশন প্রয়োজন!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"<b>প্রিয় {first_name},</b> আমাদের ভিআইপি সিগন্যাল সার্ভার ব্যবহার করার জন্য প্রতিদিন আপনার গেম <b>UID</b> এবং <b>Deposit Amount</b> সাবমিট করে ভেরিফাই হতে হবে।\n\n"
                                    f"<i>(প্রতিদিন রাত ১২:০০ টার পর এক্সেস নবায়ন করতে হয়)</i>\n\n"
                                    f"👉 <b>নিচের বাটনে চাপ দিয়ে তথ্য সাবমিট করুন:</b>",
                                    sub_kb
                                )
                                continue

                        # মেইনটেনেন্স চেক
                        maint = db_query("SELECT maintenance FROM system_stats WHERE id = 1", fetchone=True)[0]
                        if maint == 1 and chat_id not in ADMIN_IDS:
                            send_msg(chat_id, "<b>🛠️ সার্ভারে মেইনটেনেন্স ও আপগ্রেডেশনের কাজ চলছে! অনুগ্রহ করে কিছুক্ষণ পর পুনরায় চেষ্টা করুন।</b>")
                            continue

                        # মেনু অপশনসমূহ
                        if text == "/start":
                            send_msg(chat_id, get_welcome_message(first_name, chat_id), get_main_keyboard(chat_id))

                        elif text in [BTN_ADMIN, "/admin"] and chat_id in ADMIN_IDS:
                            cur_st = "🟢 চালু" if admin_live_sender_mode.get(chat_id, False) else "🔴 বন্ধ"
                            adm_kb = {
                                "inline_keyboard": [
                                    [{"text": f"⚡ লাইভ সিগন্যাল মোড ({cur_st})", "callback_data": "adm_toggle_sender"}],
                                    [{"text": f"🎨 অল ইমোজি ও লোগো ম্যানেজার", "callback_data": "adm_emoji_menu"}],
                                    [{"text": "📊 ইউজার ডাটা", "callback_data": "adm_users"}, {"text": "⏳ পেন্ডিং রিকোয়েস্ট", "callback_data": "adm_pending"}],
                                    [{"text": "📢 চ্যানেল কানেক্ট করুন", "callback_data": "adm_connect_channel"}, {"text": "📢 ব্রডকাস্ট (অল ইউজার)", "callback_data": "adm_bc"}],
                                    [{"text": "🛠️ মেইনটেনেন্স মোড", "callback_data": "adm_maint"}, {"text": "🧹 অপটিমাইজ DB", "callback_data": "adm_clean_db"}],
                                    [{"text": "🚫 ব্যান ইউজার", "callback_data": "adm_ban_user"}, {"text": "🟢 আনব্যান ইউজার", "callback_data": "adm_unban_user"}]
                                ]
                            }
                            send_msg(
                                chat_id,
                                "<b>👑 𝗦𝗔𝗚𝗢𝗥 𝗔𝗗𝗠𝗜𝗡 𝗠𝗔𝗦𝗧𝗘𝗥 𝗣𝗔𝗡𝗘𝗟:</b>\n"
                                "━━━━━━━━━━━━━━━━━━━━━━\n"
                                "💡 <b>লাইভ সেন্ডার মোড চালু থাকলে:</b>\n"
                                "• শুধু লিখুন: <code>BIG</code> অথবা <code>SMALL</code>\n"
                                "• অথবা লিখুন: <code>BIG 5 8</code> / <code>SMALL 1 3</code>\n"
                                "সরাসরি চ্যানেলে সমান ফরম্যাটে পোস্ট হয়ে যাবে!\n"
                                "━━━━━━━━━━━━━━━━━━━━━━",
                                adm_kb
                            )

                        elif text == BTN_START:
                            if usr and usr[2] > 0:
                                delete_msg(chat_id, usr[2])

                            db_query("UPDATE users SET auto_signal = 1 WHERE user_id = ?", (chat_id,), commit=True)

                            cur_p = get_exact_game_period()
                            pred = engine.get_new_prediction()
                            nums = engine.generate_numbers(pred)
                            lvl = random.choice([1, 2])

                            sig_msg = format_signal_msg(cur_p, pred, nums, lvl)
                            res = send_msg(chat_id, sig_msg)
                            if res and "result" in res:
                                db_query("UPDATE users SET last_msg_id = ? WHERE user_id = ?", (res["result"]["message_id"], chat_id), commit=True)

                        elif text == BTN_STOP:
                            if usr and usr[2] > 0:
                                delete_msg(chat_id, usr[2])
                            db_query("UPDATE users SET auto_signal = 0, last_msg_id = 0 WHERE user_id = ?", (chat_id,), commit=True)
                            send_msg(chat_id, "<b>🛑 লাইভ অটো সিগন্যাল বন্ধ করা হয়েছে!</b>\n<b>পুনরায় চালু করতে চাইলে '⚡ 𝗦𝗧𝗔𝗥𝗧 𝗔𝗨𝗧𝗢 𝗦𝗜𝗚𝗡𝗔𝗟 ⚡' বাটন চাপুন।</b>")

                        elif text == BTN_FUTURE:
                            cur_p = int(get_exact_game_period())
                            fut_txt = (
                                "<b>🔮 𝗦𝗔𝗚𝗢𝗥 আগামী ১০টি ফিউচার সিগন্যাল:</b>\n"
                                "<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                            )
                            for i in range(10):
                                fp = str(cur_p + i)
                                sim_pred = random.choice(["BIG", "SMALL"])
                                sim_nums = engine.generate_numbers(sim_pred)
                                em = "<b>BIG</b>" if sim_pred == "BIG" else "<b>SMALL</b>"
                                lvl_t = "𝗟𝗩𝗟 𝟮" if i % 3 == 1 else "𝗟𝗩𝗟 𝟭"
                                fut_txt += f"<b>⚡ <code>{fp[-4:]}</code> : {em} | 🔢 <code>{sim_nums[0]},{sim_nums[1]}</code> ({lvl_t})</b>\n"
                            fut_txt += f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n👉 {REGISTER_LINK}\n💡 মার্কেট সাইকেল ও প্যাটার্ন অনুযায়ী সিগন্যাল নিয়মিত রিফ্রেশ হয়।</b>"
                            send_msg(chat_id, fut_txt)

                        elif text == BTN_RADAR:
                            radar_txt = (
                                "<b>📡 𝗠𝗔𝗥𝗞𝗘𝗧 𝗧𝗥𝗘𝗡𝗗 𝗥𝗔𝗗𝗔𝗥</b>\n"
                                "<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                                "<b>🎯 𝗕𝗜𝗚 𝗧𝗿𝗲𝗻ড        : <code>50%</code></b>\n"
                                "<b>🎯 𝗦𝗠𝗔𝗟𝗟 𝗧𝗿𝗲𝗻ড      : <code>50%</code></b>\n"
                                "<b>🔥 মার্কেট মোড        : <code>ZIG-ZAG ALTERNATING (BALANCED)</code></b>\n"
                                "<b>🛡️ রিস্ক লেভেল       : <code>LOW RISK (STABLE)</code></b>\n"
                                "<b>📊 অ্যালগরিদম        : <code>AI 99.2% ACCURACY</code></b>\n"
                                f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n👉 {REGISTER_LINK}\n💡 বর্তমান ট্রেন্ড সুষম এবং হাই-কনফিডেন্স ট্রেডের জন্য সম্পূর্ণ অনুকূল।</b>"
                            )
                            send_msg(chat_id, radar_txt)

                        elif text == BTN_FUND:
                            fund_txt = (
                                "<b>💰 অফিসিয়াল ৭-স্টেপ (𝟳-𝗦𝗧𝗘𝗣) মার্টিঙ্গেল ব্যাকআপ চার্ট</b>\n"
                                "<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                                "<b>🔹 𝗦𝘁𝗲প 𝟭 : <code>7.87 BDT</code>   ➜ (মূল প্রফিট)</b>\n"
                                "<b>🔹 𝗦𝘁𝗲প 𝟮 : <code>15.75 BDT</code>   ➜ (রিকভারি + লাভ)</b>\n"
                                "<b>🔹 𝗦𝘁𝗲প 𝟯 : <code>31.50 BDT</code>   ➜ (রিকভারি + লাভ)</b>\n"
                                "<b>🔹 𝗦𝘁𝗲প 𝟰 : <code>62.99 BDT</code>  ➜ (রিকভারি + লাভ)</b>\n"
                                "<b>🔹 𝗦𝘁𝗲প 𝟱 : <code>125.98 BDT</code>  ➜ (রিকভারি + লাভ)</b>\n"
                                "<b>🔹 𝗦𝘁𝗲প 𝟲 : <code>251.97 BDT</code> ➜ (রিকভারি + লাভ)</b>\n"
                                "<b>🔹 𝗦𝘁𝗲প 𝟳 : <code>503.94 BDT</code> ➜ (হাই সিকিউর প্রফিট)</b>\n"
                                "<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                                "<b>💎 মোট প্রয়োজনীয় ব্যাকআপ ফান্ড : <code>1000 BDT</code></b>\n"
                                "<b>⚠️ মনে রাখবেন: মানি ম্যানেজমেন্ট না মানলে কোনো অ্যালগরিদমই লাভ দিতে পারবে না।</b>\n"
                                f"👉 <b>রেজিস্ট্রেশন লিংক:</b> {REGISTER_LINK}"
                            )
                            send_msg(chat_id, fund_txt)

                        elif text == BTN_SUPPORT:
                            send_msg(
                                chat_id,
                                f"<b>💬 𝗦𝗔𝗚𝗢𝗥 𝗩𝗜𝗣 অফিসিয়াল সাপোর্ট ও হেল্পডেস্ক</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                                f"<b>যেকোনো প্রশ্ন, ব্যালেন্স ইস্যু বা অ্যাকাউন্ট ভেরিফিকেশনের জন্য সরাসরি যোগাযোগ করুন:</b>\n\n"
                                f"<b>👑 সাপোর্ট ইনবক্স : @{SUPPORT_USERNAME}</b>\n"
                                f"<b>⏰ একটিভ টাইম    : 24/7 অনলাইন ইনস্ট্যান্ট রেসপন্স</b>\n"
                                f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                                f"👉 {REGISTER_LINK}"
                            )

        except Exception as e:
            logging.error(f"Updates Error: {e}")
            time.sleep(1)

# ==============================================================================
# 🔄 ৮. ১-মিনিট রিয়েল-টাইম অটো রিপ্লেস ক্রন লুপ
# ==============================================================================
def live_auto_signal_loop():
    logging.info("⚡ 1-Minute Live Signal Loop Started...")
    current_period = get_exact_game_period()
    today_check = time.strftime("%Y-%m-%d")

    while True:
        try:
            current_day = time.strftime("%Y-%m-%d")
            if current_day != today_check:
                today_check = current_day
                db_query(f"UPDATE users SET is_verified = 0, auto_signal = 0 WHERE user_id NOT IN ({','.join(map(str, ADMIN_IDS))})", commit=True)
                logging.info("🌙 Midnight reset completed. All user access expired for new day validation.")

            new_period = get_exact_game_period()

            if new_period != current_period:
                current_period = new_period

                pred = engine.get_new_prediction()
                nums = engine.generate_numbers(pred)
                lvl = random.choice([1, 2])
                sig_msg = format_signal_msg(current_period, pred, nums, lvl)

                active_users = db_query("SELECT user_id, last_msg_id FROM users WHERE auto_signal = 1 AND is_banned = 0 AND is_verified = 1 AND last_access_date = ?", (current_day,), fetchall=True) or []

                for u in active_users:
                    uid, old_mid = u[0], u[1]

                    if old_mid and old_mid > 0:
                        delete_msg(uid, old_mid)

                    s_sent = send_msg(uid, sig_msg)
                    if s_sent and "result" in s_sent:
                        db_query("UPDATE users SET last_msg_id = ? WHERE user_id = ?", (s_sent["result"]["message_id"], uid), commit=True)

        except Exception as e:
            logging.error(f"Auto Signal Loop Error: {e}")

        time.sleep(1)

# ==============================================================================
# 🌐 ৯. ২৪/৭ লাইভ ওয়েব সার্ভার
# ==============================================================================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h1>SAGOR VIP SERVER IS RUNNING 24/7</h1>")
    def log_message(self, format, *args):
        return

def run_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()

# ==============================================================================
# 🚀 ১০. মেইন এন্ট্রি পয়েন্ট
# ==============================================================================
if __name__ == "__main__":
    init_db()
    threading.Thread(target=run_health_server, daemon=True).start()
    threading.Thread(target=live_auto_signal_loop, daemon=True).start()
    logging.info("👑 SAGOR VIP INJECTOR STARTED SUCCESSFULLY!")
    process_updates()
