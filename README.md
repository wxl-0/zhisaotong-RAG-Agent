
````markdown
# 智扫通 RAG Agent

> 基于 LangChain ReAct Agent + RAG + Streamlit + uv 的扫地机器人智能客服系统

* * *

# 使用必看

请先完成以下配置后再运行项目：

1. 准备好通义模型调用所需的 API Key  
2. 修改 `config/agent.yml` 中的 `amap_key`，替换为你实际申请的高德 Web 服务 Key  
3. 如需使用报告/数据分析相关能力，确认 `data/external/records.csv` 文件存在且字段可用  
4. 首次运行前建议先执行知识库向量化脚本，将 `data/` 目录中的文档写入 Chroma 向量库  

* * *

## 项目简介

`zhisaotong-RAG-Agent` 是一个面向扫地机器人 / 扫拖一体机器人场景的 AI 智能体项目。  
系统以 **Streamlit** 构建轻量级前端网页，后端基于 **LangChain** 搭建 ReAct Agent，并结合 **RAG 检索增强生成** 提供更可靠的知识问答能力。

项目整合了以下核心能力：

- **RAG 增强检索**：将产品手册、常见问题、维护保养、故障排查等文档写入本地向量库，回答问题时优先检索知识库内容
- **天气与定位能力**：结合高德地图 Web 服务，支持实时天气查询与基于 IP 的位置获取
- **总结汇报模式**：中间件识别特定意图后，可自动切换 Prompt，生成面向用户使用数据的总结报告
- **多工具调用**：Agent 可根据用户问题自主选择并调用工具完成任务
- **流式响应**：前端支持流式输出，增强对话体验
- **uv 依赖管理**：项目使用 `pyproject.toml` 管理依赖，适合用 `uv` 快速安装和运行

* * *

## ✨ 核心特性

| 特性 | 说明 |
|---|---|
| LLM | 阿里云通义千问 `qwen3-max` |
| Embedding | DashScope `text-embedding-v4` |
| 向量数据库 | Chroma（本地持久化） |
| Agent 框架 | LangChain ReAct Agent + LangGraph |
| 前端 | Streamlit 对话式 Web 界面 |
| 外部服务 | 高德地图 Web 服务（天气、定位） |
| 动态提示词 | 中间件按上下文自动切换 Prompt |
| 知识库去重 | 基于 MD5 追踪已处理文件，避免重复入库 |
| 依赖管理 | uv / `pyproject.toml` |

* * *

## 系统架构

```text
┌──────────────────────────────────────────────┐
│          Streamlit 前端 (app.py)            │
│   - 对话输入  - 流式输出  - 会话状态管理      │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│       ReAct Agent (agent/react_agent.py)     │
│  ┌─────────────────────────────────────────┐ │
│  │ 中间件层 (agent/tools/middleware.py)    │ │
│  │ ├─ monitor_tool       工具调用监控       │ │
│  │ ├─ log_before_model   模型调用前日志     │ │
│  │ └─ report_prompt_switch 提示词切换       │ │
│  └─────────────────────────────────────────┘ │
│  工具集：                                     │
│  rag_summarize / get_weather /                │
│  get_user_location / get_user_id /            │
│  get_current_month / fetch_external_data /    │
│  fill_context_for_report                      │
└───────────────┬───────────────┬──────────────┘
                │               │
                ▼               ▼
        ┌──────────────┐  ┌──────────────────┐
        │  RAG 服务     │  │ 高德地图服务      │
        │  rag/         │  │ 天气 / 定位       │
        └──────┬───────┘  └──────────────────┘
               │
        ┌──────▼─────────────────────────────┐
        │   Chroma 向量数据库 (chroma_db/)   │
        │   Embedding: text-embedding-v4     │
        │   知识库文档来源：data/             │
        │   支持 TXT / PDF                   │
        └────────────────────────────────────┘
````

---

## 目录结构

```text
zhisaotong-RAG-Agent/
├── agent/
│   ├── react_agent.py                # ReAct Agent 核心逻辑
│   └── tools/
│       ├── agent_tools.py            # 工具函数定义
│       └── middleware.py             # Agent 中间件
├── chroma_db/                        # Chroma 本地持久化目录
├── config/
│   ├── agent.yml                     # 高德 Key / 外部数据配置
│   ├── chroma.yml                    # 向量库与切分参数配置
│   ├── prompts.yml                   # Prompt 路径配置
│   └── rag.yml                       # 模型配置
├── data/
│   ├── external/
│   │   └── records.csv               # 外部业务数据
│   ├── 扫地机器人100问.pdf
│   ├── 扫地机器人100问2.txt
│   ├── 扫拖一体机器人100问.txt
│   ├── 故障排除.txt
│   ├── 维护保养.txt
│   └── 选购指南.txt
├── model/
│   └── factory.py                    # 模型工厂（LLM + Embedding）
├── prompts/
│   ├── main_prompt.txt               # 主系统提示词
│   ├── rag_summarize.txt             # RAG 总结提示词
│   └── report_prompt.txt             # 报告模式提示词
├── rag/
│   ├── rag_service.py                # RAG 检索总结服务
│   └── vector_store.py               # Chroma 向量库管理
├── utils/
│   ├── config_handler.py             # YAML 配置读取
│   ├── file_handler.py               # TXT / PDF 文档加载
│   ├── logger_handler.py             # 日志工具
│   ├── path_tool.py                  # 路径工具
│   └── prompt_loader.py              # Prompt 加载器
├── app.py                            # Streamlit 前端入口
├── main.py                           # 项目入口/调试文件
├── md5.text                          # 已处理文档的 MD5 记录
├── pyproject.toml                    # uv 项目配置
└── README.md
```

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/wxl-0/zhisaotong-RAG-Agent.git
cd zhisaotong-RAG-Agent
```

