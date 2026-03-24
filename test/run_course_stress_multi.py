#!/usr/bin/env python3
"""
多用户并发压测编排：为账号 JSON 中每个用户启动**独立子进程**跑 course_stress_test.py，
各进程自行登录，服务端按 token 区分用户；本脚本不做「用户分配」，只负责起进程与汇总退出码。

默认子进程带 --llm-only，避免 N 个用户时把视频静态接口打 N 倍。需要每用户全量压测时用 --full。

一条命令示例（项目根目录）::

    uv run python test/run_course_stress_multi.py -a test/course_stress_accounts.json \\
        -- --llm-concurrency 2 --llm-requests 6

Docker::

    docker compose exec api uv run python test/run_course_stress_multi.py \\
        -a test/course_stress_accounts.json -- --llm-concurrency 2

前置：course_stress_users.py register 生成 JSON；TEST_BASE_URL 与 .env / test/.env.test 仍对子进程生效。

若 API 报 QueuePool 连接超时：流式对话会长时间占满 DB 连接，请调大 .env 中 POSTGRES_POOL_SIZE /
POSTGRES_MAX_OVERFLOW（见 docs/latest/advanced/configuration.md），或降低每进程的 --llm-concurrency。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# 项目根目录（子进程 cwd）
_ROOT = Path(__file__).resolve().parent.parent
_STRESS = _ROOT / "test" / "course_stress_test.py"


def _split_argv(argv: list[str]) -> tuple[list[str], list[str]]:
    if "--" in argv:
        i = argv.index("--")
        return argv[:i], argv[i + 1 :]
    return argv, []


def _load_accounts(path: Path) -> list[tuple[str, str, str]]:
    """(user_id_login, password, label 用于日志)"""
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("账号文件须为 JSON 数组")
    out: list[tuple[str, str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        login = (row.get("user_id_login") or row.get("username") or "").strip()
        password = (row.get("password") or "").strip()
        name = (row.get("username") or login or "?").strip()
        if login and password:
            out.append((login, password, name))
    return out


async def _run_child(
    login: str,
    password: str,
    label: str,
    child_argv: list[str],
    llm_only: bool,
    base_url: str | None,
) -> tuple[int, str]:
    env = os.environ.copy()
    env["TEST_USERNAME"] = login
    env["TEST_PASSWORD"] = password
    if base_url:
        env["TEST_BASE_URL"] = base_url

    cmd: list[str] = [sys.executable, str(_STRESS)]
    if llm_only:
        cmd.append("--llm-only")
    cmd.extend(child_argv)

    print(f"[编排] 启动 {label!r} (login_id={login!r})", flush=True)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(_ROOT),
        env=env,
    )
    code = await proc.wait()
    status = "ok" if code == 0 else f"exit {code}"
    print(f"[编排] 结束 {label!r} -> {status}", flush=True)
    return code, label


async def amain() -> None:
    own_argv, child_argv = _split_argv(sys.argv[1:])
    parser = argparse.ArgumentParser(
        description="多用户 course_stress_test：每账号一进程",
        add_help=True,
    )
    parser.add_argument(
        "-a",
        "--accounts-file",
        type=Path,
        default=Path("test/course_stress_accounts.json"),
        help="course_stress_users.py 生成的 JSON",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="子进程不加 --llm-only（每用户都会跑视频等静态压测，负载为单用户×N）",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="覆盖子进程环境变量 TEST_BASE_URL（不设则继承当前环境）",
    )
    args = parser.parse_args(own_argv)

    path = args.accounts_file
    if not path.is_file():
        print(f"错误: 账号文件不存在: {path.resolve()}")
        raise SystemExit(2)
    try:
        accounts = _load_accounts(path)
    except (json.JSONDecodeError, OSError, ValueError) as e:
        print(f"错误: 读取账号失败: {e}")
        raise SystemExit(2) from e
    if not accounts:
        print("错误: 账号文件中没有有效的 user_id_login + password")
        raise SystemExit(2)

    llm_only = not args.full
    tasks = [
        _run_child(login, pw, label, child_argv, llm_only, args.base_url)
        for login, pw, label in accounts
    ]
    results = await asyncio.gather(*tasks)
    bad = [code for code, _ in results if code != 0]
    print(f"\n[编排] 共 {len(results)} 个进程，失败 {len(bad)} 个")
    raise SystemExit(0 if not bad else 1)


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
