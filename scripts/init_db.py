#!/usr/bin/env python3
import asyncio
import sys

async def main() -> int:
    from sales_agent.db.base import Base
    from sales_agent.db.session import get_engine
    from sales_agent import models  # noqa: F401

    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await eng.dispose()
    print("tables ready")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as exc:
        print(f"init_db failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
