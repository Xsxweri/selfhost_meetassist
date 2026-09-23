# Meeting Assistant · AI 会议助理

AI 驱动的后端会议助理：实时语音转写、向量语义检索、结构化纪要与待办提取、合规授权留痕、分享与多格式导出、异步任务队列。

## 技术栈

| 领域 | 选型 |
|---|---|
| Web 框架 | FastAPI + Uvicorn（全异步） |
| 数据库 | PostgreSQL 16 + pgvector（Docker） |
| ORM / 迁移 | SQLAlchemy 2.0 asyncio + asyncpg + Alembic |
| 缓存 / 队列 | Redis 7（Celery broker & backend） |
| 异步任务 | Celery（Windows 需 `--pool=solo`） |
| ASR | faster-whisper + CTranslate2（GPU 需 cuDNN 9 + cuBLAS） |
| LLM / Embedding | Ollama：`qwen2.5:7b` + `bge-m3`（1024 维） |
| 鉴权 | JWT（python-jose）+ bcrypt（passlib） |
| 导出 | reportlab（PDF，内置 CJK 字体）、python-docx（DOCX） |
| 包管理 | uv |

## 功能特性

- **鉴权与隔离**：JWT 登录，会议按 `owner_id` 归属隔离
- **合规留痕**：录音授权 append-only（grant/revoke），删除会议自动撤回授权
- **实时转写**：WebSocket 推流，16kHz 单声道 PCM，边说边出字幕并落库
- **向量检索**：转录分段落库 bge-m3 向量，支持语义搜索
- **结构化纪要**：LLM 生成 summary + key_points + 待办（负责人/截止/优先级/状态）
- **软删除与恢复**：`deleted_at` 标记，可恢复
- **审计日志**：登录、增删改、授权、分享、导出等全事件可查
- **分享与导出**：只读分享链接（token/过期/撤回/下载开关），导出 MD / JSON / DOCX / PDF
- **异步化**：纪要生成可入队 Celery，轮询任务状态

## 目录结构
```
app/ 
├── api/v1/ # 路由：auth meetings consents stream summaries audit exports shares tasks 
├── core/ # 配置(config.py) 与 安全(security.py) 
├── curd/ # 数据访问层 
├── db/ # 异步会话 
├── models/ # SQLAlchemy 模型 
├── schemas/ # Pydantic 模型 
├── services/ # asr / llm / export / meeting 业务服务 
├── workers/ # Celery 实例与任务 
└── main.py # FastAPI 入口 
alembic/ # 数据库迁移（建表唯一入口） 
scripts/ws_test.py # WebSocket 转写测试客户端 
docker-compose.yml # PostgreSQL(pgvector) + Redis
```

## 环境准备

### 1. 依赖

```powershell
uv sync
```

### 2. Ollama 模型

```powershell
ollama pull qwen2.5:7b
ollama pull bge-m3
```

### 3. GPU 加速（可选，RTX 显卡）

- **Ollama**：需较新 NVIDIA 驱动（旧驱动会报 `device kernel image is invalid`），升级后 `ollama ps` 应显示 100% GPU。
- **faster-whisper**：CTranslate2 4.x 需 **cuDNN 9 + cuBLAS**：
  ```powershell
  uv pip install nvidia-cudnn-cu12 nvidia-cublas-cu12
  ```
  并把 venv 下 `nvidia/cudnn/bin`、`nvidia/cublas/bin` 加入 `PATH`。验证：
  ```powershell
  python -c "import ctranslate2; print(ctranslate2.get_cuda_device_count())"  # >=1 即可用 cuda
  ```
  > Ollama 的 GPU 与 faster-whisper 的 GPU 是两套独立运行库，需分别配置。

## 快速开始

```powershell
# 1. 起 PostgreSQL + Redis
docker compose up -d

# 2. 数据库迁移（建表唯一入口，勿用 create_all）
uv run alembic upgrade head

# 3. 起 API（本地开发建议 tiny+cpu，避免首次加载卡顿）
$env:WHISPER_MODEL="tiny"; $env:WHISPER_DEVICE="cpu"
uv run uvicorn app.main:app --reload --ws-ping-interval 60 --ws-ping-timeout 120

# 4. 另开终端起 Celery worker（Windows 必须 --pool=solo）
uv run celery -A app.workers.celery_app.celery worker --loglevel=info --pool=solo
```

- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health

> GPU 转写：把 `$env:WHISPER_DEVICE="cuda"`、`$env:WHISPER_MODEL="small"`（或更大）后再启动 uvicorn。

## 配置项（`.env`）

在项目根目录创建 `.env`（已在 `.gitignore` 中排除）：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `APP_NAME` | Meeting Assistant | 应用名 |
| `DEBUG` | True | 调试模式 |
| `DB_HOST` / `DB_PORT` | localhost / 5432 | 数据库地址 |
| `DB_USER` / `DB_PASSWORD` | postgres / postgres | 数据库账号 |
| `DB_NAME` | meeting_assistant | 数据库名 |
| `OLLAMA_BASE_URL` | http://localhost:11434 | Ollama 地址 |
| `LLM_MODEL` | qwen2.5:7b | 生成纪要的模型 |
| `EMBEDDING_MODEL` | bge-m3 | 向量模型（1024 维） |
| `ASR_BACKEND` | local | local / cloud |
| `WHISPER_MODEL` | small | tiny/base/small/medium/large |
| `WHISPER_DEVICE` | auto | auto / cpu / cuda |
| `WHISPER_COMPUTE_TYPE` | int8 | 8GB 显存友好 |
| `ASR_SAMPLE_RATE` | 16000 | 采样率 |
| `ASR_FLUSH_SECONDS` | 5 | 缓冲多少秒自动转写 |
| `SECRET_KEY` | 需修改 | JWT 密钥（生产必须改） |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Token 有效期 |
| `REDIS_URL` | redis://localhost:6379/0 | Celery broker/backend |

## API 一览

所有接口前缀 `/api/v1`，除注册/登录/公开分享外均需 `Authorization: Bearer <token>`。

### Auth `/auth`
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | 注册 |
| POST | `/auth/login` | 登录（表单 `username`+`password`），返回 token |
| GET | `/auth/me` | 当前用户 |

### Meetings `/meetings`
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/meetings` | 创建会议 |
| GET | `/meetings` | 列表（`skip`/`limit`，仅本人） |
| GET | `/meetings/{id}` | 详情 |
| PATCH | `/meetings/{id}` | 更新 |
| DELETE | `/meetings/{id}` | 软删除（自动撤回录音授权 + 审计） |
| POST | `/meetings/{id}/restore` | 恢复 |

### Consents `/meetings/{id}/consents`
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/meetings/{id}/consents` | 授权事件（`consent_type=recording`，`action=grant/revoke`） |
| GET | `/meetings/{id}/consents` | 授权事件列表 |
| GET | `/meetings/{id}/consents/status` | 当前授权状态 |

### Summaries & Action Items `/meetings`
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/meetings/{id}/summary` | 同步生成纪要+待办 |
| POST | `/meetings/{id}/summary/async` | 异步入队，返回 `task_id`（202） |
| GET | `/meetings/{id}/summary` | 读取已存纪要+待办 |
| GET | `/meetings/{id}/action-items` | 待办列表 |
| PATCH | `/meetings/{id}/action-items/{item_id}` | 编辑/确认待办 |
| DELETE | `/meetings/{id}/action-items/{item_id}` | 删除待办 |

### Export `/meetings/{id}/export`
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/meetings/{id}/export?format=md\|json\|docx\|pdf` | 导出（附件下载） |

### Shares `/meetings/{id}/shares`（管理，需鉴权）
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/meetings/{id}/shares` | 创建分享（`allow_download`/`expires_in_days`） |
| GET | `/meetings/{id}/shares` | 分享列表 |
| DELETE | `/meetings/{id}/shares/{token}` | 撤回 |

### Shared `/shared`（公开，无需鉴权）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/shared/{token}` | 只读访问会议内容 |
| GET | `/shared/{token}/export?format=...` | 下载（需 `allow_download=true`，否则 403） |

