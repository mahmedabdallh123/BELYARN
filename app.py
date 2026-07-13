import streamlit as st
import pandas as pd
import json
import os
import requests
import shutil
from datetime import datetime, timedelta
from github import Github

# --------------------------------
# 1. الإعدادات والتكوين
# --------------------------------
APP_CONFIG = {
    "TITLE": "نظام إدارة مكبس القطن",
    "ICON": "🏭",
    "REPO": "mahmedabdallh123/BELYARN",
    "BRANCH": "main",
    "EXCEL_FILE": "luva.xlsx",
    "MAX_USERS": 5,
    "SESSION_MINUTES": 20,
    "SHIFTS": {
        "الاولي": (8, 16),
        "الثانيه": (16, 24),
        "الثالثه": (0, 8)
    }
}

USERS_FILE = "users.json"
STATE_FILE = "state.json"
CONFIG_FILE = "config.json"
SESSION_DURATION = timedelta(minutes=APP_CONFIG["SESSION_MINUTES"])
EXCEL_PATH = APP_CONFIG["EXCEL_FILE"]
GITHUB_EXCEL_URL = f"https://raw.githubusercontent.com/{APP_CONFIG['REPO']}/{APP_CONFIG['BRANCH']}/{APP_CONFIG['EXCEL_FILE']}"

# --------------------------------
# 2. دوال التعامل مع الملفات
# --------------------------------
def load_json(filename, default):
    if not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4, ensure_ascii=False)
        return default
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    # رفع إلى GitHub إذا كان متاحاً
    token = st.secrets.get("github", {}).get("token")
    if token:
        try:
            g = Github(token)
            repo = g.get_repo(APP_CONFIG["REPO"])
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            try:
                contents = repo.get_contents(filename, ref=APP_CONFIG["BRANCH"])
                repo.update_file(filename, f"تحديث {filename}", content, contents.sha, branch=APP_CONFIG["BRANCH"])
            except:
                repo.create_file(filename, f"إنشاء {filename}", content, branch=APP_CONFIG["BRANCH"])
        except:
            pass

# --------------------------------
# 3. دوال التكوين (المشرفين والأنواع)
# --------------------------------
def load_config():
    default = {
        "supervisors": ["انسT.A", "عبدالحميدT.B", "محمود فتحيT.C", "احمد عبالعزيزT.D"],
        "bale_types": ["قماش", "تراب", "هبوه دست", "اسطبات تدویر", "برم", "برم انفاق", "بلاستيك",
                       "هبوه تنظيف", "انفاق", "شرق الغزل", "تمشيط غير مغلف", "تمشيط مغلف", "مكس", "كرد", "قطن خام", "ملح"]
    }
    return load_json(CONFIG_FILE, default)

def save_config(config):
    save_json(CONFIG_FILE, config)

def get_supervisors():
    return load_config().get("supervisors", [])

def get_bale_types():
    return load_config().get("bale_types", [])

# --------------------------------
# 4. دوال المستخدمين والجلسات
# --------------------------------
def load_users():
    default = {
        "admin": {"password": "1111", "role": "admin", "created_at": datetime.now().isoformat(),
                  "permissions": {"all_sections": True}, "sections_permissions": {}},
        "user1": {"password": "12345", "role": "data_entry", "created_at": datetime.now().isoformat(),
                  "permissions": {"all_sections": False}, "sections_permissions": {}},
        "user2": {"password": "99999", "role": "viewer", "created_at": datetime.now().isoformat(),
                  "permissions": {"all_sections": False}, "sections_permissions": {}}
    }
    users = load_json(USERS_FILE, default)
    # إصلاح الهيكل القديم إن وجد
    for uname, data in users.items():
        if "permissions" not in data or isinstance(data["permissions"], list):
            data["permissions"] = {"all_sections": data.get("role") == "admin"}
        if "sections_permissions" not in data:
            data["sections_permissions"] = {}
        if "created_at" not in data:
            data["created_at"] = datetime.now().isoformat()
    return users

def save_users(users):
    save_json(USERS_FILE, users)

def load_state():
    return load_json(STATE_FILE, {})

def save_state(state):
    save_json(STATE_FILE, state)

def cleanup_sessions():
    state = load_state()
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

