from logging import raiseExceptions

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