"""
Modular Bot V2 - Configuration
קובץ קונפיגורציה מרכזי לפרויקט
"""

import os
from dotenv import load_dotenv

# טעינת משתני סביבה מקובץ .env (אם קיים)
load_dotenv()


class Config:
    """הגדרות כלליות לדשבורד הבוט"""
    
    # שם הבוט
    BOT_NAME = "Modular Bot Dashboard"
    
    # פורט השרת (ברירת מחדל, Render יעקוף אוטומטית)
    PORT = int(os.environ.get("PORT", 5000))
    
    # רשימת פלאגינים מופעלים
    # הוסף או הסר פלאגינים מכאן
    ENABLED_PLUGINS = [
        "hello_world",
    ]
    
    # הגדרות נוספות
    # מצב Debug - False בסביבת ייצור
    DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")
    HOST = "0.0.0.0"
