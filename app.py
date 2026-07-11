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

# ---------- دوال إدارة التكوين (المشرفين وأنواع البالات) ----------
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
    users = load_users()
    state = cleanup_sessions(load_state())
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    st.title(f"{APP_CONFIG['APP_ICON']} تسجيل الدخول - {APP_CONFIG['APP_TITLE']}")
    username_input = st.selectbox("اختر المستخدم", list(users.keys()))
    password = st.text_input("كلمة المرور", type="password")
    active_users = [u for u, v in state.items() if v.get("active")]
    active_count = len(active_users)
    st.caption(f"المستخدمون النشطون: {active_count}/{MAX_ACTIVE_USERS}")

    if not st.session_state.logged_in:
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
    else:
        username = st.session_state.username
        role = st.session_state.user_role
        st.success(f"مسجل كـ {username} ({role})")
        rem = remaining_time(state, username)
        if rem:
            mins, secs = divmod(int(rem.total_seconds()), 60)
            st.info(f"الوقت المتبقي: {mins:02d}:{secs:02d}")
        else:
            st.warning("انتهت الجلسة")
            logout_action()
        if st.button("تسجيل الخروج"):
            logout_action()
        return True

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
        df.to_excel(APP_CONFIG["LOCAL_FILE"], index=False)
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

def add_new_record(df, supervisor, bale_type, weight, notes=""):
    now = datetime.now()
    new = {
        'التاريخ': now.date(),
        'الوقت': now.time(),
        'الوردية': get_current_shift(),
        'المشرف': supervisor,
        'نوع البالة': bale_type,
        'وزن البالة': weight,
        'ملاحظات': notes
    }
    return new, pd.concat([df, pd.DataFrame([new])], ignore_index=True)

def generate_statistics(df, start_date, end_date, filter_bale_type=None, filter_shift=None):
    if df.empty:
        return pd.DataFrame(), None, None, None
    df['التاريخ'] = pd.to_datetime(df['التاريخ']).dt.date
    mask = (df['التاريخ'] >= start_date) & (df['التاريخ'] <= end_date)
    fdf = df[mask].copy()
    if fdf.empty:
        return pd.DataFrame(), None, None, None
    
    if filter_bale_type and filter_bale_type != "الكل":
        fdf = fdf[fdf['نوع البالة'] == filter_bale_type]
    
    if filter_shift and filter_shift != "الكل":
        fdf = fdf[fdf['الوردية'] == filter_shift]
    
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

# ---------- تبويب إدارة البيانات (تعديل وحذف) - نسخة آمنة ----------
def data_management_tab():
    st.header("📝 إدارة البيانات (تعديل وحذف)")
    st.info("يمكنك تعديل الخلايا مباشرة أو حذف صفوف محددة. اضغط 'حفظ التغييرات' بعد التعديل.")
    
    df = load_cotton_data()
    if df.empty:
        st.warning("لا توجد بيانات لعرضها")
        return
    
    # عرض البيانات كجدول فقط (لاستعراض) مع زر حذف لكل صف
    st.subheader("📋 عرض البيانات")
    
    # عرض البيانات مع أزرار حذف
    for idx, row in df.iterrows():
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1.5, 1.5, 1, 1.5, 1.5, 1, 1.5, 0.5])
        col1.write(row['التاريخ'])
        col2.write(row['الوقت'])
        col3.write(row['الوردية'])
        col4.write(row['المشرف'])
        col5.write(row['نوع البالة'])
        col6.write(f"{row['وزن البالة']:.1f}")
        col7.write(row['ملاحظات'])
        if col8.button("🗑️", key=f"del_{idx}"):
            # حذف الصف
            df_dropped = df.drop(idx)
            if save_cotton_data(df_dropped, f"حذف صف {idx}"):
                st.success(f"✅ تم حذف الصف بنجاح")
                st.rerun()
            else:
                st.error("❌ فشل حذف الصف")
    
    # إضافة نموذج لإضافة بيانات جديدة بسرعة
    st.markdown("---")
    st.subheader("➕ إضافة سجل جديد")
    with st.form("quick_add"):
        col1, col2 = st.columns(2)
        with col1:
            sup = st.selectbox("المشرف", get_supervisors(), key="quick_sup")
            btype = st.selectbox("نوع البالة", get_bale_types(), key="quick_btype")
        with col2:
            w = st.number_input("الوزن (كجم)", min_value=0.0, step=0.1, key="quick_weight")
            note = st.text_input("ملاحظات", key="quick_note")
        if st.form_submit_button("➕ إضافة"):
            if w > 0:
                _, new_df = add_new_record(df, sup, btype, w, note)
                if save_cotton_data(new_df):
                    st.success("✅ تم إضافة السجل بنجاح")
                    st.rerun()
            else:
                st.error("❌ أدخل وزناً صحيحاً")
    
    # عرض ملخص سريع
    st.markdown("---")
    st.subheader("📊 ملخص سريع")
    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي السجلات", len(df))
    if not df.empty:
        col2.metric("إجمالي الوزن", f"{df['وزن البالة'].sum():,.1f} كجم")
        col3.metric("متوسط الوزن", f"{df['وزن البالة'].mean():.1f} كجم")

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
                    confirm = st.text_input(f"تأكيد الحذف - اكتب YES", key=f"confirm_{username}")
                    if confirm == "YES":
                        del users[username]
                        if save_users(users):
                            st.success(f"✅ تم حذف {username}")
                            st.rerun()
                        else:
                            st.error("❌ فشل الحذف")

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
    if not st.session_state.get("logged_in"):
        if not login_ui():
            st.stop()
    else:
        state = cleanup_sessions(load_state())
        user = st.session_state.username
        role = st.session_state.user_role
        rem = remaining_time(state, user)
        if rem:
            m, s = divmod(int(rem.total_seconds()), 60)
            st.success(f"👋 {user} | {role} | ⏳ {m:02d}:{s:02d}")
        else:
            logout_action()
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
        st.header("إدخال بيانات البالات يدوياً")
        st.info(f"الوردية الحالية: {get_current_shift()} - {datetime.now()}")
        with st.form("manual"):
            col1, col2 = st.columns(2)
            with col1:
                sup = st.selectbox("المشرف", get_supervisors())
                btype = st.selectbox("نوع البالة", get_bale_types())
            with col2:
                w = st.number_input("الوزن (كجم)", min_value=0.0, step=0.1)
                note = st.text_input("ملاحظات")
            if st.form_submit_button("حفظ"):
                if w > 0:
                    _, new_df = add_new_record(cotton_df, sup, btype, w, note)
                    if save_cotton_data(new_df):
                        st.success("✅ تم حفظ البيانات بنجاح")
                        st.rerun()
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
                shift_options = ["الكل"] + list(APP_CONFIG["SHIFTS"].keys())
                selected_shift = st.selectbox("الوردية", shift_options, key="filter_shift")
            with col3:
                show_charts = st.checkbox("📈 إظهار الرسوم البيانية", value=True)

            if st.button("📈 عرض الإحصائيات", type="primary"):
                stats_by_type, stats_by_supervisor, stats_by_shift, daily_data = generate_statistics(
                    cotton_df, sd, ed, selected_bale if selected_bale != "الكل" else None,
                    selected_shift if selected_shift != "الكل" else None
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
