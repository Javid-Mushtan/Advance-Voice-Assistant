import os
import subprocess
import shutil
from pathlib import Path
from langchain_core.tools import tool
from src.utils.logger import logger

@tool
def scan_files(pattern: str, search_path: str = "C:\\") -> str:
    """
    Scan the file system and find files matching a name or pattern.
    Examples: 'test.csv', '*.log', 'report_2024*'
    search_path defaults to C:\\ but the user can specify e.g. 'C:\\Users\\Javid\\Documents'
    """
    try:
        results = []
        search_root = Path(search_path)
        for match in search_root.rglob(pattern):
            results.append(str(match))
            if len(results) >= 30:   # cap at 30 so the reply isn't enormous
                results.append("... (more results truncated, narrow your search)")
                break
        if not results:
            return f"No files matching '{pattern}' found under {search_path}."
        return f"Found {len(results)} result(s):\n" + "\n".join(results)
    except PermissionError as e:
        return f"Permission denied scanning {search_path}: {e}"
    except Exception as e:
        return f"Scan error: {e}"

@tool
def delete_file(file_path: str) -> str:
    """
        Permanently delete a file or empty folder at the given path.
        ADMIN ONLY. Use with caution — this cannot be undone.
    """
    try:
        p = Path(file_path)
        if not p.exists():
            return f"'{file_path}' does not exist."
        if p.is_file():
            p.unlink()
            return f"Deleted file: {file_path}"
        elif p.is_dir() and not any(p.iterdir()):
            p.rmdir()
            return f"Deleted empty folder: {file_path}"
        else:
            return (
                f"'{file_path}' is a non-empty directory. "
                "Ask the user to confirm before deleting a folder with contents."
            )
    except PermissionError:
        return f"Permission denied deleting '{file_path}'. Try running as administrator."
    except Exception as e:
        return f"Delete error: {e}"

@tool
def move_file(source_path: str, destination_path: str) -> str:
    """
    Move or rename a file or folder.
    ADMIN ONLY.
    """
    try:
        shutil.move(source_path, destination_path)
        return f"Moved {source_path} to {destination_path}"
    except Exception as e:
        return f"Move error: {e}"


@tool
def read_file_contents(file_path: str) -> str:
    """
    Read and return the text contents of a file (first 200 lines).
    Useful for inspecting log files, config files, CSVs, etc.
    ADMIN ONLY.
    """
    try:
        p = Path(file_path)
        if not p.exists():
            return f"File not found: {file_path}"
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        preview = "".join(lines[:200])
        note = "" if len(lines) <= 200 else f"\n... ({len(lines) - 200} more lines not shown)"
        return preview + note
    except Exception as e:
        return f"Read error: {e}"


@tool
def list_directory(folder_path: str) -> str:
    """
    List all files and subfolders inside a directory.
    ADMIN ONLY.
    """
    try:
        p = Path(folder_path)
        if not p.exists():
            return f"Path not found: {folder_path}"
        entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        lines = []
        for entry in entries:
            tag = "[FILE]" if entry.is_file() else "[DIR] "
            lines.append(f"{tag}  {entry.name}")
        if not lines:
            return f"'{folder_path}' is empty."
        return f"Contents of {folder_path}:\n" + "\n".join(lines)
    except PermissionError:
        return f"Permission denied accessing '{folder_path}'."
    except Exception as e:
        return f"List error: {e}"


@tool
def uninstall_application(app_name: str) -> str:
    """
    Uninstall an application by name using Windows Package Manager (winget).
    Example: 'AnyDesk', 'VLC', 'Zoom'
    ADMIN ONLY.
    """
    try:
        result = subprocess.run(
            ["winget", "uninstall", "--name", app_name, "--silent", "--accept-source-agreements"],
            capture_output=True, text=True, timeout=120
        )
        output = result.stdout + result.stderr
        if result.returncode == 0:
            return f"Successfully uninstalled '{app_name}'."
        return f"Uninstall output:\n{output.strip()}"
    except FileNotFoundError:
        return "winget is not available. Please ensure Windows Package Manager is installed."
    except subprocess.TimeoutExpired:
        return f"Uninstall of '{app_name}' timed out. It may still be running in the background."
    except Exception as e:
        return f"Uninstall error: {e}"


