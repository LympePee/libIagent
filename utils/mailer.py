# utils/mailer.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import GMAIL_USER, GMAIL_APP_PASSWORD

def send_email(from_addr, to_addr, cc_addr, subject, body):
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Cc"] = cc_addr
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(from_addr, [to_addr, cc_addr], msg.as_string())
        return True
    except Exception as e:
        print(f"❌ Αποτυχία αποστολής email: {e}")
        return False
