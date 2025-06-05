import os
import pandas as pd
from datetime import datetime, timedelta
from utils.mailer import send_email
from utils.email_log_utils import log_email

ML_DATASET = "logs/linde_ml_dataset.csv"
EMAIL_HISTORY = "logs/email_history.csv"

# Η ΜΟΝΗ επιτρεπτή δομή/σειρά στηλών
ML_COLUMNS = [
    "date",
    "gas_type",
    "manual_order",
    "returned",
    "ordered",
    "final_stock",
    "target_stock"
]

# Συμβατικά aliases για τα gas_types (ό,τι γράψεις, θα αποθηκευτεί ως το "καθαρό" όνομα)
GAS_ALIASES = {
    "O2 Liv 5L": "Oxygen 5L (LIV)",
    "Oxygen 5L (LIV)": "Oxygen 5L (LIV)",
    "O2 10L": "Oxygen 10L",
    "Oxygen 10L": "Oxygen 10L",
    "CO2 10L": "CO2 10L",
    "CO2 50L": "CO2 50L",
    "Air 50L": "Medical Air 50L",
    "Medical Air 50L": "Medical Air 50L"
}

DEFAULT_TARGET_STOCK = {
    "Oxygen 5L (LIV)": 16,
    "Oxygen 10L": None,         # Μόνο επιστροφές (ειδική λογική)
    "CO2 50L": 5,
    "CO2 10L": 4,
    "Medical Air 50L": 15
}

def normalize_gas_type(gas):
    return GAS_ALIASES.get(gas.strip(), gas.strip())

def get_next_linde_delivery_date(base_date=None):
    """Επιστρέφει την επόμενη Τρίτη ή Πέμπτη από τη δοσμένη ημερομηνία."""
    if base_date is None:
        base_date = datetime.now()
    weekday = base_date.weekday()
    days_to_tuesday = (1 - weekday + 7) % 7
    days_to_thursday = (3 - weekday + 7) % 7
    days_to_next = min(days_to_tuesday, days_to_thursday)
    return base_date + timedelta(days=days_to_next)

def check_if_order_sent_today():
    """Ελέγχει αν έχει σταλεί παραγγελία Linde σήμερα."""
    if not os.path.exists(EMAIL_HISTORY):
        return False
    df = pd.read_csv(EMAIL_HISTORY, parse_dates=["timestamp"])
    today = datetime.now().date()
    sent_today = df[
        (df["email_type"] == "linde") &
        (df["timestamp"].dt.date == today)
    ]
    return not sent_today.empty

def get_target_stock(gas_type):
    """Επιστρέφει το target stock, από το dataset (αν υπάρχει γραμμή με τιμή), αλλιώς από default."""
    gas_type = normalize_gas_type(gas_type)
    if not os.path.exists(ML_DATASET):
        return DEFAULT_TARGET_STOCK.get(gas_type, None)
    df = pd.read_csv(ML_DATASET)
    df = df[df["gas_type"] == gas_type]
    df = df[pd.notnull(df["target_stock"])]
    if not df.empty:
        try:
            val = int(df.sort_values("date", ascending=False).iloc[0]["target_stock"])
            return val
        except Exception:
            return DEFAULT_TARGET_STOCK.get(gas_type, None)
    return DEFAULT_TARGET_STOCK.get(gas_type, None)

def update_ml_dataset(order_dict, delivery_date, mode="auto"):
    """
    Προσθέτει νέες γραμμές στο ML DATASET, διασφαλίζοντας ΣΩΣΤΗ σειρά/στήλες.
    - order_dict: dict {"Oxygen 5L (LIV)": 5, ...}
    - mode: "auto" ή "manual"
    """
    today = datetime.now().strftime("%Y-%m-%d")
    rows = []
    for gas_type, qty in order_dict.items():
        gas_type_clean = normalize_gas_type(gas_type)
        row = dict.fromkeys(ML_COLUMNS, None)
        row["date"] = today
        row["gas_type"] = gas_type_clean
        row["manual_order"] = qty if mode == "manual" else 0
        row["returned"] = 0
        row["ordered"] = qty
        row["final_stock"] = None
        row["target_stock"] = get_target_stock(gas_type_clean)
        rows.append(row)

    df_new = pd.DataFrame(rows, columns=ML_COLUMNS)
    if os.path.exists(ML_DATASET):
        df_old = pd.read_csv(ML_DATASET)
        # Προσθήκη τυχόν λειπόντων στηλών
        for col in ML_COLUMNS:
            if col not in df_old.columns:
                df_old[col] = None
        df_old = df_old[ML_COLUMNS]
        df_final = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_final = df_new
    df_final.to_csv(ML_DATASET, index=False)

def send_linde_order(order_dict, delivery_date, mode="auto", send_email_flag=True):
    """
    Κεντρική συνάρτηση: στέλνει email, κάνει logging και ενημερώνει ML dataset.
    """
    from config import GMAIL_USER, CC_EMAIL
    recipient = "gr.lindehealthcare@linde.com"
    subject = f"Παραγγελία αερίων - {delivery_date.strftime('%A %d/%m/%Y')}"
    body = "Αγαπητοί,\n\nΠαρακαλώ δείτε παρακάτω την παραγγελία αερίων του νοσοκομείου.\n"
    for k, v in order_dict.items():
        body += f"- {normalize_gas_type(k)}: {v} φιάλες\n"
    body += "\nΜε εκτίμηση,\nΤεχνική Υπηρεσία\n"

    success = False
    if send_email_flag:
        success = send_email(
            GMAIL_USER, recipient, CC_EMAIL, subject, body
        )

    log_email(
        email_type="linde",
        subject=subject,
        recipients=[recipient, CC_EMAIL],
        status="sent" if success else "failed",
        body=body
    )

    update_ml_dataset(order_dict, delivery_date, mode)
    return success
