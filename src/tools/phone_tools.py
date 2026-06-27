import re
import subprocess
from langchain_core.tools import tool

DEVICE_ADDR = None


def _adb(args: list[str], timeout: int = 15) -> tuple[int, str]:
    cmd = ["adb"]
    if DEVICE_ADDR:
        cmd += ["-s", DEVICE_ADDR]
    cmd += args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (result.stdout + result.stderr).strip()
        return result.returncode, out
    except FileNotFoundError:
        return 1, "adb not found on PATH. Install Android platform-tools."
    except subprocess.TimeoutExpired:
        return 1, "adb command timed out."


def _ensure_connected() -> str | None:
    """Returns an error string if no device is reachable, else None."""
    code, out = _adb(["get-state"], timeout=5)
    if code == 0 and out.strip() == "device":
        return None

    # Give a real diagnostic instead of a generic message - "already connected"
    # from the user doesn't mean adb still has a live session (WiFi-ADB drops
    # silently when the phone sleeps or its IP changes via DHCP).
    devices_code, devices_out = _adb(["devices", "-l"], timeout=5)
    detail = devices_out if devices_out else "(no output from 'adb devices')"

    if "unauthorized" in out or "unauthorized" in devices_out:
        return (
            "Phone shows as 'unauthorized'. Unlock the phone screen and accept "
            f"the USB-debugging prompt, then try again.\nadb devices output:\n{detail}"
        )
    if "offline" in out or "offline" in devices_out:
        return (
            "Phone shows as 'offline' - the WiFi-ADB session died (common after "
            "the phone sleeps or its IP changes). Reconnect with "
            f"'adb connect <phone-ip>:5555'.\nadb devices output:\n{detail}"
        )
    return (
        "No phone reachable over ADB right now. Run "
        "'adb connect <phone-ip>:5555' on the laptop (same WiFi network).\n"
        f"adb devices output:\n{detail}"
    )


@tool
def check_phone_connection() -> str:
    """
    Diagnostic: report exactly what ADB currently sees (connected, offline,
    unauthorized, or nothing). Use this when a phone tool fails and the user
    insists the phone is connected.
    """
    err = _ensure_connected()
    if err is None:
        return "Phone is connected and authorized over ADB."
    return err


@tool
def resolve_contact_number(contact_name: str) -> str:
    """
    Look up a phone number from the contact's name on the user's phone.
    Returns the best-matching contact's number, or a not-found message.
    """
    err = _ensure_connected()
    if err:
        return err

    code, out = _adb([
        "shell", "content", "query",
        "--uri", "content://com.android.contacts/data/phones",
        "--projection", "display_name:data1",
    ])
    if code != 0 or not out:
        return f"Could not read contacts: {out or 'no output'}"

    name_key = contact_name.strip().lower()
    best = None
    for line in out.splitlines():
        m = re.search(r"display_name=(.*?), data1=([+0-9\- ]+)", line)
        if not m:
            continue
        name, number = m.group(1).strip(), m.group(2).strip()
        if name_key == name.lower():
            return f"{name}: {number}"
        if name_key in name.lower() and best is None:
            best = f"{name}: {number}"

    return best or f"No contact matching '{contact_name}' found."


@tool
def call_contact(contact_name: str) -> str:
    """
    Place a phone call to a saved contact by name (e.g. 'mom', 'dad').
    Resolves the contact's number on the phone, then dials it.
    Confirm with the user before calling unless they already gave an explicit instruction to call.
    """
    err = _ensure_connected()
    if err:
        return err

    resolved = resolve_contact_number.invoke({"contact_name": contact_name})
    m = re.search(r":\s*([+0-9\- ]+)$", resolved)
    if not m:
        return resolved  # propagate the "not found" message

    number = m.group(1).strip()
    return call_number.invoke({"number": number})


@tool
def call_number(number: str) -> str:
    """
    Place a phone call to a specific phone number.
    Example: '+15551234567'
    """
    err = _ensure_connected()
    if err:
        return err

    clean = re.sub(r"[^\d+]", "", number)
    if not clean:
        return f"'{number}' doesn't look like a valid phone number."

    code, out = _adb([
        "shell", "am", "start",
        "-a", "android.intent.action.CALL",
        "-d", f"tel:{clean}",
    ])
    if code == 0:
        return f"Calling {clean}."
    return f"Could not place call: {out}"


@tool
def end_call() -> str:
    """Hang up the current call."""
    err = _ensure_connected()
    if err:
        return err
    code, out = _adb(["shell", "input", "keyevent", "KEYCODE_ENDCALL"])
    return "Call ended." if code == 0 else f"Could not end call: {out}"


