import streamlit as st
import uuid
import os
import pandas as pd

from database import init_db, query_df, query_students, get_distinct_values
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
/* 隐藏页脚 */
footer {visibility: hidden;}

/* 全局字体设置 */
body {
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}

/* 侧边栏样式优化 - 统一基础样式 */
[data-testid="stSidebar"] {
    background-color: #f7f7f8;
    color: #202123;
}

/* 侧边栏所有文字统一颜色（与设置区一致） */
[data-testid="stSidebar"] h1, 
[data-testid="stSidebar"] h2, 
[data-testid="stSidebar"] h3, 
[data-testid="stSidebar"] span, 
[data-testid="stSidebar"] p {
    color: #6b7280 !important;
}

/* 侧边栏所有按钮统一样式（与设置区按钮风格一致） */
[data-testid="stSidebar"] .stButton>button {
    background-color: transparent;
    color: #6b7280 !important;
    border: 1px solid #565869;
    text-align: left;
    padding: 10px;
    width: 100%;
    transition: all 0.2s ease;
}

/* 所有按钮hover效果统一 */
[data-testid="stSidebar"] .stButton>button:hover {
    background-color: #d1d5db !important;
    border-color: #9ca3af;
    color: #111827 !important;
}

/* 移除新建对话按钮的特殊样式，使其与其他按钮统一 */
[data-testid="stSidebar"] .stButton>button:first-child {
    border: 1px solid #565869;
    background-color: transparent !important;
    color: #6b7280 !important;    
}

/* 当前选中的会话按钮高亮样式（保留辨识度） */
[data-testid="stSidebar"] .stButton>button:has(> div:contains("👉")) {
    background-color: #e5e7eb !important;
    color: #111827 !important;
    border-color: #9ca3af;
}

/* 主界面样式 */
.stApp {
    background-color: #ffffff;
}

/* 聊天气泡样式 */
.stChatMessage {
    padding: 1rem;
}
.stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
    background-color: #f7f7f8; /* User Gray */
}
.stChatMessage[data-testid="stChatMessage"]:nth-child(even) {
    background-color: #ffffff; /* Assistant White */
}

/* 隐藏 Streamlit 默认的头像 */
[data-testid="stChatMessageAvatar"] {
    display: none;
}

 /* 分割线颜色 */
hr {
    border-color: #e5e7eb !important;
}     
  
