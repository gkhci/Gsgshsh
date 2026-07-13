import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import time
import logging
from datetime import datetime

# ========== تنظیمات ==========
PANEL_URL = "https://web-production-1ca13.up.railway.app"
PANEL_PASSWORD = "admin"
BOT_TOKEN = "8793482183:AAEGUa7ZEURP26N34DzKvrudnndC3q7apBk"
ADMIN_ID = "8680457924"  # اختیاری

# ========== راه‌اندازی ==========
bot = telebot.TeleBot(BOT_TOKEN)
session = requests.Session()
logging.basicConfig(level=logging.INFO)

# ========== توابع اصلی ==========
def login_panel():
    """ورود به پنل با رمز عبور"""
    try:
        url = f"{PANEL_URL}/api/login"
        response = session.post(url, json={"password": PANEL_PASSWORD}, timeout=10)
        if response.status_code == 200:
            logging.info("✅ ورود موفق به پنل")
            return True
        else:
            logging.error(f"❌ خطا در ورود: {response.text}")
            return False
    except Exception as e:
        logging.error(f"❌ خطای اتصال: {e}")
        return False

def get_stats():
    """دریافت آمار داشبورد"""
    if not login_panel():
        return None
    try:
        response = session.get(f"{PANEL_URL}/api/stats", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logging.error(f"خطا در دریافت آمار: {e}")
        return None

def get_inbounds():
    """دریافت لیست اینباندها"""
    if not login_panel():
        return None
    try:
        response = session.get(f"{PANEL_URL}/api/inbounds", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('inbounds', [])
        return None
    except Exception as e:
        logging.error(f"خطا در دریافت اینباندها: {e}")
        return None

def create_inbound(remark, traffic_limit_gb, max_ips, expiry_days):
    """ایجاد اینباند جدید"""
    if not login_panel():
        return False, "ورود به پنل ناموفق"
    try:
        payload = {
            "remark": remark,
            "traffic_limit": int(traffic_limit_gb * 1073741824),
            "max_ips": int(max_ips),
            "expiry_days": int(expiry_days),
            "protocol": "vless",
            "settings": {
                "network": "ws",
                "security": "tls"
            }
        }
        response = session.post(f"{PANEL_URL}/api/inbounds", json=payload, timeout=10)
        if response.status_code in [200, 201]:
            return True, "✅ اینباند با موفقیت ساخته شد"
        return False, f"❌ خطا: {response.text}"
    except Exception as e:
        return False, f"❌ خطا: {str(e)}"

def delete_inbound(inbound_id):
    """حذف اینباند"""
    if not login_panel():
        return False, "ورود به پنل ناموفق"
    try:
        response = session.delete(f"{PANEL_URL}/api/inbounds/{inbound_id}", timeout=10)
        if response.status_code in [200, 204]:
            return True, "✅ اینباند حذف شد"
        return False, f"❌ خطا: {response.text}"
    except Exception as e:
        return False, f"❌ خطا: {str(e)}"

def get_inbound_link(inbound_id):
    """دریافت لینک کانفیگ"""
    if not login_panel():
        return None
    try:
        response = session.get(f"{PANEL_URL}/api/inbounds/{inbound_id}/link", timeout=10)
        if response.status_code == 200:
            return response.json().get('link')
        return None
    except:
        return None

def format_bytes(bytes):
    """تبدیل بایت به فرمت خوانا"""
    if bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1024 * 1024:
        return f"{bytes/1024:.1f} KB"
    elif bytes < 1024 * 1024 * 1024:
        return f"{bytes/(1024*1024):.1f} MB"
    else:
        return f"{bytes/(1024*1024*1024):.2f} GB"

# ========== دستورات بات ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📊 آمار", callback_data="stats"),
        InlineKeyboardButton("📋 اینباندها", callback_data="list"),
        InlineKeyboardButton("➕ افزودن", callback_data="add_menu"),
        InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh")
    )
    bot.send_message(
        message.chat.id,
        "🤖 **بات مدیریت پنل Luffy**\n\n"
        "از دکمه‌های زیر برای مدیریت استفاده کنید:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "stats":
        show_stats(call.message)
    elif call.data == "list":
        show_inbounds(call.message)
    elif call.data == "add_menu":
        bot.send_message(
            call.message.chat.id,
            "📝 **افزودن اینباند جدید**\n\n"
            "فرمت:\n"
            "`/add [نام] [ترافیک_GB] [حداکثر_IP] [روز_اعتبار]`\n\n"
            "مثال:\n"
            "`/add کاربر1 100 5 30`",
            parse_mode='Markdown'
        )
    elif call.data.startswith("delete_"):
        inbound_id = call.data.split("_")[1]
        success, msg = delete_inbound(inbound_id)
        bot.answer_callback_query(call.id, msg)
        if success:
            show_inbounds(call.message)
    elif call.data.startswith("link_"):
        inbound_id = call.data.split("_")[1]
        link = get_inbound_link(inbound_id)
        if link:
            bot.send_message(call.message.chat.id, f"🔗 **لینک کانفیگ:**\n`{link}`", parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "❌ دریافت لینک ناموفق")
    elif call.data == "refresh":
        bot.answer_callback_query(call.id, "🔄 بروزرسانی شد")

def show_stats(message):
    stats = get_stats()
    if not stats:
        bot.send_message(message.chat.id, "❌ دریافت آمار ناموفق")
        return
    
    text = f"📊 **آمار پنل Luffy**\n"
    text += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    text += f"🖥️ **CPU:** `{stats.get('cpu', '0')}%`\n"
    text += f"🧠 **Memory:** `{stats.get('memory', '0')}%`\n"
    text += f"🌐 **Domain:** `{stats.get('domain', 'نامشخص')}`\n"
    text += f"📦 **Total Traffic:** `{format_bytes(stats.get('total_traffic', 0))}`\n"
    text += f"📋 **Inbounds:** `{stats.get('inbounds_count', 0)}`\n"
    text += f"⏱️ **Uptime:** `{stats.get('uptime', 'نامشخص')}`"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh"))
    keyboard.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back"))
    
    bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode='Markdown')

def show_inbounds(message):
    inbounds = get_inbounds()
    if inbounds is None:
        bot.send_message(message.chat.id, "❌ دریافت لیست اینباندها ناموفق")
        return
    if not inbounds:
        bot.send_message(message.chat.id, "📭 هیچ اینباندی یافت نشد")
        return
    
    text = "📋 **لیست اینباندها:**\n\n"
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    for item in inbounds[:15]:
        name = item.get('remark', 'بدون نام')
        usage = item.get('usage', 0)
        status = "✅" if item.get('status', False) else "❌"
        expiry = item.get('expiry', 'نامحدود')
        inbound_id = item.get('id')
        
        text += f"**{name}** {status}\n"
        text += f"📊 مصرف: `{format_bytes(usage)}`\n"
        text += f"📅 انقضا: `{expiry}`\n\n"
        
        if inbound_id:
            keyboard.add(
                InlineKeyboardButton(f"🗑️ {name}", callback_data=f"delete_{inbound_id}"),
                InlineKeyboardButton(f"🔗 لینک", callback_data=f"link_{inbound_id}")
            )
    
    keyboard.add(InlineKeyboardButton("➕ افزودن جدید", callback_data="add_menu"))
    keyboard.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back"))
    
    bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode='Markdown')

