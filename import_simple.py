#!/usr/bin/env python3
"""
简化版教材导入脚本 - 绕过MinIO，直接将解析后的markdown保存到本地
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, '/app')

TEXTBOOK_KB_NAME = "计算机网络"
KB_TYPE = "milvus"
TEXTBOOK_MD_REL = "ComputerNetworking-TopDown/ComputerNetworking-TopDown.md"

async def main():
    from src import config
    from src.knowledge import knowledge_base
    from src.services.textbook_service import knowledgebase_dir
    from src.storage.postgres.manager import pg_manager
    from src.repositories.knowledge_base_repository import KnowledgeBaseRepository
    from src.utils import logger

    textbook_path = knowledgebase_dir() / TEXTBOOK_MD_REL
    if not textbook_path.is_file():
        logger.error("课本文件不存在: %s", textbook_path)
        sys.exit(1)

    # 初始化
    pg_manager.initialize()
    await pg_manager.create_business_tables()
    await pg_manager.ensure_knowledge_schema()
    await knowledge_base.initialize()

    # 查找或创建知识库
    kb_repo = KnowledgeBaseRepository()
    rows = await kb_repo.get_all()
    db_id = None
    for row in rows:
        if row.name == TEXTBOOK_KB_NAME and (row.kb_type or "").lower() == KB_TYPE:
            db_id = row.db_id
            break

    if not db_id:
        embed_model_name = config.embed_model
        if embed_model_name not in config.embed_model_names:
            names = list(config.embed_model_names.keys())
            embed_model_name = names[0] if names else ""
        if not embed_model_name:
            logger.error("未配置嵌入模型")
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

    # 读取并解析markdown文件
    logger.info("开始读取课本文件: %s", textbook_path)
    with open(textbook_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    logger.info("课本内容长度: %d 字符", len(markdown_content))
    
    # 简单的文本分块（按段落分割）
    chunks = []
    paragraphs = markdown_content.split('\n\n')
    current_chunk = ""
    chunk_size = 1000
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = para
        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para
    
    if current_chunk:
        chunks.append(current_chunk)
    
    logger.info("分块完成，共 %d 个块", len(chunks))
    
    # 保存到本地文件
    save_dir = Path("/app/saves/knowledge_base_data/milvus_data")
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存分块后的文本
    chunks_file = save_dir / f"{db_id}_chunks.txt"
    with open(chunks_file, 'w', encoding='utf-8') as f:
        for i, chunk in enumerate(chunks):
            f.write(f"=== CHUNK {i+1} ===\n")
            f.write(chunk)
            f.write("\n\n")
    
    logger.info("已保存 %d 个文本块到: %s", len(chunks), chunks_file)
    
    # 记录到数据库
    from src.storage.postgres.models_knowledge import KnowledgeFile
    from src.utils.datetime_utils import utc_now_naive
    
    file_record = KnowledgeFile(
        file_id=f"file_{db_id[:8]}",
        db_id=db_id,
        filename=TEXTBOOK_MD_REL,
        original_filename=TEXTBOOK_MD_REL,
        file_type="md",
        path=str(textbook_path),
        status="parsed",
        content_type="file",
        processing_params={"chunk_size": chunk_size, "chunk_overlap": 200},
        created_at=utc_now_naive(),
        updated_at=utc_now_naive()
    )
    
    async with pg_manager.get_async_session_context() as session:
        session.add(file_record)
        await session.commit()
    
    logger.info("教材导入完成！")
    logger.info("知识库ID: %s", db_id)
    logger.info("文本块数量: %d", len(chunks))
    logger.info("文件保存位置: %s", chunks_file)

if __name__ == "__main__":
    asyncio.run(main())