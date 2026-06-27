"""
test_adb.py — run this directly: python test_adb.py

Isolates whether ADB problems are:
  (a) the WiFi-ADB link actually dropped (phone slept, IP changed), or
  (b) this Python process just can't see/find `adb` the way your terminal can
      (different PATH, different adb server instance, etc.)

Run it RIGHT AFTER you confirm `adb devices` works in your normal terminal,
without doing anything else in between.
"""
import shutil
import subprocess
import sys


def main():
    print("=" * 60)
    print("1. Can Python find adb on PATH?")
    print("=" * 60)
    adb_path = shutil.which("adb")
    print(f"shutil.which('adb') -> {adb_path}")
    if not adb_path:
        print(
            "\n!! Python's subprocess can't see adb at all. This is a PATH issue\n"
            "   specific to whatever environment JARVIS runs in (venv, IDE run\n"
            "   config, scheduled task, etc.) — not the same PATH your terminal uses.\n"
            "   Fix: hardcode the full path to adb.exe in phone_tools.py's _adb()\n"
            "   function, e.g. cmd = [r'C:\\path\\to\\platform-tools\\adb.exe']"
        )
        sys.exit(1)

    print("\n" + "=" * 60)
    print("2. What does this Python process's adb see right now?")
    print("=" * 60)
    result = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=10)
    print("stdout:", result.stdout.strip() or "(empty)")
    print("stderr:", result.stderr.strip() or "(empty)")

    print("\n" + "=" * 60)
    print("3. adb get-state (what the real tool checks)")
    print("=" * 60)
    result2 = subprocess.run(["adb", "get-state"], capture_output=True, text=True, timeout=5)
    print("returncode:", result2.returncode)
    print("stdout:", result2.stdout.strip() or "(empty)")
    print("stderr:", result2.stderr.strip() or "(empty)")

    print("\n" + "=" * 60)
    if "device" in result.stdout and result2.returncode == 0:
        print("RESULT: Python sees the phone fine. The earlier failure was almost")
        print("certainly the WiFi-ADB link dropping between when you connected and")
        print("when JARVIS tried to use it (commonly: phone screen went to sleep).")
        print("Try keeping the phone screen on/unlocked while testing JARVIS.")
    else:
        print("RESULT: Python's adb genuinely sees no device RIGHT NOW, matching")
        print("what JARVIS reported. Run 'adb connect <phone-ip>:5555' again,")
        print("immediately before re-running this script, with the phone awake.")
    print("=" * 60)
if __name__ == "__main__":
    main()