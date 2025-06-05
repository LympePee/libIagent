# gsheet_utils.py

import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from config import GOOGLE_SERVICE_ACCOUNT_FILE, GOOGLE_SPREADSHEET_ID

# Σύνδεση με Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
credentials = Credentials.from_service_account_file(
    GOOGLE_SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)
service = build('sheets', 'v4', credentials=credentials)

def update_google_sheet(dataframe: pd.DataFrame, sheet_name: str = "Sheet1"):
    sheet = service.spreadsheets()

    # Λήψη λίστας υπαρχόντων φύλλων
    spreadsheet = sheet.get(spreadsheetId=GOOGLE_SPREADSHEET_ID).execute()
    sheet_names = [s['properties']['title'] for s in spreadsheet['sheets']]

    # Αν δεν υπάρχει το φύλλο, το δημιουργούμε
    if sheet_name not in sheet_names:
        print(f"📄 Δημιουργία νέου φύλλου: {sheet_name}")
        body = {
            "requests": [
                {
                    "addSheet": {
                        "properties": {"title": sheet_name}
                    }
                }
            ]
        }
        sheet.batchUpdate(spreadsheetId=GOOGLE_SPREADSHEET_ID, body=body).execute()

    # Μετατροπή του DataFrame σε λίστα λιστών
    data = [dataframe.columns.tolist()] + dataframe.values.tolist()

    # Καθαρισμός προηγούμενου περιεχομένου
    sheet.values().clear(spreadsheetId=GOOGLE_SPREADSHEET_ID, range=f"{sheet_name}!A1").execute()

    # Ενημέρωση φύλλου
    sheet.values().update(
        spreadsheetId=GOOGLE_SPREADSHEET_ID,
        range=f"{sheet_name}!A1",
        valueInputOption="RAW",
        body={"values": data}
    ).execute()

    print(f"✅ Τα δεδομένα ανέβηκαν στο φύλλο '{sheet_name}' του Google Sheet.")
