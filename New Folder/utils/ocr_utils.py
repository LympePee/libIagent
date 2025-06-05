import pytesseract
import pandas as pd
import cv2
import numpy as np
from PIL import Image
import re

# --- OCR Setup ---
# Αν έχεις πρόβλημα στο Linux, μπορεί να χρειαστείς το path του tesseract π.χ.:
# pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

def preprocess_image(image_path):
    """
    Βελτιστοποιεί την εικόνα για καλύτερο OCR.
    """
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    return thresh

def extract_text_from_image(image_path):
    """
    Εκτελεί OCR και επιστρέφει ακατέργαστο κείμενο.
    """
    preprocessed_img = preprocess_image(image_path)
    text = pytesseract.image_to_string(preprocessed_img, lang='ell+eng')
    return text

def parse_text_to_table(text):
    """
    Προσπαθεί να μετατρέψει απλό κείμενο σε πίνακα (DataFrame).
    Για ειδικές φόρμες (π.χ. όπως της αποστολής ΕΑΥΜ), προσαρμόζεται.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    parsed_data = []

    for line in lines:
        parts = re.split(r"\s{2,}|	", line)
        if len(parts) >= 2:
            parsed_data.append(parts)

    if parsed_data:
        max_cols = max(len(row) for row in parsed_data)
        clean_data = [row + [""] * (max_cols - len(row)) for row in parsed_data]
        df = pd.DataFrame(clean_data)
        return df
    else:
        return pd.DataFrame([['OCR failed or no structured data found']])

def image_to_dataframe(image_path):
    """
    Από εικόνα → OCR → DataFrame
    """
    text = extract_text_from_image(image_path)
    df = parse_text_to_table(text)
    return df

# === Δημόσια συνάρτηση για import από handlers/autoxl_handler.py ===
process_uploaded_image = image_to_dataframe
