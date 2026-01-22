"""
Engine - ליבת המערכת
מנוע Flask עם טעינה דינמית של פלאגינים
תומך ב-SaaS עם מספר בוטים של משתמשים שונים
משתמש ב-MongoDB לאחסון מאובטח של טוקנים
"""

from flask import Flask, render_template, request
import importlib
import sys
import os
import traceback
from pathlib import Path
from dotenv import load_dotenv
import requests
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# טעינת משתני סביבה מקובץ .env (אם קיים)
load_dotenv()

# הוספת תיקיית הפרויקט ל-PATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = PROJECT_ROOT / "templates"
PLUGINS_DIR = PROJECT_ROOT / "plugins"
PLUGINS_CACHE = {}

# MongoDB connection
_mongo_client = None
_mongo_db = None


def get_mongo_db():
    """
    מחזיר חיבור ל-MongoDB.
    משתמש ב-connection pooling ו-lazy initialization.
    """
    global _mongo_client, _mongo_db
    
    if _mongo_db is not None:
        return _mongo_db
    
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        print("⚠️ MONGO_URI not configured - bot registry disabled")
        return None
    
    try:
        _mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # בדיקת חיבור
        _mongo_client.admin.command('ping')
        _mongo_db = _mongo_client.get_database("bot_factory")
        print("✅ MongoDB connected successfully")
        return _mongo_db
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"❌ MongoDB connection failed: {e}")
        return None
    except Exception as e:
        print(f"❌ MongoDB error: {e}")
        return None

# Flask defaults to searching for templates relative to this module/package.
# In this repo templates live at "<project_root>/templates", so we set it explicitly.
app = Flask(__name__, template_folder=str(TEMPLATES_DIR))
app.config.from_object(Config)


def set_webhook():
    """
    רישום webhook לטלגרם בעת עליית השרת.
    """
    token = os.environ.get("TELEGRAM_TOKEN")
    render_url = os.environ.get("RENDER_EXTERNAL_URL")

    if not token or not render_url:
        print("⚠️ Telegram webhook not set: missing TELEGRAM_TOKEN or RENDER_EXTERNAL_URL")
        return False

    webhook_url = f"{render_url.rstrip('/')}/{token}"
    api_url = f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}"

    try:
        response = requests.get(api_url, timeout=10)
        if response.ok:
            print("✅ Telegram webhook set successfully")
        else:
            print(f"❌ Failed setting Telegram webhook: {response.status_code} {response.text}")
        return response.ok
    except Exception as e:
        print(f"❌ Error setting Telegram webhook: {e}")
        return False


# Register webhook once on server startup
set_webhook()


def get_plugin_for_token(bot_token):
    """
    מחזיר את שם הפלאגין עבור טוקן מסוים מ-MongoDB.
    
    Args:
        bot_token: טוקן הבוט
    
    Returns:
        str: שם הפלאגין או None אם לא נמצא
    """
    db = get_mongo_db()
    if db is None:
        return None
    
    try:
        result = db.bot_registry.find_one({"token": bot_token})
        if result:
            return result.get("plugin_filename")
        return None
    except Exception as e:
        print(f"❌ Error fetching bot from MongoDB: {e}")
        return None


def register_bot_in_db(bot_token, plugin_filename):
    """
    רושם בוט חדש ב-MongoDB.
    
    Args:
        bot_token: טוקן הבוט
        plugin_filename: שם קובץ הפלאגין
    
    Returns:
        bool: האם הרישום הצליח
    """
    db = get_mongo_db()
    if db is None:
        print("❌ Cannot register bot - MongoDB not connected")
        return False
    
    try:
        # upsert - עדכן אם קיים, צור אם לא
        db.bot_registry.update_one(
            {"token": bot_token},
            {"$set": {
                "token": bot_token,
                "plugin_filename": plugin_filename,
                "created_at": __import__('datetime').datetime.utcnow()
            }},
            upsert=True
        )
        print(f"✅ Bot registered in MongoDB: {plugin_filename}")
        return True
    except Exception as e:
        print(f"❌ Error registering bot in MongoDB: {e}")
        return False


