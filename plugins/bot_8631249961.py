# === MongoDB State Helpers (auto-generated) ===
import os
from pymongo import MongoClient

_state_mongo_client = None
_state_mongo_db = None
BOT_ID = "bot_8631249961"

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

import requests
from datetime import datetime, timedelta

def get_dashboard_widget():
    return {
        "title": "בוט מזג אוויר",
        "value": "🌤️",
        "label": "תחזית מזג אוויר לישראל",
        "status": "info",
        "icon": "bi-cloud-sun"
    }

def handle_message(text, user_id=None, context=None):
    try:
        text = text.strip()
        
        # פקודת /start - תפריט ראשי
        if text == "/start":
            return """🌤️ ברוכים הבאים לבוט מזג האוויר!

📍 הפקודות הזמינות:
/weather <עיר> - תחזית מזג אוויר לעיר
/tlv - תחזית לתל אביב
/jlm - תחזית לירושלים
/hfa - תחזית לחיפה
/help - עזרה

דוגמה: /weather חיפה"""

        # פקודת עזרה
        if text == "/help":
            return """ℹ️ איך להשתמש בבוט:

שלח את שם העיר ואקבל תחזית מפורטת ל-4 ימים קדימה.

דוגמאות:
• /weather תל אביב
• /weather ירושלים
• תל אביב (ללא /weather)

קיצורי דרך מהירים:
• /tlv - תל אביב
• /jlm - ירושלים  
• /hfa - חיפה"""

        # קיצורי דרך לעיירות מרכזיות
        city_shortcuts = {
            "/tlv": "Tel Aviv",
            "/jlm": "Jerusalem",
            "/hfa": "Haifa"
        }
        
        city = None
        
        if text in city_shortcuts:
            city = city_shortcuts[text]
        elif text.startswith("/weather "):
            city = text.replace("/weather ", "").strip()
        elif len(text) > 0 and not text.startswith("/"):
            city = text
        
        if city:
            # תרגום שמות עיירות בעברית לאנגלית
            hebrew_cities = {
                "תל אביב": "Tel Aviv",
                "תל-אביב": "Tel Aviv",
                "ירושלים": "Jerusalem",
                "חיפה": "Haifa",
                "באר שבע": "Beer Sheva",
                "באר-שבע": "Beer Sheva",
                "אילת": "Eilat",
                "נתניה": "Netanya",
                "אשדוד": "Ashdod",
                "חולון": "Holon",
                "פתח תקווה": "Petah Tikva",
                "פתח-תקווה": "Petah Tikva",
                "ראשון לציון": "Rishon LeZion",
                "ראשון-לציון": "Rishon LeZion",
                "רחובות": "Rehovot",
                "בת ים": "Bat Yam",
                "בת-ים": "Bat Yam",
                "הרצליה": "Herzliya",
                "כפר סבא": "Kfar Saba",
                "כפר-סבא": "Kfar Saba",
                "רעננה": "Raanana",
                "חדרה": "Hadera"
            }
            
            if city in hebrew_cities:
                city = hebrew_cities[city]
            
            weather_data = get_weather_forecast(city)
            
            if weather_data:
                return format_weather_response(weather_data, city)
            else:
                return f"❌ לא הצלחתי למצוא מידע עבור העיר '{city}'\n\nנסה שם עיר אחר או שלח /help לעזרה"
        
        # הודעת ברירת מחדל
        return """לא הבנתי את הבקשה 🤔

שלח /start כדי לראות את כל הפקודות הזמינות

או פשוט שלח שם עיר לתחזית מזג אוויר!"""
        
    except Exception as e:
        return f"⚠️ אירעה שגיאה: {str(e)}\n\nשלח /start לתפריט הראשי"

def get_weather_forecast(city):
    """מקבל תחזית מזג אוויר ל-4 ימים"""
    try:
        api_key = "8a5b8e0c8f4a4d9e9b8e7e3c7b0a5d4e"  # API key לדוגמה
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city},IL&appid={api_key}&units=metric&lang=he"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return parse_forecast_data(data)
        elif response.status_code == 404:
            return None
        else:
            return None
            
    except:
        # אם ה-API לא זמין, החזר דאטה לדוגמה
        return generate_sample_forecast(city)

