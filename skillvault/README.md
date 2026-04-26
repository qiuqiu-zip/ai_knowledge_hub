# SkillVault

SkillVault 是一个长期自用的 AI 知识资产库 MVP，支持来源可追踪的 GitHub/手动资料采集、RAG 索引、Prompt/Skill 管理、Skill 草稿生成。

## 技术栈

- Backend: Python, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, pgvector, httpx, Pydantic, LlamaIndex
- Frontend: Vue 3, Vite, Element Plus, TypeScript, Axios
- Task System: PostgreSQL `sync_job` + Python Worker 轮询
- Deploy: Docker Compose

## 目录结构

```text
skillvault/
├── backend/
├── frontend/
├── docker-compose.yml
├── start.sh
├── .env.example
└── README.md
```

## 一键启动命令

1. 首次准备环境变量：

```bash
cp .env.example .env
```

2. 一键启动前端 + 后端（含 worker + scheduler）：

```bash
./start.sh
```

3. 常用子命令：

```bash
./start.sh backend   # 仅后端链路：postgres + backend + worker + scheduler
./start.sh frontend  # 仅前端
./start.sh down      # 停止全部服务
```

## 访问地址

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Health: `http://localhost:8000/healthz`

## 环境变量说明

- `DATABASE_URL`: PostgreSQL 连接串
- `GITHUB_TOKEN`: GitHub API Token（可选，未配置时走公开低频 API）
- `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`: OpenAI-compatible 聊天模型
- `EMBEDDING_API_KEY` / `EMBEDDING_BASE_URL` / `EMBEDDING_MODEL`: OpenAI-compatible embedding
- `EMBEDDING_DIMENSION`: pgvector 维度（默认 1536）
- `ADMIN_TOKEN`: 可选接口保护 token（通过 `X-Admin-Token` 传入）
- `SCHEDULER_POLL_INTERVAL_SECONDS`: 自动同步调度轮询间隔（默认 60 秒）
- `DEFAULT_GITHUB_SYNC_INTERVAL_MINUTES`: Source 默认同步间隔（默认 1440 分钟）
- `MIN_GITHUB_SYNC_INTERVAL_MINUTES`: 最小允许同步间隔（默认 10 分钟）

## 数据库 Migration

Backend 容器启动时执行：

```bash
alembic upgrade head
```

如需手动执行：

```bash
cd backend
alembic upgrade head
```

## 如何导入 GitHub 仓库

1. 在前端 `GitHub Import` 页面输入仓库 URL。
2. 调用 `POST /api/github/import`，返回 `job_id`。
3. Worker 异步执行 `github_sync`，采集 README 并入库。
4. 若内容为新版本，会自动继续创建任务：
   - `document_chunk`
   - `document_embed`
   - `summarize`
   - `skill_generate`

## 如何启动 Worker

Compose 已内置 `worker` 与 `scheduler` 服务：

```bash
python -m app.workers.worker
python -m app.workers.scheduler
```

Worker 使用 PostgreSQL `FOR UPDATE SKIP LOCKED` 领取任务，支持多进程不重复消费、失败重试、超时恢复。

## 如何使用 RAG 问答

- 搜索：`POST /api/search`（`mode=keyword|vector`）
- 问答：`POST /api/rag/ask`
  - 输入：`question`
  - 输出：`answer + citations`
  - 引用字段包括：`source_url`、`repo`、`file_path`、`license`、`chunk_id`

## 当前限制

- MVP 仅抓取 GitHub README，未抓 docs/examples 全量目录
- 未实现复杂权限体系（仅可选 `ADMIN_TOKEN`）
- Hybrid Search 预留，当前提供 keyword/vector 两种
- LLM 与 Embedding 未配置 key 时使用 mock 输出（便于本地联调）

## Roadmap

1. GitHub docs/examples 多文件采集
2. Hybrid Search / Rerank
3. Skill 版本对比与回滚
4. 多用户/团队协作与权限
5. 任务系统可替换为 RocketMQ
