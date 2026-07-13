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
from difflib import get_close_matches

# GitHub
try:
    from github import Github
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

# ===============================
# إعدادات التطبيق
# ===============================
APP_CONFIG = {
    "APP_TITLE": "نظام إدارة مكبس القطن",
    "APP_ICON": "🏭",
    "REPO_NAME": "mahmedabdallh123/BELYARN",
    "BRANCH": "main",
    "FILE_PATH": "luva.xlsx",
    "LOCAL_FILE": "luva.xlsx",
    "MAX_ACTIVE_USERS": 5,
    "SESSION_DURATION_MINUTES": 11,
    "SHIFTS": {
        "الاولي": {"start": 8, "end": 16},
        "الثانيه": {"start": 16, "end": 24},
        "الثالثه": {"start": 0, "end": 8}
    }
}

USERS_FILE = "users.json"
STATE_FILE = "state.json"
CONFIG_FILE = "config.json"
SESSION_DURATION = timedelta(minutes=APP_CONFIG["SESSION_DURATION_MINUTES"])
MAX_ACTIVE_USERS = APP_CONFIG["MAX_ACTIVE_USERS"]
GITHUB_EXCEL_URL = f"https://github.com/{APP_CONFIG['REPO_NAME'].split('/')[0]}/{APP_CONFIG['REPO_NAME'].split('/')[1]}/raw/{APP_CONFIG['BRANCH']}/{APP_CONFIG['FILE_PATH']}"

# ---------- دوال إدارة التكوين ----------
def load_config():
    default_config = {
        "supervisors": ["انسT.A", "عبدالحميدT.B", "محمود فتحيT.C", "احمد عبالعزيزT.D"],
        "bale_types": ["قماش", "تراب", "هبوه دست", "اسطبات تدویر", "برم", "برم انفاق", "بلاستيك",
                       "هبوه تنظيف", "انفاق", "شرق الغزل", "تمشيط غير مغلف", "تمشيط مغلف", "مكس", "كرد", "قطن خام", "ملح"]
    }
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        return default_config
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            if "supervisors" not in config:
                config["supervisors"] = default_config["supervisors"]
            if "bale_types" not in config:
                config["bale_types"] = default_config["bale_types"]
            return config
    except Exception as e:
        st.error(f"خطأ في تحميل config.json: {e}")
        return default_config

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        token = st.secrets.get("github", {}).get("token", None)
        if token and GITHUB_AVAILABLE:
            try:
                g = Github(token)
                repo = g.get_repo(APP_CONFIG["REPO_NAME"])
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                try:
                    contents = repo.get_contents(CONFIG_FILE, ref=APP_CONFIG["BRANCH"])
                    repo.update_file(CONFIG_FILE, "تحديث التكوين", content, contents.sha, branch=APP_CONFIG["BRANCH"])
                except:
                    repo.create_file(CONFIG_FILE, "إنشاء ملف التكوين", content, branch=APP_CONFIG["BRANCH"])
            except:
                pass
        return True
    except Exception as e:
        st.error(f"خطأ في حفظ config.json: {e}")
        return False

def get_supervisors():
    config = load_config()
    return config.get("supervisors", [])

def get_bale_types():
    config = load_config()
    return config.get("bale_types", [])

# ---------- دوال المستخدمين والجلسات ----------
def load_users():
    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": {
                "password": "1111",
                "role": "admin",
                "created_at": datetime.now().isoformat(),
                "permissions": {"all_sections": True},
                "sections_permissions": {}
            },
            "user1": {
                "password": "12345",
                "role": "data_entry",
                "created_at": datetime.now().isoformat(),
                "permissions": {"all_sections": False},
                "sections_permissions": {}
            },
            "user2": {
                "password": "99999",
                "role": "viewer",
                "created_at": datetime.now().isoformat(),
                "permissions": {"all_sections": False},
                "sections_permissions": {}
            }
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_users, f, indent=4, ensure_ascii=False)
        return default_users
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
            for uname, udata in users.items():
                if "permissions" not in udata or isinstance(udata["permissions"], list):
                    if udata.get("role") == "admin":
                        udata["permissions"] = {"all_sections": True}
                    else:
                        udata["permissions"] = {"all_sections": False}
                if "sections_permissions" not in udata:
                    udata["sections_permissions"] = {}
                if "created_at" not in udata:
                    udata["created_at"] = datetime.now().isoformat()
            return users
    except Exception as e:
        st.error(f"خطأ في users.json: {e}")
        return {
            "admin": {"password": "1111", "role": "admin", "created_at": datetime.now().isoformat(),
                      "permissions": {"all_sections": True}, "sections_permissions": {}}
        }

