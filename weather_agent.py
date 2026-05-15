"""Weather agent with temperature conversion.

A tool-using Claude agent with two capabilities:
- get_weather: fetch current weather for a city via Open-Meteo
- convert_temperature: convert between Celsius and Fahrenheit
"""

import json
import httpx

import anthropic
from anthropic import beta_tool

client = anthropic.Anthropic(max_retries=3)

#translate all codes received from API into human-readible definitions (so that LLM response is faster and more accurate)
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Drizzle: light",
    53: "Drizzle: moderate",
    55: "Drizzle: dense",
    56: "Freezing drizzle: light",
    57: "Freezing drizzle: dense",
    61: "Rain: slight",
    63: "Rain: moderate",
    65: "Rain: heavy",
    66: "Freezing rain: light",
    67: "Freezing rain: heavy",
    71: "Snowfall: slight",
    73: "Snowfall: moderate",
    75: "Snowfall: heavy",
    77: "Snow grains",
    80: "Rain showers: slight",
    81: "Rain showers: moderate",
    82: "Rain showers: violent",
    85: "Snow showers: slight",
    86: "Snow showers: heavy",
    95: "Thunderstorm: slight or moderate",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

#get latitude/longitude coordinates for any given city (required for later weather lookup)
def geocode_city(city: str) -> dict:
    """Convert a city name to latitude/longitude using Open-Meteo's geocoding API.
    Args: 
        city: City name to look up.
    Returns: 
        A dict with 'latitude' and 'longitude' as floats.
    Raises: 
        ValueError: If the city is not found.
    """
    #call the Open-Meteo API with a city's name
    response = httpx.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name":city, "count":1},
        timeout=5
    )
    #record API response to "data" Python dict
    response.raise_for_status()
    data = response.json()
        
    #handle a misspelled or made-up city name
    if "results" not in data or not data["results"]:
        raise ValueError(f"City not found: {city!r}")

    #extract coordinates for the top-matching city
    top_match = data["results"][0]
    return {
        "latitude": top_match["latitude"],
        "longitude": top_match["longitude"],
    }


#decorate function so it can be made available to Claude as a tool
@beta_tool
def get_weather(city: str) -> str:
    """Get current weather for a city using Open-Meteo.
    Args:
        city: City name to look up (e.g., 'Tokyo', 'London').
    Returns:
        A JSON string containing the city name, temperature in Celsius,
        wind speed in km/h, and a human-readable weather description.
    Raises:
        ValueError: If the city cannot be found.
    """
    #get city location coordinates (via above function)
    location = geocode_city(city)

    #define parameters; coordinates extracted from geocode_city dict
    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "current": "temperature_2m,weather_code,wind_speed_10m",
    }
    #call API and pass along established paramters, defining coordinates, what weather data we want back
    response = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params=params,
        timeout=5,
    )
    #capture response into "data"
    response.raise_for_status()
    data = response.json()

    current = data["current"]
    code = current["weather_code"]
    #translate received code into human-friendly language, as provided by above WEATHER_CODES
    description = WEATHER_CODES.get(code, "unknown")

#repeat the city, two pieces of data as extracted from the API response, plus weather description from lookup, as strings (vs Python dict that the Anthropic API doesn't accept):
    return json.dumps({
        "city": city,
        "temperature_c": current["temperature_2m"],
        "wind_speed_kmh": current["wind_speed_10m"],
        "weather_description": description,
    })

#tool agent can use to reliably convert between Celsius and Fahrenheit
@beta_tool
def convert_temperature(value: float, from_unit: str, to_unit: str) -> str:
    """Convert a temperature value between Celsius and Fahrenheit.

    Args:
        value: The temperature reading as a number.
        from_unit: The source unit. Must be 'celsius' or 'fahrenheit'.
        to_unit: The target unit. Must be 'celsius' or 'fahrenheit'.
    Returns:
        The converted temperature as a float.
    Raises:
        ValueError: If either unit is not 'celsius' or 'fahrenheit'.
    """
    
    # normalize inputs to lowercase to increase reliability:
    from_unit = from_unit.lower()
    to_unit = to_unit.lower()
     
    # handle junk units:
    valid_units = {"celsius", "fahrenheit"}
    if from_unit not in valid_units:
        raise ValueError(f"Unsupported from_unit: {from_unit!r}. Please use 'celsius' or 'fahrenheit'.")
    if to_unit not in valid_units:
        raise ValueError(f"Unsupported to_unit: {to_unit!r}. Please use 'celsius' or 'fahrenheit'.")

    # conduct calculation:
    if from_unit == "fahrenheit" and to_unit == "celsius":
        result = (value-32) * (5/9)

    elif from_unit == "celsius" and to_unit == "fahrenheit":
        result = value * (9/5) + 32

    else:
        result = value # same unit, no conversion needed

    return json.dumps(result)


#recruit Claude tool runner agent
result = client.beta.messages.tool_runner(
    model="claude-opus-4-7",
    max_tokens=1024,
    tools=[get_weather, convert_temperature],
    messages=[
        {
            "role": "user",
            "content": "What's the weather in Tunis?",
        }
    ],
).until_done()

for block in result.content:
    if block.type == "text":
        print(block.text)
