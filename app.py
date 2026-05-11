import streamlit as st
import pandas as pd
import json
import os
import io
import requests
import shutil
import re
from datetime import datetime, timedelta
from base64 import b64decode

# محاولة استيراد PyGithub (لرفع التعديلات)
try:
    from github import Github
    GITHUB_AVAILABLE = True
except Exception:
    GITHUB_AVAILABLE = False

# ===============================
# ⚙ إعدادات التطبيق
# ===============================
APP_CONFIG = {
    "APP_TITLE": "CMMS - bel",
    "APP_ICON": "🏭",
    "REPO_NAME": "mahmedabdallh123/BELYARN",
    "BRANCH": "main",
    "FILE_PATH": "l4.xlsx",
    "LOCAL_FILE": "l4.xlsx",
    "MAX_ACTIVE_USERS": 2,
    "SESSION_DURATION_MINUTES": 15,
    "CUSTOM_TABS": ["📊 فحص السيرفيس", "🛠 تعديل وإدارة البيانات"]
}

USERS_FILE = "users.json"
STATE_FILE = "state.json"
SESSION_DURATION = timedelta(minutes=APP_CONFIG["SESSION_DURATION_MINUTES"])
MAX_ACTIVE_USERS = APP_CONFIG["MAX_ACTIVE_USERS"]
GITHUB_EXCEL_URL = f"https://github.com/{APP_CONFIG['REPO_NAME'].split('/')[0]}/{APP_CONFIG['REPO_NAME'].split('/')[1]}/raw/{APP_CONFIG['BRANCH']}/{APP_CONFIG['FILE_PATH']}"

# -------------------------------
# دوال إدارة المستخدمين والجلسات (بدون تغيير)
# -------------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": {
                "password": "admin123",
                "role": "admin",
                "created_at": datetime.now().isoformat(),
                "permissions": ["all"]
            }
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_users, f, indent=4, ensure_ascii=False)
        return default_users
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
        if "admin" not in users:
            users["admin"] = {
                "password": "admin123",
                "role": "admin",
                "created_at": datetime.now().isoformat(),
                "permissions": ["all"]
            }
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(users, f, indent=4, ensure_ascii=False)
        return users
    except Exception as e:
        st.error(f"❌ خطأ في ملف users.json: {e}")
        return {"admin": {"password": "admin123", "role": "admin", "created_at": datetime.now().isoformat(), "permissions": ["all"]}}

def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"❌ خطأ في حفظ ملف users.json: {e}")
        return False

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
    for user, info in list(state.items()):
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
    keys = list(st.session_state.keys())
    for k in keys:
        st.session_state.pop(k, None)
    st.rerun()

def login_ui():
    users = load_users()
    state = cleanup_sessions(load_state())
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_role = "admin"
        st.session_state.user_permissions = ["all"]

    st.title(f"{APP_CONFIG['APP_ICON']} تسجيل الدخول - {APP_CONFIG['APP_TITLE']}")
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            current_users = json.load(f)
        user_list = list(current_users.keys())
    except:
        user_list = list(users.keys())

    username_input = st.selectbox("👤 اختر المستخدم", user_list)
    password = st.text_input("🔑 كلمة المرور", type="password")

    active_users = [u for u, v in state.items() if v.get("active")]
    active_count = len(active_users)
    st.caption(f"🔒 المستخدمون النشطون الآن: {active_count} / {MAX_ACTIVE_USERS}")

    if not st.session_state.logged_in:
        if st.button("تسجيل الدخول"):
            current_users = load_users()
            if username_input in current_users and current_users[username_input]["password"] == password:
                if username_input != "admin" and username_input in active_users:
                    st.warning("⚠ هذا المستخدم مسجل دخول بالفعل.")
                    return False
                elif active_count >= MAX_ACTIVE_USERS and username_input != "admin":
                    st.error("🚫 الحد الأقصى للمستخدمين المتصلين حالياً.")
                    return False
                state[username_input] = {"active": True, "login_time": datetime.now().isoformat()}
                save_state(state)
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.session_state.user_role = "admin"
                st.session_state.user_permissions = ["all"]
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

