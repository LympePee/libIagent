from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import GMAIL_USER, GMAIL_APP_PASSWORD as GMAIL_PASS, CC_EMAIL
from utils.email_log_utils import log_email

GET_CYLINDERS, GET_EXTRA_ITEMS = range(2)

# Υπολογισμός επόμενης Τρίτης ή Πέμπτης
def get_next_tuesday_or_thursday(current_date):
    weekday = current_date.weekday()
    if weekday == 1:
        return current_date + timedelta(days=2)
    elif weekday == 3:
        return current_date + timedelta(days=5)
    else:
        days_to_tuesday = (1 - weekday + 7) % 7
        days_to_thursday = (3 - weekday + 7) % 7
        return current_date + timedelta(days=min(days_to_tuesday, days_to_thursday))

# Δημιουργία email
def create_order_email(cylinders_count, delivery_date, additional_items):
    return f"""
Αγαπητοί συνεργάτες,

Θα ήθελα παρακαλώ να στείλετε στο Ωνάσειο {cylinders_count} φιάλες οξυγόνου 5 ltr τύπου liv {additional_items}την {delivery_date.strftime('%A %d/%m/%Y')}.

Με εκτίμηση,
ΠΛ
"""

# Αποστολή email
def send_linde_email(cylinders_count, additional_items):
    recipient_email = "sales-support.gr@linde.com"
    subject = "Αίτηση παραγγελίας φιαλών οξυγόνου"
    current_date = datetime.now()
    delivery_date = get_next_tuesday_or_thursday(current_date)

    if additional_items.lower() in ["όχι", "oxi", "no"]:
        additional_items = ""
    else:
        additional_items = f"και {additional_items} "

    body = create_order_email(cylinders_count, delivery_date, additional_items)

    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = recipient_email
    msg['Cc'] = CC_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    recipients = [recipient_email, CC_EMAIL]
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, recipients, msg.as_string())
        server.quit()
        print("✅ Email προς Linde στάλθηκε.")
        log_email("linde", subject, recipients, "✅ Success", f"Φιάλες: {cylinders_count}, Extra: {additional_items.strip()}")
        return True
    except Exception as e:
        print(f"❌ Σφάλμα στην αποστολή email: {e}")
        log_email("linde", subject, recipients, "❌ Failed", str(e))
        return False

# --- Telegram Handlers ---

async def start_linde(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Πόσες φιάλες οξυγόνου θέλεις να παραγγείλεις;")
    return GET_CYLINDERS

async def get_cylinders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cylinders_count'] = update.message.text.strip()
    await update.message.reply_text("Χρειάζεσαι κάτι επιπλέον; (π.χ. και CO2 50L)\nΑν όχι, γράψε Όχι / oxi / no.")
    return GET_EXTRA_ITEMS

async def get_extra_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    extra = update.message.text.strip()
    cylinders = context.user_data['cylinders_count']

    success = send_linde_email(cylinders, extra)
    if success:
        await update.message.reply_text("✅ Η παραγγελία στάλθηκε επιτυχώς στη Linde.")
    else:
        await update.message.reply_text("❌ Κάτι πήγε στραβά με την αποστολή του email.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Η διαδικασία ακυρώθηκε.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ➕ Handler για main.py
linde_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("linde", start_linde)],
    states={
        GET_CYLINDERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_cylinders)],
        GET_EXTRA_ITEMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_extra_items)]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)
