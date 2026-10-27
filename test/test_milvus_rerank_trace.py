#!/usr/bin/env python3
"""
用例：按课程对话同款参数调用 Milvus aquery，打印中间环节并确认是否调用重排序模型。

与 server/routers/course_router._get_course_knowledge_context 中 aq_kwargs 构建方式一致。

用法（项目根目录）：
  uv run python test/test_milvus_rerank_trace.py
  MILVUS_TEST_DB_ID=xxx uv run python test/test_milvus_rerank_trace.py --query "TCP三次握手"

或容器内（与 compose 中 api 一致请加 --no-dev，避免拉取 ruff 等 dev 依赖）：
  docker compose exec api uv run --no-dev python test/test_milvus_rerank_trace.py

依赖：向量检索前会调用配置的 Embedding API（默认 SiliconFlow），重排会调用 Rerank API。
若日志出现 NameResolutionError / Other Embedding request failed，说明当前环境无法访问对应公网
（容器 DNS、代理、防火墙），返回 0 条且不会进入重排序；需先修复网络或改用可达的模型网关。
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# 项目根
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _chunk_key(chunk: dict) -> str:
    meta = chunk.get("metadata") or {}
    cid = meta.get("chunk_id")
    if cid is not None and str(cid).strip():
        return str(cid)
    return f"hash:{hash((chunk.get('content') or '')[:800]) & 0xFFFFFFFFFFFFFFFF}"


def _preview(text: str, max_chars: int) -> str:
    if not text:
        return ""
    one = text.replace("\n", " ").strip()
    if len(one) <= max_chars:
        return one
    return one[:max_chars] + "…"


async def _run(query: str, db_id: str | None, preview_chars: int, list_top: int) -> None:
    from src import config as conf
    from src.knowledge import knowledge_base
    from src.repositories.knowledge_base_repository import KnowledgeBaseRepository
    from src.storage.postgres.manager import pg_manager
    from src.utils import logger

    # 与 server/routers/course_router.py 中课程 Milvus 常量一致（勿从 course_router 导入以免拉起重依赖）
    COURSE_MILVUS_RECALL_TOP_K = 8
    COURSE_MILVUS_RERANK_POOL = 48

    pg_manager.initialize()
    await pg_manager.create_business_tables()
    await pg_manager.ensure_knowledge_schema()
    await knowledge_base.initialize()

    milvus_kb = knowledge_base._get_or_create_kb_instance("milvus")
    if not milvus_kb._metadata_loaded:
        await milvus_kb._load_metadata()

    resolved_db_id = (db_id or "").strip()
    if not resolved_db_id:
        kb_repo = KnowledgeBaseRepository()
        rows = await kb_repo.get_all()
        for row in rows:
            if row.name == "计算机网络" and (row.kb_type or "").lower() == "milvus":
                resolved_db_id = row.db_id
                break
        if not resolved_db_id:
            logger.error("未找到名称为「计算机网络」的 Milvus 知识库，请先在管理端创建或设置 MILVUS_TEST_DB_ID")
            sys.exit(2)

    if resolved_db_id not in milvus_kb.databases_meta:
        logger.error(
            "db_id=%s 未在 Milvus 元数据中找到（已从 PG 加载 %s 个 Milvus 库）。请核对 MILVUS_TEST_DB_ID 或知识库名称。",
            resolved_db_id,
            len(milvus_kb.databases_meta),
        )
        logger.error("当前已加载的 db_id: %s", list(milvus_kb.databases_meta.keys()))
        sys.exit(2)

    # 与 _get_course_knowledge_context 相同
    aq_kwargs: dict = {"final_top_k": COURSE_MILVUS_RECALL_TOP_K}
    reranker_id = (getattr(conf, "reranker", None) or "").strip()
    rerank_path = bool(getattr(conf, "enable_reranker", False) and reranker_id)
    if rerank_path:
        aq_kwargs["use_reranker"] = True
        aq_kwargs["reranker_model"] = reranker_id
        aq_kwargs["recall_top_k"] = COURSE_MILVUS_RERANK_POOL
        aq_kwargs["final_top_k"] = COURSE_MILVUS_RERANK_POOL

    print("--- 中间环节 1: 配置 ---")
    print(f"  enable_reranker: {getattr(conf, 'enable_reranker', None)}")
    print(f"  reranker: {reranker_id!r}")
    print(f"  课程检索将走重排序分支: {rerank_path}")

    print("--- 中间环节 2: 与课程对话一致的 aquery 参数 ---")
    for k, v in sorted(aq_kwargs.items()):
        print(f"  {k}: {v}")

    reranker_calls: list[str] = []

    import src.models.rerank as rerank_mod

    _orig_get_reranker = rerank_mod.get_reranker

    def _traced_get_reranker(model_id, **kwargs):
        reranker_calls.append(str(model_id))
        print("--- 中间环节 3: 重排序大模型入口被调用 ---")
        print(f"  get_reranker(model_id={model_id!r})")
        return _orig_get_reranker(model_id, **kwargs)

    rerank_mod.get_reranker = _traced_get_reranker

    try:
        chunks = await knowledge_base.aquery(query, resolved_db_id, **aq_kwargs)
    finally:
        rerank_mod.get_reranker = _orig_get_reranker

    print("--- 中间环节 4: 检索结果 ---")
    print(f"  db_id: {resolved_db_id}")
    print(f"  返回 chunk 数: {len(chunks)}")
    has_rerank_score = any(isinstance(c, dict) and "rerank_score" in c for c in chunks)
    print(f"  返回结果中含 rerank_score 字段: {has_rerank_score}")
    print(f"  get_reranker 调用次数（应等于重排序分支是否执行）: {len(reranker_calls)}")

    if len(chunks) == 0:
        print("--- 注意（0 条时必读） ---")
        print("  若上方日志有 Milvus query error / Other Embedding request failed / NameResolutionError：")
        print("  表示在「向量 embedding」阶段已失败，未执行 Milvus 检索，因此不会调用重排序。")
        print("  常见原因：api 容器无外网、DNS 无法解析（如 api.siliconflow.cn）、或 API Key 未配置。")
        print("  这与「库中无相关片段」不同；后者通常无 embedding 报错且仍可能进入重排。")

    n_show = min(list_top, len(chunks)) if chunks else 0

    if chunks and rerank_path and has_rerank_score:
        by_vector = sorted(
            [c for c in chunks if isinstance(c, dict)],
            key=lambda c: float(c.get("score") or 0.0),
            reverse=True,
        )
        by_rerank = [c for c in chunks if isinstance(c, dict)]

        print("--- 排序前（按向量相似度 score 降序；与同批候选集合相同）---")
        for i in range(min(n_show, len(by_vector))):
            c = by_vector[i]
            meta = c.get("metadata") or {}
            page = meta.get("book_page", "?")
            ck = _chunk_key(c)
            sc = c.get("score")
            print(f"  #{i + 1:2d}  page={page!s}  chunk_id={ck!s}  score={sc}")
            print(f"      {_preview(c.get('content') or '', preview_chars)}")

        print("--- 排序后（接口返回顺序，按 rerank_score 重排）---")
        for i in range(min(n_show, len(by_rerank))):
            c = by_rerank[i]
            meta = c.get("metadata") or {}
            page = meta.get("book_page", "?")
            ck = _chunk_key(c)
            sc = c.get("score")
            rs = c.get("rerank_score")
            print(f"  #{i + 1:2d}  page={page!s}  chunk_id={ck!s}  vector_score={sc}  rerank_score={rs}")
            print(f"      {_preview(c.get('content') or '', preview_chars)}")

        vec_rank = {_chunk_key(c): idx + 1 for idx, c in enumerate(by_vector)}
        print("--- 位次变化（数字越小名次越靠前；Δ = 向量名次 − 重排名次，为正表示重排后更靠前）---")
        for i in range(min(n_show, len(by_rerank))):
            c = by_rerank[i]
            k = _chunk_key(c)
            vr = vec_rank.get(k)
            rr = i + 1
            if isinstance(vr, int):
                delta = vr - rr
                print(f"  重排第{rr:2d}名  chunk_id={k!s}  向量第{vr:2d}名  Δ={delta:+d}")
            else:
                print(f"  重排第{rr:2d}名  chunk_id={k!s}  向量名次未知")

    elif chunks:
        for i, c in enumerate(chunks[: min(3, len(chunks))]):
            if not isinstance(c, dict):
                continue
            meta = c.get("metadata") or {}
            page = meta.get("book_page", "?")
            score = c.get("score")
            rs = c.get("rerank_score", "—")
            print(f"  [{i}] page={page} vector_score={score} rerank_score={rs}")
            print(f"      {_preview(c.get('content') or '', min(120, preview_chars))}")

    if rerank_path and not reranker_calls:
        print("--- 说明 ---")
        print("  配置要求重排序，但 get_reranker 未被调用：可能是向量召回为空；或 embedding/检索已失败（见上方 ERROR）。")
    elif rerank_path and reranker_calls:
        print("--- 结论 ---")
        print("  已调用重排序模型（get_reranker → HTTP 重排 API）。")
    else:
        print("--- 结论 ---")
        print("  当前配置未启用重排序（enable_reranker 或 reranker 为空），仅向量检索。")


def main() -> None:
    parser = argparse.ArgumentParser(description="Milvus 课程同款检索 + 重排序链路追踪")
    parser.add_argument("--query", default="TCP 三次握手的过程是什么", help="测试查询句")
    parser.add_argument("--db-id", default=os.environ.get("MILVUS_TEST_DB_ID", ""), help="Milvus 知识库 db_id，默认同名库自动解析")
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=320,
        help="每条 chunk 正文预览长度（排序前后列表）",
    )
    parser.add_argument(
        "--list-top",
        type=int,
        default=48,
        help="排序前/后列表与位次表各打印前多少条（默认与课程 rerank 池一致 48）",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.query, args.db_id or None, args.preview_chars, args.list_top))


if __name__ == "__main__":
    main()
