"""
Engine - ליבת המערכת
מנוע Flask עם טעינה דינמית של פלאגינים
"""

from flask import Flask, render_template, request
import importlib
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import requests

# טעינת משתני סביבה מקובץ .env (אם קיים)
load_dotenv()

# הוספת תיקיית הפרויקט ל-PATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# Flask defaults to searching for templates relative to this module/package.
# In this repo templates live at "<project_root>/templates", so we set it explicitly.
app = Flask(__name__, template_folder=str(TEMPLATES_DIR))
app.config.from_object(Config)


def load_plugins():
    """
    טוען דינמית את כל הפלאגינים המופעלים
    
    Returns:
        list: רשימת מודולי הפלאגינים שנטענו
    """
    loaded_plugins = []
    
    for plugin_name in Config.ENABLED_PLUGINS:
        try:
            # ייבוא דינמי של הפלאגין
            plugin_module = importlib.import_module(f"plugins.{plugin_name}")
            loaded_plugins.append(plugin_module)
            print(f"✅ Plugin loaded: {plugin_name}")
            
        except ImportError as e:
            print(f"❌ Failed to load plugin '{plugin_name}': {e}")
        except Exception as e:
            print(f"❌ Error loading plugin '{plugin_name}': {e}")
    
    return loaded_plugins


@app.route('/')
def dashboard():
    """
    מסך הדשבורד הראשי
    טוען את כל הווידג'טים מהפלאגינים
    """
    widgets = []
    
    # טעינת כל הפלאגינים
    plugins = load_plugins()
    
    # איסוף ווידג'טים מכל פלאגין
    for plugin in plugins:
        if hasattr(plugin, 'get_dashboard_widget'):
            try:
                widget = plugin.get_dashboard_widget()
                widgets.append(widget)
            except Exception as e:
                print(f"❌ Error getting widget from {plugin.__name__}: {e}")
    
    return render_template('index.html', 
                          widgets=widgets, 
                          bot_name=Config.BOT_NAME)


@app.route('/health')
def health():
    """בדיקת בריאות השרת"""
    return {"status": "healthy", "bot": Config.BOT_NAME}


if config.TELEGRAM_TOKEN:
    @app.route(f'/{config.TELEGRAM_TOKEN}', methods=['POST'])
    def telegram_webhook():
        """
        מקבל עדכונים מטלגרם, מפנה טקסט לפלאגינים, ושולח תשובה חזרה אם פלאגין החזיר מחרוזת.
        """
        update = request.get_json(silent=True) or {}

        message = update.get("message") or {}
        text = message.get("text")

        # רק הודעות טקסט מעניינות אותנו כרגע
        if not text:
            return {"ok": True}

        chat_id = (message.get("chat") or {}).get("id")
        if chat_id is None:
            return {"ok": True}

        plugins = load_plugins()
        for plugin in plugins:
            if hasattr(plugin, "handle_message"):
                try:
                    reply = plugin.handle_message(text)
                except Exception as e:
                    print(f"❌ Error in handle_message for {plugin.__name__}: {e}")
                    continue

                if isinstance(reply, str) and reply:
                    try:
                        requests.post(
                            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
                            json={"chat_id": chat_id, "text": reply},
                            timeout=10,
                        )
                    except Exception as e:
                        print(f"❌ Failed sending Telegram message: {e}")
                    break

        return {"ok": True}


if __name__ == '__main__':
    # קריאת PORT ממשתני סביבה (לשימוש ב-Render.com)
    port = int(os.environ.get("PORT", Config.PORT))
    
    app.run(
        host=Config.HOST,
        port=port,
        debug=Config.DEBUG
    )
