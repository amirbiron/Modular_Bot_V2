# Architect Plugin - creates new plugins via GitHub API
# תומך ביצירת בוטים חדשים עבור מערכת SaaS
# כולל ממשק כפתורים ושיחה מונחית
# משתמש ב-MongoDB לאחסון מאובטח של טוקנים

import base64
import json
import os
import re
import time
import datetime
import requests
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from config import Config


COMMAND_PREFIX = "/create_bot"
GITHUB_API_BASE = "https://api.github.com"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
ANTHROPIC_VERSION = "2023-06-01"

# נתיב לתיקיית הפרויקט
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# MongoDB connection (lazy initialization)
_mongo_client = None
_mongo_db = None


def _get_mongo_db():
    """
    מחזיר חיבור ל-MongoDB.
    משתמש ב-connection pooling ו-lazy initialization.
    """
    global _mongo_client, _mongo_db
    
    if _mongo_db is not None:
        return _mongo_db
    
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        return None
    
    try:
        _mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        _mongo_client.admin.command('ping')
        _mongo_db = _mongo_client.get_database("bot_factory")
        return _mongo_db
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"❌ MongoDB connection failed in architect: {e}")
        return None
    except Exception as e:
        print(f"❌ MongoDB error in architect: {e}")
        return None

# מנגנון נעילה למניעת כפילויות - שומר את הטוקנים שנמצאים כרגע בתהליך יצירה
_creation_in_progress = {}
_CREATION_TIMEOUT = 180  # 3 דקות - זמן מקסימלי ליצירת בוט

# ניהול מצב שיחה למשתמשים (conversation state)
# מבנה: {user_id: {"state": "waiting_token" | "waiting_description", "token": "...", "timestamp": ...}}
_user_conversations = {}
_CONVERSATION_TIMEOUT = 600  # 10 דקות - זמן מקסימלי לשיחה פתוחה

# הודעות למשתמש
START_MESSAGE = """🤖 *ברוכים הבאים למפעל הבוטים!*

אני יכול ליצור עבורך בוט טלגרם חדש בהתאמה אישית.

*איך זה עובד?*
1️⃣ לחץ על הכפתור "צור בוט חדש" למטה
2️⃣ שלח לי את הטוקן שקיבלת מ-@BotFather
3️⃣ תאר לי מה הבוט צריך לעשות
4️⃣ אני אייצר את הבוט ותוכל להתחיל להשתמש בו!

*איך מקבלים טוקן?*
• פתח את @BotFather בטלגרם
• שלח /newbot ועקוב אחר ההוראות
• קבל את הטוקן והעתק אותו

*מה אני יודע לבנות מצוין?* 🚀
✅ משחקים: טריוויה, איש תלוי, ניחוש מספרים.
✅ כלים: מחשבונים, ממירים, מעצבי טקסט.
✅ תוכן: בוטים שמושכים חדשות, קריפטו, או בדיחות.
✅ AI: בוטים שעונים תשובות חכמות.
✅ ניהול קבוצות: אנטי-ספאם, מחיקת הודעות, באן משתמשים.

*מה עדיין אני לא יודע לבנות?* ⚠️
❌ בוטים שצריכים לרוץ ברקע באופן קבוע (תזכורות אוטומטיות).

*פקודות זמינות:*
/start - תפריט ראשי
/create\\_bot - יצירת בוט חדש (עם כפתורים)
/cancel - ביטול תהליך יצירה
/stats - סטטיסטיקות (אדמין בלבד)"""

WAITING_TOKEN_MESSAGE = """🔑 *שלב 1: שליחת הטוקן*

שלח לי את הטוקן של הבוט שקיבלת מ-@BotFather.

הטוקן נראה בערך ככה:
`123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`

💡 *טיפ:* פשוט העתק והדבק את הטוקן מההודעה של BotFather.

לביטול התהליך שלח /cancel"""

WAITING_DESCRIPTION_MESSAGE = """📝 *שלב 2: תיאור הבוט*

מצוין! עכשיו תאר לי מה הבוט צריך לעשות.

*דוגמאות לתיאורים:*
• "בוט שמספר בדיחות בעברית"
• "בוט לניהול משימות אישיות"
• "בוט שעונה על שאלות טריוויה"
• "בוט מזג אוויר לישראל"

ככל שהתיאור יותר מפורט, הבוט יהיה יותר מדויק! 🎯

לביטול התהליך שלח /cancel"""

CANCEL_MESSAGE = "❌ התהליך בוטל. שלח /start כדי להתחיל מחדש."

INVALID_TOKEN_MESSAGE = """⚠️ הטוקן לא נראה תקין.

טוקן תקין צריך להיות בפורמט:
`123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`

נסה שוב או שלח /cancel לביטול."""

