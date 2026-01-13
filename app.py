import streamlit as st
import uuid
import os
import pandas as pd

from database import (
    init_db,
    query_df,
    query_students,
    get_students_by_student_id,
    get_distinct_values,
    insert_student,
    update_student_by_id,
    delete_student_by_id,
)
from llm_interface import LLMInterface
from charts import smart_plot
from chat_history_manager import ChatHistoryManager

# =====================
# 页面配置（中文）
# =====================
st.set_page_config(
    page_title="学生信息管理助手",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 弱化官方 UI & ChatGPT 风格优化
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Source+Sans+3:wght@400;500;600&display=swap');

:root {
    --bg: #f5f2ea;
    --bg-2: #fdfbf7;
    --panel: #ffffff;
    --accent: #0f766e;
    --accent-2: #f59e0b;
    --text: #1f2937;
    --muted: #6b7280;
    --border: #e6e1d6;
    --bubble-user: #fff3df;
    --bubble-assistant: #eef5f4;
    --shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    --sidebar-width: 17rem;
    --header-offset: 3.25rem;
}

body:has([data-testid="stSidebar"][aria-expanded="false"]) {
    --sidebar-width: 3.5rem;
}

body:has([data-testid="collapsedControl"]) {
    --sidebar-width: 3.5rem;
}

/* Hide footer */
footer {visibility: hidden;}

/* Base typography */
body {
    font-family: "Source Sans 3", "Microsoft YaHei", sans-serif;
    color: var(--text);
}

/* App background */
.stApp {
    background: radial-gradient(circle at 15% 15%, #fdecc8 0%, rgba(253, 236, 200, 0) 45%),
                linear-gradient(180deg, var(--bg) 0%, var(--bg-2) 100%);
}

/* Headings */
.stApp h1, .stApp h2, .stApp h3 {
    font-family: "Playfair Display", "Source Sans 3", "Microsoft YaHei", sans-serif;
    letter-spacing: 0.2px;
}

/* Content width */
.block-container {
    padding-top: 5.5rem;
    padding-bottom: 7rem;
    max-width: 1200px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f0ebe1 0%, #f7f4ee 100%);
    border-right: 1px solid var(--border);
    color: var(--text);
    width: var(--sidebar-width);
    min-width: var(--sidebar-width);
    max-width: var(--sidebar-width);
}

[data-testid="stSidebar"] .block-container {
    padding-top: 0.6rem;
    padding-bottom: 0.6rem;
    padding-left: 0.6rem;
    padding-right: 0.6rem;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] p {
    color: var(--text) !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    margin-bottom: 0.4rem;
    font-size: 0.95rem;
}

/* Sidebar buttons (Flat Menu Style) */
section[data-testid="stSidebar"] .stButton button {
    border: none !important;
    box-shadow: none !important;
    text-align: left !important;
    padding: 0.35rem 0.5rem !important; /* Adjusted padding */
    transition: all 0.15s ease !important;
    font-size: 0.95rem !important;
    border-radius: 4px !important;
    display: flex !important;
    justify-content: flex-start !important; /* Force Left Align */
    align-items: center !important;
    width: 100% !important;
}

/* Force inner text alignment - Aggressive */
section[data-testid="stSidebar"] .stButton button div,
section[data-testid="stSidebar"] .stButton button p {
    text-align: left !important;
    display: block !important;
    width: 100% !important;
    margin: 0 !important;
}

/* Inactive Items */
section[data-testid="stSidebar"] .stButton button[kind="secondary"] {
    background-color: transparent !important;
    color: #4b5563 !important;
}
section[data-testid="stSidebar"] .stButton button[kind="secondary"]:hover {
    background-color: rgba(0,0,0,0.02) !important;
    color: #111827 !important;
}

/* Active Items - Minimalist */
section[data-testid="stSidebar"] .stButton button[kind="primary"] {
    background-color: transparent !important;
    color: #0f766e !important; /* Accent color */
    font-weight: 700 !important;
    border: none !important;
    border-radius: 4px !important;
}
section[data-testid="stSidebar"] .stButton button[kind="primary"]:hover {
    background-color: rgba(15, 118, 110, 0.05) !important;
}

/* Popover Button (Three dots) */
section[data-testid="stSidebar"] [data-testid="stPopover"] > button {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #9ca3af !important;
    padding: 0.5rem 0 !important;
    text-align: center !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
}
section[data-testid="stSidebar"] [data-testid="stPopover"] > button:hover {
    background-color: rgba(0,0,0,0.04) !important;
    color: #374151 !important;
}

/* Popover Menu Items (Inside) */
div[data-testid="stPopoverBody"] button {
    font-size: 0.85rem !important;
    padding: 0.2rem 0.5rem !important;
    min-height: 0 !important;
    height: auto !important;
    line-height: 1.5 !important;
}

[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    padding: 0.25rem 0.4rem;
}

[data-testid="stSidebar"] .stMarkdown {
    margin-bottom: 0.35rem;
}

[data-testid="stSidebar"] hr {
    margin: 0.4rem 0;
}

/* Chat bubbles */
.stChatMessage {
    padding: 1rem 1.2rem;
    border-radius: 18px;
    border: 1px solid rgba(17, 24, 39, 0.06);
    box-shadow: var(--shadow);
    animation: floatIn 0.35s ease;
}

.stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
    background-color: var(--bubble-user);
}

.stChatMessage[data-testid="stChatMessage"]:nth-child(even) {
    background-color: var(--bubble-assistant);
}

/* Hide default avatar */
[data-testid="stChatMessageAvatar"] {
    display: none;
}

/* Chat input */
[data-testid="stChatInput"] textarea {
    border-radius: 14px;
    border: 1px solid var(--border);
    background-color: #fffdf8;
}

[data-testid="stChatInput"] {
    position: fixed;
    bottom: 1rem;
    left: calc(var(--sidebar-width) + 1.5rem);
    right: 1.5rem;
    z-index: 1000;
    background: transparent;
}

[data-testid="stChatInput"] > div {
    background: transparent;
    max-width: 1200px;
    margin-left: auto;
    margin-right: auto;
}

@media (max-width: 900px) {
    [data-testid="stChatInput"] {
        left: 1rem;
        right: 1rem;
    }
}

body:has([data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stChatInput"] {
    left: calc(var(--sidebar-width) + 1rem);
    right: 1rem;
}

/* Tabs (Inner) */
button[role="tab"] {
    color: var(--muted) !important;
    font-weight: 600;
}

button[role="tab"][aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
}

/* Divider color */
hr {
    border-color: var(--border) !important;
}

@keyframes floatIn {
    from {
        opacity: 0;
        transform: translateY(6px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
</style>
""", unsafe_allow_html=True)

def _option_index(options, value):
    return options.index(value) if value in options else 0


def render_data_management():
    st.header("数据管理")
    st.caption("增删改查一体化管理学生信息。")

    tab_query, tab_create, tab_update, tab_delete = st.tabs(["查询", "新增", "修改", "删除"])

    with tab_query:
        st.subheader("查询")

        # 初始化 active_filters 用于存储实际查询条件
        # 注意：从单选改为多选后，需要确保默认值是空列表 [] 而不是 "全部"
        if "active_filters" not in st.session_state:
            st.session_state.active_filters = {
                "name": "", "student_id": "", "class_name": "",
                "college": [], "major": [], "grade": [], "gender": []
            }
        else:
            # 兼容性处理：如果旧状态中存在 "全部"，重置为 []
            af = st.session_state.active_filters
            if af.get("college") == "全部": af["college"] = []
            if af.get("major") == "全部": af["major"] = []
            if af.get("grade") == "全部": af["grade"] = []
            if af.get("gender") == "全部": af["gender"] = []

        # 1. 获取基础选项数据
        try:
            colleges = [c for c in get_distinct_values("college") if c]
        except Exception:
            colleges = []
        
        try:
            grades = sorted({int(g) for g in get_distinct_values("grade") if g is not None})
        except Exception:
            grades = []

        # 2. 处理级联选择逻辑 (学院 -> 专业)
        # 获取当前选中的学院（从 session_state 获取）
        current_college = st.session_state.get("filter_college", st.session_state.active_filters["college"])
        
        # 确保 current_college 是列表 (兼容旧状态)
        if current_college == "全部": current_college = []
        
        if current_college:
            try:
                # 查询所选学院下的专业 (多选)
                in_clause = "', '".join(current_college)
                major_df = query_df(f"SELECT DISTINCT major FROM students WHERE college IN ('{in_clause}')")
                majors = major_df["major"].tolist() if not major_df.empty else []
            except Exception:
                majors = []
        else:
            try:
                majors = [m for m in get_distinct_values("major") if m]
            except Exception:
                majors = []

        college_options = colleges
        major_options = majors
        grade_options = [str(g) for g in grades]
        gender_options = ["男", "女"]

        # 检查当前选中的专业是否在新的选项列表中
        # 对于多选，我们需要过滤掉不再有效的选项
        current_major = st.session_state.get("filter_major", [])
        if current_major == "全部": current_major = [] # 兼容
        
        if current_major:
            valid_majors = [m for m in current_major if m in major_options]
            if len(valid_majors) != len(current_major):
                st.session_state["filter_major"] = valid_majors

        # 3. 渲染过滤组件
        col1, col2, col3 = st.columns(3)
        
        def init_filter_key(key, field):
            if key not in st.session_state:
                st.session_state[key] = st.session_state.active_filters[field]
            # 再次确保类型正确 (防止从旧 session 恢复出 string)
            if key in ["filter_college", "filter_major", "filter_grade", "filter_gender"]:
                if st.session_state[key] == "全部":
                    st.session_state[key] = []

        init_filter_key("filter_name", "name")
        init_filter_key("filter_student_id", "student_id")
        init_filter_key("filter_class_name", "class_name")
        init_filter_key("filter_college", "college")
        init_filter_key("filter_major", "major")
        init_filter_key("filter_grade", "grade")
        init_filter_key("filter_gender", "gender")

        col1.text_input("姓名", key="filter_name")
        col2.text_input("学号", key="filter_student_id")
        col3.text_input("班级", key="filter_class_name")

        col4, col5, col6, col7 = st.columns(4)
        # 改为 multiselect
        col4.multiselect("学院", options=college_options, key="filter_college", placeholder="全部")
        col5.multiselect("专业", options=major_options, key="filter_major", placeholder="全部")
        col6.multiselect("年级", options=grade_options, key="filter_grade", placeholder="全部")
        col7.multiselect("性别", options=gender_options, key="filter_gender", placeholder="全部")

        # 4. 按钮区域
        c_apply, c_reset = st.columns(2)
        
        # 查询按钮
        if c_apply.button("查询", use_container_width=True):
            st.session_state.active_filters = {
                "name": st.session_state.filter_name,
                "student_id": st.session_state.filter_student_id,
                "class_name": st.session_state.filter_class_name,
                "college": st.session_state.filter_college,
                "major": st.session_state.filter_major,
                "grade": st.session_state.filter_grade,
                "gender": st.session_state.filter_gender,
            }
            st.rerun()

        # 重置按钮
        if c_reset.button("重置", use_container_width=True):
            st.session_state.active_filters = {
                "name": "", "student_id": "", "class_name": "",
                "college": [], "major": [], "grade": [], "gender": []
            }
            keys_to_reset = [
                "filter_name", "filter_student_id", "filter_class_name",
                "filter_college", "filter_major", "filter_grade", "filter_gender"
            ]
            for key in keys_to_reset:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        # 5. 执行查询
        filters = st.session_state.active_filters
        
        # 处理 Grade (str -> int)
        grade_val = filters["grade"]
        if grade_val and isinstance(grade_val, list):
            grade_query = [int(g) for g in grade_val]
        elif grade_val and grade_val != "全部":
            grade_query = int(grade_val)
        else:
            grade_query = None

        # 处理其他 "全部" 情况 (兼容)
        f_college = filters["college"] if filters["college"] != "全部" else None
        f_major = filters["major"] if filters["major"] != "全部" else None
        f_gender = filters["gender"] if filters["gender"] != "全部" else None

        df = query_students(
            name=filters["name"] or None,
            student_id=filters["student_id"] or None,
            class_name=filters["class_name"] or None,
            college=f_college,
            major=f_major,
            grade=grade_query,
            gender=f_gender,
        )

        st.divider()
        st.caption(f"共 {len(df)} 条记录")
        if df.empty:
            st.info("暂无匹配数据")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True, height=420)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("下载当前结果 (CSV)", csv, "students_export.csv", "text/csv")

    with tab_create:
        st.subheader("新增学生")
        st.caption("学号与姓名为必填项。")

        with st.form("create_student_form"):
            col1, col2, col3 = st.columns(3)
            student_id = col1.text_input("学号*")
            name = col2.text_input("姓名*")
            gender = col3.selectbox("性别", ["未填", "男", "女"], index=0)

            col4, col5, col6 = st.columns(3)
            grade = col4.text_input("年级")
            college = col5.text_input("学院")
            major = col6.text_input("专业")

            col7, col8 = st.columns(2)
            class_name = col7.text_input("班级")
            phone = col8.text_input("手机号")

            submitted = st.form_submit_button("新增")

        if submitted:
            if not student_id.strip() or not name.strip():
                st.error("学号和姓名为必填项。")
            else:
                existing = get_students_by_student_id(student_id.strip())
                if not existing.empty:
                    st.warning("该学号已存在，请确认后再新增。")
                else:
                    grade_value = None
                    if grade.strip():
                        try:
                            grade_value = int(grade.strip())
                        except ValueError:
                            st.error("年级需为数字。")
                            grade_value = "__invalid__"

                    if grade_value != "__invalid__":
                        row_id = insert_student({
                            "student_id": student_id.strip(),
                            "name": name.strip(),
                            "class_name": class_name.strip() or None,
                            "college": college.strip() or None,
                            "major": major.strip() or None,
                            "grade": grade_value,
                            "gender": None if gender == "未填" else gender,
                            "phone": phone.strip() or None,
                        })
                        st.success(f"新增成功，记录 ID: {row_id}")

    with tab_update:
        st.subheader("修改学生")
        st.caption("先按学号或姓名查询，再选择记录进行修改。")

        col_a, col_b, col_c = st.columns([2, 2, 1])
        search_student_id = col_a.text_input("学号", key="update_search_student_id")
        search_name = col_b.text_input("姓名", key="update_search_name")
        do_search = col_c.button("查询", key="update_search_btn")

        if do_search:
            if not search_student_id.strip() and not search_name.strip():
                st.warning("请输入学号或姓名进行查询。")
                st.session_state.update_search_df = pd.DataFrame()
            else:
                st.session_state.update_search_df = query_students(
                    student_id=search_student_id.strip() or None,
                    name=search_name.strip() or None,
                )

        update_df = st.session_state.get("update_search_df")
        if update_df is None:
            st.info("请输入学号或姓名进行查询。")
        elif update_df.empty:
            st.warning("未找到匹配记录。")
        else:
            st.dataframe(update_df, use_container_width=True, hide_index=True, height=240)
            options = update_df["id"].tolist()
            selected_id = st.selectbox(
                "选择记录",
                options,
                key="update_select_id",
                format_func=lambda x: f"ID {x} - {update_df[update_df['id'] == x].iloc[0]['name']}"
            )
            row = update_df[update_df["id"] == selected_id].iloc[0]

            gender_options = ["未填", "男", "女"]
            gender_index = gender_options.index(row["gender"]) if row["gender"] in gender_options else 0

            with st.form("update_student_form"):
                col1, col2, col3 = st.columns(3)
                new_student_id = col1.text_input("学号", value=str(row["student_id"] or ""))
                new_name = col2.text_input("姓名", value=str(row["name"] or ""))
                new_gender = col3.selectbox("性别", gender_options, index=gender_index)

                col4, col5, col6 = st.columns(3)
                new_grade = col4.text_input("年级", value=str(row["grade"] or ""))
                new_college = col5.text_input("学院", value=str(row["college"] or ""))
                new_major = col6.text_input("专业", value=str(row["major"] or ""))

                col7, col8 = st.columns(2)
                new_class_name = col7.text_input("班级", value=str(row["class_name"] or ""))
                new_phone = col8.text_input("手机号", value=str(row["phone"] or ""))

                submitted = st.form_submit_button("保存修改")

            if submitted:
                updates = {}

                def _set(field, value):
                    if value is None:
                        return
                    original = str(row[field] or "")
                    if value != "" and value != original:
                        updates[field] = value

                _set("student_id", new_student_id.strip())
                _set("name", new_name.strip())
                _set("class_name", new_class_name.strip())
                _set("college", new_college.strip())
                _set("major", new_major.strip())
                _set("phone", new_phone.strip())

                if new_gender != "未填" and new_gender != (row["gender"] or ""):
                    updates["gender"] = new_gender

                if new_grade.strip():
                    try:
                        grade_val = int(new_grade.strip())
                        if str(grade_val) != str(row["grade"] or ""):
                            updates["grade"] = grade_val
                    except ValueError:
                        st.error("年级需为数字。")
                        updates = None

                if updates is None:
                    pass
                elif not updates:
                    st.info("未检测到更改内容。")
                else:
                    rowcount = update_student_by_id(int(selected_id), updates)
                    st.success(f"修改成功，影响 {rowcount} 行。")
                    st.session_state.update_search_df = query_students(
                        student_id=search_student_id.strip() or None,
                        name=search_name.strip() or None,
                    )

    with tab_delete:
        st.subheader("删除学生")
        st.caption("删除操作不可恢复，请谨慎确认。")

        col_a, col_b, col_c = st.columns([2, 2, 1])
        del_student_id = col_a.text_input("学号", key="delete_search_student_id")
        del_name = col_b.text_input("姓名", key="delete_search_name")
        do_delete_search = col_c.button("查询", key="delete_search_btn")

        if do_delete_search:
            if not del_student_id.strip() and not del_name.strip():
                st.warning("请输入学号或姓名进行查询。")
                st.session_state.delete_search_df = pd.DataFrame()
            else:
                st.session_state.delete_search_df = query_students(
                    student_id=del_student_id.strip() or None,
                    name=del_name.strip() or None,
                )

        delete_df = st.session_state.get("delete_search_df")
        if delete_df is None:
            st.info("请输入学号或姓名进行查询。")
        elif delete_df.empty:
            st.warning("未找到匹配记录。")
        else:
            st.dataframe(delete_df, use_container_width=True, hide_index=True, height=220)
            options = delete_df["id"].tolist()
            selected_id = st.selectbox(
                "选择记录",
                options,
                key="delete_select_id",
                format_func=lambda x: f"ID {x} - {delete_df[delete_df['id'] == x].iloc[0]['name']}"
            )
            confirm = st.checkbox("我已确认删除该记录", key="delete_confirm")
            if st.button("删除", key="delete_btn"):
                if not confirm:
                    st.warning("请先勾选确认删除。")
                else:
                    rowcount = delete_student_by_id(int(selected_id))
                    st.success(f"删除成功，影响 {rowcount} 行。")
                    st.session_state.delete_search_df = query_students(
                        student_id=del_student_id.strip() or None,
                        name=del_name.strip() or None,
                    )


def render_dashboard():
    st.header("数据看板")
    st.caption("全局统计与分布概览。")
    st.subheader("关键指标")

    def safe_query(sql):
        try:
            return query_df(sql)
        except Exception:
            return pd.DataFrame()

    total_df = safe_query("SELECT COUNT(*) AS count FROM students")
    college_df = safe_query("SELECT COUNT(DISTINCT college) AS count FROM students")
    major_df = safe_query("SELECT COUNT(DISTINCT major) AS count FROM students")
    class_df = safe_query("SELECT COUNT(DISTINCT class_name) AS count FROM students")

    total = int(total_df.iloc[0, 0]) if not total_df.empty else 0
    college_count = int(college_df.iloc[0, 0]) if not college_df.empty else 0
    major_count = int(major_df.iloc[0, 0]) if not major_df.empty else 0
    class_count = int(class_df.iloc[0, 0]) if not class_df.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("学生总数", total)
    c2.metric("学院数量", college_count)
    c3.metric("专业数量", major_count)
    c4.metric("班级数量", class_count)

    st.divider()
    st.subheader("分布图表")
    left, right = st.columns(2)
    with left:
        df_college = safe_query(
            "SELECT college, COUNT(*) AS count FROM students GROUP BY college ORDER BY count DESC"
        )
        smart_plot(df_college, title="学院人数分布", use_container_width=True, height=320)
    with right:
        df_major = safe_query(
            "SELECT major, COUNT(*) AS count FROM students GROUP BY major ORDER BY count DESC LIMIT 10"
        )
        smart_plot(df_major, title="专业人数 Top 10", use_container_width=True, height=320)

    left2, right2 = st.columns(2)
    with left2:
        df_grade = safe_query(
            "SELECT grade, COUNT(*) AS count FROM students GROUP BY grade ORDER BY grade"
        )
        smart_plot(df_grade, title="年级人数分布", use_container_width=True, height=300)
    with right2:
        df_gender = safe_query(
            "SELECT gender, COUNT(*) AS count FROM students GROUP BY gender"
        )
        smart_plot(df_gender, title="性别人数分布", use_container_width=True, height=300)

# =====================
# 初始化
# =====================
init_db()
llm = LLMInterface()
history_mgr = ChatHistoryManager()

if "dashscope_api_key" not in st.session_state:
    st.session_state.dashscope_api_key = os.getenv("DASHSCOPE_API_KEY", "")
llm.set_api_key(st.session_state.dashscope_api_key)

if "quick_prompt" not in st.session_state:
    st.session_state.quick_prompt = None

# =====================
# 多会话管理
# =====================
if "sessions" not in st.session_state:
    # Load from file
    loaded_sessions = history_mgr.load_history()
    if not loaded_sessions:
        sid = str(uuid.uuid4())
        loaded_sessions = {
            sid: {"title": "新对话", "messages": [], "pending": None}
        }
        st.session_state.current_session_id = sid
    else:
        # Default to the first one
        st.session_state.current_session_id = list(loaded_sessions.keys())[0]
    
    st.session_state.sessions = loaded_sessions

# 确保 current_session_id 有效
if st.session_state.current_session_id not in st.session_state.sessions:
    st.session_state.current_session_id = list(st.session_state.sessions.keys())[0]

current_sid = st.session_state.current_session_id
current = st.session_state.sessions[current_sid]

# =====================
# 侧边栏
# =====================
# =====================
# 侧边栏 & 导航逻辑
# =====================
if "current_page" not in st.session_state:
    st.session_state.current_page = "对话"

with st.sidebar:
    # 1. 功能导航 (卡片折叠式，常态展开)
    with st.expander("🧭 功能导航", expanded=True):
        # 扁平化菜单按钮
        nav_items = {
            "对话": "💬",
            "数据看板": "📊",
            "数据管理": "🗃️"
        }
        
        for page_name, icon in nav_items.items():
            is_active = (st.session_state.current_page == page_name)
            # 选中项使用 primary 样式，未选中项使用 secondary (透明)
            if st.button(
                f"{icon} {page_name}",
                key=f"nav_btn_{page_name}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.current_page = page_name
                st.rerun()

    # 2. 历史对话
    with st.expander("🗂️ 历史对话", expanded=True):
        
        # 新建对话按钮 (保持 Secondary 样式，或可视情况改为 Primary)
        def on_new_chat():
            sid = str(uuid.uuid4())
            st.session_state.sessions[sid] = {
                "title": "新对话", "messages": [], "pending": None
            }
            st.session_state.current_session_id = sid
            st.session_state.current_page = "对话"
            history_mgr.save_history(st.session_state.sessions)

        st.button("➕ 新建对话", use_container_width=True, on_click=on_new_chat)
        st.divider()

        # 初始化重命名状态
        if "renaming_session_id" not in st.session_state:
            st.session_state.renaming_session_id = None

        # 定义重命名回调
        def on_rename_submit(sid):
            key = f"rename_input_{sid}"
            if key in st.session_state:
                new_name = st.session_state[key]
                if new_name.strip():
                    st.session_state.sessions[sid]["title"] = new_name.strip()
                    history_mgr.save_history(st.session_state.sessions)
            st.session_state.renaming_session_id = None

        # 遍历显示历史会话
        for sid in reversed(list(st.session_state.sessions.keys())):
            sess = st.session_state.sessions[sid]
            is_active = (sid == current_sid)
            
            # 调整比例，让菜单按钮更紧凑
            col_title, col_menu = st.columns([5, 1], gap="small")
            
            with col_title:
                if st.session_state.renaming_session_id == sid:
                    st.text_input(
                        "重命名",
                        value=sess["title"],
                        key=f"rename_input_{sid}",
                        label_visibility="collapsed",
                        on_change=on_rename_submit,
                        args=(sid,)
                    )
                else:
                    label = sess["title"]
                    # 选中项使用 primary 样式
                    if st.button(
                        label,
                        key=f"sess_btn_{sid}",
                        use_container_width=True,
                        type="primary" if is_active else "secondary"
                    ):
                        st.session_state.current_session_id = sid
                        st.session_state.current_page = "对话"
                        st.rerun()

            with col_menu:
                try:
                    pop = st.popover("⋮", use_container_width=True)
                    with pop:
                        if st.button("✏️ 重命名", key=f"menu_ren_{sid}", use_container_width=True):
                            st.session_state.renaming_session_id = sid
                            st.rerun()
                        
                        if st.button("🧹 清空消息", key=f"menu_clr_{sid}", use_container_width=True):
                            st.session_state.sessions[sid]["messages"] = []
                            st.session_state.sessions[sid]["pending"] = None
                            history_mgr.save_history(st.session_state.sessions)
                            st.rerun()
                            
                        if st.button("🗑️ 删除", key=f"menu_del_{sid}", use_container_width=True):
                            if len(st.session_state.sessions) > 1:
                                del st.session_state.sessions[sid]
                                if sid == current_sid:
                                    st.session_state.current_session_id = list(st.session_state.sessions.keys())[0]
                                history_mgr.save_history(st.session_state.sessions)
                                st.rerun()
                            else:
                                st.warning("至少保留一个")
                except AttributeError:
                    st.caption("⚠️")

    st.divider()

    with st.expander("示例问题", expanded=False):
        if st.button("查询李飞信息", key="quick_query_1"):
            st.session_state.quick_prompt = "查询李飞信息"
        if st.button("统计计算机学院人数", key="quick_query_2"):
            st.session_state.quick_prompt = "统计计算机学院人数"
        if st.button("统计各学院人数", key="quick_query_3"):
            st.session_state.quick_prompt = "统计各学院人数"
        if st.button("李飞是男生吗", key="quick_query_4"):
            st.session_state.quick_prompt = "李飞是男生吗"

    st.divider()

# =====================
# 主界面
# =====================
# =====================
# 主界面内容渲染
# =====================

if st.session_state.current_page == "对话":
    st.title("基于大语言模型的学生信息管理助手")
    
    # 悬浮标题 
    st.markdown(f"""
    <div class="floating-title">
        {current['title']}
    </div>
    <style>
    .floating-title {{
        position: fixed;
        top: 3.8rem;
        left: calc(50% + var(--sidebar-width) / 2);
        transform: translateX(-50%);
        z-index: 999;
        background-color: rgba(255, 255, 255, 0.95);
        padding: 6px 16px;
        border-radius: 20px;
        border: 1px solid rgba(0,0,0,0.1);
        font-size: 0.85rem;
        color: #444;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        backdrop-filter: blur(4px);
        transition: left 0.3s ease;
    }}
    </style>
    """, unsafe_allow_html=True)

    for i, msg in enumerate(current["messages"]):
        with st.chat_message(msg["role"]):
            # 尝试恢复数据
            df = None
            if "data" in msg:
                df = msg["data"]
            elif "sql" in msg:
                # 从历史记录加载时，重新查询数据
                try:
                    df = query_df(msg["sql"])
                    msg["data"] = df # 缓存回内存
                except:
                    pass

            st.markdown(msg["content"])

            if df is not None and not df.empty:
                # Case 1: 单个统计值 (e.g. 总人数) -> 使用 Metric 卡片
                if len(df) == 1 and len(df.columns) == 1:
                    val = df.iloc[0, 0]
                    col_name = df.columns[0]
                
                    # 如果是数字类型（统计结果），使用 Metric
                    if pd.api.types.is_numeric_dtype(type(val)) or "count" in col_name.lower() or "人数" in col_name:
                        c1, c2, c3 = st.columns([1, 1, 1])
                        with c2:
                            st.metric(label=col_name, value=str(val))
                    else:
                        # 如果是文本类型（如查询专业），直接显示文字
                        st.info(f"📋 **{col_name}**: {val}")

                # Case 2: 少量数据表格 -> 使用 Markdown 表格 (模仿 ChatGPT 样式)
                elif len(df) < 10 and len(df.columns) < 5:
                    # 转换为 Markdown 表格
                    try:
                        md_table = df.to_markdown(index=False)
                        st.markdown(md_table)
                    except:
                        st.dataframe(df, use_container_width=True, hide_index=True)
            
                # Case 3: 大数据表格 -> 使用交互式 DataFrame
                else:
                    st.dataframe(df, use_container_width=True, hide_index=True)
                
                should_plot = bool(msg.get("plot"))
                if not should_plot and df is not None and len(df.columns) >= 2:
                    num_cols = df.select_dtypes(include="number").columns
                    if len(num_cols) == 1:
                        should_plot = True
                
                if should_plot and not (len(df) == 1 and len(df.columns) == 1):
                    with st.expander("📊 点击查看可视化图表", expanded=True):
                        smart_plot(df, key=f"plot_{i}")

    # =====================
    # 输入
    # =====================
    user_input = st.chat_input("请输入你的问题")

    if not user_input and st.session_state.quick_prompt:
        user_input = st.session_state.quick_prompt
        st.session_state.quick_prompt = None

    if user_input:
        current["messages"].append({"role": "user", "content": user_input})

        if current["title"] == "新对话":
            current["title"] = user_input[:12]

        # 构建上下文 (最近 5 条消息)
        context_str = ""
        for msg in current["messages"][-5:]:
            context_str += f"{msg['role']}: {msg['content']}\n"

        result = llm.handle(user_input, context=context_str, pending=current.get("pending"))

        # ✅ 新增：普通聊天（不查数据库）
        if result["type"] == "chat":
            current["messages"].append({
                "role": "assistant",
                "content": result["message"]
            })

        elif result["type"] == "ask":
            current["pending"] = result.get("pending")
            current["messages"].append({
                "role": "assistant",
                "content": result["message"]
            })

        elif result["type"] == "sql":
            current["pending"] = None
            df = query_df(result["sql"])
            if df.empty:
                # 尝试从 SQL 中提取查询对象，生成更友好的提示
                import re
                target_name = "该学生"
                m = re.search(r"name\s*=\s*'(.+?)'", result["sql"])
                if m:
                    target_name = m.group(1)
            
                msg_content = f"⚠️ 抱歉，未查到 **{target_name}** 的信息，本数据库当中未有名为 **{target_name}** 的同学。"
            
                current["messages"].append({
                    "role": "assistant",
                    "content": msg_content
                })
            else:
                content = result["explain"]
            
                # 如果是查询单个学生详情，增加文字总结
                if len(df) == 1 and "name" in df.columns and "student_id" in df.columns:
                    try:
                        row = df.iloc[0]
                        # 简单的自然语言描述
                        desc = f"\n\n📄 **详细信息**：\n**{row['name']}** (学号: {row['student_id']}) 是 **{row['college']}** **{row['major']}** 专业 **{row['grade']}** 级的学生，性别 **{row['gender']}**，所在班级为 **{row['class_name']}**，手机号为 **{row['phone']}**。"
                        content += desc
                    except:
                        pass
                
                # 增加引导追问
                content += "\n\n🤔 您还想了解什么？(例如：修改手机号、统计班级人数等)"

                current["messages"].append({
                    "role": "assistant",
                    "content": content,
                    "data": df,
                    "sql": result["sql"], # 保存 SQL 以便恢复
                    "plot": result.get("response_type") == "count" or "group by" in result["sql"].lower()
                })

        # 保存历史
        history_mgr.save_history(st.session_state.sessions)
        st.rerun()

elif st.session_state.current_page == "数据看板":
    render_dashboard()

elif st.session_state.current_page == "数据管理":
    render_data_management()