def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4, ensure_ascii=False)
        token = st.secrets.get("github", {}).get("token", None)
        if token and GITHUB_AVAILABLE:
            try:
                g = Github(token)
                repo = g.get_repo(APP_CONFIG["REPO_NAME"])
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                try:
                    contents = repo.get_contents(USERS_FILE, ref=APP_CONFIG["BRANCH"])
                    repo.update_file(USERS_FILE, "تحديث المستخدمين", content, contents.sha, branch=APP_CONFIG["BRANCH"])
                except:
                    repo.create_file(USERS_FILE, "إنشاء ملف المستخدمين", content, branch=APP_CONFIG["BRANCH"])
            except:
                pass
        return True
    except Exception as e:
        st.error(f"خطأ في حفظ users.json: {e}")
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
    for k in list(st.session_state.keys()):
        st.session_state.pop(k, None)
    st.rerun()

def login_ui():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        username = st.session_state.username
        role = st.session_state.user_role
        state = load_state()
        rem = remaining_time(state, username)
        if rem:
            mins, secs = divmod(int(rem.total_seconds()), 60)
            st.success(f"مسجل كـ {username} ({role}) - الوقت المتبقي: {mins:02d}:{secs:02d}")
        else:
            st.warning("انتهت الجلسة")
            logout_action()
        if st.button("تسجيل الخروج"):
            logout_action()
        return True

    users = load_users()
    state = cleanup_sessions(load_state())
    
    st.title(f"{APP_CONFIG['APP_ICON']} تسجيل الدخول - {APP_CONFIG['APP_TITLE']}")
    username_input = st.selectbox("اختر المستخدم", list(users.keys()))
    password = st.text_input("كلمة المرور", type="password")
    active_users = [u for u, v in state.items() if v.get("active")]
    active_count = len(active_users)
    st.caption(f"المستخدمون النشطون: {active_count}/{MAX_ACTIVE_USERS}")

    if st.button("تسجيل الدخول"):
        if username_input in users and users[username_input]["password"] == password:
            if username_input == "admin":
                pass
            elif username_input in active_users:
                st.warning("هذا المستخدم مسجل دخول بالفعل")
                return False
            elif active_count >= MAX_ACTIVE_USERS:
                st.error("الحد الأقصى للمستخدمين المتصلين")
                return False
            
            state[username_input] = {"active": True, "login_time": datetime.now().isoformat()}
            save_state(state)
            st.session_state.logged_in = True
            st.session_state.username = username_input
            st.session_state.user_role = users[username_input].get("role", "viewer")
            st.session_state.user_permissions = users[username_input].get("permissions", {"all_sections": False})
            st.success(f"مرحباً {username_input}")
            st.rerun()
        else:
            st.error("كلمة المرور غير صحيحة")
            return False
    return False

# ---------- دوال الصلاحيات ----------
def get_user_permissions_dict(username):
    users = load_users()
    if username not in users:
        return {"all_sections": False, "sections_permissions": {}}
    user_data = users[username]
    perms = user_data.get("permissions", {})
    if isinstance(perms, list):
        if "all" in perms:
            perms = {"all_sections": True}
        else:
            perms = {"all_sections": False}
    if "sections_permissions" not in user_data:
        user_data["sections_permissions"] = {}
    return {
        "all_sections": perms.get("all_sections", False),
        "sections_permissions": user_data.get("sections_permissions", {})
    }

def is_admin(username):
    return username == "admin" or load_users().get(username, {}).get("role") == "admin"

# ---------- دوال GitHub والبيانات ----------
def fetch_from_github_requests():
    try:
        response = requests.get(GITHUB_EXCEL_URL, stream=True, timeout=15)
        response.raise_for_status()
        with open(APP_CONFIG["LOCAL_FILE"], "wb") as f:
            shutil.copyfileobj(response.raw, f)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"فشل التحديث: {e}")
        return False

@st.cache_data(show_spinner=False)
def load_cotton_data():
    if not os.path.exists(APP_CONFIG["LOCAL_FILE"]):
        create_new_cotton_file()
        return pd.DataFrame()
    try:
        df = pd.read_excel(APP_CONFIG["LOCAL_FILE"])
        required_cols = ['التاريخ', 'الوقت', 'الوردية', 'المشرف', 'نوع البالة', 'وزن البالة', 'ملاحظات']
        for col in required_cols:
            if col not in df.columns:
                df[col] = ""
        # تحويل عمود التاريخ إلى تاريخ للتسهيل
        df['التاريخ'] = pd.to_datetime(df['التاريخ'], errors='coerce').dt.date
        return df
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {e}")
        return pd.DataFrame()

