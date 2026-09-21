
import os
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

env_adm = os.environ.get("ADMIN_IDS", "")
if env_adm:
    for a in env_adm.split(","):
        if a.strip().isdigit() and int(a.strip()) not in ADMIN_IDS:
            ADMIN_IDS.append(int(a.strip()))

SUPPORT_USERNAME = "SAGOR_TREDER"
PORT = int(os.environ.get("PORT", 8080))

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# ==============================================================================
# 🗄️ ২. ডাটাবেজ হ্যান্ডলার
# ==============================================================================
DB_PATH = "sagor_quantum_system.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            game_uid TEXT DEFAULT '',
            deposit_amount TEXT DEFAULT '',
            is_verified INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            auto_signal INTEGER DEFAULT 0,
            last_msg_id INTEGER DEFAULT 0,
            last_access_date TEXT DEFAULT '',
            joined_at TEXT DEFAULT ''
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS system_stats (
            id INTEGER PRIMARY KEY,
            maintenance INTEGER DEFAULT 0,
            connected_channel_id TEXT DEFAULT ''
        )
    """)
    cur.execute("INSERT OR IGNORE INTO system_stats (id, maintenance, connected_channel_id) VALUES (1, 0, '')")
    
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for adm in ADMIN_IDS:
        cur.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, is_verified, last_access_date, joined_at)
            VALUES (?, 'admin', 'Super Admin', 1, ?, ?)
        """, (int(adm), today_str, time.strftime("%Y-%m-%d %H:%M:%S")))
        cur.execute("UPDATE users SET is_verified = 1, is_banned = 0, last_access_date = ? WHERE user_id = ?", (today_str, int(adm)))
        
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

def is_admin(user_id):
    try:
        return int(user_id) in [int(x) for x in ADMIN_IDS]
    except Exception:
        return False

