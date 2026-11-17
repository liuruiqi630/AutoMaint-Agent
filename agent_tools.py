import os
import mysql.connector
import requests
from langchain.tools import tool
from dotenv import load_dotenv

# 加载 .env 文件里的变量
load_dotenv()

@tool
def check_lab_status(query_type: str) -> str:
    """查询实验室设备状态。参数 query_type 必须是 'overdue' 或 'low_stock'。"""
    conn = mysql.connector.connect(
        host="localhost", 
        user="root", 
        password=os.getenv("DB_PASSWORD", "123456"), # 从环境变量读密码
        database="lab_system"
    )
    # ... 下面的代码保持不变 ...
    cursor = conn.cursor()
    result = ""
    try:
        if query_type == 'overdue':
            sql = "SELECT device_name, DATEDIFF(CURDATE(), last_maintenance) as days FROM equipment WHERE DATEDIFF(CURDATE(), last_maintenance) > 30 AND status = 'active'"
            cursor.execute(sql)
            for row in cursor.fetchall(): result += f"- {row[0]}：已超期 {row[1]} 天未维护\n"
        elif query_type == 'low_stock':
            sql = "SELECT device_name, consumable_stock FROM equipment WHERE consumable_stock < 5 AND consumable_stock >= 0 AND status = 'active'"
            cursor.execute(sql)
            for row in cursor.fetchall(): result += f"- {row[0]}：库存告急，仅剩 {row[1]} 件\n"
    except Exception as e:
        result = f"数据库查询失败：{e}"
    finally:
        cursor.close()
        conn.close()
    return result if result else "当前一切正常。"

@tool
def send_feishu_alert(message: str) -> str:
    """将预警消息发送到飞书群。"""
    # 从环境变量中安全读取 Webhook 地址
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    
    if not webhook_url:
        return "错误：未配置飞书 Webhook 地址。"

    payload = {
        "msg_type": "text",
        "content": {"text": f"🚨 **实验室管家预警**\n\n{message}"}
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        if response.json().get("code") == 0:
            return "消息已成功发送至飞书群！"
        return f"发送失败: {response.text}"
    except Exception as e:
        return f"发送异常：{e}"