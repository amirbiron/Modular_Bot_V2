# Architect Plugin - creates new plugins via GitHub API
# תומך ביצירת בוטים חדשים עבור מערכת SaaS
# כולל ממשק כפתורים ושיחה מונחית
# משתמש ב-MongoDB לאחסון מאובטח של טוקנים

import base64
import json
import os
import re
import time
import uuid
import datetime
import requests
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, DuplicateKeyError

from config import Config
from engine.app import log_funnel_event


COMMAND_PREFIX = "/create_bot"
GITHUB_API_BASE = "https://api.github.com"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
ANTHROPIC_VERSION = "2023-06-01"

# הגבלת יצירת בוטים למשתמש ליום
MAX_BOTS_PER_USER_PER_DAY = 2

# נתיב לתיקיית הפרויקט
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# MongoDB connection (lazy initialization)
_mongo_client = None
_mongo_db = None
_funnel_indexes_ready = False


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
        _ensure_funnel_indexes(_mongo_db)
        return _mongo_db
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"❌ MongoDB connection failed in architect: {e}")
        return None
    except Exception as e:
        print(f"❌ MongoDB error in architect: {e}")
        return None


def _ensure_funnel_indexes(db):
    """
    יוצר אינדקסים נדרשים למשפך ההמרה (Idempotent).
    """
    global _funnel_indexes_ready
    
    if _funnel_indexes_ready or db is None:
        return
    
    try:
        # === bot_flows ===
        db.bot_flows.create_index([("user_id", 1), ("final_status", 1)])
        db.bot_flows.create_index(
            [("bot_token_id", 1)],
            unique=True,
            partialFilterExpression={"bot_token_id": {"$type": "string"}}
        )
        db.bot_flows.create_index([("created_at", -1)])
        db.bot_flows.create_index([("updated_at", -1)])
        db.bot_flows.create_index([("current_stage", 1), ("created_at", -1)])
        
        # === funnel_events ===
        db.funnel_events.create_index([("timestamp", -1), ("event_type", 1)])
        db.funnel_events.create_index([("flow_id", 1), ("event_type", 1)])
        db.funnel_events.create_index([("bot_token_id", 1), ("event_type", 1)])
        db.funnel_events.create_index(
            [("timestamp", 1)],
            expireAfterSeconds=7776000
        )
        
        _funnel_indexes_ready = True
    except Exception as e:
        print(f"⚠️ Failed to ensure funnel indexes in architect: {e}")

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


def _generate_flow_id():
    """יוצר מזהה ייחודי לניסיון יצירה."""
    return f"f_{uuid.uuid4().hex[:12]}"


def _create_flow(user_id):
    """
    יוצר flow חדש ושומר ב-DB מיד (לא רק בזיכרון!).
    """
    db = _get_mongo_db()
    if db is None:
        return None
    
    flow_id = _generate_flow_id()
    now = datetime.datetime.utcnow()
    
    try:
        db.bot_flows.insert_one({
            "_id": flow_id,
            "user_id": str(user_id),
            "creator_id": str(user_id),
            "status": "started",
            "current_stage": 1,
            "bot_token_id": None,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "final_status": None,
            "stage_times": {"stage_1_at": now}
        })
        return flow_id
    except Exception as e:
        print(f"❌ Failed to create flow: {e}")
        return None


def _update_flow(flow_id, status=None, stage=None, bot_token_id=None, final_status=None):
    """
    מעדכן flow קיים ב-DB.
    כולל State Machine Guardrails למניעת רגרסיה!
    """
    db = _get_mongo_db()
    if db is None or not flow_id:
        return
    
    now = datetime.datetime.utcnow()
    updates = {"updated_at": now}
    
    if status:
        updates["status"] = status
    
    if bot_token_id:
        updates["bot_token_id"] = bot_token_id
    
    if final_status:
        updates["final_status"] = final_status
        updates["completed_at"] = now
    
    # 🛡️ Stage Guardrail: רק קדימה, לא אחורה!
    if stage:
        current_flow = db.bot_flows.find_one({"_id": flow_id}, {"current_stage": 1})
        current_stage = current_flow.get("current_stage", 0) if current_flow else 0
        
        if stage > current_stage or final_status in ("failed", "cancelled"):
            updates["current_stage"] = stage
            updates[f"stage_times.stage_{stage}_at"] = now
    
    db.bot_flows.update_one({"_id": flow_id}, {"$set": updates})


