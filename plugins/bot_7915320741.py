# === MongoDB State Helpers (auto-generated) ===
import os
from pymongo import MongoClient

_state_mongo_client = None
_state_mongo_db = None
BOT_ID = "bot_7915320741"

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

import subprocess

def get_dashboard_widget():
    return {
        "title": "Network Info Bot",
        "value": "ifconfig",
        "label": "מציג מידע רשת",
        "status": "info",
        "icon": "bi-hdd-network"
    }

def handle_message(text, user_id=None, context=None):
    try:
        if not text:
            return None
        
        text = text.strip()
        
        if text == "/start":
            return """🌐 ברוכים הבאים לבוט מידע רשת!

הפקודות הזמינות:
/ifconfig - הצגת מידע רשת מלא
/network - הצגת מידע רשת (קיצור)
/help - עזרה

שלח אחת מהפקודות כדי לקבל מידע על תצורת הרשת של השרת."""
        
        if text in ["/ifconfig", "/network"]:
            try:
                result = subprocess.run(
                    ["ifconfig"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    if output:
                        if len(output) > 4000:
                            output = output[:4000] + "\n\n... (התוצאה קוצרה)"
                        return f"📡 תוצאת ifconfig:\n\n```\n{output}\n```"
                    else:
                        return "❌ לא התקבלה תוצאה מ-ifconfig"
                else:
                    error = result.stderr.strip() if result.stderr else "שגיאה לא ידועה"
                    return f"❌ שגיאה בהרצת ifconfig:\n{error}"
                    
            except subprocess.TimeoutExpired:
                return "⏰ הפקודה לקחה יותר מדי זמן"
            except FileNotFoundError:
                return "❌ הפקודה ifconfig לא נמצאה על השרת"
            except Exception as e:
                return f"❌ שגיאה בהרצת הפקודה: {str(e)}"
        
        if text == "/help":
            return """📖 עזרה - בוט מידע רשת

הבוט מריץ את הפקודה ifconfig ומציג את תצורת הרשת של השרת.

פקודות זמינות:
• /ifconfig או /network - הצג מידע רשת
• /start - תפריט ראשי
• /help - הודעת עזרה זו

ℹ️ הפקודה מציגה כתובות IP, MAC, ממשקי רשת ועוד."""
        
        return """לא הבנתי את הבקשה 🤔
        
שלח /start כדי לראות את כל הפקודות הזמינות"""
        
    except Exception as e:
        return f"❌ אירעה שגיאה: {str(e)}\n\nשלח /start כדי להתחיל מחדש"