import os
import requests

THRESHOLD_TEMP = 80  # Fahrenheit
THRESHOLD_RAIN = 0.1  # Inches


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} environment variable must be set (non-empty)")
    return value


def lat_lon_from_zip(zip_code: str, *, country_code: str = "US") -> tuple[float, float]:
    """Resolve WGS84 coordinates from a postal code via Open-Meteo geocoding."""
    resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={
            "name": zip_code.strip(),
            "count": 1,
            "countryCode": country_code,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results") or []
    if not results:
        raise ValueError(
            f"No geocoding match for postal code {zip_code!r} (country {country_code})"
        )
    loc = results[0]
    return float(loc["latitude"]), float(loc["longitude"])


def check_weather():
    zip_code = _required_env("ZIP_CODE")
    country_code = _required_env("COUNTRY_CODE")
    lat, lon = lat_lon_from_zip(zip_code, country_code=country_code)
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=temperature_2m_max,precipitation_sum&timezone=auto"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    response = resp.json()

    today_temp = response["daily"]["temperature_2m_max"][0]
    today_rain = response["daily"]["precipitation_sum"][0]

    # Logic: Water if it's hot and hasn't rained much
    if today_temp > THRESHOLD_TEMP and today_rain < THRESHOLD_RAIN:
        return f"💧 Water the lawn! It's {today_temp}°F and only {today_rain}in of rain."
    else:
        return "🚫 No need to water the lawn today."


def send_notification(message):
    topic = _required_env("NTFY_TOPIC")
    requests.post(f"https://ntfy.sh/{topic}", data=message.encode("utf-8"))


if __name__ == "__main__":
    result = check_weather()
    print(result)
    send_notification(result)
