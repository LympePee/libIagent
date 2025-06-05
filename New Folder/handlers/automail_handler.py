from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, ContextTypes, filters
import openai
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import GMAIL_USER, GMAIL_APP_PASSWORD as GMAIL_PASS, OPENAI_API_KEY
import json
import os

# ✅ OpenAI Client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# --- Στάδια συνομιλίας ---
ASK_EMAIL, ASK_MESSAGE, CONFIRM_SEND = range(3)

# --- Αρχείο email διευθύνσεων ---
EMAILS_FILE = "config_data/known_emails.json"

def load_known_emails():
    if os.path.exists(EMAILS_FILE):
        with open(EMAILS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_email_to_memory(email):
    emails = load_known_emails()
    if email not in emails:
        emails.append(email)
        with open(EMAILS_FILE, 'w') as f:
            json.dump(emails, f, indent=2)

# --- Δημιουργία email με OpenAI ---
def generate_email_text(raw_text):
    prompt = f"""
    Μετατροπή σε επίσημο email:

    {raw_text}

    Δώσε μόνο το τελικό email, σωστά διαμορφωμένο.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Σφάλμα: {e}"

# --- Αποστολή email ---
def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        return False

# --- Telegram Handlers ---
async def start_automail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    known_emails = load_known_emails()
    if known_emails:
        keyboard = [[email] for email in known_emails] + [["Νέα διεύθυνση"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("📬 Διάλεξε email ή γράψε νέο:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("📬 Ποια είναι η διεύθυνση email παραλήπτη;")
    return ASK_EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    if email.lower() in ["νέα διεύθυνση", "new", "new address"]:
        await update.message.reply_text("✍️ Πληκτρολόγησε τη νέα διεύθυνση email:")
        return ASK_EMAIL

    context.user_data['email'] = email
    await update.message.reply_text("✍️ Γράψε τι θέλεις να περιέχει το email (σε απλά λόγια):", reply_markup=ReplyKeyboardRemove())
    return ASK_MESSAGE

async def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    formatted = generate_email_text(raw)
    context.user_data['message'] = formatted

    await update.message.reply_text(f"✅ Το email διαμορφώθηκε:\n\n{formatted}\n\nΝα το στείλω; (Ναι/Όχι)")
    return CONFIRM_SEND

async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = update.message.text.lower().strip()
    yes_variants = ["ναι", "nai", "yes"]
    no_variants = ["όχι", "oxi", "όχι.", "no", "οχι", "οχι."]

    if response in yes_variants:
        email = context.user_data['email']
        body = context.user_data['message']
        subject = body.split("\n")[0].replace("Θέμα:", "").strip() if "Θέμα:" in body else "Γενικό Ερώτημα"

        save_email_to_memory(email)
        success = send_email(email, subject, body)
        if success:
            await update.message.reply_text("✅ Το email στάλθηκε επιτυχώς!")
        else:
            await update.message.reply_text("❌ Σφάλμα κατά την αποστολή του email.")
        return ConversationHandler.END

    elif response in no_variants:
        await update.message.reply_text("🔁 Τι θέλεις να διορθώσουμε στο email; Πληκτρολόγησε ξανά:")
        return ASK_MESSAGE

    else:
        await update.message.reply_text("❓ Απάντησε με 'Ναι' ή 'Όχι'")
        return CONFIRM_SEND

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Η διαδικασία ακυρώθηκε.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- Export για main.py ---
automail_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("automail", start_automail)],
    states={
        ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
        ASK_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_message)],
        CONFIRM_SEND: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_send)],
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)