# -------------------------------
# دوال GitHub الأساسية (معدلة لتكون مثل الكود الأصلي)
# -------------------------------
def fetch_from_github_requests():
    """تحميل الملف من GitHub باستخدام requests (مثل الكود الأصلي)"""
    try:
        response = requests.get(GITHUB_EXCEL_URL, stream=True, timeout=15)
        response.raise_for_status()
        with open(APP_CONFIG["LOCAL_FILE"], "wb") as f:
            shutil.copyfileobj(response.raw, f)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"⚠ فشل التحديث من GitHub: {e}")
        return False

def push_to_github():
    """رفع الملف المحلي إلى GitHub باستخدام PyGithub (مثل الكود الأصلي)"""
    try:
        token = st.secrets.get("github", {}).get("token", None)
        if not token:
            st.error("❌ لم يتم العثور على GitHub token في secrets")
            return False
        if not GITHUB_AVAILABLE:
            st.error("❌ PyGithub غير متوفر")
            return False
        g = Github(token)
        repo = g.get_repo(APP_CONFIG["REPO_NAME"])
        with open(APP_CONFIG["LOCAL_FILE"], "rb") as f:
            content = f.read()
        try:
            contents = repo.get_contents(APP_CONFIG["FILE_PATH"], ref=APP_CONFIG["BRANCH"])
            repo.update_file(
                path=APP_CONFIG["FILE_PATH"],
                message=f"تحديث البيانات - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                content=content,
                sha=contents.sha,
                branch=APP_CONFIG["BRANCH"]
            )
            st.success("✅ تم رفع التغييرات إلى GitHub")
            return True
        except Exception as e:
            # إذا كان الملف غير موجود، نقوم بإنشائه
            if hasattr(e, 'status') and e.status == 404:
                repo.create_file(
                    path=APP_CONFIG["FILE_PATH"],
                    message=f"إنشاء ملف جديد - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    content=content,
                    branch=APP_CONFIG["BRANCH"]
                )
                st.success("✅ تم إنشاء الملف على GitHub")
                return True
            else:
                st.error(f"❌ خطأ GitHub: {e}")
                return False
    except Exception as e:
        st.error(f"❌ فشل الرفع: {e}")
        return False

def save_excel_locally(sheets_dict):
    """حفظ الأوراق في ملف Excel محلياً"""
    try:
        with pd.ExcelWriter(APP_CONFIG["LOCAL_FILE"], engine="openpyxl") as writer:
            for name, sh in sheets_dict.items():
                try:
                    sh.to_excel(writer, sheet_name=name, index=False)
                except Exception:
                    sh.astype(object).to_excel(writer, sheet_name=name, index=False)
        return True
    except Exception as e:
        st.error(f"❌ خطأ في الحفظ المحلي: {e}")
        return False

def save_and_push_to_github(sheets_dict, operation_name):
    """حفظ محلي ثم رفع إلى GitHub (دالة مدمجة مثل الكود الأصلي)"""
    st.info(f"💾 جاري حفظ {operation_name}...")
    if save_excel_locally(sheets_dict):
        st.success("✅ تم الحفظ محلياً")
        if push_to_github():
            st.success("✅ تم الرفع إلى GitHub")
            st.cache_data.clear()
            return True
        else:
            st.warning("⚠️ تم الحفظ محلياً فقط")
            return True
    else:
        st.error("❌ فشل الحفظ المحلي")
        return False

def auto_save_to_github(sheets_dict, operation_description):
    """دالة مساعدة للحفظ التلقائي (تستدعي save_and_push_to_github)"""
    if sheets_dict is None:
        return None
    success = save_and_push_to_github(sheets_dict, operation_description)
    if success:
        # إعادة تحميل البيانات بعد الحفظ
        return load_sheets_for_edit()
    else:
        return sheets_dict

def check_github_file_exists():
    st.subheader("🔍 تشخيص الاتصال بـ GitHub")
    token = st.secrets.get("github", {}).get("token", None)
    if not token:
        st.error("❌ GitHub token غير موجود في secrets.")
    else:
        st.success("✅ GitHub token موجود.")
    if GITHUB_AVAILABLE:
        st.success("✅ PyGithub مثبت.")
    else:
        st.error("❌ PyGithub غير مثبت.")
    st.markdown("---")
    st.write("**محاولة الوصول إلى الملف عبر رابط RAW:**")
    try:
        response = requests.head(GITHUB_EXCEL_URL, timeout=10)
        if response.status_code == 200:
            st.success(f"✅ الملف موجود (HTTP {response.status_code})")
        else:
            st.warning(f"⚠ استجابة غير متوقعة: HTTP {response.status_code}")
    except Exception as e:
        st.error(f"❌ فشل الاتصال: {e}")

