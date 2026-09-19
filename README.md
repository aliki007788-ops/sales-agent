# Autonomous Sales Agent (ASA) v0.5.0

محصول واقعی و قابل اجرا — multi-tenant، چندکاناله.

## وضعیت

| لایه | وضعیت |
|------|--------|
| Unit/Integration tests | **37 PASS** |
| Live smoke test (uvicorn) | **PASS** |
| Alembic migration | ✅ `0001_initial` |
| Docker Compose | ✅ Postgres + API |
| Webhook end-to-end | ✅ |

## اجرا با Docker (توصیه‌شده)

```bash
cd sales-agent
cp .env.example .env
# SECRET_KEY را عوض کنید
docker compose up --build
```

سپس:
```bash
curl http://localhost:8000/health
python scripts/smoke_test.py
```

## اجرای محلی (بدون Docker)

```bash
export SECRET_KEY=$(openssl rand -hex 32)
export DATABASE_URL=sqlite+aiosqlite:///./asa.db
export PYTHONPATH=src
python -c "import asyncio; from sales_agent.db.base import Base; from sales_agent.db.session import get_engine; from sales_agent import models
async def i():
 e=get_engine();
 async with e.begin() as c: await c.run_sync(Base.metadata.create_all)
asyncio.run(i())"
uvicorn sales_agent.main:app --reload --port 8000
```

## کانال‌ها

`bale` · `telegram` · `eitaa` · `rubika` · `divar` · `torb` · `emalls`

## API اصلی

```
POST /api/v1/tenants
GET  /api/v1/tenants/me
POST/GET/PATCH /api/v1/leads
POST/GET /api/v1/events
POST /api/v1/agent/channels/{ch}/credentials
POST /api/v1/agent/events
POST /api/v1/agent/campaigns/start
POST /api/v1/webhooks/{tenant_id}/{channel}
```

## تست

```bash
PYTHONPATH=src pytest -q
```
