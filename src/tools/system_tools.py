import os
import subprocess
from langchain_core.tools import tool

WINDOWS_APP_MAP = {
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "firefox": "firefox",
    "word": "winword",
    "microsoft word": "winword",
    "excel": "excel",
    "microsoft excel": "excel",
    "powerpoint": "powerpnt",
    "spotify": "spotify",
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "explorer": "explorer",
    "file explorer": "explorer",
    "cmd": "cmd",
    "command prompt": "cmd",
    "terminal": "wt",
    "settings": "ms-settings:",
    "whatsapp": "whatsapp",
}

@tool
def open_app(app_name: str) -> str:
    """Open an application on the laptop by name (e.g. 'chrome', 'notepad', 'spotify', 'vscode')."""
    try:
        if os.name == 'nt':
            command = WINDOWS_APP_MAP.get(app_name.strip().lower(), app_name.strip())
            # The empty "" after start is the window-title slot, required so that
            # commands/paths containing spaces don't get misread by cmd's "start".
            os.system(f'start "" {command}')
        else:
            subprocess.Popen(["open", "-a", app_name])
        return f"Opened {app_name}"
    except Exception as e:
        return f"Could not open {app_name}: {str(e)}"

@tool
def close_app(app_name: str) -> str:
    """Close an application by name."""
    try:
        if os.name == "nt":
            os.system(f"taskkill /f /im {app_name}.exe")
        else:
            subprocess.Popen(["pkill", "-f", app_name])

        return f"Closed {app_name}"

    except Exception as e:
        return f"Could not close {app_name}: {str(e)}"


@tool
def get_volume() -> str:
    """Return the current system volume (placeholder)."""
    return "Volume control not implemented yet."


@tool
def shutdown_pc() -> str:
    """Shutdown the computer (currently disabled for safety)."""
    return "Shutdown command is disabled for safety."