# קוד עזר לשמירת מצב - יתווסף אוטומטית לכל בוט שנוצר
# Note: Double curly braces {{ }} are escaped for .format() - they become single { } in output
STATE_HELPER_CODE = '''# === MongoDB State Helpers (auto-generated) ===
import os
from pymongo import MongoClient

_state_mongo_client = None
_state_mongo_db = None
BOT_ID = "{bot_id}"

def _get_state_db():
    """מחזיר חיבור ל-MongoDB לשמירת מצב."""
    global _state_mongo_client, _state_mongo_db
    if _state_mongo_db is None:
        mongo_uri = os.environ.get("MONGO_URI")
        if mongo_uri:
            try:
                _state_mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
                _state_mongo_db = _state_mongo_client.get_database("bot_factory")
            except Exception:
                return None
    return _state_mongo_db

def save_state(user_id, key, value):
    """
    שומר מידע ב-MongoDB עבור משתמש ספציפי.
    
    Args:
        user_id: מזהה המשתמש
        key: מפתח לשמירה (כמו "score", "game_state", "preferences")
        value: הערך לשמירה (יכול להיות מספר, מחרוזת, רשימה או מילון)
    
    Returns:
        bool: האם השמירה הצליחה
    """
    db = _get_state_db()
    if db is None:
        return False
    try:
        db.bot_states.update_one(
            {{"bot_id": BOT_ID, "user_id": str(user_id), "key": key}},
            {{"$set": {{"value": value}}}},
            upsert=True
        )
        return True
    except Exception:
        return False

def load_state(user_id, key, default=None):
    """
    טוען מידע מ-MongoDB עבור משתמש ספציפי.
    
    Args:
        user_id: מזהה המשתמש
        key: מפתח לטעינה
        default: ערך ברירת מחדל אם המפתח לא קיים
    
    Returns:
        הערך השמור או ערך ברירת המחדל
    """
    db = _get_state_db()
    if db is None:
        return default
    try:
        doc = db.bot_states.find_one({{"bot_id": BOT_ID, "user_id": str(user_id), "key": key}})
        return doc.get("value", default) if doc else default
    except Exception:
        return default

# === End of State Helpers ===

'''