@bot.message_handler(commands=['add'])
def add_command(message):
    args = message.text.split()
    if len(args) != 5:
        bot.reply_to(message, "⚠️ **فرمت صحیح:**\n`/add [نام] [ترافیک_GB] [حداکثر_IP] [روز_اعتبار]`")
        return
    
    try:
        _, remark, traffic, max_ips, days = args
        traffic = float(traffic)
        max_ips = int(max_ips)
        days = int(days)
        
        if traffic <= 0 or max_ips <= 0 or days <= 0:
            bot.reply_to(message, "❌ همه مقادیر باید مثبت باشند")
            return
        
        bot.reply_to(message, "⏳ در حال ساخت اینباند...")
        success, msg = create_inbound(remark, traffic, max_ips, days)
        bot.reply_to(message, msg)
        if success:
            show_inbounds(message)
    except ValueError:
        bot.reply_to(message, "❌ مقادیر عددی را درست وارد کنید")

@bot.message_handler(commands=['help'])
def help_command(message):
    text = """
📚 **راهنمای بات**

**دستورات:**
`/start` - منوی اصلی
`/stats` - آمار پنل
`/list` - لیست اینباندها
`/add [نام] [ترافیک_GB] [IP] [روز]` - افزودن اینباند
`/help` - این راهنما

**دکمه‌ها:**
• 🗑️ - حذف اینباند
• 🔗 - دریافت لینک کانفیگ
• ➕ - افزودن اینباند جدید
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ========== اجرا ==========
if __name__ == "__main__":
    print("🤖 بات Luffy Panel Manager در حال اجراست...")
    print(f"📡 پنل: {PANEL_URL}")
    print("✅ برای شروع، دستور /start را در تلگرام بزنید")
    
    try:
        bot.polling(none_stop=True, interval=0)
    except Exception as e:
        print(f"❌ خطا: {e}")