def remaining_time(username):
    state = load_state()
    if username not in state or not state[username].get("active"):
        return None
    try:
        lt = datetime.fromisoformat(state[username]["login_time"])
        remaining = SESSION_DURATION - (datetime.now() - lt)
        return remaining if remaining.total_seconds() > 0 else None
    except:
        return None

def logout():
    username = st.session_state.get("username")
    if username:
        state = load_state()
        if username in state:
            state[username]["active"] = False
            state[username].pop("login_time", None)
            save_state(state)
    for key in list(st.session_state.keys()):
        st.session_state.pop(key)
    st.rerun()

def login_ui():
    if st.session_state.get("logged_in"):
        username = st.session_state.username
        role = st.session_state.user_role
        rem = remaining_time(username)
        if rem:
            mins, secs = divmod(int(rem.total_seconds()), 60)
            st.success(f"مسجل كـ {username} ({role}) - الوقت المتبقي: {mins:02d}:{secs:02d}")
        else:
            st.warning("انتهت الجلسة")
            logout()
        return True

    users = load_users()
    state = cleanup_sessions()
    st.title(f"{APP_CONFIG['ICON']} تسجيل الدخول - {APP_CONFIG['TITLE']}")
    username = st.selectbox("اختر المستخدم", list(users.keys()))
    password = st.text_input("كلمة المرور", type="password")
    active_count = sum(1 for v in state.values() if v.get("active"))
    st.caption(f"المستخدمون النشطون: {active_count}/{APP_CONFIG['MAX_USERS']}")

    if st.button("تسجيل الدخول"):
        if username in users and users[username]["password"] == password:
            if username != "admin" and state.get(username, {}).get("active"):
                st.warning("هذا المستخدم مسجل دخول بالفعل")
                return False
            if username != "admin" and active_count >= APP_CONFIG["MAX_USERS"]:
                st.error("الحد الأقصى للمستخدمين المتصلين")
                return False
            state[username] = {"active": True, "login_time": datetime.now().isoformat()}
            save_state(state)
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.user_role = users[username].get("role", "viewer")
            st.session_state.user_permissions = users[username].get("permissions", {"all_sections": False})
            st.success(f"مرحباً {username}")
            st.rerun()
        else:
            st.error("كلمة المرور غير صحيحة")
    return False

def is_admin():
    return st.session_state.get("user_role") == "admin"

def get_permissions():
    role = st.session_state.get("user_role", "viewer")
    perms = st.session_state.get("user_permissions", {"all_sections": False})
    if perms.get("all_sections"):
        return {"can_input": True, "can_view_stats": True}
    if role == "admin":
        return {"can_input": True, "can_view_stats": True}
    if role == "data_entry":
        return {"can_input": True, "can_view_stats": False}
    return {"can_input": False, "can_view_stats": True}

# --------------------------------
# 5. دوال بيانات القطن (Excel)
# --------------------------------
def fetch_excel():
    try:
        r = requests.get(GITHUB_EXCEL_URL, stream=True, timeout=15)
        r.raise_for_status()
        with open(EXCEL_PATH, "wb") as f:
            shutil.copyfileobj(r.raw, f)
        st.cache_data.clear()
        return True
    except:
        return False

@st.cache_data(show_spinner=False)
def load_cotton_data():
    if not os.path.exists(EXCEL_PATH):
        create_empty_excel()
        return pd.DataFrame()
    try:
        df = pd.read_excel(EXCEL_PATH)
        required = ['التاريخ', 'الوقت', 'الوردية', 'المشرف', 'نوع البالة', 'وزن البالة', 'ملاحظات']
        for col in required:
            if col not in df.columns:
                df[col] = ""
        df['التاريخ'] = pd.to_datetime(df['التاريخ'], errors='coerce').dt.date
        return df
    except:
        return pd.DataFrame()

def create_empty_excel():
    cols = ['التاريخ', 'الوقت', 'الوردية', 'المشرف', 'نوع البالة', 'وزن البالة', 'ملاحظات']
    pd.DataFrame(columns=cols).to_excel(EXCEL_PATH, index=False)

