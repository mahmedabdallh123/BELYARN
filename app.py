import streamlit as st
import pandas as pd
import json
import os
import io
import requests
import shutil
import re
import traceback
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
    "BRANCH": "main",       # ✅ تم التغيير إلى الفرع الصحيح
    "FILE_PATH": "l4.xlsx",
    "LOCAL_FILE": "l4.xlsx",
    "MAX_ACTIVE_USERS": 2,
    "SESSION_DURATION_MINUTES": 15,
    "CUSTOM_TABS": ["📊 عرض وفحص الماكينات", "🛠 تعديل وإدارة البيانات"]
}

USERS_FILE = "users.json"
STATE_FILE = "state.json"
SESSION_DURATION = timedelta(minutes=APP_CONFIG["SESSION_DURATION_MINUTES"])
MAX_ACTIVE_USERS = APP_CONFIG["MAX_ACTIVE_USERS"]
GITHUB_EXCEL_URL = f"https://github.com/{APP_CONFIG['REPO_NAME'].split('/')[0]}/{APP_CONFIG['REPO_NAME'].split('/')[1]}/raw/{APP_CONFIG['BRANCH']}/{APP_CONFIG['FILE_PATH']}"

# -------------------------------
# دوال المستخدمين والجلسات
# -------------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": {"password": "admin123", "role": "admin", "created_at": datetime.now().isoformat(), "permissions": ["all"]},
            "user1": {"password": "user1123", "role": "editor", "created_at": datetime.now().isoformat(), "permissions": ["view", "edit"]},
            "user2": {"password": "user2123", "role": "viewer", "created_at": datetime.now().isoformat(), "permissions": ["view"]}
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_users, f, indent=4, ensure_ascii=False)
        return default_users
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
            for username, user_data in users.items():
                if "role" not in user_data:
                    user_data["role"] = "admin" if username == "admin" else "viewer"
                if "permissions" not in user_data:
                    if user_data["role"] == "admin":
                        user_data["permissions"] = ["all"]
                    elif user_data["role"] == "editor":
                        user_data["permissions"] = ["view", "edit"]
                    else:
                        user_data["permissions"] = ["view"]
                if "created_at" not in user_data:
                    user_data["created_at"] = datetime.now().isoformat()
            return users
    except Exception as e:
        st.error(f"❌ خطأ في users.json: {e}")
        return {"admin": {"password": "admin123", "role": "admin", "permissions": ["all"], "created_at": datetime.now().isoformat()}}

def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"❌ خطأ في حفظ users.json: {e}")
        return False

def load_state():
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w") as f:
            json.dump({}, f)
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

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
                st.session_state.user_role = users[username_input].get("role", "viewer")
                st.session_state.user_permissions = users[username_input].get("permissions", ["view"])
                st.success(f"✅ تم تسجيل الدخول: {username_input}")
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة.")
        return False
    else:
        username = st.session_state.username
        user_role = st.session_state.user_role
        st.success(f"✅ مسجل الدخول كـ: {username} ({user_role})")
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
# تحميل وتحديث الملف من GitHub
# -------------------------------
def fetch_from_github_requests():
    try:
        response = requests.get(GITHUB_EXCEL_URL, stream=True, timeout=15)
        response.raise_for_status()
        with open(APP_CONFIG["LOCAL_FILE"], "wb") as f:
            shutil.copyfileobj(response.raw, f)
        st.cache_data.clear()
        return True, None
    except Exception as e:
        return False, str(e)

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
        return True, None
    except Exception as e:
        return False, str(e)

# -------------------------------
# تحميل الشيتات
# -------------------------------
@st.cache_data(show_spinner=False)
def load_all_sheets():
    if not os.path.exists(APP_CONFIG["LOCAL_FILE"]):
        return None
    try:
        sheets = pd.read_excel(APP_CONFIG["LOCAL_FILE"], sheet_name=None)
        if sheets:
            for name, df in sheets.items():
                df.columns = df.columns.astype(str).str.strip()
        return sheets
    except Exception as e:
        st.error(f"❌ خطأ في قراءة الملف: {e}")
        return None

@st.cache_data(show_spinner=False)
def load_sheets_for_edit():
    if not os.path.exists(APP_CONFIG["LOCAL_FILE"]):
        return None
    try:
        sheets = pd.read_excel(APP_CONFIG["LOCAL_FILE"], sheet_name=None, dtype=object)
        if sheets:
            for name, df in sheets.items():
                df.columns = df.columns.astype(str).str.strip()
        return sheets
    except Exception as e:
        st.error(f"❌ خطأ في تحميل الشيتات للتحرير: {e}")
        return None

