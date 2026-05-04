#!/usr/bin/env python3
"""
课程智能体 API 压力测试（对话流、题目生成、视频伴读相关接口）。

并发能力说明（FastAPI 非 Java，但结论类似）：
- 视频列表、视频 Range 分片、字幕/总结 JSON：多为异步友好的 I/O，单进程下可支撑较高并发，
  瓶颈通常在磁盘带宽、反向代理、Uvicorn worker 数量。
- POST /api/course/exercises/generate、POST /api/course/chat/stream：每次请求会触发 LLM（及可能的
  检索），成本高、耗时长，整体吞吐由模型服务速率与连接池决定，不适合与静态资源同一量级并发。

运行示例（需服务已启动，默认读 test/.env.test 或环境变量）::

    uv run python test/course_stress_test.py --skip-llm --static-concurrency 80
    uv run python test/course_stress_test.py --llm-concurrency 3 --static-concurrency 20

Docker 内::

    docker compose exec api uv run python test/course_stress_test.py --skip-llm

压测前建议关闭 API 热重载（否则保存代码会重启 Worker，打断长流式请求并刷 CancelledError）::

    docker compose -f docker-compose.yml -f docker-compose.stress.yml up -d

登录环境变量（压 LLM 接口时）::

    TEST_USERNAME / TEST_PASSWORD（见 test/.env.test.example）
    或 YUXI_SUPER_ADMIN_NAME / YUXI_SUPER_ADMIN_PASSWORD（根目录 .env）

本脚本**不**实现「用户如何分配」：HTTP 无状态，身份由请求里的 Bearer token 决定，**识别用户是服务端职责**。
压测端只使用**一组**凭证登录一次，再并发发相同业务输入并统计指标。

多用户一条命令：::

    uv run python test/run_course_stress_multi.py -a test/course_stress_accounts.json -- --llm-concurrency 2

（每账号独立进程 + 独立 token，默认子进程带 --llm-only 避免 N 倍打静态接口。）
手动多进程：各进程 export 不同 TEST_USERNAME/TEST_PASSWORD。清理账号见 course_stress_users.py。
"""

from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import httpx
from dotenv import load_dotenv

load_dotenv(".env", override=False)
load_dotenv("test/.env.test", override=False)


def _base_url() -> str:
    return os.getenv("TEST_BASE_URL", "http://localhost:5050").rstrip("/")


def _auth_pair() -> tuple[str, str]:
    u = os.getenv("TEST_USERNAME") or os.getenv("YUXI_SUPER_ADMIN_NAME") or ""
    p = os.getenv("TEST_PASSWORD") or os.getenv("YUXI_SUPER_ADMIN_PASSWORD") or ""
    return u, p


@dataclass
class RequestRecord:
    name: str
    ok: bool
    status_code: int | None
    seconds: float
    error: str | None = None
    ttft_seconds: float | None = None