def bot_exists_in_db(bot_token):
    """
    בודק אם בוט עם הטוקן הזה כבר קיים ב-MongoDB.
    
    Args:
        bot_token: טוקן הבוט
    
    Returns:
        bool: האם הבוט קיים
    """
    db = get_mongo_db()
    if db is None:
        return False
    
    try:
        result = db.bot_registry.find_one({"token": bot_token})
        return result is not None
    except Exception as e:
        print(f"❌ Error checking bot existence in MongoDB: {e}")
        return False


def log_user_action(user_id, action_type, bot_token=None, details=None):
    """
    רושם פעולת משתמש ב-MongoDB לצורכי אנליטיקס.
    
    Args:
        user_id: מזהה המשתמש בטלגרם
        action_type: סוג הפעולה (message, callback, command)
        bot_token: טוקן הבוט (אופציונלי, מוסתר חלקית)
        details: פרטים נוספים (אופציונלי)
    """
    db = get_mongo_db()
    if db is None:
        return
    
    try:
        # הסתרת חלק מהטוקן לאבטחה
        safe_bot_id = None
        if bot_token and ':' in bot_token:
            safe_bot_id = bot_token.split(':')[0]
        
        db.user_actions.insert_one({
            "user_id": user_id,
            "action_type": action_type,
            "bot_id": safe_bot_id,
            "details": details,
            "timestamp": __import__('datetime').datetime.utcnow()
        })
    except Exception as e:
        # לא נכשיל את הבקשה בגלל לוג
        print(f"⚠️ Failed to log user action: {e}")


def load_plugin_by_name(plugin_name):
    """
    טוען פלאגין ספציפי לפי שם.
    
    Args:
        plugin_name: שם הפלאגין (ללא סיומת .py)
    
    Returns:
        module: מודול הפלאגין או None אם נכשל
    """
    if plugin_name in PLUGINS_CACHE:
        return PLUGINS_CACHE[plugin_name]
    
    plugin_path = PLUGINS_DIR / f"{plugin_name}.py"
    if not plugin_path.exists():
        print(f"❌ Plugin file not found: {plugin_name}")
        return None
    
    try:
        importlib.invalidate_caches()
        plugin_module = importlib.import_module(f"plugins.{plugin_name}")
        PLUGINS_CACHE[plugin_name] = plugin_module
        print(f"✅ Plugin loaded: {plugin_name}")
        return plugin_module
    except ImportError as e:
        print(f"❌ Failed to load plugin '{plugin_name}': {e}")
        return None
    except Exception as e:
        print(f"❌ Error loading plugin '{plugin_name}': {e}")
        return None


def load_plugins():
    """
    טוען דינמית את כל הפלאגינים מתיקיית plugins.
    שומר את הפלאגינים במטמון גלובלי כדי למנוע טעינה מחדש בכל בקשה.
    
    Returns:
        list: רשימת מודולי הפלאגינים שנטענו
    """
    if not PLUGINS_DIR.exists():
        return []

    importlib.invalidate_caches()

    plugin_names = {
        path.stem
        for path in PLUGINS_DIR.iterdir()
        if path.is_file() and path.suffix == ".py" and not path.name.startswith("__")
    }

    # הסרת פלאגינים שנמחקו מהתיקייה
    for cached_name in list(PLUGINS_CACHE.keys()):
        if cached_name not in plugin_names:
            PLUGINS_CACHE.pop(cached_name, None)

    # טעינת פלאגינים חדשים בלבד
    for plugin_name in sorted(plugin_names):
        if plugin_name in PLUGINS_CACHE:
            continue
        try:
            plugin_module = importlib.import_module(f"plugins.{plugin_name}")
            PLUGINS_CACHE[plugin_name] = plugin_module
            print(f"✅ Plugin loaded: {plugin_name}")
        except ImportError as e:
            print(f"❌ Failed to load plugin '{plugin_name}': {e}")
        except Exception as e:
            print(f"❌ Error loading plugin '{plugin_name}': {e}")

    return [PLUGINS_CACHE[name] for name in sorted(PLUGINS_CACHE)]


