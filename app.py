import streamlit as st
import pandas as pd
import requests
import json
import os
import io
import shutil
import re
from datetime import datetime, timedelta
from github import Github

# ===============================
# 🔐 إعدادات المستخدمين والجلسات
# ===============================
USERS_FILE = "users.json"       # يحتوي على users {"admin":{"password":"123"}, "user1":{"password":"abc"}}
STATE_FILE = "state.json"
SESSION_DURATION = timedelta(minutes=10)
MAX_ACTIVE_USERS = 2

# ===============================
# 📂 إعداد GitHub و Excel
# ===============================
REPO_NAME = "mahmedabdallh123/BELYARN"
BRANCH = "main"
FILE_PATH = "Machine_Service_Lookup.xlsx"
LOCAL_FILE = "Machine_Service_Lookup.xlsx"
GITHUB_EXCEL_URL = f"https://raw.githubusercontent.com/{REPO_NAME}/{BRANCH}/{FILE_PATH}"

# ===============================
# 🧩 دوال مساعدة
# ===============================
def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        st.error("❌ خطأ في ملف users.json")
        st.stop()

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

def load_state():
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

def cleanup_sessions(state):
    now = datetime.now()
    changed = False
    for user, info in state.items():
        if info.get("active") and "login_time" in info:
            try:
                login_time = datetime.fromisoformat(info["login_time"])
                if now - login_time > SESSION_DURATION:
                    info["active"] = False
                    info.pop("login_time", None)
                    changed = True
            except:
                info["active"] = False
                changed = True
    if changed:
        save_state(state)
    return state

def remaining_time(state, username):
    if not username or username not in state:
        return None
    info = state.get(username)
    if not info or not info.get("active"):
        return None
    try:
        lt = datetime.fromisoformat(info["login_time"])
        remaining = SESSION_DURATION - (datetime.now() - lt)
        if remaining.total_seconds() <= 0:
            return None
        return remaining
    except:
        return None

def logout_action():
    state = load_state()
    username = st.session_state.get("username")
    if username and username in state:
        state[username]["active"] = False
        state[username].pop("login_time", None)
        save_state(state)
    st.session_state.clear()
    st.rerun()

def login_ui():
    users = load_users()
    state = cleanup_sessions(load_state())
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None

    st.title("🔐 تسجيل الدخول - Bail Yarn")
    username_input = st.selectbox("👤 اختر المستخدم", list(users.keys()))
    password = st.text_input("🔑 كلمة المرور", type="password")

    active_users = [u for u, v in state.items() if v.get("active")]
    active_count = len(active_users)
    st.caption(f"🔒 المستخدمون النشطون الآن: {active_count} / {MAX_ACTIVE_USERS}")

    if not st.session_state.logged_in:
        if st.button("تسجيل الدخول"):
            if username_input in users and users[username_input]["password"] == password:
                if username_input == "admin":
                    pass
                elif username_input in active_users:
                    st.warning("⚠ هذا المستخدم مسجل دخول بالفعل.")
                    return False
                elif active_count >= MAX_ACTIVE_USERS:
                    st.error("🚫 الحد الأقصى للمستخدمين المتصلين حالياً.")
                    return False
                state[username_input] = {"active": True, "login_time": datetime.now().isoformat()}
                save_state(state)
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.success(f"✅ تم تسجيل الدخول: {username_input}")
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة.")
        return False
    else:
        username = st.session_state.username
        st.success(f"✅ مسجل الدخول كـ: {username}")
        rem = remaining_time(state, username)
        if rem:
            mins, secs = divmod(int(rem.total_seconds()), 60)
            st.info(f"⏳ الوقت المتبقي: {mins:02d}:{secs:02d}")
        else:
            st.warning("⏰ انتهت الجلسة، سيتم تسجيل الخروج.")
            logout_action()
        if st.button("🚪 تسجيل الخروج"):
            logout_action()
        return True

