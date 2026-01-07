import streamlit as st
import uuid
import pandas as pd

from database import init_db, query_df
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

# =====================
# 初始化
# =====================
init_db()
llm = LLMInterface()
history_mgr = ChatHistoryManager()

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
                # 居中显示 Metric
                c1, c2, c3 = st.columns([1, 1, 1])
                with c2:
                    st.metric(label=col_name, value=str(val))
            
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

# =====================
# 输入
# =====================
user_input = st.chat_input("请输入你的问题")

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
                "plot": result.get("response_type") == "count"
            })

    # 保存历史
    history_mgr.save_history(st.session_state.sessions)
    st.rerun()