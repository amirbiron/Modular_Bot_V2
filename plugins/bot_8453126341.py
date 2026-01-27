# === MongoDB State Helpers (auto-generated) ===
import os
from pymongo import MongoClient

_state_mongo_client = None
_state_mongo_db = None
BOT_ID = "bot_8453126341"

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

# -*- coding: utf-8 -*-

def get_dashboard_widget():
    return {
        "title": "בוט חדש",
        "value": "פעיל",
        "label": "בוט כללי מוכן לשימוש",
        "status": "success",
        "icon": "bi-robot"
    }

def handle_message(text, user_id=None, context=None):
    try:
        text_clean = text.strip()
        
        # טיפול בפקודת /start
        if text_clean == "/start":
            return """👋 ברוכים הבאים לבוט החדש!

הפקודות הזמינות:
/start - תפריט ראשי
/help - עזרה ומידע על הבוט
/about - אודות הבוט

שלח לי כל הודעה ואגיב לך! 😊"""
        
        # טיפול בפקודת /help
        if text_clean == "/help":
            return """ℹ️ עזרה

הבוט הזה מגיב לכל הודעה שתשלח אליו.
אתה יכול לשלוח כל טקסט והבוט יענה לך בחזרה.

שלח /start כדי לראות את כל הפקודות הזמינות."""
        
        # טיפול בפקודת /about
        if text_clean == "/about":
            return """🤖 אודות הבוט

זהו בוט חדש שנוצר במערכת מפעל הבוטים המודולרי.
הבוט יכול להגיב לכל הודעה ולספק תשובות אינטראקטיביות.

גרסה: 1.0
תאריך יצירה: 2025"""
        
        # טיפול בהודעות רגילות
        if text_clean:
            return f"📨 קיבלתי את ההודעה שלך: \"{text_clean}\"\n\nשלח /start כדי לראות את כל האפשרויות הזמינות."
        
        # הודעה ברירת מחדל
        return "לא הבנתי את הבקשה 🤔\nשלח /start כדי לראות את כל הפקודות הזמינות"
        
    except Exception as e:
        return f"⚠️ אירעה שגיאה: {str(e)}\nאנא נסה שוב או שלח /start"