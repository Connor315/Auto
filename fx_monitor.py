import os
import re
import smtplib
import certifi
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------- Load configuration ----------
load_dotenv()
API_KEY = os.getenv("EXCHANGE_API_KEY")
BASE_URL = f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/"
LOG_FILE = "rates_log.txt"

# ---------- Core rate retrieval ----------
def fetch_rates(base_currency):
    """Fetch exchange rates given a base currency, forcing requests to use certifi's CA bundle."""
    url = BASE_URL + base_currency
    response = requests.get(url, verify=certifi.where())
    response.raise_for_status()
    return response.json()["conversion_rates"]

def log_rate(pair, date_str, value):
    """Append formatted rate info to log file."""
    line = f"{pair}: {date_str}: {value:.4f}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(line.strip())

# ---------- Historical analysis ----------
def load_recent_rates(pair, days=7):
    if not os.path.exists(LOG_FILE):
        return []
    cutoff = datetime.now(ZoneInfo("America/Toronto")) - timedelta(days=days)
    rates = []

    pattern = re.compile(
        rf"^{pair}:\s+(\d{{4}}-\d{{2}}-\d{{2}}):\s+([0-9.]+)$"
    )

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                date_str, value = match.groups()
                date = datetime.strptime(date_str, "%Y-%m-%d").replace(
                    tzinfo=ZoneInfo("America/Toronto")
                )
                if date >= cutoff:
                    rates.append(float(value))

    return rates

# ---------- Analysis and recommendation ----------
def analyze_rate(pair, current_rate):
    """Compare current rate to true 7-day average and classify trend."""
    last_week = load_recent_rates(pair)
    if len(last_week) < 7:
        return "Not sufficient data", "gray", "N/A", "N/A", "N/A"

    avg = sum(last_week) / len(last_week)
    diff = (current_rate - avg) / avg * 100

    if diff > 1.0:
        status, color, reason = "Strong", "green", f"{pair} is {diff:.2f}% above 7-day avg"
    elif diff < -1.0:
        status, color, reason = "Weak", "red", f"{pair} is {abs(diff):.2f}% below 7-day avg"
    else:
        status, color, reason = "Stable", "gray", f"{pair} within ±1% of 7-day avg"

    # Logic per currency pair
    if pair == "USD-CAD":
        # High USD/CAD means USD is strong, CAD is weak
        suggestion = "Transfer CAD → USD" if status == "Strong" else "Transfer USD → CAD"
    elif pair == "USD-CNY":
        suggestion = "Transfer CAD → USD" if status == "Strong" else "Transfer USD → CAD"
    elif pair == "USD-HKD":
        suggestion = "Transfer CAD → USD" if status == "Strong" else "Transfer HKD → USD"
    elif pair == "CAD-CNY":
        # High CAD/CNY means CAD is strong, good time to send CAD abroad
        suggestion = "Transfer CAD → CNY" if status == "Strong" else "Transfer CNY → CAD"
    elif pair == "CAD-HKD":
        suggestion = "Transfer CAD → HKD" if status == "Strong" else "Transfer HKD → CAD"
    else:
        suggestion = "Hold"

    return status, color, reason, avg, suggestion

# ---------- Email reporting ----------
def send_email(results):
    sender = os.environ['EMAIL_SENDER']
    password = os.environ['EMAIL_PASSWORD']
    receivers = os.environ['EMAIL_RECEIVERS'].split(',')

    now = datetime.now(ZoneInfo("America/Toronto")).strftime("%Y-%m-%d")
    subject = f"Currency Report – {now}"

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ", ".join(receivers)

    html = "<html><body>"
    html += f"<h2>Currency Monitoring Summary ({now})</h2>"
    html += "<table border='1' cellpadding='6' cellspacing='0'>"
    html += "<tr><th>Pair</th><th>Current</th><th>7-day Avg</th><th>Status</th><th>Reason</th><th>Recommendation</th></tr>"

    for pair, current, avg, status, color, reason, suggestion in results:
        avg_display = f"{avg:.4f}" if isinstance(avg, float) else "N/A"
        html += f"<tr><td>{pair}</td><td>{current:.4f}</td><td>{avg_display}</td>"
        html += f"<td style='color:{color};font-weight:bold'>{status}</td>"
        html += f"<td>{reason}</td><td><b>{suggestion}</b></td></tr>"

    html += "</table><br><p><i>Color legend: Green = strong, Red = weak, Gray = stable or insufficient data.</i></p>"
    html += "</body></html>"
    msg.attach(MIMEText(html, 'html'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receivers, msg.as_string())

    print("Email sent successfully.")

# ---------- Main flow ----------
def main():
    now = datetime.now(ZoneInfo("America/Toronto")).strftime("%Y-%m-%d")

    try:
        usd_rates = fetch_rates("USD")
        cad_rates = fetch_rates("CAD")

        pairs = {
            "USD-CAD": usd_rates["CAD"],
            "USD-CNY": usd_rates["CNY"],
            "USD-HKD": usd_rates["HKD"],
            "CAD-CNY": cad_rates["CNY"],
            "CAD-HKD": cad_rates["HKD"],
        }

        results = []
        for pair, rate in pairs.items():
            log_rate(pair, now, rate)
            status, color, reason, avg, suggestion = analyze_rate(pair, rate)
            results.append((pair, rate, avg, status, color, reason, suggestion))

        send_email(results)

    except Exception as e:
        print(f"[Error] {e}")

if __name__ == "__main__":
    main()
