# === MongoDB State Helpers (auto-generated) ===
import os
from pymongo import MongoClient

_state_mongo_client = None
_state_mongo_db = None
BOT_ID = "bot_7876725279"

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
import shlex
from datetime import datetime

def get_dashboard_widget():
    return {
        "title": "Terminal Bot",
        "value": "🖥️ מוכן",
        "label": "בוט הרצת פקודות טרמינל",
        "status": "success",
        "icon": "bi-terminal"
    }

def handle_message(text, user_id=None, context=None):
    text = text.strip()
    
    if text == "/start":
        return """🖥️ ברוכים הבאים לבוט הטרמינל!

הפקודות הזמינות:
/run <פקודה> - להריץ פקודת טרמינל
/help - עזרה ומידע
/examples - דוגמאות לפקודות

⚠️ שימו לב: הבוט מריץ פקודות על השרת ויש לו הגבלות אבטחה."""

    if text == "/help":
        return """📚 עזרה - Terminal Bot

🔹 איך משתמשים:
שלח /run ואחריו את הפקודה שברצונך להריץ

דוגמאות:
/run ping -c 4 1.1.1.1
/run uname -a
/run whoami
/run df -h
/run uptime

⚠️ מגבלות אבטחה:
• זמן ריצה מקסימלי: 30 שניות
• פקודות מסוכנות חסומות
• אין גישה לקבצים רגישים

💡 טיפ: השתמש בפקודות קצרות ובטוחות בלבד!"""

    if text == "/examples":
        return """💡 דוגמאות לפקודות:

🌐 רשת:
/run ping -c 4 google.com
/run curl -I https://www.google.com
/run nslookup google.com

📊 מערכת:
/run uname -a
/run uptime
/run whoami
/run df -h
/run free -h
/run ps aux | head -10

📁 קבצים:
/run ls -la
/run pwd
/run date

⚙️ מידע:
/run env | head -10
/run which python3"""

    if text.startswith("/run "):
        command = text[5:].strip()
        
        if not command:
            return "❌ לא ציינת פקודה להרצה!\nדוגמה: /run ping -c 4 1.1.1.1"
        
        # רשימה שחורה של פקודות מסוכנות
        dangerous_commands = [
            'rm', 'rmdir', 'del', 'format', 'mkfs',
            'dd', 'fdisk', 'parted', 'shutdown', 'reboot',
            'init', 'systemctl', 'service', 'kill', 'killall',
            'sudo', 'su', 'chmod', 'chown', 'passwd',
            'useradd', 'userdel', 'groupadd', 'groupdel',
            '>', '>>', '|', '&', ';', '$(', '`',
            'wget', 'curl -o', 'nc', 'netcat', 'telnet'
        ]
        
        command_lower = command.lower()
        for dangerous in dangerous_commands:
            if dangerous in command_lower:
                return f"⛔ הפקודה '{dangerous}' חסומה מטעמי אבטחה!"
        
        try:
            # הרצת הפקודה עם timeout
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                env={'PATH': '/usr/local/bin:/usr/bin:/bin'}
            )
            
            output = result.stdout.strip()
            error = result.stderr.strip()
            
            if result.returncode == 0:
                if not output:
                    output = "✅ הפקודה הושלמה בהצלחה (ללא פלט)"
                
                # הגבלת אורך הפלט
                if len(output) > 3000:
                    output = output[:3000] + "\n\n... (פלט חתוך - יותר מדי תווים)"
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                return f"🖥️ תוצאות הפקודה [{timestamp}]:\n\n```\n{output}\n```"
            else:
                error_msg = error if error else "שגיאה לא ידועה"
                if len(error_msg) > 1000:
                    error_msg = error_msg[:1000] + "..."
                return f"❌ הפקודה נכשלה (קוד שגיאה {result.returncode}):\n\n```\n{error_msg}\n```"
                
        except subprocess.TimeoutExpired:
            return "⏱️ הפקודה חרגה מזמן הריצה המקסימלי (30 שניות)"
        except FileNotFoundError:
            return "❌ הפקודה לא נמצאה במערכת"
        except Exception as e:
            return f"❌ שגיאה בהרצת הפקודה:\n{str(e)}"
    
    # הודעה ברירת מחדל
    return """לא הבנתי את הבקשה 🤔
    
שלח /start כדי לראות את כל הפקודות הזמינות
או שלח /help למידע נוסף"""