def _get_flow(flow_id):
    """שולף flow מה-DB."""
    db = _get_mongo_db()
    if db is None or not flow_id:
        return None
    return db.bot_flows.find_one({"_id": flow_id})


def _is_token_used_in_flow(bot_token_id, exclude_flow_id=None):
    """
    בודק אם ה-bot_token_id כבר קיים ב-flow אחר.
    
    Args:
        bot_token_id: מזהה הטוקן (החלק הראשון לפני הנקודתיים)
        exclude_flow_id: flow_id לא לספור (כדי לא לספור את ה-flow הנוכחי)
    
    Returns:
        bool: האם הטוקן כבר בשימוש
    """
    db = _get_mongo_db()
    if db is None or not bot_token_id:
        return False
    
    try:
        query = {"bot_token_id": bot_token_id}
        if exclude_flow_id:
            query["_id"] = {"$ne": exclude_flow_id}
        
        existing = db.bot_flows.find_one(query)
        return existing is not None
    except Exception as e:
        print(f"❌ Error checking token in flows: {e}")
        return False


def _get_user_active_flow(user_id):
    """
    שולף flow פעיל של משתמש (לשחזור אחרי restart).
    """
    db = _get_mongo_db()
    if db is None:
        return None
    
    return db.bot_flows.find_one({
        "user_id": str(user_id),
        "final_status": None
    }, sort=[("created_at", -1)])


def _get_user_flow_id(user_id):
    """
    מחזיר את ה-flow_id של המשתמש.
    קודם מזיכרון, אם אין - מנסה לשחזר מ-DB.
    """
    flow_id = _user_conversations.get(user_id, {}).get("flow_id")
    if flow_id:
        return flow_id
    
    active_flow = _get_user_active_flow(user_id)
    if active_flow:
        _user_conversations[user_id] = {
            "flow_id": active_flow["_id"],
            "state": active_flow.get("status"),
            "token": None,
            "timestamp": time.time()
        }
        return active_flow["_id"]
    
    return None


def _get_user_state(user_id):
    """מחזיר את מצב השיחה של המשתמש."""
    _cleanup_old_conversations()
    state = _user_conversations.get(user_id, {}).get("state")
    if state:
        return state
    
    # אם אין בזיכרון - נסה לשחזר מ-DB (אחרי restart)
    active_flow = _get_user_active_flow(user_id)
    if active_flow:
        _user_conversations[user_id] = {
            "flow_id": active_flow["_id"],
            "state": active_flow.get("status"),
            "token": None,
            "timestamp": time.time()
        }
        return active_flow.get("status")
    
    return None


def _set_user_state(user_id, state, token=None, flow_id=None):
    """מגדיר את מצב השיחה של המשתמש."""
    if state is None:
        # ניקוי - גם מזיכרון וגם לסגור flow ב-DB אם פתוח
        old_flow_id = _user_conversations.get(user_id, {}).get("flow_id")
        if old_flow_id:
            _update_flow(old_flow_id, final_status="cancelled")
            log_funnel_event(user_id, "flow_cancelled", flow_id=old_flow_id,
                             unique_key=f"cancel_{old_flow_id}")
        
        _user_conversations.pop(user_id, None)
    else:
        data = {"state": state, "timestamp": time.time()}
        if token:
            data["token"] = token
        elif user_id in _user_conversations and "token" in _user_conversations[user_id]:
            data["token"] = _user_conversations[user_id]["token"]
        
        if flow_id:
            data["flow_id"] = flow_id
        elif user_id in _user_conversations:
            data["flow_id"] = _user_conversations[user_id].get("flow_id")
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


