import ctypes
import os
import re
import subprocess
import sys
import time
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

            if key in WINDOWS_APP_MAP:
                command = WINDOWS_APP_MAP[key]
                os.system(f'start "" {command}')
                return f"Opened {app_name}"

            app_id = _find_app_id(app_name)
            if app_id:
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

WINDOWS_PROCESS_MAP = {
    "notepad": "notepad.exe",
    "calculator": "CalculatorApp.exe",
    "calc": "CalculatorApp.exe",
    "paint": "mspaint.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "firefox": "firefox.exe",
    "word": "winword.exe",
    "microsoft word": "winword.exe",
    "excel": "excel.exe",
    "microsoft excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "spotify": "spotify.exe",
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "visual studio code": "Code.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "whatsapp": "WhatsApp.exe",
}

def _find_running_process(app_name: str) -> str | None:
    """
    Look through currently running processes (via tasklist) for one whose
    name contains app_name. Lets us close apps that aren't in the map above
    without needing the exact .exe name.
    """
    try:
        result = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=10)
        name_key = app_name.strip().lower()
        for line in result.stdout.splitlines():
            parts = line.split()
            if parts and name_key in parts[0].lower():
                return parts[0]
        return None
    except Exception as e:
        logger.warning(f"Process lookup failed for '{app_name}': {e}")
        return None


@tool
def close_app(app_name: str) -> str:
    """Close a running application by name (e.g. 'chrome', 'whatsapp', 'spotify')."""
    try:
        if os.name == "nt":
            key = app_name.strip().lower()
            process_name = WINDOWS_PROCESS_MAP.get(key) or _find_running_process(app_name)

            if not process_name:
                return f"'{app_name}' doesn't seem to be running right now."

            result = subprocess.run(
                ["taskkill", "/f", "/im", process_name],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return f"Closed {app_name}"
            return f"Could not close {app_name}: {result.stderr.strip() or result.stdout.strip()}"
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

def _netsh(args: list[str], timeout: int = 15) -> str:
    """Run a netsh command and return output."""
    try:
        result = subprocess.run(
            ["netsh"] + args,
            capture_output=True, text=True, timeout=timeout
        )
        return (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s"
    except Exception as e:
        return f"Command error: {e}"

def _powershell(script: str, timeout: int = 15) -> str:
    """Run a PowerShell command and return output."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=timeout
        )
        return (result.stdout + result.stderr).strip()
    except Exception as e:
        return f"PowerShell error: {e}"

def _get_wifi_interface() -> str:
    """Get the name of the active WiFi interface (e.g. 'Wi-Fi' or 'WiFi')."""
    out = _netsh(["wlan", "show", "interfaces"])
    for line in out.splitlines():
        if "Name" in line and ":" in line:
            return line.split(":", 1)[1].strip()
    return "Wi-Fi"

@tool
def toggle_wifi(enable):
    """Turn WiFi ON or OFF."""

    if not is_admin():
        return " Admin privileges required"

    interface = _get_wifi_interface()
    if not interface:
        return " Could not find WiFi interface"

    action = "enable" if enable else "disable"
    action_text = "ON" if enable else "OFF"

    print(f"\n[WiFi] Turning {action_text} on interface: {interface}")

    try:
        print("[Method 1] Trying netsh...")
        result = subprocess.run(
            ['netsh', 'interface', 'set', 'interface', interface, action],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(f"[Method 1] Success: {result.stdout}")
            time.sleep(2)

            if verify_wifi_state(enable):
                return f"✅ WiFi turned {action_text} successfully (netsh)"

    except Exception as e:
        print(f"[Method 1] Failed: {e}")

    try:
        print("[Method 2] Trying PowerShell...")
        ps_command = f"Enable-NetAdapter -Name '{interface}' -Confirm:$false" if enable \
            else f"Disable-NetAdapter -Name '{interface}' -Confirm:$false"

        result = subprocess.run(
            ['powershell', '-Command', ps_command],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(f"[Method 2] Success")
            time.sleep(2)
            if verify_wifi_state(enable):
                return f"✅ WiFi turned {action_text} successfully (PowerShell)"

    except Exception as e:
        print(f"[Method 2] Failed: {e}")

    try:
        print("[Method 3] Trying alternative PowerShell...")
        ps_command = f"Get-NetAdapter -Name '{interface}' | {'Enable' if enable else 'Disable'}-NetAdapter -Confirm:$false"

        result = subprocess.run(
            ['powershell', '-Command', ps_command],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(f"[Method 3] Success")
            time.sleep(2)
            if verify_wifi_state(enable):
                return f"✅ WiFi turned {action_text} successfully (PowerShell alt)"
    except Exception as e:
        print(f"[Method 3] Failed: {e}")

    try:
        print("[Method 4] Trying netsh wlan...")
        if enable:
            result = subprocess.run(
                ['netsh', 'wlan', 'connect', 'name=' + get_current_ssid()],
                capture_output=True,
                text=True,
                timeout=10
            )
        else:
            result = subprocess.run(
                ['netsh', 'wlan', 'disconnect'],
                capture_output=True,
                text=True,
                timeout=10
            )

        if result.returncode == 0:
            print(f"[Method 4] Success")
            return f"✅ WiFi turned {action_text} successfully (wlan)"
    except Exception as e:
        print(f"[Method 4] Failed: {e}")

    return f"Failed to turn WiFi {action_text} after trying all methods"


def get_current_ssid():
    """Get current WiFi SSID."""
    try:
        result = subprocess.run(
            ['netsh', 'wlan', 'show', 'interfaces'],
            capture_output=True,
            text=True,
            timeout=5
        )

        for line in result.stdout.split('\n'):
            if 'SSID' in line and 'BSSID' not in line:
                return line.split(':')[1].strip()
    except:
        pass
    return ""

def verify_wifi_state(expected_enabled):
    """Verify WiFi state after toggle."""
    try:
        interface = _get_wifi_interface()
        if not interface:
            return False

        result= subprocess.run(
            ['netsh', 'interface', 'show', 'interface'],
            capture_output=True,
            text=True,
            timeout=5
        )

        for line in result.stdout.split('\n'):
            if interface in line:
                is_enabled = 'Enabled' in line
                return is_enabled == expected_enabled
    except:
        pass

    return False

def is_admin():
    """Check if running as admin."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

@tool
def ensure_admin():
    """Request admin privileges if not already."""
    if is_admin():
        return True

    print("[Admin JD] Requesting administrator privileges...")
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])

    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        sys.exit(0)
    except Exception as e:
        print(f"[Admin] Failed to elevate: {e}")
        return False

