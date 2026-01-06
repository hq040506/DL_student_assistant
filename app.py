import streamlit as st
from database import query_df
from llm_interface import LLMInterface
from database import init_db
init_db()


st.set_page_config(page_title="学生信息管理助手", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending" not in st.session_state:
    st.session_state.pending = None

llm = LLMInterface()

st.sidebar.title("📌 系统信息")
st.sidebar.markdown("""
- 数据库：SQLite  
- 支持自然语言查询  
- 支持多轮对话  
- 支持统计分析  
""")

st.title("🎓 学生信息管理助手")

# 历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if "data" in msg:
            st.dataframe(msg["data"], use_container_width=True)
        else:
            st.markdown(msg["content"])

user_input = st.chat_input("请输入你的问题，例如：查询张三信息、统计计算机学院人数")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    result = llm.handle(user_input, st.session_state.pending)

    if result["type"] == "ask":
        st.session_state.pending = result.get("pending")
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["message"]
        })

    elif result["type"] == "sql":
        st.session_state.pending = None
        df = query_df(result["sql"])

        if result["response_type"] == "query":
            content = "🔍 为你查询到以下学生信息："
        else:
            content = "📊 统计结果如下："

        st.session_state.messages.append({
            "role": "assistant",
            "content": content,
            "data": df
        })

    st.rerun()
