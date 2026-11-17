# 🤖 AutoMaint-Agent：实验室设备智能预警管家

## 📖 项目简介
**AutoMaint-Agent** 是一个基于大语言模型（LLM）与智能体（Agent）架构的实验室设备自动化巡检系统。
针对传统实验室设备维保“靠人记、易遗漏、响应慢”的痛点，本项目引入了**“数据找人”**的理念。系统每日定时唤醒，Agent 会自主调用工具查询 MySQL 数据库，识别超期未维护或耗材告急的设备，并主动向飞书群推送预警。同时提供支持多轮对话的 Web 可视化界面，实现“静默后台监控”与“Web端按需交互”的双重业务闭环。

## ✨ 核心特性
*   **🧠 智能体自主决策**：基于 **LangChain 1.x** 的 `create_agent` 架构，大模型能自主判断何时查库、何时发预警，无需硬编码业务流。
*   **🛡️ 企业级鲁棒性（防脏数据）**：底层 SQL 查询加入了状态校验（过滤报废设备）与非负校验（过滤负库存bug），确保 Agent 的预警100%精准。
*   **🔌 标准化工具集成**：将 MySQL 查询与飞书 Webhook 封装为标准 `Tool`，采用 `try...finally` 保障数据库连接池安全。
*   **💬 全栈可视化交互**：基于 **Streamlit** 构建 Web 端。利用 `@st.cache_resource` 缓存模型，利用 `st.session_state` 实现多轮对话记忆与状态流转。
*   **⏰ 无人值守调度**：配合 Windows 任务计划程序（或 Cron），实现每天定时自动唤醒并落盘日志（Log）。
*   **🔐 配置与代码分离**：使用 `.env` 隔离敏感环境变量（API Key、Webhook、数据库密码），确保代码开源安全。

## 🛠️ 技术栈
*   **大模型**：DeepSeek-Chat API (兼容 OpenAI 格式)
*   **Agent 框架**：LangChain 1.x, Langgraph
*   **数据库**：MySQL 8.4 (使用 `mysql-connector-python` 驱动)
*   **前端框架**：Streamlit
*   **工程化工具**：python-dotenv, Faker (造测试数据), Requests (飞书 API)

## 🏗️ 系统架构流程
1.  **触发层**：定时任务 (`.bat` + Windows Task Scheduler) 或 用户网页输入。
2.  **控制层**：Agent 接收指令，结合系统提示词（System Prompt）分析意图。
3.  **工具层**：
    *   `check_lab_status(query_type)`：连接 MySQL 执行安全查询，返回异常列表。
    *   `send_feishu_alert(message)`：将自然语言报告通过 HTTP POST 推送到飞书。
4.  **输出层**：飞书群收到预警消息，或网页端渲染对话气泡。

---

## 🚀 快速开始

### 1. 环境准备
建议使用 Python 3.11+，并创建虚拟环境：
```bash
python -m venv .venv
# Windows 激活：
.\.venv\Scripts\activate
# Mac/Linux 激活：
source .venv/bin/activate
```
安装依赖：
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量
在项目根目录创建 `.env` 文件，填入你的敏感信息：
```env
DEEPSEEK_API_KEY=sk-你的DeepSeek密钥
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/你的飞书Webhook
DB_PASSWORD=你的MySQL密码
```

### 3. 初始化数据库与数据
执行造数脚本，生成包含正常、超期、报废、脏数据的 150 条模拟设备数据：
```bash
python generate_data.py
```

### 4. 运行 Web 端 (开发环境)
```bash
streamlit run app.py
```
浏览器将自动打开 `http://localhost:8501`。你可以使用底部的聊天框，或者点击左侧的“立即执行全量巡检”。

### 5. 配置后台无人值守巡检
*   在根目录创建 `run_agent.bat` 批处理文件（注意切换至虚拟环境）。
*   打开 Windows 任务计划程序（Task Scheduler），创建基本任务。
*   触发器设为每天 08:00，操作设为启动该 `.bat` 脚本。

---

## 📁 项目结构
```text
AutoMaint-Agent/
├── .env                  # 环境变量配置（切勿提交至 Git）
├── .gitignore            # Git 忽略文件配置
├── app.py                # Streamlit Web 主程序
├── agent_core.py         # Agent 核心逻辑封装与定时执行入口
├── agent_tools.py        # 数据库查询与飞书 API 工具封装
├── generate_data.py      # 基于 Faker 的模拟数据生成脚本
├── requirements.txt      # 项目依赖列表
└── run_agent.bat         # Windows 定时唤醒脚本
```

---

## ☁️ 公网部署 (Streamlit Community Cloud)
本项目已适配 Streamlit 云端托管：
1. 将代码上传至 GitHub 仓库（确保 `.env` 在 `.gitignore` 中）。
2. 登录 [share.streamlit.io](https://share.streamlit.io/)，关联仓库。
3. 在 **Advanced settings -> Secrets** 中，按 TOML 格式填入 `.env` 中的环境变量。
4. 点击 Deploy 即可生成公网可访问的网页链接。

---

## 💡 开发踩坑记录（Backend Dev Notes）
*   **Windows 控制台编码问题**：使用 `.bat` 运行 Python 脚本时遇到 `UnicodeEncodeError`。通过在代码顶部强制 `sys.stdout.reconfigure(encoding='utf-8')`，并在 `.bat` 脚本中使用 `chcp 65001` 彻底解决中文字符与 Emoji 输出报错。
*   **Streamlit 状态丢失问题**：Streamlit 刷新机制会导致组件状态丢失，通过深入理解 `st.session_state` 与 `st.rerun()` 的底层逻辑，实现了“按钮触发任务并持久化渲染”。
*   **数据库连接泄露**：通过 `try...except...finally` 结合 `mysql.connector`，确保在遭遇异常时连接池能够安全释放，解决了网络连接停留在 `CLOSE_WAIT` 状态的隐患。

---
*Created by [刘锐奇] | 2026*

---

**最后一步**：把这个 README 里的 `[你的名字]` 换成你，然后连同你删减过的 `requirements.txt`、代码文件，一起 `git push` 到 GitHub 吧！去感受一下自己的项目被别人点 Star 的成就感！