def save_cotton_data(df, msg="تحديث"):
    try:
        df_save = df.copy()
        df_save['التاريخ'] = pd.to_datetime(df_save['التاريخ'], errors='coerce').dt.strftime('%Y-%m-%d')
        df_save['الوقت'] = df_save['الوقت'].apply(lambda x: x.strftime('%H:%M:%S') if hasattr(x, 'strftime') else x)
        df_save.to_excel(EXCEL_PATH, index=False)
        st.cache_data.clear()
        # رفع إلى GitHub
        token = st.secrets.get("github", {}).get("token")
        if token:
            try:
                g = Github(token)
                repo = g.get_repo(APP_CONFIG["REPO"])
                with open(EXCEL_PATH, "rb") as f:
                    content = f.read()
                try:
                    contents = repo.get_contents(APP_CONFIG["EXCEL_FILE"], ref=APP_CONFIG["BRANCH"])
                    repo.update_file(APP_CONFIG["EXCEL_FILE"], msg, content, contents.sha, branch=APP_CONFIG["BRANCH"])
                except:
                    repo.create_file(APP_CONFIG["EXCEL_FILE"], msg, content, branch=APP_CONFIG["BRANCH"])
            except:
                pass
        return True
    except:
        return False

def get_current_shift():
    h = datetime.now().hour
    for name, (start, end) in APP_CONFIG["SHIFTS"].items():
        if start <= h < end:
            return name
    return "الثالثه"

# تم تعديل هذه الدالة للتحقق من التكرار
def add_record(df, supervisor, bale_type, weight, note="", selected_date=None):
    now = datetime.now()
    record_date = selected_date or now.date()
    # التحقق من وجود سجل مكرر بنفس التاريخ والمشرف والنوع والوزن
    duplicate = df[
        (df['التاريخ'] == record_date) &
        (df['المشرف'] == supervisor) &
        (df['نوع البالة'] == bale_type) &
        (df['وزن البالة'] == weight)
    ]
    if not duplicate.empty:
        return None  # يعني مكرر
    record = {
        'التاريخ': record_date,
        'الوقت': now.time(),
        'الوردية': get_current_shift(),
        'المشرف': supervisor,
        'نوع البالة': bale_type,
        'وزن البالة': weight,
        'ملاحظات': note
    }
    return pd.concat([df, pd.DataFrame([record])], ignore_index=True)

# --------------------------------
# 6. دوال الإحصائيات
# --------------------------------
def generate_stats(df, start, end, filter_bale=None, filter_supervisor=None):
    if df.empty:
        return None, None, None, None
    df['التاريخ'] = pd.to_datetime(df['التاريخ']).dt.date
    mask = (df['التاريخ'] >= start) & (df['التاريخ'] <= end)
    fdf = df[mask].copy()
    if fdf.empty:
        return None, None, None, None
    if filter_bale and filter_bale != "الكل":
        fdf = fdf[fdf['نوع البالة'] == filter_bale]
    if filter_supervisor and filter_supervisor != "الكل":
        fdf = fdf[fdf['المشرف'] == filter_supervisor]
    if fdf.empty:
        return None, None, None, None

    by_type = fdf.groupby('نوع البالة').agg({'وزن البالة': ['count', 'sum', 'mean']}).round(2)
    by_type.columns = ['عدد البالات', 'إجمالي الوزن', 'متوسط الوزن']
    by_type = by_type.reset_index()

    by_sup = fdf.groupby('المشرف').agg({'وزن البالة': ['count', 'sum', 'mean']}).round(2)
    by_sup.columns = ['عدد البالات', 'إجمالي الوزن', 'متوسط الوزن']
    by_sup = by_sup.reset_index()

    by_shift = fdf.groupby('الوردية').agg({'وزن البالة': ['count', 'sum', 'mean']}).round(2)
    by_shift.columns = ['عدد البالات', 'إجمالي الوزن', 'متوسط الوزن']
    by_shift = by_shift.reset_index()

    daily = fdf.groupby('التاريخ').agg({'وزن البالة': ['sum', 'count']}).round(2)
    daily.columns = ['إجمالي الوزن', 'عدد البالات']
    daily = daily.reset_index().sort_values('التاريخ')

    return by_type, by_sup, by_shift, daily

