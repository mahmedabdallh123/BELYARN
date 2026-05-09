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

try:
    from github import Github
    GITHUB_AVAILABLE = True
except Exception:
    GITHUB_AVAILABLE = False

# ===============================
# ⚙ إعدادات التطبيق
# ===============================
APP_CONFIG = {
    "APP_TITLE": "CMMS - BELYARN",
    "APP_ICON": "🏭",
    "REPO_NAME": "mahmedabdallh123/BELYARN",
    "BRANCH": "main",
    "FILE_PATH": "l4.xlsx",
    "LOCAL_FILE": "l4.xlsx",
    "MAX_ACTIVE_USERS": 2,
    "SESSION_DURATION_MINUTES": 15
}

USERS_FILE = "users.json"
STATE_FILE = "state.json"
SESSION_DURATION = timedelta(minutes=APP_CONFIG["SESSION_DURATION_MINUTES"])
MAX_ACTIVE_USERS = APP_CONFIG["MAX_ACTIVE_USERS"]

GITHUB_EXCEL_URL = f"https://github.com/{APP_CONFIG['REPO_NAME'].split('/')[0]}/{APP_CONFIG['REPO_NAME'].split('/')[1]}/raw/{APP_CONFIG['BRANCH']}/{APP_CONFIG['FILE_PATH']}"

# -------------------------------
# 🧩 دوال المستخدمين والجلسات
# -------------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": {"password": "admin123", "role": "admin", "permissions": ["all"]},
            "editor": {"password": "editor123", "role": "editor", "permissions": ["view", "edit"]},
            "viewer": {"password": "viewer123", "role": "viewer", "permissions": ["view"]}
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_users, f, indent=4)
        return default_users
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
        return True
    except:
        return False

def load_state():
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)

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
    for k in list(st.session_state.keys()):
        st.session_state.pop(k, None)
    st.rerun()

# -------------------------------
# 🔐 تسجيل الدخول
# -------------------------------
def login_ui():
    users = load_users()
    state = cleanup_sessions(load_state())
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_role = None
        st.session_state.user_permissions = []

    st.title(f"{APP_CONFIG['APP_ICON']} تسجيل الدخول - {APP_CONFIG['APP_TITLE']}")

    username_input = st.selectbox("👤 اختر المستخدم", list(users.keys()))
    password = st.text_input("🔑 كلمة المرور", type="password")

    active_users = [u for u, v in state.items() if v.get("active")]
    active_count = len(active_users)
    st.caption(f"🔒 المستخدمون النشطون الآن: {active_count} / {MAX_ACTIVE_USERS}")

    if not st.session_state.logged_in:
        if st.button("تسجيل الدخول"):
            if username_input in users and users[username_input]["password"] == password:
                if username_input in active_users:
                    st.warning("⚠ هذا المستخدم مسجل دخول بالفعل.")
                    return False
                if active_count >= MAX_ACTIVE_USERS:
                    st.error("🚫 الحد الأقصى للمستخدمين المتصلين حالياً.")
                    return False
                state[username_input] = {"active": True, "login_time": datetime.now().isoformat()}
                save_state(state)
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.session_state.user_role = users[username_input].get("role", "viewer")
                st.session_state.user_permissions = users[username_input].get("permissions", ["view"])
                st.success(f"✅ تم تسجيل الدخول: {username_input} ({st.session_state.user_role})")
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
# 🔄 تحميل الملف من GitHub
# -------------------------------
def fetch_from_github_requests():
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

def fetch_from_github_api():
    if not GITHUB_AVAILABLE:
        return fetch_from_github_requests()
    try:
        token = st.secrets.get("github", {}).get("token", None)
        if not token:
            return fetch_from_github_requests()
        g = Github(token)
        repo = g.get_repo(APP_CONFIG["REPO_NAME"])
        file_content = repo.get_contents(APP_CONFIG["FILE_PATH"], ref=APP_CONFIG["BRANCH"])
        content = b64decode(file_content.content)
        with open(APP_CONFIG["LOCAL_FILE"], "wb") as f:
            f.write(content)
        st.cache_data.clear()
        return True
    except:
        return fetch_from_github_requests()

