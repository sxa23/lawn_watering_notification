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
    # Past 2h + current + next 2h in local time; hourly precipitation (API default mm unless overridden).
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "precipitation,temperature_2m",
            "past_hours": 2,
            "forecast_hours": 2,
            "timezone": "auto",
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
        },
        timeout=30,
    )
    resp.raise_for_status()
    response = resp.json()

    hourly = response.get("hourly") or {}
    precip_hours = hourly.get("precipitation") or []
    temp_hours = hourly.get("temperature_2m") or []

    total_rain = sum(p if p is not None else 0.0 for p in precip_hours)
    temps = [t for t in temp_hours if t is not None]
    max_temp = max(temps) if temps else None

    # Logic: Water if it's hot and hasn't rained much (over the hourly window).
    if (max_temp is not None and max_temp > THRESHOLD_TEMP) or (
        total_rain < THRESHOLD_RAIN
    ):
        return (
            f"💧 Water the lawn! High around {max_temp:.0f}°F and only "
            f"{total_rain:.2f}in of rain in the past/current/next few hours."
        )
    return (
        f"🚫 No need to water the lawn today. High around {max_temp:.0f}°F and "
        f"only {total_rain:.2f}in of rain in the past/current/next few hours."
    )


def send_notification(message):
    topic = _required_env("NTFY_TOPIC")
    requests.post(f"https://ntfy.sh/{topic}", data=message.encode("utf-8"))


if __name__ == "__main__":
    result = check_weather()
    print(result)
    send_notification(result)