@app.route('/')
def dashboard():
    """
    מסך הדשבורד הראשי
    טוען את כל הווידג'טים מהפלאגינים
    """
    widgets = []

    # טעינת כל הפלאגינים
    plugins = load_plugins()

    # איסוף ווידג'טים מכל פלאגין
    for plugin in plugins:
        widget = None
        if hasattr(plugin, 'get_dashboard_widget'):
            try:
                widget = plugin.get_dashboard_widget()
            except Exception as e:
                print(f"❌ Error getting widget from {plugin.__name__}: {e}")

        if not isinstance(widget, dict):
            plugin_name = plugin.__name__.split(".")[-1]
            widget = {
                "title": plugin_name,
                "value": "Loaded",
                "label": "No dashboard widget provided",
                "status": "info",
                "icon": "bi-plug",
            }

        widgets.append(widget)
    
    return render_template('index.html', 
                          widgets=widgets, 
                          bot_name=Config.BOT_NAME)


@app.route('/health')
def health():
    """בדיקת בריאות השרת"""
    return {"status": "healthy", "bot": Config.BOT_NAME}


def send_telegram_message(bot_token, chat_id, reply):
    """
    שולח הודעה לטלגרם - תומך בטקסט פשוט או בתשובה מורכבת עם כפתורים.
    
    Args:
        bot_token: טוקן הבוט
        chat_id: מזהה הצ'אט
        reply: מחרוזת פשוטה או dict עם text ו-reply_markup
    """
    if not reply:
        return
    
    # בניית payload ההודעה
    if isinstance(reply, str):
        payload = {"chat_id": chat_id, "text": reply}
    elif isinstance(reply, dict):
        payload = {"chat_id": chat_id}
        if "text" in reply:
            payload["text"] = reply["text"]
        if "reply_markup" in reply:
            payload["reply_markup"] = reply["reply_markup"]
        if "parse_mode" in reply:
            payload["parse_mode"] = reply["parse_mode"]
    else:
        return
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json=payload,
            timeout=10,
        )
    except Exception as e:
        print(f"❌ Failed sending Telegram message: {e}")


def answer_callback_query(bot_token, callback_query_id, text=None):
    """
    עונה ל-callback query (לחיצה על כפתור).
    """
    try:
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
            json=payload,
            timeout=10,
        )
    except Exception as e:
        print(f"❌ Failed answering callback query: {e}")


