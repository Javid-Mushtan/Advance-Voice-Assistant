import json # followed by tutorials
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Any
from langchain_core.tools import tool
from src.utils.logger import logger

MACROS_FILE = "data/macros.json"

def get_all_tools_map():
    from src.tools.system_tools import (
        open_app, close_app, get_volume, open_website,
        toggle_wifi, scan_wifi_networks, connect_wifi,
        disconnect_wifi, get_wifi_status, list_saved_wifi_networks,
        forget_wifi_network, get_wifi_password,
        set_volume, get_current_volume, increase_volume, decrease_volume,
        mute_volume, unmute_volume,
        set_brightness, get_brightness, increase_brightness, decrease_brightness,
        turn_on_bluetooth, turn_off_bluetooth, toggle_airplane_mode,
    )
    from src.tools.api_tools import (
        get_weather, web_search,
        get_weather_current_location, get_city,
    )
    from src.tools.personal_tools import (
        send_email, add_note,
        send_whatsapp_message, open_whatsapp_chat_for_call,
    )
    from src.tools.phone_tools import (
        call_contact, call_number, end_call, resolve_contact_number,
        get_phone_last_location, get_phone_live_location,
        open_app_on_phone, set_phone_wifi, compose_sms, check_phone_connection,
    )
    from src.tools.location_tools import (
        get_current_location, get_location_coordinates, get_maps_link,
    )
    from src.tools.admin_tools import (
        scan_files, delete_file, move_file, read_file_contents, list_directory,
        uninstall_application, install_application, list_installed_apps,
        list_running_processes, kill_process, run_command,
        get_network_info, list_open_ports, ping_host,
        get_disk_usage, get_system_info, shutdown_pc, cancel_shutdown, restart_pc,
    )
    from src.tools.news_search_tools import (
        get_world_news, get_news_by_topic, deep_search, search_person,
    )

    all_tools = [
        open_app, close_app, get_volume, open_website,
        toggle_wifi, scan_wifi_networks, connect_wifi,
        disconnect_wifi, get_wifi_status, list_saved_wifi_networks,
        forget_wifi_network, get_wifi_password,
        set_volume, get_current_volume, increase_volume, decrease_volume,
        mute_volume, unmute_volume,
        set_brightness, get_brightness, increase_brightness, decrease_brightness,
        turn_on_bluetooth, turn_off_bluetooth, toggle_airplane_mode,
        get_weather, web_search, get_weather_current_location, get_city,
        send_email, add_note, send_whatsapp_message, open_whatsapp_chat_for_call,
        call_contact, call_number, end_call, resolve_contact_number,
        get_phone_last_location, get_phone_live_location,
        open_app_on_phone, set_phone_wifi, compose_sms, check_phone_connection,
        get_current_location, get_location_coordinates, get_maps_link,
        scan_files, delete_file, move_file, read_file_contents, list_directory,
        uninstall_application, install_application, list_installed_apps,
        list_running_processes, kill_process, run_command,
        get_network_info, list_open_ports, ping_host,
        get_disk_usage, get_system_info, shutdown_pc, cancel_shutdown, restart_pc,
        get_world_news, get_news_by_topic, deep_search, search_person,
    ]

    return {t.name: t for t in all_tools}
