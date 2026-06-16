import os
import subprocess
from langchain_core.tools import tool


@tool
def open_app(app_name: str) -> str:
    """Open an application by name."""
    try:
        if os.name == 'nt':
            os.system(f"start {app_name}")
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