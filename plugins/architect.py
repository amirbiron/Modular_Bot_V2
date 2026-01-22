# Architect Plugin - auto-generates new plugin scaffolds

import re
from pathlib import Path


PLUGIN_DIR = Path(__file__).resolve().parent
COMMAND_PREFIX = "/newbot"


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
            f"# Auto-generated plugin: {name}",
            f"# Instruction: {normalized}",
            "",
            "def get_dashboard_widget():",
            "    return {",
            f"        'title': '{name}',",
            "        'value': 'Ready',",
            "        'label': 'Auto-generated plugin',",
            "        'status': 'info',",
            "        'icon': 'bi-robot'",
            "    }",
            "",
            "def handle_message(text):",
            f"    if text.strip().startswith('/{name}'):",
            f"        return {instruction_literal}",
            "    return None",
            "",
        ]
    )


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

    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
    plugin_path = PLUGIN_DIR / f"{name}.py"
    if plugin_path.exists():
        return "פלאגין בשם הזה כבר קיים."

    try:
        template = _build_template(name, instruction)
        plugin_path.write_text(template, encoding="utf-8")
    except Exception as e:
        return f"יצירת הבוט נכשלה: {e}"

    return "הבוט נוצר! כדי להפעיל אותו, יש לבצע Deploy מחדש"