def create_new_cotton_file():
    try:
        cols = ['التاريخ', 'الوقت', 'الوردية', 'المشرف', 'نوع البالة', 'وزن البالة', 'ملاحظات']
        df = pd.DataFrame(columns=cols)
        df.to_excel(APP_CONFIG["LOCAL_FILE"], index=False)
        return True
    except Exception as e:
        st.error(f"خطأ في إنشاء الملف: {e}")
        return False

def save_cotton_data(df, commit_message="تحديث"):
    try:
        # تحويل التاريخ إلى نص للـ Excel
        df_save = df.copy()
        df_save['التاريخ'] = pd.to_datetime(df_save['التاريخ'], errors='coerce').dt.strftime('%Y-%m-%d')
        df_save['الوقت'] = df_save['الوقت'].apply(lambda x: x.strftime('%H:%M:%S') if hasattr(x, 'strftime') else x)
        df_save.to_excel(APP_CONFIG["LOCAL_FILE"], index=False)
        st.cache_data.clear()
        token = st.secrets.get("github", {}).get("token", None)
        if token and GITHUB_AVAILABLE:
            try:
                g = Github(token)
                repo = g.get_repo(APP_CONFIG["REPO_NAME"])
                with open(APP_CONFIG["LOCAL_FILE"], "rb") as f:
                    content = f.read()
                try:
                    contents = repo.get_contents(APP_CONFIG["FILE_PATH"], ref=APP_CONFIG["BRANCH"])
                    repo.update_file(APP_CONFIG["FILE_PATH"], commit_message, content, contents.sha, branch=APP_CONFIG["BRANCH"])
                    st.success("✅ تم الحفظ والرفع إلى GitHub")
                except:
                    repo.create_file(APP_CONFIG["FILE_PATH"], commit_message, content, branch=APP_CONFIG["BRANCH"])
                    st.success("✅ تم إنشاء الملف على GitHub")
            except Exception as e:
                st.warning(f"⚠️ تم الحفظ محلياً فقط: {e}")
        return True
    except Exception as e:
        st.error(f"❌ خطأ في الحفظ: {e}")
        return False

# ---------- دوال النظام الأساسية ----------
def get_current_shift():
    now = datetime.now()
    h = now.hour
    for name, times in APP_CONFIG["SHIFTS"].items():
        if times["start"] <= h < times["end"]:
            return name
    return "الثالثه"

def add_new_record(df, supervisor, bale_type, weight, notes="", selected_date=None):
    now = datetime.now()
    record_date = selected_date if selected_date else now.date()
    new = {
        'التاريخ': record_date,
        'الوقت': now.time(),
        'الوردية': get_current_shift(),
        'المشرف': supervisor,
        'نوع البالة': bale_type,
        'وزن البالة': weight,
        'ملاحظات': notes
    }
    return new, pd.concat([df, pd.DataFrame([new])], ignore_index=True)

def generate_statistics(df, start_date, end_date, filter_bale_type=None, filter_supervisor=None):
    if df.empty:
        return pd.DataFrame(), None, None, None
    df['التاريخ'] = pd.to_datetime(df['التاريخ']).dt.date
    mask = (df['التاريخ'] >= start_date) & (df['التاريخ'] <= end_date)
    fdf = df[mask].copy()
    if fdf.empty:
        return pd.DataFrame(), None, None, None
    
    if filter_bale_type and filter_bale_type != "الكل":
        fdf = fdf[fdf['نوع البالة'] == filter_bale_type]
    
    if filter_supervisor and filter_supervisor != "الكل":
        fdf = fdf[fdf['المشرف'] == filter_supervisor]
    
    if fdf.empty:
        return pd.DataFrame(), None, None, None

    stats_by_type = fdf.groupby('نوع البالة').agg({
        'وزن البالة': ['count', 'sum', 'mean']
    }).round(2)
    stats_by_type.columns = ['عدد البالات', 'إجمالي الوزن', 'متوسط الوزن']
    stats_by_type = stats_by_type.reset_index()

    stats_by_supervisor = fdf.groupby('المشرف').agg({
        'وزن البالة': ['count', 'sum', 'mean']
    }).round(2)
    stats_by_supervisor.columns = ['عدد البالات', 'إجمالي الوزن', 'متوسط الوزن']
    stats_by_supervisor = stats_by_supervisor.reset_index()

    stats_by_shift = fdf.groupby('الوردية').agg({
        'وزن البالة': ['count', 'sum', 'mean']
    }).round(2)
    stats_by_shift.columns = ['عدد البالات', 'إجمالي الوزن', 'متوسط الوزن']
    stats_by_shift = stats_by_shift.reset_index()

    daily_data = fdf.groupby('التاريخ').agg({
        'وزن البالة': ['sum', 'count']
    }).round(2)
    daily_data.columns = ['إجمالي الوزن', 'عدد البالات']
    daily_data = daily_data.reset_index()
    daily_data = daily_data.sort_values('التاريخ')

    return stats_by_type, stats_by_supervisor, stats_by_shift, daily_data

