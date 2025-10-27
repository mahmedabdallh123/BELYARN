import streamlit as st
import pandas as pd
import json
import io
import os
import requests
from datetime import datetime, timedelta

# ===============================
# إعدادات التطبيق
# ===============================
st.set_page_config(page_title="CMMS Service System", layout="wide")

GITHUB_EXCEL_URL = "https://raw.githubusercontent.com/USERNAME/REPO/main/Machine_Service_Lookup.xlsx"
GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxxx"  # ضع التوكن بتاعك هنا

# ===============================
# إدارة المستخدمين والجلسات
# ===============================
USERS = {
    "admin": {"password": "1234", "role": "admin"},
    "user1": {"password": "1111", "role": "user"},
    "user2": {"password": "2222", "role": "user"}
}

SESSION_TIMEOUT = 60 * 30  # 30 دقيقة

def login():
    st.sidebar.header("🔐 تسجيل الدخول")
    username = st.sidebar.text_input("اسم المستخدم")
    password = st.sidebar.text_input("كلمة المرور", type="password")
    login_btn = st.sidebar.button("تسجيل الدخول")

    if login_btn:
        if username in USERS and USERS[username]["password"] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = USERS[username]["role"]
            st.session_state["login_time"] = datetime.now()
            st.sidebar.success("✅ تم تسجيل الدخول بنجاح")
            st.rerun()
        else:
            st.sidebar.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")

def check_session():
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        login()
        st.stop()
    else:
        elapsed = (datetime.now() - st.session_state["login_time"]).total_seconds()
        if elapsed > SESSION_TIMEOUT:
            st.warning("⏳ انتهت الجلسة، يرجى تسجيل الدخول مرة أخرى.")
            for key in ["logged_in", "username", "role"]:
                st.session_state.pop(key, None)
            st.rerun()
        st.sidebar.info(f"👋 {st.session_state['username']} ({st.session_state['role']})")

        if st.sidebar.button("تسجيل الخروج"):
            for key in ["logged_in", "username", "role"]:
                st.session_state.pop(key, None)
            st.rerun()

# ===============================
# تحميل البيانات من GitHub
# ===============================
@st.cache_data
def fetch_from_github():
    try:
        df = pd.read_excel(GITHUB_EXCEL_URL, sheet_name=None)
        return df
    except Exception as e:
        st.error(f"❌ فشل تحميل الملف من GitHub: {e}")
        return None

def upload_to_github(df_dict):
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for sheet, data in df_dict.items():
                data.to_excel(writer, index=False, sheet_name=sheet)
        content = buffer.getvalue()

        repo = "USERNAME/REPO"  # ضع اسم الريبو هنا
        path = "Machine_Service_Lookup.xlsx"
        api_url = f"https://api.github.com/repos/{repo}/contents/{path}"

        # الحصول على SHA
        res = requests.get(api_url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        sha = res.json().get("sha", "")

        payload = {
            "message": "تحديث البيانات من Streamlit",
            "content": content.encode("base64"),
            "sha": sha
        }

        res = requests.put(api_url, headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }, data=json.dumps(payload))

        if res.status_code in [200, 201]:
            st.success("✅ تم رفع الملف بنجاح إلى GitHub.")
        else:
            st.error(f"فشل رفع الملف: {res.text}")
    except Exception as e:
        st.error(f"حدث خطأ أثناء رفع الملف: {e}")

# ===============================
# عرض حالة الماكينة
# ===============================
def check_machine_status(card_num, current_tons, all_sheets):
    sheet_name = list(all_sheets.keys())[0]
    df = all_sheets[sheet_name]
    if "Machine No" not in df.columns:
        st.error("❌ لا يوجد عمود باسم 'Machine No' في الملف.")
        return

    row = df[df["Machine No"] == card_num]
    if row.empty:
        st.warning("⚠ لم يتم العثور على الماكينة.")
        return

    st.write("### 🧾 تفاصيل الماكينة:")
    st.dataframe(row)

    try:
        last_tons = row.iloc[0]["Last Service Tons"]
        interval = row.iloc[0]["Interval Tons"]
        due = last_tons + interval

        if current_tons >= due:
            st.error("🔴 الخدمة مطلوبة الآن!")
        elif current_tons >= due - interval * 0.2:
            st.warning("🟡 اقترب موعد الخدمة.")
        else:
            st.success("🟢 الماكينة تعمل بشكل طبيعي.")
    except Exception:
        st.info("⚙ لم يتم العثور على بيانات كافية للحساب.")

# ===============================
# تعديل البيانات (للأدمن)
# ===============================
def show_edit_page(all_sheets):
    st.subheader("🛠 تعديل بيانات الإكسيل")
    sheet_name = st.selectbox("اختر الشيت:", list(all_sheets.keys()))
    df = all_sheets[sheet_name]
    st.dataframe(df, use_container_width=True)

    st.write("### ✏ تعديل صف")
    idx = st.number_input("رقم الصف:", min_value=0, max_value=len(df)-1, step=1)
    col = st.selectbox("العمود:", df.columns)
    new_val = st.text_input("القيمة الجديدة:")

    if st.button("حفظ التعديل"):
        df.at[idx, col] = new_val
        all_sheets[sheet_name] = df
        upload_to_github(all_sheets)

# ===============================
# تشغيل التطبيق
# ===============================
check_session()
tabs = ["📋 عرض الحالة"]
if st.session_state.get("role") == "admin":
    tabs.append("🛠 تعديل البيانات")

tab1, *rest = st.tabs(tabs)
with tab1:
    all_sheets = fetch_from_github()
    if all_sheets:
        card_num = st.number_input("رقم الماكينة:", min_value=1, step=1)
        current_tons = st.number_input("عدد الأطنان الحالية:", min_value=0, step=100)
        if st.button("عرض الحالة"):
            check_machine_status(card_num, current_tons, all_sheets)
    else:
        st.warning("⚠ الملف غير متاح حالياً.")

if st.session_state.get("role") == "admin":
    with rest[0]:
        all_sheets = fetch_from_github()
        if all_sheets:
            show_edit_page(all_sheets)
