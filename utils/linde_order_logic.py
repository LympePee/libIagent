import os
import pandas as pd
from datetime import datetime
from config import GMAIL_USER, CC_EMAIL

EMAIL_HISTORY = "logs/email_history.csv"
ML_DATASET = "logs/linde_ml_dataset.csv"

# === Email content ===
def create_linde_email_content(order_dict):
    header = "Αγαπητοί,\n\nΠαρακαλώ δείτε παρακάτω την παραγγελία αερίων του νοσοκομείου.\n"
    table_lines = [
        f"- {gas_type}: {qty} φιάλες"
        for gas_type, qty in order_dict.items()
    ]
    footer = "\n\nΜε εκτίμηση,\nΤεχνική Υπηρεσία\n"
    return header + "\n".join(table_lines) + footer

# === Rule-based λογική για αποστολή παραγγελίας ===
def rule_based_linde_order():
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # === Βήμα 1: Έλεγχος αν έχει ήδη σταλεί email σήμερα προς Linde ===
    if os.path.exists(EMAIL_HISTORY):
        df_email = pd.read_csv(EMAIL_HISTORY)
        df_email["timestamp"] = pd.to_datetime(df_email["timestamp"])

        sent_today = df_email[
            (df_email["timestamp"].dt.date == now.date())
            & (df_email["email_type"] == "linde")
        ]
        if not sent_today.empty:
            return {"skipped": True, "ordered": {}, "note": "Ήδη στάλθηκε παραγγελία σήμερα."}

    # === Βήμα 2: Φόρτωση δεδομένων και υπολογισμός παραγγελίας ===
    if not os.path.exists(ML_DATASET):
        return {"skipped": True, "ordered": {}, "note": "Δεν βρέθηκε το αρχείο ML dataset."}

    df = pd.read_csv(ML_DATASET)
    df["date"] = pd.to_datetime(df["date"])
    recent = df.sort_values(by="date", ascending=False).groupby("gas_type").head(2)

    orders = {}
    for gas_type, group in recent.groupby("gas_type"):
        total_returned = group["returned"].sum()
        current_stock = group.iloc[0]["stock"] if not group.empty else 0
        ideal_stock = group.iloc[0]["ideal_stock"]

        to_order = max(0, min(total_returned, ideal_stock - current_stock))
        if to_order > 0:
            orders[gas_type] = int(to_order)

    if not orders:
        return {"skipped": True, "ordered": {}, "note": "Δεν απαιτείται παραγγελία."}

    # === Βήμα 3: Σύνταξη email ===
    subject = f"Παραγγελία αερίων - {today_str}"
    body = create_linde_email_content(orders)

    email_data = {
        "from": GMAIL_USER,
        "to": "gr.lindehealthcare@linde.com",
        "cc": CC_EMAIL,
        "subject": subject,
        "body": body
    }

    return {"skipped": False, "ordered": orders, "email": email_data, "note": ""}
