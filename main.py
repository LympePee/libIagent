import os  # ✅ Ξεχασμένο import
import logging
import time
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# === Ρυθμίσεις Logging ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === Φορτώνουμε ρυθμίσεις από config.py ===
from config import (
    GMAIL_USER,
    GMAIL_APP_PASSWORD as GMAIL_PASS,
    CC_EMAIL,
    TELEGRAM_TOKEN,
    OPENAI_API_KEY,
    GOOGLE_SERVICE_ACCOUNT_FILE,
    GOOGLE_SPREADSHEET_ID
)

# === Φορτώνουμε Handlers ===
from handlers.automail_handler import automail_conv_handler
from handlers.autoxl_handler import autoxl_conv_handler
from handlers.medicplan_handler import medicplan_conv_handler
from handlers.scoramida_handler import scoramida_conv_handler
from handlers.linde_handler import (
    start_linde, get_cylinders, get_extra_items, cancel,
    GET_CYLINDERS, GET_EXTRA_ITEMS
)
from handlers.linde_feedback_handler import linde_feedback_conv_handler  # ✅ νέος handler επιστροφών

# === Scheduler ===
scheduler_path = os.path.join(os.path.dirname(__file__), "linde_order_scheduler.py")
if os.path.exists(scheduler_path):
    try:
        from linde_order_scheduler import start_linde_scheduler
    except Exception as e:
        logging.warning(f"⚠️ Αποτυχία φόρτωσης του scheduler: {e}")
        start_linde_scheduler = None
else:
    logging.warning("⚠️ Δεν βρέθηκε το αρχείο linde_order_scheduler.py. Ο scheduler Linde δεν θα ξεκινήσει.")
    start_linde_scheduler = None

# === Εκκίνηση Telegram Bot με επανεκκίνηση αν χαθεί σύνδεση ===
if __name__ == "__main__":
    while True:
        try:
            app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

            # ➕ Linde Handler
            linde_conv_handler = ConversationHandler(
                entry_points=[CommandHandler("linde", start_linde)],
                states={
                    GET_CYLINDERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_cylinders)],
                    GET_EXTRA_ITEMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_extra_items)]
                },
                fallbacks=[CommandHandler("cancel", cancel)]
            )

            # ➕ Προσθήκη όλων των handlers
            app.add_handler(linde_conv_handler)
            app.add_handler(automail_conv_handler)
            app.add_handler(autoxl_conv_handler)
            app.add_handler(medicplan_conv_handler)
            app.add_handler(scoramida_conv_handler)
            app.add_handler(linde_feedback_conv_handler)  # ✅ /lindeFB

            # ✅ Εκκίνηση Scheduler παραγγελιών Linde (αν υπάρχει)
            if start_linde_scheduler:
                start_linde_scheduler()
                print("📅 Ο scheduler της Linde ξεκίνησε!")

            print("🤖 Bot ενεργό... Περιμένει εντολές!")
            app.run_polling()

        except Exception as e:
            logging.error(f"❌ Σφάλμα bot: {e}\n🔁 Επανεκκίνηση σε 10 δευτερόλεπτα...")
            time.sleep(10)