# -------------------------------
# 📂 تحميل الشيتات
# -------------------------------
@st.cache_data(show_spinner=False)
def load_all_sheets():
    if not os.path.exists(APP_CONFIG["LOCAL_FILE"]):
        return None
    try:
        sheets = pd.read_excel(APP_CONFIG["LOCAL_FILE"], sheet_name=None)
        for df in sheets.values():
            df.columns = df.columns.astype(str).str.strip()
        return sheets
    except:
        return None

@st.cache_data(show_spinner=False)
def load_sheets_for_edit():
    if not os.path.exists(APP_CONFIG["LOCAL_FILE"]):
        return None
    try:
        sheets = pd.read_excel(APP_CONFIG["LOCAL_FILE"], sheet_name=None, dtype=object)
        for df in sheets.values():
            df.columns = df.columns.astype(str).str.strip()
        return sheets
    except:
        return None

# -------------------------------
# 🔁 حفظ ورفع التغييرات تلقائياً
# -------------------------------
def save_local_excel_and_push(sheets_dict, commit_message="Update from Streamlit"):
    try:
        with pd.ExcelWriter(APP_CONFIG["LOCAL_FILE"], engine="openpyxl") as writer:
            for name, sh in sheets_dict.items():
                sh.to_excel(writer, sheet_name=name, index=False)
    except Exception as e:
        st.error(f"⚠ خطأ أثناء الحفظ المحلي: {e}")
        return None
    st.cache_data.clear()

    token = st.secrets.get("github", {}).get("token", None)
    if not token or not GITHUB_AVAILABLE:
        st.warning("⚠ لا يمكن الرفع إلى GitHub (token غير موجود أو PyGithub غير متاح). تم الحفظ محلياً فقط.")
        return load_sheets_for_edit()

    try:
        g = Github(token)
        repo = g.get_repo(APP_CONFIG["REPO_NAME"])
        with open(APP_CONFIG["LOCAL_FILE"], "rb") as f:
            content = f.read()
        try:
            contents = repo.get_contents(APP_CONFIG["FILE_PATH"], ref=APP_CONFIG["BRANCH"])
            repo.update_file(APP_CONFIG["FILE_PATH"], commit_message, content, contents.sha, branch=APP_CONFIG["BRANCH"])
        except:
            repo.create_file(APP_CONFIG["FILE_PATH"], commit_message, content, branch=APP_CONFIG["BRANCH"])
        st.success("✅ تم الحفظ والرفع إلى GitHub بنجاح")
        return load_sheets_for_edit()
    except Exception as e:
        st.error(f"❌ فشل الرفع إلى GitHub: {e}")
        return None

def auto_save_to_github(sheets_dict, operation_description):
    username = st.session_state.get("username", "unknown")
    commit_message = f"{operation_description} by {username} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    result = save_local_excel_and_push(sheets_dict, commit_message)
    if result is not None:
        return result
    else:
        st.error("❌ فشل الحفظ التلقائي")
        return sheets_dict

# -------------------------------
# 🧰 دوال مساعدة للفحص
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
        "Min_Tons": "background-color: #ebf5fb; color:#154360; font-weight:bold;",
        "Max_Tons": "background-color: #f9ebea; color:#641e16; font-weight:bold;",
        "Card Number": "background-color: #ebdef0; color:#4a235a; font-weight:bold;"
    }
    return color_map.get(col_name, "")

def style_table(row):
    return [highlight_cell(row[col], col) for col in row.index]

def get_user_permissions(user_role, user_permissions):
    if "all" in user_permissions or user_role == "admin":
        return {"can_view": True, "can_edit": True}
    elif "edit" in user_permissions or user_role == "editor":
        return {"can_view": True, "can_edit": True}
    else:
        return {"can_view": True, "can_edit": False}

