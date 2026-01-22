# Architect Plugin - creates new plugins via GitHub API
# תומך ביצירת בוטים חדשים עבור מערכת SaaS

import base64
import json
import os
import re
import time
import requests
from pathlib import Path

from config import Config


COMMAND_PREFIX = "/create_bot"
GITHUB_API_BASE = "https://api.github.com"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
ANTHROPIC_VERSION = "2023-06-01"
BOT_REGISTRY_FILE = "bot_registry.json"

# נתיב לקובץ הרישום המקומי
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_BOT_REGISTRY_PATH = PROJECT_ROOT / BOT_REGISTRY_FILE

# מנגנון נעילה למניעת כפילויות - שומר את הטוקנים שנמצאים כרגע בתהליך יצירה
_creation_in_progress = {}
_CREATION_TIMEOUT = 180  # 3 דקות - זמן מקסימלי ליצירת בוט
CLAUDE_SYSTEM_PROMPT = """אתה המוח מאחורי 'מפעל בוטים מודולרי'. אתה מפתח פייתון מומחה.

עליך לייצר קוד פייתון מושלם שמתאים למבנה הפלאגינים שלנו.

הקוד חייב לכלול בדיוק שתי פונקציות:

1. get_dashboard_widget() - מחזירה מילון עם המבנה הבא:
   {
       "title": "שם הפלאגין",
       "value": "ערך להצגה",
       "label": "תיאור קצר",
       "status": "success/warning/danger/info",
       "icon": "bi-icon-name"  # Bootstrap Icon
   }

2. handle_message(text) - מקבלת טקסט מהמשתמש:
   - הפלאגין צריך להגיב לכל הודעה שנשלחת אליו (כי זה בוט עצמאי)
   - מבצע לוגיקה ומחזיר תשובה (string)

=== הנחיות קריטיות ליצירת הקוד ===

חובת /start:
- הפונקציה handle_message חייבת תמיד לזהות ולטפל בפקודה /start
- זו הפקודה הראשונה שכל משתמש שולח לבוט

תפריט ראשי:
- התגובה לפקודת /start חייבת להיות בעברית
- התגובה חייבת לכלול רשימה ברורה של כל הפקודות הזמינות בבוט
- לדוגמה: "ברוכים הבאים! הפקודות הזמינות:\n/new_game - להתחיל משחק חדש\n/stats - לצפות בסטטיסטיקות\n/help - עזרה"

פקודות גנריות:
- אל תשתמש בטוקן או בשם הקובץ כחלק מהפקודה
- אסור להשתמש בפקודות כמו /bot_123 או /plugin_name
- השתמש בפקודות טבעיות באנגלית בלבד (כמו /stats, /help, /reset, /new_game, /score)

טיפול בשגיאות:
- אם המשתמש שולח פקודה או הודעה לא מוכרת, הבוט צריך להחזיר הודעה ידידותית
- ההודעה צריכה להציע למשתמש ללחוץ על /start כדי לראות את רשימת הפקודות הזמינות
- לדוגמה: "לא הבנתי את הבקשה 🤔\nשלח /start כדי לראות את כל הפקודות הזמינות"

=== כללים חשובים נוספים ===
- החזר אך ורק את הקוד, ללא הסברים, ללא markdown, ללא ```python
- הקוד חייב להיות תקין ומוכן להרצה
- אם צריך לגשת ל-API חיצוני, השתמש ב-requests עם timeout
- תפוס שגיאות בצורה נכונה והחזר הודעת שגיאה ידידותית
- הבוט הזה יהיה עצמאי ולכן צריך להגיב לכל הודעה"""
SUCCESS_MESSAGE = (
    "✅ הבוט נוצר בהצלחה!\n"
    "📦 הקוד נשמר בגיטהאב\n"
    "🔗 Webhook הוגדר לטלגרם\n"
    "⏳ ה-Deploy האוטומטי של Render התחיל - בעוד 2 דקות הבוט יהיה פעיל"
)