@dataclass
class ScenarioStats:
    name: str
    records: list[RequestRecord] = field(default_factory=list)

    def add(self, r: RequestRecord) -> None:
        self.records.append(r)

    def summary(self) -> str:
        n = len(self.records)
        oks = [r for r in self.records if r.ok]
        fails = [r for r in self.records if not r.ok]
        lat = [r.seconds for r in oks]
        ttft = [r.ttft_seconds for r in oks if r.ttft_seconds is not None]
        lines = [
            f"\n=== {self.name} ===",
            f"  请求数: {n}  成功: {len(oks)}  失败: {len(fails)}",
        ]
        if lat:
            lines.append(
                f"  成功耗时(s): min={min(lat):.3f}  max={max(lat):.3f}  "
                f"mean={statistics.mean(lat):.3f}  stdev={statistics.stdev(lat) if len(lat) > 1 else 0:.3f}"
            )
            lines.append(
                f"  p50={_percentile(lat, 50):.3f}  p95={_percentile(lat, 95):.3f}  p99={_percentile(lat, 99):.3f}"
            )
        if ttft:
            lines.append(
                f"  首 token 时间TTFT(s): min={min(ttft):.3f}  max={max(ttft):.3f}  "
                f"mean={statistics.mean(ttft):.3f}  p50={_percentile(ttft, 50):.3f}  "
                f"p95={_percentile(ttft, 95):.3f}  p99={_percentile(ttft, 99):.3f}"
            )
        if fails:
            err_sample = {}
            for r in fails[:5]:
                key = f"{r.status_code or '—'} {r.error or ''}"[:120]
                err_sample[key] = err_sample.get(key, 0) + 1
            lines.append(f"  失败样例: {err_sample}")
        return "\n".join(lines)


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    xs = sorted(sorted_vals)
    k = (len(xs) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return xs[f]
    return xs[f] + (xs[c] - xs[f]) * (k - f)


async def _login(client: httpx.AsyncClient, username: str, password: str) -> str:
    r = await client.post("/api/auth/token", data={"username": username, "password": password})
    r.raise_for_status()
    token = r.json().get("access_token")
    if not token:
        raise RuntimeError("登录响应中无 access_token")
    return token


async def _fetch_first_video_id(client: httpx.AsyncClient) -> str | None:
    r = await client.get("/api/course/videos")
    if r.status_code != 200:
        return None
    data = r.json()
    for ch in data.get("chapters") or []:
        for v in ch.get("videos") or []:
            vid = v.get("id")
            if vid:
                return str(vid)
    return None


async def run_static_list(client: httpx.AsyncClient, sem: asyncio.Semaphore, stats: ScenarioStats) -> None:
    async with sem:
        t0 = time.perf_counter()
        try:
            r = await client.get("/api/course/videos")
            dt = time.perf_counter() - t0
            ok = r.status_code == 200
            stats.add(RequestRecord("videos_list", ok, r.status_code, dt, None if ok else r.text[:200]))
        except Exception as e:
            dt = time.perf_counter() - t0
            stats.add(RequestRecord("videos_list", False, None, dt, str(e)))


async def run_video_range(
    client: httpx.AsyncClient, sem: asyncio.Semaphore, stats: ScenarioStats, video_id: str
) -> None:
    async with sem:
        t0 = time.perf_counter()
        try:
            r = await client.get(
                f"/api/course/videos/{video_id}",
                headers={"Range": "bytes=0-65535"},
            )
            dt = time.perf_counter() - t0
            ok = r.status_code in (200, 206)
            stats.add(RequestRecord("video_range", ok, r.status_code, dt, None if ok else r.text[:120]))
        except Exception as e:
            dt = time.perf_counter() - t0
            stats.add(RequestRecord("video_range", False, None, dt, str(e)))


async def run_video_summary(
    client: httpx.AsyncClient, sem: asyncio.Semaphore, stats: ScenarioStats, video_id: str
) -> None:
    async with sem:
        t0 = time.perf_counter()
        try:
            r = await client.get(f"/api/course/videos/{video_id}/summary")
            dt = time.perf_counter() - t0
            ok = r.status_code == 200
            err = None
            if not ok:
                err = "404 无总结文件" if r.status_code == 404 else r.text[:120]
            stats.add(RequestRecord("video_summary", ok, r.status_code, dt, err))
        except Exception as e:
            dt = time.perf_counter() - t0
            stats.add(RequestRecord("video_summary", False, None, dt, str(e)))


async def run_exercise_generate(
    client: httpx.AsyncClient, sem: asyncio.Semaphore, stats: ScenarioStats, headers: dict[str, str]
) -> None:
    body = {
        "question_type": "choice",
        "knowledge_point": "TCP 三次握手的基本步骤",
        "chapter": 1,
    }
    async with sem:
        t0 = time.perf_counter()
        try:
            r = await client.post("/api/course/exercises/generate", json=body, headers=headers)
            dt = time.perf_counter() - t0
            ok = r.status_code == 200
            stats.add(RequestRecord("exercise_generate", ok, r.status_code, dt, None if ok else r.text[:200]))
        except Exception as e:
            dt = time.perf_counter() - t0
            stats.add(RequestRecord("exercise_generate", False, None, dt, str(e)))


async def run_course_chat_stream_head(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    stats: ScenarioStats,
    headers: dict[str, str],
    max_bytes: int,
) -> None:
    body = {
        "query": "用一句话说明 TCP 和 UDP 的主要区别。",
        "knowledge_base": "computer_networking",
        "meta": {},
    }
    async with sem:
        t0 = time.perf_counter()
        try:
            async with client.stream(
                "POST",
                "/api/course/chat/stream",
                json=body,
                headers=headers,
            ) as r:
                status = r.status_code
                if status != 200:
                    text = await r.aread()
                    dt = time.perf_counter() - t0
                    stats.add(
                        RequestRecord(
                            "course_chat_stream",
                            False,
                            status,
                            dt,
                            text.decode(errors="replace")[:200],
                        )
                    )
                    return
                n = 0
                first_chunk_at: float | None = None
                async for chunk in r.aiter_bytes():
                    if first_chunk_at is None and chunk:
                        first_chunk_at = time.perf_counter()
                    n += len(chunk)
                    if n >= max_bytes:
                        break
                dt = time.perf_counter() - t0
                ttft_seconds = None if first_chunk_at is None else first_chunk_at - t0
                stats.add(RequestRecord("course_chat_stream", True, status, dt, None, ttft_seconds))
        except Exception as e:
            dt = time.perf_counter() - t0
            stats.add(RequestRecord("course_chat_stream", False, None, dt, str(e)))


async def run_pool(
    name: str,
    n: int,
    concurrency: int,
    fn: Callable[[asyncio.Semaphore, ScenarioStats], Awaitable[None]],
) -> ScenarioStats:
    stats = ScenarioStats(name=name)
    sem = asyncio.Semaphore(concurrency)

    async def one() -> None:
        await fn(sem, stats)

    await asyncio.gather(*(one() for _ in range(n)))
    return stats


async def amain() -> None:
    parser = argparse.ArgumentParser(description="课程 API 压力测试")
    parser.add_argument("--base-url", default=_base_url(), help="API 根地址，默认 TEST_BASE_URL")
    parser.add_argument("--static-concurrency", type=int, default=40, help="静态类请求同时发起数上限")
    parser.add_argument("--static-requests", type=int, default=200, help="静态类请求总次数")
    parser.add_argument("--llm-concurrency", type=int, default=5, help="LLM 类请求并发上限")
    parser.add_argument("--llm-requests", type=int, default=10, help="每类 LLM 请求总次数")
    parser.add_argument(
        "--chat-prefix-bytes",
        type=int,
        default=8192,
        help="课程对话流每个请求读取的字节数后断开（减轻压力）",
    )
    parser.add_argument("--skip-llm", action="store_true", help="跳过题目生成与课程对话流")
    parser.add_argument(
        "--llm-only",
        action="store_true",
        help="只压 LLM 相关接口，跳过视频等静态场景（多用户并行时由 run_course_stress_multi 默认加上）",
    )
    args = parser.parse_args()

    if args.llm_only and args.skip_llm:
        print("错误: --llm-only 与 --skip-llm 不能同时使用")
        raise SystemExit(2)

    username, password = _auth_pair()
    timeout = httpx.Timeout(300.0, connect=30.0)
    max_conn = (
        args.llm_concurrency + 20
        if args.llm_only
        else max(args.static_concurrency, args.llm_concurrency) + 20
    )
    limits = httpx.Limits(max_connections=max_conn)

    summaries: list[ScenarioStats] = []

    async with httpx.AsyncClient(base_url=args.base_url, timeout=timeout, limits=limits) as client:
        if not args.llm_only:
            video_id = await _fetch_first_video_id(client)
            if not video_id:
                print("警告: 未从 /api/course/videos 解析到任何 video_id，将跳过 video_range / video_summary。")

            # --- 静态：视频列表 ---
            async def videos_list_worker(sem: asyncio.Semaphore, st: ScenarioStats) -> None:
                await run_static_list(client, sem, st)

            summaries.append(
                await run_pool(
                    "GET /api/course/videos",
                    args.static_requests,
                    args.static_concurrency,
                    videos_list_worker,
                )
            )

            if video_id:
                # --- 静态：视频 Range 首 64KB ---
                async def video_range_worker(sem: asyncio.Semaphore, st: ScenarioStats) -> None:
                    await run_video_range(client, sem, st, video_id)

                summaries.append(
                    await run_pool(
                        f"GET /api/course/videos/{{id}} Range (video_id={video_id})",
                        args.static_requests,
                        args.static_concurrency,
                        video_range_worker,
                    )
                )

                # --- 静态：视频总结 JSON ---
                async def video_summary_worker(sem: asyncio.Semaphore, st: ScenarioStats) -> None:
                    await run_video_summary(client, sem, st, video_id)

                probe_sm = await client.get(f"/api/course/videos/{video_id}/summary")
                if probe_sm.status_code != 200:
                    print(
                        f"提示: /summary 对 video_id={video_id} 返回 {probe_sm.status_code}，跳过该压力场景。"
                    )
                else:
                    summaries.append(
                        await run_pool(
                            "GET /api/course/videos/{id}/summary",
                            args.static_requests,
                            args.static_concurrency,
                            video_summary_worker,
                        )
                    )

        if not args.skip_llm:
            if not username or not password:
                print("错误: 需要 TEST_USERNAME/TEST_PASSWORD（或 YUXI_SUPER_ADMIN_*）才能测 LLM 接口。")
                raise SystemExit(2)
            token = await _login(client, username, password)
            headers = {"Authorization": f"Bearer {token}"}

            async def ex_worker(sem: asyncio.Semaphore, st: ScenarioStats) -> None:
                await run_exercise_generate(client, sem, st, headers)

            summaries.append(
                await run_pool(
                    "POST /api/course/exercises/generate",
                    args.llm_requests,
                    args.llm_concurrency,
                    ex_worker,
                )
            )

            async def chat_worker(sem: asyncio.Semaphore, st: ScenarioStats) -> None:
                await run_course_chat_stream_head(client, sem, st, headers, args.chat_prefix_bytes)

            summaries.append(
                await run_pool(
                    "POST /api/course/chat/stream (read prefix then stop)",
                    args.llm_requests,
                    args.llm_concurrency,
                    chat_worker,
                )
            )

    print(f"Base URL: {args.base_url}")
    for s in summaries:
        print(s.summary())


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
