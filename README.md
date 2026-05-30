# RAG2 智能笔记助手

基于 RAG（检索增强生成）技术的智能笔记应用，支持知识库文档检索、AI 辅助写作和 Agent 驱动的笔记管理。

## 功能特性

- **AI Agent 笔记管理** — 自然语言驱动创建、查看、修改、删除笔记，7 个工具覆盖完整 CRUD
- **知识库检索问答** — 支持 PDF/TXT/DOCX/MD/PPTX 文档上传，基于内容的语义问答
- **混合检索 + LLM 重排序** — BM25 关键词 + ChromaDB 向量语义 RRF 加权融合 + DeepSeek 精排，精确短语匹配奖励
- **流式交互** — Agent 对话和文件上传均使用 SSE 实时推送进度和 Token
- **反幻觉机制** — 归因强制 Prompt + CoT 内部推理 + 信息边界约束 + 输出格式化清洗 + 遗漏自检
- **查询预处理** — 短查询关键词增强，提升 BM25 命中率
- **时间感知检索** — 文档入库时自动提取文件时间戳与内容年份范围，回答中保留时间限定
- **语义分块** — 支持递归字符分割与 Markdown 结构感知语义分块双策略
- **多会话管理** — 聊天会话独立存储，支持单选/多选/全选删除 + 一键清空
- **笔记批量管理** — 笔记列表支持编辑模式多选删除，带确认提示
- **页面状态保持** — AI 对话页切换标签后再返回，保留对话内容和滚动位置
- **暗色调支持** — 亮/暗主题切换，CSS 变量全局控制，选中项在两种模式下均有明显视觉反馈
- **中英双语** — 前后端完整国际化支持
- **检索评估体系** — 20+ 条对抗测试用例，支持 MRR / Recall@K / Hit Rate / 来源准确率指标

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
│       │   ├── rag_service.py      # 检索增强生成（Prompt + 后处理）
│       │   ├── retriever.py        # 混合检索器（RRF + 精确匹配 + BM25缓存）
│       │   ├── query_processor.py  # 查询预处理（关键词提取 + 短查询增强）
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
- Ollama（本地嵌入模型，可选但推荐）

### 方式一：一键启动（推荐）

```bash
# 第一次使用：安装所有依赖
双击 setup.bat

# 之后每次启动：
双击 start.bat
```

`start.bat` 会自动启动后端 + 前端 + 打开浏览器。

### 方式二：手动启动

#### 1. 配置

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

#### 2. 后端

```bash
cd backend
uv sync
.venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8005
```

#### 3. 前端

```bash
cd front
npm install
npm run dev
```

### 访问

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

### 混合检索（RRF 加权融合）

```
用户查询 ──┬── ChromaDB Vector Search（语义，权重 0.7，Cosine 距离）
           ├── BM25 关键词检索（稀疏匹配，权重 0.3）
           └── 精确短语匹配奖励（稀有实体 ×1.5）
                    │
              RRF（Reciprocal Rank Fusion）统一排序
                    │
         相似度阈值过滤 → 返回 TOP_K 结果 → LLM 生成回答
```

检索支持 BM25 索引缓存（增量更新），避免每次检索全量重建。

### 数据库锁解决

SQLite 启用 WAL 模式 + `NullPool`（禁用连接池）+ `busy_timeout=5000ms`，配合 Agent 工具独立会话提交，彻底解决"database is locked"问题。

### 页面缓存

AI 对话页使用 Vue `<KeepAlive>` 缓存组件实例，切换标签时记录滚动比例，切回时通过 `requestAnimationFrame` + `setTimeout` 双重恢复确保位置准确。

## 版本历史

| 版本 | 日期 | 类型 | 说明 |
|------|------|------|------|
| v2.0.0 | 2026-05-30 | 全栈 | **RAG 回答质量全面升级**：CoT 内部推理 + 信息边界约束 + 输出格式化清洗（Agent 静默推理→后端清洗→流式输出干净答案）；**LLM 重排序**（DeepSeek 精排叠加 RRF，MRR +7.7%）；**时间感知检索**（文件时间戳 + 内容年份提取）；**语义分块策略**（Markdown 标题感知）；**检索评估体系**（20+ 对抗用例，MRR/Recall@K/Hit Rate/来源准确率）；**前端批量管理**（会话/笔记编辑模式多选删除）；**UI 优化**（选中项高亮适配亮暗双模） |
| v1.1.2 | 2026-05-28 | 内核 | RAG检索精度全面升级：RRF融合检索(BM25+向量+精确匹配)、Cosine距离度量、归因强制Prompt+反幻觉机制+遗漏自检、查询预处理模块、解码参数优化(frequency_penalty/presence_penalty/top_p)、BM25索引缓存 |
| v1.0.2 | 2026-05-28 | 前端 | 修复暗色调搜索栏输入文字不可见；修复搜索高亮在暗色调下与背景同色；搜索支持按分类标签过滤 |
| v1.0.1 | 2026-05-28 | 前端 | AI Agent 笔记管理、页面状态保持(KeepAlive)、SQLite 锁修复(WAL+NullPool)、暗色调支持 |
| v1.0.0 | 2026-05-27 | 内核 | 初始版本：RAG 智能笔记助手，知识库检索、AI 对话、笔记 CRUD、混合检索 |
