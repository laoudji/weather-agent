# Weather Agent

Built with the Anthropic SDK. Demonstrates tool use, error handling, and the agent loop, no frameworks.

## What it does

Given a natural-language weather query, the agent:
1. Looks up current weather for a city via Open-Meteo.
2. Optionally converts the temperature between Celsius and Fahrenheit.
3. Returns a conversational answer.

## Tools

- `get_weather(city)`: fetches current weather from Open-Meteo. Translates WMO weather codes to descriptions.
- `convert_temperature(value, from_unit, to_unit)`: converts between Celsius and Fahrenheit.

## Example

Input: "What's the weather in Tunis? Tell me in Fahrenheit."
Output: "It's currently 73°F and partly cloudy in Tunis with light winds."

## Notes

Built as a learning exercise. Uses the Anthropic SDK's `tool_runner` for the agent loop and Open-Meteo's free forecast and geocoding APIs.
