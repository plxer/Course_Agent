"""课程智能体路由：课本伴读、视频伴读、课程对话流。"""

import os
import re
import json
import uuid
import random
from pathlib import Path

import fitz
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src import config as conf
from src.agents import agent_manager
from src import knowledge_base as kb_manager
from sqlalchemy import func, select, update

from src.agents.common import load_chat_model
from src.services.chat_stream_service import stream_agent_chat
from src.services.exercise_service import grade_answer, generate_question
from src.services.textbook_service import get_textbook_chapters
from src.storage.postgres.models_business import (
    BookReadingPosition,
    ExerciseAttempt,
    MallItem,
    User,
    UserMallItem,
)
from src.utils import logger
from src.utils.datetime_utils import format_utc_datetime, utc_now_naive
from server.utils.auth_middleware import get_db, get_required_user

course = APIRouter(prefix="/course", tags=["course"])

# 课本目录：环境变量 KNOWLEDGEBASE_DIR 或默认 knowledgebase（相对项目根）
_KNOWLEDGEBASE_DIR = os.environ.get("KNOWLEDGEBASE_DIR", "knowledgebase")
_BOOKS_DIR = Path(_KNOWLEDGEBASE_DIR).resolve() / "books"
_VIDEOS_DIR = Path(_KNOWLEDGEBASE_DIR).resolve() / "videos"


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
    # 按文件名排序后的前两个视为“课本”（第 1 本指定课本，第 2 本拓展阅读），其余为“讲义”
    # 注意：分类规则依赖排序结果，不在这里根据文件内容识别。
    out: list[dict] = []
    sorted_pdfs = sorted(books.glob("*.pdf"))
    for idx, f in enumerate(sorted_pdfs):
        try:
            stat = f.stat()
            if idx == 0:
                book_type = "course_textbook"
                book_label = "指定课本"
            elif idx == 1:
                book_type = "supplement"
                book_label = "拓展阅读"
            else:
                book_type = "handout"
                book_label = "讲义"

            out.append(
                {
                    "id": f.stem,
                    "name": f.name,
                    "size": stat.st_size,
                    "book_type": book_type,
                    "book_label": book_label,
                    "sort_order": idx,
                }
            )
        except OSError:
            continue
    return out


# --- 视频列表与播放（knowledgebase/videos，文件名含 Chapter数字 按章节归类）---


def _list_videos() -> list[dict]:
    """扫描 videos 目录（含子目录）下的 .mp4，按文件名中的 Chapter 数字分组，返回 chapters 列表。"""
    root = _VIDEOS_DIR
    if not root.is_dir():
        return []
    chapter_re = re.compile(r"Chapter\s*(\d+)", re.IGNORECASE)
    by_chapter: dict[int, list[dict]] = {}
    for path in root.rglob("*.mp4"):
        try:
            stat = path.stat()
            stem = path.stem
            name = path.name
            m = chapter_re.search(stem)
            ch = int(m.group(1)) if m else 0
            if ch not in by_chapter:
                by_chapter[ch] = []
            by_chapter[ch].append({"id": stem, "name": name, "size": stat.st_size})
        except (OSError, ValueError):
            continue
    for vlist in by_chapter.values():
        vlist.sort(key=lambda x: x["name"])
    chapters = [{"chapter": ch, "videos": vlist} for ch, vlist in sorted(by_chapter.items())]
    return chapters


def _resolve_video_path(video_id: str) -> Path | None:
    """根据 video_id（文件名不含扩展名）解析视频路径。"""
    root = _VIDEOS_DIR
    if not root.is_dir():
        return None
    for path in root.rglob("*.mp4"):
        if path.stem == video_id:
            return path
    return None


@course.get("/videos")
def list_videos():
    """视频列表（按章节）：knowledgebase/videos 下含 Chapter数字 的 .mp4 按章节归类。"""
    return {"chapters": _list_videos()}


@course.get("/videos/{video_id}")
def get_video(video_id: str):
    """视频文件流，支持 Range 便于拖动进度。"""
    path = _resolve_video_path(video_id)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="视频不存在")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@course.get("/videos/{video_id}/caption")
def get_video_caption(video_id: str):
    """返回视频字幕 JSON（knowledgebase/videos/caption/{video_id}.json），含 sentence_timestamps。"""
    caption_path = _VIDEOS_DIR / "caption" / f"{video_id}.json"
    if not caption_path.is_file():
        raise HTTPException(status_code=404, detail="该视频暂无字幕")
    try:
        with open(caption_path, encoding="utf-8") as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"读取字幕失败: {e!s}") from e


