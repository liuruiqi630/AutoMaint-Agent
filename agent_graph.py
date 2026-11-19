import os
import operator
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

# 导入你写好的工具
from agent_tools import check_lab_status, send_feishu_alert

load_dotenv()

# ==========================================
# 初始化大模型
# ==========================================
llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"), 
    temperature=0.3,
)

# ==========================================
# 第一步：定义状态 (State)
# ==========================================
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    abnormal_data: str
    error_msg: str
    retry_count: int
    alert_message: str
    approval_status: str

# ==========================================
# 第二步 & 第三步：编写节点函数 (Nodes)
# ==========================================

# 节点 1：查库
def query_db_node(state: AgentState):
    print("--- [节点1] 正在查库 ---")
    try:
        # 调用工具查库，假设查超期设备
        result = check_lab_status.invoke({"query_type": "overdue"})
        
        # 判断工具是否返回了错误提示（根据你 agent_tools.py 中的逻辑）
        if "数据库查询失败" in result:
            raise Exception(result)
            
        return {"abnormal_data": result, "error_msg": ""}
    except Exception as e:
        # 捕获异常，增加重试次数
        print(f"❌ 查库异常: {e}")
        return {"error_msg": str(e), "retry_count": state.get("retry_count", 0) + 1}

# 节点 2：大模型决策（判断异常 + 生成文案）
def decision_node(state: AgentState):
    print("--- [节点2] 大模型正在阅读数据并决策 ---")
    data = state.get("abnormal_data", "")
    
    # 如果一切正常，直接短路结束，不浪费大模型 Token
    if not data or "当前一切正常" in data:
        return {"alert_message": "当前一切正常，无需预警。"}

    # 如果有异常，调用大模型生成专业的预警文案
    system_prompt = "你是一个专业的实验室管家。请根据下面提供的异常数据，写一段发给管理员的飞书预警文案。要求：语气专业、条理清晰、直接列出超期设备名称及天数。"
    user_prompt = f"这是查库发现的异常数据：\n{data}\n请生成预警文案。"
    
    response = llm.invoke([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    
    alert_msg = response.content
    return {"alert_message": alert_msg, "approval_status": "pending"}

# 节点 3：人工审批（核心中断点）
def human_approval_node(state: AgentState):
    print("--- [节点3] 触发 Human-in-the-loop，等待审批 ---")
    # 触发中断，把待审批的消息作为 payload 传出去，流程在此挂起
    # 前端 Streamlit 收到这个 payload 后，会弹窗展示
    user_decision = interrupt({"message": state["alert_message"]})
    
    # 前端点击"同意/驳回"后，恢复执行，传入 "approved" 或 "rejected"
    return {"approval_status": user_decision}

# 节点 4：发飞书
def send_alert_node(state: AgentState):
    print("--- [节点4] 正在处理发送逻辑 ---")
    if state.get("approval_status") == "approved":
        # 调用你的飞书发送工具
        send_feishu_alert.invoke({"message": state["alert_message"]})
        return {"messages": [("assistant", "✅ 预警已通过审批，并成功发送至飞书！")]}
    else:
        return {"messages": [("assistant", "❌ 预警被管理员驳回，已取消发送。")]}

# ==========================================
# 第四步：构建图与条件路由 (Graph)
# ==========================================
builder = StateGraph(AgentState)

# 添加节点
builder.add_node("query", query_db_node)
builder.add_node("decision", decision_node)
builder.add_node("approval", human_approval_node)
builder.add_node("send", send_alert_node)

# 设置入口
builder.add_edge(START, "query")

# 路由 1：查库失败重试逻辑
def route_after_query(state: AgentState):
    if state.get("error_msg"):
        if state.get("retry_count", 0) < 3:
            return "retry" # 小于 3 次，回退重试
        else:
            return "end"   # 超过 3 次，直接结束
    return "success"       # 没报错，往下走

builder.add_conditional_edges(
    "query",
    route_after_query,
    {"retry": "query", "success": "decision", "end": END}
)

# 路由 2：判断是否需要审批
def route_after_decision(state: AgentState):
    if state.get("approval_status") == "pending":
        return "need_approval"
    return "no_alert"

builder.add_conditional_edges(
    "decision",
    route_after_decision,
    {"need_approval": "approval", "no_alert": END}
)

# 固定连线
builder.add_edge("approval", "send")
builder.add_edge("send", END)

# 编译图，并加上 MemorySaver 以支持中断后恢复状态
memory = MemorySaver()
app_graph = builder.compile(checkpointer=memory)

print("✅ LangGraph 工作流构建成功！")