# Architect Plugin - creates new plugins via GitHub API

import base64
import re
import requests

from config import Config


COMMAND_PREFIX = "/newbot"
GITHUB_API_BASE = "https://api.github.com"
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


def _build_template(name, instruction):
    normalized = _normalize_instruction(instruction)
    instruction_literal = repr(normalized)
    return "\n".join(
        [
            f"\"\"\"",
            f"Auto-generated plugin: {name}",
            f"Instruction: {normalized}",
            f"\"\"\"",
            "",
            "def get_dashboard_widget():",
            "    return {",
            f"        \"title\": \"{name}\",",
            "        \"value\": \"Ready\",",
            "        \"label\": \"Auto-generated plugin\",",
            "        \"status\": \"info\",",
            "        \"icon\": \"bi-robot\",",
            "    }",
            "",
            "def handle_message(text):",
            f"    if text.strip().startswith(\"/{name}\"):",
            f"        return {instruction_literal}",
            "    return None",
            "",
        ]
    )


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

    template = _build_template(name, instruction)
    created, error = _github_create_file(settings, plugin_path, template)
    if not created:
        return error or "יצירת הבוט נכשלה."

    return SUCCESS_MESSAGE