@course.get("/videos/{video_id}/summary")
def get_video_summary(video_id: str):
    """返回视频分段总结 JSON（knowledgebase/videos/summary/{video_id}.json），用于「总结视频」展示与跳转。"""
    summary_path = _VIDEOS_DIR / "summary" / f"{video_id}.json"
    if not summary_path.is_file():
        raise HTTPException(status_code=404, detail="该视频暂无总结")
    try:
        with open(summary_path, encoding="utf-8") as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"读取总结失败: {e!s}") from e


# --- 课程对话流（课本伴读侧边栏、对话页共用）---


# 课程知识库列表：用户可在对话页选择，选中后对话会先检索对应课本再作答
# pdf_book_id：对应课本伴读中的 PDF（knowledgebase/books 下文件名不含扩展名），用于页码跳转
COURSE_KNOWLEDGE_BASES = [
    {"id": "computer_networking", "name": "计算机网络", "pdf_book_id": "ComputerNetworking-TopDown-v8-2021"},
]


class CourseChatRequest(BaseModel):
    query: str
    thread_id: str | None = None
    meta: dict = {}
    enable_web_search: bool | None = None  # 本次对话是否启用网络搜索，不传则用智能体/部门配置
    knowledge_base: str | None = None  # 课程知识库 id，如 "computer_networking" 表示先检索《计算机网络》课本再作答


class ConversationTitleRequest(BaseModel):
    """根据首轮一问一答生成对话标题"""

    first_question: str
    first_answer: str


@course.post("/chat/title")
async def generate_conversation_title(
    body: ConversationTitleRequest,
    current_user: User = Depends(get_required_user),
):
    """根据用户第一个问题和智能体第一个回答，用模型生成一句简短的对话标题。"""
    from langchain_core.messages import HumanMessage, SystemMessage

    prompt = """根据下面用户的第一条问题和助手的第一次回复，生成一句简短的对话标题（不超过20字，不要引号、不要markdown、不要“标题：”等前缀）。只输出标题内容。"""
    user_content = f"用户问题：{body.first_question[:500]}\n助手回复：{body.first_answer[:500]}"
    model = load_chat_model(conf.fast_model)
    try:
        msg_list = [
            SystemMessage(content=prompt),
            HumanMessage(content=user_content),
        ]
        resp = await model.ainvoke(msg_list)
        title = (resp.content if hasattr(resp, "content") else str(resp)).strip()
        # 去掉可能的引号、前缀
        for prefix in ("标题：", "标题:", "标题 "):
            if title.lower().startswith(prefix.lower()):
                title = title[len(prefix) :].strip()
        if len(title) > 24:
            title = title[:21] + "…"
        if not title:
            title = body.first_question[:20] + "…" if len(body.first_question) > 20 else body.first_question
        return {"title": title}
    except Exception as e:
        logger.warning("generate_conversation_title failed: %s", e)
        fallback = body.first_question.strip()
        return {"title": fallback[:20] + "…" if len(fallback) > 20 else fallback}


@course.get("/knowledge-bases")
def list_course_knowledge_bases():
    """课程对话可选的知识库列表，选中后对话会先检索对应课本再作答。"""
    return {"knowledge_bases": COURSE_KNOWLEDGE_BASES}


async def _get_course_knowledge_context(query: str, kb_id: str, current_user) -> str:
    """
    根据课程知识库 id 从 Milvus 检索上下文。无回退：找不到对应库或调用失败即报错。
    """
    course_entry = next((c for c in COURSE_KNOWLEDGE_BASES if c.get("id") == kb_id), None)
    display_name = course_entry.get("name", "") if course_entry else ""
    if not display_name:
        raise HTTPException(
            status_code=400,
            detail=f"未知的课程知识库 id: {kb_id!r}，请选择有效的课程知识库",
        )

    user_info = {"role": getattr(current_user, "role", None), "department_id": getattr(current_user, "department_id", None)}
    result = await kb_manager.get_databases_by_user(user_info)
    databases = result.get("databases") or []
    milvus_db = next(
        (d for d in databases if (d.get("name") == display_name and (d.get("kb_type") or "").lower() == "milvus")),
        None,
    )
    if not milvus_db or not milvus_db.get("db_id"):
        raise HTTPException(
            status_code=503,
            detail=f"课程知识库「{display_name}」对应的 Milvus 知识库未找到或不可用，请先在知识库管理中创建并导入课本（名称须为「{display_name}」、类型为 Milvus）",
        )

    try:
        chunks = await kb_manager.aquery(
            query,
            milvus_db["db_id"],
            final_top_k=8,
        )
    except Exception as e:
        logger.exception("Milvus 课程知识库检索失败: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"课程知识库检索失败（Milvus 调用异常）: {e!s}",
        ) from e

    if not chunks:
        return ""
    parts = []
    total = 0
    max_chars = 8000
    for item in chunks:
        content = (item.get("content") or "").strip()
        if not content:
            continue
        source = (item.get("metadata") or {}).get("source", "")
        block = f"【{source}】\n{content}\n" if source else f"{content}\n"
        if total + len(block) > max_chars:
            block = block[: max_chars - total]
        parts.append(block)
        total += len(block)
        if total >= max_chars:
            break
    return "\n".join(parts).strip() if parts else ""