@tool
def install_application(app_name: str) -> str:
    """
    Install an application by name using winget.
    Example: 'VLC', 'Git', '7-Zip'
    ADMIN ONLY.
    """
    try:
        result = subprocess.run(
            ["winget", "install", "--name", app_name, "--silent", "--accept-package-agreements",
             "--accept-source-agreements"],
            capture_output=True, text=True, timeout=300
        )
        output = result.stdout + result.stderr
        if result.returncode == 0:
            return f"Successfully installed '{app_name}'."
        return f"Install output:\n{output.strip()}"
    except FileNotFoundError:
        return "winget is not available."
    except subprocess.TimeoutExpired:
        return f"Install of '{app_name}' timed out. It may still be downloading."
    except Exception as e:
        return f"Install error: {e}"


@tool
def list_installed_apps() -> str:
    """
    List all installed applications on the system using winget.
    ADMIN ONLY.
    """
    try:
        result = subprocess.run(
            ["winget", "list"],
            capture_output=True, text=True, timeout=30
        )
        lines = result.stdout.strip().splitlines()
        if len(lines) > 60:
            lines = lines[:60]
            lines.append("... (truncated, showing first 60 apps)")
        return "\n".join(lines) if lines else "No apps found."
    except Exception as e:
        return f"Error listing apps: {e}"


@tool
def list_running_processes() -> str:
    """
    List all currently running processes with their PID and CPU/memory usage.
    ADMIN ONLY.
    """
    try:
        result = subprocess.run(
            ["tasklist", "/fo", "csv", "/nh"],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().splitlines()[:40]
        processes = []
        for line in lines:
            parts = line.strip('"').split('","')
            if len(parts) >= 5:
                processes.append(f"{parts[0]:<35} PID: {parts[1]:<8} Mem: {parts[4]}")
        return "\n".join(processes) if processes else "No processes found."
    except Exception as e:
        return f"Process list error: {e}"


@tool
def kill_process(process_name_or_pid: str) -> str:
    """
    Force-terminate a running process by name or PID.
    Example: 'chrome.exe' or '1234'
    ADMIN ONLY.
    """
    try:
        if process_name_or_pid.isdigit():
            result = subprocess.run(
                ["taskkill", "/f", "/pid", process_name_or_pid],
                capture_output=True, text=True
            )
        else:
            result = subprocess.run(
                ["taskkill", "/f", "/im", process_name_or_pid],
                capture_output=True, text=True
            )
        output = (result.stdout + result.stderr).strip()
        return output if output else f"Kill command sent for '{process_name_or_pid}'."
    except Exception as e:
        return f"Kill error: {e}"


@tool
def run_command(command: str) -> str:
    """
    Run any shell command on the system and return its output.
    ADMIN ONLY. Use this for advanced tasks not covered by other tools.
    Example: 'ipconfig /all', 'sfc /scannow', 'chkdsk C: /f'
    """
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=60
        )
        output = (result.stdout + result.stderr).strip()
        return output if output else f"Command executed with return code {result.returncode}."
    except subprocess.TimeoutExpired:
        return f"Command timed out after 60 seconds: {command}"
    except Exception as e:
        return f"Command error: {e}"


@tool
def get_network_info() -> str:
    """
    Show all network adapter details — IP addresses, DNS, gateway.
    ADMIN ONLY.
    """
    try:
        result = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, timeout=10)
        return result.stdout.strip()[:3000]
    except Exception as e:
        return f"Network info error: {e}"


@tool
def list_open_ports() -> str:
    """
    Show all currently open/listening network ports and which process owns them.
    ADMIN ONLY.
    """
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=15
        )
        lines = [l for l in result.stdout.splitlines() if "LISTENING" in l or "ESTABLISHED" in l]
        return "\n".join(lines[:40]) if lines else "No active connections found."
    except Exception as e:
        return f"Port list error: {e}"


