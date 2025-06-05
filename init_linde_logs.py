import pandas as pd
import os

# Φτιάξε τους φακέλους αν δεν υπάρχουν
os.makedirs("logs", exist_ok=True)

# Τα gas_types σου και τα default target stock (αν θες)
GAS_TYPES = [
    "Oxygen 5L (LIV)",
    "Oxygen 10L",
    "CO2 10L",
    "CO2 50L",
    "Medical Air 50L"
]
TARGET_STOCK = {
    "Oxygen 5L (LIV)": 16,
    "Oxygen 10L": 0,
    "CO2 50L": 5,
    "CO2 10L": 4,
    "Medical Air 50L": 15
}

# --- 1. linde_ml_dataset.csv ---
ml_columns = ["date", "gas_type", "manual_order", "returned", "ordered", "final_stock", "target_stock"]
# Δημιουργεί μόνο τα headers (κενό csv)
pd.DataFrame(columns=ml_columns).to_csv("logs/linde_ml_dataset.csv", index=False)

# --- 2. linde_feedback.csv ---
fb_columns = ["date"] + GAS_TYPES
pd.DataFrame(columns=fb_columns).to_csv("logs/linde_feedback.csv", index=False)

# --- 3. (optional) linde_stock_config.json για εύκολη αλλαγή στο μέλλον ---
import json
with open("logs/linde_stock_config.json", "w", encoding="utf-8") as f:
    json.dump(TARGET_STOCK, f, indent=2, ensure_ascii=False)

print("✅ Τα αρχεία αρχικοποιήθηκαν ΣΩΣΤΑ!")
