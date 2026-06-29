import subprocess
from logging import raiseExceptions
import requests as _requests
import requests
from langchain_core.tools import tool

from src.utils.config import WEATHER_API_KEY, TAVILY_API_KEY


@tool
def get_weather(city: str) -> str:
    """Get current weather for a city using OpenWeatherApi"""
    if not WEATHER_API_KEY:
        return "Weather API key not set"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(url).json()
        if response.get("main"):
            temp = response["main"]["temp"]
            desc = response["weather"][0]["description"]
            return f"The weather in {city} is {desc} with a temperature of {temp}°C."
        else:
            return f"Could not fetch weather for {city}. {response.get('message', '')}"
    except Exception as e:
        return f"Error fetching weather: {str(e)}"

@tool
def web_search(query: str) -> str:
    """Search the web for current, up-to-date information - news, current events, who currently holds a position, prices, recent facts, or anything that may have changed since training. Use this instead of guessing whenever the user asks about something time-sensitive or recent."""
    if not TAVILY_API_KEY:
        return "Web search isn't configured (missing TAVILY_API_KEY in .env)."
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": 5,
                "search_depth": "basic"
            },
            timeout=10,
        )
        data = response.json()
        results = data.get("results",[])

        if not results:
            return f"No search results found for '{query}'."
        return "\n".join(
            f"- {r.get('title', '')}: {r.get('content', '')[:300]}"
            for r in results
        )

    except Exception as e:
        return f"Web search error: {str(e)}"

@tool
def get_city(lat: float, lon: float) -> dict:
    """
    Convert geographic coordinates (latitude and longitude) into a human-readable location.

    This tool performs reverse geocoding using the OpenStreetMap Nominatim API.
    It returns the city, town, village, state/province, and country associated
    with the provided coordinates.

    Use this tool whenever you have latitude and longitude coordinates and need
    to determine the corresponding location name.

    Args:
        lat (float): Latitude of the location (e.g., 5.94499537439529).
        lon (float): Longitude of the location (e.g., 80.5529741917055).

    Returns:
        dict: A dictionary containing:
            - city (str | None): City name, if available.
            - town (str | None): Town name, if available.
            - village (str | None): Village name, if available.
            - state (str | None): State or province.
            - country (str | None): Country name.

        If the request fails, returns:
            {"error": "<error message>"}
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json"
    }

    headers = {
        "User-Agent": "AdvanceVoiceAssistant/1.0 (javidmushtan@gmail.com)"
    }

    response = requests.get(url, params=params, headers=headers)

    print("STATUS:", response.status_code)
    print("RAW:", response.text[:300])

    if response.status_code != 200:
        return {"error": "API failed"}

    try:
        data = response.json()
    except Exception:
        return {"error": "Invalid JSON response", "raw": response.text[:200]}

    address = data.get("address", {})

    return {
        "city": address.get("city"),
        "town": address.get("town"),
        "village": address.get("village"),
        "state": address.get("state"),
        "country": address.get("country")
    }

@tool
def get_weather_current_location():
    """
    Get the current weather at the laptop's current location.
    Call this whenever user says 'weather here', 'weather in my location',
    'current location weather', 'what is the weather', 'weather today'.
    This tool detects location AND fetches weather in one step.
    Never call get_current_location separately for weather queries.
    """

    ps = r"""
        Add-Type -AssemblyName System.Device
        $w = New-Object System.Device.Location.GeoCoordinateWatcher
        $w.Start()
        Start-Sleep -Seconds 5
        $c = $w.Position.Location

        if ($c.IsUnknown) {
            Write-Output "UNKNOWN"
        } else {
            Write-Output "$($c.Latitude),$($c.Longitude)"
        }
        """

    result = subprocess.run(
        ["powershell", "-Command", ps],
        capture_output=True, text=True
    )

    out = result.stdout.strip()

    if out == "UNKNOWN":
        return None

    lat, lon = out.split(",")

    data = get_city(float(lat), float(lon))
    print(data.get("city"))
    city = data.get("city")

    if not WEATHER_API_KEY:
        return "WEATHER_API_KEY not set in .env"

    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
        )
        w = _requests.get(url, timeout=8).json()
        main = w.get("main", {})
        if not main:
            return f"Weather API error: {w.get('message', 'unknown')}"

        name = w.get("name", city)
        desc = w["weather"][0]["description"].capitalize()
        temp = main["temp"]
        feels = main["feels_like"]
        humidity = main["humidity"]
        wind = w.get("wind", {}).get("speed", "?")

        return (
            f"Weather in {name}: {desc}. "
            f"Temperature {temp}°C, feels like {feels}°C. "
            f"Humidity {humidity}%, wind {wind} m/s."
        )
    except Exception as e:
        return f"Weather fetch error: {e}"