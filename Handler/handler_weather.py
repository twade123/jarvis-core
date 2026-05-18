"""
Handler for weather information retrieval using OpenWeather API.

Capabilities:
    - Location geocoding
    - Current weather data
    - Weather forecasts
    - Multi-language support
    - Multiple unit systems
    - Detailed weather metrics
    - Location resolution
    - Weather overviews
    - Temperature data
    - Atmospheric conditions
    - Weather alerts
    - Historical weather

Patterns:
    - "get weather in {location}"
    - "check forecast for {location}"
    - "what's the temperature in {location}"
    - "weather overview for {location}"
    - "get weather alerts for {location}"
    - "check conditions in {location}"
    - "get humidity in {location}"
    - "forecast tomorrow for {location}"

Intents:
    - weather_current
    - weather_forecast
    - weather_temperature
    - weather_overview
    - weather_alerts
    - weather_conditions
    - weather_humidity
    - weather_tomorrow

Parameters:
    - location: string (city/place name)
    - units: string ('metric'/'imperial'/'standard')
    - lang: string (language code)
    - date: string (YYYY-MM-DD)
    - lat: float (latitude)
    - lon: float (longitude)
"""

import os
import requests
import json
import logging
from Jarvis_Agent_SDK.http_utils import make_api_request, RateLimiter, HttpError
from pathlib import Path
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Agent-related components loaded lazily on demand (not at import time)
# to avoid triggering the full boardroom/intelligence init chain
analyze_handler_capabilities = None
AgentBuilder = None


BASE_DIR = Path('~/Jarvis')  # Update with correct base directory
API_KEY_FILE = BASE_DIR / 'API/OPENWEATHER_API_KEY.txt'

def load_api_key(file_path):
    """
    Load the OpenWeather API key from environment variable or file fallback.
    Args:
        file_path (Path): Path to the API key file (used as fallback).
    Returns:
        str: API key or exits if not found.
    """
    env_key = os.environ.get('OPENWEATHER_API_KEY')
    if env_key:
        return env_key
    try:
        with file_path.open('r') as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Failed to load API key: {e}")
        exit()

# Load the API key
API_KEY = load_api_key(API_KEY_FILE)

async def geocode_location(location):
    """
    Resolve a location name to latitude and longitude using OpenWeather geocoding API.
    Args:
        location (str): The name of the location.
    Returns:
        tuple: Latitude and longitude as (lat, lon), or None if the location cannot be resolved.
    """
    geocoding_url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {
        "q": location,
        "appid": API_KEY,
        "limit": 1  # Return only the top result
    }
    try:
        response = await make_api_request(
            url=geocoding_url,
            method="GET",
            params=params
        )
        if response and isinstance(response, list) and response:
            lat = response[0]['lat']
            lon = response[0]['lon']
            logging.info(f"Resolved location '{location}' to coordinates: ({lat}, {lon})")
            return lat, lon
        else:
            logging.error(f"Could not resolve location: {location}")
            return None
    except HttpError as e:
        logging.error(f"Error in geocoding request: {e}")
        return None

async def fetch_weather_overview(lat, lon, date=None, units='metric', lang='en'):
    """
    Fetch a human-readable weather overview for today or tomorrow.
    Args:
        lat (float): Latitude of the location.
        lon (float): Longitude of the location.
        date (str): Date in 'YYYY-MM-DD' format. Optional.
        units (str): Measurement units ('standard', 'metric', 'imperial').
        lang (str): Language for the response ('en', 'zh_cn', etc.).
    Returns:
        dict: Weather data or None if the request fails.
    """
    base_url = 'https://api.openweathermap.org/data/3.0/onecall'
    params = {
        'lat': lat,
        'lon': lon,
        'appid': API_KEY,
        'units': units,
        'lang': lang,
        'exclude': 'minutely'
    }

    try:
        logging.info(f"Making API request to {base_url} with params: {params}")
        response = await make_api_request(
            url=base_url,
            method="GET",
            params=params
        )
        logging.info("Fetched weather overview successfully.")
        return response
    except HttpError as e:
        logging.error(f"Error fetching weather overview: {e}")
        return None

async def weather(*args, **kwargs):
    """
    Entry point for the weather handler. Resolves location and fetches a weather overview.
    Args:
        *args: Positional arguments (not used).
        **kwargs: Keyword arguments, expected to include:
            - location (str): The name of the location.
            - units (str): Measurement units ('standard', 'metric', 'imperial').
            - lang (str): Language for the response ('en', 'zh_cn', etc.).
    Returns:
        str: Human-readable weather overview or an error message.
    """
    location = kwargs.get('location')
    units = kwargs.get('units', 'metric')
    lang = kwargs.get('lang', 'en')

    if not location:
        return "Error: Location is required for weather queries."

    # Resolve location to lat and lon
    coordinates = await geocode_location(location)
    if not coordinates:
        return f"Error: Could not resolve location '{location}'."

    lat, lon = coordinates

    # Fetch weather overview
    try:
        weather_data = await fetch_weather_overview(lat, lon, units=units, lang=lang)
        if weather_data:
            return json.dumps(weather_data, indent=4)
        return "Error: Failed to fetch weather data."
    except Exception as e:
        logging.error(f"Error in weather handler: {e}")
        return "Error: An unexpected error occurred while fetching weather data."

