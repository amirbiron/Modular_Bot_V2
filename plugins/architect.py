# Architect Plugin - creates new plugins via GitHub API

import base64
import re
import requests

from config import Config


COMMAND_PREFIX = "/newbot"
GITHUB_API_BASE = "https://api.github.com"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
ANTHROPIC_VERSION = "2023-06-01"
CLAUDE_SYSTEM_PROMPT = (
    "אתה המוח מאחורי 'מפעל בוטים מודולרי'. אתה מפתח פייתון מומחה ועליך לייצר "
    "קוד פייתון מושלם שמתאים למבנה הפלאגינים שלנו. הקוד חייב לכלול פונקציית "
    "get_dashboard_widget() שמחזירה מילון עיצובי ופונקציית handle_message(text) "
    "שמבצעת את הלוגיקה המבוקשת. החזר אך ורק את הקוד, ללא הסברים מסביב"
)
SUCCESS_MESSAGE = (
    "הקוד נשמר בגיטהאב. ה-Deploy האוטומטי של Render התחיל! "
    "בעוד 2 דקות הבוט יהיה פעיל"
)


def get_dashboard_widget():
    return {
        "title": "Architect",
        "value": "Ready",
        "label": "Create new plugins with /newbot",
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
    return "\n".join(text_parts).strip()


def _generate_plugin_code(name, instruction):
    api_key = Config.ANTHROPIC_API_KEY
    if not api_key:
        return None, "חסר ANTHROPIC_API_KEY בקונפיגורציה."

    data = {
        "model": "claude-sonnet-4-5-20250929",
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": instruction}],
    }
    try:
        response = requests.post(
            ANTHROPIC_API_URL,
            headers=_anthropic_headers(api_key),
            json=data,
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException:
        try:
            print(f"Claude API Error: {response.text}")
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


def handle_message(text):
    if not text:
        return None

    stripped = text.strip()
    if not stripped.startswith(COMMAND_PREFIX):
        return None

    parts = stripped.split(maxsplit=2)
    if len(parts) < 3:
        return "שימוש: /newbot <name> <instruction>"

    _, name, instruction = parts
    if not _is_valid_name(name):
        return "שם פלאגין לא חוקי. השתמש באותיות, מספרים וקו תחתון בלבד."

    settings, error = _get_github_settings()
    if error:
        return error

    plugin_path = f"plugins/{name}.py"
    exists, error = _github_file_exists(settings, plugin_path)
    if error:
        return error
    if exists:
        return "פלאגין בשם הזה כבר קיים."

    code, error = _generate_plugin_code(name, instruction)
    if error:
        return error

    created, error = _github_create_file(settings, plugin_path, code)
    if not created:
        return error or "יצירת הבוט נכשלה."

    return SUCCESS_MESSAGE