# -------------------------------
# 🖥 فحص الماكينة (الخدمات فقط)
# -------------------------------
def check_machine_status(card_num, current_tons, all_sheets):
    if not all_sheets or "ServicePlan" not in all_sheets:
        st.error("❌ الملف لا يحتوي على شيت ServicePlan.")
        return

    service_plan_df = all_sheets["ServicePlan"]
    card_sheet_name = f"Card{card_num}"
    if card_sheet_name not in all_sheets:
        st.warning(f"⚠ لا يوجد شيت باسم {card_sheet_name}")
        return

    card_df = all_sheets[card_sheet_name]

    if "view_option" not in st.session_state:
        st.session_state.view_option = "الشريحة الحالية فقط"

    st.subheader("⚙ نطاق العرض")
    view_option = st.radio(
        "اختر نطاق العرض:",
        ("الشريحة الحالية فقط", "كل الشرائح الأقل", "كل الشرائح الأعلى", "نطاق مخصص", "كل الشرائح"),
        horizontal=True,
        key="view_option"
    )

    min_range = st.session_state.get("min_range", max(0, current_tons - 500))
    max_range = st.session_state.get("max_range", current_tons + 500)
    if view_option == "نطاق مخصص":
        col1, col2 = st.columns(2)
        with col1:
            min_range = st.number_input("من (طن):", min_value=0, step=100, value=min_range, key="min_range")
        with col2:
            max_range = st.number_input("إلى (طن):", min_value=min_range, step=100, value=max_range, key="max_range")

    if view_option == "الشريحة الحالية فقط":
        selected_slices = service_plan_df[(service_plan_df["Min_Tones"] <= current_tons) & (service_plan_df["Max_Tones"] >= current_tons)]
    elif view_option == "كل الشرائح الأقل":
        selected_slices = service_plan_df[service_plan_df["Max_Tones"] <= current_tons]
    elif view_option == "كل الشرائح الأعلى":
        selected_slices = service_plan_df[service_plan_df["Min_Tones"] >= current_tons]
    elif view_option == "نطاق مخصص":
        selected_slices = service_plan_df[(service_plan_df["Min_Tones"] >= min_range) & (service_plan_df["Max_Tones"] <= max_range)]
    else:
        selected_slices = service_plan_df.copy()

    if selected_slices.empty:
        st.warning("⚠ لا توجد شرائح مطابقة.")
        return

    all_results = []
    for _, current_slice in selected_slices.iterrows():
        slice_min = current_slice["Min_Tones"]
        slice_max = current_slice["Max_Tones"]
        needed_service_raw = current_slice.get("Service", "")
        needed_parts = split_needed_services(needed_service_raw)
        needed_norm = [normalize_name(p) for p in needed_parts]

        mask = (card_df.get("Min_Tones", 0).fillna(0) <= slice_max) & (card_df.get("Max_Tones", 0).fillna(0) >= slice_min)
        matching_rows = card_df[mask]

        if not matching_rows.empty:
            for _, row in matching_rows.iterrows():
                done_services_set = set()
                metadata_columns = {"card", "tones", "min_tones", "max_tones", "date", "other", "servised by", "event", "correction"}
                all_cols = set(card_df.columns)
                service_cols = [c for c in all_cols if normalize_name(c) not in metadata_columns]
                for col in service_cols:
                    val = str(row.get(col, "")).strip()
                    if val and val.lower() not in ["nan", "none", "", "null", "0", "no", "false", "not done", "لم تتم", "x", "-"]:
                        done_services_set.add(col)

                done_services = sorted(done_services_set)
                done_norm = [normalize_name(c) for c in done_services]
                not_done = [p for p, np in zip(needed_parts, needed_norm) if np not in done_norm]

                all_results.append({
                    "Card Number": card_num,
                    "Min_Tons": slice_min,
                    "Max_Tons": slice_max,
                    "Service Needed": " + ".join(needed_parts) if needed_parts else "-",
                    "Service Done": ", ".join(done_services) if done_services else "-",
                    "Service Didn't Done": ", ".join(not_done) if not_done else "-"
                })
        else:
            all_results.append({
                "Card Number": card_num,
                "Min_Tons": slice_min,
                "Max_Tons": slice_max,
                "Service Needed": " + ".join(needed_parts) if needed_parts else "-",
                "Service Done": "-",
                "Service Didn't Done": ", ".join(needed_parts) if needed_parts else "-"
            })

    result_df = pd.DataFrame(all_results).dropna(how="all").reset_index(drop=True)

    # إخفاء الصفوف التي ليس فيها أي خدمات
    result_df = result_df[
        ~((result_df["Service Needed"] == "-") &
          (result_df["Service Done"] == "-") &
          (result_df["Service Didn't Done"] == "-"))
    ]

    if result_df.empty:
        st.info("ℹ️ لا توجد خدمات مطلوبة أو منجزة في النطاق المحدد.")
        return

    st.markdown("### 📋 نتائج فحص الخدمات")
    st.dataframe(result_df.style.apply(style_table, axis=1), use_container_width=True)

    buffer = io.BytesIO()
    result_df.to_excel(buffer, index=False, engine="openpyxl")
    st.download_button(
        label="💾 حفظ النتائج كـ Excel",
        data=buffer.getvalue(),
        file_name=f"Service_Report_Card{card_num}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ===============================
# 🖥 الواجهة الرئيسية (تبويبان)
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
    if st.button("🔄 تحديث الملف من GitHub"):
        if fetch_from_github_requests():
            st.rerun()
    if st.button("🗑 مسح الكاش"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🚪 تسجيل الخروج"):
        logout_action()

# تحميل البيانات
all_sheets = load_all_sheets()
sheets_edit = load_sheets_for_edit()

st.title(f"{APP_CONFIG['APP_ICON']} {APP_CONFIG['APP_TITLE']}")

# الصلاحيات
permissions = get_user_permissions(
    st.session_state.get("user_role", "viewer"),
    st.session_state.get("user_permissions", ["view"])
)

# إنشاء التبويبات حسب الصلاحيات
if permissions["can_edit"]:
    tabs = st.tabs(["📊 عرض وفحص الماكينات", "🛠 تعديل وإدارة البيانات"])
else:
    tabs = st.tabs(["📊 عرض وفحص الماكينات"])

# تبويب عرض وفحص الماكينات
with tabs[0]:
    st.header("📊 عرض وفحص الماكينات")
    if all_sheets is None:
        st.warning("❗ الملف المحلي غير موجود. استخدم زر التحديث في الشريط الجانبي لتحميل الملف من GitHub.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            card_num = st.number_input("رقم الماكينة:", min_value=1, step=1, key="card_num_main")
        with col2:
            current_tons = st.number_input("عدد الأطنان الحالية:", min_value=0, step=100, key="current_tons_main")
        if st.button("عرض الحالة"):
            st.session_state["show_results"] = True
        if st.session_state.get("show_results", False):
            check_machine_status(card_num, current_tons, all_sheets)

# تبويب تعديل وإدارة البيانات (للمستخدمين المصرح لهم)
if permissions["can_edit"] and len(tabs) > 1:
    with tabs[1]:
        st.header("🛠 تعديل وإدارة البيانات")
        if sheets_edit is None:
            st.warning("❗ الملف المحلي غير موجود. قم بالتحديث أولاً.")
        else:
            edit_tabs = st.tabs(["عرض وتعديل شيت", "إضافة صف جديد", "إضافة عمود جديد", "🗑 حذف صف"])

            # تعديل البيانات
            with edit_tabs[0]:
                sheet_name = st.selectbox("اختر الشيت:", list(sheets_edit.keys()), key="edit_sheet")
                df = sheets_edit[sheet_name].astype(str)
                edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"editor_{sheet_name}")
                if not edited_df.equals(df):
                    sheets_edit[sheet_name] = edited_df.astype(object)
                    sheets_edit = auto_save_to_github(sheets_edit, f"تعديل تلقائي في شيت {sheet_name}")
                    if sheets_edit:
                        st.rerun()

            # إضافة صف
            with edit_tabs[1]:
                sheet_name_add = st.selectbox("اختر الشيت:", list(sheets_edit.keys()), key="add_sheet")
                df_add = sheets_edit[sheet_name_add].astype(str).reset_index(drop=True)
                new_data = {}
                cols = st.columns(3)
                for i, col in enumerate(df_add.columns):
                    with cols[i % 3]:
                        new_data[col] = st.text_input(f"{col}", key=f"add_{sheet_name_add}_{col}")
                if st.button("💾 إضافة الصف الجديد", key=f"add_row_{sheet_name_add}"):
                    new_row_df = pd.DataFrame([new_data]).astype(str)
                    # تحديد موقع الإدراج بناءً على Min_Tones / Max_Tones إن وجدت
                    min_col = next((c for c in df_add.columns if c.lower() in ("min_tones", "min_tone", "min")), None)
                    max_col = next((c for c in df_add.columns if c.lower() in ("max_tones", "max_tone", "max")), None)
                    if min_col and max_col:
                        try:
                            new_min = float(new_data.get(min_col, 0))
                            df_add["_min_num"] = pd.to_numeric(df_add[min_col], errors='coerce').fillna(-1)
                            insert_pos = int((df_add["_min_num"] < new_min).sum())
                            df_add = df_add.drop(columns=["_min_num"])
                        except:
                            insert_pos = len(df_add)
                    else:
                        insert_pos = len(df_add)
                    df_new = pd.concat([df_add.iloc[:insert_pos], new_row_df, df_add.iloc[insert_pos:]], ignore_index=True)
                    sheets_edit[sheet_name_add] = df_new.astype(object)
                    sheets_edit = auto_save_to_github(sheets_edit, f"إضافة صف جديد في {sheet_name_add}")
                    if sheets_edit:
                        st.rerun()

            # إضافة عمود
            with edit_tabs[2]:
                sheet_name_col = st.selectbox("اختر الشيت:", list(sheets_edit.keys()), key="add_col_sheet")
                df_col = sheets_edit[sheet_name_col].astype(str)
                new_col_name = st.text_input("اسم العمود الجديد:")
                default_value = st.text_input("القيمة الافتراضية:", "")
                if st.button("💾 إضافة العمود", key=f"add_col_{sheet_name_col}"):
                    if new_col_name:
                        df_col[new_col_name] = default_value
                        sheets_edit[sheet_name_col] = df_col.astype(object)
                        sheets_edit = auto_save_to_github(sheets_edit, f"إضافة عمود {new_col_name} إلى {sheet_name_col}")
                        if sheets_edit:
                            st.rerun()
                    else:
                        st.warning("⚠ الرجاء إدخال اسم العمود.")

            # حذف صفوف
            with edit_tabs[3]:
                sheet_name_del = st.selectbox("اختر الشيت:", list(sheets_edit.keys()), key="delete_sheet")
                df_del = sheets_edit[sheet_name_del].astype(str).reset_index(drop=True)
                st.dataframe(df_del, use_container_width=True)
                rows_input = st.text_input("أرقام الصفوف للحذف (مفصولة بفواصل):")
                confirm = st.checkbox("✅ تأكيد الحذف")
                if st.button("🗑 حذف", key="delete_rows"):
                    if not rows_input.strip() or not confirm:
                        st.warning("⚠ أدخل أرقاماً وأكّد الحذف.")
                    else:
                        try:
                            rows_to_del = [int(x.strip()) for x in rows_input.split(",") if x.strip().isdigit()]
                            rows_to_del = [r for r in rows_to_del if 0 <= r < len(df_del)]
                            if rows_to_del:
                                df_new = df_del.drop(rows_to_del).reset_index(drop=True)
                                sheets_edit[sheet_name_del] = df_new.astype(object)
                                sheets_edit = auto_save_to_github(sheets_edit, f"حذف صفوف {rows_to_del} من {sheet_name_del}")
                                if sheets_edit:
                                    st.rerun()
                            else:
                                st.warning("⚠ لم يتم العثور على صفوف صالحة.")
                        except Exception as e:
                            st.error(f"خطأ: {e}")
