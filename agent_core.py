import sys
import io
# 强制将标准输出和错误输出转换为 utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate

from agent_tools import check_lab_status, send_feishu_alert

load_dotenv()


# 1. 初始化大模型（密钥从环境变量读取）
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise ValueError("未找到 DEEPSEEK_API_KEY，请检查 .env 文件")

llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=api_key,
    temperature=0,
)


# 2. 准备工具列表
tools = [check_lab_status, send_feishu_alert]


# 3. 新版 create_agent 的推荐方式：用 system_prompt 描述职责，而不是手写 ReAct 模板
system_prompt = """你是一个专业的实验室设备管家。

你的职责是：
1. 巡检实验室设备，检查是否有“维护超期”或“耗材告急”的情况。
2. 一旦发现异常，必须调用 send_feishu_alert 工具，把详细情况整理成一段话发给管理员。
3. 如果没有异常，直接回复“当前一切正常”，不要调用发送工具。

注意：
- 查询超期用 check_lab_status，参数 query_type 传 'overdue'。
- 查询耗材用 check_lab_status，参数 query_type 传 'low_stock'。
- 只有确实发现异常时，才调用 send_feishu_alert。
"""


# 4. 创建 Agent（新版标准入口）
agent_executor = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt,
)


# 5. 运行测试
if __name__ == "__main__":
    print("🤖 管家开始日常巡检...\n")

    result = agent_executor.invoke(
        {
            "messages": [
                (
                    "user",
                    "请检查实验室是否有超期未维护的设备，以及是否有耗材告急的设备。"
                    "如果有，把详细情况整理成一段话，发给飞书群。",
                )
            ]
        }
    )

    # 新版返回的是一个包含 messages 列表的字典，最后一条就是 Agent 的最终回复
    final_message = result["messages"][-1]
    print("\n================ 最终输出 ================")
    print(final_message.content)