@tool
def ping_host(host: str) -> str:
    """
    Ping a hostname or IP address to check connectivity.
    Example: 'google.com', '192.168.1.1'
    ADMIN ONLY.
    """
    try:
        result = subprocess.run(
            ["ping", "-n", "4", host],
            capture_output=True, text=True, timeout=20
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Ping error: {e}"


@tool
def get_disk_usage() -> str:
    """
    Show disk usage for all drives on the system.
    ADMIN ONLY.
    """
    try:
        import shutil as _shutil
        import string
        lines = []
        for drive in string.ascii_uppercase:
            path = f"{drive}:\\"
            if os.path.exists(path):
                total, used, free = _shutil.disk_usage(path)
                gb = 1024 ** 3
                lines.append(
                    f"{path}  Total: {total / gb:.1f} GB  "
                    f"Used: {used / gb:.1f} GB  Free: {free / gb:.1f} GB"
                )
        return "\n".join(lines) if lines else "No drives found."
    except Exception as e:
        return f"Disk usage error: {e}"


@tool
def get_system_info() -> str:
    """
    Return detailed system information: OS, CPU, RAM, uptime.
    ADMIN ONLY.
    """
    try:
        result = subprocess.run(["systeminfo"], capture_output=True, text=True, timeout=30)
        # Only return the most useful lines to keep it concise
        useful = [
            "Host Name", "OS Name", "OS Version", "System Type",
            "Total Physical Memory", "Available Physical Memory",
            "System Boot Time"
        ]
        lines = []
        for line in result.stdout.splitlines():
            if any(line.startswith(k) for k in useful):
                lines.append(line.strip())
        return "\n".join(lines) if lines else result.stdout[:1500]
    except Exception as e:
        return f"System info error: {e}"


@tool
def shutdown_pc(delay_seconds: int = 30) -> str:
    """
    Schedule a system shutdown after a delay (default 30 seconds).
    Use delay_seconds=0 for immediate shutdown.
    ADMIN ONLY.
    """
    try:
        subprocess.run(["shutdown", "/s", "/t", str(delay_seconds)], check=True)
        if delay_seconds == 0:
            return "Shutting down immediately."
        return f"PC will shut down in {delay_seconds} seconds. Say 'cancel shutdown' to abort."
    except Exception as e:
        return f"Shutdown error: {e}"


@tool
def cancel_shutdown() -> str:
    """
    Cancel a scheduled shutdown.
    ADMIN ONLY.
    """
    try:
        subprocess.run(["shutdown", "/a"], check=True)
        return "Shutdown has been cancelled."
    except Exception as e:
        return f"Cancel shutdown error: {e}"


@tool
def restart_pc(delay_seconds: int = 30) -> str:
    """
    Restart the computer after a delay (default 30 seconds).
    ADMIN ONLY.
    """
    try:
        subprocess.run(["shutdown", "/r", "/t", str(delay_seconds)], check=True)
        return f"PC will restart in {delay_seconds} seconds."
    except Exception as e:
        return f"Restart error: {e}"


@tool
def set_volume(level: int) -> str:
    """
    Set the system volume to a level from 0 to 100.
    ADMIN ONLY.
    """
    if not (0 <= level <= 100):
        return "Volume level must be between 0 and 100."
    try:
        ps_script = f"""
        $obj = New-Object -ComObject WScript.Shell
        $vol = {level}
        Add-Type -TypeDefinition @'
        using System.Runtime.InteropServices;
        [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        interface IAudioEndpointVolume {{ int f(); int g(); int h(); int i();
            int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
        }}
        [Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        interface IMMDevice {{ int Activate(ref System.Guid id, int clsCtx, int activationParams, out IAudioEndpointVolume aev); }}
        [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        interface IMMDeviceEnumerator {{ int f(); int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint); }}
        [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorClass {{}}
        '@
        """
        # Simpler approach via nircmd if available
        result = subprocess.run(
            ["nircmd", "setsysvolume", str(int(level * 655.35))],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return f"Volume set to {level}%."
        # Fallback: PowerShell approach
        ps = f"(New-Object -ComObject WScript.Shell).SendKeys([char]173)" if level == 0 else ""
        return f"Volume set attempt to {level}% (nircmd method)."
    except Exception as e:
        return f"Volume error: {e}. Try installing nircmd for volume control."