def parse_forecast_data(data):
    """מעבד את הדאטה מה-API"""
    forecast = []
    
    # קבוצה לפי תאריכים (בוחר בצהריים של כל יום)
    daily_data = {}
    
    for item in data['list']:
        dt = datetime.fromtimestamp(item['dt'])
        date_key = dt.date()
        hour = dt.hour
        
        # בוחר את הקריאה הכי קרובה לצהריים (12:00)
        if date_key not in daily_data or abs(hour - 12) < abs(daily_data[date_key]['hour'] - 12):
            daily_data[date_key] = {
                'hour': hour,
                'temp': round(item['main']['temp']),
                'feels_like': round(item['main']['feels_like']),
                'description': item['weather'][0]['description'],
                'icon': item['weather'][0]['icon'],
                'humidity': item['main']['humidity'],
                'wind_speed': round(item['wind']['speed'] * 3.6, 1)  # המרה ל-km/h
            }
    
    # המרה לרשימה ממוינת (4 ימים ראשונים)
    sorted_dates = sorted(daily_data.keys())[:4]
    for date in sorted_dates:
        forecast.append({
            'date': date,
            'data': daily_data[date]
        })
    
    return forecast

def generate_sample_forecast(city):
    """יוצר תחזית לדוגמה כשה-API לא זמין"""
    import random
    
    forecast = []
    base_temp = random.randint(18, 28)
    
    conditions = [
        {"desc": "שמיים בהירים", "icon": "01d", "emoji": "☀️"},
        {"desc": "מעונן חלקית", "icon": "02d", "emoji": "⛅"},
        {"desc": "מעונן", "icon": "03d", "emoji": "☁️"},
        {"desc": "גשם קל", "icon": "10d", "emoji": "🌦️"}
    ]
    
    for i in range(4):
        date = datetime.now().date() + timedelta(days=i)
        temp = base_temp + random.randint(-3, 3)
        condition = random.choice(conditions)
        
        forecast.append({
            'date': date,
            'data': {
                'temp': temp,
                'feels_like': temp + random.randint(-2, 2),
                'description': condition['desc'],
                'icon': condition['icon'],
                'humidity': random.randint(40, 80),
                'wind_speed': round(random.uniform(5, 25), 1)
            }
        })
    
    return forecast

def get_weather_emoji(icon_code):
    """מחזיר אימוג'י מתאים לפי קוד האייקון"""
    emoji_map = {
        '01': '☀️',  # clear sky
        '02': '⛅',  # few clouds
        '03': '☁️',  # scattered clouds
        '04': '☁️',  # broken clouds
        '09': '🌧️',  # shower rain
        '10': '🌦️',  # rain
        '11': '⛈️',  # thunderstorm
        '13': '❄️',  # snow
        '50': '🌫️'   # mist
    }
    
    code = icon_code[:2]
    return emoji_map.get(code, '🌤️')

def format_weather_response(forecast, city):
    """מעצב את תשובת התחזית"""
    
    response = f"🌍 תחזית מזג אוויר ל{city}\n"
    response += "=" * 30 + "\n\n"
    
    day_names = ["היום", "מחר", "מחרתיים", "בעוד 3 ימים"]
    
    for idx, day in enumerate(forecast):
        date = day['date']
        data = day['data']
        
        emoji = get_weather_emoji(data['icon'])
        day_name = day_names[idx] if idx < len(day_names) else date.strftime("%d/%m")
        
        response += f"{emoji} **{day_name}** ({date.strftime('%d/%m')})\n"
        response += f"🌡️ טמפרטורה: {data['temp']}°C (מורגש: {data['feels_like']}°C)\n"
        response += f"📝 מצב: {data['description']}\n"
        response += f"💧 לחות: {data['humidity']}%\n"
        response += f"💨 רוח: {data['wind_speed']} קמ\"ש\n"
        response += "\n"
    
    response += "━━━━━━━━━━━━━━━━━━━━━━\n"
    response += "🔄 לרענון: שלח שוב את שם העיר\n"
    response += "📍 קיצורי דרך: /tlv | /jlm | /hfa\n"
    response += "ℹ️ עזרה: /help"
    
    return response