# --------------------------------
# 7. تبويب إدخال البيانات (مع رسائل ومنع التكرار)
# --------------------------------
def input_tab(df):
    st.header("📥 إدخال بيانات البالات")
    st.info(f"الوردية الحالية: {get_current_shift()} - الوقت: {datetime.now().strftime('%H:%M:%S')}")
    with st.form("input_form"):
        cols = st.columns(2)
        with cols[0]:
            date = st.date_input("📅 التاريخ", datetime.now().date())
            sup = st.selectbox("المشرف", get_supervisors())
            btype = st.selectbox("نوع البالة", get_bale_types())
        with cols[1]:
            weight = st.number_input("الوزن (كجم)", min_value=0.0, step=0.1)
            note = st.text_input("ملاحظات")
        submitted = st.form_submit_button("حفظ", type="primary")
        if submitted:
            if weight > 0:
                new_df = add_record(df, sup, btype, weight, note, date)
                if new_df is not None:
                    if save_cotton_data(new_df, "إدخال جديد"):
                        st.session_state.success_msg = "✅ تم حفظ البيانات بنجاح"
                        st.rerun()
                    else:
                        st.error("❌ فشل حفظ البيانات")
                else:
                    st.warning("⚠️ سجل مكرر! نفس التاريخ، المشرف، النوع والوزن موجود بالفعل.")
            else:
                st.error("❌ أدخل وزناً صحيحاً")