</style>
""", unsafe_allow_html=True)

def _option_index(options, value):
    return options.index(value) if value in options else 0


def render_data_management():
    st.subheader("学生信息查询")

    default_filters = {
        "name": "",
        "student_id": "",
        "class_name": "",
        "college": "全部",
        "major": "全部",
        "grade": "全部",
        "gender": "全部",
    }

    if "data_filters" not in st.session_state:
        st.session_state.data_filters = default_filters

    filters = st.session_state.data_filters

    try:
        colleges = [c for c in get_distinct_values("college") if c]
    except Exception:
        colleges = []
    try:
        majors = [m for m in get_distinct_values("major") if m]
    except Exception:
        majors = []
    try:
        grades = sorted({int(g) for g in get_distinct_values("grade") if g is not None})
    except Exception:
        grades = []

    college_options = ["全部"] + colleges
    major_options = ["全部"] + majors
    grade_options = ["全部"] + [str(g) for g in grades]
    gender_options = ["全部", "男", "女"]

    with st.form("data_filters_form"):
        col1, col2, col3 = st.columns(3)
        name = col1.text_input("姓名", value=filters["name"])
        student_id = col2.text_input("学号", value=filters["student_id"])
        class_name = col3.text_input("班级", value=filters["class_name"])

        col4, col5, col6, col7 = st.columns(4)
        college = col4.selectbox(
            "学院",
            options=college_options,
            index=_option_index(college_options, filters["college"])
        )
        major = col5.selectbox(
            "专业",
            options=major_options,
            index=_option_index(major_options, filters["major"])
        )
        grade = col6.selectbox(
            "年级",
            options=grade_options,
            index=_option_index(grade_options, filters["grade"])
        )
        gender = col7.selectbox(
            "性别",
            options=gender_options,
            index=_option_index(gender_options, filters["gender"])
        )

        submitted = st.form_submit_button("应用过滤")

    if submitted:
        st.session_state.data_filters = {
            "name": name,
            "student_id": student_id,
            "class_name": class_name,
            "college": college,
            "major": major,
            "grade": grade,
            "gender": gender,
        }
        filters = st.session_state.data_filters

    grade_value = filters["grade"]
    grade_query = int(grade_value) if grade_value and grade_value != "全部" else None

    df = query_students(
        name=filters["name"] or None,
        student_id=filters["student_id"] or None,
        class_name=filters["class_name"] or None,
        college=None if filters["college"] == "全部" else filters["college"],
        major=None if filters["major"] == "全部" else filters["major"],
        grade=grade_query,
        gender=None if filters["gender"] == "全部" else filters["gender"],
    )

    st.caption(f"共 {len(df)} 条记录")
    if df.empty:
        st.info("暂无匹配数据")
        return

    st.dataframe(df, use_container_width=True, hide_index=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("下载当前结果 (CSV)", csv, "students_export.csv", "text/csv")


def render_dashboard():
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

    st.subheader("分布图表")
    left, right = st.columns(2)
    with left:
        df_college = safe_query(
            "SELECT college, COUNT(*) AS count FROM students GROUP BY college ORDER BY count DESC"
        )
        smart_plot(df_college, title="学院人数分布")
    with right:
        df_major = safe_query(
            "SELECT major, COUNT(*) AS count FROM students GROUP BY major ORDER BY count DESC LIMIT 10"
        )
        smart_plot(df_major, title="专业人数 Top 10")

    left2, right2 = st.columns(2)
    with left2:
        df_grade = safe_query(
            "SELECT grade, COUNT(*) AS count FROM students GROUP BY grade ORDER BY grade"
        )
        smart_plot(df_grade, title="年级人数分布")
    with right2:
        df_gender = safe_query(
            "SELECT gender, COUNT(*) AS count FROM students GROUP BY gender"
        )
        smart_plot(df_gender, title="性别人数分布")

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
with st.sidebar:
    if st.button("➕ 新建对话", use_container_width=True):
        sid = str(uuid.uuid4())
        st.session_state.sessions[sid] = {
            "title": "新对话", "messages": [], "pending": None
        }
        st.session_state.current_session_id = sid
        history_mgr.save_history(st.session_state.sessions)
        st.rerun()

    st.divider()
    st.markdown("### 🗂️ 历史对话")
    
    # 倒序显示，最新的在上面
    for sid in reversed(list(st.session_state.sessions.keys())):
        sess = st.session_state.sessions[sid]
        # 高亮当前会话
        label = sess["title"]
        if sid == current_sid:
            label = f"👉 {label}"
            
        if st.button(label, key=sid, use_container_width=True):
            st.session_state.current_session_id = sid
            st.rerun()

    st.divider()
    
    # 当前会话设置
    with st.expander("⚙️ 当前对话设置", expanded=False):
        new_title = st.text_input("重命名", value=current["title"])
        if st.button("保存名称"):
            current["title"] = new_title
            history_mgr.save_history(st.session_state.sessions)
            st.rerun()
            
        if st.button("🧹 清空消息"):
            current["messages"] = []
            current["pending"] = None
            history_mgr.save_history(st.session_state.sessions)
            st.rerun()
            
        if st.button("🗑️ 删除对话"):
            if len(st.session_state.sessions) > 1:
                del st.session_state.sessions[current_sid]
                # Switch to another
                st.session_state.current_session_id = list(st.session_state.sessions.keys())[0]
                history_mgr.save_history(st.session_state.sessions)
                st.rerun()
            else:
                st.warning("至少保留一个对话")

    st.divider()

    with st.expander("模型设置", expanded=False):
        api_key = st.text_input(
            "DASHSCOPE_API_KEY",
            type="password",
            value=st.session_state.dashscope_api_key
        )
        if api_key != st.session_state.dashscope_api_key:
            st.session_state.dashscope_api_key = api_key
            llm.set_api_key(api_key)

        if not llm.has_api_key():
            st.warning("未检测到 API Key，部分智能解析功能将不可用。")
        else:
            st.caption("已加载 API Key")

    with st.expander("示例问题", expanded=False):
        if st.button("查询张三信息", key="quick_query_1"):
            st.session_state.quick_prompt = "查询张三信息"
        if st.button("统计计算机学院人数", key="quick_query_2"):
            st.session_state.quick_prompt = "统计计算机学院人数"
        if st.button("统计各学院人数", key="quick_query_3"):
            st.session_state.quick_prompt = "统计各学院人数"
        if st.button("张三是男生吗", key="quick_query_4"):
            st.session_state.quick_prompt = "张三是男生吗"

# =====================
# 主界面
# =====================
st.title("🎓 基于大语言模型的学生信息管理助手")

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

            if msg.get("plot"):
                if not (len(df) == 1 and len(df.columns) == 1):
                     with st.expander("📊 点击查看可视化图表", expanded=True):
                        smart_plot(df, key=f"plot_{i}")

st.divider()
with st.expander("数据看板", expanded=False):
    render_dashboard()

with st.expander("数据管理", expanded=False):
    render_data_management()

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
