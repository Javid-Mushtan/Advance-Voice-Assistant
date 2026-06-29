"""
WiFi Control - Standalone Working Version
Run this directly to test WiFi toggling
"""

import ctypes
import subprocess
import sys
import os
import time


# ──────────────────────────────────────────────
# ADMIN CHECK
# ──────────────────────────────────────────────

def is_admin():
    """Check if running as admin."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


def ensure_admin():
    """Request admin privileges if not already."""
    if is_admin():
        return True

    print("[Admin] Requesting administrator privileges...")
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


# ──────────────────────────────────────────────
# WIFI INTERFACE DETECTION - IMPROVED
# ──────────────────────────────────────────────

def get_wifi_interface():
    """Find WiFi interface using multiple methods."""

    # Method 1: netsh interface show interface
    try:
        result = subprocess.run(
            ['netsh', 'interface', 'show', 'interface'],
            capture_output=True,
            text=True,
            timeout=5
        )

        print("[DEBUG] Looking for WiFi interface...")
        for line in result.stdout.split('\n'):
            if 'Wi-Fi' in line or 'Wireless' in line or 'WLAN' in line:
                parts = line.split()
                if len(parts) >= 4:
                    interface = parts[-1].strip()
                    print(f"[DEBUG] Found: {interface}")
                    return interface
    except:
        pass

    # Method 2: netsh wlan show interfaces
    try:
        result = subprocess.run(
            ['netsh', 'wlan', 'show', 'interfaces'],
            capture_output=True,
            text=True,
            timeout=5
        )

        for line in result.stdout.split('\n'):
            if 'Name' in line and ':' in line:
                interface = line.split(':')[1].strip()
                print(f"[DEBUG] Found via wlan: {interface}")
                return interface
    except:
        pass

    # Method 3: Common names
    common_names = ['Wi-Fi', 'WLAN', 'WiFi', 'Wireless']
    for name in common_names:
        try:
            result = subprocess.run(
                ['netsh', 'interface', 'show', 'interface', f'name={name}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if 'Enabled' in result.stdout or 'Connected' in result.stdout:
                print(f"[DEBUG] Found via common name: {name}")
                return name
        except:
            continue

    # Method 4: PowerShell
    try:
        ps_command = 'Get-NetAdapter -Physical | Where-Object {$_.Name -match "Wi-Fi|Wireless|WLAN"} | Select-Object -ExpandProperty Name'
        result = subprocess.run(
            ['powershell', '-Command', ps_command],
            capture_output=True,
            text=True,
            timeout=5
        )
        interface = result.stdout.strip()
        if interface:
            print(f"[DEBUG] Found via PowerShell: {interface}")
            return interface
    except:
        pass

    print("[DEBUG] No WiFi interface found!")
    return None


# ──────────────────────────────────────────────
# WIFI TOGGLE - WORKING VERSION
# ──────────────────────────────────────────────

def toggle_wifi(enable):
    """Turn WiFi ON or OFF."""

    if not is_admin():
        return "❌ Admin privileges required"

    interface = get_wifi_interface()
    if not interface:
        return "❌ Could not find WiFi interface"

    action = "enable" if enable else "disable"
    action_text = "ON" if enable else "OFF"

    print(f"\n[WiFi] Turning {action_text} on interface: {interface}")

    # Try multiple methods

    # Method 1: netsh
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
            # Verify
            if verify_wifi_state(enable):
                return f"✅ WiFi turned {action_text} successfully (netsh)"
    except Exception as e:
        print(f"[Method 1] Failed: {e}")

    # Method 2: PowerShell
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

    # Method 3: Alternative PowerShell
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

    # Method 4: netsh wlan (if available)
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

    return f"❌ Failed to turn WiFi {action_text} after trying all methods"


def verify_wifi_state(expected_enabled):
    """Verify WiFi state after toggle."""
    try:
        interface = get_wifi_interface()
        if not interface:
            return False

        result = subprocess.run(
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


def get_wifi_status():
    """Get current WiFi status."""
    try:
        interface = get_wifi_interface()
        if not interface:
            return {'enabled': False, 'error': 'No interface'}

        result = subprocess.run(
            ['netsh', 'interface', 'show', 'interface'],
            capture_output=True,
            text=True,
            timeout=5
        )

        for line in result.stdout.split('\n'):
            if interface in line:
                enabled = 'Enabled' in line
                connected = 'Connected' in line
                return {
                    'enabled': enabled,
                    'connected': connected,
                    'interface': interface,
                    'status': 'Connected' if connected else 'Disconnected' if enabled else 'Disabled'
                }

        return {'enabled': False, 'interface': interface}
    except Exception as e:
        return {'enabled': False, 'error': str(e)}


# ──────────────────────────────────────────────
# MAIN TEST
# ──────────────────────────────────────────────

def main():
    """Test WiFi toggling."""
    print("\n" + "="*60)
    print("WIFI CONTROL TEST (STANDALONE)")
    print("="*60)

    # Check admin
    if not is_admin():
        print("\n⚠️ Not running as administrator!")
        print("Restarting with admin privileges...\n")
        ensure_admin()
        return

    print("\n✅ Running with administrator privileges.")

    # Get interface
    print("\n📡 Detecting WiFi Interface...")
    interface = get_wifi_interface()
    if interface:
        print(f"   ✅ Found: {interface}")
    else:
        print("   ❌ No WiFi interface found!")
        return

    # Current status
    print("\n📊 Current Status:")
    status = get_wifi_status()
    print(f"   Enabled: {status.get('enabled', False)}")
    print(f"   Connected: {status.get('connected', False)}")

    # Test toggling
    print("\n🔄 Testing WiFi toggle...")
    print("-" * 50)

    # Turn OFF
    print("\n1️⃣ Turning WiFi OFF...")
    result = toggle_wifi(False)
    print(f"   Result: {result}")
    time.sleep(2)

    # Status after OFF
    status = get_wifi_status()
    print(f"\n   Status after OFF:")
    print(f"   Enabled: {status.get('enabled', False)}")

    # Turn ON
    print("\n2️⃣ Turning WiFi ON...")
    result = toggle_wifi(True)
    print(f"   Result: {result}")
    time.sleep(2)

    # Status after ON
    status = get_wifi_status()
    print(f"\n   Status after ON:")
    print(f"   Enabled: {status.get('enabled', False)}")
    print(f"   Connected: {status.get('connected', False)}")

    # Turn OFF again
    print("\n3️⃣ Turning WiFi OFF again...")
    result = toggle_wifi(False)
    print(f"   Result: {result}")
    time.sleep(2)

    print("\n" + "="*60)
    print("✅ Test complete!")
    print("="*60)


if __name__ == "__main__":
    main()