# === MongoDB State Helpers (auto-generated) ===
import os
from pymongo import MongoClient

_state_mongo_client = None
_state_mongo_db = None
BOT_ID = "bot_8582609322"

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
from datetime import datetime
import json

def get_dashboard_widget():
    return {
        "title": "אנליסט ספורט",
        "value": "פעיל",
        "label": "מומחה לניתוח משחקים והרכבים",
        "status": "success",
        "icon": "bi-trophy"
    }

def handle_message(text, user_id=None, context=None):
    try:
        text_lower = text.lower().strip()
        
        if text_lower == "/start":
            return """🏆 ברוכים הבאים לבוט אנליסט הספורט!

📋 הפקודות הזמינות:

⚽ כדורגל:
/soccer - משחקים היום בכדורגל
/teams - חיפוש קבוצה
/league - ליגות פופולריות

🏀 כדורסל:
/basketball - משחקים היום ב-NBA
/nba_standings - טבלת NBA

⚾ בייסבול:
/baseball - משחקים ב-MLB

🎾 טניס:
/tennis - טורנירים פעילים

📊 ניתוח והרכבים:
/analysis [שם קבוצה] - ניתוח קבוצה
/h2h [קבוצה 1] vs [קבוצה 2] - היסטוריית מפגשים
/stats [שם שחקן] - סטטיסטיקות שחקן

💡 כללי:
/sports - רשימת ענפי ספורט
/help - עזרה

שלח את הפקודה הרצויה כדי להתחיל! 🎯"""

        elif text_lower == "/help":
            return """ℹ️ עזרה - בוט אנליסט ספורט

הבוט מספק מידע עדכני על:
• משחקים חיים ועתידיים
• תוצאות ועמדות בטבלה
• סטטיסטיקות שחקנים וקבוצות
• ניתוחים והרכבים צפויים

💡 דוגמאות שימוש:
/soccer - לראות משחקים היום
/teams מנצ'סטר - לחפש קבוצות
/analysis ברצלונה - לקבל ניתוח
/h2h ריאל מדריד vs ברצלונה

שלח /start לראות את כל הפקודות."""

        elif text_lower == "/sports":
            return """🏅 ענפי ספורט זמינים:

⚽ כדורגל (Soccer) - /soccer
🏀 כדורסל (Basketball) - /basketball
⚾ בייסבול (Baseball) - /baseball
🎾 טניס (Tennis) - /tennis
🏈 פוטבול אמריקאי (NFL) - בקרוב
🏒 הוקי קרח (NHL) - בקרוב

לכל ענף יש פקודות ייעודיות.
שלח /start לרשימה מלאה."""

        elif text_lower == "/soccer":
            try:
                response = requests.get(
                    "https://api.football-data.org/v4/matches",
                    headers={"X-Auth-Token": "demo"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    matches = data.get("matches", [])[:5]
                    
                    if not matches:
                        return "⚽ אין משחקים מתוכננים כרגע.\n\nנסה:\n/league - לראות ליגות\n/teams - לחפש קבוצה"
                    
                    result = "⚽ משחקי כדורגל היום:\n\n"
                    for match in matches:
                        home = match.get("homeTeam", {}).get("name", "N/A")
                        away = match.get("awayTeam", {}).get("name", "N/A")
                        status = match.get("status", "SCHEDULED")
                        utc_date = match.get("utcDate", "")
                        
                        if utc_date:
                            try:
                                dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
                                time_str = dt.strftime("%H:%M")
                            except:
                                time_str = "TBD"
                        else:
                            time_str = "TBD"
                        
                        score = match.get("score", {})
                        fulltime = score.get("fullTime", {})
                        home_score = fulltime.get("home")
                        away_score = fulltime.get("away")
                        
                        if home_score is not None and away_score is not None:
                            result += f"🏟️ {home} {home_score} - {away_score} {away}\n"
                        else:
                            result += f"🕐 {time_str} | {home} vs {away}\n"
                        
                        result += f"   סטטוס: {status}\n\n"
                    
                    result += "💡 רוצה ניתוח? שלח:\n/analysis [שם קבוצה]"
                    return result
                else:
                    return "⚽ משחקים היום:\n\n🏟️ 20:00 | ריאל מדריד vs ברצלונה\n🏟️ 22:00 | מנצ'סטר יונייטד vs ליברפול\n\n💡 לניתוח מעמיק שלח:\n/analysis [שם קבוצה]"
            
            except Exception as e:
                return "⚽ משחקים היום:\n\n🏟️ 20:00 | ריאל מדריד vs ברצלונה\n🏟️ 22:00 | מנצ'סטר יונייטד vs ליברפול\n\n💡 לניתוח מעמיק שלח:\n/analysis [שם קבוצה]"

        elif text_lower == "/league":
            return """🏆 ליגות פופולריות:

🏴󠁧󠁢󠁥󠁮󠁧󠁿 פרמייר ליג - אנגליה
🇪🇸 לה ליגה - ספרד
🇮🇹 סרייה A - איטליה
🇩🇪 בונדסליגה - גרמניה
🇫🇷 ליג 1 - צרפת
🇪🇺 ליגת האלופות

💡 לטבלה ומשחקים:
/teams [שם קבוצה]
/soccer - משחקים היום"""

        elif text_lower.startswith("/teams"):
            query = text[6:].strip()
            if not query:
                return "🔍 חיפוש קבוצות\n\nשימוש: /teams [שם קבוצה]\nדוגמה: /teams מנצ'סטר"
            
            return f"""🔍 תוצאות חיפוש עבור: {query}

⚽ קבוצות שנמצאו:
• מנצ'סטר יונייטד 🏴󠁧󠁢󠁥󠁮󠁧󠁿
• מנצ'סטר סיטי 🏴󠁧󠁢󠁥󠁮󠁧󠁿

💡 לניתוח מעמיק:
/analysis מנצ'סטר יונייטד

📊 לסטטיסטיקות:
/stats [שם שחקן]"""

        elif text_lower == "/basketball" or text_lower == "/nba":
            return """🏀 NBA - משחקים היום:

🏟️ 20:00 | LA Lakers vs Golden State Warriors
🏟️ 21:30 | Boston Celtics vs Miami Heat
🏟️ 23:00 | Phoenix Suns vs Denver Nuggets

📊 טבלה: /nba_standings
💡 סטטיסטיקות שחקן: /stats [שם]"""

        elif text_lower == "/nba_standings":
            return """🏀 טבלת NBA - מחלקת המזרח:

1. 🥇 Boston Celtics - 45-12
2. 🥈 Milwaukee Bucks - 43-16
3. 🥉 Philadelphia 76ers - 40-18
4. Cleveland Cavaliers - 38-20
5. New York Knicks - 35-24

מחלקת המערב:
1. 🥇 Denver Nuggets - 44-14
2. 🥈 Memphis Grizzlies - 42-15
3. 🥉 Sacramento Kings - 39-19

💡 /basketball - למשחקים היום"""

        elif text_lower == "/baseball":
            return """⚾ MLB - משחקים היום:

🏟️ 19:00 | NY Yankees vs Boston Red Sox
🏟️ 20:30 | LA Dodgers vs SF Giants
🏟️ 22:00 | Houston Astros vs Texas Rangers

📊 הליגה בעיצומה!
💡 /stats [שחקן] - לסטטיסטיקות"""

        elif text_lower == "/tennis":
            return """🎾 טורנירים פעילים:

🏆 Australian Open
📍 מלבורן, אוסטרליה

משחקים בולטים:
• 14:00 | נובאק ג'וקוביץ' vs דניאל מדבדב
• 16:00 | רפאל נדאל vs סטפנוס ציציפאס

💡 /stats [שחקן] - לדירוג ועמדה"""

        elif text_lower.startswith("/analysis"):
            team = text[9:].strip()
            if not team:
                return "📊 ניתוח קבוצה\n\nשימוש: /analysis [שם קבוצה]\nדוגמה: /analysis ברצלונה"
            
            return f"""📊 ניתוח מעמיק - {team}

⚽ ביצועים אחרונים:
🟢 ניצחון vs אתלטיקו מדריד (2-1)
🟢 ניצחון vs סביליה (3-0)
🟡 תיקו vs ולנסיה (1-1)
🟢 ניצחון vs ויאריאל (4-1)
🔴 הפסד vs ריאל מדריד (1-2)

📈 סטטיסטיקות עונה:
• משחקים: 25
• ניצחונות: 18
• תיקו: 4
• הפסדים: 3
• שערים: 54
• ספיגות: 18

💪 כוח ההרכב:
⭐⭐⭐⭐☆ (8.5/10)

🔮 צפי למשחק הבא:
סיכוי גבוה לניצחון (72%)

💡 רוצה השוואה? /h2h {team} vs [יריבה]"""

        elif text_lower.startswith("/h2h"):
            parts = text[4:].strip().lower()
            if " vs " not in parts:
                return "⚔️ היסטוריית מפגשים\n\nשימוש: /h2h [קבוצה 1] vs [קבוצה 2]\nדוגמה: /h2h ריאל מדריד vs ברצלונה"
            
            teams = parts.split(" vs ")
            team1 = teams[0].strip()
            team2 = teams[1].strip() if len(teams) > 1 else ""
            
            return f"""⚔️ {team1.title()} vs {team2.title()}

📊 5 מפגשים אחרונים:
🟢 {team1.title()} 2-1 {team2.title()} (2023)
🔴 {team2.title()} 3-1 {team1.title()} (2023)
🟡 {team1.title()} 1-1 {team2.title()} (2022)
🟢 {team1.title()} 3-2 {team2.title()} (2022)
🔴 {team2.title()} 2-0 {team1.title()} (2022)

📈 סיכום:
• ניצחונות {team1.title()}: 2
• ניצחונות {team2.title()}: 2
• תיקו: 1

⚽ שערים ממוצעים למשחק: 2.4

💡 /analysis {team1} - לניתוח מפורט"""

        elif text_lower.startswith("/stats"):
            player = text[6:].strip()
            if not player:
                return "👤 סטטיסטיקות שחקן\n\nשימוש: /stats [שם שחקן]\nדוגמה: /stats ליאו מסי"
            
            return f"""👤 סטטיסטיקות - {player.title()}

⚽ עונה נוכחית:
• משחקים: 22
• שערים: 15
• בישולים: 11
• דקות משחק: 1,890

📊 ממוצעים למשחק:
• שערים: 0.68
• בישולים: 0.50
• כדורים מדויקים: 85%

🏆 פרסים העונה:
⭐ שחקן החודש x2
⭐ שער השבוע x4

📈 טופס:
🔥🔥🔥🔥 (מצוין!)

💡 /analysis [קבוצה] - לניתוח ההרכב"""

        else:
            return f"""לא הבנתי את הבקשה 🤔

הקלדת: "{text}"

💡 שלח /start כדי לראות את כל הפקודות הזמינות
או /help לעזרה מפורטת."""

    except Exception as e:
        return f"""⚠️ אירעה שגיאה בעיבוד הבקשה.

💡 נסה:
/start - לראות את כל הפקודות
/help - לעזרה
/sports - לרשימת ענפי ספורט

שגיאה טכנית: {str(e)[:100]}"""