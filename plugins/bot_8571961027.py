# === MongoDB State Helpers (auto-generated) ===
import os
from pymongo import MongoClient

_state_mongo_client = None
_state_mongo_db = None
BOT_ID = "bot_8571961027"

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
import random
from datetime import datetime

def get_dashboard_widget():
    return {
        "title": "בוט מזג אוויר + בדיחות",
        "value": "🌤️😄",
        "label": "מזג אוויר לישראל עם בדיחות",
        "status": "success",
        "icon": "bi-cloud-sun"
    }

def handle_message(text, user_id=None, context=None):
    if text.strip() == "/start":
        return """🌤️ ברוכים הבאים לבוט מזג האוויר והבדיחות! 😄

הפקודות הזמינות:
/weather - מזג אוויר נוכחי לתל אביב
/weather_jerusalem - מזג אוויר לירושלים
/weather_haifa - מזג אוויר לחיפה
/weather_eilat - מזג אוויר לאילת
/joke - בדיחה על מזג האוויר
/help - הצגת הפקודות

שלח /weather כדי להתחיל!"""

    if text.strip() == "/help":
        return """📋 רשימת הפקודות:

/weather - מזג אוויר נוכחי לתל אביב
/weather_jerusalem - מזג אוויר לירושלים
/weather_haifa - מזג אוויר לחיפה
/weather_eilat - מזג אוויר לאילת
/joke - בדיחה על מזג האוויר

כל תחזית מגיעה עם בדיחה מתאימה! 🌤️😄"""

    if text.strip() == "/joke":
        jokes = [
            "למה העננים תמיד עצובים? כי הם כל הזמן בוכים! ☁️😢",
            "מה השמש אמרה לעננים? 'תזוזו, זה התור שלי!' ☀️",
            "למה הרוח לא מספרת סודות? כי היא פזרנית! 💨",
            "מה עושים כשיורד גשם? פותחים מטריה... או רק מתלוננים 🌧️😄",
            "למה הברק מגיע לפני הרעם? כי האור מהיר יותר מהקול! ⚡",
            "איך קוראים למזג אוויר בישראל? לא יציב! 🌤️🌧️☀️"
        ]
        return random.choice(jokes)

    cities = {
        "/weather": ("Tel Aviv", "תל אביב"),
        "/weather_jerusalem": ("Jerusalem", "ירושלים"),
        "/weather_haifa": ("Haifa", "חיפה"),
        "/weather_eilat": ("Eilat", "אילת")
    }

    if text.strip() in cities:
        city_en, city_he = cities[text.strip()]
        return get_weather_with_joke(city_en, city_he)

    return """לא הבנתי את הבקשה 🤔
שלח /start כדי לראות את כל הפקודות הזמינות"""

def get_weather_with_joke(city_en, city_he):
    try:
        url = f"https://wttr.in/{city_en}?format=j1"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return "⚠️ לא הצלחתי לקבל מידע על מזג האוויר כרגע. נסה שוב מאוחר יותר."
        
        data = response.json()
        current = data['current_condition'][0]
        
        temp_c = current['temp_C']
        feels_like = current['FeelsLikeC']
        humidity = current['humidity']
        weather_desc = current['weatherDesc'][0]['value']
        wind_speed = current['windspeedKmph']
        
        weather_desc_he = translate_weather(weather_desc)
        
        weather_icon = get_weather_icon(weather_desc)
        
        weather_report = f"""{weather_icon} מזג אוויר ב{city_he}:

🌡️ טמפרטורה: {temp_c}°C
🤚 מרגיש כמו: {feels_like}°C
💧 לחות: {humidity}%
💨 מהירות רוח: {wind_speed} קמ"ש
☁️ מצב: {weather_desc_he}

"""
        
        joke = get_contextual_joke(weather_desc, int(temp_c))
        
        return weather_report + "😄 " + joke
        
    except Exception as e:
        return "⚠️ אירעה שגיאה בקבלת נתוני מזג האוויר. אנא נסה שוב."

