from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, ContextTypes, filters
import tempfile
import os

# ⬇️ Imports από τα utils
from utils.ocr_utils import process_uploaded_image
from utils.gsheet_utils import update_google_sheet  # Διορθώσαμε το όνομα της συνάρτησης

ASK_IMAGE = 0

# === /autoxl ===
async def start_autoxl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📤 Στείλε μου μία εικόνα που περιέχει δεδομένα για το Excel.")
    return ASK_IMAGE

async def receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1] if update.message.photo else None
    document = update.message.document if update.message.document else None

    if not photo and not document:
        await update.message.reply_text("❌ Δεν εντόπισα εικόνα. Δοκίμασε ξανά.")
        return ASK_IMAGE

    file = photo or document
    file_path = os.path.join(tempfile.gettempdir(), "uploaded_image.jpg")
    new_file = await file.get_file()
    await new_file.download_to_drive(file_path)

    await update.message.reply_text("🧠 Επεξεργάζομαι την εικόνα... Μισό λεπτό...")

    try:
        df = process_uploaded_image(file_path)

        if df.empty:
            await update.message.reply_text("⚠️ Δεν εντόπισα χρήσιμα δεδομένα στην εικόνα.")
            return ConversationHandler.END

        sheet_name = "AutoXL_Import"
        update_google_sheet(df, sheet_name)

        await update.message.reply_text(
            f"✅ Τα δεδομένα καταχωρήθηκαν στο φύλλο Google Sheets: *{sheet_name}*",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Σφάλμα κατά την επεξεργασία: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Η διαδικασία ακυρώθηκε.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# === Handler για main.py ===
autoxl_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("autoxl", start_autoxl)],
    states={
        ASK_IMAGE: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_image)]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)
