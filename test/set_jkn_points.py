"""
将超级管理员 jkn 的积分设置为 10。
用法（在项目根目录）：docker compose exec api uv run python test/set_jkn_points.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("YUXI_SKIP_APP_INIT", "1")

from sqlalchemy import select

from src.storage.postgres.manager import pg_manager
from src.storage.postgres.models_business import User


async def main():
    pg_manager.initialize()
    if not pg_manager._initialized:
        print("ERROR: PostgreSQL not initialized (check POSTGRES_URL)")
        sys.exit(1)

    async with pg_manager.get_async_session_context() as session:
        result = await session.execute(select(User).where(User.username == "jkn"))
        user = result.scalar_one_or_none()
        if not user:
            print("ERROR: 未找到用户 jkn")
            sys.exit(1)
        old_points = user.points
        user.points = 10
        await session.commit()
        print(f"已将用户 jkn 的积分从 {old_points} 设置为 10")


if __name__ == "__main__":
    asyncio.run(main())