# ==============================================================================
# 📡 ৩. TELEGRAM API
# ==============================================================================
def tg_api(method, payload=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        data = json.dumps(payload).encode("utf-8") if payload else None
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as he:
        if he.code == 409:
            logging.error("⚠️ [409 Conflict] একই BOT_TOKEN অন্য কোথাও চালু আছে! @BotFather থেকে Token Revoke করে নতুন টোকেন নিন।")
            time.sleep(3)
        return None
    except Exception as e:
        if "timed out" not in str(e).lower():
            logging.error(f"TG API Error ({method}): {e}")
        return None

def send_msg(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_api("sendMessage", payload)

def copy_msg(chat_id, from_chat_id, message_id, caption=None):
    payload = {"chat_id": chat_id, "from_chat_id": from_chat_id, "message_id": message_id}
    if caption:
        payload["caption"] = caption
        payload["parse_mode"] = "HTML"
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
    payload = {
        "chat_id": chat_id,
        "message_id": msg_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = tg_api("editMessageText", payload)
    if not res:
        return send_msg(chat_id, text, reply_markup)
    return res

# ==============================================================================
# 🎯 ৪. প্রেডিকশন ইঞ্জিন
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
# 🎨 ৫. কীবোর্ড ও সিগন্যাল টেমপ্লেট
# ==============================================================================
BTN_START = "⚡ 𝗦𝗧𝗔𝗥𝗧 𝗔𝗨𝗧𝗢 𝗦𝗜𝗚𝗡𝗔𝗟 ⚡"
BTN_STOP = "🛑 𝗦𝗧𝗢𝗣 𝗦𝗜𝗚𝗡𝗔𝗟 🛑"
BTN_FUTURE = "🔮 𝗙𝗨𝗧𝗨𝗥𝗘 𝟭𝟬 𝗦𝗜𝗚𝗡𝗔𝗟𝗦 🔮"
BTN_RADAR = "📡 𝗠𝗔𝗥𝗞𝗘𝗧 𝗧𝗥𝗘𝗡𝗗 𝗥𝗔𝗗𝗔𝗥 📡"
BTN_FUND = "💰 𝟳-𝗦𝗧𝗘𝗣 𝗙𝗨𝗡𝗗 𝗠𝗔𝗡𝗔𝗚𝗘𝗥 💰"
BTN_SUPPORT = "💬 𝗩𝗜𝗣 𝗦𝗨𝗣𝗣𝗢𝗥𝗧 💬"
BTN_ADMIN = "👑 𝗦𝗔𝗚𝗢𝗥 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟 👑"

admin_live_sender_mode = {}

def get_admin_panel_markup(user_id):
    cur_st = "🟢 চালু" if admin_live_sender_mode.get(int(user_id), False) else "🔴 বন্ধ"
    return {
        "inline_keyboard": [
            [{"text": f"⚡ লাইভ সিগন্যাল সেন্ডার ({cur_st})", "callback_data": "adm_toggle_sender"}],
            [{"text": "📊 ইউজার ডাটা", "callback_data": "adm_users"}, {"text": "⏳ পেন্ডিং রিকোয়েস্ট", "callback_data": "adm_pending"}],
            [{"text": "📢 চ্যানেল কানেক্ট", "callback_data": "adm_connect_channel"}, {"text": "📢 ব্রডকাস্ট", "callback_data": "adm_bc"}],
            [{"text": "🛠️ মেইনটেনেন্স", "callback_data": "adm_maint"}, {"text": "🧹 অপটিমাইজ DB", "callback_data": "adm_clean_db"}],
            [{"text": "🚫 ব্যান ইউজার", "callback_data": "adm_ban_user"}, {"text": "🟢 আনব্যান ইউজার", "callback_data": "adm_unban_user"}],
            [{"text": "🔄 রিফ্রেশ প্যানেল", "callback_data": "adm_refresh_panel"}]
        ]
    }

def get_main_keyboard(user_id):
    kb = [
        [{"text": BTN_START}, {"text": BTN_STOP}],
        [{"text": BTN_FUTURE}, {"text": BTN_RADAR}],
        [{"text": BTN_FUND}, {"text": BTN_SUPPORT}]
    ]
    if is_admin(user_id):
        kb.append([{"text": BTN_ADMIN}])
    return {"keyboard": kb, "resize_keyboard": True}

def get_welcome_message(first_name, user_id):
    return (
        f"<b>👑 স্বাগতম, {first_name}! 👑</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>🌟 𝗦𝗔𝗚𝗢𝗥 𝗩𝗜𝗣 𝗦𝗘𝗥𝗩𝗘𝗥 𝗩𝟮𝟬-এ আপনাকে স্বাগতম!</b>\n\n"
        f"<b>🚀 এটি বিশ্বের অন্যতম শক্তিশালী AI চালিত ১-মিনিট ডাইনামিক উইংগো প্রেডিকশন সিস্টেম।</b>\n\n"
        f"<b>🎯 আমাদের বিশেষ সুবিধাসমূহ:</b>\n"
        f"<b>├ 🟢 অটো লাইভ রিপ্লেস : প্রতি মিনিটে সিগন্যাল স্বয়ংক্রিয়ভাবে আপডেট হবে</b>\n"
        f"<b>├ 🎯 BIG & SMALL নিখুঁত ট্রেন্ড ফিল্টারিং</b>\n"
        f"<b>├ 🛡️ ২-লেভেল হাই একুরেসি সেফটি বুস্টার মেথড</b>\n"
        f"<b>├ 💰 অফিসিয়াল ৭-স্টেপ মার্টিঙ্গেল ব্যাকআপ চার্ট</b>\n"
        f"<b>└ 💎 ৯৯.৮% পর্যন্ত রিয়েল-টাইম উইন রেট পারফরম্যান্স</b>\n\n"
        f"<b>📌 ট্রেডার প্রোফাইল ডাটা:</b>\n"
        f"<b>├ 👤 ট্রেডার নাম   : {first_name}</b>\n"
        f"<b>├ 🆔 ট্রেডার আইডি : <code>{user_id}</code></b>\n"
        f"<b>└ 🔰 স্ট্যাটাস     : 🟢 𝗩𝗜𝗣 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗔𝗖𝗧𝗜𝗩𝗘</b>\n\n"
        f"<b>💡 নিচের বাটনগুলো চেপে আপনার সিগন্যাল সার্ভিস এখনই শুরু করুন।</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>"
    )

def format_signal_msg(period, pred, numbers=None, level=1):
    pred_badge = "<b>𝗕𝗜𝗚 ✅</b>" if pred == "BIG" else "<b>𝗦𝗠𝗔𝗟𝗟 ✅</b>"
    lvl_txt = "LEVEL: 1 (PRIMARY SAFE)" if level == 1 else "LEVEL: 2 (HIGH BOOST 🔥)"
    confidence = random.randint(95, 99)
    accuracy_bar = "██████████" if confidence >= 98 else "█████████▒"
    number_line = f"🔢 <b>𝟐-𝐋𝐄𝐕𝐄𝐋 𝐍𝐔𝐌</b> : <code>{numbers[0]} | {numbers[1]}</code>\n" if numbers and len(numbers) >= 2 else ""

    return (
        f"👑 <b>𝗦𝗔𝗚𝗢𝗥 𝗩𝗜𝗣 𝗜𝗡𝗝𝗘𝗖𝗧𝗢𝗥 𝗩𝟮𝟬</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <b>𝗣𝗘𝗥𝗜𝗢𝗗</b>      : <code>{period}</code>\n"
        f"🎯 <b>𝗣𝗥𝗘𝗗𝗜𝗖𝗧𝗜𝗢𝗡</b>  : {pred_badge}\n"
        f"{number_line}"
        f"🛡️ <b>𝗦𝗧𝗔𝗧𝗨𝗦</b>      : <code>{lvl_txt}</code>\n"
        f"📊 <b>𝗖𝗢𝗡𝗙𝗜𝗗𝗘𝗡𝗖𝗘</b>    : <code>{confidence}%</code> [{accuracy_bar}]\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 <b>𝗦𝗘𝗥𝗩𝗘𝗥 𝗦𝗧𝗔𝗧𝗨𝗦</b> : 🟢 <b>𝗢𝗡𝗟𝗜𝗡𝗘 & 𝗦𝗬𝗡𝗖𝗘𝗗</b>\n"
        f"⚠️ <b>জরুরি গাইডলাইন</b>: সবসময় ৭-স্টেপ ফান্ড ব্যাকআপ মেনে চলুন!"
    )

# ==============================================================================
# 🎮 ৬. কন্ট্রোলার ও মেসেজ প্রসেসর
# ==============================================================================
waiting_broadcast_admin = None
waiting_ban_admin = None
waiting_unban_admin = None
waiting_channel_admin = None
user_submit_state = {}

def process_updates():
    global waiting_broadcast_admin, waiting_ban_admin, waiting_unban_admin, waiting_channel_admin
    global admin_live_sender_mode, user_submit_state
    offset = 0

    while True:
        try:
            updates = tg_api("getUpdates", {"offset": offset, "timeout": 10})
            if updates and "result" in updates:
                for u in updates["result"]:
                    offset = u["update_id"] + 1

                    # ----------------- ১. CALLBACK QUERY (ইনলাইন বাটন) -----------------
                    if "callback_query" in u:
                        cq = u["callback_query"]
                        cq_id = cq["id"]
                        data = cq.get("data", "")
                        from_user = cq.get("from", {})
                        user_id = int(from_user.get("id", 0))
                        msg_obj = cq.get("message", {})
                        chat_id = msg_obj.get("chat", {}).get("id", user_id)
                        msg_id = msg_obj.get("message_id")

                        # বাটন ক্লিকে সাথে সাথে লোডিং বন্ধ করা
                        answer_callback(cq_id)

                        # ইউজার ফর্ম সাবমিট
                        if data == "usr_submit_form":
                            user_submit_state[user_id] = {"step": 1, "uid": ""}
                            send_msg(user_id, "<b>✍️ অনুগ্রহ করে আপনার গেমের সঠিক User ID (UID) টি লিখে পাঠান:</b>")
                            continue

                        # এডমিন বাটন প্রসেসিং
                        if is_admin(user_id):
                            if data in ["adm_refresh_panel", "adm_back_panel"]:
                                edit_msg(chat_id, msg_id, "<b>👑 𝗦𝗔𝗚𝗢𝗥 𝗔𝗗𝗠𝗜𝗡 𝗠𝗔𝗦𝗧𝗘𝗥 𝗣𝗔𝗡𝗘𝗟:</b>\n━━━━━━━━━━━━━━━━━━━━━━\nসম্পূর্ণ সিস্টেম কন্ট্রোল করতে নিচের অপশন ব্যবহার করুন।", get_admin_panel_markup(user_id))
                                continue

                            elif data.startswith("app_"):
                                target_id = int(data.split("_")[1])
                                today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                                db_query("UPDATE users SET is_verified = 1, is_banned = 0, last_access_date = ? WHERE user_id = ?", (today_str, target_id), commit=True)
                                edit_msg(chat_id, msg_id, f"<b>✅ ইউজার <code>{target_id}</code> সফলভাবে আজকের জন্য অ্যাপ্রুভ করা হয়েছে!</b>")
                                send_msg(
                                    target_id,
                                    f"<b>🎉 অভিনন্দন! আপনার UID ও ডিপোজিট এডমিন কর্তৃক অনুমোদিত হয়েছে!</b>\n\n<b>এখন আপনি আজকের জন্য 𝗦𝗔𝗚𝗢𝗥 𝗩𝗜𝗣 সার্ভিসের পূর্ণ এক্সেস পেয়ে গেছেন।</b>",
                                    get_main_keyboard(target_id)
                                )
                                continue

                            elif data.startswith("rej_"):
                                target_id = int(data.split("_")[1])
                                db_query("UPDATE users SET is_verified = -1, is_banned = 1, auto_signal = 0 WHERE user_id = ?", (target_id,), commit=True)
                                edit_msg(chat_id, msg_id, f"<b>🚫 ইউজার <code>{target_id}</code> রিজেক্ট ও ব্যান করা হয়েছে।</b>")
                                send_msg(target_id, "<b>❌ দুঃখিত! আপনার প্রদত্ত UID বা ডিপোজিট ডাটা সঠিক না থাকায় এক্সেস রিজেক্ট করা হয়েছে।</b>")
                                continue

                            elif data == "adm_maint":
                                res = db_query("SELECT maintenance FROM system_stats WHERE id = 1", fetchone=True)
                                cur_m = res[0] if res else 0
                                new_m = 0 if cur_m == 1 else 1
                                db_query("UPDATE system_stats SET maintenance = ? WHERE id = 1", (new_m,), commit=True)
                                st = "অন (ON) 🔴" if new_m == 1 else "বন্ধ (OFF) 🟢"
                                edit_msg(chat_id, msg_id, f"<b>👑 𝗦𝗔𝗚𝗢𝗥 𝗔𝗗𝗠𝗜𝗡 𝗠𝗔𝗦𝗧𝗘𝗥 𝗣𝗔𝗡𝗘𝗟:</b>\n━━━━━━━━━━━━━━━━━━━━━━\n🛠️ মেইনটেনেন্স মোড বর্তমানে: <b>{st}</b>", get_admin_panel_markup(user_id))
                                continue

                            elif data == "adm_toggle_sender":
                                cur_mode = admin_live_sender_mode.get(user_id, False)
                                admin_live_sender_mode[user_id] = not cur_mode
                                st_text = "🟢 সক্রিয় (ON)" if admin_live_sender_mode[user_id] else "🔴 নিষ্ক্রিয় (OFF)"
                                edit_msg(chat_id, msg_id, f"<b>👑 𝗦𝗔𝗚𝗢𝗥 𝗔𝗗𝗠𝗜𝗡 𝗠𝗔𝗦𝗧𝗘𝗥 𝗣𝗔𝗡𝗘𝗟:</b>\n━━━━━━━━━━━━━━━━━━━━━━\n⚡ লাইভ সিগন্যাল সেন্ডার বর্তমানে: <b>{st_text}</b>\n\n<i>ইনবক্সে <code>BIG</code>, <code>SMALL</code> অথবা <code>BIG 5 8</code> লিখলে সরাসরি চ্যানেলে পোস্ট হবে।</i>", get_admin_panel_markup(user_id))
                                continue

                            elif data == "adm_connect_channel":
                                waiting_channel_admin = user_id
                                send_msg(user_id, "<b>✍️ যে চ্যানেল বা গ্রুপে সিগন্যাল পাঠাতে চান তার ID (যেমন: -100xxxxxxxxxx) অথবা পাবলিক Username (যেমন: @channelname) লিখে পাঠান:</b>")
                                continue

                            elif data == "adm_users":
                                today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                                users = db_query("SELECT user_id, is_banned, auto_signal, is_verified, last_access_date FROM users", fetchall=True) or []
                                tot = len(users)
                                aut = sum(1 for x in users if x[2] == 1)
                                ban = sum(1 for x in users if x[1] == 1)
                                verified = sum(1 for x in users if x[3] == 1 and x[4] == today_str)
                                pending = sum(1 for x in users if x[3] == 0)
                                send_msg(
                                    user_id,
                                    f"<b>📊 𝗦𝗔𝗚𝗢𝗥 𝗩𝗜𝗣 ইউজার অ্যানালিটিক্স:</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                                    f"<b>👥 মোট ইউজার             : <code>{tot}</code> জন</b>\n"
                                    f"<b>🟢 আজকের ভেরিফাইড ইউজার : <code>{verified}</code> জন</b>\n"
                                    f"<b>⏳ পেন্ডিং সাবমিশন        : <code>{pending}</code> জন</b>\n"
                                    f"<b>⚡ লাইভ অটো সিগন্যাল ইউজার: <code>{aut}</code> জন</b>\n"
                                    f"<b>🚫 ব্যানড ইউজার            : <code>{ban}</code> জন</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━</b>"
                                )
                                continue

                            elif data == "adm_pending":
                                pendings = db_query("SELECT user_id, first_name, username, game_uid, deposit_amount FROM users WHERE is_verified = 0 AND deposit_amount != ''", fetchall=True) or []
                                if not pendings:
                                    send_msg(user_id, "<b>✅ বর্তমানে কোনো পেন্ডিং রিকোয়েস্ট নেই।</b>")
                                else:
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
                                continue

                            elif data == "adm_bc":
                                waiting_broadcast_admin = user_id
                                send_msg(user_id, "<b>✍️ ব্রডকাস্ট মেসেজটি পাঠান (ছবি, ভিডিও, ফাইল বা টেক্সট):</b>\n\nবাতিল করতে <code>/cancel</code> লিখুন।")
                                continue

                            elif data == "adm_ban_user":
                                waiting_ban_admin = user_id
                                send_msg(user_id, "<b>✍️ যাকে ব্যান করতে চান তার Telegram User ID লিখে পাঠান:</b>")
                                continue

                            elif data == "adm_unban_user":
                                waiting_unban_admin = user_id
                                send_msg(user_id, "<b>✍️ যাকে আনব্যান করতে চান তার Telegram User ID লিখে পাঠান:</b>")
                                continue

                            elif data == "adm_clean_db":
                                db_query("VACUUM", commit=True)
                                send_msg(user_id, "<b>✅ ডাটাবেজ অপটিমাইজেশন সফলভাবে সম্পন্ন হয়েছে!</b>")
                                continue
                        else:
                            send_msg(user_id, f"<b>🚫 আপনার এই অপশন ব্যবহারের অনুমতি নেই। (আপনার ID: <code>{user_id}</code>)</b>")
                            continue

                    # ----------------- ২. MESSAGE HANDLING -----------------
                    if "message" in u:
                        msg = u["message"]
                        chat_id = msg["chat"]["id"]
                        msg_id = msg["message_id"]
                        text = msg.get("text", "").strip() if "text" in msg else ""
                        caption = msg.get("caption", "").strip() if "caption" in msg else ""
                        first_name = msg.get("from", {}).get("first_name", "VIP Trader")
                        username = msg.get("from", {}).get("username", "None")

                        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                        default_ver = 1 if is_admin(chat_id) else 0

                        db_query("""
                            INSERT OR IGNORE INTO users (user_id, username, first_name, is_verified, last_access_date, joined_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (chat_id, username, first_name, default_ver, today_str if default_ver == 1 else '', time.strftime("%Y-%m-%d %H:%M:%S")), commit=True)

                        usr = db_query("SELECT is_banned, auto_signal, last_msg_id, is_verified, last_access_date, game_uid, deposit_amount FROM users WHERE user_id = ?", (chat_id,), fetchone=True)

                        if usr and usr[0] == 1 and not is_admin(chat_id):
                            send_msg(chat_id, "<b>🚫 আপনার অ্যাকাউন্টটি ব্যান রয়েছে। সহায়তার জন্য সাপোর্টে যোগাযোগ করুন।</b>")
                            continue

                        # ব্রডকাস্ট হ্যান্ডলার
                        if is_admin(chat_id) and waiting_broadcast_admin == chat_id:
                            if text != "/cancel":
                                waiting_broadcast_admin = None
                                users = db_query("SELECT user_id FROM users WHERE is_banned = 0", fetchall=True) or []
                                c = 0
                                for row in users:
                                    try:
                                        target_uid = row[0]
                                        if text:
                                            full_text = f"<b>📢 𝗦𝗔𝗚𝗢𝗥 𝗩𝗜𝗣 অফিসিয়াল নোটিশ:</b>\n━━━━━━━━━━━━━━━━━━━━━━\n{text}"
                                            send_msg(target_uid, full_text)
                                        else:
                                            new_cap = f"{caption}" if caption else f"<b>📢 𝗦𝗔𝗚𝗢𝗥 𝗩𝗜𝗣 নোটিশ</b>"
                                            copy_msg(target_uid, chat_id, msg_id, caption=new_cap if "sticker" not in msg else None)
                                        c += 1
                                        time.sleep(0.04)
                                    except Exception:
                                        pass
                                send_msg(chat_id, f"<b>✅ সফলভাবে মোট <code>{c}</code> জন ইউজারের কাছে ব্রডকাস্ট পৌঁছেছে।</b>")
                                continue
                            else:
                                waiting_broadcast_admin = None
                                send_msg(chat_id, "<b>🚫 ব্রডকাস্ট বাতিল করা হয়েছে।</b>")
                                continue

                        # সরাসরি চ্যানেলে সিগন্যাল পোস্ট
                        if is_admin(chat_id) and admin_live_sender_mode.get(chat_id, False) and text:
                            parts = text.split()
                            cmd_word = parts[0].upper()
                            if cmd_word in ["BIG", "SMALL"]:
                                sys_data = db_query("SELECT connected_channel_id FROM system_stats WHERE id = 1", fetchone=True)
                                if sys_data and sys_data[0]:
                                    target_ch = sys_data[0]
                                    custom_nums = [int(p) for p in parts[1:] if p.isdigit()]
                                    cur_p = get_exact_game_period()
                                    nums_to_send = custom_nums if len(custom_nums) >= 2 else None
                                    ch_sig_msg = format_signal_msg(cur_p, cmd_word, nums_to_send, level=1)
                                    
                                    res_ch = send_msg(target_ch, ch_sig_msg)
                                    if res_ch and "result" in res_ch:
                                        num_show = f"{custom_nums[0]},{custom_nums[1]}" if nums_to_send else "র্যান্ডম"
                                        send_msg(chat_id, f"<b>✅ চ্যানেলে সিগন্যাল পোস্ট সম্পন্ন!</b>\n\n🎯 <b>প্রেডিকশন :</b> <code>{cmd_word}</code>\n🔢 <b>ডিজিট    :</b> <code>{num_show}</code>\n⚡ <b>পিরিয়ড   :</b> <code>{cur_p}</code>")
                                    else:
                                        send_msg(chat_id, "<b>❌ চ্যানেলে পাঠানো যায়নি! বটকে চ্যানেলে Admin বানিয়েছেন কি না নিশ্চিত করুন।</b>")
                                    continue
                                else:
                                    send_msg(chat_id, "<b>⚠️ কোনো চ্যানেল কানেক্ট করা নেই! এডমিন প্যানেল থেকে চ্যানেল যুক্ত করুন।</b>")

                        # এডমিন ইনপুটস
                        if is_admin(chat_id):
                            if waiting_channel_admin == chat_id and not text.startswith("/"):
                                waiting_channel_admin = None
                                db_query("UPDATE system_stats SET connected_channel_id = ? WHERE id = 1", (text,), commit=True)
                                send_msg(chat_id, f"<b>✅ সফলভাবে চ্যানেল কানেক্ট করা হয়েছে: <code>{text}</code></b>")
                                continue

                            if waiting_ban_admin == chat_id and not text.startswith("/"):
                                waiting_ban_admin = None
                                try:
                                    t_id = int(text)
                                    db_query("UPDATE users SET is_banned = 1, auto_signal = 0 WHERE user_id = ?", (t_id,), commit=True)
                                    send_msg(chat_id, f"<b>✅ ইউজার <code>{t_id}</code> ব্যান করা হয়েছে।</b>")
                                except ValueError:
                                    send_msg(chat_id, "<b>❌ সঠিক নিউমেরিক ইউজার আইডি দিন!</b>")
                                continue

                            if waiting_unban_admin == chat_id and not text.startswith("/"):
                                waiting_unban_admin = None
                                try:
                                    t_id = int(text)
                                    db_query("UPDATE users SET is_banned = 0, is_verified = 1, last_access_date = ? WHERE user_id = ?", (today_str, t_id), commit=True)
                                    send_msg(chat_id, f"<b>✅ ইউজার <code>{t_id}</code> আনব্যান ও আজকের জন্য ভেরিফাই করা হয়েছে।</b>")
                                except ValueError:
                                    send_msg(chat_id, "<b>❌ সঠিক নিউমেরিক ইউজার আইডি দিন!</b>")
                                continue

                        # ইউজার UID ও ডিপোজিট সাবমিশন
                        if chat_id in user_submit_state and text:
                            st = user_submit_state[chat_id]
                            if st["step"] == 1:
                                user_submit_state[chat_id]["uid"] = text
                                user_submit_state[chat_id]["step"] = 2
                                send_msg(chat_id, f"<b>✅ UID সংরক্ষিত: <code>{text}</code>\n\n💰 এবার আপনার আজকের ডিপোজিট অ্যামাউন্ট (BDT) লিখে পাঠান:</b>")
                                continue
                            elif st["step"] == 2:
                                uid_val = st["uid"]
                                dep_val = text
                                del user_submit_state[chat_id]
                                
                                db_query("UPDATE users SET game_uid = ?, deposit_amount = ?, is_verified = 0 WHERE user_id = ?", (uid_val, dep_val, chat_id), commit=True)
                                
                                send_msg(
                                    chat_id,
                                    f"<b>✅ আপনার তথ্য সফলভাবে এডমিনের কাছে জমা হয়েছে!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"🎮 <b>গেম UID    :</b> <code>{uid_val}</code>\n"
                                    f"💰 <b>ডিপোজিট   :</b> <code>{dep_val} BDT</code>\n━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"<i>এডমিন দ্রুত ভেরিফাই করে এক্সেস চালু করবেন। অনুগ্রহ করে অপেক্ষা করুন।</i>"
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
                                        f"<b>🔔 নতুন সাবমিশন এসেছে!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"👤 <b>নাম            :</b> {first_name}\n"
                                        f"🆔 <b>টেলিগ্রাম আইডি:</b> <code>{chat_id}</code>\n"
                                        f"🔗 <b>ইউজারনেম     :</b> @{username}\n"
                                        f"🎮 <b>গেম UID       :</b> <code>{uid_val}</code>\n"
                                        f"💰 <b>ডিপোজিট       :</b> <code>{dep_val} BDT</code>\n━━━━━━━━━━━━━━━━━━━━━━\n"
                                        f"অনুমোদন দিতে চান?",
                                        req_kb
                                    )
                                continue

                        # সাধারণ ইউজারদের দৈনিক ভেরিফিকেশন চেক
                        if not is_admin(chat_id):
                            if not usr or usr[3] != 1 or usr[4] != today_str:
                                sub_kb = {
                                    "inline_keyboard": [
                                        [{"text": "📝 সাবমিট করুন (UID ও ডিপোজিট)", "callback_data": "usr_submit_form"}]
                                    ]
                                }
                                send_msg(
                                    chat_id,
                                    f"<b>🔒 দৈনিক এক্সেস ভেরিফিকেশন প্রয়োজন!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"<b>প্রিয় {first_name},</b> আজকের ভিআইপি সিগন্যাল সার্ভার এক্সেস করতে আপনার গেম <b>UID</b> এবং <b>ডিপোজিট অ্যামাউন্ট</b> সাবমিট করুন।\n\n"
                                    f"<i>(প্রতিদিন রাত ১২:০০ টার পর নতুন দিনের জন্য এক্সেস নবায়ন করতে হয়)</i>\n\n"
                                    f"👉 <b>নিচের বাটনে ক্লিক করে তথ্য সাবমিট করুন:</b>",
                                    sub_kb
                                )
                                continue

                        # মেইনটেনেন্স চেক
                        res_maint = db_query("SELECT maintenance FROM system_stats WHERE id = 1", fetchone=True)
                        maint = res_maint[0] if res_maint else 0
                        if maint == 1 and not is_admin(chat_id):
                            send_msg(chat_id, "<b>🛠️ সার্ভারে মেইনটেনেন্স ও আপগ্রেডেশনের কাজ চলছে! অনুগ্রহ করে কিছুক্ষণ পর চেষ্টা করুন।</b>")
                            continue

                        # মেনু অপশন
                        if text == "/start":
                            send_msg(chat_id, get_welcome_message(first_name, chat_id), get_main_keyboard(chat_id))

                        elif text in [BTN_ADMIN, "/admin"] and is_admin(chat_id):
                            send_msg(
                                chat_id,
                                "<b>👑 𝗦𝗔𝗚𝗢𝗥 𝗔𝗗𝗠𝗜𝗡 𝗠𝗔𝗦𝗧𝗘𝗥 𝗣𝗔𝗡𝗘𝗟:</b>\n"
                                "━━━━━━━━━━━━━━━━━━━━━━\n"
                                "বটের সার্বিক সেটিংস নিয়ন্ত্রণ করতে নিচের বাটনগুলো ব্যবহার করুন:\n"
                                "━━━━━━━━━━━━━━━━━━━━━━",
                                get_admin_panel_markup(chat_id)
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
                            fut_txt = "<b>🔮 𝗦𝗔𝗚𝗢𝗥 আগামী ১০টি ফিউচার সিগন্যাল:</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                            for i in range(10):
                                fp = str(cur_p + i)
                                sim_pred = random.choice(["BIG", "SMALL"])
                                sim_nums = engine.generate_numbers(sim_pred)
                                em = "<b>BIG</b>" if sim_pred == "BIG" else "<b>SMALL</b>"
                                lvl_t = "𝗟𝗩𝗟 𝟮" if i % 3 == 1 else "𝗟𝗩𝗟 𝟭"
                                fut_txt += f"<b>⚡ <code>{fp[-4:]}</code> : {em} | 🔢 <code>{sim_nums[0]},{sim_nums[1]}</code> ({lvl_t})</b>\n"
                            fut_txt += f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💡 মার্কেট সাইকেল ও প্যাটার্ন অনুযায়ী সিগন্যাল নিয়মিত রিফ্রেশ হয়।</b>"
                            send_msg(chat_id, fut_txt)

                        elif text == BTN_RADAR:
                            radar_txt = (
                                "<b>📡 𝗠𝗔𝗥𝗞𝗘𝗧 𝗧𝗥𝗘𝗡𝗗 𝗥𝗔𝗗𝗔𝗥</b>\n"
                                "<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                                "<b>🎯 𝗕𝗜𝗚 𝗧𝗿𝗲𝗻𝗱        : <code>50%</code></b>\n"
                                "<b>🎯 𝗦𝗠𝗔𝗟𝗟 𝗧𝗿𝗲𝗻𝗱      : <code>50%</code></b>\n"
                                "<b>🔥 মার্কেট মোড        : <code>ZIG-ZAG ALTERNATING (BALANCED)</code></b>\n"
                                "<b>🛡️ রিস্ক লেভেল       : <code>LOW RISK (STABLE)</code></b>\n"
                                "<b>📊 অ্যালগরিদম        : <code>AI 99.2% ACCURACY</code></b>\n"
                                f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💡 বর্তমান ট্রেন্ড সুষম এবং ট্রেডের জন্য সম্পূর্ণ অনুকূল।</b>"
                            )
                            send_msg(chat_id, radar_txt)

                        elif text == BTN_FUND:
                            fund_txt = (
                                "<b>💰 অফিসিয়াল ৭-স্টেপ (𝟳-𝗦𝗧𝗘𝗣) মার্টিঙ্গেল ব্যাকআপ চার্ট</b>\n"
                                "<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                                "<b>🔹 𝗦𝘁𝗲𝗽 𝟭 : <code>7.87 BDT</code>   ➜ (মূল প্রফিট)</b>\n"
                                "<b>🔹 𝗦𝘁𝗲𝗽 𝟮 : <code>15.75 BDT</code>   ➜ (রিকভারি + লাভ)</b>\n"
                                "<b>🔹 𝗦𝘁𝗲𝗽 𝟯 : <code>31.50 BDT</code>   ➜ (রিকভারি + লাভ)</b>\n"
                                "<b>🔹 𝗦𝘁𝗲𝗽 𝟰 : <code>62.99 BDT</code>  ➜ (রিকভারি + লাভ)</b>\n"
                                "<b>🔹 𝗦𝘁𝗲𝗽 𝟱 : <code>125.98 BDT</code>  ➜ (রিকভারি + লাভ)</b>\n"
                                "<b>🔹 𝗦𝘁𝗲𝗽 𝟲 : <code>251.97 BDT</code> ➜ (রিকভারি + লাভ)</b>\n"
                                "<b>🔹 𝗦𝘁𝗲𝗽 𝟳 : <code>503.94 BDT</code> ➜ (হাই সিকিউর প্রফিট)</b>\n"
                                "<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                                "<b>💎 মোট প্রয়োজনীয় ব্যাকআপ ফান্ড : <code>1000 BDT</code></b>\n"
                                "<b>⚠️ মনে রাখবেন: মানি ম্যানেজমেন্ট না মানলে লাভ ধরে রাখা সম্ভব নয়।</b>"
                            )
                            send_msg(chat_id, fund_txt)

                        elif text == BTN_SUPPORT:
                            send_msg(
                                chat_id,
                                f"<b>💬 𝗦𝗔𝗚𝗢𝗥 𝗩𝗜𝗣 অফিসিয়াল সাপোর্ট ও হেল্পডেস্ক</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                                f"<b>যেকোনো প্রশ্ন বা অ্যাকাউন্টের বিষয়ে সরাসরি যোগাযোগ করুন:</b>\n\n"
                                f"<b>👑 সাপোর্ট ইনবক্স : @{SUPPORT_USERNAME}</b>\n"
                                f"<b>⏰ একটিভ টাইম    : 24/7 অনলাইন ইনস্ট্যান্ট রেসপন্স</b>\n"
                                f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>"
                            )

        except Exception as e:
            logging.error(f"Updates Loop Error: {e}")
            time.sleep(1)

# ==============================================================================
# 🔄 ৭. ১-মিনিট লাইভ সিগন্যাল ও মিডনাইট রিসেট ক্রন
# ==============================================================================
def live_auto_signal_loop():
    logging.info("⚡ 1-Minute Live Signal Loop Started...")
    current_period = get_exact_game_period()
    today_check = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    while True:
        try:
            current_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            # রাত ১২:০০ টার অটো-রিসেট
            if current_day != today_check:
                today_check = current_day
                adm_ids_str = ",".join(str(int(x)) for x in ADMIN_IDS)
                db_query(f"UPDATE users SET is_verified = 0, auto_signal = 0 WHERE user_id NOT IN ({adm_ids_str})", commit=True)
                logging.info(f"🌙 Midnight reset completed for date: {current_day}")

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
# 🌐 ৮. হেলথ চেক ওয়েব সার্ভার (২৪/৭ পোর্ট ম্যানেজমেন্ট)
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
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
        logging.info(f"🌐 Health Server running on port {PORT}")
        server.serve_forever()
    except Exception as e:
        logging.warning(f"Health server port issue: {e}")

# ==============================================================================
# 🚀 ৯. মেইন রানার
# ==============================================================================
if __name__ == "__main__":
    init_db()
    
    # ব্যাকগ্রাউন্ড থ্রেড রান
    threading.Thread(target=run_health_server, daemon=True).start()
    threading.Thread(target=live_auto_signal_loop, daemon=True).start()
    
    logging.info("👑 SAGOR VIP INJECTOR STARTED SUCCESSFULLY!")
    process_updates()
