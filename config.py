"""
Modular Bot V2 - Configuration
קובץ קונפיגורציה מרכזי לפרויקט
"""

import os
from dotenv import load_dotenv

# טעינת משתני סביבה מקובץ .env (אם קיים)
load_dotenv()

# Telegram / Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
# Render provides this automatically (e.g. https://<service>.onrender.com)
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")

# GitHub (for Architect plugin)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_USER = os.environ.get("GITHUB_USER")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH")

# Anthropic (for Architect plugin)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Admin notifications
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")  # Telegram chat ID for alerts

# MongoDB (for secure bot registry - tokens not exposed in GitHub)
MONGO_URI = os.environ.get("MONGO_URI")  # mongodb+srv://...


class Config:
    """הגדרות כלליות לדשבורד הבוט"""
    
    # שם הבוט
    BOT_NAME = "Modular Bot Dashboard"
    
    # פורט השרת (ברירת מחדל, Render יעקוף אוטומטית)
    PORT = int(os.environ.get("PORT", 5000))
    
    # רשימת פלאגינים מופעלים
    # הוסף או הסר פלאגינים מכאן
    ENABLED_PLUGINS = []
    
    # הגדרות נוספות
    # מצב Debug - False בסביבת ייצור
    DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")
    HOST = "0.0.0.0"

    # Telegram / Render
    TELEGRAM_TOKEN = TELEGRAM_TOKEN
    WEBHOOK_URL = WEBHOOK_URL

    # GitHub (for Architect plugin)
    GITHUB_TOKEN = GITHUB_TOKEN
    GITHUB_USER = GITHUB_USER
    GITHUB_REPO = GITHUB_REPO
    GITHUB_BRANCH = GITHUB_BRANCH

    # Anthropic (for Architect plugin)
    ANTHROPIC_API_KEY = ANTHROPIC_API_KEY

    # Admin notifications
    ADMIN_CHAT_ID = ADMIN_CHAT_ID

    # MongoDB
    MONGO_URI = MONGO_URI


# Convenience module-level aliases (for engine/app.py usage)
ENABLED_PLUGINS = Config.ENABLED_PLUGINS