# -----------------------------------------------
# دوال الحفظ مع إرجاع رسائل خطأ مفصلة
# -----------------------------------------------
# -----------------------------------------------
# دوال الحفظ مع إرجاع رسائل خطأ مفصلة (محسّن)
# -----------------------------------------------
def save_local_excel_and_push(sheets_dict, commit_message="Update from Streamlit"):
    """
    حفظ الملف محلياً ورفعه إلى GitHub على الفرع 'main' مع التحقق من وجود الملف.
    """
    # 1. حفظ محلي - يبقى كما هو
    try:
        with pd.ExcelWriter(APP_CONFIG["LOCAL_FILE"], engine="openpyxl") as writer:
            for name, sh in sheets_dict.items():
                try:
                    sh.to_excel(writer, sheet_name=name, index=False)
                except Exception as inner_e:
                    st.warning(f"⚠ تحويل شيت {name} إلى object بسبب: {inner_e}")
                    sh.astype(object).to_excel(writer, sheet_name=name, index=False)
    except Exception as e:
        error_msg = f"❌ فشل الحفظ المحلي:\n{str(e)}\n\n{traceback.format_exc()}"
        return (None, error_msg)
    
    # 2. مسح الكاش - يبقى كما هو
    try:
        st.cache_data.clear()
    except:
        pass
    
    # 3. رفع إلى GitHub (تم التعديل هنا)
    token = st.secrets.get("github", {}).get("token", None)
    if not token:
        error_msg = "⚠⚠⚠ لا يوجد GitHub token في secrets. تم الحفظ محلياً فقط."
        return (load_sheets_for_edit(), error_msg)
    
    if not GITHUB_AVAILABLE:
        error_msg = "⚠⚠⚠ PyGithub غير مثبت. تم الحفظ محلياً فقط."
        return (load_sheets_for_edit(), error_msg)
    
    try:
        g = Github(token)
        repo = g.get_repo(APP_CONFIG["REPO_NAME"])
        with open(APP_CONFIG["LOCAL_FILE"], "rb") as f:
            content = f.read()
        
        # استخدام الفرع 'main' كما هو محدد في إعدادات التطبيق
        target_branch = APP_CONFIG["BRANCH"]  # يجب أن يساوي "main" في الإعدادات
        
        # 🔄 التحقق من وجود الملف أولاً لتجنب خطأ 404
        try:
            # محاولة جلب معلومات الملف من GitHub
            contents = repo.get_contents(APP_CONFIG["FILE_PATH"], ref=target_branch)
            # الملف موجود -> تحديثه
            result = repo.update_file(
                path=APP_CONFIG["FILE_PATH"],
                message=commit_message,
                content=content,
                sha=contents.sha,
                branch=target_branch
            )
            return (load_sheets_for_edit(), None)
            
        except github.GithubException.UnknownObjectException:
            # الملف غير موجود -> إنشاؤه لأول مرة
            result = repo.create_file(
                path=APP_CONFIG["FILE_PATH"],
                message=f"Create initial file: {commit_message}",
                content=content,
                branch=target_branch
            )
            return (load_sheets_for_edit(), None)
            
    except Exception as e:
        error_msg = f"❌❌❌ فشل الاتصال بـ GitHub أو الرفع:\n{str(e)}\n{traceback.format_exc()}"
        return (None, error_msg)

def auto_save_to_github(sheets_dict, operation_description):
    """دالة مساعدة للحفظ على GitHub (بدون تغيير)"""
    username = st.session_state.get("username", "unknown")
    commit_message = f"{operation_description} by {username} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    new_sheets, error = save_local_excel_and_push(sheets_dict, commit_message)
    return (new_sheets, error)
# -------------------------------
# دوال مساعدة للواجهة والفحص
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
        "Min_Tons": "background-color: #ebf5fb; color:#154360; font-weight:bold;",
        "Max_Tons": "background-color: #f9ebea; color:#641e16; font-weight:bold;",
        "Event": "background-color: #e2f0d9; color:#2e6f32; font-weight:bold;",
        "Correction": "background-color: #fdebd0; color:#7d6608; font-weight:bold;",
        "Servised by": "background-color: #f0f0f0; color:#333; font-weight:bold;",
        "Card Number": "background-color: #ebdef0; color:#4a235a; font-weight:bold;"
    }
    return color_map.get(col_name, "")