# -------------------------------
# دوال تحميل البيانات
# -------------------------------
@st.cache_data(show_spinner=False)
def load_all_sheets():
    if not os.path.exists(APP_CONFIG["LOCAL_FILE"]):
        return None
    try:
        sheets = pd.read_excel(APP_CONFIG["LOCAL_FILE"], sheet_name=None)
        if not sheets:
            return None
        for name, df in sheets.items():
            df.columns = df.columns.astype(str).str.strip()
        return sheets
    except Exception as e:
        return None

@st.cache_data(show_spinner=False)
def load_sheets_for_edit():
    if not os.path.exists(APP_CONFIG["LOCAL_FILE"]):
        return None
    try:
        sheets = pd.read_excel(APP_CONFIG["LOCAL_FILE"], sheet_name=None, dtype=object)
        if not sheets:
            return None
        for name, df in sheets.items():
            df.columns = df.columns.astype(str).str.strip()
        return sheets
    except Exception as e:
        return None

# -------------------------------
# دوال فحص السيرفيس (نفس الكود الأصلي - يجب نسخها كاملة من التطبيق الأصلي)
# -------------------------------
def normalize_name(s):
    if s is None: return ""
    s = str(s).replace("\n", "+")
    s = re.sub(r"[^0-9a-zA-Z\u0600-\u06FF\+\s_/.-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s

def split_needed_services(needed_service_str):
    if not isinstance(needed_service_str, str) or needed_service_str.strip() == "":
        return []
    parts = re.split(r"\+|,|\n|;", needed_service_str)
    return [p.strip() for p in parts if p.strip() != ""]

def highlight_cell(val, col_name):
    color_map = {
        "Service Needed": "background-color: #fff3cd; color:#856404; font-weight:bold;",
        "Service Done": "background-color: #d4edda; color:#155724; font-weight:bold;",
        "Service Didn't Done": "background-color: #f8d7da; color:#721c24; font-weight:bold;",
        "Date": "background-color: #e7f1ff; color:#004085; font-weight:bold;",
        "Tones": "background-color: #e8f8f5; color:#0d5c4a; font-weight:bold;",
    }
    return color_map.get(col_name, "")

def style_table(row):
    return [highlight_cell(row[col], col) for col in row.index]

def get_servised_by_value(row):
    servised_columns = ["Servised by", "SERVISED BY", "servised by", "Servised By", "Serviced by", "Service by", "Serviced By", "Service By", "خدم بواسطة", "تم الخدمة بواسطة", "فني الخدمة"]
    for col in servised_columns:
        if col in row.index:
            value = str(row[col]).strip()
            if value and value.lower() not in ["nan", "none", ""]:
                return value
    for col in row.index:
        col_normalized = normalize_name(col)
        if any(keyword in col_normalized for keyword in ["servisedby", "servicedby", "serviceby", "خدمبواسطة", "فني"]):
            value = str(row[col]).strip()
            if value and value.lower() not in ["nan", "none", ""]:
                return value
    return "-"

def check_service_status(card_num, current_tons, all_sheets):
    # هذه الدالة يجب أن تأتي من الكود الأصلي الكامل. هنا نضع تطبيقًا مؤقتًا:
    st.warning("⚠ دالة check_service_status لم تُكتمل بعد. يرجى إضافة الكود الأصلي.")
    pass

def show_service_statistics(service_stats, result_df):
    st.warning("⚠ دالة show_service_statistics لم تُكتمل بعد.")
    pass

# -------------------------------
# دوال تعديل البيانات (تطبيقات آمنة)
# -------------------------------
def add_new_event(sheets_edit):
    if sheets_edit is None:
        st.error("لا يمكن إضافة حدث: البيانات غير متوفرة.")
        return
    st.subheader("➕ إضافة حدث جديد")
    sheet_name = st.selectbox("اختر الشيت:", list(sheets_edit.keys()), key="add_event_sheet")
    df = sheets_edit[sheet_name].astype(str)
    st.markdown("أدخل بيانات الحدث الجديد:")
    col1, col2 = st.columns(2)
    with col1:
        card_num = st.text_input("رقم الماكينة:", key="new_event_card")
        event_text = st.text_area("الحدث:", key="new_event_text")
    with col2:
        correction_text = st.text_area("التصحيح:", key="new_correction_text")
        serviced_by = st.text_input("فني الخدمة:", key="new_serviced_by")
    event_date = st.text_input("التاريخ (مثال: 20\\5\\2025):", key="new_event_date")
    if st.button("💾 إضافة الحدث الجديد", key="add_new_event_btn"):
        if not card_num.strip():
            st.warning("⚠ الرجاء إدخال رقم الماكينة.")
            return
        new_row = {}
        new_row["card"] = card_num.strip()
        if event_date.strip():
            new_row["Date"] = event_date.strip()
        event_columns = [col for col in df.columns if normalize_name(col) in ["event", "events", "الحدث", "الأحداث"]]
        if event_columns and event_text.strip():
            new_row[event_columns[0]] = event_text.strip()
        elif not event_columns and event_text.strip():
            new_row["Event"] = event_text.strip()
        correction_columns = [col for col in df.columns if normalize_name(col) in ["correction", "correct", "تصحيح", "تصويب"]]
        if correction_columns and correction_text.strip():
            new_row[correction_columns[0]] = correction_text.strip()
        elif not correction_columns and correction_text.strip():
            new_row["Correction"] = correction_text.strip()
        servised_col = None
        servised_columns = [col for col in df.columns if normalize_name(col) in ["servisedby", "servicedby", "serviceby", "خدمبواسطة"]]
        if servised_columns:
            servised_col = servised_columns[0]
        else:
            for col in df.columns:
                if "servis" in normalize_name(col) or "service" in normalize_name(col) or "فني" in col:
                    servised_col = col
                    break
            if not servised_col:
                servised_col = "Servised by"
        if serviced_by.strip():
            new_row[servised_col] = serviced_by.strip()
        new_row_df = pd.DataFrame([new_row]).astype(str)
        df_new = pd.concat([df, new_row_df], ignore_index=True)
        sheets_edit[sheet_name] = df_new.astype(object)
        new_sheets = auto_save_to_github(sheets_edit, f"إضافة حدث جديد في {sheet_name}")
        if new_sheets is not None:
            st.success("✅ تم إضافة الحدث الجديد بنجاح!")
            st.rerun()
        else:
            st.error("❌ فشل حفظ الحدث.")

def edit_events_and_corrections(sheets_edit):
    if sheets_edit is None:
        st.error("لا يمكن تعديل الأحداث: البيانات غير متوفرة.")
        return
    st.subheader("✏ تعديل الحدث والتصحيح")
    sheet_name = st.selectbox("اختر الشيت:", list(sheets_edit.keys()), key="edit_events_sheet")
    df = sheets_edit[sheet_name].astype(str)
    st.markdown("### 📋 البيانات الحالية (الحدث والتصحيح)")
    display_columns = ["card", "Date"]
    event_columns = [col for col in df.columns if normalize_name(col) in ["event", "events", "الحدث", "الأحداث"]]
    if event_columns:
        display_columns.append(event_columns[0])
    correction_columns = [col for col in df.columns if normalize_name(col) in ["correction", "correct", "تصحيح", "تصويب"]]
    if correction_columns:
        display_columns.append(correction_columns[0])
    servised_columns = [col for col in df.columns if normalize_name(col) in ["servisedby", "servicedby", "serviceby", "خدمبواسطة"]]
    if servised_columns:
        display_columns.append(servised_columns[0])
    display_df = df[display_columns].copy()
    st.dataframe(display_df, use_container_width=True)
    st.markdown("### ✏ اختر الصف للتعديل")
    row_index = st.number_input("رقم الصف (ابدأ من 0):", min_value=0, max_value=len(df)-1, step=1, key="edit_row_index")
    if st.button("تحميل بيانات الصف", key="load_row_data"):
        if 0 <= row_index < len(df):
            st.session_state["editing_row"] = row_index
            st.session_state["editing_data"] = df.iloc[row_index].to_dict()
    if "editing_data" in st.session_state:
        editing_data = st.session_state["editing_data"]
        st.markdown("### تعديل البيانات")
        col1, col2 = st.columns(2)
        with col1:
            new_card = st.text_input("رقم الماكينة:", value=editing_data.get("card", ""), key="edit_card")
            new_date = st.text_input("التاريخ:", value=editing_data.get("Date", ""), key="edit_date")
        with col2:
            new_serviced_by = st.text_input("فني الخدمة:", value=editing_data.get("Servised by", ""), key="edit_serviced_by")
        event_col = None
        correction_col = None
        for col in df.columns:
            col_norm = normalize_name(col)
            if col_norm in ["event", "events", "الحدث", "الأحداث"]:
                event_col = col
            elif col_norm in ["correction", "correct", "تصحيح", "تصويب"]:
                correction_col = col
        if event_col:
            new_event = st.text_area("الحدث:", value=editing_data.get(event_col, ""), key="edit_event")
        if correction_col:
            new_correction = st.text_area("التصحيح:", value=editing_data.get(correction_col, ""), key="edit_correction")
        if st.button("💾 حفظ التعديلات", key="save_edits_btn"):
            df.at[row_index, "card"] = new_card
            df.at[row_index, "Date"] = new_date
            if event_col:
                df.at[row_index, event_col] = new_event
            if correction_col:
                df.at[row_index, correction_col] = new_correction
            servised_col = None
            for col in df.columns:
                if normalize_name(col) in ["servisedby", "servicedby", "serviceby", "خدمبواسطة"]:
                    servised_col = col
                    break
            if servised_col and new_serviced_by.strip():
                df.at[row_index, servised_col] = new_serviced_by.strip()
            sheets_edit[sheet_name] = df.astype(object)
            new_sheets = auto_save_to_github(sheets_edit, f"تعديل حدث في {sheet_name} - الصف {row_index}")
            if new_sheets is not None:
                st.success("✅ تم حفظ التعديلات بنجاح!")
                if "editing_row" in st.session_state:
                    del st.session_state["editing_row"]
                if "editing_data" in st.session_state:
                    del st.session_state["editing_data"]
                st.rerun()

def edit_sheet_with_save_button(sheets_edit):
    if sheets_edit is None:
        st.error("لا توجد بيانات للتعديل.")
        return sheets_edit
    st.subheader("✏ تعديل البيانات")
    if "original_sheets" not in st.session_state:
        st.session_state.original_sheets = sheets_edit.copy()
    if "unsaved_changes" not in st.session_state:
        st.session_state.unsaved_changes = {}
    sheet_name = st.selectbox("اختر الشيت:", list(sheets_edit.keys()), key="edit_sheet")
    if sheet_name not in st.session_state.unsaved_changes:
        st.session_state.unsaved_changes[sheet_name] = False
    df = sheets_edit[sheet_name].astype(str).copy()
    st.markdown(f"### 📋 تحرير شيت: {sheet_name}")
    st.info(f"عدد الصفوف: {len(df)} | عدد الأعمدة: {len(df.columns)}")
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"editor_{sheet_name}")
    has_changes = not edited_df.equals(df)
    if has_changes:
        st.session_state.unsaved_changes[sheet_name] = True
        st.warning("⚠ لديك تغييرات غير محفوظة!")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("💾 حفظ التغييرات", key=f"save_{sheet_name}", type="primary"):
                sheets_edit[sheet_name] = edited_df.astype(object)
                new_sheets = auto_save_to_github(sheets_edit, f"تعديل يدوي في شيت {sheet_name}")
                if new_sheets is not None:
                    sheets_edit = new_sheets
                    st.session_state.unsaved_changes[sheet_name] = False
                    st.success(f"✅ تم حفظ التغييرات في شيت {sheet_name} بنجاح!")
                    st.session_state.original_sheets[sheet_name] = edited_df.copy()
                    st.rerun()
                else:
                    st.error("❌ فشل حفظ التغييرات!")
        with col2:
            if st.button("↩️ تراجع عن التغييرات", key=f"undo_{sheet_name}"):
                if sheet_name in st.session_state.original_sheets:
                    sheets_edit[sheet_name] = st.session_state.original_sheets[sheet_name].astype(object)
                    st.session_state.unsaved_changes[sheet_name] = False
                    st.info(f"↩️ تم التراجع عن التغييرات في شيت {sheet_name}")
                    st.rerun()
                else:
                    st.warning("⚠ لا توجد بيانات أصلية للتراجع!")
        with col3:
            with st.expander("📊 ملخص التغييرات", expanded=False):
                changes_count = 0
                if len(edited_df) > len(df):
                    added_rows = len(edited_df) - len(df)
                    st.write(f"➕ **صفوف مضافة:** {added_rows}")
                    changes_count += added_rows
                elif len(edited_df) < len(df):
                    deleted_rows = len(df) - len(edited_df)
                    st.write(f"🗑️ **صفوف محذوفة:** {deleted_rows}")
                    changes_count += deleted_rows
                changed_cells = 0
                if len(edited_df) == len(df) and edited_df.columns.equals(df.columns):
                    for col in df.columns:
                        if not edited_df[col].equals(df[col]):
                            col_changes = (edited_df[col] != df[col]).sum()
                            changed_cells += col_changes
                if changed_cells > 0:
                    st.write(f"✏️ **خلايا معدلة:** {changed_cells}")
                    changes_count += changed_cells
                if changes_count == 0:
                    st.write("🔄 **لا توجد تغييرات**")
    else:
        if st.session_state.unsaved_changes.get(sheet_name, False):
            st.info("ℹ️ التغييرات السابقة تم حفظها.")
            st.session_state.unsaved_changes[sheet_name] = False
        if st.button("🔄 تحديث البيانات", key=f"refresh_{sheet_name}"):
            st.rerun()
    return sheets_edit