@tool
def scan_wifi_networks() -> str:
    """
    Scan and list all available WiFi networks nearby with their
    signal strength, security type, and channel.
    ADMIN ONLY.
    """

    _netsh(["wlan", "scan"])
    time.sleep(2)

    out = _netsh(["wlan", "show", "networks", "mode=bssid"])

    if "There is no wireless interface" in out:
        return "WiFi adapter not found or WiFi is turned off. Turn WiFi on first."

    networks = []
    current = {}

    for line in out.splitlines():
        line = line.strip()
        if line.startswith("SSID") and "BSSID" not in line:
            if current:
                networks.append(current)
            name = line.split(":", 1)[1].strip() if ":" in line else ""
            current = {"ssid": name}
        elif "Authentication" in line:
            current["security"] = line.split(":", 1)[1].strip()
        elif "Signal" in line:
            current["signal"] = line.split(":", 1)[1].strip()
        elif "Radio type" in line:
            current["radio"] = line.split(":", 1)[1].strip()
        elif "Channel" in line:
            current["channel"] = line.split(":", 1)[1].strip()

    if current:
        networks.append(current)

    if not networks:
        return "No WiFi networks found. Make sure WiFi is turned on."

    lines = [f"📶 Found {len(networks)} WiFi network(s):\n"]
    for i, net in enumerate(networks, start=1):
        ssid = net.get("ssid","")
        signal = net.get("signal","?")
        security = net.get("security","?")
        channel = net.get("channel","?")


        try:
            pct = int(signal.replace("%",""))
            bar = "▓▓▓▓" if pct >= 75 else "▓▓▓░" if pct >= 50 else "▓▓░░" if pct >= 25 else "▓░░░"

        except Exception:
            bar = "░░░░"

        lines.append(
            f"  {i:2}. {bar} {signal:>4}  "
            f"{ssid:<30}  "
            f"🔒 {security}  "
            f"Ch:{channel}"
        )

        return "\n".join(lines)


