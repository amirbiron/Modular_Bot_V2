"""
Engine - ליבת המערכת
מנוע Flask עם טעינה דינמית של פלאגינים
"""

from flask import Flask, render_template, redirect, url_for
import importlib
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# טעינת משתני סביבה מקובץ .env (אם קיים)
load_dotenv()

# הוספת תיקיית הפרויקט ל-PATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"

# Flask defaults to searching for templates relative to this module/package.
# In this repo templates live at "<project_root>/templates", so we set it explicitly.
#
# We also explicitly set a project-level static directory so Render/Flask can serve assets
# like favicon files from "<project_root>/static".
app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path="/static",
)
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


@app.get("/favicon.ico")
def favicon():
    """
    Handle default browser favicon requests.

    Many browsers request "/favicon.ico" even when the HTML declares a different icon.
    We redirect to our SVG favicon to avoid 404 noise in logs.
    """
    return redirect(url_for("static", filename="favicon.svg"))


@app.route('/health')
def health():
    """בדיקת בריאות השרת"""
    return {"status": "healthy", "bot": Config.BOT_NAME}


if __name__ == '__main__':
    # קריאת PORT ממשתני סביבה (לשימוש ב-Render.com)
    port = int(os.environ.get("PORT", Config.PORT))
    
    app.run(
        host=Config.HOST,
        port=port,
        debug=Config.DEBUG
    )
