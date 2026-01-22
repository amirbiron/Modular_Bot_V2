# === MongoDB State Helpers (auto-generated) ===
import os
from pymongo import MongoClient

_state_mongo_client = None
_state_mongo_db = None
BOT_ID = "bot_8210175758"

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
        "title": "בוט H",
        "value": "פעיל",
        "label": "בוט פשוט ומהיר",
        "status": "success",
        "icon": "bi-lightning-charge"
    }

def handle_message(text, user_id=None, context=None):
    try:
        text = text.strip()
        
        if text == "/start":
            return """ברוכים הבאים לבוט H! ⚡

הפקודות הזמינות:
/help - עזרה ומידע על הבוט
/info - מידע כללי

שלח כל הודעה והבוט יגיב!"""
        
        if text == "/help":
            return """📖 עזרה - בוט H

הבוט מגיב לכל הודעה שתשלח אליו.

פקודות זמינות:
/start - תפריט ראשי
/info - מידע על הבוט
/help - הודעה זו

פשוט שלח כל טקסט והבוט יענה לך!"""
        
        if text == "/info":
            return """ℹ️ אודות בוט H

בוט פשוט ומהיר שנוצר במפעל הבוטים המודולרי.

הבוט מגיב לכל הודעה בצורה ידידותית וקלילה.

שלח /start לתפריט הראשי"""
        
        # תגובה לכל הודעה אחרת
        return f"קיבלתי את ההודעה שלך: '{text}' ⚡\n\nשלח /start לראות את כל הפקודות הזמינות!"
        
    except Exception as e:
        return f"אופס! משהו השתבש 🤔\n\nשלח /start לראות את כל הפקודות הזמינות"