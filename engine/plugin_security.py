"""
Plugin security helpers.

This project dynamically imports user-generated plugins (e.g. plugins/bot_<id>.py).
To reduce risk, we perform a conservative static validation of plugin source code
and reject obvious dangerous capabilities (process execution, shell access, env
secrets access, arbitrary file IO, eval/exec).

NOTE: This is NOT a perfect sandbox. It is a guardrail / policy gate.
For strong isolation, run untrusted plugins in a separate container/VM.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Optional, Tuple


STATE_HELPER_END_MARKER = "# === End of State Helpers ==="


FORBIDDEN_IMPORT_ROOTS = {
    # process / shell execution
    "subprocess",
    "pty",
    "pexpect",
    # dynamic loading / introspection abuse
    "importlib",
}

FORBIDDEN_BUILTIN_CALLS = {
    "eval",
    "exec",
    "compile",
    "__import__",
    # arbitrary file IO (can leak secrets / write backdoors)
    "open",
}

FORBIDDEN_OS_CALL_ATTRS = {
    "system",
    "popen",
    # exec/spawn variants
    "execl",
    "execle",
    "execlp",
    "execlpe",
    "execv",
    "execve",
    "execvp",
    "execvpe",
    "spawnl",
    "spawnle",
    "spawnlp",
    "spawnlpe",
    "spawnv",
    "spawnve",
    "spawnvp",
    "spawnvpe",
}

FORBIDDEN_SYS_ATTRS = {
    # grabbing interpreter internals / module cache for abuse
    "modules",
}


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: Optional[str] = None


def _module_root(name: str) -> str:
    return name.split(".", 1)[0]


def _find_state_helper_end_line(source: str) -> Optional[int]:
    """
    Returns 1-based line number of the end-marker line, if present.
    Used to allow minimal env access in the injected helper only.
    """
    lines = source.splitlines()
    for idx, line in enumerate(lines, start=1):
        if line.strip() == STATE_HELPER_END_MARKER:
            return idx
    return None


def validate_user_plugin_source(source: str) -> ValidationResult:
    """
    Conservative static validation for user-generated plugins.

    Policy:
    - No process execution or shell utilities (subprocess/pty/pexpect, os.system, etc.)
    - No eval/exec/compile/__import__
    - No direct file IO via open()
    - No access to environment variables (os.environ) outside the injected state helper
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return ValidationResult(False, f"syntax_error: {e.msg}")

    helper_end_line = _find_state_helper_end_line(source)  # may be None

    for node in ast.walk(tree):
        # --- imports ---
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = _module_root(alias.name)
                if root in FORBIDDEN_IMPORT_ROOTS:
                    return ValidationResult(False, f"forbidden_import: {alias.name}")

        if isinstance(node, ast.ImportFrom):
            if node.module:
                root = _module_root(node.module)
                if root in FORBIDDEN_IMPORT_ROOTS:
                    return ValidationResult(False, f"forbidden_import: {node.module}")

        # --- forbidden builtin calls ---
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_BUILTIN_CALLS:
                return ValidationResult(False, f"forbidden_call: {node.func.id}")

        # --- attribute-based calls/access ---
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            base = node.func.value
            attr = node.func.attr

            # os.system(), os.popen(), os.exec*, os.spawn*
            if isinstance(base, ast.Name) and base.id == "os" and attr in FORBIDDEN_OS_CALL_ATTRS:
                return ValidationResult(False, f"forbidden_os_call: os.{attr}")

            # subprocess.* even if imported indirectly
            if isinstance(base, ast.Name) and base.id == "subprocess":
                return ValidationResult(False, "forbidden_subprocess_usage")

            # shlex.* is often used to help shelling out
            if isinstance(base, ast.Name) and base.id == "shlex":
                return ValidationResult(False, "forbidden_shlex_usage")

        # os.environ access (secrets) outside helper block
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "os" and node.attr == "environ":
                lineno = getattr(node, "lineno", None)
                if helper_end_line is None:
                    return ValidationResult(False, "forbidden_env_access: os.environ")
                if lineno is None or lineno > helper_end_line:
                    return ValidationResult(False, "forbidden_env_access: os.environ")

        # sys.modules access can be used for weird bypasses
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "sys" and node.attr in FORBIDDEN_SYS_ATTRS:
                return ValidationResult(False, f"forbidden_sys_access: sys.{node.attr}")

    return ValidationResult(True)

