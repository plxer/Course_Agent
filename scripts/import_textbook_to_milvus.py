#!/usr/bin/env python3
"""
将《计算机网络：自顶向下方法》Markdown 课本切分并导入 Milvus 知识库，供课程对话检索使用。

使用方式（在项目根目录，且 Milvus 已启动）：
  docker compose exec api uv run python scripts/import_textbook_to_milvus.py

或本地（需已配置 POSTGRES_URL、MILVUS_URI、KNOWLEDGEBASE_DIR 等）：
  uv run python scripts/import_textbook_to_milvus.py
"""

import asyncio
import os
import sys
from pathlib import Path

# 确保项目根在 path 中
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 课程知识库显示名称（与 course_router.COURSE_KNOWLEDGE_BASES 中「计算机网络」一致，用于按名称解析 db_id）
TEXTBOOK_KB_NAME = "计算机网络"
KB_TYPE = "milvus"
TEXTBOOK_MD_REL = "ComputerNetworking-TopDown/ComputerNetworking-TopDown.md"


async def main():
    from src import config
    from src.knowledge import knowledge_base
    from src.storage.postgres.manager import pg_manager
    from src.repositories.knowledge_base_repository import KnowledgeBaseRepository
    from src.utils import logger

    # 解析课本路径（支持 KNOWLEDGEBASE_DIR 环境变量）
    kb_dir = os.environ.get("KNOWLEDGEBASE_DIR", "knowledgebase")
    textbook_path = Path(kb_dir).resolve() / TEXTBOOK_MD_REL
    if not textbook_path.is_file():
        logger.error("课本文件不存在: %s", textbook_path)
        sys.exit(1)

    # 初始化 DB 与知识库（与 lifespan 一致）
    pg_manager.initialize()
    await pg_manager.create_business_tables()
    await pg_manager.ensure_knowledge_schema()
    await knowledge_base.initialize()

    kb_repo = KnowledgeBaseRepository()
    rows = await kb_repo.get_all()
    db_id = None
    for row in rows:
        if row.name == TEXTBOOK_KB_NAME and (row.kb_type or "").lower() == KB_TYPE:
            db_id = row.db_id
            break

    if not db_id:
        # 创建 Milvus 知识库
        embed_model_name = config.embed_model
        if embed_model_name not in config.embed_model_names:
            names = list(config.embed_model_names.keys())
            embed_model_name = names[0] if names else ""
        if not embed_model_name:
            logger.error("未配置嵌入模型，请在 config 或环境中设置 embed_model")
            sys.exit(1)
        embed_info = config.embed_model_names[embed_model_name].model_dump()
        db_info = await knowledge_base.create_database(
            TEXTBOOK_KB_NAME,
            description="《计算机网络：自顶向下方法》课本，用于课程对话检索",
            kb_type=KB_TYPE,
            embed_info=embed_info,
        )
        db_id = db_info["db_id"]
        logger.info("已创建 Milvus 知识库: name=%s db_id=%s", TEXTBOOK_KB_NAME, db_id)
    else:
        logger.info("使用已有知识库: name=%s db_id=%s", TEXTBOOK_KB_NAME, db_id)

    # 使用绝对路径以便校验与解析
    path_str = str(textbook_path)

    # 检查是否已导入过该文件，避免重复
    kb_instance = knowledge_base._get_or_create_kb_instance(KB_TYPE)
    await kb_instance._load_metadata()
    path_resolved = Path(path_str).resolve()
    for finfo in kb_instance.files_meta.values():
        if finfo.get("database_id") != db_id:
            continue
        existing = finfo.get("path") or ""
        if not existing:
            continue
        try:
            if Path(existing).resolve() == path_resolved:
                logger.info("课本文件已存在于该知识库，跳过导入。")
                return
        except (OSError, RuntimeError):
            pass

    # 添加文件记录并解析、入库
    try:
        file_meta = await knowledge_base.add_file_record(
            db_id,
            path_str,
            params={
                "content_type": "file",
                "chunk_size": 1000,
                "chunk_overlap": 200,
                # 课本 MD 含 ![](_page_<印刷页码>_...) 插图路径，先按锚点分段再按长度切分
                "page_anchor_split": True,
            },
            operator_id=None,
        )
    except ValueError as e:
        logger.error("添加文件记录失败（路径可能未在允许目录内）: %s", e)
        sys.exit(1)

    file_id = file_meta["file_id"]
    logger.info("已添加文件记录 file_id=%s，开始解析…", file_id)

    await knowledge_base.parse_file(db_id, file_id, operator_id=None)
    logger.info("解析完成，开始向量入库…")
    await knowledge_base.index_file(db_id, file_id, operator_id=None)
    logger.info("课本已切分并导入 Milvus 知识库，课程对话将使用该知识库进行检索。")


if __name__ == "__main__":
    asyncio.run(main())