async def _is_query_related_to_computer_networking(query: str) -> bool:
    """
    判断用户问题是否与《计算机网络》课程相关。不相关则返回 False，便于尽早拒绝以节省 token。
    调用异常或超时时视为相关，避免误拦。
    """
    query = (query or "").strip()[:500]
    if not query:
        return False
    from langchain_core.messages import HumanMessage, SystemMessage

    prompt = (
        "你是一个判断题助手。仅根据用户的问题判断：该问题是否与《计算机网络》课程内容相关？\n"
        "相关包括：网络协议、TCP/IP、HTTP、DNS、路由、交换机、网络安全、拥塞控制、Socket 等课本概念与习题。\n"
        "不相关包括：与网络无关的数学、编程、其他课程、生活闲聊等。\n"
        "只回答一个词：YES 或 NO。"
    )
    try:
        model = load_chat_model(conf.fast_model)
        msg_list = [
            SystemMessage(content=prompt),
            HumanMessage(content=query),
        ]
        resp = await model.ainvoke(msg_list)
        text = (resp.content if hasattr(resp, "content") else str(resp)).strip().upper()
        # 仅当明确回答 NO 时判为不相关
        if text.startswith("NO") or text == "NO":
            return False
        return True
    except Exception as e:
        logger.warning("课程问题相关性检测失败，视为相关: %s", e)
        return True