@tool
def get_phone_last_location() -> str:
    """
    Get the phone's LAST KNOWN location (not a fresh live GPS fix — ADB has no
    direct command for that). Accuracy and freshness depend on when the phone
    last got a fix from GPS/WiFi/cell.
    """
    err = _ensure_connected()
    if err:
        return err

    code, out = _adb(["shell", "dumpsys", "location"], timeout=10)
    if code != 0:
        return f"Could not read location service: {out}"

    matches = re.findall(r"(?:Location\[|last location=)[^\]]*lat[^\n]*", out, re.IGNORECASE)
    if matches:
        return "Last known location info:\n" + "\n".join(matches[:5])
    return (
        "No recent location fix found in dumpsys output. "
        "For reliable live GPS, a small companion app (e.g. Termux:API) "
        "reporting coordinates to JARVIS is more robust than parsing dumpsys."
    )


@tool
def open_app_on_phone(app_name: str) -> str:
    """
    Open an app on the phone by its common name (e.g. 'whatsapp', 'camera', 'maps').
    Requires knowing the Android package name; falls back to a small built-in map.
    """
    err = _ensure_connected()
    if err:
        return err

    PACKAGE_MAP = {
        "whatsapp": "com.whatsapp",
        "camera": "com.android.camera",
        "maps": "com.google.android.apps.maps",
        "gmail": "com.google.android.gm",
        "youtube": "com.google.android.youtube",
        "chrome": "com.android.chrome",
        "settings": "com.android.settings",
        "phone": "com.android.dialer",
        "messages": "com.google.android.apps.messaging",
    }
    key = app_name.strip().lower()
    package = PACKAGE_MAP.get(key)
    if not package:
        return f"Don't have a package mapping for '{app_name}'. Add it to PACKAGE_MAP."

    code, out = _adb([
        "shell", "monkey", "-p", package,
        "-c", "android.intent.category.LAUNCHER", "1",
    ])
    if code == 0:
        return f"Opened {app_name} on the phone."
    return f"Could not open {app_name}: {out}"


@tool
def set_phone_wifi(enabled: bool) -> str:
    """Turn the phone's WiFi on or off."""
    err = _ensure_connected()
    if err:
        return err
    state = "enable" if enabled else "disable"
    code, out = _adb(["shell", "svc", "wifi", state])
    return f"Phone WiFi {'enabled' if enabled else 'disabled'}." if code == 0 else f"Error: {out}"


@tool
def compose_sms(number: str, message: str) -> str:
    """
    Open the SMS compose screen on the phone, prefilled with a number and message.
    Does NOT send automatically — most phones block silent SMS-send over ADB, so
    the user has to tap Send themselves. Tell the user to check their phone.
    """
    err = _ensure_connected()
    if err:
        return err

    clean_number = re.sub(r"[^\d+]", "", number)
    if not clean_number:
        return f"'{number}' doesn't look like a valid phone number."
    if not message.strip():
        return "I need a message to prefill."

    code, out = _adb([
        "shell", "am", "start",
        "-a", "android.intent.action.SENDTO",
        "-d", f"sms:{clean_number}",
        "--es", "sms_body", message,
    ])
    if code == 0:
        return f"Opened SMS to {clean_number} prefilled — tap Send on the phone to confirm."
    return f"Could not open SMS compose: {out}"


@tool
def get_phone_live_location() -> str:
    """
    Get a FRESH GPS fix from the phone (not a stale cached one).
    Requires the Termux + Termux:API companion script to be running on the
    phone (see termux_gps_reporter.sh) — it writes the latest fix to
    /sdcard/jarvis_location.json every ~30s, and this tool pulls that file.
    """
    err = _ensure_connected()
    if err:
        return err

    import json
    import tempfile
    import os as _os

    with tempfile.TemporaryDirectory() as tmp:
        local_path = _os.path.join(tmp, "loc.json")
        code, out = _adb(["pull", "/sdcard/jarvis_location.json", local_path], timeout=10)
        if code != 0 or not _os.path.exists(local_path):
            return (
                "No live location file found on the phone. Make sure the Termux "
                "GPS reporter script is running (see termux_gps_reporter.sh)."
            )
        try:
            with open(local_path) as f:
                data = json.load(f)
            lat = data.get("latitude")
            lon = data.get("longitude")
            ts = data.get("timestamp", "unknown time")
            if lat is None or lon is None:
                return f"Location file found but missing coordinates: {data}"
            return f"Phone location: {lat}, {lon} (captured at {ts})"
        except Exception as e:
            return f"Could not parse location file: {e}"