CLAUDE_SYSTEM_PROMPT = """אתה המוח מאחורי 'מפעל בוטים מודולרי'. אתה מפתח פייתון מומחה.

עליך לייצר קוד פייתון מושלם שמתאים למבנה הפלאגינים שלנו.

הקוד חייב לכלול בדיוק שתי פונקציות:

1. get_dashboard_widget() - מחזירה מילון עם המבנה הבא:
   {
       "title": "שם הפלאגין",
       "value": "ערך להצגה",
       "label": "תיאור קצר",
       "status": "success/warning/danger/info",
       "icon": "bi-icon-name"  # Bootstrap Icon
   }

2. handle_message(text, user_id=None, context=None) - מקבלת טקסט, מזהה משתמש ו-context:
   - הפלאגין צריך להגיב לכל הודעה שנשלחת אליו (כי זה בוט עצמאי)
   - מבצע לוגיקה ומחזיר תשובה (string)
   - user_id מאפשר לזהות משתמשים ולשמור מידע ייחודי לכל אחד
   - context מכיל מידע נוסף ופונקציות לניהול קבוצות (ראה בהמשך)

=== PERSISTENT STORAGE - MongoDB Helper Functions ===

Two helper functions are pre-injected into every bot for saving/loading user data:

save_state(user_id, key, value) - Saves data to MongoDB
   - user_id: The user's Telegram ID (passed to handle_message)
   - key: A string key like "score", "game_state", "preferences"
   - value: Any JSON-serializable value (int, str, list, dict)
   - Returns: True if saved successfully, False otherwise

load_state(user_id, key, default=None) - Loads data from MongoDB
   - user_id: The user's Telegram ID
   - key: The key to load
   - default: Value to return if key doesn't exist
   - Returns: The saved value or default

Example usage:
   score = load_state(user_id, "score", 0)
   score += 10
   save_state(user_id, "score", score)

IMPORTANT: Do NOT import or define these functions - they are already available!
Do NOT use global variables (like users = {} or scores = []) - use save_state/load_state instead.

=== GROUP MANAGEMENT - Context Object ===

The context parameter contains information about the message and helper functions for group management:

Context properties (read-only):
   context["chat_id"]        - The chat/group ID
   context["chat_type"]      - "private", "group", "supergroup", or "channel"
   context["chat_title"]     - Group name (None for private chats)
   context["message_id"]     - The message ID (for deletion)
   context["user_id"]        - Sender's user ID
   context["username"]       - Sender's username (may be None)
   context["first_name"]     - Sender's first name
   context["is_group"]       - True if this is a group/supergroup
   context["is_private"]     - True if this is a private chat
   context["sender_is_admin"] - True if the sender is an admin in the group

Context functions (for group management):
   context["delete_message"](message_id=None) - Delete a message (current message if no ID given)
   context["ban_user"](user_id, until_date=None) - Ban a user from the group
   context["kick_user"](user_id) - Kick user (can rejoin)
   context["mute_user"](user_id, until_date=None) - Mute a user
   context["unmute_user"](user_id) - Unmute a user
   context["is_admin"](user_id) - Check if a user is admin
   context["reply"](text) - Send a reply to the chat

Example - Anti-spam bot that deletes messages with links from non-admins:
   def handle_message(text, user_id=None, context=None):
       if context and context["is_group"]:
           if "http" in text.lower() and not context["sender_is_admin"]:
               context["delete_message"]()
               return f"⚠️ {context['first_name']}, קישורים מותרים רק לאדמינים!"
       return None

IMPORTANT: 
- context may be None for older bots or the main bot - always check before using!
- The bot must be an ADMIN in the group to use management functions
- Always check sender_is_admin before allowing dangerous commands

=== CRITICAL TECHNICAL CONSTRAINTS ===

Passive Mode Only: The bot can only reply to messages it receives. It CANNOT proactively send scheduled messages or run background tasks without a trigger.

Refusal: If the user asks for "Auto-Forwarder" or automatic scheduled messages, politely explain that you cannot build these types of bots yet (requires background workers).

=== הנחיות קריטיות ליצירת הקוד ===

חובת /start:
- הפונקציה handle_message חייבת תמיד לזהות ולטפל בפקודה /start
- זו הפקודה הראשונה שכל משתמש שולח לבוט

תפריט ראשי:
- התגובה לפקודת /start חייבת להיות בעברית
- התגובה חייבת לכלול רשימה ברורה של כל הפקודות הזמינות בבוט
- לדוגמה: "ברוכים הבאים! הפקודות הזמינות:\n/new_game - להתחיל משחק חדש\n/stats - לצפות בסטטיסטיקות\n/help - עזרה"

פקודות גנריות:
- אל תשתמש בטוקן או בשם הקובץ כחלק מהפקודה
- אסור להשתמש בפקודות כמו /bot_123 או /plugin_name
- השתמש בפקודות טבעיות באנגלית בלבד (כמו /stats, /help, /reset, /new_game, /score)

טיפול בשגיאות:
- אם המשתמש שולח פקודה או הודעה לא מוכרת, הבוט צריך להחזיר הודעה ידידותית
- ההודעה צריכה להציע למשתמש ללחוץ על /start כדי לראות את רשימת הפקודות הזמינות
- לדוגמה: "לא הבנתי את הבקשה 🤔\nשלח /start כדי לראות את כל הפקודות הזמינות"

=== Available Libraries ===
You have the following libraries pre-installed. You MAY import them without asking:
- Data & Math: numpy, pandas, scipy
- HTTP & Web: requests, beautifulsoup4, httpx, aiohttp, feedparser
- Files & Documents: openpyxl, pypdf, pyyaml
- Images & Charts: Pillow, matplotlib, qrcode
- Database: pymongo, redis
- Date & Time: python-dateutil, pytz
- Text & Validation: regex, pydantic, validators, phonenumbers, langdetect, emoji
- Utilities: cachetools, schedule, tenacity
- Finance: yfinance, pycoingecko

=== STRICT RULE - Library Restrictions ===
Do NOT try to import any other external library that is not listed above!
Forbidden libraries include (but not limited to): cv2, opencv, sklearn, scikit-learn, selenium, playwright, fastapi, django, tensorflow, pytorch, keras, transformers.

If the user asks for a feature requiring a missing library, you MUST implement a workaround using:
1. Standard Python libraries (json, re, math, random, datetime, collections, itertools, functools, etc.)
2. The available libraries listed above

Examples of workarounds:
- Instead of sklearn for simple regression → use numpy for the math calculations
- Instead of cv2 for basic image operations → use Pillow
- Instead of selenium for web scraping → use requests + beautifulsoup4

=== כללים חשובים נוספים ===
- החזר אך ורק את הקוד, ללא הסברים, ללא markdown, ללא ```python
- הקוד חייב להיות תקין ומוכן להרצה
- אם צריך לגשת ל-API חיצוני, השתמש ב-requests עם timeout
- תפוס שגיאות בצורה נכונה והחזר הודעת שגיאה ידידותית
- הבוט הזה יהיה עצמאי ולכן צריך להגיב לכל הודעה
- עטוף את כל הלוגיקה ב-try/except כדי למנוע קריסות"""
SUCCESS_MESSAGE = (
    "✅ הבוט נוצר בהצלחה!\n"
    "📦 הקוד נשמר בגיטהאב\n"
    "🔗 Webhook הוגדר לטלגרם\n"
    "⏳ ה-Deploy האוטומטי התחיל - בעוד כ7 דקות הבוט החדש שלך יהיה פעיל - שלח `/start` בבוט החדש לבדיקה"
)


def _is_creation_in_progress(bot_token):
    """
    בודק אם יש כרגע תהליך יצירה פעיל לטוקן זה.
    מנקה תהליכים ישנים שעברו timeout.
    """
    current_time = time.time()
    
    # ניקוי תהליכים ישנים
    expired = [t for t, start_time in _creation_in_progress.items() 
               if current_time - start_time > _CREATION_TIMEOUT]
    for t in expired:
        _creation_in_progress.pop(t, None)
    
    return bot_token in _creation_in_progress


