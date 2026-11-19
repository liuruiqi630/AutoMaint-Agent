import sys
import io
# 强制将标准输出转换为 utf-8（解决 Windows 下 emoji 乱码问题）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.types import Command

# 直接引入你已经构建好的 LangGraph 工作流
from agent_graph import app_graph

load_dotenv()

def run_cron_job():
    print("🤖 管家开始日常巡检（后台模式）...\n")
    
    # 每次运行分配一个新的 thread_id，保证状态干净
    import uuid
    config = {"configurable": {"thread_id": f"cron_{uuid.uuid4().hex[:8]}"}}
    
    initial_state = {
        "messages": [HumanMessage(content="请检查实验室是否有超期未维护的设备，以及是否有耗材告急的设备。")],
        "retry_count": 0,
        "error_msg": ""
    }
    
    # 启动图
    app_graph.invoke(initial_state, config)
    
    # 检查是否被 interrupt 打断（等待审批）
    state = app_graph.get_state(config)
    
    while state.next and "approval" in state.next:
        # 提取需要审批的消息
        alert_msg = state.values.get("alert_message", "无预警内容")
        print(f"\n⚠️ 发现设备异常，Agent 请求发送飞书预警：\n{alert_msg}\n")
        
        # ----------------------------------------------------
        # 【模式一：终端手动审批】（用于测试和演示）
        # 如果你做成纯后台自动任务，可以把这段 input 删掉，直接写 resume_val = "approved"
        # ----------------------------------------------------
        decision = input("是否同意发送？(y/n): ").strip().lower()
        resume_val = "approved" if decision == 'y' else "rejected"
        
        # 恢复图执行
        print("处理中...")
        app_graph.invoke(Command(resume=resume_val), config)
        
        # 再次更新状态，防止连续中断
        state = app_graph.get_state(config)
        
    # 打印最终回复
    if state.values.get("messages"):
        final_message = state.values["messages"][-1]
        
        # 因为 agent_graph.py 里返回的是元组 ("assistant", "内容")
        # 我们需要提取第二个元素
        if isinstance(final_message, tuple):
            content = final_message[1]
        else:
            content = final_message.content
            
        print("\n================ 最终输出 ================")
        print(content)

if __name__ == "__main__":
    run_cron_job()