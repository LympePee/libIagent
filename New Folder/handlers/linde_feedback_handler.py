from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ConversationHandler, CommandHandler,
    MessageHandler, ContextTypes, filters
)
import pandas as pd
import os
from datetime import datetime

# === Σταθερές ===
GAS_TYPES = [
    "O2 Liv 5L",
    "O2 50L",
    "CO2 10L",
    "CO2 50L",
    "Air 50L"
]
GET_RETURN = range(1)
ML_DATASET_PATH = "logs/linde_ml_dataset.csv"  # not used yet, κρατιέται για επέκταση
RETURN_LOG_PATH = "logs/linde_feedback.csv"

# === Εκκίνηση συνομιλίας ===
async def start_linde_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['returns'] = {}
    context.user_data['current_index'] = 0
    await update.message.reply_text(
        "🔄 Καταγραφή επιστροφών προς Linde.\nΠόσες φιάλες επιστράφηκαν για:"
    )
    return await ask_next_gas(update, context)

# === Ερώτηση για το επόμενο είδος ===
async def ask_next_gas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data['current_index']
    if index >= len(GAS_TYPES):
        return await finish_feedback(update, context)

    gas = GAS_TYPES[index]
    await update.message.reply_text(f"{gas};\n(γράψε 0 αν δεν επιστράφηκαν)")
    return GET_RETURN

# === Λήψη απάντησης χρήστη ===
async def receive_return(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gas = GAS_TYPES[context.user_data['current_index']]
    try:
        qty = int(update.message.text.strip())
        if qty < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Έδωσες μη έγκυρο αριθμό. Προσπάθησε ξανά.")
        return GET_RETURN

    context.user_data['returns'][gas] = qty
    context.user_data['current_index'] += 1
    return await ask_next_gas(update, context)

# === Τέλος — Καταγραφή ===
async def finish_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().strftime("%Y-%m-%d")
    returns = context.user_data['returns']

    row = {
        'date': today,
        **{gas: returns.get(gas, 0) for gas in GAS_TYPES}
    }

    os.makedirs("logs", exist_ok=True)
    df = pd.DataFrame([row])
    if os.path.exists(RETURN_LOG_PATH):
        df.to_csv(RETURN_LOG_PATH, mode='a', index=False, header=False)
    else:
        df.to_csv(RETURN_LOG_PATH, index=False)

    await update.message.reply_text("✅ Οι επιστροφές καταγράφηκαν επιτυχώς.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# === Ακύρωση ===
async def cancel_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Η καταγραφή ακυρώθηκε.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# === Ορισμός ConversationHandler ===
linde_feedback_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("lindeFB", start_linde_feedback)],
    states={
        GET_RETURN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_return)],
    },
    fallbacks=[CommandHandler("cancel", cancel_feedback)]
)
