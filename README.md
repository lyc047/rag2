# RAG2 智能笔记助手

基于 RAG（检索增强生成）技术的智能笔记应用，支持知识库文档检索、AI 辅助写作和 Agent 驱动的笔记管理。

## 功能特性

- **AI Agent 笔记管理** — 自然语言驱动创建、查看、修改、删除笔记，7 个工具覆盖完整 CRUD
- **知识库检索问答** — 支持 PDF/TXT/DOCX/MD/PPTX 文档上传，基于内容的语义问答
- **混合检索** — BM25 关键词检索 + ChromaDB 向量语义检索加权融合，提升召回质量
- **流式交互** — Agent 对话和文件上传均使用 SSE 实时推送进度和 Token
- **多会话管理** — 聊天会话独立存储，支持历史回溯和删除
- **页面状态保持** — AI 对话页切换标签后再返回，保留对话内容和滚动位置
- **暗色调支持** — 亮/暗主题切换，CSS 变量全局控制
- **中英双语** — 前后端完整国际化支持

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.12+) |
| 数据库 | SQLite + SQLAlchemy 2.0 异步 ORM，WAL 模式 |
| 向量库 | ChromaDB |
| LLM | Ollama (qwen3) / DeepSeek API，通过 LangChain 调用 |
| Agent | LangChain `create_agent` API，7 个工具 |
| 嵌入模型 | qwen3-embedding (Ollama) |
| 前端 | Vue 3 + Vite 5 |
| UI 组件 | Vant 4 (移动端) |
| 国际化 | 自定义 i18n (zh-CN / en) |

## 项目结构

```
rag2/
├── backend/
│   ├── main.py                    # FastAPI 入口，CORS、路由注册
│   ├── pyproject.toml              # Python 依赖
│   ├── .env                        # LLM 配置、数据库路径等
│   ├── data/                       # SQLite、ChromaDB、MD5去重、日志
│   └── app/
│       ├── config/settings.py      # 全局配置（从 .env 加载）
│       ├── core/                   # 日志、统一响应格式
│       ├── db/database.py          # SQLAlchemy 异步引擎（WAL + NullPool）
│       ├── models/                 # Note、ChatSession、ChatMessage ORM
│       ├── schemas/models.py       # Pydantic 请求/响应模型
│       ├── router/                 # health、knowledge、chat、note 路由
│       ├── services/               # 笔记服务、会话服务
│       ├── rag/                    # RAG 核心
│       │   ├── agent.py            # AgentService（7个工具 + 流式对话）
│       │   ├── rag_service.py      # 检索增强生成
│       │   ├── retriever.py        # 混合检索器（BM25 + 向量）
│       │   ├── vector_store.py     # ChromaDB 封装（知识库 + 笔记向量库）
│       │   ├── loader.py           # 多格式文件加载
│       │   └── text_splitter.py    # 文本切片
│       └── utils/                  # LLM/Embedding 工厂、MD5 去重
└── front/
    ├── vite.config.js              # Vite 配置（含 API 代理）
    ├── index.html                  # SPA 入口
    └── src/
        ├── App.vue                 # 根组件（底部导航 + KeepAlive）
        ├── style.css               # 全局样式 + CSS 变量 + Vant 主题覆写
        ├── config/api.js           # API 端点映射
        ├── router/index.js         # 路由配置
        ├── composables/            # useI18n（国际化）、useTheme（主题）
        └── views/                  # 页面组件
            ├── AIChat.vue          # AI 对话（SSE 流式渲染）
            ├── NoteList.vue        # 笔记列表（分类筛选、搜索）
            ├── NoteEditor.vue      # 笔记编辑器
            ├── KnowledgeBase.vue   # 知识库管理
            └── Profile.vue         # 个人设置
```

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- Ollama（本地 LLM 模式，可选）

### 1. 后端

```bash
cd backend

# 安装依赖
uv sync

# 配置环境变量（编辑 .env）
# LLM_TYPE=OLLAMA         # 或 DEEPSEEK
# OLLAMA_CHAT_MODEL=qwen3:latest
# OLLAMA_EMBED_MODEL=qwen3-embedding:0.6b

# 启动（默认端口 8005）
.venv/Scripts/uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

### 2. 前端

```bash
cd front

# 安装依赖
npm install

# 启动开发服务器（默认端口 3001）
npm run dev
```

### 3. 访问

- 前端：`http://localhost:3001`
- 后端 API 文档：`http://localhost:8005/docs`

## 核心实现

### Agent 工具链

Agent 拥有 7 个工具，可自主决定调用：

- `search_knowledge` — 搜索知识库文档
- `search_notes` — 语义搜索用户笔记
- `create_note` — 创建笔记
- `get_note` — 获取笔记详情
- `update_note` — 修改笔记
- `delete_note` — 删除笔记（需用户确认）
- `get_current_time` — 获取当前时间

流式对话通过 SSE 返回 `token`、`tool_start`、`tool_end`、`finish` 四种事件。

### 混合检索

```
用户查询 ──┬── BM25Retriever（关键词匹配，权重 0.3）
           └── ChromaDB Vector Search（语义匹配，权重 0.7）
                    │
              EnsembleRetriever（加权融合去重）
                    │
              返回 TOP_K 结果 → LLM 生成回答
```

### 数据库锁解决

SQLite 启用 WAL 模式 + `NullPool`（禁用连接池）+ `busy_timeout=5000ms`，配合 Agent 工具独立会话提交，彻底解决"database is locked"问题。

### 页面缓存

AI 对话页使用 Vue `<KeepAlive>` 缓存组件实例，切换标签时记录滚动比例，切回时通过 `requestAnimationFrame` + `setTimeout` 双重恢复确保位置准确。
