"""Fetch local weather from Open-Meteo and ntfy when lawn watering may be needed."""

import logging
import os

import requests

logger = logging.getLogger(__name__)

THRESHOLD_TEMP = 80  # Fahrenheit
THRESHOLD_RAIN = 0.1  # Inches

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} environment variable must be set (non-empty)")
    return value


def lat_lon_from_zip(zip_code: str, *, country_code: str = "US") -> tuple[float, float]:
    """Resolve WGS84 coordinates from a postal code via Open-Meteo geocoding."""
    resp = requests.get(
        GEOCODING_URL,
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


def _summarize_hourly(hourly: dict) -> tuple[float, float | None]:
    """Return (total_precip_inches, max_temp_f) from hourly series; None temps ignored for max."""
    precip_hours = hourly.get("precipitation") or []
    temp_hours = hourly.get("temperature_2m") or []

    total_rain = sum(p if p is not None else 0.0 for p in precip_hours)
    temps = [t for t in temp_hours if t is not None]
    max_temp = max(temps) if temps else None
    return total_rain, max_temp


def _format_temp(max_temp: float | None) -> str:
    return f"{max_temp:.0f}°F" if max_temp is not None else "N/A"


def check_weather() -> str:
    """Return a human-readable line about whether to water, using past/current/next few hours."""
    zip_code = _required_env("ZIP_CODE")
    country_code = _required_env("COUNTRY_CODE")
    lat, lon = lat_lon_from_zip(zip_code, country_code=country_code)

    resp = requests.get(
        FORECAST_URL,
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
    logger.info("Open-Meteo forecast URL: %s", resp.url)
    logger.info(
        "Open-Meteo forecast response: status=%s body=%s",
        resp.status_code,
        resp.text,
    )
    resp.raise_for_status()
    hourly = resp.json().get("hourly") or {}

    total_rain, max_temp = _summarize_hourly(hourly)

    # Alert when either threshold trips: hot spell or little rain in the window.
    is_hot = max_temp is not None and max_temp > THRESHOLD_TEMP
    is_dry = total_rain < THRESHOLD_RAIN
    should_water = is_hot or is_dry

    temp_label = _format_temp(max_temp)
    rain_label = f"{total_rain:.2f}in"
    window = "past/current/next few hours"

    if should_water:
        return (
            f"💧 Water the lawn! High around {temp_label} and only {rain_label} of rain "
            f"in the {window}."
        )
    return (
        f"🚫 No need to water the lawn today. High around {temp_label} and "
        f"only {rain_label} of rain in the {window}."
    )


def send_notification(message: str) -> None:
    topic = _required_env("NTFY_TOPIC")
    requests.post(f"https://ntfy.sh/{topic}", data=message.encode("utf-8"))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = check_weather()
    print(result)
    send_notification(result)
