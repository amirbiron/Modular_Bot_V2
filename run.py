"""
Modular Bot V2 - Runner
נקודת כניסה ראשית להפעלת השרת
"""

import os
from dotenv import load_dotenv
from engine.app import app
from config import Config

# טעינת משתני סביבה
load_dotenv()


if __name__ == '__main__':
    # קריאת PORT ממשתני סביבה (חשוב ל-Render.com)
    port = int(os.environ.get("PORT", Config.PORT))
    
    print("=" * 60)
    print(f"🚀 Starting {Config.BOT_NAME}")
    print(f"📡 Server running on http://{Config.HOST}:{port}")
    print(f"🔧 Debug Mode: {Config.DEBUG}")
    print(f"🔌 Enabled Plugins: {', '.join(Config.ENABLED_PLUGINS)}")
    print("=" * 60)
    print()
    
    app.run(
        host=Config.HOST,
        port=port,
        debug=Config.DEBUG
    )
