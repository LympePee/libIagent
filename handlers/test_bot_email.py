from dotenv import load_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Φόρτωση μεταβλητών από .env
load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Συνάρτηση αποστολής email
def send_test_email():
    from_email = GMAIL_USER
    to_email = "liberispngt@gmail.com"
    cc_email = "ty_technologoi@ocsc.gr"
    subject = "✅ Τεστ αποστολής από Telegram Bot"
    body = "Αυτό είναι ένα δοκιμαστικό email που στάλθηκε από το Telegram bot."

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Cc'] = cc_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_email, GMAIL_PASS)
        recipients = [to_email] + [cc_email]
        server.sendmail(from_email, recipients, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Σφάλμα κατά την αποστολή: {e}")
        return False

# Telegram handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    success = send_test_email()
    if success:
        await update.message.reply_text("📤 Το email στάλθηκε με επιτυχία!")
    else:
        await update.message.reply_text("❌ Η αποστολή email απέτυχε.")

# Εκκίνηση bot
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("🤖 Bot is running... Περιμένει /start")
    app.run_polling()