def _register_bot_in_mongodb(bot_token, plugin_filename, user_id=None):
    """
    רושם בוט חדש ב-MongoDB.
    זה מאפשר לבוט החדש לעבוד מיד.
    
    Args:
        bot_token: טוקן הבוט
        plugin_filename: שם קובץ הפלאגין
        user_id: מזהה המשתמש שיצר את הבוט (אופציונלי)
    
    Returns:
        tuple: (success: bool, error: str or None)
    """
    db = _get_mongo_db()
    if db is None:
        return False, "MongoDB לא מוגדר. הוסף MONGO_URI למשתני הסביבה."
    
    try:
        # בניית המסמך לשמירה
        doc = {
            "token": bot_token,
            "plugin_filename": plugin_filename,
            "created_at": datetime.datetime.utcnow()
        }
        
        # הוספת מזהה היוצר אם קיים
        if user_id:
            doc["created_by_user_id"] = str(user_id)
        
        # upsert - עדכן אם קיים, צור אם לא
        db.bot_registry.update_one(
            {"token": bot_token},
            {"$set": doc},
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


def _get_user_bots_created_today(user_id):
    """
    מחזיר את מספר הבוטים שהמשתמש יצר ב-24 השעות האחרונות.
    
    Args:
        user_id: מזהה המשתמש בטלגרם
    
    Returns:
        int: מספר הבוטים שנוצרו היום
    """
    if not user_id:
        return 0
    
    db = _get_mongo_db()
    if db is None:
        return 0
    
    try:
        # חישוב תאריך לפני 24 שעות
        twenty_four_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        
        # ספירת בוטים שנוצרו על ידי המשתמש ב-24 שעות האחרונות
        count = db.bot_registry.count_documents({
            "created_by_user_id": str(user_id),
            "created_at": {"$gte": twenty_four_hours_ago}
        })
        return count
    except Exception as e:
        print(f"❌ Error counting user bots: {e}")
        return 0


def _can_user_create_bot(user_id):
    """
    בודק אם המשתמש יכול ליצור בוט נוסף (לא עבר את המגבלה היומית).
    
    Args:
        user_id: מזהה המשתמש בטלגרם
    
    Returns:
        tuple: (can_create: bool, bots_created_today: int)
    """
    if not user_id:
        # אם אין user_id, נאפשר יצירה (לתאימות אחורה)
        return True, 0
    
    # אדמין לא מוגבל
    admin_chat_id = Config.ADMIN_CHAT_ID
    if admin_chat_id and str(user_id) == str(admin_chat_id):
        return True, 0
    
    bots_created_today = _get_user_bots_created_today(user_id)
    can_create = bots_created_today < MAX_BOTS_PER_USER_PER_DAY
    return can_create, bots_created_today


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




def _set_telegram_webhook(bot_token, max_retries=3):
    """
    מגדיר webhook לטלגרם עבור הבוט החדש.
    כולל retry logic עם exponential backoff.
    """
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not render_url:
        return False, "חסר RENDER_EXTERNAL_URL בקונפיגורציה"
    
    webhook_url = f"{render_url.rstrip('/')}/{bot_token}"
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    last_error = None
    for attempt in range(max_retries):
        try:
            # timeout גדל עם כל ניסיון: 30, 45, 60 שניות
            timeout = 30 + (attempt * 15)
            response = requests.post(
                api_url,
                json={"url": webhook_url},
                timeout=timeout
            )
            if response.ok:
                result = response.json()
                if result.get("ok"):
                    if attempt > 0:
                        print(f"✅ Webhook set successfully on attempt {attempt + 1}")
                    return True, None
                return False, f"Telegram API error: {result.get('description', 'Unknown error')}"
            last_error = f"שגיאה בהגדרת webhook: {response.status_code}"
        except requests.exceptions.Timeout:
            last_error = f"Timeout בניסיון {attempt + 1}/{max_retries}"
            print(f"⏳ Webhook timeout (attempt {attempt + 1}/{max_retries}), retrying...")
        except Exception as e:
            last_error = f"שגיאה בהגדרת webhook: {e}"
            print(f"⚠️ Webhook error (attempt {attempt + 1}/{max_retries}): {e}")
        
        # המתנה לפני ניסיון נוסף (exponential backoff: 2, 4, 8 שניות)
        if attempt < max_retries - 1:
            time.sleep(2 ** (attempt + 1))
    
    return False, last_error


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
        # בדיקת מגבלה יומית לפני התחלת התהליך
        can_create, bots_today = _can_user_create_bot(user_id)
        if not can_create:
            return {
                "text": f"⚠️ *הגעת למגבלה היומית!*\n\nיצרת כבר {bots_today} בוטים ב-24 השעות האחרונות.\n\nהמגבלה היא {MAX_BOTS_PER_USER_PER_DAY} בוטים ליום.\nנסה שוב מחר 🙏",
                "parse_mode": "Markdown"
            }
        
        # המשתמש לחץ על "צור בוט חדש"
        flow_id = _create_flow(user_id)
        if not flow_id:
            return "אירעה שגיאה, נסה שוב"
        
        _set_user_state(user_id, "waiting_token", flow_id=flow_id)
        _update_flow(flow_id, status="waiting_token", stage=1)
        
        log_funnel_event(user_id, "flow_started", flow_id=flow_id,
                         unique_key=f"start_{flow_id}")
        
        # הוספת מידע על המגבלה
        remaining = MAX_BOTS_PER_USER_PER_DAY - bots_today
        limit_info = f"\n\n📊 _נותרו לך {remaining} בוטים להיום_" if bots_today > 0 else ""
        
        return {
            "text": WAITING_TOKEN_MESSAGE + limit_info,
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
            # בדיקת מגבלה יומית לפני התחלת התהליך
            can_create, bots_today = _can_user_create_bot(user_id)
            if not can_create:
                return {
                    "text": f"⚠️ *הגעת למגבלה היומית!*\n\nיצרת כבר {bots_today} בוטים ב-24 השעות האחרונות.\n\nהמגבלה היא {MAX_BOTS_PER_USER_PER_DAY} בוטים ליום.\nנסה שוב מחר 🙏",
                    "parse_mode": "Markdown"
                }
            
            flow_id = _create_flow(user_id)
            if not flow_id:
                return "אירעה שגיאה, נסה שוב"
            
            _set_user_state(user_id, "waiting_token", flow_id=flow_id)
            _update_flow(flow_id, status="waiting_token", stage=1)
            
            log_funnel_event(user_id, "flow_started", flow_id=flow_id,
                             unique_key=f"start_{flow_id}")
            
            # הוספת מידע על המגבלה
            remaining = MAX_BOTS_PER_USER_PER_DAY - bots_today
            limit_info = f"\n\n📊 _נותרו לך {remaining} בוטים להיום_" if bots_today > 0 else ""
            
            return {
                "text": WAITING_TOKEN_MESSAGE + limit_info,
                "parse_mode": "Markdown",
                "reply_markup": _create_inline_keyboard([
                    [{"text": "❌ ביטול", "callback_data": "cancel"}]
                ])
            }
        # אם אין user_id, נחזיר הודעה רגילה
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
            flow_id = _get_user_flow_id(user_id)
            if not flow_id:
                _set_user_state(user_id, None)
                return "אירעה שגיאה. שלח /start כדי להתחיל מחדש."
            
            # וידוא שהטוקן נראה תקין
            if ':' not in stripped or len(stripped) < 20:
                log_funnel_event(user_id, "invalid_token_attempt", flow_id=flow_id,
                                 metadata={"token_preview": stripped[:10]})
                return {
                    "text": INVALID_TOKEN_MESSAGE,
                    "parse_mode": "Markdown",
                    "reply_markup": _create_inline_keyboard([
                        [{"text": "❌ ביטול", "callback_data": "cancel"}]
                    ])
                }
            
            # שמירת הטוקן ומעבר לשלב הבא
            bot_token_id = stripped.split(':')[0] if ':' in stripped else None
            
            # בדיקה אם הטוקן כבר בשימוש ב-flow אחר
            if _is_token_used_in_flow(bot_token_id, exclude_flow_id=flow_id):
                log_funnel_event(user_id, "token_already_used", flow_id=flow_id,
                                 bot_token_id=bot_token_id,
                                 metadata={"error": "duplicate_token_in_flow"})
                _set_user_state(user_id, None)
                _update_flow(flow_id, final_status="failed")
                return {
                    "text": "⚠️ *טוקן זה כבר בשימוש*\n\nנראה שכבר התחלת תהליך יצירה עם הטוקן הזה בעבר.\n\nאם הבוט לא נוצר, נסה ליצור טוקן חדש ב-@BotFather ושלח /start כדי להתחיל מחדש.",
                    "parse_mode": "Markdown",
                    "reply_markup": _create_inline_keyboard([
                        [{"text": "🚀 התחל מחדש", "callback_data": "create_bot"}]
                    ])
                }
            
            try:
                _update_flow(flow_id, status="waiting_description", stage=2, bot_token_id=bot_token_id)
            except DuplicateKeyError:
                # מקרה קצה - טוקן נוסף בין הבדיקה לעדכון
                log_funnel_event(user_id, "token_already_used", flow_id=flow_id,
                                 bot_token_id=bot_token_id,
                                 metadata={"error": "duplicate_key_error"})
                _set_user_state(user_id, None)
                return {
                    "text": "⚠️ *טוקן זה כבר בשימוש*\n\nנסה ליצור טוקן חדש ב-@BotFather ושלח /start כדי להתחיל מחדש.",
                    "parse_mode": "Markdown",
                    "reply_markup": _create_inline_keyboard([
                        [{"text": "🚀 התחל מחדש", "callback_data": "create_bot"}]
                    ])
                }
            
            _set_user_state(user_id, "waiting_description", token=stripped, flow_id=flow_id)
            
            log_funnel_event(user_id, "token_accepted", flow_id=flow_id,
                             bot_token_id=bot_token_id,
                             unique_key=f"token_{flow_id}")
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
            flow_id = _get_user_flow_id(user_id)
            if not bot_token:
                _set_user_state(user_id, None)
                return "אירעה שגיאה. שלח /start כדי להתחיל מחדש."
            if not flow_id:
                _set_user_state(user_id, None)
                return "אירעה שגיאה. שלח /start כדי להתחיל מחדש."
            
            instruction = stripped
            
            # סימון מעבר ליצירה
            _set_user_state(user_id, "creating", token=bot_token, flow_id=flow_id)
            
            # יצירת הבוט - כולל מזהה המשתמש לבדיקת מגבלות
            result = _create_bot(bot_token, instruction, user_id, flow_id=flow_id)
            return result
    
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
        
        flow_id = _create_flow(user_id) if user_id else None
        if flow_id:
            _update_flow(flow_id, status="waiting_token", stage=1)
            log_funnel_event(user_id, "flow_started", flow_id=flow_id,
                             unique_key=f"start_{flow_id}")
        
        if flow_id and ':' in bot_token and len(bot_token) >= 20:
            bot_token_id = bot_token.split(':')[0]
            try:
                _update_flow(flow_id, status="waiting_description", stage=2,
                             bot_token_id=bot_token_id)
                log_funnel_event(user_id, "token_accepted", flow_id=flow_id,
                                 bot_token_id=bot_token_id,
                                 unique_key=f"token_{flow_id}")
            except DuplicateKeyError:
                # טוקן כבר בשימוש - לא נעצור את התהליך, פשוט לא נעדכן את ה-flow
                print(f"⚠️ Token {bot_token_id} already used in another flow")
        
        return _create_bot(bot_token, instruction, user_id, flow_id=flow_id)
    
    return None


def _fail_flow(flow_id, user_id, bot_token_id, error_message):
    """
    מסמן flow ככשלון ושומר אירוע.
    """
    if not flow_id:
        return
    try:
        _update_flow(flow_id, status="failed", final_status="failed", bot_token_id=bot_token_id)
    except DuplicateKeyError:
        # אם יש כפילות, נעדכן בלי ה-bot_token_id
        _update_flow(flow_id, status="failed", final_status="failed")
    log_funnel_event(user_id, "creation_failed", flow_id=flow_id,
                     bot_token_id=bot_token_id,
                     metadata={"error": error_message})


def _create_bot(bot_token, instruction, user_id=None, flow_id=None):
    """
    יוצר בוט חדש.
    
    Args:
        bot_token: טוקן הבוט מ-BotFather
        instruction: תיאור מה הבוט צריך לעשות
        user_id: מזהה המשתמש שיוצר את הבוט (לבדיקת מגבלות)
        flow_id: מזהה ניסיון היצירה (למשפך ההמרה)
    
    Returns:
        str: הודעת הצלחה או שגיאה
    """
    bot_token_id = bot_token.split(':')[0] if ':' in bot_token else None
    
    # וידוא שהטוקן נראה תקין (פורמט בסיסי)
    if ':' not in bot_token or len(bot_token) < 20:
        if flow_id:
            log_funnel_event(user_id, "invalid_token_attempt", flow_id=flow_id,
                             metadata={"token_preview": bot_token[:10]})
        return "טוקן לא תקין. וודא שהעתקת את הטוקן המלא מ-BotFather."
    
    # עדכון flow לשלב יצירה + לוג תיאור
    if flow_id:
        try:
            _update_flow(flow_id, status="creating", stage=3, bot_token_id=bot_token_id)
        except DuplicateKeyError:
            # טוקן כבר בשימוש ב-flow אחר
            return {
                "text": "⚠️ *טוקן זה כבר בשימוש*\n\nנראה שכבר התחלת תהליך יצירה עם הטוקן הזה בעבר.\n\nאם הבוט לא נוצר, נסה ליצור טוקן חדש ב-@BotFather ושלח /start כדי להתחיל מחדש.",
                "parse_mode": "Markdown"
            }
        log_funnel_event(user_id, "description_submitted", flow_id=flow_id,
                         bot_token_id=bot_token_id,
                         unique_key=f"desc_{flow_id}")

    # בדיקת מגבלת יצירת בוטים יומית
    can_create, bots_today = _can_user_create_bot(user_id)
    if not can_create:
        remaining_text = f"יצרת כבר {bots_today} בוטים ב-24 השעות האחרונות."
        error_message = (
            f"⚠️ הגעת למגבלה היומית!\n\n{remaining_text}\n\n"
            f"המגבלה היא {MAX_BOTS_PER_USER_PER_DAY} בוטים ליום.\nנסה שוב מחר 🙏"
        )
        _fail_flow(flow_id, user_id, bot_token_id, error_message)
        return error_message

    # בדיקה אם יש כבר תהליך יצירה פעיל לטוקן זה (מניעת כפילויות)
    if _is_creation_in_progress(bot_token):
        print(f"⏳ Creation already in progress for token: {bot_token[:10]}...")
        return "⏳ הבוט כבר בתהליך יצירה, אנא המתן..."

    # יצירת שם פלאגין מהטוקן
    plugin_name = _generate_plugin_name_from_token(bot_token)

    settings, error = _get_github_settings()
    if error:
        _fail_flow(flow_id, user_id, bot_token_id, error)
        return error

    # בדיקה אם הבוט כבר קיים ב-MongoDB
    if _bot_exists_in_mongodb(bot_token):
        error_message = "בוט עם טוקן זה כבר קיים במערכת. אם תרצה ליצור בוט חדש, השתמש בטוקן אחר."
        _fail_flow(flow_id, user_id, bot_token_id, error_message)
        return error_message

    plugin_path = f"plugins/{plugin_name}.py"
    exists, error = _github_file_exists(settings, plugin_path)
    if error:
        _fail_flow(flow_id, user_id, bot_token_id, error)
        return error
    if exists:
        error_message = (
            "בוט עם טוקן זה כבר קיים במערכת (קובץ הפלאגין קיים). "
            "אם תרצה ליצור בוט חדש, השתמש בטוקן אחר."
        )
        _fail_flow(flow_id, user_id, bot_token_id, error_message)
        return error_message

    # הודעה שהתהליך התחיל
    print(f"🚀 Starting bot creation for token: {bot_token[:10]}... (user: {user_id})")
    
    # סימון שתהליך היצירה התחיל (למניעת כפילויות מ-webhook)
    _start_creation(bot_token)

    try:
        # יצירת קוד הפלאגין
        code, error = _generate_plugin_code(plugin_name, instruction)
        if error:
            _fail_flow(flow_id, user_id, bot_token_id, error)
            return error

        # שמירת הקוד בגיטהאב
        created, error = _github_create_file(settings, plugin_path, code)
        if not created:
            error_message = error or "יצירת הבוט נכשלה."
            _fail_flow(flow_id, user_id, bot_token_id, error_message)
            return error_message

        print(f"✅ Plugin file created on GitHub: {plugin_path}")

        # רישום הבוט ב-MongoDB (מאובטח - לא חשוף בגיטהאב) - כולל מזהה היוצר
        registered, error = _register_bot_in_mongodb(bot_token, f"{plugin_name}.py", user_id)
        if not registered:
            error_message = f"הקוד נשמר אבל הרישום ב-MongoDB נכשל: {error}"
            _fail_flow(flow_id, user_id, bot_token_id, error_message)
            return error_message

        print(f"✅ Bot registered in MongoDB: {plugin_name}")

        # הגדרת webhook לטלגרם
        webhook_set, error = _set_telegram_webhook(bot_token)
        if not webhook_set:
            # הבוט נוצר בהצלחה אבל ה-webhook נכשל
            # זה לא נחשב ככישלון כי הבוט יעבוד אחרי ה-deploy הבא
            print(f"⚠️ Webhook setup failed for {plugin_name}: {error}")
            
            if flow_id:
                _update_flow(flow_id, status="created_webhook_pending", stage=4)
                log_funnel_event(user_id, "bot_created_webhook_pending", flow_id=flow_id,
                                 bot_token_id=bot_token_id,
                                 metadata={"webhook_error": str(error)},
                                 unique_key=f"created_{flow_id}")
            
            return (
                "✅ הבוט נוצר בהצלחה!\n"
                "📦 הקוד נשמר בגיטהאב\n"
                "🔗 *שים לב:* הגדרת ה-Webhook נכשלה זמנית (בעיית רשת)\n\n"
                "⏳ אל דאגה! הבוט יתחיל לעבוד אוטומטית בעוד כ-7 דקות עם ה-Deploy הבא.\n"
                "שלח `/start` בבוט החדש לאחר מכן לבדיקה 🚀"
            )

        print(f"✅ Webhook set for bot: {plugin_name}")

        # אחרי הצלחה: עדכון Flow + אירוע
        if flow_id:
            _update_flow(flow_id, status="created", stage=4)
            log_funnel_event(user_id, "bot_created", flow_id=flow_id,
                             bot_token_id=bot_token_id,
                             unique_key=f"created_{flow_id}")
        
        return SUCCESS_MESSAGE
    finally:
        # סימון שתהליך היצירה הסתיים
        _end_creation(bot_token)
