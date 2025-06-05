from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, ContextTypes, filters
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from datetime import datetime

from config import (
    GMAIL_USER,
    GMAIL_APP_PASSWORD as GMAIL_PASS,
    CC_EMAIL
)

from utils.email_log_utils import log_email  # ✅ Χρήση κοινής συνάρτησης

GET_TYPE, GET_DAMAGE, GET_DEPT, GET_SERIAL, ASK_PHOTO, GET_PHOTO = range(6)

def create_medic_plan_email(equipment_type, damage_report, department, serial_number, photo_attached=False):
    message = f"""
Αγαπητοί συνεργάτες,

Σας ενημερώνουμε για πρόβλημα που παρουσιάστηκε στον εξοπλισμό τύπου "{equipment_type}" με σειριακό αριθμό "{serial_number}".

Σύμφωνα με την αναφορά, το πρόβλημα είναι το εξής:
"{damage_report}"

Ο εξοπλισμός βρίσκεται στο τμήμα "{department}" και απαιτεί τεχνική υποστήριξη.
"""
    if photo_attached:
        message += "\nΕπισυνάπτεται σχετική φωτογραφία του εξοπλισμού.\n"

    message += "\nΜε εκτίμηση,\nΠαναγιώτης Λυμπέρης\nΤΥ ΩΚΚ"
    return message

def send_medicplan_email(equipment_type, damage_report, department, serial_number, photo_path=None):
    to_emails = ["techsecretary@medic-plan.com", "info@medic-plan.com"]
    subject = f'Βλάβη εξοπλισμού: {equipment_type} ("{serial_number}")'
    body = create_medic_plan_email(equipment_type, damage_report, department, serial_number, photo_attached=bool(photo_path))

    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = ", ".join(to_emails)
    msg['Cc'] = CC_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    if photo_path:
        try:
            with open(photo_path, "rb") as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(photo_path)}"')
                msg.attach(part)
        except Exception as e:
            print(f"⚠️ Δεν ήταν δυνατή η προσθήκη της φωτογραφίας: {e}")

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        recipients = to_emails + [CC_EMAIL]
        server.sendmail(GMAIL_USER, recipients, msg.as_string())
        server.quit()
        print("✅ Email προς MedicPlan στάλθηκε.")
        log_email("medicplan", subject, recipients, "✅ Sent", body)
        return True
    except Exception as e:
        print(f"❌ Σφάλμα στην αποστολή email: {e}")
        log_email("medicplan", subject, recipients, f"❌ Error", str(e))
        return False

# === Telegram Conversation ===

async def start_medicplan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Τι εξοπλισμός παρουσιάζει πρόβλημα;")
    return GET_TYPE

async def get_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['type'] = update.message.text.strip()
    await update.message.reply_text("Ποια είναι η αναφορά βλάβης;")
    return GET_DAMAGE

async def get_damage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['damage'] = update.message.text.strip()
    await update.message.reply_text("Σε ποιο τμήμα βρίσκεται ο εξοπλισμός;")
    return GET_DEPT

async def get_dept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dept'] = update.message.text.strip()
    await update.message.reply_text("Ποιος είναι ο σειριακός αριθμός; (ή γράψε No SN αν δεν υπάρχει)")
    return GET_SERIAL

async def get_serial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['serial'] = update.message.text.strip()
    await update.message.reply_text("Υπάρχει σχετική φωτογραφία; (Ναι/Όχι)",
        reply_markup=ReplyKeyboardMarkup([["Ναι", "Όχι"]], one_time_keyboard=True, resize_keyboard=True))
    return ASK_PHOTO

async def ask_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = update.message.text.lower()
    if response in ["ναι", "yes"]:
        await update.message.reply_text("Ανέβασε τη φωτογραφία τώρα.", reply_markup=ReplyKeyboardRemove())
        return GET_PHOTO
    else:
        return await send_email_and_finish(update, context)

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()
    photo_path = f"/tmp/photo_{update.effective_user.id}.jpg"
    await file.download_to_drive(photo_path)
    context.user_data['photo_path'] = photo_path
    return await send_email_and_finish(update, context)

async def send_email_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    serial = data.get('serial') or "no SN"
    photo_path = data.get('photo_path', None)

    try:
        success = send_medicplan_email(
            data['type'], data['damage'], data['dept'], serial, photo_path
        )
    except Exception as e:
        print(f"❌ Σφάλμα μέσα στη send_medicplan_email: {e}")
        success = False

    if photo_path and os.path.exists(photo_path):
        os.remove(photo_path)

    if success:
        await update.message.reply_text("✅ Το email στάλθηκε επιτυχώς στη Medic Plan.")
    else:
        await update.message.reply_text("❌ Κάτι πήγε στραβά με την αποστολή του email.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Η διαδικασία ακυρώθηκε.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

medicplan_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("medicplan", start_medicplan)],
    states={
        GET_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_type)],
        GET_DAMAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_damage)],
        GET_DEPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_dept)],
        GET_SERIAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_serial)],
        ASK_PHOTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_photo)],
        GET_PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
