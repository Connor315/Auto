import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

load_dotenv()

def fetch_gas_price_change(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        section = soup.find("div", class_="gas-prices-section")
        if section:
            info_box = section.get_text(separator="\n").strip()
            return info_box
    return "Gas price information could not be retrieved."

def determine_price_change_status(gas_info: str) -> str:
    lowered = gas_info.lower()
    if "increase" in lowered or "up" in lowered or "rise" in lowered or "higher" in lowered:
        return "up"
    elif "drop" in lowered or "decrease" in lowered or "down" in lowered or "fall" in lowered:
        return "down"
    elif "no change" in lowered or "unchanged" in lowered:
        return "unchanged"
    else:
        return "unknown"

def send_email(gas_info):
    sender = os.environ['EMAIL_SENDER']
    password = os.environ['EMAIL_PASSWORD']
    receivers = os.environ['EMAIL_RECEIVERS'].split(',')

    status = determine_price_change_status(gas_info)

    tomorrow = (datetime.now(pytz.timezone('America/Toronto')) + timedelta(days=1)).strftime('%A, %B %d, %Y')

    if status == "up":
        subject = f"⬆️ Price Increasing Tomorrow – Fuel Up Today!"
    elif status == "down":
        subject = f"⬇️ Price Dropping Tomorrow – Wait to Fuel Up!"
    elif status == "unchanged":
        subject = f"⏸️ Price Unchanged Tomorrow – Fuel Anytime"
    else:
        subject = "ℹ️ Gas Price Update – Unable to Determine Change"

    color_map = {
        "up": "red",
        "down": "green",
        "unchanged": "gray",
        "unknown": "black"
    }
    color = color_map.get(status, "black")

    html = f"""
    <html>
        <body>
            <h2 style="color:{color};">Gas Price Forecast for {tomorrow}</h2>
            <p>{gas_info}</p>
            <p><a href="https://toronto.citynews.ca/toronto-gta-gas-prices/">View Full Details</a></p>
        </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ", ".join(receivers)
    msg.attach(MIMEText(html, 'html'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender, password)
    server.sendmail(sender, receivers, msg.as_string())
    server.quit()

url = 'https://toronto.citynews.ca/toronto-gta-gas-prices/'
gas_info = fetch_gas_price_change(url)
send_email(gas_info)