def _is_creation_in_progress(bot_token):
    """
    בודק אם יש כרגע תהליך יצירה פעיל לטוקן זה.
    מנקה תהליכים ישנים שעברו timeout.
    """
    current_time = time.time()
    
    # ניקוי תהליכים ישנים
    expired = [t for t, start_time in _creation_in_progress.items() 
               if current_time - start_time > _CREATION_TIMEOUT]
    for t in expired:
        _creation_in_progress.pop(t, None)
    
    return bot_token in _creation_in_progress


def _start_creation(bot_token):
    """מסמן שתהליך יצירה התחיל לטוקן זה."""
    _creation_in_progress[bot_token] = time.time()


def _end_creation(bot_token):
    """מסמן שתהליך יצירה הסתיים לטוקן זה."""
    _creation_in_progress.pop(bot_token, None)


def _update_local_registry(bot_token, plugin_filename):
    """
    מעדכן את קובץ הרישום המקומי (לא רק בגיטהאב).
    זה מאפשר לבוט החדש לעבוד מיד ללא צורך בהמתנה ל-Deploy.
    """
    try:
        # קרא את הרישום הקיים
        if LOCAL_BOT_REGISTRY_PATH.exists():
            with open(LOCAL_BOT_REGISTRY_PATH, 'r', encoding='utf-8') as f:
                registry = json.load(f)
        else:
            registry = {}
        
        # הוסף את הבוט החדש
        registry[bot_token] = plugin_filename
        
        # שמור את הקובץ
        with open(LOCAL_BOT_REGISTRY_PATH, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Local registry updated: {plugin_filename}")
        return True
    except Exception as e:
        print(f"❌ Failed to update local registry: {e}")
        return False


def get_dashboard_widget():
    return {
        "title": "Architect",
        "value": "Ready",
        "label": "Create new bots with /create_bot",
        "status": "info",
        "icon": "bi-building",
    }


def _is_valid_name(name):
    return re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name) is not None


def _normalize_instruction(instruction):
    return " ".join(instruction.strip().split())


def _anthropic_headers(api_key):
    return {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }


def _build_user_prompt(name, instruction):
    normalized = _normalize_instruction(instruction)
    return "\n".join(
        [
            f"שם הפלאגין: {name}",
            f"הנחיית משתמש: {normalized}",
            f"הפלאגין צריך להגיב לפקודה /{name}.",
        ]
    )


def _format_claude_error(response):
    if response.status_code >= 500:
        return "שירות Claude לא זמין כרגע. נסה שוב מאוחר יותר."

    error_text = response.text
    try:
        error_text = response.json()
    except Exception:
        pass
    return f"שגיאה בשירות Claude: {response.status_code} {error_text}"


def _clean_code_from_markdown(code):
    """Remove markdown code fences if Claude returned them despite instructions."""
    code = code.strip()
    # Remove ```python or ``` at the start
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    # Remove ``` at the end
    if code.endswith("```"):
        code = code[:-3]
    return code.strip()


def _extract_claude_code(payload):
    content = payload.get("content") if isinstance(payload, dict) else None
    if not isinstance(content, list):
        return None

    text_parts = [
        part.get("text")
        for part in content
        if isinstance(part, dict) and part.get("type") == "text" and part.get("text")
    ]
    if not text_parts:
        return None
    
    raw_code = "\n".join(text_parts).strip()
    return _clean_code_from_markdown(raw_code)


