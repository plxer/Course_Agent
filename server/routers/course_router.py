"""课程智能体路由：课本伴读、视频伴读、课程对话流。"""

import os
import uuid
from pathlib import Path
from typing import Optional

import fitz
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src import config as conf
from src.agents import agent_manager
from src.services.chat_stream_service import stream_agent_chat
from src.storage.postgres.models_business import User
from server.utils.auth_middleware import get_db, get_required_user

course = APIRouter(prefix="/course", tags=["course"])

# 课本目录：环境变量 KNOWLEDGEBASE_DIR 或默认 knowledgebase（相对项目根）
_KNOWLEDGEBASE_DIR = os.environ.get("KNOWLEDGEBASE_DIR", "knowledgebase")
_BOOKS_DIR = Path(_KNOWLEDGEBASE_DIR).resolve() / "books"


def _books_dir() -> Path:
    return _BOOKS_DIR


def _resolve_book_path(book_id: str) -> Path | None:
    """根据 book_id（文件名不含扩展名）解析 PDF 路径，找不到返回 None。"""
    books = _books_dir()
    if not books.is_dir():
        return None
    # book_id 可能含 URL 解码后的字符，与文件名 stem 匹配
    for f in books.glob("*.pdf"):
        if f.stem == book_id:
            return f
    return None


def _list_pdf_books() -> list[dict]:
    """扫描 books 目录下的 PDF，返回 { id, name, size } 列表。"""
    books = _books_dir()
    if not books.is_dir():
        return []
    out = []
    for f in sorted(books.glob("*.pdf")):
        try:
            stat = f.stat()
            out.append({"id": f.stem, "name": f.name, "size": stat.st_size})
        except OSError:
            continue
    return out


# --- 课程对话流（课本伴读侧边栏、对话页共用）---


class CourseChatRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None
    meta: dict = {}


@course.post("/chat/stream")
async def course_chat_stream(
    request: CourseChatRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """课程对话流式接口：使用默认智能体，课本伴读侧边栏对话会调用此接口。"""
    agent_id = conf.default_agent_id or ""
    if not agent_id:
        agents = await agent_manager.get_agents_info()
        if agents:
            agent_id = agents[0].get("id", "")
    if not agent_id:
        raise HTTPException(
            status_code=503,
            detail="未配置默认智能体，请在系统设置中设置默认智能体",
        )

    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"thread_id": thread_id}
    meta = request.meta or {}
    if "request_id" not in meta or not meta.get("request_id"):
        meta["request_id"] = str(uuid.uuid4())
    meta.update({
        "query": request.query,
        "agent_id": agent_id,
        "thread_id": thread_id,
        "user_id": current_user.id,
        "has_image": False,
    })

    return StreamingResponse(
        stream_agent_chat(
            agent_id=agent_id,
            query=request.query,
            config=config,
            meta=meta,
            image_content=None,
            current_user=current_user,
            db=db,
        ),
        media_type="application/json",
    )


# --- 课本列表 ---


@course.get("/books")
def list_books():
    """课本列表：knowledgebase/books 下的 PDF。"""
    return {"books": _list_pdf_books()}


# --- 课本页数 ---


@course.get("/books/{book_id}/pages")
def get_book_pages(book_id: str):
    """返回指定课本的页数。"""
    path = _resolve_book_path(book_id)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="课本不存在")
    try:
        doc = fitz.open(path)
        try:
            return {"page_count": len(doc)}
        finally:
            doc.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"无法读取课本: {e!s}") from e


# --- 课本某一页图片 ---


@course.get("/books/{book_id}/page/{page_num}")
def get_book_page_image(book_id: str, page_num: int):
    """返回指定课本指定页的 PNG 图片。"""
    if page_num < 1:
        raise HTTPException(status_code=400, detail="页码从 1 开始")
    path = _resolve_book_path(book_id)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="课本不存在")
    try:
        doc = fitz.open(path)
        try:
            if page_num > len(doc):
                raise HTTPException(status_code=404, detail="页码超出范围")
            page = doc[page_num - 1]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            png_bytes = pix.tobytes(output="png")
            return Response(content=png_bytes, media_type="image/png")
        finally:
            doc.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"无法渲染页面: {e!s}") from e


# --- 选区 OCR ---


class OcrRequest(BaseModel):
    book_id: str
    page_num: int
    x: float
    y: float
    width: float
    height: float


@course.post("/books/ocr")
def ocr_text_selection(body: OcrRequest):
    """对课本某一页的选区做 OCR，返回识别文本。"""
    if body.page_num < 1:
        raise HTTPException(status_code=400, detail="页码从 1 开始")
    path = _resolve_book_path(body.book_id)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="课本不存在")
    try:
        doc = fitz.open(path)
        try:
            if body.page_num > len(doc):
                raise HTTPException(status_code=404, detail="页码超出范围")
            page = doc[body.page_num - 1]
            # 选区为相对原始页面的坐标
            rect = fitz.Rect(body.x, body.y, body.x + body.width, body.y + body.height)
            clip = rect & page.rect
            if clip.is_empty:
                return {"success": True, "text": ""}
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip, alpha=False)
            img_bytes = pix.tobytes(output="png")

            try:
                from src.plugins.rapid_ocr_processor import RapidOcrProcessor
                proc = RapidOcrProcessor()
                if proc.check_health().get("status") == "healthy":
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        tmp.write(img_bytes)
                        tmp.flush()
                        try:
                            text = proc.process_file(tmp.name) or ""
                            return {"success": True, "text": text.strip()}
                        finally:
                            Path(tmp.name).unlink(missing_ok=True)
            except Exception:
                pass
            # 兜底：从 PDF 提取该区域的文本块
            words = page.get_text("words", clip=clip)
            text = " ".join(w[4] for w in words).strip()
            return {"success": True, "text": text}
        finally:
            doc.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 失败: {e!s}") from e