@course.post("/chat/stream")
async def course_chat_stream(
    request: CourseChatRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """课程对话流式接口：使用默认智能体，课本伴读侧边栏对话会调用此接口。"""
    # 本平台课程对话必须选择课程知识库（当前仅支持「计算机网络」），不可选择「无」
    kb_id = (request.knowledge_base or "").strip()
    valid_ids = [c.get("id") for c in COURSE_KNOWLEDGE_BASES if c.get("id")]
    if not kb_id or kb_id not in valid_ids:
        raise HTTPException(
            status_code=400,
            detail="本平台课程对话必须选择「计算机网络」知识库，不可选择「无」。请在上方选择「计算机网络」后再提问。",
        )

    # 先检测问题是否与计算机网络相关，完全不相关则立即停止并提示，减少 token 浪费
    if not await _is_query_related_to_computer_networking(request.query):
        raise HTTPException(
            status_code=400,
            detail="您的问题与《计算机网络》课程内容无关。为节省资源，请仅在此处询问与计算机网络相关的问题（如协议、TCP/IP、HTTP、DNS、路由、网络安全等）。",
        )

    # 课程对话优先使用环境变量 DEFAULT_AGENT_ID，否则 config，否则固定 ChatbotAgent（不依赖 agents 顺序）
    agent_id = (os.getenv("DEFAULT_AGENT_ID") or "").strip() or conf.default_agent_id or "ChatbotAgent"
    agents = await agent_manager.get_agents_info()
    agent_ids = [a.get("id", "") for a in agents] if agents else []
    if agent_id not in agent_ids and agent_ids:
        agent_id = agent_ids[0]
    if not agent_id:
        raise HTTPException(
            status_code=503,
            detail="未配置默认智能体，请在系统设置中设置默认智能体",
        )

    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"thread_id": thread_id}
    if request.enable_web_search is not None:
        config["enable_web_search"] = request.enable_web_search
    # 已校验 kb_id 必选，检索课本并注入
    context = await _get_course_knowledge_context(
        request.query, kb_id, current_user
    )
    if context:
        config["course_knowledge_context"] = context
    meta = request.meta or {}
    if "request_id" not in meta or not meta.get("request_id"):
        meta["request_id"] = str(uuid.uuid4())
    meta.update(
        {
            "query": request.query,
            "agent_id": agent_id,
            "thread_id": thread_id,
            "user_id": current_user.id,
            "has_image": False,
        }
    )
    # 前端可传 meta.source（如 "reading"），写入对话 metadata，问答页列表会排除 source=reading

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
    """对课本某一页的选区做 OCR，返回识别文本。
    前端传入的 (x,y,width,height) 为「页面图片」像素坐标，与 GET /books/{id}/page/{num} 返回的图片尺寸一致（Matrix 2x），需转换为 PDF 坐标后裁剪。
    """
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
            # 前端传的是页面图片像素坐标（与 get_pixmap(matrix=2,2) 的尺寸一致），转换为 PDF 坐标
            scale = 2.0  # 与下方 get_pixmap(Matrix(2,2)) 一致
            x_pdf = body.x / scale
            y_pdf = body.y / scale
            w_pdf = body.width / scale
            h_pdf = body.height / scale
            rect = fitz.Rect(x_pdf, y_pdf, x_pdf + w_pdf, y_pdf + h_pdf)
            clip = rect & page.rect
            if clip.is_empty:
                return {"success": True, "text": ""}
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip, alpha=False)
            img_bytes = pix.tobytes(output="png")

            # 优先 PaddleOCR（高精度），其次 RapidOCR，最后 PDF 文本兜底
            text = ""
            try:
                from src.plugins.paddle_ocr_processor import PaddleOcrProcessor

                proc = PaddleOcrProcessor()
                if proc.check_health().get("status") == "healthy":
                    import tempfile

                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        tmp.write(img_bytes)
                        tmp.flush()
                        try:
                            text = (proc.process_file(tmp.name) or "").strip()
                            if text:
                                logger.info("课本伴读 OCR 使用 PaddleOCR，识别 %d 字", len(text))
                        finally:
                            Path(tmp.name).unlink(missing_ok=True)
            except Exception:
                pass
            if not text:
                try:
                    from src.plugins.rapid_ocr_processor import RapidOcrProcessor

                    proc = RapidOcrProcessor()
                    if proc.check_health().get("status") == "healthy":
                        import tempfile

                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                            tmp.write(img_bytes)
                            tmp.flush()
                            try:
                                text = (proc.process_file(tmp.name) or "").strip()
                            finally:
                                Path(tmp.name).unlink(missing_ok=True)
                except Exception:
                    pass
            if not text:
                words = page.get_text("words", clip=clip)
                text = " ".join(w[4] for w in words).strip()
            return {"success": True, "text": text}
        finally:
            doc.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 失败: {e!s}") from e


# --- 课本伴读选区翻译（英译汉，不落库）---


class TranslateRequest(BaseModel):
    text: str


@course.post("/translate")
async def translate_text(
    body: TranslateRequest,
    current_user: User = Depends(get_required_user),
):
    """将选区文本翻译为中文（默认英译汉），不保存结果。"""
    from langchain_core.messages import HumanMessage, SystemMessage

    text = (body.text or "").strip()
    if not text:
        return {"success": True, "translated": ""}

    prompt = "将以下英文翻译成中文。只输出译文，不要解释、不要序号、不要标题。若原文已是中文，则输出原文或简要说明。"
    model = load_chat_model(conf.fast_model)
    try:
        msg_list = [
            SystemMessage(content=prompt),
            HumanMessage(content=text[:8000]),
        ]
        resp = await model.ainvoke(msg_list)
        translated = (resp.content if hasattr(resp, "content") else str(resp)).strip()
        return {"success": True, "translated": translated}
    except Exception as e:
        logger.warning("translate_text failed: %s", e)
        raise HTTPException(status_code=500, detail=f"翻译失败: {e!s}") from e


# --- 课本伴读阅读进度（永久记录，需登录）---


class ReadingPositionBody(BaseModel):
    book_id: str
    page: int


