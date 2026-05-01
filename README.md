# 三文鱼项目管理系统 (Salmon PMS)

**版本**: V8.2  
**技术栈**: React 19 + FastAPI + SQLite(开发) / PostgreSQL(生产) + Redis + MinIO  
**状态**: 🚧 开发中 — 骨架搭建完成

---

## 快速启动

### 开发环境

```bash
# 后端
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload

# 前端
cd frontend
pnpm dev
```

访问地址：
- 前端: http://localhost:5173
- 后端: http://localhost:8000
- API 文档: http://localhost:8000/docs

### 生产环境 (Docker)

```bash
cd docker
docker compose up -d
```

---

## 项目结构

```
salmon-pms/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/       # API 路由（9个模块）
│   │   ├── core/         # 配置、数据库连接
│   │   ├── models/       # SQLAlchemy 模型（16个核心表）
│   │   ├── schemas/      # Pydantic 校验（待实现）
│   │   ├── services/     # 业务逻辑（待实现）
│   │   └── tasks/        # Celery 异步任务（待实现）
│   ├── migrations/       # Alembic 迁移
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── .env
├── frontend/             # React + Vite 前端
│   ├── src/
│   │   ├── components/ui/   # shadcn/ui 组件
│   │   ├── components/layout/  # 布局组件
│   │   ├── pages/        # 页面组件（9个页面）
│   │   ├── hooks/        # 自定义 Hooks（待实现）
│   │   ├── stores/       # Zustand 状态管理（待实现）
│   │   └── lib/          # API 封装、工具函数
│   ├── Dockerfile
│   └── nginx.conf
├── docker/               # Docker Compose
│   └── docker-compose.yml
├── docs/                 # 文档（待补充）
├── scripts/              # 辅助脚本
│   └── start-dev.sh      # 一键启动开发环境
└── README.md
```

---

## 核心模块（38个）

详见 `salmon-pms-design/MODULE_DESIGN_V8.2.md`

**已实现**：
- ✅ 数据库模型：16个核心表
- ✅ API 路由骨架：9个模块
- ✅ 前端页面骨架：9个页面
- ✅ 开发环境验证：前后端均可启动

**待实现**：
- Pydantic Schemas
- 业务逻辑 Services
- 前端状态管理
- 前端 API 集成
- 数据迁移脚本
- 报表生成逻辑
- 权限控制
- 测试用例

---

## 技术栈

| 层级 | 选型 | 版本 |
|------|------|------|
| 前端 | React 19 + TypeScript 5.4 + Vite 6 + TanStack Query + Zustand + shadcn/ui + Tailwind CSS | latest |
| 后端 | Python 3.12 + FastAPI 0.115 + Pydantic v2 + SQLAlchemy 2.0 + Alembic | latest |
| 数据库 | SQLite(开发) / PostgreSQL 16(生产) | - |
| 缓存/队列 | Redis 7 | latest |
| 异步任务 | Celery + Redis | latest |
| 文件存储 | MinIO / 本地磁盘 | latest |
| 部署 | Docker Compose | latest |
| 包管理 | uv (Python) / pnpm (Node) | latest |

---

## 设计文档

- `salmon-pms-design/MODULE_DESIGN_V8.2.md` — 模块设计方案
- `salmon-pms-design/FIXES_APPLIED_V8.2.md` — 隐患修复落实

---

_创建于 2026-04-29_  
_最后更新: 2026-04-29_