def _start_creation(bot_token):
    """מסמן שתהליך יצירה התחיל לטוקן זה."""
    _creation_in_progress[bot_token] = time.time()


def _end_creation(bot_token):
    """מסמן שתהליך יצירה הסתיים לטוקן זה."""
    _creation_in_progress.pop(bot_token, None)


def _cleanup_old_conversations():
    """מנקה שיחות ישנות שעברו timeout."""
    current_time = time.time()
    expired = [uid for uid, data in _user_conversations.items()
               if current_time - data.get("timestamp", 0) > _CONVERSATION_TIMEOUT]
    for uid in expired:
        _user_conversations.pop(uid, None)


def _get_user_state(user_id):
    """מחזיר את מצב השיחה של המשתמש."""
    _cleanup_old_conversations()
    return _user_conversations.get(user_id, {}).get("state")


def _set_user_state(user_id, state, token=None):
    """מגדיר את מצב השיחה של המשתמש."""
    if state is None:
        _user_conversations.pop(user_id, None)
    else:
        data = {"state": state, "timestamp": time.time()}
        if token:
            data["token"] = token
        elif user_id in _user_conversations and "token" in _user_conversations[user_id]:
            data["token"] = _user_conversations[user_id]["token"]
        _user_conversations[user_id] = data


def _get_user_token(user_id):
    """מחזיר את הטוקן ששמרנו עבור המשתמש."""
    return _user_conversations.get(user_id, {}).get("token")


def _create_inline_keyboard(buttons):
    """
    יוצר inline keyboard לטלגרם.
    
    Args:
        buttons: רשימת רשימות של כפתורים. כל כפתור הוא dict עם text ו-callback_data.
    
    Returns:
        dict: reply_markup מוכן לשליחה לטלגרם
    """
    return {
        "inline_keyboard": buttons
    }