# ===============================
# 🔄 GitHub & Excel Functions
# ===============================
def fetch_from_github():
    try:
        response = requests.get(GITHUB_EXCEL_URL, stream=True, timeout=10)
        response.raise_for_status()
        with open(LOCAL_FILE, "wb") as f:
            shutil.copyfileobj(response.raw, f)
        st.cache_data.clear()
        st.session_state["last_update"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        st.success("✅ تم تحديث البيانات من GitHub بنجاح وتم مسح الكاش.")
    except Exception as e:
        st.error(f"⚠ فشل التحديث من GitHub: {e}")

@st.cache_data(show_spinner=False)
def load_all_sheets():
    if not os.path.exists(LOCAL_FILE):
        st.error("❌ الملف المحلي غير موجود. برجاء الضغط على زر التحديث أولًا.")
        return None
    sheets = pd.read_excel(LOCAL_FILE, sheet_name=None)
    for name, df in sheets.items():
        df.columns = df.columns.str.strip()
    return sheets

# ===============================
# 🛠 Excel Edit Module (Admin)
# ===============================
def show_edit_page():
    st.title("🛠 CMMS - تعديل وإضافة بيانات (GitHub)")
    sheets = load_all_sheets()
    if not sheets:
        return

    sheet_name = st.selectbox("اختر الشيت:", list(sheets.keys()))
    df = sheets[sheet_name].astype(str)
    edited_df = st.data_editor(df, num_rows="dynamic")
    if st.button("💾 حفظ التعديلات"):
        sheets[sheet_name] = edited_df.astype(object)
        save_local_excel_and_push(sheets)

def save_local_excel_and_push(sheets_dict, commit_message="Update from Streamlit"):
    import openpyxl
    with pd.ExcelWriter(LOCAL_FILE, engine="openpyxl") as writer:
        for name, sh in sheets_dict.items():
            try:
                sh.to_excel(writer, sheet_name=name, index=False)
            except Exception:
                sh.astype(object).to_excel(writer, sheet_name=name, index=False)

    try:
        token = st.secrets["github"]["token"]
    except:
        st.error("🔒 GitHub token not found in Streamlit secrets.")
        return False

    g = Github(token)
    repo = g.get_repo(REPO_NAME)

    with open(LOCAL_FILE, "rb") as f:
        content = f.read()

    try:
        contents = repo.get_contents(FILE_PATH, ref=BRANCH)
        repo.update_file(path=FILE_PATH, message=commit_message, content=content, sha=contents.sha, branch=BRANCH)
    except Exception as e:
        st.error(f"⚠ فشل رفع الملف إلى GitHub: {e}")
        return False

    st.cache_data.clear()
    st.success("✅ تم الحفظ والرفع على GitHub بنجاح.")
    return True

# ===============================
# 🖥 Main
# ===============================
if not st.session_state.get("logged_in"):
    if not login_ui():
        st.stop()
else:
    tabs = ["📋 عرض الحالة"]
    if st.session_state.get("username") == "admin":
        tabs.append("🛠 تعديل البيانات (Admin)")

    selected_tab = st.tabs(tabs)

    # ---------- Tab 1: عرض الحالة ----------
    with selected_tab[0]:
        if st.button("🔄 تحديث البيانات من GitHub"):
            fetch_from_github()

        all_sheets = load_all_sheets()
        card_num = st.number_input("رقم الماكينة:", min_value=1, step=1)
        current_tons = st.number_input("عدد الأطنان الحالية:", min_value=0, step=100)

        if st.button("عرض الحالة") and all_sheets:
            st.write("✅ هنا سيتم استدعاء دالة check_machine_status(card_num, current_tons, all_sheets)")
            # يمكن دمج دالة check_machine_status كما في كودك السابق

    # ---------- Tab 2: تعديل البيانات ----------
    if st.session_state.get("username") == "admin":
        with selected_tab[1]:
            show_edit_page()
