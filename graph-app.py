import streamlit as st
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.types import Command
import uuid
# 从后端导入编译好的图
from agent_graph import app_graph

# 1. 基础配置
st.set_page_config(page_title="实验室智能管家", page_icon="🤖", layout="centered")
st.title("🤖 实验室设备智能预警管家")
st.caption("基于 LangGraph 状态机与 Human-in-the-loop 的自动化巡检系统")

load_dotenv()

# 2. 初始化记忆与图配置
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    # ✅ 每个新用户/新会话，动态生成一个唯一的 UUID
    st.session_state.thread_id = f"user_{uuid.uuid4().hex[:8]}"

config = {"configurable": {"thread_id": st.session_state.thread_id}}

# 3. 渲染历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 辅助函数：检查图是否处于等待审批状态
def check_and_handle_interrupt():
    state = app_graph.get_state(config)
    if state.next and "approval" in state.next:
        return state.values.get("alert_message", "")
    return None

# 核心引擎：执行图并同步前端状态
def execute_graph(initial_state=None, resume_action=None):
    try:
        if resume_action:
            app_graph.invoke(Command(resume=resume_action), config)
        else:
            app_graph.invoke(initial_state, config)
            
        # 检查是否触发中断
        state = app_graph.get_state(config)
        if state.next and "approval" in state.next:
            return True # 触发了中断
            
        # 如果没有中断，提取最后一条 AI 消息并写入前端历史
        if state.values.get("messages"):
            last_msg = state.values["messages"][-1]
            # 确保是标准 AIMessage 且有内容
            if hasattr(last_msg, "content") and last_msg.__class__.__name__ == "AIMessage":
                # 防重复添加
                if not st.session_state.messages or st.session_state.messages[-1]["content"] != last_msg.content:
                    st.session_state.messages.append({"role": "assistant", "content": last_msg.content})
        return False
    except Exception as e:
        st.error(f"执行失败：{e}")
        return False

# ================= 核心逻辑分发 =================

pending_message = check_and_handle_interrupt()

if pending_message:
    # 4. 审批 UI（如果图处于中断状态）
    st.warning("⚠️ 发现设备异常，大模型已生成预警文案，请管理员审批：")
    st.info(pending_message)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 同意并发送飞书", type="primary", use_container_width=True):
            with st.spinner("正在发送..."):
                execute_graph(resume_action="approved")
            st.rerun()
            
    with col2:
        if st.button("❌ 驳回预警", use_container_width=True):
            with st.spinner("正在撤销..."):
                execute_graph(resume_action="rejected")
            st.rerun()
            
    st.chat_input("请先处理上方的审批请求...", disabled=True)

else:
    # 5. 侧边栏控制面板（正常状态）
    with st.sidebar:
        st.header("⚙️ 控制面板")
        if st.button("🚀 立即执行全量巡检", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "🔔 [系统自动巡检指令]"})
            with st.spinner("Agent 正在全量扫描数据库..."):
                initial_state = {
                    "messages": [HumanMessage(content="请巡检实验室设备。")],
                    "retry_count": 0,
                    "error_msg": ""
                }
                execute_graph(initial_state=initial_state)
            st.rerun()

        st.divider()
        if st.button("🗑️ 清空聊天与状态", use_container_width=True):
            st.session_state.messages = []
            # 重置 thread_id 彻底清空 LangGraph 的后台记忆
            st.session_state.thread_id = f"session_{os.urandom(4).hex()}"
            st.rerun()

    # 6. 正常状态下的底部输入框
    if prompt := st.chat_input("请输入指令，例如：帮我查一下超期的设备？"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):#画汽包
            st.markdown(prompt)

        with st.spinner("管家正在查库..."):
            initial_state = {
                "messages": [HumanMessage(content=prompt)],
                "retry_count": 0,
                "error_msg": ""
            }
            execute_graph(initial_state=initial_state)
        st.rerun()