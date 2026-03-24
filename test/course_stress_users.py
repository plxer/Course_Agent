#!/usr/bin/env python3
"""
课程/压力测试专用：批量自助注册普通用户，并从数据库硬删除账号及其业务数据。

说明
----
- 注册走公开接口 POST /api/auth/register（系统需已完成初始化）。
- 清理脚本直连 PostgreSQL，与 API 使用同一 POSTGRES_URL；请在 api 容器内执行：
    docker compose exec api uv run python test/course_stress_users.py cleanup --execute

用户名规则：默认前缀 cst_ + 8 位 hex，总长度 ≤20，符合平台校验。

用法
----
  uv run python test/course_stress_users.py register -n 10 --output test/course_stress_accounts.json
  uv run python test/course_stress_users.py cleanup --from-file test/course_stress_accounts.json --execute
  uv run python test/course_stress_users.py cleanup --prefix cst_ --execute   # 按用户名前缀清理

多用户一条命令：test/run_course_stress_multi.py -a test/course_stress_accounts.json -- --llm-concurrency 2
（每账号独立子进程，见该脚本说明。）
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv
from sqlalchemy import delete, select

# 项目根目录
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
os.environ.setdefault("YUXI_SKIP_APP_INIT", "1")

load_dotenv(_ROOT / ".env", override=False)
load_dotenv(_ROOT / "test" / ".env.test", override=False)


def _base_url() -> str:
    return os.getenv("TEST_BASE_URL", "http://localhost:5050").rstrip("/")


def _default_password() -> str:
    return os.getenv("STRESS_TEST_PASSWORD", "StressTest1!")


def _make_username() -> str:
    """cst_ + 8 hex，长度 12。"""
    return f"cst_{uuid.uuid4().hex[:8]}"


async def cmd_register(args: argparse.Namespace) -> None:
    base = args.base_url or _base_url()
    password = args.password or _default_password()
    out_path = Path(args.output).resolve()

    created: list[dict] = []
    async with httpx.AsyncClient(base_url=base, timeout=60.0) as client:
        for i in range(args.count):
            username = _make_username()
            r = await client.post(
                "/api/auth/register",
                json={"username": username, "password": password},
            )
            if r.status_code != 200:
                print(f"[{i + 1}/{args.count}] 注册失败 {username}: {r.status_code} {r.text[:300]}")
                continue
            data = r.json()
            row = {
                "id": data.get("user_id"),
                "username": data.get("username"),
                "user_id_login": data.get("user_id_login"),
                "password": password,
            }
            created.append(row)
            print(f"[{i + 1}/{args.count}] 已注册: {row['username']} 登录ID={row['user_id_login']} 内部id={row['id']}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(created, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入 {len(created)} 条账号到 {out_path}")
    print("登录 OAuth2 表单字段：username 填「登录ID user_id_login」，password 填密码。")


async def _purge_users(session, user_ids: list[int]) -> None:
    from src.storage.postgres.models_business import (
        BookReadingPosition,
        Conversation,
        ExerciseAttempt,
        MessageFeedback,
        OperationLog,
        User,
        UserMallItem,
    )

    if not user_ids:
        return

    str_ids = [str(uid) for uid in user_ids]

    await session.execute(delete(MessageFeedback).where(MessageFeedback.user_id.in_(str_ids)))

    conv_result = await session.execute(select(Conversation).where(Conversation.user_id.in_(str_ids)))
    for conv in conv_result.scalars():
        await session.delete(conv)

    await session.execute(delete(ExerciseAttempt).where(ExerciseAttempt.user_id.in_(user_ids)))
    await session.execute(delete(BookReadingPosition).where(BookReadingPosition.user_id.in_(user_ids)))
    await session.execute(delete(UserMallItem).where(UserMallItem.user_id.in_(user_ids)))
    await session.execute(delete(OperationLog).where(OperationLog.user_id.in_(user_ids)))
    await session.execute(delete(User).where(User.id.in_(user_ids)))


async def cmd_cleanup(args: argparse.Namespace) -> None:
    from src.storage.postgres.manager import pg_manager
    from src.storage.postgres.models_business import User

    pg_manager.initialize()
    if not pg_manager._initialized:
        print("ERROR: PostgreSQL 未初始化，请检查 POSTGRES_URL（建议在 api 容器内执行本脚本）")
        raise SystemExit(1)

    user_ids: list[int] = []
    preview: list[tuple[int, str, str]] = []

    async with pg_manager.get_async_session_context() as session:
        if args.from_file:
            path = Path(args.from_file).resolve()
            if not path.is_file():
                print(f"ERROR: 文件不存在 {path}")
                raise SystemExit(1)
            rows = json.loads(path.read_text(encoding="utf-8"))
            raw_ids: list[int] = []
            for row in rows:
                uid = row.get("id")
                if uid is None:
                    continue
                raw_ids.append(int(uid))
            raw_ids = list(dict.fromkeys(raw_ids))
            res = await session.execute(select(User).where(User.id.in_(raw_ids)))
            for u in res.scalars():
                if u.role != "user":
                    print(f"跳过（非普通用户）: id={u.id} username={u.username!r} role={u.role}")
                    continue
                if u.is_deleted:
                    print(f"跳过（已软删除）: id={u.id} username={u.username!r}")
                    continue
                user_ids.append(u.id)
                preview.append((u.id, u.username, u.role))
        else:
            prefix = args.prefix
            res = await session.execute(
                select(User).where(
                    User.is_deleted == 0,
                    User.role == "user",
                    User.username.startswith(prefix),
                )
            )
            for u in res.scalars():
                user_ids.append(u.id)
                preview.append((u.id, u.username, u.role))

        if not user_ids:
            print("没有匹配的用户，无需清理。")
            return

        print("将处理以下用户（硬删除 + 关联数据）:")
        for uid, name, role in preview:
            print(f"  id={uid}  username={name!r}  role={role}")

        if not args.execute:
            print("\n未加 --execute，仅预览。确认后执行：")
            hint = f"--from-file {args.from_file!r}" if args.from_file else f"--prefix {args.prefix!r}"
            print(f"  uv run python test/course_stress_users.py cleanup {hint} --execute")
            return

        await _purge_users(session, user_ids)

    print(f"\n已硬删除 {len(user_ids)} 个用户及其对话/习题/阅读进度/商城记录/操作日志等关联数据。")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="课程压力测试账号：注册 / 硬删除清理")
    sub = p.add_subparsers(dest="command", required=True)

    pr = sub.add_parser("register", help="调用 /api/auth/register 批量注册普通用户")
    pr.add_argument("-n", "--count", type=int, default=5, help="注册数量")
    pr.add_argument("--password", default=None, help="统一密码，默认读环境变量 STRESS_TEST_PASSWORD")
    pr.add_argument("--base-url", default=None, help="API 根地址，默认 TEST_BASE_URL")
    pr.add_argument(
        "-o",
        "--output",
        default="test/course_stress_accounts.json",
        help="写出账号 JSON（含 id / username / user_id_login / password）",
    )
    pr.set_defaults(func=cmd_register)

    pc = sub.add_parser("cleanup", help="按文件或用户名前缀硬删除测试用户及数据")
    pc.add_argument(
        "--from-file",
        default=None,
        help="register 生成的 JSON；与 --prefix 二选一，优先使用文件中的 id",
    )
    pc.add_argument(
        "--prefix",
        default="cst_",
        help="无 --from-file 时：删除 username 以此前缀开头且 role=user 的账号（默认 cst_）",
    )
    pc.add_argument(
        "--execute",
        action="store_true",
        help="真正执行删除；省略则只打印预览",
    )
    pc.set_defaults(func=cmd_cleanup)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
