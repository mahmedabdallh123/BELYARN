import streamlit as st
import pandas as pd
import json
import os
import io
import re
from datetime import datetime, timedelta

# ===============================
# 🔐 إعدادات المستخدمين والجلسات
# ===============================
USERS_FILE = "users.json"
STATE_FILE = "state.json"
SESSION_DURATION = timedelta(minutes=10)

# -------------------------------
# تحميل بيانات المستخدمين
# -------------------------------
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

# -------------------------------
# حفظ بيانات المستخدمين
# -------------------------------
def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# -------------------------------
# إنشاء مستخدم افتراضي admin
# -------------------------------
def ensure_admin():
    users = load_users()
    if "admin" not in users:
        users["admin"] = {"password": "1234", "role": "admin", "hall": "A"}
        save_users(users)
ensure_admin()

# -------------------------------
# تحميل حالة الجلسة
# -------------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

# -------------------------------
# حفظ حالة الجلسة
# -------------------------------
def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

# -------------------------------
# التحقق من الجلسة
# -------------------------------
def check_session(username):
    state = load_state()
    if username in state:
        last_login = datetime.fromisoformat(state[username]["last_login"])
        if datetime.now() - last_login < SESSION_DURATION:
            return True
    return False

# -------------------------------
# تحديث الجلسة
# -------------------------------
def update_session(username):
    state = load_state()
    state[username] = {"last_login": datetime.now().isoformat()}
    save_state(state)

# ===============================
# 📂 تحميل بيانات الصالة
# ===============================
def load_excel_for_hall(hall):
    path = f"data_hall_{hall}.xlsx"
    if not os.path.exists(path):
        df = pd.DataFrame(columns=["ID", "Machine", "Status", "Date"])
        df.to_excel(path, index=False)
    return pd.read_excel(path), path

# ===============================
# 🚪 تسجيل الدخول
# ===============================
def login():
    st.title("🔐 نظام إدارة الصالات")
    users = load_users()

    username = st.text_input("اسم المستخدم")
    password = st.text_input("كلمة المرور", type="password")

    if st.button("تسجيل الدخول"):
        if username in users and users[username]["password"] == password:
            update_session(username)
            st.session_state["user"] = username
            st.rerun()
        else:
            st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")

# ===============================
# 🧭 الواجهة الرئيسية
# ===============================
def main_app():
    users = load_users()
    username = st.session_state["user"]
    user_info = users[username]
    hall = user_info["hall"]
    role = user_info.get("role", "user")

    st.sidebar.title("📋 القائمة")
    st.sidebar.write(f"👤 المستخدم: {username}")
    st.sidebar.write(f"🏛 الصالة: {hall}")
    st.sidebar.write(f"🔑 الصلاحية: {role}")

    df, path = load_excel_for_hall(hall)
    st.title(f"📊 بيانات الصالة {hall}")

    # عرض البيانات
    st.dataframe(df, use_container_width=True)

    # -------------------------------
    # 🧩 خيارات الأدمين فقط
    # -------------------------------
    if role == "admin":
        st.subheader("✏ تعديل البيانات")

        option = st.radio("اختر العملية", ["إضافة", "تعديل", "حذف"])

        if option == "إضافة":
            with st.form("add_form"):
                new_id = st.text_input("ID")
                machine = st.text_input("Machine")
                status = st.selectbox("Status", ["Running", "Stopped", "Service Needed"])
                date = st.date_input("Date", datetime.now())
                submitted = st.form_submit_button("➕ إضافة")
                if submitted:
                    new_row = {"ID": new_id, "Machine": machine, "Status": status, "Date": date}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_excel(path, index=False)
                    st.success("✅ تمت الإضافة بنجاح")
                    st.rerun()

        elif option == "تعديل":
            edit_id = st.selectbox("اختر ID للتعديل", df["ID"].astype(str))
            row = df[df["ID"].astype(str) == edit_id].iloc[0]
            with st.form("edit_form"):
                machine = st.text_input("Machine", row["Machine"])
                status = st.selectbox("Status", ["Running", "Stopped", "Service Needed"], index=["Running", "Stopped", "Service Needed"].index(row["Status"]))
                date = st.date_input("Date", pd.to_datetime(row["Date"]))
                submitted = st.form_submit_button("💾 حفظ التعديلات")
                if submitted:
                    df.loc[df["ID"].astype(str) == edit_id, ["Machine", "Status", "Date"]] = [machine, status, date]
                    df.to_excel(path, index=False)
                    st.success("✅ تم التعديل بنجاح")
                    st.rerun()

        elif option == "حذف":
            del_id = st.selectbox("اختر ID للحذف", df["ID"].astype(str))
            if st.button("🗑 حذف"):
                df = df[df["ID"].astype(str) != del_id]
                df.to_excel(path, index=False)
                st.success("🗑 تم الحذف بنجاح")
                st.rerun()

    # -------------------------------
    # 👥 صفحة إدارة المستخدمين (Admin)
    # -------------------------------
    if role == "admin":
        st.sidebar.subheader("👥 إدارة المستخدمين")
        manage_users = st.sidebar.checkbox("فتح صفحة إدارة المستخدمين")
        if manage_users:
            st.subheader("👥 إدارة المستخدمين")
            all_users = pd.DataFrame.from_dict(users, orient="index")
            st.dataframe(all_users)

            with st.form("add_user"):
                new_user = st.text_input("اسم المستخدم الجديد")
                new_pass = st.text_input("كلمة المرور", type="password")
                new_role = st.selectbox("الدور", ["user", "admin"])
                hall = st.selectbox("الصالة", ["A", "B"])
                submitted = st.form_submit_button("➕ إضافة مستخدم")
                if submitted:
                    if new_user in users:
                        st.warning("⚠ هذا المستخدم موجود بالفعل")
                    else:
                        users[new_user] = {"password": new_pass, "role": new_role, "hall": hall}
                        save_users(users)
                        st.success("✅ تمت إضافة المستخدم بنجاح")
                        st.rerun()

    # -------------------------------
    # 🚪 تسجيل الخروج
    # -------------------------------
    if st.sidebar.button("🚪 تسجيل الخروج"):
        del st.session_state["user"]
        st.rerun()

# ===============================
# 🚀 تشغيل التطبيق
# ===============================
if "user" not in st.session_state:
    login()
else:
    if check_session(st.session_state["user"]):
        main_app()
    else:
        st.warning("⏰ انتهت صلاحية الجلسة، سجل الدخول مرة أخرى")
        del st.session_state["user"]
        st.rerun()
