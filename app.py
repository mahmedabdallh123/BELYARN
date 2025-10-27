import streamlit as st
import pandas as pd
import requests
import os
from github import Github

# ===============================
# 📂 إعدادات الملف
# ===============================
REPO_NAME = "mahmedabdallh123/BELYARN"
BRANCH = "main"
FILE_PATH = "Machine_Service_Lookup.xlsx"
LOCAL_FILE = "Machine_Service_Lookup.xlsx"

# ===============================
# تحميل Excel من GitHub
# ===============================
def fetch_excel():
    if not os.path.exists(LOCAL_FILE):
        st.info("📥 تحميل الملف من GitHub...")
        try:
            url = f"https://raw.githubusercontent.com/{REPO_NAME}/{BRANCH}/{FILE_PATH}"
            r = requests.get(url)
            r.raise_for_status()
            with open(LOCAL_FILE, "wb") as f:
                f.write(r.content)
            st.success("✅ تم تحميل الملف بنجاح.")
        except Exception as e:
            st.error(f"⚠ فشل تحميل الملف: {e}")
            st.stop()

# ===============================
# تحميل الشيتات
# ===============================
@st.cache_data
def load_sheets():
    fetch_excel()
    sheets = pd.read_excel(LOCAL_FILE, sheet_name=None)
    for name, df in sheets.items():
        df.columns = df.columns.str.strip()
    return sheets

# ===============================
# رفع الملف إلى GitHub
# ===============================
def push_to_github(local_file, commit_message="Update Excel via Streamlit"):
    token = st.secrets["github"]["token"]
    g = Github(token)
    repo = g.get_repo(REPO_NAME)

    with open(local_file, "rb") as f:
        content = f.read()

    try:
        contents = repo.get_contents(FILE_PATH, ref=BRANCH)
        repo.update_file(
            path=FILE_PATH,
            message=commit_message,
            content=content,
            sha=contents.sha,
            branch=BRANCH
        )
    except Exception as e:
        st.error(f"⚠ فشل رفع الملف إلى GitHub: {e}")
        return False

    st.success("✅ تم رفع الملف إلى GitHub بنجاح!")
    return True

# ===============================
# الواجهة
# ===============================
st.title("🛠 CMMS - تعديل وإضافة بيانات (GitHub)")

sheets = load_sheets()

tab1, tab2, tab3 = st.tabs(["عرض وتعديل شيت", "إضافة صف جديد", "إضافة عمود جديد"])

# ===============================
# Tab 1: تعديل البيانات
# ===============================
with tab1:
    st.subheader("✏️ تعديل البيانات")
    sheet_name = st.selectbox("اختر الشيت:", list(sheets.keys()))
    df = sheets[sheet_name]

    edited_df = st.data_editor(df, num_rows="dynamic")
    if st.button("💾 حفظ التعديلات", key="save_edit"):
        sheets[sheet_name] = edited_df
        with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
            for name, sh in sheets.items():
                sh.to_excel(writer, sheet_name=name, index=False)
        push_to_github(LOCAL_FILE, commit_message=f"Edit sheet {sheet_name}")

# ===============================
# Tab 2: إضافة صف جديد
# ===============================
with tab2:
    st.subheader("➕ إضافة صف جديد")
    sheet_name_add = st.selectbox("اختر الشيت لإضافة صف:", list(sheets.keys()), key="add_sheet")
    df_add = sheets[sheet_name_add]

    new_data = {}
    for col in df_add.columns:
        new_data[col] = st.text_input(f"{col}", key=f"add_{col}")

    if st.button("💾 إضافة الصف الجديد"):
        df_add = df_add.append(new_data, ignore_index=True)
        sheets[sheet_name_add] = df_add
        with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
            for name, sh in sheets.items():
                sh.to_excel(writer, sheet_name=name, index=False)
        push_to_github(LOCAL_FILE, commit_message=f"Add new row to {sheet_name_add}")

# ===============================
# Tab 3: إضافة عمود جديد
# ===============================
with tab3:
    st.subheader("🆕 إضافة عمود جديد")
    sheet_name_col = st.selectbox("اختر الشيت لإضافة عمود:", list(sheets.keys()), key="add_col_sheet")
    df_col = sheets[sheet_name_col]

    new_col_name = st.text_input("اسم العمود الجديد:")
    default_value = st.text_input("القيمة الافتراضية لكل الصفوف (اختياري):", "")

    if st.button("💾 إضافة العمود الجديد"):
        if new_col_name:
            df_col[new_col_name] = default_value
            sheets[sheet_name_col] = df_col
            with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
                for name, sh in sheets.items():
                    sh.to_excel(writer, sheet_name=name, index=False)
            push_to_github(LOCAL_FILE, commit_message=f"Add new column '{new_col_name}' to {sheet_name_col}")
        else:
            st.warning("⚠ الرجاء إدخال اسم العمود الجديد.")