# --------------------------------
# 8. تبويب إدارة البيانات (مع فلاتر التاريخ والمشرف)
# --------------------------------
def management_tab(df_full):
    st.header("📝 إدارة البيانات (تعديل وحذف)")
    if st.session_state.get("success_msg"):
        st.success(st.session_state.success_msg)
        del st.session_state.success_msg

    st.info("حدد نطاقاً زمنياً و/أو مشرفاً، ثم عدّل في الجدول واحفظ.")

    # فلترة
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    with col1:
        start = st.date_input("من", st.session_state.get('filter_start', datetime.now().date() - timedelta(days=30)),
                              key="start_inp")
    with col2:
        end = st.date_input("إلى", st.session_state.get('filter_end', datetime.now().date()), key="end_inp")
    with col3:
        sup_list = ["الكل"] + get_supervisors()
        default_sup = st.session_state.get('filter_sup', "الكل")
        sup = st.selectbox("المشرف", sup_list, index=sup_list.index(default_sup) if default_sup in sup_list else 0,
                           key="sup_inp")
    with col4:
        if st.button("تطبيق الفلتر", use_container_width=True):
            st.session_state['filter_start'] = start
            st.session_state['filter_end'] = end
            st.session_state['filter_sup'] = sup
            st.session_state.data_editor_df = None
            st.rerun()
        if st.button("إزالة الفلتر", use_container_width=True):
            for k in ['filter_start', 'filter_end', 'filter_sup']:
                st.session_state.pop(k, None)
            st.session_state.data_editor_df = None
            st.rerun()

    # تطبيق الفلاتر
    df_filtered = df_full.copy()
    if 'filter_start' in st.session_state and 'filter_end' in st.session_state:
        df_filtered = df_filtered[(df_filtered['التاريخ'] >= st.session_state['filter_start']) &
                                  (df_filtered['التاريخ'] <= st.session_state['filter_end'])]
    if 'filter_sup' in st.session_state and st.session_state['filter_sup'] != "الكل":
        df_filtered = df_filtered[df_filtered['المشرف'] == st.session_state['filter_sup']]

    st.caption(f"عرض {len(df_filtered)} سجل من {len(df_full)}")

    if df_filtered.empty:
        st.warning("لا توجد بيانات تطابق المعايير")
        return

    # تحضير البيانات للعرض
    df_display = df_filtered.copy()
    df_display['التاريخ'] = pd.to_datetime(df_display['التاريخ']).dt.date
    df_display['الوقت'] = df_display['الوقت'].apply(
        lambda t: t.strftime('%H:%M:%S') if hasattr(t, 'strftime') else str(t)
    )
    df_display['حذف'] = False

    if 'data_editor_df' not in st.session_state or st.session_state.data_editor_df is None:
        st.session_state.data_editor_df = df_display

    edited = st.data_editor(st.session_state.data_editor_df, num_rows="dynamic", use_container_width=True, key="editor")
    st.session_state.data_editor_df = edited

    if 'حذف' not in edited.columns:
        edited['حذف'] = False

    # أزرار التحكم
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("💾 حفظ التغييرات", type="primary", use_container_width=True,
                     disabled=st.session_state.get('saving', False)):
            st.session_state.saving = True
            try:
                save_df = edited.drop(columns=['حذف'], errors='ignore')
                save_df['التاريخ'] = pd.to_datetime(save_df['التاريخ'], errors='coerce').dt.date
                save_df['الوقت'] = save_df['الوقت'].apply(
                    lambda x: datetime.strptime(str(x), '%H:%M:%S').time() if isinstance(x, str) else x
                )
                if save_cotton_data(save_df, "تعديل البيانات"):
                    st.session_state.success_msg = "✅ تم حفظ التغييرات"
                    st.session_state.data_editor_df = None
                    st.session_state.saving = False
                    st.rerun()
                else:
                    st.session_state.saving = False
                    st.error("❌ فشل الحفظ")
            except Exception as e:
                st.session_state.saving = False
                st.error(f"❌ خطأ: {e}")

    with c2:
        to_delete = edited[edited['حذف'] == True] if 'حذف' in edited.columns else pd.DataFrame()
        if not to_delete.empty:
            if st.button(f"🗑️ حذف {len(to_delete)} صف", use_container_width=True):
                st.session_state.confirm_delete = True
                st.rerun()
        else:
            st.button("🗑️ حذف المحددات", disabled=True, use_container_width=True)

    with c3:
        if st.button("🔄 تحديث", use_container_width=True):
            st.cache_data.clear()
            st.session_state.data_editor_df = None
            st.rerun()

    # تأكيد الحذف
    if st.session_state.get('confirm_delete', False):
        to_delete = edited[edited['حذف'] == True] if 'حذف' in edited.columns else pd.DataFrame()
        if to_delete.empty:
            st.session_state.confirm_delete = False
            st.rerun()
        st.warning(f"⚠️ سيتم حذف {len(to_delete)} صف. هل أنت متأكد؟")
        col_yes, col_no = st.columns(2)
        if col_yes.button("نعم", key="del_yes"):
            keep = edited[edited['حذف'] == False] if 'حذف' in edited.columns else edited
            save_df = keep.drop(columns=['حذف'], errors='ignore')
            save_df['التاريخ'] = pd.to_datetime(save_df['التاريخ'], errors='coerce').dt.date
            save_df['الوقت'] = save_df['الوقت'].apply(
                lambda x: datetime.strptime(str(x), '%H:%M:%S').time() if isinstance(x, str) else x
            )
            if save_cotton_data(save_df, f"حذف {len(to_delete)} صف"):
                st.session_state.success_msg = f"✅ تم حذف {len(to_delete)} صف"
                st.session_state.confirm_delete = False
                st.session_state.data_editor_df = None
                st.rerun()
            else:
                st.error("❌ فشل الحذف")
        if col_no.button("إلغاء", key="del_no"):
            st.session_state.confirm_delete = False
            st.rerun()

    # ملخص
    st.markdown("---")
    st.subheader("📊 ملخص")
    c1, c2, c3 = st.columns(3)
    c1.metric("السجلات المعروضة", len(edited))
    if not edited.empty:
        c2.metric("إجمالي الوزن", f"{edited['وزن البالة'].sum():,.1f} كجم")
        c3.metric("المتوسط", f"{edited['وزن البالة'].mean():.1f} كجم")

