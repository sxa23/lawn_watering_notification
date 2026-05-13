import requests
import os

# Configuration
ZIP_CODE = "44039" # North Ridgeville
LAT, LON = 41.38, -82.01 # Approx coordinates for accuracy
THRESHOLD_TEMP = 80 # Fahrenheit
THRESHOLD_RAIN = 0.1 # Inches

def check_weather():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=temperature_2m_max,precipitation_sum&timezone=auto"
    response = requests.get(url).json()
    
    today_temp = response['daily']['temperature_2m_max'][0]
    today_rain = response['daily']['precipitation_sum'][0]
    
    # Logic: Water if it's hot and hasn't rained much
    if today_temp > THRESHOLD_TEMP and today_rain < THRESHOLD_RAIN:
        return f"💧 Water the lawn! It's {today_temp}°F and only {today_rain}in of rain."
    else:
        return "🚫 No need to water the lawn today."

def send_notification(message):
    # We use NTFY.sh (Free, no account needed)
    # You can download the NTFY app on your phone to get the alert
    topic = "my_private_alerts_soma2307" 
    requests.post(f"https://ntfy.sh/{topic}", data=message.encode('utf-8'))

if __name__ == "__main__":
    result = check_weather()
    print(result)
    send_notification(result)