def style_table(row):
    return [highlight_cell(row[col], col) for col in row.index]

def get_user_permissions(user_role, user_permissions):
    if "all" in user_permissions:
        return {"can_view": True, "can_edit": True, "can_manage_users": False, "can_see_tech_support": False}
    elif "edit" in user_permissions:
        return {"can_view": True, "can_edit": True}
    else:
        return {"can_view": True, "can_edit": False}

def check_machine_status(card_num, current_tons, all_sheets):
    if not all_sheets:
        st.error("❌ لم يتم تحميل أي شيتات.")
        return
    if "ServicePlan" not in all_sheets:
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
    view_option = st.radio("اختر نطاق العرض:", ("الشريحة الحالية فقط", "كل الشرائح الأقل", "كل الشرائح الأعلى", "نطاق مخصص", "كل الشرائح"), horizontal=True, key="view_option")
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
                metadata_columns = {"card", "Tones", "Min_Tones", "Max_Tones", "Date", "Other", "Servised by", "Event", "Correction", "Card", "TONES", "MIN_TONES", "MAX_TONES", "DATE", "OTHER", "EVENT", "CORRECTION", "SERVISED BY", "servised by", "Servised By", "Serviced by", "Service by", "Serviced By", "Service By", "خدم بواسطة", "تم الخدمة بواسطة", "فني الخدمة"}
                all_columns = set(card_df.columns)
                service_columns = all_columns - metadata_columns
                final_service_columns = set()
                for col in service_columns:
                    col_normalized = normalize_name(col)
                    metadata_normalized = {normalize_name(mc) for mc in metadata_columns}
                    if col_normalized not in metadata_normalized:
                        final_service_columns.add(col)
                for col in final_service_columns:
                    val = str(row.get(col, "")).strip()
                    if val and val.lower() not in ["nan", "none", "", "null", "0"] and val.lower() not in ["no", "false", "not done", "لم تتم", "x", "-"]:
                        done_services_set.add(col)
                current_date = str(row.get("Date", "")).strip() if pd.notna(row.get("Date")) else "-"
                current_tones = str(row.get("Tones", "")).strip() if pd.notna(row.get("Tones")) else "-"
                event_value = "-"
                for potential_col in ["Event", "EVENT", "event", "Events", "events", "الحدث", "الأحداث"]:
                    if potential_col in card_df.columns and pd.notna(row.get(potential_col)) and str(row.get(potential_col)).strip() != "":
                        event_value = str(row.get(potential_col)).strip()
                        break
                correction_value = "-"
                for potential_col in ["Correction", "CORRECTION", "correction", "Correct", "correct", "تصحيح", "تصويب"]:
                    if potential_col in card_df.columns and pd.notna(row.get(potential_col)) and str(row.get(potential_col)).strip() != "":
                        correction_value = str(row.get(potential_col)).strip()
                        break
                servised_by_value = "-"
                for potential_col in ["Servised by", "SERVISED BY", "servised by", "Servised By", "Serviced by", "Service by", "خدم بواسطة"]:
                    if potential_col in card_df.columns and pd.notna(row.get(potential_col)) and str(row.get(potential_col)).strip() != "":
                        servised_by_value = str(row.get(potential_col)).strip()
                        break
                done_services = sorted(list(done_services_set))
                done_norm = [normalize_name(c) for c in done_services]
                not_done = []
                for needed_part, needed_norm_part in zip(needed_parts, needed_norm):
                    if needed_norm_part not in done_norm:
                        not_done.append(needed_part)
                all_results.append({"Card Number": card_num, "Min_Tons": slice_min, "Max_Tons": slice_max, "Service Needed": " + ".join(needed_parts) if needed_parts else "-", "Service Done": ", ".join(done_services) if done_services else "-", "Service Didn't Done": ", ".join(not_done) if not_done else "-", "Tones": current_tones, "Event": event_value, "Correction": correction_value, "Servised by": servised_by_value, "Date": current_date})
        else:
            all_results.append({"Card Number": card_num, "Min_Tons": slice_min, "Max_Tons": slice_max, "Service Needed": " + ".join(needed_parts) if needed_parts else "-", "Service Done": "-", "Service Didn't Done": ", ".join(needed_parts) if needed_parts else "-", "Tones": "-", "Event": "-", "Correction": "-", "Servised by": "-", "Date": "-"})
    result_df = pd.DataFrame(all_results).dropna(how="all").reset_index(drop=True)
    st.markdown("### 📋 نتائج الفحص - جميع الأحداث")
    st.dataframe(result_df.style.apply(style_table, axis=1), use_container_width=True)
    buffer = io.BytesIO()
    result_df.to_excel(buffer, index=False, engine="openpyxl")
    st.download_button(label="💾 حفظ النتائج كـ Excel", data=buffer.getvalue(), file_name=f"Service_Report_Card{card_num}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

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
        user_role = st.session_state.user_role
        rem = remaining_time(state, username)
        if rem:
            mins, secs = divmod(int(rem.total_seconds()), 60)
            st.success(f"👋 {username} | الدور: {user_role} | ⏳ {mins:02d}:{secs:02d}")
        else:
            logout_action()
    st.markdown("---")
    st.write("🔧 أدوات:")
    if st.button("🔄 تحديث الملف من GitHub"):
        with st.spinner("جاري التحميل..."):
            success, err = fetch_from_github_requests()
            if success:
                st.success("تم التحديث بنجاح")
                st.rerun()
            else:
                st.error(f"فشل التحديث: {err}")
    if st.button("🗑 مسح الكاش"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    if st.button("🚪 تسجيل الخروج"):
        logout_action()

all_sheets = load_all_sheets()
sheets_edit = load_sheets_for_edit()
st.title(f"{APP_CONFIG['APP_ICON']} {APP_CONFIG['APP_TITLE']}")

username = st.session_state.get("username")
user_role = st.session_state.get("user_role", "viewer")
user_permissions = st.session_state.get("user_permissions", ["view"])
permissions = get_user_permissions(user_role, user_permissions)

if permissions.get("can_edit", False):
    tabs = st.tabs(APP_CONFIG["CUSTOM_TABS"])
else:
    tabs = st.tabs(["📊 عرض وفحص الماكينات"])

# تبويب عرض وفحص الماكينات
with tabs[0]:
    st.header("📊 عرض وفحص الماكينات")
    if all_sheets is None:
        st.warning("❗ الملف المحلي غير موجود. استخدم زر التحديث في الشريط الجانبي.")
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

# تبويب تعديل البيانات (مع عرض ثابت للخطأ)
if permissions.get("can_edit", False) and len(tabs) > 1:
    with tabs[1]:
        st.header("🛠 تعديل وإدارة البيانات")
        
        # مكان ثابت لعرض الأخطاء (لن يختفي)
        error_container = st.empty()
        
        if sheets_edit is None:
            st.error("لا يمكن تحميل البيانات. تأكد من وجود الملف المحلي.")
        else:
            sheet_names = list(sheets_edit.keys())
            selected_sheet = st.selectbox("اختر الشيت", sheet_names, key="edit_sheet_select")
            current_df = sheets_edit[selected_sheet].astype(str)
            
            st.markdown("### ✏ قم بتعديل البيانات مباشرة في الجدول")
            edited_df = st.data_editor(current_df, num_rows="dynamic", use_container_width=True, key="data_editor_main")
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("💾 حفظ التغييرات الآن", type="primary", use_container_width=True):
                    if edited_df.equals(current_df):
                        st.info("ℹ️ لا توجد تغييرات جديدة للحفظ.")
                    else:
                        sheets_edit[selected_sheet] = edited_df.astype(object)
                        new_sheets, error = auto_save_to_github(sheets_edit, f"تعديل يدوي في شيت {selected_sheet}")
                        if error:
                            # عرض الخطأ بشكل ثابت وواضح
                            error_container.error(f"⚠⚠⚠ فشل الحفظ ⚠⚠⚠\n\n{error}")
                            st.session_state.save_error = error  # نخزنه في session_state ليبقى حتى بعد إعادة التشغيل
                        else:
                            sheets_edit = new_sheets
                            error_container.success("✅ تم الحفظ بنجاح ورفعه إلى GitHub")
                            st.rerun()
            
            # إذا كان هناك خطأ مخزّن سابقاً، أظهره
            if "save_error" in st.session_state and st.session_state.save_error:
                error_container.error(f"⚠⚠⚠ خطأ سابق في الحفظ ⚠⚠⚠\n\n{st.session_state.save_error}")
            
            # باقي العمليات (إضافة صف، عمود، حذف) بنفس المنطق مع error_container
            st.markdown("---")
            with st.expander("➕ إضافة صف جديد"):
                df_add = sheets_edit[selected_sheet].astype(str).reset_index(drop=True)
                new_data = {}
                cols = st.columns(3)
                for i, col in enumerate(df_add.columns):
                    with cols[i % 3]:
                        new_data[col] = st.text_input(f"{col}", key=f"add_{selected_sheet}_{col}")
                if st.button("💾 إضافة الصف وحفظ", key="add_row_btn"):
                    new_row_df = pd.DataFrame([new_data]).astype(str)
                    # إيجاد أعمدة Min/Max
                    min_col = max_col = card_col = None
                    for c in df_add.columns:
                        c_low = c.strip().lower()
                        if c_low in ("min_tones", "min_tone", "min tones", "min"):
                            min_col = c
                        if c_low in ("max_tones", "max_tone", "max tones", "max"):
                            max_col = c
                        if c_low in ("card", "machine", "machine_no", "machine id"):
                            card_col = c
                    if not min_col or not max_col:
                        error_container.error("⚠ لم يتم العثور على أعمدة Min_Tones / Max_Tones في هذا الشيت. لا يمكن إضافة الصف.")
                    else:
                        new_min_raw = str(new_data.get(min_col, "")).strip()
                        new_max_raw = str(new_data.get(max_col, "")).strip()
                        insert_pos = len(df_add)
                        try:
                            df_add["_min_num"] = pd.to_numeric(df_add[min_col], errors='coerce').fillna(-1)
                            new_min_num = float(new_min_raw) if new_min_raw.replace('.', '', 1).isdigit() else -1
                            insert_pos = int((df_add["_min_num"] < new_min_num).sum())
                            df_add = df_add.drop(columns=["_min_num"])
                        except:
                            pass
                        df_top = df_add.iloc[:insert_pos].reset_index(drop=True)
                        df_bottom = df_add.iloc[insert_pos:].reset_index(drop=True)
                        df_new = pd.concat([df_top, new_row_df.reset_index(drop=True), df_bottom], ignore_index=True)
                        sheets_edit[selected_sheet] = df_new.astype(object)
                        new_sheets, error = auto_save_to_github(sheets_edit, f"إضافة صف في {selected_sheet}")
                        if error:
                            error_container.error(f"⚠⚠⚠ فشل إضافة الصف: {error}")
                        else:
                            sheets_edit = new_sheets
                            st.success("تمت الإضافة والحفظ بنجاح")
                            st.rerun()
            
            with st.expander("🆕 إضافة عمود جديد"):
                new_col_name = st.text_input("اسم العمود الجديد:", key="new_col_name")
                default_value = st.text_input("القيمة الافتراضية:", key="default_value")
                if st.button("إضافة العمود وحفظ", key="add_col_btn"):
                    if new_col_name:
                        df_col = sheets_edit[selected_sheet].astype(str)
                        df_col[new_col_name] = default_value
                        sheets_edit[selected_sheet] = df_col.astype(object)
                        new_sheets, error = auto_save_to_github(sheets_edit, f"إضافة عمود {new_col_name}")
                        if error:
                            error_container.error(f"⚠⚠⚠ فشل إضافة العمود: {error}")
                        else:
                            sheets_edit = new_sheets
                            st.success("تمت الإضافة والحفظ بنجاح")
                            st.rerun()
                    else:
                        error_container.warning("الرجاء إدخال اسم العمود.")
            
            with st.expander("🗑 حذف صفوف"):
                df_del = sheets_edit[selected_sheet].astype(str).reset_index(drop=True)
                st.dataframe(df_del, use_container_width=True)
                rows_to_delete = st.text_input("أرقام الصفوف (مفصولة بفاصلة):", key="rows_del")
                confirm = st.checkbox("تأكيد الحذف", key="confirm_del")
                if st.button("حذف وحفظ", key="del_rows_btn"):
                    if rows_to_delete and confirm:
                        try:
                            rows_list = [int(x.strip()) for x in rows_to_delete.split(",") if x.strip().isdigit()]
                            rows_list = [r for r in rows_list if 0 <= r < len(df_del)]
                            if rows_list:
                                df_new = df_del.drop(rows_list).reset_index(drop=True)
                                sheets_edit[selected_sheet] = df_new.astype(object)
                                new_sheets, error = auto_save_to_github(sheets_edit, f"حذف صفوف {rows_list}")
                                if error:
                                    error_container.error(f"⚠⚠⚠ فشل حذف الصفوف: {error}")
                                else:
                                    sheets_edit = new_sheets
                                    st.success("تم الحذف والحفظ بنجاح")
                                    st.rerun()
                            else:
                                error_container.warning("لم يتم العثور على صفوف صالحة للحذف.")
                        except Exception as e:
                            error_container.error(f"خطأ أثناء الحذف: {str(e)}")
