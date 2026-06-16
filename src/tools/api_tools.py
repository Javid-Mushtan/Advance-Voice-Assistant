from logging import raiseExceptions

import requests
from langchain_core.tools import tool

from src.utils.config import WEATHER_API_KEY


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