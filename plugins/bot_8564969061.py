import time
from datetime import datetime

# מאגר זיכרון פשוט לשמירת מצב הבוט
bot_state = {
    'running': False,
    'source_chat': None,
    'target_chat': None,
    'last_message_id': None,
    'forwarded_count': 0,
    'errors': 0
}

def get_dashboard_widget():
    status = 'success' if bot_state['running'] else 'info'
    value = f"{bot_state['forwarded_count']} הועברו"
    label = 'פעיל' if bot_state['running'] else 'לא פעיל'
    
    return {
        'title': 'העברת פוסטים אוטומטית',
        'value': value,
        'label': label,
        'status': status,
        'icon': 'bi-arrow-left-right'
    }

def handle_message(text):
    try:
        text = text.strip()
        
        # פקודת /start - תפריט ראשי
        if text == '/start':
            return """ברוכים הבאים לבוט העברת פוסטים! 🤖

הפקודות הזמינות:

📋 הגדרות:
/setup - הגדרת קבוצת מקור וקבוצת יעד
/status - בדיקת מצב הבוט הנוכחי

▶️ הפעלה:
/start_forward - התחלת העברת פוסטים
/stop_forward - עצירת העברת פוסטים

📊 מידע:
/stats - סטטיסטיקות העברה
/reset - איפוס כל ההגדרות

❓ /help - עזרה והסבר מפורט"""

        # פקודת /help
        elif text == '/help':
            return """📚 עזרה - בוט העברת פוסטים

איך זה עובד?
1️⃣ הגדר את קבוצת המקור וקבוצת היעד עם /setup
2️⃣ הפעל את הבוט עם /start_forward
3️⃣ הבוט יעביר באופן אוטומטי פוסטים חדשים

⚠️ חשוב לדעת:
- הבוט צריך להיות מנהל בשתי הקבוצות
- העברה היא לפי מזהה הקבוצה
- ניתן לעצור בכל עת עם /stop_forward

📝 דוגמה:
/setup -1001234567890 -1009876543210

שלח /start לתפריט הראשי"""

        # פקודת /setup - הגדרת קבוצות
        elif text.startswith('/setup'):
            parts = text.split()
            if len(parts) != 3:
                return """❌ שימוש לא נכון!

פורמט: /setup <מזהה_קבוצת_מקור> <מזהה_קבוצת_יעד>

דוגמה:
/setup -1001234567890 -1009876543210

💡 איך למצוא מזהה קבוצה?
1. הוסף את @userinfobot לקבוצה
2. שלח הודעה בקבוצה
3. הבוט יחזיר את מזהה הקבוצה

שלח /start לתפריט הראשי"""

            try:
                source = parts[1]
                target = parts[2]
                
                # וידוא שהמזהים הם מספרים
                if not (source.lstrip('-').isdigit() and target.lstrip('-').isdigit()):
                    return "❌ מזהי קבוצה חייבים להיות מספרים!\n\nשלח /help לעזרה נוספת"
                
                bot_state['source_chat'] = source
                bot_state['target_chat'] = target
                
                return f"""✅ ההגדרות נשמרו בהצלחה!

📥 קבוצת מקור: {source}
📤 קבוצת יעד: {target}

כעת השתמש ב-/start_forward כדי להתחיל את ההעברה"""

            except Exception as e:
                return f"❌ שגיאה בהגדרת הקבוצות: {str(e)}\n\nשלח /start לתפריט הראשי"

        # פקודת /status - מצב נוכחי
        elif text == '/status':
            if not bot_state['source_chat'] or not bot_state['target_chat']:
                return """⚙️ מצב הבוט: לא מוגדר

📋 יש להגדיר קבוצות תחילה עם:
/setup <מקור> <יעד>

שלח /start לתפריט הראשי"""
            
            status_emoji = '✅' if bot_state['running'] else '⏸️'
            status_text = 'פעיל' if bot_state['running'] else 'לא פעיל'
            
            return f"""📊 מצב הבוט

{status_emoji} סטטוס: {status_text}
📥 קבוצת מקור: {bot_state['source_chat']}
📤 קבוצת יעד: {bot_state['target_chat']}
📨 פוסטים הועברו: {bot_state['forwarded_count']}
❌ שגיאות: {bot_state['errors']}

שלח /start לתפריט הראשי"""

        # פקודת /start_forward - התחלת העברה
        elif text == '/start_forward':
            if not bot_state['source_chat'] or not bot_state['target_chat']:
                return """❌ לא ניתן להתחיל!

יש להגדיר קבוצות תחילה עם:
/setup <מקור> <יעד>

שלח /start לתפריט הראשי"""
            
            if bot_state['running']:
                return "⚠️ הבוט כבר פועל!\n\nשלח /stop_forward לעצירה"
            
            bot_state['running'] = True
            return f"""✅ הבוט החל לפעול!

מעביר פוסטים מ-{bot_state['source_chat']} ל-{bot_state['target_chat']}

שלח /stop_forward לעצירה
שלח /stats לסטטיסטיקות"""

        # פקודת /stop_forward - עצירת העברה
        elif text == '/stop_forward':
            if not bot_state['running']:
                return "⚠️ הבוט לא פועל כרגע\n\nשלח /start לתפריט הראשי"
            
            bot_state['running'] = False
            return f"""⏸️ הבוט נעצר בהצלחה

📊 סיכום:
- פוסטים הועברו: {bot_state['forwarded_count']}
- שגיאות: {bot_state['errors']}

שלח /start_forward להפעלה מחדש"""

        # פקודת /stats - סטטיסטיקות
        elif text == '/stats':
            return f"""📊 סטטיסטיקות העברה

📨 סה"כ פוסטים הועברו: {bot_state['forwarded_count']}
❌ שגיאות: {bot_state['errors']}
⏱️ סטטוס: {'פעיל' if bot_state['running'] else 'לא פעיל'}

📥 מקור: {bot_state['source_chat'] or 'לא מוגדר'}
📤 יעד: {bot_state['target_chat'] or 'לא מוגדר'}

שלח /start לתפריט הראשי"""

        # פקודת /reset - איפוס
        elif text == '/reset':
            bot_state['running'] = False
            bot_state['source_chat'] = None
            bot_state['target_chat'] = None
            bot_state['last_message_id'] = None
            bot_state['forwarded_count'] = 0
            bot_state['errors'] = 0
            
            return """🔄 כל ההגדרות אופסו!

שלח /setup להגדרה מחדש
שלח /start לתפריט הראשי"""

        # הודעה לא מזוהה
        else:
            return """לא הבנתי את הבקשה 🤔

שלח /start כדי לראות את כל הפקודות הזמינות"""

    except Exception as e:
        return f"""❌ אירעה שגיאה: {str(e)}

שלח /start כדי לראות את כל הפקודות הזמינות"""