import requests
import subprocess
from langchain_core.tools import tool
from src.utils.logger import logger


def _get_location_windows_api() -> dict | None:
    """
    Try Windows Location API via PowerShell.
    Works if the laptop has a GPS chip or Windows Location Services is on.
    Returns dict with lat, lon, accuracy or None if unavailable.
    """
    ps_script = """
    Add-Type -AssemblyName System.Device
    try {
        $watcher = New-Object System.Device.Location.GeoCoordinateWatcher
        $watcher.Start()
        $timeout = 0
        while ($watcher.Status -ne 'Ready' -and $timeout -lt 30) {
            Start-Sleep -Milliseconds 200
            $timeout++
        }
        $coord = $watcher.Position.Location
        if ($coord.IsUnknown) {
            Write-Output "UNKNOWN"
        } else {
            Write-Output "$($coord.Latitude),$($coord.Longitude),$($coord.HorizontalAccuracy)"
        }
        $watcher.Stop()
    } catch {
        Write-Output "UNAVAILABLE"
    }
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=10
        )
        out = result.stdout.strip()
        if out and out not in ("UNKNOWN", "UNAVAILABLE") and "," in out:
            parts = out.split(",")
            return {
                "lat":      float(parts[0]),
                "lon":      float(parts[1]),
                "accuracy": float(parts[2]) if len(parts) > 2 else None,
                "source":   "Windows Location API (GPS)",
            }
    except Exception as e:
        logger.debug(f"Windows Location API failed: {e}")
    return None


def _get_location_ip() -> dict | None:
    """
    Get location from IP geolocation (city-level, ~1–5 km accuracy).
    Uses ip-api.com — free, no API key needed.
    """
    try:
        r = requests.get("http://ip-api.com/json/", timeout=5)
        data = r.json()
        if data.get("status") == "success":
            return {
                "lat":      data.get("lat"),
                "lon":      data.get("lon"),
                "city":     data.get("city"),
                "region":   data.get("regionName"),
                "country":  data.get("country"),
                "isp":      data.get("isp"),
                "timezone": data.get("timezone"),
                "ip":       data.get("query"),
                "accuracy": "~1–5 km (IP based)",
                "source":   "IP geolocation (ip-api.com)",
            }
    except Exception as e:
        logger.debug(f"ip-api.com failed: {e}")

    try:
        r = requests.get("https://ipinfo.io/json", timeout=5)
        data = r.json()
        loc = data.get("loc", "").split(",")
        if len(loc) == 2:
            return {
                "lat":      float(loc[0]),
                "lon":      float(loc[1]),
                "city":     data.get("city"),
                "region":   data.get("region"),
                "country":  data.get("country"),
                "ip":       data.get("ip"),
                "accuracy": "~1–5 km (IP based)",
                "source":   "IP geolocation (ipinfo.io)",
            }
    except Exception as e:
        logger.debug(f"ipinfo.io failed: {e}")

    return None


def _build_maps_link(lat: float, lon: float) -> str:
    return f"https://maps.google.com/?q={lat},{lon}"

@tool
def get_current_location() -> str:
    """
    Get the current location of the laptop.
    Tries Windows GPS first, falls back to IP geolocation.
    Returns city, region, country, coordinates, and a Google Maps link.
    """
    loc = _get_location_windows_api()

    if not loc:
        loc = _get_location_ip()

    if not loc:
        return (
            "Could not determine location. "
            "Check your internet connection or enable Windows Location Services: "
            "Settings → Privacy → Location → turn on."
        )

    lat = loc.get("lat")
    lon = loc.get("lon")
    lines = [f" Current laptop location ({loc['source']}):"]

    if loc.get("city"):
        lines.append(f"  City:     {loc['city']}")
    if loc.get("region"):
        lines.append(f"  Region:   {loc['region']}")
    if loc.get("country"):
        lines.append(f"  Country:  {loc['country']}")
    if lat and lon:
        lines.append(f"  Coords:   {lat}, {lon}")
        lines.append(f"  Maps:     {_build_maps_link(lat, lon)}")
    if loc.get("accuracy"):
        lines.append(f"  Accuracy: {loc['accuracy']}")
    if loc.get("timezone"):
        lines.append(f"  Timezone: {loc['timezone']}")
    if loc.get("isp"):
        lines.append(f"  ISP:      {loc['isp']}")

    return "\n".join(lines)


@tool
def get_location_coordinates() -> str:
    """
    Get just the raw latitude and longitude of the laptop.
    Useful when you need coordinates for another tool (e.g. weather by coords).
    """
    loc = _get_location_windows_api() or _get_location_ip()
    if not loc or not loc.get("lat"):
        return "Coordinates unavailable."
    return f"{loc['lat']},{loc['lon']}"


@tool
def get_maps_link() -> str:
    """
    Get a Google Maps link for the laptop's current location.
    """
    loc = _get_location_windows_api() or _get_location_ip()
    if not loc or not loc.get("lat"):
        return "Location unavailable — cannot generate map link."
    link = _build_maps_link(loc["lat"], loc["lon"])
    city = loc.get("city", "")
    return f"Your location on Google Maps ({city}):\n{link}"