def _load_macros():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(MACROS_FILE):
        return {}
    try:
        with open(MACROS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_macros(macros: dict):
    os.makedirs("data", exist_ok=True)
    with open(MACROS_FILE, "w") as f:
        json.dump(macros, f, indent=2)

BUILTIN_MACROS = {
    "morning routine": {
        "description": "Start the day — open Chrome, check weather, play music",
        "trigger_phrases": ["morning routine", "good morning", "start my day"],
        "steps": [
            {"tool": "get_weather_current_location", "args": {}, "delay": 0},
            {"tool": "get_world_news",               "args": {}, "delay": 1},
            {"tool": "open_app",  "args": {"app_name": "chrome"},   "delay": 2},
            {"tool": "open_app",  "args": {"app_name": "spotify"},  "delay": 3},
        ]
    },
    "work mode": {
        "description": "Focus mode — open VS Code, close distractions",
        "trigger_phrases": ["work mode", "focus mode", "start working"],
        "steps": [
            {"tool": "close_app",     "args": {"app_name": "spotify"},  "delay": 0},
            {"tool": "open_app",      "args": {"app_name": "vscode"},   "delay": 1},
            {"tool": "set_volume",    "args": {"level": 30},            "delay": 2},
            {"tool": "set_brightness","args": {"level": 80},            "delay": 0},
        ]
    },
    "break time": {
        "description": "Take a break — lock screen, open Spotify, dim screen",
        "trigger_phrases": ["break time", "take a break", "i need a break"],
        "steps": [
            {"tool": "open_app",      "args": {"app_name": "spotify"},  "delay": 0},
            {"tool": "set_volume",    "args": {"level": 60},            "delay": 1},
            {"tool": "set_brightness","args": {"level": 40},            "delay": 0},
        ]
    },
    "shutdown routine": {
        "description": "End of day — save notes, then shut down",
        "trigger_phrases": ["shutdown routine", "end of day", "good night"],
        "steps": [
            {"tool": "add_note",   "args": {"content": "Session ended — end of day routine triggered."}, "delay": 0},
            {"tool": "shutdown_pc","args": {"delay_seconds": 60}, "delay": 2},
        ]
    },
    "presentation mode": {
        "description": "Prepare for a presentation — full brightness, max volume, close extra apps",
        "trigger_phrases": ["presentation mode", "start presentation", "screen share mode"],
        "steps": [
            {"tool": "set_brightness","args": {"level": 100},            "delay": 0},
            {"tool": "set_volume",    "args": {"level": 80},             "delay": 0},
            {"tool": "close_app",     "args": {"app_name": "spotify"},   "delay": 1},
            {"tool": "open_website",  "args": {"url": "slides.google.com"}, "delay": 2},
        ]
    },
    "night mode": {
        "description": "Wind down — dim screen, low volume, close work apps",
        "trigger_phrases": ["night mode", "wind down", "going to sleep"],
        "steps": [
            {"tool": "set_brightness","args": {"level": 20},            "delay": 0},
            {"tool": "set_volume",    "args": {"level": 20},            "delay": 0},
            {"tool": "close_app",     "args": {"app_name": "chrome"},   "delay": 1},
            {"tool": "close_app",     "args": {"app_name": "vscode"},   "delay": 1},
        ]
    },
}

def _execute_macro_steps(macro_name: str, steps: list, tool_map: dict) -> str:
    """
    Execute a list of macro steps sequentially.
    Returns a summary of what was done.
    """

    results = []
    logger.info(f"[Macro] Executing: {macro_name} ({len(steps)} steps)")

    for i, step in enumerate(steps):
        tool_name = step.get("tool")
        args = step.get("args", {})
        delay = step.get("delay", 0)

        if delay > 0:
            time.sleep(delay)

        if tool_name not in tool_map:
            results.append(f"Step {i + 1}: unknown tool '{tool_name}' — skipped")
            logger.warning(f"[Macro] Unknown tool: {tool_name}")
            continue

        try:
            result = tool_map[tool_name].invoke(args)
            short = str(result)[:60]
            results.append(f"Step {i + 1} ({tool_name}): {short}")
            logger.info(f"[Macro] Step {i + 1} '{tool_name}' → {short}")
        except Exception as e:
            results.append(f"Step {i + 1} ({tool_name}): error — {e}")
            logger.error(f"[Macro] Step {i + 1} error: {e}")

    return f"Macro '{macro_name}' complete:\n" + "\n".join(results)


@tool
def run_macro(macro_name: str) -> str:
    """
    Run a saved macro (multi-step routine) by name.
    Use for: 'morning routine', 'work mode', 'break time', 'night mode',
    'presentation mode', 'shutdown routine', or any custom macro the user created.

    This executes all steps in sequence automatically.
    """

    name_key = macro_name.strip().lower()

    user_macros = _load_macros()
    macro = user_macros.get(name_key) or BUILTIN_MACROS.get(name_key)
    if not macro:
        for key, m in {**BUILTIN_MACROS, **user_macros}.items():
            phrases = m.get("trigger_phrases", [])
            if any(name_key in p or p in name_key for p in phrases):
                macro = m
                name_key = key
                break

    if not macro:
        saved_names = list(user_macros.keys()) + list(BUILTIN_MACROS.keys())
        return (
            f"No macro named '{macro_name}' found. "
            f"Available: {', '.join(saved_names)}. "
            f"Say 'create a macro called X' to make a new one."
        )

    tool_map = get_all_tools_map()
    steps = macro.get("steps", [])

    if not steps:
        return f"Macro '{macro_name}' has no steps defined."

    return _execute_macro_steps(name_key, steps, tool_map)


@tool
def create_macro(name: str, description: str, steps_json: str) -> str:
    """
    Create and save a new named macro (multi-step routine).

    Args:
        name:        Short name for the macro, e.g. 'gym mode'
        description: What it does, e.g. 'Prepare for the gym'
        steps_json:  JSON array of steps. Each step:
                     {"tool": "tool_name", "args": {...}, "delay": 0}

    Example steps_json:
        [
          {"tool": "set_volume", "args": {"level": 80}, "delay": 0},
          {"tool": "open_app", "args": {"app_name": "spotify"}, "delay": 1}
        ]

    Call this when the user says 'create a macro', 'save a routine',
    'when I say X do Y and Z'.
    """
    try:
        steps = json.loads(steps_json)
    except json.JSONDecodeError as e:
        return f"Invalid steps JSON: {e}. Please provide valid JSON."

    if not isinstance(steps, list) or not steps:
        return "Steps must be a non-empty JSON array."

    macros = _load_macros()
    key = name.strip().lower()
    macros[key] = {
        "description": description,
        "trigger_phrases": [key],
        "steps": steps,
        "created_at": datetime.now().isoformat(),
    }
    _save_macros(macros)

    step_summary = "\n".join(
        f"  {i + 1}. {s.get('tool')}({s.get('args', {})})"
        for i, s in enumerate(steps)
    )
    return (
        f"Macro '{name}' saved with {len(steps)} steps:\n"
        f"{step_summary}\n"
        f"Say 'run {name}' anytime to execute it."
    )


@tool
def list_macros() -> str:
    """
    List all available macros — both built-in and user-created.
    Use for: 'what macros do I have', 'show my routines', 'list automations'.
    """
    user_macros = _load_macros()
    lines = ["📋 Available macros:\n"]

    lines.append("Built-in:")
    for name, macro in BUILTIN_MACROS.items():
        n_steps = len(macro.get("steps", []))
        lines.append(f"  • {name} — {macro['description']} ({n_steps} steps)")

    if user_macros:
        lines.append("\nYour custom macros:")
        for name, macro in user_macros.items():
            n_steps = len(macro.get("steps", []))
            lines.append(f"  • {name} — {macro.get('description', 'no description')} ({n_steps} steps)")
    else:
        lines.append("\nNo custom macros yet. Say 'create a macro called X' to make one.")

    return "\n".join(lines)


@tool
def delete_macro(name: str) -> str:
    """
    Delete a saved custom macro by name.
    Note: built-in macros cannot be deleted.
    Use for: 'delete the gym mode macro', 'remove macro X'.
    """
    macros = _load_macros()
    key = name.strip().lower()
    if key not in macros:
        if key in BUILTIN_MACROS:
            return f"'{name}' is a built-in macro and cannot be deleted."
        return f"No custom macro named '{name}' found."
    del macros[key]
    _save_macros(macros)
    return f"Macro '{name}' deleted."


@tool
def schedule_macro(macro_name: str, time_str: str, repeat: str = "once") -> str:
    """
    Schedule a macro to run automatically at a specific time.

    Args:
        macro_name: Name of the macro to schedule, e.g. 'morning routine'
        time_str:   Time to run it, e.g. '08:00', '8am', '14:30'
        repeat:     'once', 'daily', 'weekdays', 'weekends'

    Use for: 'run morning routine every day at 8am',
             'schedule work mode at 9am on weekdays'.
    """
    macros = _load_macros()
    key = macro_name.strip().lower()

    if key not in macros and key not in BUILTIN_MACROS:
        return f"No macro named '{macro_name}'. Create it first."

    # Normalize time string
    time_str = time_str.strip().lower().replace("am", "").replace("pm", "").strip()
    try:
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        run_at = f"{hour:02d}:{minute:02d}"
    except Exception:
        return f"Couldn't parse time '{time_str}'. Use format like '08:00' or '8am'."

    # Save schedule
    schedules_file = "data/schedules.json"
    try:
        schedules = json.load(open(schedules_file)) if os.path.exists(schedules_file) else []
    except Exception:
        schedules = []

    schedule_entry = {
        "macro": key,
        "time": run_at,
        "repeat": repeat,
        "created_at": datetime.now().isoformat(),
        "active": True,
    }
    schedules.append(schedule_entry)
    os.makedirs("data", exist_ok=True)
    json.dump(schedules, open(schedules_file, "w"), indent=2)

    return (
        f"Scheduled '{macro_name}' to run at {run_at} ({repeat}). "
        f"Make sure JARVIS is running at that time."
    )


@tool
def describe_macro(macro_name: str) -> str:
    """
    Show all steps of a specific macro in detail.
    Use for: 'what does morning routine do', 'show me the steps of work mode'.
    """
    user_macros = _load_macros()
    key = macro_name.strip().lower()
    macro = user_macros.get(key) or BUILTIN_MACROS.get(key)

    if not macro:
        return f"No macro named '{macro_name}'."

    steps = macro.get("steps", [])
    lines = [
        f"Macro: {macro_name}",
        f"Description: {macro.get('description', 'N/A')}",
        f"Steps ({len(steps)}):",
    ]
    for i, step in enumerate(steps):
        tool_name = step.get("tool", "?")
        args = step.get("args", {})
        delay = step.get("delay", 0)
        delay_str = f" (wait {delay}s)" if delay else ""
        args_str = ", ".join(f"{k}={v}" for k, v in args.items())
        lines.append(f"  {i + 1}. {tool_name}({args_str}){delay_str}")

    return "\n".join(lines)


class MacroScheduler:
    """
    Background thread that checks every minute if a scheduled macro
    should run and executes it if so.
    Run MacroScheduler().start() once when JARVIS starts.
    """

    def __init__(self):
        self._thread = None
        self._stop = threading.Event()

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="MacroScheduler"
        )
        self._thread.start()
        logger.info("[MacroScheduler] Started.")

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            try:
                self._check_schedules()
            except Exception as e:
                logger.error(f"[MacroScheduler] Error: {e}")
            self._stop.wait(timeout=30)

    def _check_schedules(self):
        schedules_file = "data/schedules.json"
        if not os.path.exists(schedules_file):
            return

        try:
            schedules = json.load(open(schedules_file))
        except Exception:
            return

        now = datetime.now()
        now_str = now.strftime("%H:%M")
        weekday = now.weekday()
        changed = False

        for entry in schedules:
            if not entry.get("active"):
                continue
            if entry.get("time") != now_str:
                continue

            repeat = entry.get("repeat", "once")

            should_run = False
            if repeat == "once":
                should_run = True
                entry["active"] = False
                changed = True
            elif repeat == "daily":
                should_run = True
            elif repeat == "weekdays" and weekday < 5:
                should_run = True
            elif repeat == "weekends" and weekday >= 5:
                should_run = True

            if should_run:
                macro_name = entry.get("macro", "")
                logger.info(f"[MacroScheduler] Triggering scheduled macro: {macro_name}")
                threading.Thread(
                    target=self._run_macro_background,
                    args=(macro_name,),
                    daemon=True,
                ).start()

        if changed:
            json.dump(schedules, open(schedules_file, "w"), indent=2)

    def _run_macro_background(self, macro_name: str):
        try:
            result = run_macro.invoke({"macro_name": macro_name})
            logger.info(f"[MacroScheduler] {macro_name} result: {result[:100]}")
        except Exception as e:
            logger.error(f"[MacroScheduler] Failed to run {macro_name}: {e}")

macro_scheduler = MacroScheduler()
