"""
客户端错误收集接口
前端 JS 错误和 API 500 错误自动上报落盘
"""
import json
import os
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["错误监控"])

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
ERROR_LOG = os.path.join(LOG_DIR, "client_errors.jsonl")


class ClientError(BaseModel):
    type: str
    message: str | None = None
    stack: str | None = None
    url: str | None = None
    status: int | None = None
    user_agent: str | None = None
    api_path: str | None = None
    timestamp: str


@router.post("/client-errors")
async def log_client_error(error: ClientError):
    """接收前端上报的错误"""
    record = {
        **error.model_dump(),
        "server_ts": datetime.utcnow().isoformat(),
    }
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True}


@router.get("/client-errors")
async def list_client_errors(limit: int = 50, since_minutes: int = 30):
    """Agent 用：查询最近的客户端错误"""
    if not os.path.exists(ERROR_LOG):
        return {"errors": [], "count": 0}

    cutoff = datetime.utcnow().timestamp() - since_minutes * 60
    errors = []
    try:
        with open(ERROR_LOG, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    ts = rec.get("server_ts") or rec.get("timestamp")
                    if ts:
                        from datetime import datetime as _dt
                        try:
                            t = _dt.fromisoformat(ts.replace("Z", "+00:00"))
                            if t.timestamp() < cutoff:
                                continue
                        except Exception:
                            pass
                    errors.append(rec)
                    if len(errors) >= limit:
                        break
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass

    # 返回时倒序（最新的在前）
    return {"errors": list(reversed(errors)), "count": len(errors)}
