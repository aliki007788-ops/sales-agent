# ==========================================
# Simple CLI: sales-agent health | plans | version
# ==========================================
from __future__ import annotations

import argparse
import json
import sys

import httpx

from sales_agent import __version__
from sales_agent.billing.plans import PLANS


def cmd_version(_: argparse.Namespace) -> int:
    print(__version__)
    return 0


def cmd_plans(_: argparse.Namespace) -> int:
    for p in PLANS.values():
        print(
            f"{p.name:12} {p.monthly_price_irr:>12} IRR  "
            f"msg={p.max_messages_per_month} llm={p.max_llm_calls_per_month}"
        )
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    base = args.base.rstrip("/")
    r = httpx.get(f"{base}/health", timeout=10.0)
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    return 0 if r.status_code == 200 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sales-agent")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_v = sub.add_parser("version")
    p_v.set_defaults(func=cmd_version)

    p_p = sub.add_parser("plans")
    p_p.set_defaults(func=cmd_plans)

    p_h = sub.add_parser("health")
    p_h.add_argument("--base", default="http://127.0.0.1:8000")
    p_h.set_defaults(func=cmd_health)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
