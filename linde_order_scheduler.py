import os
import pandas as pd
from datetime import datetime
import schedule
import threading
import time
from utils.linde_order_utils import (
    send_linde_order, get_next_linde_delivery_date, check_if_order_sent_today,
    ML_DATASET, ML_COLUMNS
)

def compute_auto_order():
    """Υπολογίζει την ιδανική αυτόματη παραγγελία για κάθε gas_type."""
    if not os.path.exists(ML_DATASET):
        print("⚠️ Δεν υπάρχει ML dataset.")
        return {}

    df = pd.read_csv(ML_DATASET)
    df = df[ML_COLUMNS]
    today = datetime.now().strftime("%Y-%m-%d")

    orders = {}
    for gas_type in df["gas_type"].unique():
        sub = df[df["gas_type"] == gas_type].sort_values("date", ascending=False)

        # Αν δεν υπάρχει target_stock ή final_stock, skip
        try:
            target = int(sub["target_stock"].dropna().iloc[0])
        except Exception:
            continue

        try:
            # Τελευταίο final_stock που υπάρχει
            last_stock = int(sub["final_stock"].dropna().iloc[0])
        except Exception:
            last_stock = 0

        # Πόσες επέστρεψες στις 2 τελευταίες επιστροφές;
        last_returns = sub["returned"].dropna().astype(int).tolist()[:2]
        sum_returned = sum(last_returns) if last_returns else 0

        # Πόσες λείπουν για να φτάσεις το target (χωρίς να ξεπερνάς returns/target)
        need = max(0, min(sum_returned, target - last_stock))
        if need > 0:
            orders[gas_type] = need

    return orders

def auto_linde_job():
    print("⏰ Auto Linde Check:", datetime.now())
    if check_if_order_sent_today():
        print("➡️ Έχει ήδη σταλεί παραγγελία σήμερα. Τέλος.")
        return

    orders = compute_auto_order()
    if not orders:
        print("➡️ Δεν απαιτείται παραγγελία σήμερα.")
        return

    delivery_date = get_next_linde_delivery_date()
    print(f"📤 Αυτόματη παραγγελία: {orders}")
    send_linde_order(orders, delivery_date, mode="auto", send_email_flag=True)

def start_linde_scheduler():
    """Τρέχει το schedule σε thread."""
    schedule.every().monday.at("11:30").do(auto_linde_job)
    schedule.every().wednesday.at("11:30").do(auto_linde_job)

    def run_loop():
        while True:
            schedule.run_pending()
            time.sleep(60)

    t = threading.Thread(target=run_loop, daemon=True)
    t.start()
    print("✅ Linde auto scheduler ξεκίνησε.")

# --- Αν θες το τρέχεις από εδώ ή το κάνεις import στο main σου:
if __name__ == "__main__":
    start_linde_scheduler()
    while True:
        time.sleep(100)