@course.get("/reading-position")
async def get_reading_position(
    book_id: str,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户对某本书的阅读进度。"""
    from sqlalchemy import select

    result = await db.execute(
        select(BookReadingPosition).where(
            BookReadingPosition.user_id == current_user.id,
            BookReadingPosition.book_id == book_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        return {"page": None}
    return {"page": row.page}


@course.put("/reading-position")
async def save_reading_position(
    body: ReadingPositionBody,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """保存当前用户对某本书的阅读进度（永久记录）。"""
    from sqlalchemy import select

    from src.utils.datetime_utils import utc_now_naive

    if body.page < 1:
        raise HTTPException(status_code=400, detail="页码从 1 开始")
    result = await db.execute(
        select(BookReadingPosition).where(
            BookReadingPosition.user_id == current_user.id,
            BookReadingPosition.book_id == body.book_id,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.page = body.page
        row.updated_at = utc_now_naive()
    else:
        db.add(
            BookReadingPosition(
                user_id=current_user.id,
                book_id=body.book_id,
                page=body.page,
            )
        )
    return {"success": True, "page": body.page}


# --- 习题推荐：出题、作答、错题统计、积分与商城 ---


@course.get("/exercises/textbook-chapters")
async def exercises_textbook_chapters():
    """获取课本章节目录（先选章节、再选知识点）。"""
    return {"chapters": get_textbook_chapters()}


class ExerciseGenerateRequest(BaseModel):
    question_type: str  # choice / fill / short_answer
    knowledge_point: str
    chapter: int | None = None  # 章号 1–8，与 knowledge_point 一起时结合课本出题
    section_id: str | None = None  # 小节 id 如 "1.1"，不填则用整章


@course.post("/exercises/generate")
async def exercises_generate(
    body: ExerciseGenerateRequest,
    current_user: User = Depends(get_required_user),
):
    """根据题型和知识点生成一道题（不落库，提交答案时再记录）；可选章节时结合课本内容出题。"""
    try:
        out = await generate_question(
            body.question_type,
            body.knowledge_point,
            chapter=body.chapter,
            section_id=body.section_id,
        )
        return out
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class ExerciseQuizGenerateRequest(BaseModel):
    chapter: int  # 章号 1–8
    question_type_counts: dict[str, int]  # {"choice": 2, "fill": 3, ...}
    knowledge_point_ids: list[str] = []  # 空表示使用该章节全部知识点


@course.post("/exercises/generate-quiz")
async def exercises_generate_quiz(
    body: ExerciseQuizGenerateRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """生成小测：一次生成多题（多种题型 + 数量）。知识点支持可选集合；未选时默认个性化抽取。"""

    allowed_types = {"choice", "fill", "short_answer"}
    question_sequence: list[str] = []
    for q_type, count in (body.question_type_counts or {}).items():
        if q_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"不支持的题型：{q_type}")
        n = int(count or 0)
        if n <= 0:
            continue
        question_sequence.extend([q_type] * n)

    if not question_sequence:
        raise HTTPException(status_code=400, detail="question_type_counts 总数量必须大于 0")

    chapters = get_textbook_chapters()
    chapter_obj = next((c for c in chapters if int(c.get("id")) == int(body.chapter)), None)
    if not chapter_obj:
        raise HTTPException(status_code=400, detail="章节不存在")

    all_kps = chapter_obj.get("knowledge_points") or []
    selected_ids = (body.knowledge_point_ids or [])[:]
    if selected_ids:
        id_set = {str(x) for x in selected_ids}
        eligible_kps = [kp for kp in all_kps if str(kp.get("id")) in id_set]
    else:
        eligible_kps = all_kps

    if not eligible_kps:
        raise HTTPException(status_code=400, detail="未找到可用知识点")

    eligible_titles = [str(kp.get("title") or "") for kp in eligible_kps]

    # 个性化：权重 = 错题次数 + 1（保证未出现过的知识点仍有非零概率）
    q_wrong = (
        select(ExerciseAttempt.knowledge_point, func.count(ExerciseAttempt.id).label("count"))
        .where(
            ExerciseAttempt.user_id == current_user.id,
            ExerciseAttempt.is_correct == 0,
            ExerciseAttempt.chapter == str(body.chapter),
            ExerciseAttempt.knowledge_point.in_(eligible_titles),
        )
        .group_by(ExerciseAttempt.knowledge_point)
    )
    result = await db.execute(q_wrong)
    wrong_rows = result.all()
    wrong_cnt_by_title: dict[str, int] = {str(r[0] or "").strip() or "未分类": int(r[1] or 0) for r in wrong_rows}

    weights = [wrong_cnt_by_title.get(str(kp.get("title") or "").strip() or "未分类", 0) + 1 for kp in eligible_kps]

    questions: list[dict] = []
    for q_type in question_sequence:
        kp = random.choices(eligible_kps, weights=weights, k=1)[0]
        out = await generate_question(
            q_type,
            kp.get("title") or "",
            chapter=body.chapter,
            section_id=kp.get("section_id"),
        )
        out["knowledge_point_id"] = kp.get("id")
        out["knowledge_point"] = kp.get("title") or ""
        questions.append(out)

    return {"questions": questions}


class ExerciseSubmitRequest(BaseModel):
    question_type: str
    knowledge_point: str
    question_content: str
    correct_answer: str
    scoring_points: list = []
    user_answer: str
    chapter: str | None = None  # 章节号，用于错题统计展示
    section_title: str | None = None  # 小节标题，用于错题统计展示


@course.post("/exercises/submit")
async def exercises_submit(
    body: ExerciseSubmitRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """提交答案：批改、记录对错(0/1)、答对加 1 积分。"""
    try:
        result = await grade_answer(
            question_type=body.question_type,
            question_content=body.question_content,
            correct_answer=body.correct_answer,
            scoring_points=body.scoring_points or [],
            user_answer=body.user_answer.strip(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    is_correct = result["is_correct"]
    explanation = result.get("explanation") or ""

    attempt = ExerciseAttempt(
        user_id=current_user.id,
        question_type=body.question_type,
        knowledge_point=body.knowledge_point,
        question_content=body.question_content,
        correct_answer=body.correct_answer,
        scoring_points=body.scoring_points or [],
        user_answer=body.user_answer,
        is_correct=is_correct,
        explanation=explanation,
        chapter=body.chapter,
        section_title=body.section_title,
    )
    db.add(attempt)

    if is_correct:
        user_row = await db.get(User, current_user.id)
        if user_row:
            user_row.points = (user_row.points or 0) + 1
            user_row.last_login = utc_now_naive()

    await db.commit()
    await db.refresh(attempt)
    return {
        "is_correct": is_correct,
        "explanation": explanation,
        "attempt_id": attempt.id,
    }


@course.get("/exercises/wrong-analysis")
async def exercises_wrong_analysis(
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
):
    """错题分析：直接读取与运维「做题记录」同一数据库同一表。
    数据库：PostgreSQL（环境变量 POSTGRES_URL）；表：exercise_attempts。
    与 dashboard 的 get_exercise_attempts 使用同一 db、同一 ExerciseAttempt 表，join User 按登录名筛选。"""
    login = (getattr(current_user, "user_id", None) or "").strip()
    uid = current_user.id
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size

    # 与运维一致：join User 按登录名筛选；若登录名为空则回退为按用户 id 筛选
    use_login = bool(login)
    if use_login:
        total_any_q = (
            select(func.count())
            .select_from(ExerciseAttempt)
            .join(User, ExerciseAttempt.user_id == User.id)
            .where(User.user_id == login)
        )
    else:
        logger.warning("wrong-analysis: current_user.user_id 为空，改用 user.id=%s 筛选", uid)
        total_any_q = select(func.count()).select_from(ExerciseAttempt).where(ExerciseAttempt.user_id == uid)
    total_any_result = await db.execute(total_any_q)
    total_attempts = int(total_any_result.scalar() or 0)

    if use_login:
        q_kp = (
            select(ExerciseAttempt.knowledge_point, func.count(ExerciseAttempt.id).label("count"))
            .select_from(ExerciseAttempt)
            .join(User, ExerciseAttempt.user_id == User.id)
            .where(User.user_id == login, ExerciseAttempt.is_correct == 0)
            .group_by(ExerciseAttempt.knowledge_point)
        )
        total_wrong_q = (
            select(func.count())
            .select_from(ExerciseAttempt)
            .join(User, ExerciseAttempt.user_id == User.id)
            .where(User.user_id == login, ExerciseAttempt.is_correct == 0)
        )
        q_list = (
            select(ExerciseAttempt)
            .join(User, ExerciseAttempt.user_id == User.id)
            .where(User.user_id == login, ExerciseAttempt.is_correct == 0)
            .order_by(ExerciseAttempt.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    else:
        q_kp = (
            select(ExerciseAttempt.knowledge_point, func.count(ExerciseAttempt.id).label("count"))
            .select_from(ExerciseAttempt)
            .where(ExerciseAttempt.user_id == uid, ExerciseAttempt.is_correct == 0)
            .group_by(ExerciseAttempt.knowledge_point)
        )
        total_wrong_q = (
            select(func.count())
            .select_from(ExerciseAttempt)
            .where(ExerciseAttempt.user_id == uid, ExerciseAttempt.is_correct == 0)
        )
        q_list = (
            select(ExerciseAttempt)
            .where(ExerciseAttempt.user_id == uid, ExerciseAttempt.is_correct == 0)
            .order_by(ExerciseAttempt.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

    result_kp = await db.execute(q_kp)
    rows_kp = result_kp.all()
    total_wrong = sum(int(r[1] or 0) for r in rows_kp)
    by_knowledge_point = []
    for r in rows_kp:
        name = (r[0] or "").strip() or "未分类"
        cnt = int(r[1]) if r[1] is not None else 0
        if cnt > 0:
            by_knowledge_point.append({"name": name, "count": cnt})

    total_wrong_result = await db.execute(total_wrong_q)
    total_count = int(total_wrong_result.scalar() or 0)
    result_list = await db.execute(q_list)
    attempts = result_list.scalars().all()
    items = [a.to_dict() for a in attempts]

    # 无数据时查表总量便于排查
    debug_table_total = None
    if total_attempts == 0:
        r_all = await db.execute(select(func.count()).select_from(ExerciseAttempt))
        debug_table_total = int(r_all.scalar() or 0)
        logger.info(
            "wrong-analysis: login=%r uid=%s total_attempts=0 表中总记录数=%s",
            login,
            uid,
            debug_table_total,
        )
    else:
        logger.info(
            "wrong-analysis: login=%s total_attempts=%s total_wrong=%s list_page=%s returned=%s",
            login,
            total_attempts,
            total_wrong,
            page,
            len(items),
        )
    out = {
        "by_knowledge_point": by_knowledge_point,
        "total_attempts": total_attempts,
        "total_wrong": total_wrong,
        "user_login": login or None,
        "items": items,
        "total": total_count,
        "page": page,
        "page_size": page_size,
    }
    if debug_table_total is not None:
        out["debug_table_total"] = debug_table_total
    return out


@course.get("/exercises/wrong-stats")
async def exercises_wrong_stats(
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """按知识点统计答错次数，用于环状图。与运维做题记录同源，join User 按 User.user_id 筛选。"""
    login = (getattr(current_user, "user_id", None) or "").strip()
    total_any_q = (
        select(func.count())
        .select_from(ExerciseAttempt)
        .join(User, ExerciseAttempt.user_id == User.id)
        .where(User.user_id == login)
    )
    total_any_result = await db.execute(total_any_q)
    total_attempts = int(total_any_result.scalar() or 0)
    q = (
        select(ExerciseAttempt.knowledge_point, func.count(ExerciseAttempt.id).label("count"))
        .select_from(ExerciseAttempt)
        .join(User, ExerciseAttempt.user_id == User.id)
        .where(User.user_id == login, ExerciseAttempt.is_correct == 0)
        .group_by(ExerciseAttempt.knowledge_point)
    )
    result = await db.execute(q)
    rows = result.all()
    total_wrong = sum(int(r[1] or 0) for r in rows)
    logger.info(
        "wrong-stats: login=%s total_attempts=%s total_wrong=%s by_kp_rows=%s",
        login,
        total_attempts,
        total_wrong,
        len(rows),
    )
    by_knowledge_point = []
    for r in rows:
        name = (r[0] or "").strip() or "未分类"
        cnt = int(r[1]) if r[1] is not None else 0
        if cnt > 0:
            by_knowledge_point.append({"name": name, "count": cnt})
    return {
        "by_knowledge_point": by_knowledge_point,
        "total_attempts": total_attempts,
        "total_wrong": total_wrong,
        "user_login": login or None,
    }


@course.get("/exercises/wrong-list")
async def exercises_wrong_list(
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
):
    """分页获取当前用户的错题列表。与运维做题记录同源，join User 按 User.user_id 筛选。"""
    login = (getattr(current_user, "user_id", None) or "").strip()
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size
    total_q = (
        select(func.count())
        .select_from(ExerciseAttempt)
        .join(User, ExerciseAttempt.user_id == User.id)
        .where(User.user_id == login, ExerciseAttempt.is_correct == 0)
    )
    total = await db.execute(total_q)
    total_count = int(total.scalar() or 0)
    q = (
        select(ExerciseAttempt)
        .join(User, ExerciseAttempt.user_id == User.id)
        .where(User.user_id == login, ExerciseAttempt.is_correct == 0)
        .order_by(ExerciseAttempt.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(q)
    attempts = result.scalars().all()
    logger.info(
        "wrong-list: login=%s total=%s page=%s returned=%s",
        login,
        total_count,
        page,
        len(attempts),
    )
    items = [a.to_dict() for a in attempts]
    return {
        "items": items,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "user_login": login or None,
    }


@course.get("/points")
async def get_points(
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """当前用户积分。"""
    user_row = await db.get(User, current_user.id)
    points = user_row.points if user_row else 0
    return {"points": points}


MALL_COST_MIN, MALL_COST_MAX = 1, 100

_DEFAULT_MALL_ITEMS = [
    ("初出茅庐", "积分达到 10 即可兑换", 10, "🌱", 1),
    ("小试牛刀", "积分达到 30 即可兑换", 30, "⚔️", 2),
    ("勤学不辍", "积分达到 50 即可兑换", 50, "📚", 3),
    ("网络达人", "积分达到 80 即可兑换", 80, "🏆", 4),
    ("学神附体", "积分达到 100 即可兑换", 100, "✨", 5),
]


async def _ensure_mall_items(db: AsyncSession):
    """确保商城有默认称号（可重复调用）。兑换规则：单价 1～100 积分，兑换时不扣积分。"""
    r = await db.execute(select(func.count()).select_from(MallItem))
    if (r.scalar() or 0) == 0:
        for name, desc, cost, icon, order in _DEFAULT_MALL_ITEMS:
            db.add(MallItem(name=name, description=desc, cost=cost, icon=icon, sort_order=order))
    # 已有数据也做一次迁移：把 cost 限制在 1～100，并把默认 5 个称号的文案与 cost 同步
    await db.execute(
        update(MallItem).values(cost=func.least(func.greatest(MallItem.cost, MALL_COST_MIN), MALL_COST_MAX))
    )
    for name, desc, cost, icon, order in _DEFAULT_MALL_ITEMS:
        await db.execute(update(MallItem).where(MallItem.name == name).values(description=desc, cost=cost))


@course.get("/mall")
async def mall_list(
    db: AsyncSession = Depends(get_db),
):
    """商城称号列表（所有人可看）。"""
    await _ensure_mall_items(db)
    await db.commit()
    result = await db.execute(select(MallItem).order_by(MallItem.sort_order))
    items = result.scalars().all()
    return {"items": [x.to_dict() for x in items]}


class MallPurchaseRequest(BaseModel):
    item_id: int


@course.post("/mall/purchase")
async def mall_purchase(
    body: MallPurchaseRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """用积分兑换称号。规则：商品单价 1～100 积分，兑换时不扣积分（仅校验积分达标即可兑换）。"""
    await _ensure_mall_items(db)
    await db.commit()
    item = await db.get(MallItem, body.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="商品不存在")
    if not (MALL_COST_MIN <= item.cost <= MALL_COST_MAX):
        raise HTTPException(
            status_code=400,
            detail=f"商品积分不在有效范围（{MALL_COST_MIN}～{MALL_COST_MAX}）",
        )
    user_row = await db.get(User, current_user.id)
    points = user_row.points if user_row else 0
    if points < item.cost:
        raise HTTPException(status_code=400, detail="积分不足")
    existing = await db.execute(
        select(UserMallItem).where(
            UserMallItem.user_id == current_user.id,
            UserMallItem.mall_item_id == body.item_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="已兑换过该称号")
    db.add(UserMallItem(user_id=current_user.id, mall_item_id=body.item_id))
    await db.commit()
    return {"success": True, "points_remaining": points}


@course.get("/mall/my-titles")
async def mall_my_titles(
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """当前用户已兑换的称号列表。"""
    q = (
        select(MallItem, UserMallItem.acquired_at)
        .join(UserMallItem, UserMallItem.mall_item_id == MallItem.id)
        .where(UserMallItem.user_id == current_user.id)
        .order_by(UserMallItem.acquired_at.desc())
    )
    result = await db.execute(q)
    rows = result.all()
    out = []
    for row in rows:
        mall_item, acquired_at = row[0], row[1]
        out.append(
            {
                "item": mall_item.to_dict(),
                "acquired_at": format_utc_datetime(acquired_at) if acquired_at else None,
            }
        )
    return {"items": out}
