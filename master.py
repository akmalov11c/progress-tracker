import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# === НАСТРОЙКИ ===
CSV_FILE = "all_periods_progress.csv"  # наш CSV с прогрессом
GOOGLE_SHEET_NAME = "Data science - progress"  # название Google Sheet'а

# === ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS ===
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
gc = gspread.authorize(creds)
# Открываем таблицу
sheet = gc.open(GOOGLE_SHEET_NAME).sheet1

# Читаем CSV
df = pd.read_csv(CSV_FILE)

# Загружаем данные в Google Sheets
sheet.clear()  # очищаем старое содержимое
df = df.fillna('')  # или df.fillna(0), если хочешь числом
sheet.update([df.columns.values.tolist()] + df.values.tolist())

print("✅ Таблица успешно обновлена в Google Sheets!")