@app.route('/<bot_token>', methods=['POST'])
def telegram_webhook(bot_token):
    """
    מקבל עדכונים מטלגרם עבור בוט ספציפי.
    טוען את הפלאגין המשויך לטוקן ומפעיל את handle_message שלו.
    תומך גם בטוקן הראשי (מ-config) וגם בבוטים רשומים ב-bot_registry.
    תומך גם ב-callback queries (לחיצות על כפתורים).
    """
    update = request.get_json(silent=True) or {}

    # טיפול ב-callback query (לחיצה על כפתור)
    callback_query = update.get("callback_query")
    if callback_query:
        callback_id = callback_query.get("id")
        callback_data = callback_query.get("data")
        message = callback_query.get("message") or {}
        chat_id = (message.get("chat") or {}).get("id")
        user_id = (callback_query.get("from") or {}).get("id")
        
        if chat_id is None:
            return {"ok": True}
        
        # רישום פעולת משתמש לאנליטיקס
        log_user_action(user_id, "callback", bot_token, {"data": callback_data})
        
        # ענה על ה-callback query כדי להסיר את ה"שעון חול"
        answer_callback_query(bot_token, callback_id)
        
        # טיפול בבוט הראשי
        if config.TELEGRAM_TOKEN and bot_token == config.TELEGRAM_TOKEN:
            plugins = load_plugins()
            for plugin in plugins:
                if hasattr(plugin, "handle_callback"):
                    try:
                        reply = plugin.handle_callback(callback_data, user_id)
                    except Exception as e:
                        print(f"❌ Error in handle_callback for {plugin.__name__}: {e}")
                        traceback.print_exc()
                        error_message = "⚠️ אירעה שגיאה פנימית בבוט זה.\nנסה שוב מאוחר יותר או שלח /start"
                        send_telegram_message(bot_token, chat_id, error_message)
                        continue

                    if reply:
                        send_telegram_message(bot_token, chat_id, reply)
                        break
            return {"ok": True}
        
        # טיפול בבוטים רשומים (מ-MongoDB)
        plugin_filename = get_plugin_for_token(bot_token)
        if plugin_filename:
            plugin_name = plugin_filename.replace('.py', '')
            plugin = load_plugin_by_name(plugin_name)
            
            if plugin and hasattr(plugin, "handle_callback"):
                try:
                    reply = plugin.handle_callback(callback_data, user_id)
                    if reply:
                        send_telegram_message(bot_token, chat_id, reply)
                except Exception as e:
                    print(f"❌ Error in handle_callback for {plugin.__name__}: {e}")
                    traceback.print_exc()
                    error_message = "⚠️ אירעה שגיאה פנימית בבוט זה.\nנסה שוב מאוחר יותר או שלח /start"
                    send_telegram_message(bot_token, chat_id, error_message)
        
        return {"ok": True}

    # טיפול בהודעות רגילות
    message = update.get("message") or {}
    text = message.get("text")

    # רק הודעות טקסט מעניינות אותנו כרגע
    if not text:
        return {"ok": True}

    chat_id = (message.get("chat") or {}).get("id")
    user_id = (message.get("from") or {}).get("id")
    if chat_id is None:
        return {"ok": True}

    # רישום פעולת משתמש לאנליטיקס
    action_type = "command" if text.startswith("/") else "message"
    log_user_action(user_id, action_type, bot_token, {"text_preview": text[:50] if text else None})

    # בדיקה אם זה הטוקן הראשי (הבוט המקורי)
    if config.TELEGRAM_TOKEN and bot_token == config.TELEGRAM_TOKEN:
        # התנהגות מקורית - טען את כל הפלאגינים
        plugins = load_plugins()
        for plugin in plugins:
            if hasattr(plugin, "handle_message"):
                try:
                    # ננסה לשלוח גם user_id אם הפלאגין תומך
                    try:
                        reply = plugin.handle_message(text, user_id)
                    except TypeError:
                        reply = plugin.handle_message(text)
                except Exception as e:
                    print(f"❌ Error in handle_message for {plugin.__name__}: {e}")
                    traceback.print_exc()
                    # שליחת הודעת שגיאה ידידותית למשתמש
                    error_message = "⚠️ אירעה שגיאה פנימית בבוט זה.\nנסה שוב מאוחר יותר או שלח /start"
                    send_telegram_message(bot_token, chat_id, error_message)
                    continue

                if reply:
                    send_telegram_message(bot_token, chat_id, reply)
                    break
        return {"ok": True}

    # בדיקה אם הטוקן רשום ב-MongoDB
    plugin_filename = get_plugin_for_token(bot_token)
    if not plugin_filename:
        print(f"⚠️ Unknown bot token received: {bot_token[:10]}...")
        return {"ok": True}

    # הסר את סיומת .py אם קיימת
    plugin_name = plugin_filename.replace('.py', '')
    
    plugin = load_plugin_by_name(plugin_name)
    if not plugin:
        print(f"❌ Failed to load plugin for bot: {plugin_name}")
        return {"ok": True}

    if hasattr(plugin, "handle_message"):
        try:
            # ננסה לשלוח גם user_id אם הפלאגין תומך
            try:
                reply = plugin.handle_message(text, user_id)
            except TypeError:
                reply = plugin.handle_message(text)
            if reply:
                send_telegram_message(bot_token, chat_id, reply)
        except Exception as e:
            # תפיסת כל שגיאה מהפלאגין - רישום לוג והחזרת הודעה ידידותית למשתמש
            print(f"❌ Error in handle_message for {plugin.__name__}: {e}")
            traceback.print_exc()
            # שליחת הודעת שגיאה ידידותית למשתמש
            error_message = "⚠️ אירעה שגיאה פנימית בבוט זה.\nנסה שוב מאוחר יותר או שלח /start"
            send_telegram_message(bot_token, chat_id, error_message)

    return {"ok": True}


if __name__ == '__main__':
    # קריאת PORT ממשתני סביבה (לשימוש ב-Render.com)
    port = int(os.environ.get("PORT", Config.PORT))
    
    app.run(
        host=Config.HOST,
        port=port,
        debug=Config.DEBUG
    )
