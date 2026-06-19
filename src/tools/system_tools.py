import os
import subprocess
import webbrowser
from langchain_core.tools import tool
from src.utils.logger import logger

# Common Windows app names -> the actual command Windows understands.
# "start" only works for things on PATH or registered in Windows, so plain
# words like "chrome" or "word" need to be mapped to their real launch command.
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
}


def _find_app_id(app_name: str) -> str | None:
    """
    Ask Windows itself which installed app best matches app_name, using
    Get-StartApps (the same list the Start Menu search uses). This is what
    lets things like 'whatsapp' or any other installed Store/desktop app be
    found without us having to hardcode every possible app name.
    Returns the AppID Windows uses to launch it, or None if nothing matched.
    """
    try:
        ps_script = (
            f"$m = Get-StartApps | Where-Object {{ $_.Name -like '*{app_name}*' }} "
            "| Select-Object -First 1; $m.AppID"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=10
        )
        app_id = result.stdout.strip()
        return app_id or None
    except Exception as e:
        logger.warning(f"App lookup failed for '{app_name}': {e}")
        return None


@tool
def open_app(app_name: str) -> str:
    """Open an application on the laptop by name (e.g. 'chrome', 'notepad', 'whatsapp', 'spotify', 'vscode')."""
    try:
        if os.name == 'nt':
            key = app_name.strip().lower()

            # Fast path for common apps we already know the launch command for.
            if key in WINDOWS_APP_MAP:
                command = WINDOWS_APP_MAP[key]
                # The empty "" after start is the window-title slot, required so that
                # commands/paths containing spaces don't get misread by cmd's "start".
                os.system(f'start "" {command}')
                return f"Opened {app_name}"

            # Otherwise, ask Windows what's actually installed (covers Store
            # apps like WhatsApp, plus anything else not in the map above).
            app_id = _find_app_id(app_name)
            if app_id:
                # os.startfile talks to the Windows shell directly (ShellExecute),
                # so it doesn't depend on explorer.exe being resolvable on PATH.
                os.startfile(f'shell:AppsFolder\\{app_id}')
                return f"Opened {app_name}"

            return (
                f"I couldn't find '{app_name}' installed on this laptop. "
                f"Check the spelling, or it may not be installed."
            )
        else:
            subprocess.Popen(["open", "-a", app_name])
            return f"Opened {app_name}"
    except Exception as e:
        return f"Could not open {app_name}: {str(e)}"

@tool
def open_website(url: str) -> str:
    """Open a website in MS Edge. Pass a site name or URL, e.g. 'youtube.com' or 'https://github.com'."""
    site = url.strip()
    if not site.lower().startswith(("http://", "https://")):
        site = f"https://{site}"
    try:
        if os.name == "nt":
            os.system(f'start chrome "{site}"')
        else:
            subprocess.Popen(["open", "-a", "Google Chrome", site])
        return f"Opened {site} in Chrome"
    except Exception:
        try:
            webbrowser.open(site)
            return f"Chrome wasn't available, so I opened {site} in your default browser instead."
        except Exception as e:
            return f"Could not open {site}: {str(e)}"


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