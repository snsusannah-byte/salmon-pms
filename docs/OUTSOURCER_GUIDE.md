# 🐟 salmon-pms 仓库访问指引

> 外包开发：成品销售模块

---

## 1. 仓库信息

| 项目 | 详情 |
|------|------|
| **平台** | GitHub |
| **仓库地址** | https://github.com/snsusannah-byte/salmon-pms |
| **可见性** | 私有仓库 |
| **开发分支** | `feature/finished-product-sales-v2` |
| **PR 目标分支** | `main` |

---

## 2. 克隆代码

```bash
git clone https://github.com/snsusannah-byte/salmon-pms.git
cd salmon-pms
```

---

## 3. 环境准备

### 3.1 后端

```bash
cd backend

# 安装依赖（需要 uv）
uv sync
source .venv/bin/activate

# 复制环境变量模板
cp .env.example .env

# 启动服务
uvicorn app.main:app --reload
```

- **API 文档**: http://localhost:8000/docs
- **后端地址**: http://localhost:8000

### 3.2 前端

```bash
cd frontend

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

- **前端地址**: http://localhost:5173

---

## 4. 技术栈确认

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端 | FastAPI + SQLAlchemy 2.0 + Pydantic v2 | latest |
| 前端 | React 19 + TypeScript 5.4 + Vite 6 | latest |
| 数据库 | SQLite (开发) / PostgreSQL (生产) | - |
| UI 框架 | shadcn/ui + Tailwind CSS | latest |
| 状态管理 | TanStack Query + Zustand | latest |
| 包管理 | uv (Python) / pnpm (Node) | latest |

---

## 5. 开发规范

### 5.1 分支策略

```bash
# 从 main 创建开发分支
git checkout -b feature/finished-product-sales-v2

# 开发完成后提交 PR 到 main
```

### 5.2 代码检查

```bash
# 后端格式化
cd backend
ruff check .
ruff format .
mypy .

# 前端构建检查
cd frontend
pnpm build
```

### 5.3 数据库迁移

```bash
cd backend
alembic revision --autogenerate -m "your migration message"
alembic upgrade head
```

---

## 6. 开发依据

**唯一需求文档**:
```
docs/FINISHED_PRODUCT_SALES_RFP.md
```

**必须参考的现有代码**:
- `backend/app/api/v1/endpoints/sales.py` — 整鱼销售 API（功能标杆）
- `frontend/src/pages/SalesPage.tsx` — 整鱼销售页面（含详情弹窗）
- `frontend/src/pages/ProductsPage.tsx` — 产品管理页面
- `backend/app/models/__init__.py` — 数据模型定义

---

## 7. 协作方式

- **沟通**: GitHub Issues / PR Comments
- **代码提交**: 通过 PR 提交到 `main` 分支
- **Review**: 我方负责 PR Review 和合并

---

## 8. 注意事项

1. **不要修改现有核心表结构**（products, companies, users 等），只能扩展
2. **保持 API 向后兼容**，现有 `finished_product_sales` API 不能破坏
3. **不要使用新的技术栈**，严格遵循现有技术选型
4. **敏感信息不提交**，`.env` 文件已在 `.gitignore` 中，不会推送到仓库

---

**开始开发前请先阅读 `docs/FINISHED_PRODUCT_SALES_RFP.md`**
