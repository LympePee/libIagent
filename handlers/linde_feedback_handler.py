from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime
import os
import pandas as pd

GAS_TYPES = [
    "Oxygen 5L (LIV)",
    "Oxygen 10L",
    "CO2 10L",
    "CO2 50L",
    "Medical Air 50L"
]

ML_DATASET_PATH = "logs/linde_ml_dataset.csv"
RETURN_LOG_PATH = "logs/linde_feedback.csv"
ML_COLUMNS = [
    "date", "gas_type", "manual_order", "returned", "ordered", "final_stock", "target_stock"
]
GET_RETURN = range(1)

def update_ml_returned(date_str, returns):
    """
    Ενημερώνει ΜΟΝΟ τη στήλη returned του ML dataset για κάθε gas_type και ημερομηνία.
    Δεν αλλοιώνει ή διαγράφει ποτέ τα υπόλοιπα δεδομένα.
    ΕΞΑΝΑΓΚΑΖΕΙ ΣΩΣΤΗ ΣΕΙΡΑ/ΤΙΤΛΟΥΣ ΣΤΗΛΩΝ, ΔΕΝ ΑΦΗΝΕΙ index/None/περιττές.
    """
    # Αν δεν υπάρχει, δημιουργεί το σωστό template με ΜΟΝΟ τις σωστές στήλες
    if not os.path.exists(ML_DATASET_PATH):
        rows = []
        for gas_type, qty in returns.items():
            row = dict.fromkeys(ML_COLUMNS, "")
            row["date"] = date_str
            row["gas_type"] = gas_type
            row["manual_order"] = 0
            row["returned"] = qty
            row["ordered"] = 0
            row["final_stock"] = ""
            row["target_stock"] = ""
            rows.append(row)
        pd.DataFrame(rows, columns=ML_COLUMNS).to_csv(ML_DATASET_PATH, index=False)
        return

    df = pd.read_csv(ML_DATASET_PATH, dtype=str)
    # Κρατά ΜΟΝΟ τα σωστά columns, προσθέτει αν λείπει, πετάει ό,τι περιττό
    for col in ML_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[ML_COLUMNS]

    for gas_type, qty in returns.items():
        mask = (df["date"] == date_str) & (df["gas_type"] == gas_type)
        if mask.any():
            df.loc[mask, "returned"] = str(qty)
        else:
            new_row = dict.fromkeys(ML_COLUMNS, "")
            new_row["date"] = date_str
            new_row["gas_type"] = gas_type
            new_row["manual_order"] = 0
            new_row["returned"] = str(qty)
            new_row["ordered"] = 0
            new_row["final_stock"] = ""
            new_row["target_stock"] = ""
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df = df[ML_COLUMNS]
    df.to_csv(ML_DATASET_PATH, index=False)

# --- Telegram Conversation Flow ---

async def start_linde_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['returns'] = {}
    context.user_data['current_index'] = 0
    await update.message.reply_text(
        "🔄 Καταγραφή επιστροφών προς Linde.\nΠόσες φιάλες επιστράφηκαν για:"
    )
    return await ask_next_gas(update, context)

async def ask_next_gas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data['current_index']
    if index >= len(GAS_TYPES):
        return await finish_feedback(update, context)
    gas = GAS_TYPES[index]
    await update.message.reply_text(f"{gas};\n(γράψε 0 αν δεν επιστράφηκαν)")
    return GET_RETURN

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

async def finish_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().strftime("%Y-%m-%d")
    returns = context.user_data['returns']
    # Καταγραφή στο linde_feedback.csv (ιστορικό)
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
    # Ενημέρωση linde_ml_dataset.csv
    update_ml_returned(today, returns)
    await update.message.reply_text("✅ Οι επιστροφές καταγράφηκαν και ενημερώθηκε το ML dataset.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def cancel_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Η καταγραφή ακυρώθηκε.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

linde_feedback_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("lindeFB", start_linde_feedback)],
    states={
        GET_RETURN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_return)],
    },
    fallbacks=[CommandHandler("cancel", cancel_feedback)]
)