# --------------------------------
# 9. تبويب الإحصائيات المتقدمة
# --------------------------------
def stats_tab(df):
    st.header("📊 الإحصائيات المتقدمة")
    if df.empty:
        st.warning("لا توجد بيانات")
        return

    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("من", datetime.now().date() - timedelta(days=30))
    with col2:
        end = st.date_input("إلى", datetime.now().date())

    with st.expander("🔍 خيارات التصفية", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            bale_types = ["الكل"] + get_bale_types()
            selected_bale = st.selectbox("نوع البالة", bale_types, key="stat_bale")
        with c2:
            sup_list = ["الكل"] + get_supervisors()
            selected_sup = st.selectbox("المشرف", sup_list, key="stat_sup")
        with c3:
            show_charts = st.checkbox("📈 إظهار الرسوم البيانية", value=True)

    if st.button("📈 عرض الإحصائيات", type="primary"):
        by_type, by_sup, by_shift, daily = generate_stats(df, start, end, selected_bale, selected_sup)
        if by_type is None:
            st.warning("⚠️ لا توجد بيانات تطابق المعايير")
            return

        total_weight = by_type['إجمالي الوزن'].sum()
        total_bales = by_type['عدد البالات'].sum()
        avg = total_weight / total_bales if total_bales else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي الوزن", f"{total_weight:,.1f} كجم")
        c2.metric("عدد البالات", f"{total_bales:,}")
        c3.metric("متوسط الوزن", f"{avg:.1f} كجم")

        st.markdown("---")

        if show_charts and daily is not None and not daily.empty:
            st.subheader("📈 اتجاه الوزن اليومي")
            st.line_chart(daily.set_index('التاريخ')['إجمالي الوزن'], use_container_width=True)
            st.subheader("📈 عدد البالات اليومي")
            st.line_chart(daily.set_index('التاريخ')['عدد البالات'], use_container_width=True, color='#ff7f0e')
            st.markdown("---")

        st.subheader("📊 توزيع البالات حسب النوع")
        c1, c2 = st.columns([2, 1])
        with c1:
            if show_charts and not by_type.empty:
                st.bar_chart(by_type.set_index('نوع البالة')['إجمالي الوزن'], use_container_width=True)
            else:
                st.info("الرسوم البيانية معطلة")
        with c2:
            st.dataframe(by_type, use_container_width=True)

        st.subheader("👨‍🏭 أداء المشرفين")
        c1, c2 = st.columns([2, 1])
        with c1:
            if show_charts and not by_sup.empty:
                st.bar_chart(by_sup.set_index('المشرف')['إجمالي الوزن'], use_container_width=True, color='#2ca02c')
            else:
                st.info("الرسوم البيانية معطلة")
        with c2:
            st.dataframe(by_sup, use_container_width=True)

        st.subheader("🕒 توزيع الإنتاج حسب الوردية")
        c1, c2 = st.columns([2, 1])
        with c1:
            if show_charts and not by_shift.empty:
                st.bar_chart(by_shift.set_index('الوردية')['إجمالي الوزن'], use_container_width=True, color='#d62728')
            else:
                st.info("الرسوم البيانية معطلة")
        with c2:
            st.dataframe(by_shift, use_container_width=True)

# --------------------------------
# 10. تبويبات الإدارة (المستخدمين والتكوين)
# --------------------------------
def users_management_tab():
    st.header("👥 إدارة المستخدمين")
    users = load_users()

    for username, info in users.items():
        with st.expander(f"👤 {username} ({info.get('role')})"):
            col1, col2 = st.columns(2)
            with col1:
                new_pass = st.text_input("كلمة المرور الجديدة", type="password", key=f"pass_{username}")
                if new_pass and st.button(f"🔐 تغيير", key=f"chpass_{username}"):
                    users[username]["password"] = new_pass
                    save_users(users)
                    st.success("تم التغيير")
                    st.rerun()
            with col2:
                roles = ["admin", "data_entry", "viewer"]
                new_role = st.selectbox("الدور", roles, index=roles.index(info.get("role", "viewer")), key=f"role_{username}")
                if new_role != info.get("role"):
                    users[username]["role"] = new_role
                    users[username]["permissions"] = {"all_sections": new_role == "admin"}
                    save_users(users)
                    st.success("تم تحديث الدور")
                    st.rerun()

            if username != "admin":
                if st.button(f"🗑️ حذف {username}", key=f"del_{username}"):
                    confirm = st.text_input("اكتب 'تم' لتأكيد الحذف", key=f"conf_{username}")
                    if confirm == "تم":
                        del users[username]
                        save_users(users)
                        st.success(f"تم حذف {username}")
                        st.rerun()
                    elif confirm:
                        st.warning("أكتب 'تم' فقط")

    st.markdown("---")
    st.subheader("➕ إضافة مستخدم")
    with st.form("add_user"):
        new_user = st.text_input("اسم المستخدم (إنجليزي أو أرقام)")
        new_pass = st.text_input("كلمة المرور", type="password")
        new_role = st.selectbox("الدور", ["viewer", "data_entry", "admin"])
        if st.form_submit_button("إضافة"):
            if not new_user or not new_pass:
                st.error("املأ جميع الحقول")
            elif new_user in users:
                st.error("المستخدم موجود")
            elif not new_user.replace("_", "").isalnum():
                st.error("اسم المستخدم غير صالح")
            else:
                users[new_user] = {
                    "password": new_pass,
                    "role": new_role,
                    "created_at": datetime.now().isoformat(),
                    "permissions": {"all_sections": new_role == "admin"},
                    "sections_permissions": {}
                }
                save_users(users)
                st.success("تمت الإضافة")
                st.balloons()
                st.rerun()

def config_management_tab():
    st.header("⚙️ إدارة المشرفين وأنواع البالات")
    config = load_config()

    st.subheader("👨‍🏭 المشرفون")
    c1, c2 = st.columns([3, 1])
    with c1:
        new_sup = st.text_input("إضافة مشرف", key="new_sup")
    with c2:
        if st.button("➕ إضافة", key="add_sup"):
            if new_sup and new_sup.strip() not in config["supervisors"]:
                config["supervisors"].append(new_sup.strip())
                save_config(config)
                st.success("تمت الإضافة")
                st.rerun()
            else:
                st.warning("اسم غير صحيح أو موجود")

    for sup in config["supervisors"]:
        col1, col2 = st.columns([4, 1])
        col1.write(f"• {sup}")
        if col2.button("🗑️", key=f"del_sup_{sup}"):
            if len(config["supervisors"]) > 1:
                config["supervisors"].remove(sup)
                save_config(config)
                st.rerun()
            else:
                st.warning("لا يمكن حذف آخر مشرف")

    st.markdown("---")
    st.subheader("📦 أنواع البالات")
    c1, c2 = st.columns([3, 1])
    with c1:
        new_bale = st.text_input("إضافة نوع", key="new_bale")
    with c2:
        if st.button("➕ إضافة", key="add_bale"):
            if new_bale and new_bale.strip() not in config["bale_types"]:
                config["bale_types"].append(new_bale.strip())
                save_config(config)
                st.success("تمت الإضافة")
                st.rerun()
            else:
                st.warning("اسم غير صحيح أو موجود")

    for btype in config["bale_types"]:
        col1, col2 = st.columns([4, 1])
        col1.write(f"• {btype}")
        if col2.button("🗑️", key=f"del_bale_{btype}"):
            if len(config["bale_types"]) > 1:
                config["bale_types"].remove(btype)
                save_config(config)
                st.rerun()
            else:
                st.warning("لا يمكن حذف آخر نوع")

# --------------------------------
# 11. تشغيل التطبيق الرئيسي
# --------------------------------
st.set_page_config(page_title=APP_CONFIG["TITLE"], layout="wide")

# الشريط الجانبي
with st.sidebar:
    st.header("الجلسة")
    logged = login_ui()
    if not logged:
        st.stop()

    st.markdown("---")
    if st.button("🔄 تحديث من GitHub"):
        if fetch_excel():
            st.rerun()
    if st.button("🗑 مسح الكاش"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    if st.button("🚪 تسجيل الخروج"):
        logout()

# تحميل البيانات
df = load_cotton_data()
st.title(f"{APP_CONFIG['ICON']} {APP_CONFIG['TITLE']}")

# صلاحيات
perms = get_permissions()
tabs_list = []
if perms["can_input"]:
    tabs_list.append("📥 إدخال البيانات")
    tabs_list.append("📝 إدارة البيانات")
if perms["can_view_stats"]:
    tabs_list.append("📊 الإحصائيات المتقدمة")
if is_admin():
    tabs_list.append("👥 إدارة المستخدمين")
    tabs_list.append("⚙️ إدارة التكوين")

tabs = st.tabs(tabs_list)

tab_idx = 0
if "📥 إدخال البيانات" in tabs_list:
    with tabs[tab_idx]:
        input_tab(df)
    tab_idx += 1
if "📝 إدارة البيانات" in tabs_list:
    with tabs[tab_idx]:
        management_tab(df)
    tab_idx += 1
if "📊 الإحصائيات المتقدمة" in tabs_list:
    with tabs[tab_idx]:
        stats_tab(df)
    tab_idx += 1
if is_admin() and "👥 إدارة المستخدمين" in tabs_list:
    with tabs[tab_idx]:
        users_management_tab()
    tab_idx += 1
if is_admin() and "⚙️ إدارة التكوين" in tabs_list:
    with tabs[tab_idx]:
        config_management_tab()
    tab_idx += 1