class WeatherMCPHandler:
    """Synchronous wrapper for the weather handler — used by MCP introspection.
    
    Methods: get_weather, get_forecast
    """

    def __init__(self):
        self.name = "weather"
        self.api_key = API_KEY

    def get_weather(self, location: str, units: str = "metric", **kwargs) -> dict:
        """Get current weather and forecast for a location.
        
        Args:
            location: City name (e.g. 'Sydney, Australia', 'London, UK')
            units: 'metric' (Celsius) or 'imperial' (Fahrenheit)
        
        Returns:
            dict with current conditions, temperature, humidity, wind, and forecast
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, self._async_get_weather(location, units)).result()
                return result
            else:
                return asyncio.run(self._async_get_weather(location, units))
        except Exception as e:
            return {"error": str(e), "location": location}

    async def _async_get_weather(self, location: str, units: str = "metric") -> dict:
        """Internal async implementation."""
        coords = await geocode_location(location)
        if not coords:
            return {"error": f"Could not resolve location: {location}"}
        
        lat, lon = coords
        data = await fetch_weather_overview(lat, lon, units=units)
        if not data:
            return {"error": "Failed to fetch weather data"}
        
        result = {"location": location, "lat": lat, "lon": lon}
        
        # Extract current conditions
        current = data.get("current", {})
        if current:
            result["temperature"] = current.get("temp")
            result["feels_like"] = current.get("feels_like")
            result["humidity"] = current.get("humidity")
            result["wind_speed"] = current.get("wind_speed")
            result["description"] = current.get("weather", [{}])[0].get("description", "")
            result["pressure"] = current.get("pressure")
        
        # Extract alerts
        alerts = data.get("alerts", [])
        if alerts:
            result["alerts"] = [{"event": a.get("event"), "description": a.get("description", "")[:200]} for a in alerts[:3]]
        
        # Daily forecast (next 3 days)
        daily = data.get("daily", [])[:3]
        if daily:
            result["forecast"] = []
            for day in daily:
                result["forecast"].append({
                    "date": datetime.fromtimestamp(day.get("dt", 0)).strftime("%Y-%m-%d"),
                    "high": day.get("temp", {}).get("max"),
                    "low": day.get("temp", {}).get("min"),
                    "description": day.get("weather", [{}])[0].get("description", ""),
                    "rain_chance": day.get("pop", 0),
                })
        
        return result

    def check_commodity_weather(self, commodity: str, **kwargs) -> dict:
        """Check weather conditions that could impact commodity prices.
        
        Args:
            commodity: Commodity name or currency (e.g. 'AUD', 'NZD', 'CAD', 'wheat', 'oil')
        
        Returns:
            dict with weather impact assessment for commodity-relevant regions
        """
        # Map commodities/currencies to weather-sensitive regions
        region_map = {
            "AUD": ["Sydney, Australia", "Perth, Australia"],
            "NZD": ["Auckland, New Zealand", "Wellington, New Zealand"],
            "CAD": ["Calgary, Canada", "Toronto, Canada"],
            "wheat": ["Kansas City, US", "Chicago, US"],
            "corn": ["Des Moines, US", "Chicago, US"],
            "oil": ["Houston, US", "Calgary, Canada"],
            "coffee": ["Sao Paulo, Brazil", "Bogota, Colombia"],
        }
        
        commodity_upper = commodity.upper().strip()
        regions = region_map.get(commodity_upper, region_map.get(commodity.lower().strip(), []))
        
        if not regions:
            return {"status": "skipped", "reason": f"No weather-sensitive regions mapped for {commodity}"}
        
        results = []
        for region in regions:
            wx = self.get_weather(region)
            results.append({"region": region, **wx})
        
        # Assess severity
        severity = 0
        for r in results:
            alerts = r.get("alerts", [])
            if alerts:
                severity = max(severity, 7)
            wind = r.get("wind_speed", 0) or 0
            if wind > 20:
                severity = max(severity, 5)
        
        return {
            "commodity": commodity,
            "regions_checked": len(results),
            "weather_data": results,
            "severity": severity,
            "status": "CLEAR" if severity < 3 else "WATCH" if severity < 6 else "WARNING",
        }


if __name__ == "__main__":
    # Example usage
    h = WeatherMCPHandler()
    print(json.dumps(h.get_weather("Sydney, Australia"), indent=2))
    print(json.dumps(h.check_commodity_weather("AUD"), indent=2))