def get_user_permissions(role, perms):
    if isinstance(perms, dict):
        if perms.get("all_sections", False):
            return {"can_input": True, "can_view_stats": True}
        else:
            if role == "admin":
                return {"can_input": True, "can_view_stats": True}
            elif role == "data_entry":
                return {"can_input": True, "can_view_stats": False}
            else:
                return {"can_input": False, "can_view_stats": True}
    else:
        if "all" in perms:
            return {"can_input": True, "can_view_stats": True}
        elif "data_entry" in perms:
            return {"can_input": True, "can_view_stats": False}
        elif "view_stats" in perms:
            return {"can_input": False, "can_view_stats": True}
        else:
            return {"can_input": False, "can_view_stats": True}

# =============================================================================
# تبويب إدارة البيانات (مع إضافة خيار التصفية الزمنية)
# =============================================================================
def data_management_tab():
    st.header("📝 إدارة البيانات (تعديل وحذف)")
    
    # عرض رسالة نجاح إذا وجدت
    if st.session_state.get("success_msg"):
        st.success(st.session_state.success_msg)
        del st.session_state.success_msg

    st.info("يمكنك تحديد نطاق زمني لعرض البيانات المراد تعديلها أو حذفها، ثم قم بالتعديل في الجدول واضغط 'حفظ التغييرات'.")

    # تحميل البيانات كاملة
    df_full = load_cotton_data()
    if df_full.empty:
        st.warning("لا توجد بيانات لعرضها")
        return

    # التأكد من أن التاريخ هو تاريخ
    df_full['التاريخ'] = pd.to_datetime(df_full['التاريخ'], errors='coerce').dt.date

    # واجهة تحديد النطاق الزمني
    col_date1, col_date2, col_btn1, col_btn2 = st.columns([2, 2, 1, 1])
    with col_date1:
        start_date = st.date_input("من", value=datetime.now().date() - timedelta(days=30), key="filter_start_date")
    with col_date2:
        end_date = st.date_input("إلى", value=datetime.now().date(), key="filter_end_date")
    with col_btn1:
        if st.button("تطبيق الفلتر", use_container_width=True):
            st.session_state.filter_start_date = start_date
            st.session_state.filter_end_date = end_date
            st.session_state.data_editor_df = None  # لإعادة تحميل البيانات المُفلترة
            st.rerun()
    with col_btn2:
        if st.button("إزالة الفلتر", use_container_width=True):
            if "filter_start_date" in st.session_state:
                del st.session_state.filter_start_date
            if "filter_end_date" in st.session_state:
                del st.session_state.filter_end_date
            st.session_state.data_editor_df = None
            st.rerun()

    # تحديد النطاق الفعلي
    if "filter_start_date" in st.session_state and "filter_end_date" in st.session_state:
        start_dt = st.session_state.filter_start_date
        end_dt = st.session_state.filter_end_date
        # فلترة البيانات
        df_filtered = df_full[(df_full['التاريخ'] >= start_dt) & (df_full['التاريخ'] <= end_dt)]
        st.caption(f"عرض {len(df_filtered)} سجل من {len(df_full)} الكلية للفترة من {start_dt} إلى {end_dt}")
    else:
        df_filtered = df_full.copy()
        st.caption(f"عرض جميع السجلات ({len(df_filtered)})")

    if df_filtered.empty:
        st.warning("لا توجد بيانات في النطاق الزمني المحدد")
        return

    # تحويل الوقت إلى نص
    def safe_time_to_str(t):
        try:
            if pd.isna(t):
                return "00:00:00"
            if isinstance(t, str):
                return t
            if hasattr(t, 'strftime'):
                return t.strftime('%H:%M:%S')
            if isinstance(t, datetime):
                return t.strftime('%H:%M:%S')
            return "00:00:00"
        except:
            return "00:00:00"

    df_filtered['الوقت'] = df_filtered['الوقت'].apply(safe_time_to_str)

    # إضافة عمود الحذف
    df_display = df_filtered.copy()
    df_display['حذف'] = False

    # استعادة البيانات المعدلة من الجلسة إن وجدت
    if 'data_editor_df' not in st.session_state or st.session_state.data_editor_df is None:
        st.session_state.data_editor_df = df_display

    # عرض المحرر
    edited_df = st.data_editor(
        st.session_state.data_editor_df,
        num_rows="dynamic",
        use_container_width=True,
        key="data_editor"
    )
    st.session_state.data_editor_df = edited_df

    if 'حذف' not in edited_df.columns:
        edited_df['حذف'] = False

    # أزرار التحكم
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        is_saving = st.session_state.get("saving", False)
        if st.button("💾 حفظ التغييرات", type="primary", use_container_width=True, disabled=is_saving):
            st.session_state.saving = True
            try:
                # إزالة عمود الحذف
                save_df = edited_df.drop(columns=['حذف'], errors='ignore')
                # التأكد من أن التاريخ هو تاريخ
                save_df['التاريخ'] = pd.to_datetime(save_df['التاريخ'], errors='coerce').dt.date
                # تحويل الوقت من نص إلى وقت
                def str_to_time(s):
                    try:
                        if pd.isna(s) or s == "":
                            return datetime.strptime("00:00:00", "%H:%M:%S").time()
                        if hasattr(s, 'strftime'):
                            return s
                        return datetime.strptime(s, '%H:%M:%S').time()
                    except:
                        return datetime.strptime("00:00:00", "%H:%M:%S").time()
                save_df['الوقت'] = save_df['الوقت'].apply(str_to_time)
                # حفظ البيانات
                if save_cotton_data(save_df, "تعديل البيانات يدوياً"):
                    st.session_state.success_msg = "✅ تم حفظ التغييرات بنجاح"
                    st.session_state.data_editor_df = None
                    st.session_state.saving = False
                    st.rerun()
                else:
                    st.session_state.saving = False
                    st.error("❌ فشل حفظ التغييرات")
            except Exception as e:
                st.session_state.saving = False
                st.error(f"❌ حدث خطأ: {e}")

    with col2:
        rows_to_delete = edited_df[edited_df['حذف'] == True] if 'حذف' in edited_df.columns else pd.DataFrame()
        if not rows_to_delete.empty:
            if st.button(f"🗑️ حذف {len(rows_to_delete)} صف", use_container_width=True):
                st.session_state.confirm_delete = True
                st.rerun()
        else:
            st.button("🗑️ حذف المحددات", disabled=True, use_container_width=True)

    with col3:
        if st.button("🔄 تحديث البيانات", use_container_width=True):
            st.cache_data.clear()
            st.session_state.data_editor_df = None
            st.rerun()

    # معالج التأكيد للحذف
    if st.session_state.get('confirm_delete', False):
        rows_to_delete = edited_df[edited_df['حذف'] == True] if 'حذف' in edited_df.columns else pd.DataFrame()
        if rows_to_delete.empty:
            st.session_state.confirm_delete = False
            st.rerun()
        st.warning(f"⚠️ سيتم حذف {len(rows_to_delete)} صف(وف). هل أنت متأكد؟")
        col_yes, col_no = st.columns(2)
        if col_yes.button("نعم، تأكيد الحذف", key="confirm_yes"):
            keep_df = edited_df[edited_df['حذف'] == False] if 'حذف' in edited_df.columns else edited_df
            save_df = keep_df.drop(columns=['حذف'], errors='ignore')
            save_df['التاريخ'] = pd.to_datetime(save_df['التاريخ'], errors='coerce').dt.date
            def str_to_time(s):
                try:
                    if pd.isna(s) or s == "":
                        return datetime.strptime("00:00:00", "%H:%M:%S").time()
                    if hasattr(s, 'strftime'):
                        return s
                    return datetime.strptime(s, '%H:%M:%S').time()
                except:
                    return datetime.strptime("00:00:00", "%H:%M:%S").time()
            save_df['الوقت'] = save_df['الوقت'].apply(str_to_time)
            if save_cotton_data(save_df, f"حذف {len(rows_to_delete)} صف"):
                st.session_state.success_msg = f"✅ تم حذف {len(rows_to_delete)} صف بنجاح"
                st.session_state.confirm_delete = False
                st.session_state.data_editor_df = None
                st.rerun()
            else:
                st.error("❌ فشل حذف الصفوف")
        if col_no.button("إلغاء", key="confirm_no"):
            st.session_state.confirm_delete = False
            st.rerun()

    st.markdown("---")
    st.subheader("📊 ملخص سريع")
    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي السجلات المعروضة", len(edited_df))
    if not edited_df.empty:
        col2.metric("إجمالي الوزن (المعروض)", f"{edited_df['وزن البالة'].sum():,.1f} كجم")
        col3.metric("متوسط الوزن (المعروض)", f"{edited_df['وزن البالة'].mean():.1f} كجم")