def _generate_plugin_code(name, instruction):
    api_key = Config.ANTHROPIC_API_KEY
    if not api_key:
        return None, "חסר ANTHROPIC_API_KEY בקונפיגורציה."

    user_prompt = _build_user_prompt(name, instruction)
    data = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 8000,
        "system": CLAUDE_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    try:
        response = requests.post(
            ANTHROPIC_API_URL,
            headers=_anthropic_headers(api_key),
            json=data,
            timeout=120,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Claude API RequestException: {e}")
        try:
            print(f"Claude API Response: {response.text}")
        except Exception:
            pass
        return None, "שירות Claude לא זמין כרגע. נסה שוב מאוחר יותר."

    try:
        response_payload = response.json()
    except ValueError:
        return None, "שגיאה בפענוח תגובת Claude."

    code = _extract_claude_code(response_payload)
    if not code:
        return None, "Claude לא החזיר קוד."

    return code, None


def _get_github_settings():
    token = Config.GITHUB_TOKEN
    user = Config.GITHUB_USER
    repo = Config.GITHUB_REPO
    branch = Config.GITHUB_BRANCH
    if not token or not user or not repo:
        return None, "חסר GITHUB_TOKEN, GITHUB_USER או GITHUB_REPO בקונפיגורציה."
    return {
        "token": token,
        "user": user,
        "repo": repo,
        "branch": branch,
    }, None


def _github_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


def _github_file_exists(settings, path):
    url = f"{GITHUB_API_BASE}/repos/{settings['user']}/{settings['repo']}/contents/{path}"
    params = {}
    if settings.get("branch"):
        params["ref"] = settings["branch"]

    response = requests.get(
        url, headers=_github_headers(settings["token"]), params=params, timeout=10
    )
    if response.status_code == 200:
        return True, None
    if response.status_code == 404:
        return False, None
    return None, f"שגיאה בבדיקת קיום הקובץ: {response.status_code} {response.text}"


def _github_create_file(settings, path, content):
    url = f"{GITHUB_API_BASE}/repos/{settings['user']}/{settings['repo']}/contents/{path}"
    payload = {
        "message": f"Add plugin {path} via architect",
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
    }
    if settings.get("branch"):
        payload["branch"] = settings["branch"]

    response = requests.put(
        url, headers=_github_headers(settings["token"]), json=payload, timeout=10
    )
    if response.status_code in (200, 201):
        return True, None

    error_text = response.text
    try:
        error_text = response.json()
    except Exception:
        pass
    return False, f"שגיאה ביצירת הקובץ בגיטהאב: {response.status_code} {error_text}"


def _github_get_file(settings, path):
    """
    קורא קובץ מגיטהאב ומחזיר את התוכן וה-SHA.
    """
    url = f"{GITHUB_API_BASE}/repos/{settings['user']}/{settings['repo']}/contents/{path}"
    params = {}
    if settings.get("branch"):
        params["ref"] = settings["branch"]

    response = requests.get(
        url, headers=_github_headers(settings["token"]), params=params, timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content, data["sha"], None
    if response.status_code == 404:
        return None, None, None
    return None, None, f"שגיאה בקריאת הקובץ: {response.status_code}"


def _github_update_file(settings, path, content, sha, message):
    """
    מעדכן קובץ קיים בגיטהאב.
    """
    url = f"{GITHUB_API_BASE}/repos/{settings['user']}/{settings['repo']}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "sha": sha,
    }
    if settings.get("branch"):
        payload["branch"] = settings["branch"]

    response = requests.put(
        url, headers=_github_headers(settings["token"]), json=payload, timeout=10
    )
    if response.status_code in (200, 201):
        return True, None
    
    error_text = response.text
    try:
        error_text = response.json()
    except Exception:
        pass
    return False, f"שגיאה בעדכון הקובץ בגיטהאב: {response.status_code} {error_text}"


def _add_bot_to_registry(settings, bot_token, plugin_filename):
    """
    מוסיף בוט חדש לקובץ הרישום בגיטהאב.
    """
    # קרא את הקובץ הקיים
    content, sha, error = _github_get_file(settings, BOT_REGISTRY_FILE)
    
    if error:
        return False, error
    
    # אם הקובץ לא קיים, צור אותו
    if content is None:
        registry = {}
        # צור קובץ חדש
        registry[bot_token] = plugin_filename
        new_content = json.dumps(registry, indent=2, ensure_ascii=False)
        return _github_create_file(settings, BOT_REGISTRY_FILE, new_content)
    
    # עדכן את הרישום הקיים
    try:
        registry = json.loads(content)
    except json.JSONDecodeError:
        registry = {}
    
    registry[bot_token] = plugin_filename
    new_content = json.dumps(registry, indent=2, ensure_ascii=False)
    
    return _github_update_file(
        settings, 
        BOT_REGISTRY_FILE, 
        new_content, 
        sha,
        f"Add bot {plugin_filename} to registry"
    )


def _set_telegram_webhook(bot_token):
    """
    מגדיר webhook לטלגרם עבור הבוט החדש.
    """
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not render_url:
        return False, "חסר RENDER_EXTERNAL_URL בקונפיגורציה"
    
    webhook_url = f"{render_url.rstrip('/')}/{bot_token}"
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    try:
        response = requests.post(
            api_url,
            json={"url": webhook_url},
            timeout=10
        )
        if response.ok:
            result = response.json()
            if result.get("ok"):
                return True, None
            return False, f"Telegram API error: {result.get('description', 'Unknown error')}"
        return False, f"שגיאה בהגדרת webhook: {response.status_code}"
    except Exception as e:
        return False, f"שגיאה בהגדרת webhook: {e}"


def _generate_plugin_name_from_token(bot_token):
    """
    יוצר שם פלאגין בטוח מהטוקן.
    משתמש בחלק הראשון של הטוקן (ה-bot_id).
    """
    # הטוקן בפורמט: BOT_ID:HASH
    # ניקח את ה-bot_id ונוסיף prefix
    if ':' in bot_token:
        bot_id = bot_token.split(':')[0]
    else:
        bot_id = bot_token[:10]
    
    return f"bot_{bot_id}"


def handle_message(text):
    if not text:
        return None

    stripped = text.strip()
    if not stripped.startswith(COMMAND_PREFIX):
        return None

    parts = stripped.split(maxsplit=2)
    if len(parts) < 3:
        return "שימוש: /create_bot <token> <instruction>\nדוגמה: /create_bot 123456:ABC-DEF בוט שמספר בדיחות"

    _, bot_token, instruction = parts
    
    # וידוא שהטוקן נראה תקין (פורמט בסיסי)
    if ':' not in bot_token or len(bot_token) < 20:
        return "טוקן לא תקין. וודא שהעתקת את הטוקן המלא מ-BotFather."

    # בדיקה אם יש כבר תהליך יצירה פעיל לטוקן זה (מניעת כפילויות)
    if _is_creation_in_progress(bot_token):
        print(f"⏳ Creation already in progress for token: {bot_token[:10]}...")
        return "⏳ הבוט כבר בתהליך יצירה, אנא המתן..."

    # יצירת שם פלאגין מהטוקן
    plugin_name = _generate_plugin_name_from_token(bot_token)

    settings, error = _get_github_settings()
    if error:
        return error

    plugin_path = f"plugins/{plugin_name}.py"
    exists, error = _github_file_exists(settings, plugin_path)
    if error:
        return error
    if exists:
        return "בוט עם טוקן זה כבר קיים במערכת. אם תרצה ליצור בוט חדש, השתמש בטוקן אחר."

    # סימון שתהליך היצירה התחיל (למניעת כפילויות מ-webhook)
    _start_creation(bot_token)
    print(f"🚀 Starting bot creation for token: {bot_token[:10]}...")

    try:
        # יצירת קוד הפלאגין
        code, error = _generate_plugin_code(plugin_name, instruction)
        if error:
            return error

        # שמירת הקוד בגיטהאב
        created, error = _github_create_file(settings, plugin_path, code)
        if not created:
            return error or "יצירת הבוט נכשלה."

        print(f"✅ Plugin file created on GitHub: {plugin_path}")

        # הוספת הבוט לרישום בגיטהאב
        registered, error = _add_bot_to_registry(settings, bot_token, f"{plugin_name}.py")
        if not registered:
            return f"הקוד נשמר אבל הרישום בגיטהאב נכשל: {error}"

        print(f"✅ Bot registered on GitHub: {plugin_name}")

        # עדכון הרישום המקומי (כדי שהבוט יעבוד מיד)
        _update_local_registry(bot_token, f"{plugin_name}.py")

        # הגדרת webhook לטלגרם
        webhook_set, error = _set_telegram_webhook(bot_token)
        if not webhook_set:
            return f"הקוד נשמר והבוט נרשם, אבל הגדרת ה-Webhook נכשלה: {error}"

        print(f"✅ Webhook set for bot: {plugin_name}")

        return SUCCESS_MESSAGE
    finally:
        # סימון שתהליך היצירה הסתיים
        _end_creation(bot_token)
