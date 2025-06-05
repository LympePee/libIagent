from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, ContextTypes, filters
from pathlib import Path
import os
import csv
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

# 🔹 Φόρτωση μεταβλητών .env
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")
CC_EMAIL = os.getenv("CC_EMAIL", "ty_technologoi@ocsc.gr")

# === Logging ===
LOG_FILE = "logs/email_history.csv"
os.makedirs("logs", exist_ok=True)

def log_email_event(timestamp, subject, recipients, cc, body, success):
    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            timestamp,
            subject,
            ", ".join(recipients),
            cc,
            body.strip().replace("\n", " ")[:300],
            "OK" if success else "FAIL"
        ])

# --- Βήματα συνομιλίας ---
SELECT_DEPARTMENT, ENTER_NOTE = range(2)

# Λίστα επιλογών τμημάτων
department_options = [
    ["1", "2"],
    ["3", "4"],
    ["5"]
]

# Λεξικό τμημάτων
departments = {
    "1": "ΜΕΘ κ/δ",
    "2": "ΜΕΘ κ/χ",
    "3": "4ος όροφος",
    "4": "5ος όροφος",
    "5": "6ος όροφος"
}

# --- Συνάρτηση για αποστολή email ---
def send_scoramides_email(department_key: str, note: str = "") -> bool:
    if department_key not in departments:
        return False

    department = departments[department_key]
    recipient = "papoudis@papoudis.gr"
    subject = "Αίτημα για έλεγχο πλυντηρίου σκοραμιδών"

    body = f"""Αξιότιμοι κύριοι,

Το πλυντήριο σκοραμιδών στο τμήμα {department} είναι εκτός λειτουργίας. Παρακαλούμε να αποστείλετε τον τεχνικό σας το συντομότερο δυνατόν για την αποκατάσταση της βλάβης."""

    if note:
        body += f"\n\nΠαρατήρηση: {note}"

    body += """

Ευχαριστούμε εκ των προτέρων για την άμεση ανταπόκρισή σας.
Με εκτίμηση,
ΠΛ
ΤΥ ΩΚΚ
t : 6946167079
"""

    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = recipient
        msg['Cc'] = CC_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        recipients = [recipient, CC_EMAIL]
        server.sendmail(GMAIL_USER, recipients, msg.as_string())
        server.quit()

        log_email_event(
            datetime.now().isoformat(timespec='seconds'),
            subject,
            recipients,
            CC_EMAIL,
            body,
            success=True
        )
        return True

    except Exception as e:
        print(f"❌ Σφάλμα κατά την αποστολή email: {e}")
        log_email_event(
            datetime.now().isoformat(timespec='seconds'),
            subject,
            [recipient],
            CC_EMAIL,
            body,
            success=False
        )
        return False

# --- Telegram Handlers ---

async def start_scoramida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔹 Σε ποιο τμήμα υπάρχει το πρόβλημα;\nΔώσε αριθμό:",
        reply_markup=ReplyKeyboardMarkup(department_options, one_time_keyboard=True, resize_keyboard=True)
    )
    return SELECT_DEPARTMENT

async def select_department(update: Update, context: ContextTypes.DEFAULT_TYPE):
    department_key = update.message.text
    if department_key not in departments:
        await update.message.reply_text("⚠️ Μη έγκυρη επιλογή. Προσπάθησε ξανά.")
        return SELECT_DEPARTMENT

    context.user_data["department_key"] = department_key
    await update.message.reply_text(
        "💬 Θες να προσθέσεις κάποια παρατήρηση;\n(Αν όχι, πάτα Enter)",
        reply_markup=ReplyKeyboardRemove()
    )
    return ENTER_NOTE

async def enter_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text
    department_key = context.user_data["department_key"]

    success = send_scoramides_email(department_key, note)
    if success:
        await update.message.reply_text("✉️ Το email για το πλυντήριο σκοραμιδών στάλθηκε επιτυχώς!")
    else:
        await update.message.reply_text("❌ Παρουσιάστηκε πρόβλημα κατά την αποστολή του email.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Ακύρωση διαδικασίας.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# 🔁 Αντικείμενο handler για το main.py
scoramida_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("scoramida", start_scoramida)],
    states={
        SELECT_DEPARTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_department)],
        ENTER_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_note)]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)
