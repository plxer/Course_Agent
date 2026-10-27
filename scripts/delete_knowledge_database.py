#!/usr/bin/env python3
"""
命令行删除知识库（Milvus 会 drop 对应 collection，并清理 Postgres 记录与本地工作目录）。

示例（容器内，与 import_textbook_to_milvus 相同环境）：
  docker compose exec api uv run python scripts/delete_knowledge_database.py --name 计算机网络 -y

按 db_id：
  docker compose exec api uv run python scripts/delete_knowledge_database.py --db-id <uuid> -y

可选只删 Milvus 类型（避免名称与其它类型库重名时误删）：
  ... --name 计算机网络 --kb-type milvus -y
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def main() -> None:
    parser = argparse.ArgumentParser(description="删除知识库（含 Milvus collection）")
    parser.add_argument("--db-id", help="知识库 db_id（与接口/数据库一致）")
    parser.add_argument("--name", help="知识库显示名称")
    parser.add_argument(
        "--kb-type",
        default="",
        help="可选：仅匹配该 kb_type（如 milvus），避免与其它类型同名库冲突",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="不询问，直接删除",
    )
    args = parser.parse_args()

    if not args.db_id and not args.name:
        parser.error("请指定 --db-id 或 --name")

    from src.knowledge import knowledge_base
    from src.repositories.knowledge_base_repository import KnowledgeBaseRepository
    from src.storage.postgres.manager import pg_manager
    from src.agents import agent_manager
    from src.utils import logger

    pg_manager.initialize()
    await pg_manager.create_business_tables()
    await pg_manager.ensure_knowledge_schema()
    await knowledge_base.initialize()

    kb_repo = KnowledgeBaseRepository()
    rows = await kb_repo.get_all()

    db_id: str | None = args.db_id
    if not db_id:
        want_type = (args.kb_type or "").strip().lower()
        matches = [
            r
            for r in rows
            if r.name == args.name
            and (not want_type or (r.kb_type or "").lower() == want_type)
        ]
        if not matches:
            logger.error("未找到名称=%r 的知识库%s", args.name, f"（kb_type={want_type!r}）" if want_type else "")
            sys.exit(1)
        if len(matches) > 1:
            logger.error(
                "存在多个同名知识库，请使用 --db-id 或加上 --kb-type：%s",
                [(m.db_id, m.kb_type) for m in matches],
            )
            sys.exit(1)
        db_id = matches[0].db_id

    row = next((r for r in rows if r.db_id == db_id), None)
    if not row:
        logger.error("不存在 db_id=%s 的知识库", db_id)
        sys.exit(1)

    if not args.yes:
        print(f"将删除: name={row.name!r} db_id={db_id} kb_type={row.kb_type!r}")
        confirm = input("输入 yes 确认: ").strip().lower()
        if confirm != "yes":
            print("已取消")
            return

    logger.info("正在删除知识库 db_id=%s ...", db_id)
    await knowledge_base.delete_database(db_id)
    try:
        await agent_manager.reload_all()
    except Exception as e:
        logger.warning("reload_all 失败（可忽略，重启 api 后生效）: %s", e)

    logger.info("删除完成: %s", db_id)


if __name__ == "__main__":
    asyncio.run(main())
