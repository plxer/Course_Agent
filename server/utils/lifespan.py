import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import course_reading_paddle_ocr_enabled
from src.services.task_service import tasker
from src.services.mcp_service import init_mcp_servers
from src.storage.postgres.manager import pg_manager
from src.knowledge import knowledge_base
from src.utils import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan事件管理器"""
    # 初始化数据库连接
    try:
        pg_manager.initialize()
        await pg_manager.create_business_tables()
        await pg_manager.ensure_knowledge_schema()
    except Exception as e:
        logger.error(f"Failed to initialize database during startup: {e}")

    # 初始化 MCP 服务器配置
    try:
        await init_mcp_servers()
    except Exception as e:
        logger.error(f"Failed to initialize MCP servers during startup: {e}")

    # 初始化知识库管理器
    try:
        await knowledge_base.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize knowledge base manager: {e}")

    await tasker.start()

    async def _warm_course_reading_ocr() -> None:
        """后台预热 RapidOCR；Paddle 仅当 COURSE_READING_ENABLE_PADDLE_OCR=1 时预热。"""
        try:

            def _run() -> None:
                from src.plugins.rapid_ocr_processor import get_course_reading_rapid_ocr_processor

                r = get_course_reading_rapid_ocr_processor()
                rh = r.check_health()
                if rh.get("status") == "healthy":
                    logger.info("课本伴读 RapidOCR 预热就绪")
                else:
                    logger.warning("课本伴读 RapidOCR 预热未就绪: {}", rh.get("message"))

                if course_reading_paddle_ocr_enabled():
                    from src.plugins.paddle_ocr_processor import get_course_reading_ocr_processor

                    p = get_course_reading_ocr_processor()
                    ph = p.check_health()
                    if ph.get("status") == "healthy":
                        logger.info("课本伴读 PaddleOCR 预热就绪")
                    else:
                        logger.warning("课本伴读 PaddleOCR 预热未就绪: {}", ph.get("message"))

            await asyncio.to_thread(_run)
        except Exception as e:
            logger.warning("课本伴读 OCR 后台预热异常（非致命）: {}", e)

    asyncio.create_task(_warm_course_reading_ocr())
    yield
    await tasker.shutdown()
    await pg_manager.close()
