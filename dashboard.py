import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QTextEdit, QMessageBox, QHBoxLayout
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

LOG_FILE = "logs/email_history.csv"

class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LibeBot Dashboard")
        self.setMinimumSize(600, 400)
        self.layout = QVBoxLayout()

        self.label_status = QLabel("🔍 Κατάσταση: Φόρτωση...")
        self.label_status.setStyleSheet("font-weight: bold; font-size: 16px")
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)

        # Buttons
        self.button_reload = QPushButton("🔄 Επαναφόρτωση")
        self.button_linde = QPushButton("🚀 Εκτέλεση Linde Handler")
        self.button_medic = QPushButton("🛠️ MedicPlan Handler")
        self.button_scor = QPushButton("🧼 Scoramida Handler")

        self.button_reload.clicked.connect(self.load_email_logs)
        self.button_linde.clicked.connect(lambda: self.run_handler("linde"))
        self.button_medic.clicked.connect(lambda: self.run_handler("medicplan"))
        self.button_scor.clicked.connect(lambda: self.run_handler("scoramida"))

        # Layouts
        self.layout.addWidget(self.label_status)
        self.layout.addWidget(self.text_area)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.button_reload)
        button_layout.addWidget(self.button_linde)
        button_layout.addWidget(self.button_medic)
        button_layout.addWidget(self.button_scor)
        self.layout.addLayout(button_layout)

        self.setLayout(self.layout)
        self.load_email_logs()

    def load_email_logs(self):
        if not os.path.exists(LOG_FILE):
            self.text_area.setText("Δεν βρέθηκε το αρχείο logs/email_history.csv")
            return

        try:
            df = pd.read_csv(LOG_FILE, header=None)
            df.columns = ["timestamp", "email_type", "subject", "recipients", "cc", "status", "preview"]
            df = df.tail(10)

            output = "".join([
                f"[{row['timestamp']}] - {row['email_type']}\n"
                f"  Προς: {row['recipients']}\n"
                f"  Θέμα: {row['subject']}\n"
                f"  Κατάσταση: {row['status']}\n\n"
                for _, row in df.iterrows()
            ])
            self.text_area.setText(output)

            # Check Linde status
            linde_df = df[df['email_type'] == 'linde']
            if not linde_df.empty:
                last_time = datetime.strptime(linde_df.iloc[-1]['timestamp'], "%Y-%m-%d %H:%M:%S")
                days_diff = (datetime.now() - last_time).days
                if days_diff > 4:
                    self.label_status.setText(f"⚠️ Τελευταία αποστολή στη Linde: πριν {days_diff} ημέρες!")
                    self.label_status.setStyleSheet("color: red; font-weight: bold; font-size: 16px")
                else:
                    self.label_status.setText(f"✅ Linde ενημερώθηκε πριν {days_diff} ημέρες")
                    self.label_status.setStyleSheet("color: green; font-weight: bold; font-size: 16px")
            else:
                self.label_status.setText("⚠️ Δεν έχει σταλεί ποτέ email στη Linde!")
                self.label_status.setStyleSheet("color: red; font-weight: bold; font-size: 16px")

        except Exception as e:
            self.text_area.setText(f"⚠️ Σφάλμα ανάγνωσης CSV: {e}")

    def run_handler(self, handler_name):
        try:
            os.system(f"xfce4-terminal -e 'bash -c \"source .venv/bin/activate && python -m handlers.{handler_name}_handler; exec bash\"'")
        except Exception as e:
            QMessageBox.critical(self, "Σφάλμα", f"Δεν ήταν δυνατή η εκτέλεση του handler '{handler_name}': {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec())