### Audit `/audits`
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/audits` | 当前用户审计日志（可按 `meeting_id` 过滤） |

### Tasks `/tasks`
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/tasks/{task_id}` | 异步任务状态：PENDING/STARTED/SUCCESS/FAILURE |

### Stream（WebSocket）
| 路径 | 说明 |
|---|---|
| `WS /meetings/{id}/stream?token=<JWT>` | 实时转写推流 |

## WebSocket 实时转写协议

**前置条件**：连接前必须先授予录音权限（`POST /meetings/{id}/consents`，`consent_type=recording`，`action=grant`），否则被拒（1008）。

**音频格式**：16kHz、单声道、16-bit 小端 PCM，二进制帧发送。

**消息流**：
- 连接成功 → 服务端下发 `{"type":"ready","sample_rate":16000}`
- 客户端持续发送 PCM 二进制帧；满 `ASR_FLUSH_SECONDS` 自动转写
- 服务端返回字幕 `{"type":"subtitle","segments":[{"start","end","text","speaker"}]}`
- 客户端可发文本控制帧 `{"type":"flush"}` 强制转写、`{"type":"end"}` 结束
- 结束 → 服务端回 `{"type":"end","duration":<秒>}`
- 异常 → `{"type":"error","detail":"..."}` 后关闭（1008 鉴权/授权失败，1011 内部错误）

测试客户端：
```powershell
python scripts/ws_test.py <token> <meeting_id> <audio.pcm>
```

## 典型使用流程

```powershell
# 1. 注册 + 登录取 token
curl.exe -s -X POST http://127.0.0.1:8000/api/v1/auth/register -H "Content-Type: application/json" -d '{"email":"a@b.com","password":"secret123"}'
$token = (curl.exe -s -X POST http://127.0.0.1:8000/api/v1/auth/login -d "username=a@b.com&password=secret123" | ConvertFrom-Json).access_token

# 2. 创建会议
$resp = curl.exe -s -X POST http://127.0.0.1:8000/api/v1/meetings -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d '{"title":"demo"}'
$mid = [regex]::Match($resp, '"id":"([0-9a-fA-F\-]{36})"').Groups[1].Value

# 3. 授予录音权限（推流前必须）
curl.exe -s -X POST "http://127.0.0.1:8000/api/v1/meetings/$mid/consents" -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d '{"consent_type":"recording","action":"grant"}'

# 4. WebSocket 推流转写（见上）

# 5. 生成纪要（同步 / 异步）
curl.exe -s -X POST "http://127.0.0.1:8000/api/v1/meetings/$mid/summary" -H "Authorization: Bearer $token"
$task = curl.exe -s -X POST "http://127.0.0.1:8000/api/v1/meetings/$mid/summary/async" -H "Authorization: Bearer $token"

# 6. 导出 / 分享
curl.exe -s "http://127.0.0.1:8000/api/v1/meetings/$mid/export?format=pdf" -H "Authorization: Bearer $token" -o meeting.pdf
```

## 数据库迁移

Alembic 是建表**唯一入口**，新增模型后：
```powershell
uv run alembic revision --autogenerate -m "描述"
uv run alembic upgrade head
```
迁移链：meetings → transcripts → embedding → users → owner_id → consents → action_items → deleted_at+audit_logs → share_links。

## 常见问题

- **任务一直 PENDING**：Celery worker 没起。必须独立进程常驻：`celery -A app.workers.celery_app.celery worker --pool=solo`。
- **WebSocket 1011 keepalive timeout**：首次模型加载过慢。本地开发用 `WHISPER_MODEL=tiny`、`WHISPER_DEVICE=cpu`，并加 `--ws-ping-interval 60 --ws-ping-timeout 120`。
- **Ollama `device kernel image is invalid`**：NVIDIA 驱动过旧，升级驱动后重启 Ollama。
- **`.gitignore` 规则不生效**：文件被存成 CRLF 会导致 pattern 尾部多 `\r` 而失配，需转为 LF（无 BOM）。
- **Token 过期 / 换终端**：每次新开 PowerShell 都要重新登录取 `$token`、重设 `$mid`（默认 30 分钟过期）。

## License

私有项目，保留所有权利。