def _notify_admin(message, error_type="general"):
    """
    שולח התראה לאדמין בטלגרם.
    
    Args:
        message: תוכן ההתראה
        error_type: סוג השגיאה (quota, api_error, general)
    """
    admin_chat_id = Config.ADMIN_CHAT_ID
    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    
    if not admin_chat_id or not telegram_token:
        print(f"⚠️ Admin notification skipped (missing ADMIN_CHAT_ID or TELEGRAM_TOKEN): {message}")
        return
    
    # הוספת אייקון לפי סוג השגיאה
    icons = {
        "quota": "🚨",
        "api_error": "⚠️",
        "general": "ℹ️",
    }
    icon = icons.get(error_type, "ℹ️")
    
    full_message = f"{icon} *התראת מערכת - Architect*\n\n{message}"
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{telegram_token}/sendMessage",
            json={
                "chat_id": admin_chat_id,
                "text": full_message,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
        print(f"✅ Admin notified: {error_type}")
    except Exception as e:
        print(f"❌ Failed to notify admin: {e}")


def _register_bot_in_mongodb(bot_token, plugin_filename):
    """
    רושם בוט חדש ב-MongoDB.
    זה מאפשר לבוט החדש לעבוד מיד.
    
    Args:
        bot_token: טוקן הבוט
        plugin_filename: שם קובץ הפלאגין
    
    Returns:
        tuple: (success: bool, error: str or None)
    """
    db = _get_mongo_db()
    if db is None:
        return False, "MongoDB לא מוגדר. הוסף MONGO_URI למשתני הסביבה."
    
    try:
        # upsert - עדכן אם קיים, צור אם לא
        db.bot_registry.update_one(
            {"token": bot_token},
            {"$set": {
                "token": bot_token,
                "plugin_filename": plugin_filename,
                "created_at": datetime.datetime.utcnow()
            }},
            upsert=True
        )
        print(f"✅ Bot registered in MongoDB: {plugin_filename}")
        return True, None
    except Exception as e:
        print(f"❌ Failed to register bot in MongoDB: {e}")
        return False, f"שגיאה ברישום ב-MongoDB: {e}"


def _bot_exists_in_mongodb(bot_token):
    """
    בודק אם בוט עם הטוקן הזה כבר קיים ב-MongoDB.
    
    Args:
        bot_token: טוקן הבוט
    
    Returns:
        bool: האם הבוט קיים
    """
    db = _get_mongo_db()
    if db is None:
        return False
    
    try:
        result = db.bot_registry.find_one({"token": bot_token})
        return result is not None
    except Exception as e:
        print(f"❌ Error checking bot in MongoDB: {e}")
        return False


def _get_admin_stats(user_id):
    """
    מחזיר סטטיסטיקות מערכת - לאדמין בלבד.
    
    Args:
        user_id: מזהה המשתמש
    
    Returns:
        dict או str: תגובה עם סטטיסטיקות או הודעת שגיאה
    """
    # בדיקת הרשאות אדמין
    admin_chat_id = Config.ADMIN_CHAT_ID
    if not admin_chat_id or str(user_id) != str(admin_chat_id):
        return "⛔ פקודה זו זמינה לאדמין בלבד."
    
    db = _get_mongo_db()
    if db is None:
        return "❌ MongoDB לא מוגדר. אין גישה לסטטיסטיקות."
    
    try:
        # חישוב תאריך לפני שבוע
        one_week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        
        # ספירת משתמשים ייחודיים בשבוע האחרון
        unique_users_pipeline = [
            {"$match": {"timestamp": {"$gte": one_week_ago}}},
            {"$group": {"_id": "$user_id"}},
            {"$count": "total"}
        ]
        unique_users_result = list(db.user_actions.aggregate(unique_users_pipeline))
        unique_users_count = unique_users_result[0]["total"] if unique_users_result else 0
        
        # סה"כ פעולות בשבוע האחרון
        total_actions = db.user_actions.count_documents({"timestamp": {"$gte": one_week_ago}})
        
        # פעולות לפי סוג
        actions_by_type_pipeline = [
            {"$match": {"timestamp": {"$gte": one_week_ago}}},
            {"$group": {"_id": "$action_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        actions_by_type = list(db.user_actions.aggregate(actions_by_type_pipeline))
        
        # טופ 10 משתמשים פעילים
        top_users_pipeline = [
            {"$match": {"timestamp": {"$gte": one_week_ago}}},
            {"$group": {"_id": "$user_id", "actions": {"$sum": 1}}},
            {"$sort": {"actions": -1}},
            {"$limit": 10}
        ]
        top_users = list(db.user_actions.aggregate(top_users_pipeline))
        
        # מספר בוטים רשומים
        total_bots = db.bot_registry.count_documents({})
        
        # בניית ההודעה
        stats_message = f"""📊 *סטטיסטיקות מערכת - 7 ימים אחרונים*

👥 *משתמשים:*
• משתמשים ייחודיים: {unique_users_count}
• סה"כ פעולות: {total_actions}

🤖 *בוטים רשומים:* {total_bots}

📈 *פעולות לפי סוג:*"""
        
        for action in actions_by_type:
            action_type = action["_id"] or "unknown"
            count = action["count"]
            emoji = {"command": "⌨️", "message": "💬", "callback": "🔘"}.get(action_type, "•")
            stats_message += f"\n{emoji} {action_type}: {count}"
        
        stats_message += "\n\n🏆 *משתמשים פעילים (טופ 10):*"
        
        for i, user in enumerate(top_users, 1):
            user_id_display = user["_id"]
            actions_count = user["actions"]
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            stats_message += f"\n{medal} `{user_id_display}` - {actions_count} פעולות"
        
        if not top_users:
            stats_message += "\nאין נתונים עדיין"
        
        return {
            "text": stats_message,
            "parse_mode": "Markdown"
        }
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return f"❌ שגיאה בשליפת סטטיסטיקות: {e}"


def get_dashboard_widget():
    return {
        "title": "Architect",
        "value": "Ready",
        "label": "Create new bots with /create_bot",
        "status": "info",
        "icon": "bi-building",
    }


def _is_valid_name(name):
    return re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name) is not None


def _normalize_instruction(instruction):
    return " ".join(instruction.strip().split())


def _anthropic_headers(api_key):
    return {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }


def _build_user_prompt(name, instruction):
    normalized = _normalize_instruction(instruction)
    return "\n".join(
        [
            f"שם הפלאגין: {name}",
            f"הנחיית משתמש: {normalized}",
            f"הפלאגין צריך להגיב לפקודה /{name}.",
        ]
    )


def _format_claude_error(response):
    if response.status_code >= 500:
        return "שירות Claude לא זמין כרגע. נסה שוב מאוחר יותר."

    error_text = response.text
    try:
        error_text = response.json()
    except Exception:
        pass
    return f"שגיאה בשירות Claude: {response.status_code} {error_text}"


def _clean_code_from_markdown(code):
    """Remove markdown code fences if Claude returned them despite instructions."""
    code = code.strip()
    # Remove ```python or ``` at the start
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    # Remove ``` at the end
    if code.endswith("```"):
        code = code[:-3]
    return code.strip()


def _extract_claude_code(payload):
    content = payload.get("content") if isinstance(payload, dict) else None
    if not isinstance(content, list):
        return None

    text_parts = [
        part.get("text")
        for part in content
        if isinstance(part, dict) and part.get("type") == "text" and part.get("text")
    ]
    if not text_parts:
        return None
    
    raw_code = "\n".join(text_parts).strip()
    return _clean_code_from_markdown(raw_code)


def _generate_plugin_code(name, instruction):
    api_key = Config.ANTHROPIC_API_KEY
    if not api_key:
        _notify_admin("חסר ANTHROPIC_API_KEY בקונפיגורציה!", "api_error")
        return None, "חסר ANTHROPIC_API_KEY בקונפיגורציה."

    user_prompt = _build_user_prompt(name, instruction)
    data = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 8000,
        "system": CLAUDE_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    try:
        response = requests.post(
            ANTHROPIC_API_URL,
            headers=_anthropic_headers(api_key),
            json=data,
            timeout=120,
        )
        
        # בדיקת שגיאות ספציפיות לפני raise_for_status
        if response.status_code == 429:
            # Rate limit / Quota exceeded
            error_details = ""
            try:
                error_json = response.json()
                error_details = error_json.get("error", {}).get("message", response.text)
            except Exception:
                error_details = response.text
            
            _notify_admin(
                f"*נגמרה מכסת הטוקנים של Claude API!*\n\n"
                f"סטטוס: 429 Rate Limited\n"
                f"פרטים: {error_details[:500]}",
                "quota"
            )
            return None, "🚫 המערכת עמוסה כרגע. נסה שוב מאוחר יותר."
        
        elif response.status_code == 401:
            # Invalid API key
            _notify_admin(
                f"*מפתח API של Claude לא תקין!*\n\n"
                f"סטטוס: 401 Unauthorized\n"
                f"יש לבדוק את ANTHROPIC_API_KEY",
                "api_error"
            )
            return None, "שגיאת הזדהות במערכת. נסה שוב מאוחר יותר."
        
        elif response.status_code == 400:
            # Bad request - might be billing issue
            error_details = ""
            try:
                error_json = response.json()
                error_details = error_json.get("error", {}).get("message", response.text)
            except Exception:
                error_details = response.text
            
            # בדיקה אם זו בעיית חיוב
            if "credit" in error_details.lower() or "billing" in error_details.lower():
                _notify_admin(
                    f"*בעיית חיוב ב-Claude API!*\n\n"
                    f"סטטוס: 400\n"
                    f"פרטים: {error_details[:500]}",
                    "quota"
                )
                return None, "🚫 המערכת לא זמינה כרגע. נסה שוב מאוחר יותר."
        
        elif response.status_code >= 500:
            # Server error
            _notify_admin(
                f"*שגיאת שרת ב-Claude API*\n\n"
                f"סטטוס: {response.status_code}\n"
                f"השירות לא זמין זמנית",
                "api_error"
            )
            return None, "שירות Claude לא זמין כרגע. נסה שוב מאוחר יותר."
        
        response.raise_for_status()
        
    except requests.RequestException as e:
        print(f"Claude API RequestException: {e}")
        try:
            print(f"Claude API Response: {response.text}")
        except Exception:
            pass
        
        _notify_admin(
            f"*שגיאת חיבור ל-Claude API*\n\n"
            f"שגיאה: {str(e)[:300]}",
            "api_error"
        )
        return None, "שירות Claude לא זמין כרגע. נסה שוב מאוחר יותר."

    try:
        response_payload = response.json()
    except ValueError:
        return None, "שגיאה בפענוח תגובת Claude."

    code = _extract_claude_code(response_payload)
    if not code:
        return None, "Claude לא החזיר קוד."

    # הוספת פונקציות העזר לשמירת מצב בתחילת הקוד
    helper_code = STATE_HELPER_CODE.format(bot_id=name)
    full_code = helper_code + code

    return full_code, None


def _get_github_settings():
    token = Config.GITHUB_TOKEN
    user = Config.GITHUB_USER
    repo = Config.GITHUB_REPO
    branch = Config.GITHUB_BRANCH
    if not token or not user or not repo:
        return None, "חסר GITHUB_TOKEN, GITHUB_USER או GITHUB_REPO בקונפיגורציה."
    return {
        "token": token,
        "user": user,
        "repo": repo,
        "branch": branch,
    }, None


def _github_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


def _github_file_exists(settings, path):
    url = f"{GITHUB_API_BASE}/repos/{settings['user']}/{settings['repo']}/contents/{path}"
    params = {}
    if settings.get("branch"):
        params["ref"] = settings["branch"]

    response = requests.get(
        url, headers=_github_headers(settings["token"]), params=params, timeout=10
    )
    if response.status_code == 200:
        return True, None
    if response.status_code == 404:
        return False, None
    return None, f"שגיאה בבדיקת קיום הקובץ: {response.status_code} {response.text}"


def _github_create_file(settings, path, content):
    url = f"{GITHUB_API_BASE}/repos/{settings['user']}/{settings['repo']}/contents/{path}"
    payload = {
        "message": f"Add plugin {path} via architect",
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
    }
    if settings.get("branch"):
        payload["branch"] = settings["branch"]

    response = requests.put(
        url, headers=_github_headers(settings["token"]), json=payload, timeout=10
    )
    if response.status_code in (200, 201):
        return True, None

    error_text = response.text
    try:
        error_text = response.json()
    except Exception:
        pass
    return False, f"שגיאה ביצירת הקובץ בגיטהאב: {response.status_code} {error_text}"


def _github_get_file(settings, path):
    """
    קורא קובץ מגיטהאב ומחזיר את התוכן וה-SHA.
    """
    url = f"{GITHUB_API_BASE}/repos/{settings['user']}/{settings['repo']}/contents/{path}"
    params = {}
    if settings.get("branch"):
        params["ref"] = settings["branch"]

    response = requests.get(
        url, headers=_github_headers(settings["token"]), params=params, timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content, data["sha"], None
    if response.status_code == 404:
        return None, None, None
    return None, None, f"שגיאה בקריאת הקובץ: {response.status_code}"


def _github_update_file(settings, path, content, sha, message):
    """
    מעדכן קובץ קיים בגיטהאב.
    """
    url = f"{GITHUB_API_BASE}/repos/{settings['user']}/{settings['repo']}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "sha": sha,
    }
    if settings.get("branch"):
        payload["branch"] = settings["branch"]

    response = requests.put(
        url, headers=_github_headers(settings["token"]), json=payload, timeout=10
    )
    if response.status_code in (200, 201):
        return True, None
    
    error_text = response.text
    try:
        error_text = response.json()
    except Exception:
        pass
    return False, f"שגיאה בעדכון הקובץ בגיטהאב: {response.status_code} {error_text}"




def _set_telegram_webhook(bot_token):
    """
    מגדיר webhook לטלגרם עבור הבוט החדש.
    """
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not render_url:
        return False, "חסר RENDER_EXTERNAL_URL בקונפיגורציה"
    
    webhook_url = f"{render_url.rstrip('/')}/{bot_token}"
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    try:
        response = requests.post(
            api_url,
            json={"url": webhook_url},
            timeout=10
        )
        if response.ok:
            result = response.json()
            if result.get("ok"):
                return True, None
            return False, f"Telegram API error: {result.get('description', 'Unknown error')}"
        return False, f"שגיאה בהגדרת webhook: {response.status_code}"
    except Exception as e:
        return False, f"שגיאה בהגדרת webhook: {e}"


def _generate_plugin_name_from_token(bot_token):
    """
    יוצר שם פלאגין בטוח מהטוקן.
    משתמש בחלק הראשון של הטוקן (ה-bot_id).
    """
    # הטוקן בפורמט: BOT_ID:HASH
    # ניקח את ה-bot_id ונוסיף prefix
    if ':' in bot_token:
        bot_id = bot_token.split(':')[0]
    else:
        bot_id = bot_token[:10]
    
    return f"bot_{bot_id}"


def handle_callback(callback_data, user_id):
    """
    מטפל בלחיצות על כפתורים (callback queries).
    
    Args:
        callback_data: המידע שנשלח עם הכפתור
        user_id: מזהה המשתמש
    
    Returns:
        dict או str: התגובה לשליחה למשתמש
    """
    if callback_data == "create_bot":
        # המשתמש לחץ על "צור בוט חדש"
        _set_user_state(user_id, "waiting_token")
        return {
            "text": WAITING_TOKEN_MESSAGE,
            "parse_mode": "Markdown"
        }
    
    elif callback_data == "cancel":
        _set_user_state(user_id, None)
        return CANCEL_MESSAGE
    
    return None


def handle_message(text, user_id=None):
    """
    מטפל בהודעות נכנסות.
    תומך בשיחה מונחית עם כפתורים וגם בפקודה הישירה.
    
    Args:
        text: טקסט ההודעה
        user_id: מזהה המשתמש (אופציונלי, נדרש לשיחה מונחית)
    
    Returns:
        dict או str: התגובה לשליחה למשתמש
    """
    if not text:
        return None

    stripped = text.strip()
    
    # פקודת /start - תפריט ראשי עם כפתורים
    if stripped == "/start":
        if user_id:
            _set_user_state(user_id, None)  # אתחול מצב
        return {
            "text": START_MESSAGE,
            "parse_mode": "Markdown",
            "reply_markup": _create_inline_keyboard([
                [{"text": "🚀 צור בוט חדש", "callback_data": "create_bot"}]
            ])
        }
    
    # פקודת /stats - סטטיסטיקות (לאדמין בלבד)
    if stripped == "/stats":
        return _get_admin_stats(user_id)
    
    # פקודת /cancel - ביטול תהליך
    if stripped == "/cancel":
        if user_id:
            _set_user_state(user_id, None)
        return CANCEL_MESSAGE
    
    # פקודת /create_bot - התחלת תהליך יצירה (גם דרך פקודה)
    if stripped == "/create_bot":
        if user_id:
            _set_user_state(user_id, "waiting_token")
        return {
            "text": WAITING_TOKEN_MESSAGE,
            "parse_mode": "Markdown",
            "reply_markup": _create_inline_keyboard([
                [{"text": "❌ ביטול", "callback_data": "cancel"}]
            ])
        }
    
    # בדיקת מצב שיחה אם יש user_id
    if user_id:
        state = _get_user_state(user_id)
        
        # מחכים לטוקן
        if state == "waiting_token":
            # וידוא שהטוקן נראה תקין
            if ':' not in stripped or len(stripped) < 20:
                return {
                    "text": INVALID_TOKEN_MESSAGE,
                    "parse_mode": "Markdown",
                    "reply_markup": _create_inline_keyboard([
                        [{"text": "❌ ביטול", "callback_data": "cancel"}]
                    ])
                }
            
            # שמירת הטוקן ומעבר לשלב הבא
            _set_user_state(user_id, "waiting_description", token=stripped)
            return {
                "text": WAITING_DESCRIPTION_MESSAGE,
                "parse_mode": "Markdown",
                "reply_markup": _create_inline_keyboard([
                    [{"text": "❌ ביטול", "callback_data": "cancel"}]
                ])
            }
        
        # מחכים לתיאור
        if state == "waiting_description":
            bot_token = _get_user_token(user_id)
            if not bot_token:
                _set_user_state(user_id, None)
                return "אירעה שגיאה. שלח /start כדי להתחיל מחדש."
            
            instruction = stripped
            
            # ניקוי מצב השיחה
            _set_user_state(user_id, None)
            
            # יצירת הבוט
            return _create_bot(bot_token, instruction)
    
    # תמיכה בפקודה הישירה (לתאימות אחורה)
    if stripped.startswith(COMMAND_PREFIX):
        parts = stripped.split(maxsplit=2)
        if len(parts) < 3:
            return {
                "text": "שימוש: /create_bot <token> <instruction>\n\n💡 או פשוט שלח /start ותן לי להדריך אותך בתהליך!",
                "reply_markup": _create_inline_keyboard([
                    [{"text": "🚀 צור בוט חדש", "callback_data": "create_bot"}]
                ])
            }
        
        _, bot_token, instruction = parts
        return _create_bot(bot_token, instruction)
    
    return None


def _create_bot(bot_token, instruction):
    """
    יוצר בוט חדש.
    
    Args:
        bot_token: טוקן הבוט מ-BotFather
        instruction: תיאור מה הבוט צריך לעשות
    
    Returns:
        str: הודעת הצלחה או שגיאה
    """
    # וידוא שהטוקן נראה תקין (פורמט בסיסי)
    if ':' not in bot_token or len(bot_token) < 20:
        return "טוקן לא תקין. וודא שהעתקת את הטוקן המלא מ-BotFather."

    # בדיקה אם יש כבר תהליך יצירה פעיל לטוקן זה (מניעת כפילויות)
    if _is_creation_in_progress(bot_token):
        print(f"⏳ Creation already in progress for token: {bot_token[:10]}...")
        return "⏳ הבוט כבר בתהליך יצירה, אנא המתן..."

    # יצירת שם פלאגין מהטוקן
    plugin_name = _generate_plugin_name_from_token(bot_token)

    settings, error = _get_github_settings()
    if error:
        return error

    # בדיקה אם הבוט כבר קיים ב-MongoDB
    if _bot_exists_in_mongodb(bot_token):
        return "בוט עם טוקן זה כבר קיים במערכת. אם תרצה ליצור בוט חדש, השתמש בטוקן אחר."

    plugin_path = f"plugins/{plugin_name}.py"
    exists, error = _github_file_exists(settings, plugin_path)
    if error:
        return error
    if exists:
        return "בוט עם טוקן זה כבר קיים במערכת (קובץ הפלאגין קיים). אם תרצה ליצור בוט חדש, השתמש בטוקן אחר."

    # הודעה שהתהליך התחיל
    print(f"🚀 Starting bot creation for token: {bot_token[:10]}...")
    
    # סימון שתהליך היצירה התחיל (למניעת כפילויות מ-webhook)
    _start_creation(bot_token)

    try:
        # יצירת קוד הפלאגין
        code, error = _generate_plugin_code(plugin_name, instruction)
        if error:
            return error

        # שמירת הקוד בגיטהאב
        created, error = _github_create_file(settings, plugin_path, code)
        if not created:
            return error or "יצירת הבוט נכשלה."

        print(f"✅ Plugin file created on GitHub: {plugin_path}")

        # רישום הבוט ב-MongoDB (מאובטח - לא חשוף בגיטהאב)
        registered, error = _register_bot_in_mongodb(bot_token, f"{plugin_name}.py")
        if not registered:
            return f"הקוד נשמר אבל הרישום ב-MongoDB נכשל: {error}"

        print(f"✅ Bot registered in MongoDB: {plugin_name}")

        # הגדרת webhook לטלגרם
        webhook_set, error = _set_telegram_webhook(bot_token)
        if not webhook_set:
            return f"הקוד נשמר והבוט נרשם, אבל הגדרת ה-Webhook נכשלה: {error}"

        print(f"✅ Webhook set for bot: {plugin_name}")

        return SUCCESS_MESSAGE
    finally:
        # סימון שתהליך היצירה הסתיים
        _end_creation(bot_token)