@tool
def connect_wifi(ssid: str, password: str = "") -> str:
    """
    Connect to a WiFi network by its name (SSID).
    If the network was previously connected, password is not needed.
    For new networks, provide the password.
    Example: connect_wifi("MyHomeWifi", "mypassword123")
    ADMIN ONLY.
    """
    if not ssid.strip():
        return "Please provide the network name (SSID)."

    out = _netsh(["wlan", "connect", f"name={ssid}"])

    if "successfully" in out.lower() or "request was completed" in out.lower():
        time.sleep(3)
        return f"Connected to '{ssid}' successfully."

    if password:
        profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""

        profile_path = "C:/Users/MMM JAVID/Desktop/Advance_Voice_Assistant/data/temp_wifi_profile.xml"
        try:
            import os
            os.makedirs("data", exist_ok=True)
            with open(profile_path, "w") as f:
                f.write(profile_xml)

            _netsh(["wlan", "add", "profile", f"filename={profile_path}"])

            out = _netsh(["wlan", "connect", f"name={ssid}"])
            time.sleep(4)

            status = get_wifi_status.invoke({})
            if ssid in status:
                return f"Connected to '{ssid}' successfully."
            return f"Connection attempted. Status:\n{status}"

        except Exception as e:
            return f"Connection error: {e}"
        finally:
            import os
            if os.path.exists(profile_path):
                os.remove(profile_path)

    return (
        f"Could not connect to '{ssid}'. "
        f"If this is a new network, provide the password: "
        f"connect to {ssid} with password yourpassword"
    )


@tool
def disconnect_wifi() -> str:
    """
    Disconnect from the current WiFi network.
    ADMIN ONLY.
    """
    out = _netsh(["wlan", "disconnect"])
    if "successfully" in out.lower() or "completed" in out.lower():
        return "Disconnected from WiFi."
    return f"Disconnect result: {out}"


@tool
def get_wifi_status() -> str:
    """
    Show the current WiFi connection details —
    connected network, IP address, signal strength, speed.
    ADMIN ONLY.
    """
    out = _netsh(["wlan", "show", "interfaces"])

    if "There is no wireless interface" in out:
        return "No WiFi adapter detected."

    fields = {
        "State": None,
        "SSID": None,
        "Signal": None,
        "Receive rate": None,
        "Transmit rate": None,
        "Authentication": None,
        "Channel": None,
    }

    for line in out.splitlines():
        for key in fields:
            if line.strip().startswith(key) and ":" in line:
                fields[key] = line.split(":", 1)[1].strip()

    state = fields.get("State", "unknown")

    if state and "disconnected" in state.lower():
        return "WiFi is ON but not connected to any network."

    if not fields.get("SSID"):
        return "WiFi appears to be OFF or not connected."

    ip_out = subprocess.run(
        ["ipconfig"], capture_output=True, text=True
    ).stdout
    ip_addr = "unknown"
    capture = False
    for line in ip_out.splitlines():
        if "wireless" in line.lower() or "wi-fi" in line.lower():
            capture = True
        if capture and "IPv4" in line:
            ip_addr = line.split(":", 1)[1].strip()
            break

    lines = [
        f"📶 WiFi Status:",
        f"  Network:    {fields.get('SSID', 'unknown')}",
        f"  State:      {state}",
        f"  Signal:     {fields.get('Signal', 'unknown')}",
        f"  Speed ↓:    {fields.get('Receive rate', 'unknown')} Mbps",
        f"  Speed ↑:    {fields.get('Transmit rate', 'unknown')} Mbps",
        f"  Security:   {fields.get('Authentication', 'unknown')}",
        f"  Channel:    {fields.get('Channel', 'unknown')}",
        f"  IP Address: {ip_addr}",
    ]
    return "\n".join(lines)


@tool
def list_saved_wifi_networks() -> str:
    """
    List all WiFi networks saved/remembered on this laptop.
    ADMIN ONLY.
    """
    out = _netsh(["wlan", "show", "profiles"])
    profiles = re.findall(r"All User Profile\s*:\s*(.+)", out)
    if not profiles:
        return "No saved WiFi profiles found."
    lines = [f"Saved WiFi networks ({len(profiles)}):"]
    for i, p in enumerate(profiles, 1):
        lines.append(f"  {i:2}. {p.strip()}")
    return "\n".join(lines)


@tool
def forget_wifi_network(ssid: str) -> str:
    """
    Remove / forget a saved WiFi network profile.
    Example: forget_wifi_network("OldHomeWifi")
    ADMIN ONLY.
    """
    out = _netsh(["wlan", "delete", "profile", f"name={ssid}"])
    if "deleted" in out.lower() or "successfully" in out.lower():
        return f"Forgotten WiFi network '{ssid}'."
    return f"Could not forget '{ssid}': {out}"


@tool
def get_wifi_password(ssid: str) -> str:
    """
    Reveal the saved password for a WiFi network on this laptop.
    Only works for networks this laptop has connected to before.
    ADMIN ONLY.
    """
    out = _netsh(["wlan", "show", "profile", f"name={ssid}", "key=clear"])
    match = re.search(r"Key Content\s*:\s*(.+)", out)
    if match:
        password = match.group(1).strip()
        return f"Password for '{ssid}': {password}"
    if "not found" in out.lower():
        return f"No saved profile found for '{ssid}'."
    return f"Could not retrieve password for '{ssid}'. Make sure the network is saved."