# ---------- تبويب إدارة التكوين ----------
def admin_config_management_tab():
    st.header("⚙️ إدارة المشرفين وأنواع البالات")
    st.info("هنا يمكنك إضافة أو حذف المشرفين وأنواع البالات. التغييرات تحفظ محلياً وعلى GitHub.")

    config = load_config()

    st.subheader("👨‍🏭 المشرفون")
    col1, col2 = st.columns([3, 1])
    with col1:
        new_supervisor = st.text_input("إضافة مشرف جديد", key="new_supervisor")
    with col2:
        if st.button("➕ إضافة مشرف", key="add_supervisor_btn"):
            if new_supervisor and new_supervisor.strip():
                if new_supervisor.strip() not in config["supervisors"]:
                    config["supervisors"].append(new_supervisor.strip())
                    if save_config(config):
                        st.success(f"✅ تم إضافة المشرف {new_supervisor.strip()}")
                        st.rerun()
                    else:
                        st.error("❌ فشل حفظ التغييرات")
                else:
                    st.warning("⚠️ هذا المشرف موجود بالفعل")
            else:
                st.warning("⚠️ الرجاء إدخال اسم المشرف")

    if config["supervisors"]:
        for sup in config["supervisors"]:
            col1, col2 = st.columns([4, 1])
            col1.write(f"• {sup}")
            if col2.button("🗑️", key=f"del_sup_{sup}"):
                if len(config["supervisors"]) <= 1:
                    st.warning("⚠️ لا يمكن حذف آخر مشرف، يجب أن يكون هناك مشرف واحد على الأقل")
                else:
                    config["supervisors"].remove(sup)
                    if save_config(config):
                        st.success(f"✅ تم حذف المشرف {sup}")
                        st.rerun()
                    else:
                        st.error("❌ فشل الحذف")
    else:
        st.warning("لا يوجد مشرفون، الرجاء إضافة مشرف")

    st.markdown("---")

    st.subheader("📦 أنواع البالات")
    col1, col2 = st.columns([3, 1])
    with col1:
        new_bale = st.text_input("إضافة نوع بالة جديد", key="new_bale")
    with col2:
        if st.button("➕ إضافة نوع", key="add_bale_btn"):
            if new_bale and new_bale.strip():
                if new_bale.strip() not in config["bale_types"]:
                    config["bale_types"].append(new_bale.strip())
                    if save_config(config):
                        st.success(f"✅ تم إضافة نوع البالة {new_bale.strip()}")
                        st.rerun()
                    else:
                        st.error("❌ فشل حفظ التغييرات")
                else:
                    st.warning("⚠️ هذا النوع موجود بالفعل")
            else:
                st.warning("⚠️ الرجاء إدخال نوع البالة")

    if config["bale_types"]:
        for btype in config["bale_types"]:
            col1, col2 = st.columns([4, 1])
            col1.write(f"• {btype}")
            if col2.button("🗑️", key=f"del_bale_{btype}"):
                if len(config["bale_types"]) <= 1:
                    st.warning("⚠️ لا يمكن حذف آخر نوع، يجب أن يكون هناك نوع واحد على الأقل")
                else:
                    config["bale_types"].remove(btype)
                    if save_config(config):
                        st.success(f"✅ تم حذف نوع البالة {btype}")
                        st.rerun()
                    else:
                        st.error("❌ فشل الحذف")
    else:
        st.warning("لا توجد أنواع بالات، الرجاء إضافة نوع")