# ===============================
# الواجهة الرئيسية
# ===============================
st.set_page_config(page_title=APP_CONFIG["APP_TITLE"], layout="wide")

with st.sidebar:
    st.header("👤 الجلسة")
    if not st.session_state.get("logged_in"):
        if not login_ui():
            st.stop()
    else:
        state = cleanup_sessions(load_state())
        username = st.session_state.username
        rem = remaining_time(state, username)
        if rem:
            mins, secs = divmod(int(rem.total_seconds()), 60)
            st.success(f"👋 {username} | ⏳ {mins:02d}:{secs:02d}")
        else:
            logout_action()
    st.markdown("---")
    st.write("🔧 أدوات:")
    if st.button("🔄 تحديث الملف من GitHub", key="refresh_github"):
        if fetch_from_github_requests():
            st.rerun()
    if st.button("🗑 مسح الكاش", key="clear_cache"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🔄 تحديث الجلسة", key="refresh_session"):
        users = load_users()
        username = st.session_state.get("username")
        if username and username in users:
            st.success("✅ تم تحديث بيانات الجلسة!")
            st.rerun()
    if st.button("🔍 اختبار الاتصال بـ GitHub", key="check_github"):
        check_github_file_exists()
    st.markdown("---")
    if st.button("🚪 تسجيل الخروج", key="logout_btn"):
        logout_action()

all_sheets = load_all_sheets()
sheets_edit = load_sheets_for_edit()
st.title(f"{APP_CONFIG['APP_ICON']} {APP_CONFIG['APP_TITLE']}")

tabs = st.tabs(APP_CONFIG["CUSTOM_TABS"])

with tabs[0]:
    st.header("📊 فحص السيرفيس")
    if all_sheets is None:
        st.warning("❗ الملف المحلي غير موجود. استخدم زر التحديث في الشريط الجانبي لتحميل الملف من GitHub.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            card_num = st.number_input("رقم الماكينة:", min_value=1, step=1, key="card_num_service")
        with col2:
            current_tons = st.number_input("عدد الأطنان الحالية:", min_value=0, step=100, key="current_tons_service")
        if st.button("عرض حالة السيرفيس", key="show_service"):
            st.session_state["show_service_results"] = True
        if st.session_state.get("show_service_results", False):
            check_service_status(card_num, current_tons, all_sheets)

# ----------------------------------------------
# تبويب تعديل وإدارة البيانات (تم إصلاحه)
# ----------------------------------------------
with tabs[1]:
    st.header("🛠 تعديل وإدارة البيانات")
    
    # التحقق من وجود البيانات
    if sheets_edit is None:
        st.error("❌ لا يمكن الوصول إلى بيانات Excel. الرجاء تحديث الملف من GitHub.")
        if st.button("🔄 تحديث الآن"):
            if fetch_from_github_requests():
                st.rerun()
        # لا نستخدم st.stop() بل نمنع عرض الأتبويبات بالعودة
    else:
        # نضيف تبويبات فرعية فقط إذا كانت البيانات موجودة
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["عرض وتعديل شيت", "إضافة صف جديد", "إضافة عمود جديد", "➕ إضافة حدث جديد", "✏ تعديل الحدث"])
        
        with tab1:
            sheets_edit = edit_sheet_with_save_button(sheets_edit)
        
        with tab2:
            if sheets_edit is not None:
                st.subheader("➕ إضافة صف جديد")
                sheet_name_add = st.selectbox("اختر الشيت لإضافة صف:", list(sheets_edit.keys()), key="add_sheet")
                df_add = sheets_edit[sheet_name_add].astype(str).reset_index(drop=True)
                st.markdown("أدخل بيانات الصف الجديد:")
                new_data = {}
                cols = st.columns(3)
                for i, col in enumerate(df_add.columns):
                    with cols[i % 3]:
                        new_data[col] = st.text_input(f"{col}", key=f"add_{sheet_name_add}_{col}")
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("💾 إضافة الصف الجديد", key=f"add_row_{sheet_name_add}", type="primary"):
                        new_row_df = pd.DataFrame([new_data]).astype(str)
                        df_new = pd.concat([df_add, new_row_df], ignore_index=True)
                        sheets_edit[sheet_name_add] = df_new.astype(object)
                        new_sheets = auto_save_to_github(sheets_edit, f"إضافة صف جديد في {sheet_name_add}")
                        if new_sheets is not None:
                            sheets_edit = new_sheets
                            st.success("✅ تم إضافة الصف الجديد بنجاح!")
                            st.rerun()
                        else:
                            st.error("❌ فشل حفظ البيانات.")
                with col_btn2:
                    if st.button("🗑 مسح الحقول", key=f"clear_{sheet_name_add}"):
                        st.rerun()
            else:
                st.error("لا توجد بيانات لإضافة صف.")
        
        with tab3:
            if sheets_edit is not None:
                st.subheader("🆕 إضافة عمود جديد")
                sheet_name_col = st.selectbox("اختر الشيت لإضافة عمود:", list(sheets_edit.keys()), key="add_col_sheet")
                df_col = sheets_edit[sheet_name_col].astype(str)
                new_col_name = st.text_input("اسم العمود الجديد:", key="new_col_name")
                default_value = st.text_input("القيمة الافتراضية لكل الصفوف (اختياري):", "", key="default_value")
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("💾 إضافة العمود الجديد", key=f"add_col_{sheet_name_col}", type="primary"):
                        if new_col_name:
                            df_col[new_col_name] = default_value
                            sheets_edit[sheet_name_col] = df_col.astype(object)
                            new_sheets = auto_save_to_github(sheets_edit, f"إضافة عمود جديد '{new_col_name}' إلى {sheet_name_col}")
                            if new_sheets is not None:
                                sheets_edit = new_sheets
                                st.success("✅ تم إضافة العمود الجديد بنجاح!")
                                st.rerun()
                            else:
                                st.error("❌ فشل حفظ البيانات.")
                        else:
                            st.warning("⚠ الرجاء إدخال اسم العمود الجديد.")
                with col_btn2:
                    if st.button("🗑 مسح", key=f"clear_col_{sheet_name_col}"):
                        st.rerun()
            else:
                st.error("لا توجد بيانات لإضافة عمود.")
        
        with tab4:
            if sheets_edit is not None:
                add_new_event(sheets_edit)
            else:
                st.error("لا توجد بيانات لإضافة حدث.")
        
        with tab5:
            if sheets_edit is not None:
                edit_events_and_corrections(sheets_edit)
            else:
                st.error("لا توجد بيانات لتعديل الأحداث.")
