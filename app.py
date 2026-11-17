import streamlit as st
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from agent_tools import check_lab_status, send_feishu_alert

# 1. 基础配置
st.set_page_config(page_title="实验室智能管家", page_icon="🤖", layout="centered")
st.title("🤖 实验室设备智能预警管家")
st.caption("基于大模型 Agent 与 MySQL 的自动化巡检系统")

load_dotenv()

# 2. 缓存 Agent
@st.cache_resource
def get_agent():
    llm = ChatOpenAI(
        model="deepseek-chat",
        base_url="https://api.deepseek.com",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        temperature=0,
    )
    tools = [check_lab_status, send_feishu_alert]
    system_prompt = """你是一个专业的实验室设备管家。
你的职责是：
1. 巡检实验室设备，检查是否有“维护超期”或“耗材告急”的情况。
2. 一旦发现异常，必须调用 send_feishu_alert 工具，把详细情况整理成一段话发给管理员。
3. 如果没有异常，直接回复“当前一切正常”，不要调用发送工具。
注意：
- 查询超期用 check_lab_status，参数 query_type 传 'overdue'。
- 查询耗材用 check_lab_status，参数 query_type 传 'low_stock'。"""
    return create_agent(model=llm, tools=tools, system_prompt=system_prompt)

agent_executor = get_agent()

# 3. 初始化记忆
if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. 渲染历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 5. 侧边栏控制面板
with st.sidebar:
    st.header("⚙️ 控制面板")
    if st.button("🚀 立即执行全量巡检", use_container_width=True):
        # 优化1：改名，避免和上面的 system_prompt 冲突
        auto_prompt = "请检查实验室是否有超期未维护的设备，以及是否有耗材告急的设备。如果有，整理成一段话发给飞书群。"
        st.session_state.messages.append({"role": "user", "content": "🔔 [系统自动巡检指令]"})
        
        with st.spinner("Agent 正在全量扫描数据库..."):
            # 优化2：加上异常捕获，防止系统崩溃
            try:
                result = agent_executor.invoke({"messages": [("user", auto_prompt)]})
                final_message = result["messages"][-1].content
                st.session_state.messages.append({"role": "assistant", "content": final_message})
                st.rerun() # 刷新页面，显示新消息
            except Exception as e:
                st.error(f"巡检失败，请检查网络或 API：{e}")

    st.divider()
    if st.button("🗑️ 清空聊天记录", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# 6. 处理底部输入框
if prompt := st.chat_input("请输入指令，例如：帮我查一下今天有没有超期的设备？"):
    # 保存并显示用户输入
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("管家正在查库并思考..."):
            try:
                # 优化3：传入完整的历史记录，实现多轮对话记忆
                # 注意：如果你的历史记录太长，可能会超出 Token 限制，实际生产中需要截断
                history = [("user", m["content"]) if m["role"] == "user" else ("assistant", m["content"]) for m in st.session_state.messages]
                history = history[-10:]
                result = agent_executor.invoke({"messages": history})
                final_message = result["messages"][-1].content
                
                st.markdown(final_message)
                st.session_state.messages.append({"role": "assistant", "content": final_message})
            except Exception as e:
                st.error(f"管家生病了：{e}")