# ---------- تبويب إدارة المستخدمين ----------
def admin_users_management_tab():
    st.header("👥 إدارة المستخدمين والصلاحيات")
    st.info("هنا يمكنك إضافة، تعديل، أو حذف المستخدمين وتحديد صلاحياتهم.")

    users = load_users()

    st.subheader("📋 قائمة المستخدمين")
    for username, info in users.items():
        with st.expander(f"👤 {username} (الدور: {info.get('role', 'viewer')})"):
            col1, col2 = st.columns(2)

            with col1:
                new_password = st.text_input(f"كلمة المرور الجديدة", type="password", key=f"pass_{username}")
                if new_password:
                    if st.button(f"🔐 تغيير كلمة المرور", key=f"change_pass_{username}"):
                        users[username]["password"] = new_password
                        if save_users(users):
                            st.success(f"✅ تم تغيير كلمة مرور {username}")
                            st.rerun()
                        else:
                            st.error("❌ فشل حفظ التغييرات")

            with col2:
                current_role = info.get("role", "viewer")
                role_options = ["admin", "data_entry", "viewer"]
                new_role = st.selectbox(f"الدور", role_options, index=role_options.index(current_role), key=f"role_{username}")
                if new_role != info.get("role"):
                    users[username]["role"] = new_role
                    if new_role == "admin":
                        users[username]["permissions"] = {"all_sections": True}
                    else:
                        users[username]["permissions"] = {"all_sections": False}
                    if save_users(users):
                        st.success(f"✅ تم تغيير دور {username} إلى {new_role}")
                        st.rerun()

            if username != "admin":
                st.markdown("---")
                if st.button(f"🗑️ حذف المستخدم {username}", key=f"delete_{username}"):
                    confirm = st.text_input(f"تأكيد الحذف - اكتب 'تم'", key=f"confirm_{username}")
                    if confirm == "تم":
                        del users[username]
                        if save_users(users):
                            st.success(f"✅ تم حذف {username}")
                            st.rerun()
                        else:
                            st.error("❌ فشل الحذف")
                    elif confirm:
                        st.warning("⚠️ أكتب 'تم' لتأكيد الحذف")

    st.markdown("---")
    st.subheader("➕ إضافة مستخدم جديد")
    with st.form("add_user_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_username = st.text_input("اسم المستخدم (حروف إنجليزية أو أرقام فقط)")
            new_password = st.text_input("كلمة المرور", type="password")
        with col2:
            new_role = st.selectbox("الدور الافتراضي", ["viewer", "data_entry", "admin"])

        submitted = st.form_submit_button("➕ إضافة المستخدم", type="primary")
        if submitted:
            if not new_username or not new_password:
                st.error("❌ اسم المستخدم وكلمة المرور مطلوبة")
            elif new_username in users:
                st.error(f"❌ المستخدم '{new_username}' موجود بالفعل")
            elif not new_username.replace("_", "").isalnum():
                st.error("❌ اسم المستخدم يجب أن يحتوي على حروف إنجليزية أو أرقام فقط")
            else:
                users[new_username] = {
                    "password": new_password,
                    "role": new_role,
                    "created_at": datetime.now().isoformat(),
                    "permissions": {"all_sections": True} if new_role == "admin" else {"all_sections": False},
                    "sections_permissions": {}
                }
                if save_users(users):
                    st.success(f"✅ تم إضافة المستخدم {new_username}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ فشل حفظ المستخدم الجديد")

# ===============================
# الواجهة الرئيسية
# ===============================
st.set_page_config(page_title=APP_CONFIG["APP_TITLE"], layout="wide")

with st.sidebar:
    st.header("الجلسة")
    logged = login_ui()
    if not logged:
        st.stop()
    
    st.markdown("---")
    if st.button("🔄 تحديث من GitHub"):
        if fetch_from_github_requests():
            st.rerun()
    if st.button("🗑 مسح الكاش"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    if st.button("🚪 تسجيل الخروج"):
        logout_action()

cotton_df = load_cotton_data()
st.title(f"{APP_CONFIG['APP_ICON']} {APP_CONFIG['APP_TITLE']}")

perms = get_user_permissions(
    st.session_state.get("user_role", "viewer"),
    st.session_state.get("user_permissions", {"all_sections": False})
)

tabs_list = []
if perms["can_input"]:
    tabs_list.append("📥 إدخال البيانات")
    tabs_list.append("📝 إدارة البيانات")
if perms["can_view_stats"]:
    tabs_list.append("📊 الإحصائيات المتقدمة")

if is_admin(st.session_state.get("username")):
    tabs_list.append("👥 إدارة المستخدمين")
    tabs_list.append("⚙️ إدارة التكوين")

if not tabs_list:
    tabs_list = ["📊 الإحصائيات المتقدمة"]

tabs = st.tabs(tabs_list)
idx = 0

# تبويب الإدخال اليدوي
if perms["can_input"] and "📥 إدخال البيانات" in tabs_list:
    with tabs[idx]:
        if st.session_state.get("success_msg"):
            st.success(st.session_state.success_msg)
            del st.session_state.success_msg
        
        st.header("إدخال بيانات البالات يدوياً")
        st.info(f"الوردية الحالية: {get_current_shift()} - الوقت الحالي: {datetime.now().strftime('%H:%M:%S')}")
        
        with st.form("manual"):
            col1, col2 = st.columns(2)
            with col1:
                selected_date = st.date_input("📅 التاريخ", value=datetime.now().date())
                sup = st.selectbox("المشرف", get_supervisors())
                btype = st.selectbox("نوع البالة", get_bale_types())
            with col2:
                w = st.number_input("الوزن (كجم)", min_value=0.0, step=0.1)
                note = st.text_input("ملاحظات")
            
            submitted = st.form_submit_button("حفظ", type="primary")
            if submitted:
                if w > 0:
                    _, new_df = add_new_record(cotton_df, sup, btype, w, note, selected_date=selected_date)
                    if save_cotton_data(new_df):
                        st.session_state.success_msg = "✅ تم حفظ البيانات بنجاح"
                        st.rerun()
                    else:
                        st.error("❌ فشل حفظ البيانات")
                else:
                    st.error("❌ أدخل وزناً صحيحاً")
    idx += 1

# تبويب إدارة البيانات
if perms["can_input"] and "📝 إدارة البيانات" in tabs_list:
    with tabs[idx]:
        data_management_tab()
    idx += 1

# تبويب الإحصائيات المتقدمة
if perms["can_view_stats"] and "📊 الإحصائيات المتقدمة" in tabs_list:
    with tabs[idx]:
        st.header("📊 الإحصائيات المتقدمة والرسوم البيانية")
        if cotton_df.empty:
            st.warning("لا توجد بيانات لعرض الإحصائيات")
        else:
            col1, col2 = st.columns(2)
            with col1:
                sd = st.date_input("من", datetime.now().date() - timedelta(days=30))
            with col2:
                ed = st.date_input("إلى", datetime.now().date())

            st.subheader("🔍 خيارات التصفية")
            col1, col2, col3 = st.columns(3)
            with col1:
                bale_options = ["الكل"] + get_bale_types()
                selected_bale = st.selectbox("نوع البالة", bale_options, key="filter_bale")
            with col2:
                supervisor_options = ["الكل"] + get_supervisors()
                selected_supervisor = st.selectbox("المشرف", supervisor_options, key="filter_supervisor")
            with col3:
                show_charts = st.checkbox("📈 إظهار الرسوم البيانية", value=True)

            if st.button("📈 عرض الإحصائيات", type="primary"):
                stats_by_type, stats_by_supervisor, stats_by_shift, daily_data = generate_statistics(
                    cotton_df, sd, ed,
                    filter_bale_type=selected_bale if selected_bale != "الكل" else None,
                    filter_supervisor=selected_supervisor if selected_supervisor != "الكل" else None
                )

                if stats_by_type.empty:
                    st.warning("⚠️ لا توجد بيانات تطابق معايير التصفية")
                else:
                    total_weight = stats_by_type['إجمالي الوزن'].sum() if not stats_by_type.empty else 0
                    total_bales = stats_by_type['عدد البالات'].sum() if not stats_by_type.empty else 0
                    avg_weight = total_weight / total_bales if total_bales > 0 else 0

                    col1, col2, col3 = st.columns(3)
                    col1.metric("إجمالي الوزن", f"{total_weight:,.1f} كجم")
                    col2.metric("عدد البالات", f"{total_bales:,}")
                    col3.metric("متوسط الوزن", f"{avg_weight:.1f} كجم")

                    st.markdown("---")

                    if show_charts:
                        if daily_data is not None and not daily_data.empty:
                            st.subheader("📈 اتجاه الوزن الإجمالي اليومي")
                            daily_weight = daily_data.set_index('التاريخ')['إجمالي الوزن']
                            st.line_chart(daily_weight, use_container_width=True)

                            st.subheader("📈 عدد البالات اليومي")
                            daily_count = daily_data.set_index('التاريخ')['عدد البالات']
                            st.line_chart(daily_count, use_container_width=True, color='#ff7f0e')

                        st.markdown("---")

                    st.subheader("📊 توزيع البالات حسب النوع")
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        if show_charts and not stats_by_type.empty:
                            bar_data = stats_by_type.set_index('نوع البالة')['إجمالي الوزن']
                            st.bar_chart(bar_data, use_container_width=True)
                        else:
                            st.info("الرسوم البيانية معطلة")
                    with col2:
                        st.dataframe(stats_by_type, use_container_width=True)

                    st.markdown("---")

                    st.subheader("👨‍🏭 أداء المشرفين")
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        if show_charts and not stats_by_supervisor.empty:
                            bar_sup = stats_by_supervisor.set_index('المشرف')['إجمالي الوزن']
                            st.bar_chart(bar_sup, use_container_width=True, color='#2ca02c')
                        else:
                            st.info("الرسوم البيانية معطلة")
                    with col2:
                        st.dataframe(stats_by_supervisor, use_container_width=True)

                    st.markdown("---")

                    st.subheader("🕒 توزيع الإنتاج حسب الوردية")
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        if show_charts and not stats_by_shift.empty:
                            shift_data = stats_by_shift.set_index('الوردية')['إجمالي الوزن']
                            st.bar_chart(shift_data, use_container_width=True, color='#d62728')
                        else:
                            st.info("الرسوم البيانية معطلة")
                    with col2:
                        st.dataframe(stats_by_shift, use_container_width=True)
    idx += 1

# تبويب إدارة المستخدمين
if is_admin(st.session_state.get("username")):
    with tabs[idx]:
        admin_users_management_tab()
    idx += 1

# تبويب إدارة التكوين
if is_admin(st.session_state.get("username")):
    with tabs[idx]:
        admin_config_management_tab()
    idx += 1