def translate_weather(desc):
    translations = {
        "Sunny": "שמשי ☀️",
        "Clear": "בהיר 🌙",
        "Partly cloudy": "מעונן חלקית ⛅",
        "Cloudy": "מעונן ☁️",
        "Overcast": "מעונן כבד ☁️☁️",
        "Mist": "ערפל 🌫️",
        "Fog": "ערפל כבד 🌫️",
        "Light rain": "גשם קל 🌦️",
        "Moderate rain": "גשם בינוני 🌧️",
        "Heavy rain": "גשם כבד 🌧️⛈️",
        "Thundery outbreaks possible": "אפשרות לרעמים ⛈️",
        "Patchy rain possible": "אפשרות לגשם מקומי 🌦️"
    }
    for key in translations:
        if key.lower() in desc.lower():
            return translations[key]
    return desc

def get_weather_icon(desc):
    desc_lower = desc.lower()
    if "rain" in desc_lower:
        return "🌧️"
    elif "thunder" in desc_lower:
        return "⛈️"
    elif "cloud" in desc_lower:
        return "☁️"
    elif "sunny" in desc_lower or "clear" in desc_lower:
        return "☀️"
    elif "fog" in desc_lower or "mist" in desc_lower:
        return "🌫️"
    else:
        return "🌤️"

def get_contextual_joke(weather_desc, temp):
    desc_lower = weather_desc.lower()
    
    if "rain" in desc_lower:
        jokes = [
            "מה ההבדל בין גשם בישראל לחופש? שניהם לא מגיעים מספיק! 🌧️😄",
            "גשם בישראל זה כמו אורח נדיר - כולם מתרגשים כשהוא מגיע! ☔",
            "למה הישראלים אוהבים גשם? כי זו הסיבה היחידה לא לשטוף את הרכב! 🚗🌧️"
        ]
        return random.choice(jokes)
    
    elif "thunder" in desc_lower:
        jokes = [
            "רעמים זה פשוט השמיים שמריבים עם העננים! ⛈️",
            "למה הרעם תמיד מאחר? כי הברק תמיד מגיע ראשון! ⚡😄",
            "רעמים בישראל? השכנים מלמעלה מרעישים שוב! ⛈️🏠"
        ]
        return random.choice(jokes)
    
    elif temp > 30:
        jokes = [
            "חם? זה לא חם, זה 'מזג אוויר ישראלי רגיל'! 🔥😅",
            "בחום כזה אפילו השמש מזיעה! ☀️💦",
            "למה הישראלים לא מפחדים מהשמש? כי הם רגילים לחום! 🌡️😎",
            "חום בישראל זה תירוץ טוב לאכול גלידה כל יום! 🍦☀️"
        ]
        return random.choice(jokes)
    
    elif temp < 15:
        jokes = [
            "קר? בישראל? זה סתם תירוץ להישאר במיטה! 🛏️❄️",
            "למה הישראלים מתלוננים על קור ב-15 מעלות? כי הם פונקים! 😄🧥",
            "קור בישראל זה כמו שלג - נדיר ומפתיע! ❄️"
        ]
        return random.choice(jokes)
    
    elif "cloud" in desc_lower:
        jokes = [
            "עננים זה פשוט השמיים שעושים צל! ☁️😄",
            "למה העננים תמיד ביחד? כי הם חברים טובים! ☁️☁️",
            "עננים בישראל זה כמו הבטחות של פוליטיקאים - הרבה אבל לא תמיד מגשימים! ☁️😅"
        ]
        return random.choice(jokes)
    
    else:
        jokes = [
            "מזג אוויר מושלם ליום מושלם! 🌤️😊",
            "יום כזה צריך לצאת החוצה ולא לשבת בבית! 🌞🚶",
            "למה מזג האוויר בישראל לא יציב? כי גם הוא ישראלי! 🇮🇱😄",
            "מזג אוויר נחמד = תירוץ מצוין לטיול! 🥾🌤️"
        ]
        return random.choice(jokes)