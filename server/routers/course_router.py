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
    enable_web_search: Optional[bool] = None  # 本次对话是否启用网络搜索，不传则用智能体/部门配置


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


@course.post("/chat/stream")
async def course_chat_stream(
    request: CourseChatRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """课程对话流式接口：使用默认智能体，课本伴读侧边栏对话会调用此接口。"""
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
    chapter: Optional[int] = None  # 章号 1–8，与 knowledge_point 一起时结合课本出题
    section_id: Optional[str] = None  # 小节 id 如 "1.1"，不填则用整章


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


class ExerciseSubmitRequest(BaseModel):
    question_type: str
    knowledge_point: str
    question_content: str
    correct_answer: str
    scoring_points: list = []
    user_answer: str
    chapter: Optional[str] = None  # 章节号，用于错题统计展示
    section_title: Optional[str] = None  # 小节标题，用于错题统计展示


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
        update(MallItem).values(
            cost=func.least(func.greatest(MallItem.cost, MALL_COST_MIN), MALL_COST_MAX)
        )
    )
    for name, desc, cost, icon, order in _DEFAULT_MALL_ITEMS:
        await db.execute(
            update(MallItem).where(MallItem.name == name).values(description=desc, cost=cost)
        )


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
        out.append({
            "item": mall_item.to_dict(),
            "acquired_at": format_utc_datetime(acquired_at) if acquired_at else None,
        })
    return {"items": out}
