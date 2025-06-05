import os
import csv
from datetime import datetime

EMAIL_LOG_FILE = "logs/email_history.csv"
os.makedirs("logs", exist_ok=True)


def log_email(email_type, subject, recipients, status, body):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = [
        now_str,
        email_type,
        subject,
        "; ".join(recipients),
        status,
        body.strip().replace("\n", " ")[:300]  # περιορισμός στους 300 χαρακτήρες
    ]

    write_header = not os.path.exists(EMAIL_LOG_FILE)

    with open(EMAIL_LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        if write_header:
            writer.writerow(["timestamp", "email_type", "subject", "recipients", "status", "body"])
        writer.writerow(log_entry)
