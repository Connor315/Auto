import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz

cautionary_keywords = ["showers", "thunderstorm", "snow", "icy", "heavy rain", "hail", "gale", "blizzard", "fog", "sleet", "flurries"]

def fetch_weather_data(url):
    response = requests.get(url)
    forecast_data = []
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        elements = soup.find_all(attrs={"data-testid": "period-section-heading"})
        second_element = elements[1] if len(elements) > 1 else None
        parent_div = second_element.find_parent('div') if second_element else None
        
        weather_forecasts = parent_div.find_all(attrs={"data-testid": "forecast-module-row"})
        for row in weather_forecasts:
            time = row.find(attrs={"data-testid": "row-date-or-time"}).text
            weather = row.find(attrs={"data-testid": "weather-icon"}).img['alt']
            temperature = row.find(attrs={"data-testid": "row-temperature"}).text
            feels_like = row.find(attrs={"data-testid": "row-feels-like"}).text.replace("Feels", "").strip()
            pop_info = row.find(attrs={"data-testid": "collapsed-row-pop-info"})
            pop = pop_info.find_all("div")[-1].text if pop_info else "No data"
            severe_weather = any(keyword in weather.lower() for keyword in cautionary_keywords)
            forecast_data.append((time, weather, temperature, feels_like, pop, severe_weather))
    return forecast_data

def send_email(weather_data):
    sender = os.environ['EMAIL_SENDER']
    password = os.environ['EMAIL_PASSWORD']
    receivers = os.environ['EMAIL_RECEIVERS'].split(',')
    
    severe_conditions = {data[1] for data in weather_data if data[-1]}

    if severe_conditions:
        weather_list = ", ".join(sorted(severe_conditions))
        subject = f"Weather Alert: Severe Conditions Expected Tomorrow - {weather_list}"
    else:
        subject = "Enjoy a Nice Day Tomorrow"

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ", ".join(receivers)
    
    tomorrow = (datetime.now(pytz.timezone('America/Toronto')) + timedelta(days=1)).strftime('%A, %B %d, %Y')

    html = f"<html><body><h2>Weather Forecast for Tomorrow ({tomorrow})</h2>"
    
    for data in weather_data:
        time, weather, temp, feels_like, pop, severe = data
        color = 'red' if severe else 'black'
        html += f"<p><span style='color:{color};'>{time}: Weather: {weather}, Temp: {temp}°C, Feels like: {feels_like}°C, P.O.P.: {pop}</span></p>"

    html += "</body></html>"
    msg.attach(MIMEText(html, 'html'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender, password)
    server.sendmail(sender, receivers, msg.as_string())
    server.quit()

url = 'https://www.theweathernetwork.com/en/city/ca/ontario/north-york/hourly'
weather_data = fetch_weather_data(url)
send_email(weather_data)