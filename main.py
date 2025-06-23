import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import os

ID_COLUMN = "Name"
PROGRESS_COLUMN = "Progress %"
HISTORY_FILE = "all_periods_progress.xlsx"

# ==== FUNCTIONS ====
def read_excel_safely(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        raise ValueError(f"❌ Failed to read Excel file: {e}")

    if ID_COLUMN not in df.columns or PROGRESS_COLUMN not in df.columns:
        raise ValueError(f"❌ '{ID_COLUMN}' and '{PROGRESS_COLUMN}' columns are required.")

    return df

def process_file(df, label, total_tasks):
    df = df.copy()
    df[PROGRESS_COLUMN] = df[PROGRESS_COLUMN].astype(str).str.replace('%', '').astype(float)
    df[f"{label}_Tasks_Completed"] = (df[PROGRESS_COLUMN] / 100 * total_tasks).round().astype(int)
    return df[[ID_COLUMN, f"{label}_Tasks_Completed"]]

# ==== FRONTEND ====
st.set_page_config(page_title="Unicraft Progress Tracker", layout="centered")
st.title("Unicraft Progress Tracker")

with st.form("progress_form"):
    st.subheader("📁 XLSX fayllarni yuklang")
    file1 = st.file_uploader("Birinchi davr fayli (masalan, Aprel)", type="xlsx", key="f1")
    file2 = st.file_uploader("Ikkinchi davr fayli (masalan, May)", type="xlsx", key="f2")
    month = st.text_input("📅 Ikkinchi davr nomi (masalan, May)")
    course_name = st.text_input("📘 Kurs nomi (o'zingiz uchun)")
    total_tasks = st.number_input("🔢 Umumiy vazifalar soni", min_value=1, value=50)
    submit_btn = st.form_submit_button("🔍 Taqqoslash va Hisobot yaratish")

if submit_btn and file1 and file2 and month:
    try:
        df1 = read_excel_safely(file1)
        df2 = read_excel_safely(file2)
    except Exception as e:
        st.error(f"🚨 Error reading files: {e}")
        st.stop()

    df1 = process_file(df1, "First", total_tasks)
    df2 = process_file(df2, month, total_tasks)

    df = pd.merge(df1, df2, on=ID_COLUMN, how='outer')

    def status(row):
        if pd.isna(row.get("First_Tasks_Completed")):
            return "New"
        elif pd.isna(row.get(f"{month}_Tasks_Completed")):
            return "Completed Course"
        return "Active"

    df["Status"] = df.apply(status, axis=1)
    df["Growth"] = df[f"{month}_Tasks_Completed"] - df["First_Tasks_Completed"]
    df = df.fillna("")

    for col in [f"{month}_Tasks_Completed", "First_Tasks_Completed", "Growth"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    result_filename = f"progress_for_{month.lower()}.xlsx"
    df.to_excel(result_filename, index=False)

    st.success(f"✅ Report generated: {result_filename}")
    st.dataframe(df, use_container_width=True)
    st.download_button(
        label="📅 Download Report",
        data=open(result_filename, "rb"),
        file_name=result_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # === Append to Google Sheets ===
    df_history = df[[ID_COLUMN, "Growth", "Status"]].copy()
    df_history[month] = df_history["Growth"].apply(
        lambda x: int(x) if isinstance(x, (int, float)) else x
    )
    df_history = df_history.drop(columns=["Growth"])

    try:
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        gc = gspread.authorize(creds)

        SHEET_ID = "1uYI9gbLG0DRyYL9vDsD-hW3A_tRRaFwv-nfJjbgA1Qs"
        SHEET_NAME = "Data science - progress"
        sheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

        data = sheet.get_all_values()
        df_existing = pd.DataFrame(data[1:], columns=data[0]) if data else pd.DataFrame()

        df_existing[ID_COLUMN] = df_existing[ID_COLUMN].astype(str).str.strip()
        df_history[ID_COLUMN] = df_history[ID_COLUMN].astype(str).str.strip()

        df_combined = pd.merge(df_existing, df_history, on=ID_COLUMN, how="outer") if ID_COLUMN in df_existing.columns else df_history

        df_combined = df_combined.fillna("")
        df_combined = df_combined.applymap(lambda x: ''.join(c for c in str(x) if c.isprintable()) if isinstance(x, str) else x)

        sheet.update([df_combined.columns.tolist()] + df_combined.values.tolist())
        st.success("\u2705 Google Sheet successfully updated!")

    except Exception as e:
        st.error(f"❌ Failed to update Google Sheet: {e}")