### 2. 使用 uv 安装依赖

```bash
uv sync
```

### 3. 配置项目参数

修改以下配置文件：

#### `config/rag.yml`

```yaml
chat_model_name: qwen3-max
embedding_model_name: text-embedding-v4
```

#### `config/agent.yml`

```yaml
external_data_path: data/external/records.csv

# 高德 Web服务 Key
amap_key: 你的高德APIkey

# 可选：前端/网关把真实用户IP写到哪个环境变量里
user_real_ip_env: USER_REAL_IP
```

#### `config/chroma.yml`

```yaml
collection_name: agent
persist_directory: chroma_db
k: 3
data_path: data
md5_hex_store: md5.text
allow_knowledge_file_type: ["txt", "pdf"]
chunk_size: 200
chunk_overlap: 20
separators: ["\n\n", "\n", ".", "!", "?", "。", "！", "？", " ", ""]
```

### 4. 初始化知识库

首次运行前，建议先将 `data/` 目录中的知识文档写入向量库：

```bash
uv run python rag/vector_store.py
```

### 5. 启动前端

```bash
uv run streamlit run app.py
```

启动后，在浏览器中打开 Streamlit 提示的本地地址即可开始使用。

---

## 配置说明

### 1. 模型配置

项目当前通过 `model/factory.py` 统一创建：

* 聊天模型：`qwen3-max`
* 向量模型：`text-embedding-v4`

后续可以通过修改 `config/rag.yml` 扩展为其他模型。

### 2. Prompt 配置

`config/prompts.yml` 用于指定系统提示词路径：

```yaml
main_prompt_path: prompts/main_prompt.txt
rag_summarize_prompt_path: prompts/rag_summarize.txt
report_prompt_path: prompts/report_prompt.txt
```

项目支持两类核心提示词模式：

* **普通问答模式**：回答扫地机器人相关问题
* **报告模式**：在获取用户数据后，生成使用情况总结和建议

### 3. 知识库配置

知识库默认读取 `data/` 目录中的 `.txt` 和 `.pdf` 文件，并按如下策略切分：

* `chunk_size = 200`
* `chunk_overlap = 20`
* 检索条数 `k = 3`

### 4. 去重机制

项目会将已处理文件的 MD5 记录到 `md5.text` 中。
如果知识库文件未变化，重复执行向量化脚本时会自动跳过，避免重复写入向量库。

---

## 核心能力说明

### 1. RAG 问答

当用户提问时，系统会：

1. 将问题发送给向量检索器
2. 从 Chroma 中召回相关文档片段
3. 结合 `rag_summarize.txt` 提示词，让模型根据参考资料生成回答

这样可以减少模型“胡编”的概率，让回答更贴近本地知识库内容。

### 2. 实时天气与定位

系统支持结合高德地图服务完成：

* 用户城市定位
* 实时天气查询
* 结合当前城市天气给出保养或使用建议

### 3. 报告生成模式

项目包含一组与用户数据相关的工具：

* `get_user_id`
* `get_current_month`
* `fetch_external_data`
* `fill_context_for_report`

这使得 Agent 不仅能做 FAQ 问答，也可以根据外部数据生成结构化总结报告。

---

## 示例问题

你可以尝试在页面中输入类似问题：

* 扫地机器人适合小户型吗？
* 扫地机器人在我所在城市这种天气下应该如何保养？
* 扫地机器人总是迷路怎么办？
* 扫拖一体机器人和扫地机器人有什么区别？
* 帮我生成一份本月机器使用情况报告

---

## 适用场景

* 产品 FAQ 智能问答
* 扫地机器人售前咨询
* 售后故障排查辅助
* 维护保养建议生成
* 内部知识库问答
* 基于业务数据的报告生成

---

## 后续可优化方向

* 增加 Docker 部署方案
* 增加 API 服务层（如 FastAPI）
* 支持上传文档后自动入库
* 支持多用户会话隔离
* 增加更完整的日志与监控能力
* 增加更丰富的前端交互界面
* 扩展更多设备品类知识库

---

## License

如需开源发布，建议补充 `LICENSE` 文件，例如 MIT License。

```

要是你愿意，我可以继续给你一版“更像 bamboo-moon 那个仓库排版风格”的增强版，带徽章、运行截图占位、以及更漂亮的章节标题。
::contentReference[oaicite:1]{index=1}
```

[1]: https://github.com/bamboo-moon/zhisaotong-Agent "GitHub - bamboo-moon/zhisaotong-Agent: 用streamlit编写简易前端网页，调用高德MCP提供实时定位和天气等服务,基于LangChain编写出一个AI智能体 · GitHub"
