# === MongoDB State Helpers (auto-generated) ===
import os
from pymongo import MongoClient

_state_mongo_client = None
_state_mongo_db = None
BOT_ID = "bot_8578440231"

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

import os
from datetime import datetime

def get_dashboard_widget():
    return {
        "title": "מנהל קבצים",
        "value": "0 קבצים",
        "label": "מערכת העלאה והורדה",
        "status": "info",
        "icon": "bi-file-earmark-arrow-up"
    }

def handle_message(text, user_id=None, context=None):
    try:
        if not user_id:
            return "שגיאה: לא ניתן לזהות משתמש"
        
        text = text.strip()
        
        # פקודת התחלה
        if text == "/start":
            return """📁 ברוכים הבאים למנהל הקבצים!

הפקודות הזמינות:
/upload - להעלות קובץ חדש
/list - לראות את כל הקבצים שלך
/delete - למחוק קובץ
/help - עזרה

💡 כדי להוריד קובץ, פשוט שלח את שם הקובץ"""
        
        # עזרה
        if text == "/help":
            return """📚 עזרה - מנהל קבצים

🔹 להעלאת קובץ:
   1. שלח /upload
   2. הזן שם לקובץ
   3. הזן את תוכן הקובץ

🔹 להורדת קובץ:
   שלח את שם הקובץ המלא

🔹 לרשימת קבצים:
   שלח /list

🔹 למחיקת קובץ:
   1. שלח /delete
   2. הזן את שם הקובץ למחיקה"""
        
        # טיפול בהעלאת קובץ
        if text == "/upload":
            save_state(user_id, "awaiting_upload_name", True)
            return "📝 הזן את שם הקובץ (כולל סיומת, למשל: document.txt):"
        
        # המשך תהליך העלאה - שלב שם קובץ
        if load_state(user_id, "awaiting_upload_name"):
            save_state(user_id, "awaiting_upload_name", False)
            save_state(user_id, "upload_filename", text)
            save_state(user_id, "awaiting_upload_content", True)
            return f"✅ שם הקובץ: {text}\n\n📄 כעת שלח את תוכן הקובץ:"
        
        # המשך תהליך העלאה - שלב תוכן
        if load_state(user_id, "awaiting_upload_content"):
            filename = load_state(user_id, "upload_filename")
            save_state(user_id, "awaiting_upload_content", False)
            
            # שמירת הקובץ
            files = load_state(user_id, "files", {})
            files[filename] = {
                "content": text,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "size": len(text)
            }
            save_state(user_id, "files", files)
            
            return f"✅ הקובץ '{filename}' הועלה בהצלחה!\n\n📊 גודל: {len(text)} תווים\n⏰ תאריך: {files[filename]['created']}\n\n💡 שלח את שם הקובץ כדי להוריד אותו"
        
        # רשימת קבצים
        if text == "/list":
            files = load_state(user_id, "files", {})
            if not files:
                return "📭 אין לך קבצים שמורים.\n\nשלח /upload כדי להעלות קובץ חדש"
            
            response = "📁 הקבצים שלך:\n\n"
            for i, (filename, info) in enumerate(files.items(), 1):
                response += f"{i}. 📄 {filename}\n"
                response += f"   📊 גודל: {info['size']} תווים\n"
                response += f"   ⏰ תאריך: {info['created']}\n\n"
            
            response += "💡 שלח את שם הקובץ כדי להוריד אותו"
            return response
        
        # מחיקת קובץ
        if text == "/delete":
            files = load_state(user_id, "files", {})
            if not files:
                return "📭 אין לך קבצים למחיקה"
            
            save_state(user_id, "awaiting_delete", True)
            file_list = "\n".join([f"• {name}" for name in files.keys()])
            return f"🗑️ הזן את שם הקובץ למחיקה:\n\n{file_list}"
        
        # המשך תהליך מחיקה
        if load_state(user_id, "awaiting_delete"):
            save_state(user_id, "awaiting_delete", False)
            files = load_state(user_id, "files", {})
            
            if text in files:
                del files[text]
                save_state(user_id, "files", files)
                return f"✅ הקובץ '{text}' נמחק בהצלחה!"
            else:
                return f"❌ הקובץ '{text}' לא נמצא.\n\nשלח /list לרשימת הקבצים"
        
        # ניסיון להוריד קובץ
        files = load_state(user_id, "files", {})
        if text in files:
            file_info = files[text]
            response = f"📄 קובץ: {text}\n"
            response += f"📊 גודל: {file_info['size']} תווים\n"
            response += f"⏰ תאריך יצירה: {file_info['created']}\n\n"
            response += "📥 תוכן הקובץ:\n"
            response += "=" * 30 + "\n"
            response += file_info['content']
            response += "\n" + "=" * 30
            return response
        
        # הודעה ברירת מחדל
        return """לא הבנתי את הבקשה 🤔

שלח /start כדי לראות את כל הפקודות הזמינות

💡 או שלח את שם הקובץ כדי להוריד אותו"""
    
    except Exception as e:
        return f"❌ שגיאה: {str(e)}\n\nשלח /start כדי להתחיל מחדש"