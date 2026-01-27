# === MongoDB State Helpers (auto-generated) ===
import os
from pymongo import MongoClient

_state_mongo_client = None
_state_mongo_db = None
BOT_ID = "bot_8575828217"

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
            {"bot_id": BOT_ID, "user_id": str(user_id), "key": key},
            {"$set": {"value": value}},
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
        doc = db.bot_states.find_one({"bot_id": BOT_ID, "user_id": str(user_id), "key": key})
        return doc.get("value", default) if doc else default
    except Exception:
        return default

# === End of State Helpers ===

def get_dashboard_widget():
    return {
        "title": "File Sender Bot",
        "value": "🚫 Disabled",
        "label": "Security: File access blocked",
        "status": "danger",
        "icon": "bi-shield-exclamation"
    }

def handle_message(text, user_id=None, context=None):
    text = text.strip()
    
    if text == "/start":
        return """🤖 ברוכים הבאים לבוט שליחת קבצים!

⚠️ **שימו לב: בוט זה מושבת מסיבות אבטחה**

מטעמי אבטחה, בוטים לא יכולים לגשת למערכת הקבצים של השרת.

אם אתם צריכים לשלוח קבצים למשתמשים, אנא שקלו חלופות כמו:
• שמירת קבצים ב-cloud storage (Google Drive, Dropbox)
• שימוש ב-API חיצוני להעלאת קבצים
• שליחת קישורים להורדה

שלחו /help למידע נוסף."""

    if text == "/help":
        return """ℹ️ **מדוע הבוט לא עובד?**

בוטים במערכת זו פועלים בסביבה מאובטחת ולא יכולים:
❌ לגשת לקבצים בשרת
❌ לקרוא או לכתוב לדיסק
❌ להריץ פקודות במערכת

זה נעשה כדי להגן על השרת ועל המשתמשים.

**רוצים לשלוח קבצים? הנה רעיונות:**
✅ העלו את הקבצים ל-Google Drive ושלחו קישורים
✅ השתמשו בשירות cloud storage
✅ צרו API חיצוני שמחזיר קישורי הורדה

צריכים עזרה? שלחו הודעה למפתח."""

    return """⚠️ בוט זה מושבת מטעמי אבטחה

מטעמי אבטחה, בוטים במערכת לא יכולים לגשת לקבצים בשרת.

שלח /start למידע נוסף על חלופות אפשריות."""