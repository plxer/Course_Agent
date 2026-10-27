#!/usr/bin/env python3
import asyncio
import sys

sys.path.insert(0, "/app")

from src import knowledge_base as kb_manager


async def check():
    await kb_manager.initialize()
    # 获取所有知识库
    result = await kb_manager.get_databases_by_user({"role": None, "department_id": None})
    databases = result.get("databases") or []
    print(f"Found {len(databases)} knowledge bases:")
    for db in databases:
        print(f"  - {db.get('name')} ({db.get('kb_type')}) - db_id: {db.get('db_id')}")

    # 测试查询计算机网络知识库
    cn_db = next((d for d in databases if d.get("name") == "计算机网络"), None)
    if cn_db:
        print("\nTesting query on 计算机网络 knowledge base...")
        try:
            chunks = await kb_manager.aquery("TCP协议", cn_db["db_id"], final_top_k=3)
            print(f"Query returned {len(chunks)} chunks")
            for i, chunk in enumerate(chunks[:2]):
                content = chunk.get("content", "")[:100]
                print(f"  Chunk {i + 1}: {content}...")
        except Exception as e:
            print(f"Query failed: {e}")
    else:
        print("计算机网络 knowledge base not found!")


if __name__ == "__main__":
    asyncio.run(check())
