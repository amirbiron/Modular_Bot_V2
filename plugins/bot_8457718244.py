# === MongoDB State Helpers (auto-generated) ===
import os
from pymongo import MongoClient

_state_mongo_client = None
_state_mongo_db = None
BOT_ID = "bot_8457718244"

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

import re
import requests
from urllib.parse import quote

def get_dashboard_widget():
    return {
        "title": "העברת הודעות + ניווט",
        "value": "פעיל",
        "label": "סינון הודעות וניווט Waze",
        "status": "success",
        "icon": "bi-arrow-left-right"
    }

def handle_message(text, user_id=None, context=None):
    if not text:
        return None
    
    text_lower = text.lower().strip()
    
    # פקודת /start
    if text_lower == "/start":
        return """🤖 ברוכים הבאים לבוט העברת הודעות + ניווט!

הפקודות הזמינות:

📋 ניהול סינונים:
/add_filter <מילה> - הוסף מילה לסינון (רק הודעות עם המילה יעברו)
/remove_filter <מילה> - הסר מילה מהסינון
/list_filters - הצג את כל הסינונים הפעילים
/clear_filters - נקה את כל הסינונים

🗺️ ניווט Waze:
/navigate <כתובת מלאה> - קבל קישור ניווט ל-Waze
דוגמה: /navigate ירושלים אברהם שטרן 25

📨 העברת הודעות:
/forward <הודעה> - העבר הודעה לפי הסינונים
/test <הודעה> - בדוק אם הודעה תעבור את הסינונים

⚙️ הגדרות:
/mode exact - התאמה מדויקת למילה שלמה
/mode contain - התאמה אם המילה מופיעה בטקסט
/mode lang - סינון לפי שפה (עברית/אנגלית)
/stats - הצג סטטיסטיקות

שלח /start בכל עת כדי לראות תפריט זה"""
    
    try:
        # טעינת מצב המשתמש
        filters = load_state(user_id, "filters", [])
        filter_mode = load_state(user_id, "filter_mode", "contain")  # exact/contain/lang
        forwarded_count = load_state(user_id, "forwarded_count", 0)
        blocked_count = load_state(user_id, "blocked_count", 0)
        
        # הוספת סינון
        if text_lower.startswith("/add_filter "):
            word = text[12:].strip()
            if not word:
                return "❌ אנא ציין מילה להוספה.\nדוגמה: /add_filter דחוף"
            
            if word.lower() not in [f.lower() for f in filters]:
                filters.append(word)
                save_state(user_id, "filters", filters)
                return f"✅ הסינון '{word}' נוסף בהצלחה!\n\nסינונים פעילים: {', '.join(filters)}"
            else:
                return f"⚠️ הסינון '{word}' כבר קיים."
        
        # הסרת סינון
        if text_lower.startswith("/remove_filter "):
            word = text[15:].strip()
            if not word:
                return "❌ אנא ציין מילה להסרה.\nדוגמה: /remove_filter דחוף"
            
            filters_lower = [f.lower() for f in filters]
            if word.lower() in filters_lower:
                idx = filters_lower.index(word.lower())
                removed = filters.pop(idx)
                save_state(user_id, "filters", filters)
                return f"✅ הסינון '{removed}' הוסר בהצלחה!"
            else:
                return f"❌ הסינון '{word}' לא נמצא."
        
        # רשימת סינונים
        if text_lower == "/list_filters":
            if not filters:
                return "📋 אין סינונים פעילים כרגע.\n\nהשתמש ב-/add_filter כדי להוסיף."
            return f"📋 סינונים פעילים ({len(filters)}):\n\n" + "\n".join([f"• {f}" for f in filters]) + f"\n\nמצב סינון: {filter_mode}"
        
        # ניקוי סינונים
        if text_lower == "/clear_filters":
            save_state(user_id, "filters", [])
            return "🗑️ כל הסינונים נמחקו!"
        
        # שינוי מצב סינון
        if text_lower.startswith("/mode "):
            mode = text[6:].strip().lower()
            if mode not in ["exact", "contain", "lang"]:
                return "❌ מצב לא חוקי. השתמש ב:\n/mode exact - התאמה מדויקת\n/mode contain - התאמה חלקית\n/mode lang - סינון לפי שפה"
            
            save_state(user_id, "filter_mode", mode)
            mode_text = {
                "exact": "התאמה מדויקת למילה שלמה",
                "contain": "התאמה אם המילה מופיעה בטקסט",
                "lang": "סינון לפי שפה (עברית/אנגלית)"
            }
            return f"✅ מצב הסינון שונה ל: {mode_text[mode]}"
        
        # ניווט Waze
        if text_lower.startswith("/navigate "):
            address = text[10:].strip()
            if not address:
                return "❌ אנא ציין כתובת.\nדוגמה: /navigate ירושלים אברהם שטרן 25"
            
            try:
                # ניסיון לקבל קואורדינטות מ-Nominatim (OpenStreetMap)
                nominatim_url = f"https://nominatim.openstreetmap.org/search?q={quote(address)}&format=json&limit=1"
                headers = {"User-Agent": "TelegramBot/1.0"}
                response = requests.get(nominatim_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        lat = data[0]["lat"]
                        lon = data[0]["lon"]
                        display_name = data[0].get("display_name", address)
                        
                        # יצירת קישור Waze
                        waze_url = f"https://waze.com/ul?ll={lat},{lon}&navigate=yes"
                        
                        return f"""🗺️ נמצא מיקום!

📍 כתובת: {display_name}
🌐 קואורדינטות: {lat}, {lon}

🚗 קישור לניווט ב-Waze:
{waze_url}

💡 לחץ על הקישור כדי לפתוח את Waze ולנווט למיקום"""
                    else:
                        return f"❌ לא נמצאה כתובת עבור: {address}\n\nנסה לפרט יותר (עיר, רחוב, מספר בית)"
                else:
                    return "❌ שגיאה בחיפוש הכתובת. נסה שוב מאוחר יותר."
            
            except Exception as e:
                return f"❌ שגיאה בחיפוש המיקום: {str(e)}"
        
        # בדיקת הודעה
        if text_lower.startswith("/test "):
            message = text[6:].strip()
            if not message:
                return "❌ אנא ציין הודעה לבדיקה.\nדוגמה: /test דחוף! אירוע רפואי"
            
            passed, reason = check_filters(message, filters, filter_mode)
            if passed:
                return f"✅ ההודעה תעבור!\n\nסיבה: {reason}\n\nהודעה: {message}"
            else:
                return f"❌ ההודעה תיחסם!\n\nסיבה: {reason}\n\nהודעה: {message}"
        
        # העברת הודעה
        if text_lower.startswith("/forward "):
            message = text[9:].strip()
            if not message:
                return "❌ אנא ציין הודעה להעברה.\nדוגמה: /forward דחוף! אירוע רפואי"
            
            if not filters:
                return "⚠️ אין סינונים מוגדרים. כל ההודעות יעברו.\n\nהשתמש ב-/add_filter כדי להוסיף סינונים."
            
            passed, reason = check_filters(message, filters, filter_mode)
            
            if passed:
                forwarded_count += 1
                save_state(user_id, "forwarded_count", forwarded_count)
                return f"✅ ההודעה הועברה בהצלחה!\n\nסיבה: {reason}\n\n📨 הודעה:\n{message}"
            else:
                blocked_count += 1
                save_state(user_id, "blocked_count", blocked_count)
                return f"🚫 ההודעה נחסמה!\n\nסיבה: {reason}\n\n❌ הודעה:\n{message}"
        
        # סטטיסטיקות
        if text_lower == "/stats":
            total = forwarded_count + blocked_count
            pass_rate = (forwarded_count / total * 100) if total > 0 else 0
            
            return f"""📊 סטטיסטיקות:

✅ הודעות שהועברו: {forwarded_count}
🚫 הודעות שנחסמו: {blocked_count}
📈 סך הכל: {total}
📊 אחוז מעבר: {pass_rate:.1f}%

🔍 סינונים פעילים: {len(filters)}
⚙️ מצב סינון: {filter_mode}"""
        
        # הודעה לא מזוהה
        return """🤔 לא הבנתי את הבקשה.

שלח /start כדי לראות את כל הפקודות הזמינות."""
    
    except Exception as e:
        return f"❌ אירעה שגיאה: {str(e)}\n\nשלח /start כדי להתחיל מחדש."

def check_filters(message, filters, mode):
    """בדיקה האם הודעה עוברת את הסינונים"""
    if not filters:
        return True, "אין סינונים מוגדרים"
    
    message_lower = message.lower()
    
    if mode == "exact":
        # התאמה מדויקת - המילה חייבת להופיע כמילה שלמה
        words = re.findall(r'\b\w+\b', message_lower)
        for filter_word in filters:
            if filter_word.lower() in words:
                return True, f"נמצאה התאמה מדויקת למילה '{filter_word}'"
        return False, "לא נמצאה התאמה מדויקת לאף מילת סינון"
    
    elif mode == "contain":
        # התאמה חלקית - המילה יכולה להופיע בכל מקום
        for filter_word in filters:
            if filter_word.lower() in message_lower:
                return True, f"המילה '{filter_word}' נמצאה בהודעה"
        return False, "אף מילת סינון לא נמצאה בהודעה"
    
    elif mode == "lang":
        # סינון לפי שפה
        has_hebrew = bool(re.search(r'[\u0590-\u05FF]', message))
        has_english = bool(re.search(r'[a-zA-Z]', message))
        
        for filter_word in filters:
            filter_lower = filter_word.lower()
            if filter_lower in ["hebrew", "עברית", "he"] and has_hebrew:
                return True, "הודעה מכילה עברית"
            if filter_lower in ["english", "אנגלית", "en"] and has_english:
                return True, "הודעה מכילה אנגלית"
        
        return False, "השפה לא תואמת את הסינונים"
    
    return False, "מצב סינון לא ידוע"