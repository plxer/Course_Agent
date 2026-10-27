"""课程智能体路由：课本伴读、视频伴读、课程对话流。"""

import os
import re
import json
import uuid
import random
import math
from pathlib import Path
from typing import Any

import fitz
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src import config as conf
from src.config import course_reading_paddle_ocr_enabled
from src.agents import agent_manager
from src import knowledge_base as kb_manager
from sqlalchemy import func, select, update

from src.agents.common import load_chat_model
from src.services.chat_stream_service import stream_agent_chat
from src.services.exercise_service import grade_answer, generate_question
from src.services.llm_usage_log_service import (
    COURSE_RELEVANCE_AGENT_ID,
    COURSE_TRANSLATE_AGENT_ID,
    extract_usage_from_lc_response,
    log_course_aux_llm_call,
)
from src.services.textbook_service import get_textbook_chapters, knowledgebase_dir
from src.repositories.conversation_repository import ConversationRepository
from src.storage.postgres.models_business import (
    BookReadingPosition,
    ExerciseAttempt,
    MallItem,
    Message,
    User,
    UserMallItem,
)
from src.utils import logger
from src.utils.datetime_utils import format_utc_datetime, utc_now_naive
from server.utils.auth_middleware import get_db, get_required_user

course = APIRouter(prefix="/course", tags=["course"])

_EXERCISE_QUESTION_TYPES = frozenset({"choice", "multi_choice", "short_answer", "calculation"})
_EXERCISE_TS_HALF_LIFE_DAYS = 14.0
_EXERCISE_TS_DECAY_COUNT_CAP = 30.0


def _sample_kp_score_with_thompson(wrong_attempts: float, correct_attempts: float) -> float:
    """
    Thompson Sampling（Beta-Bernoulli）采样得分，目标是优先抽到「更可能答错」的知识点。
    posterior = Beta(1 + wrong_attempts, 1 + correct_attempts)
    """
    a = 1.0 + max(0.0, float(wrong_attempts))
    b = 1.0 + max(0.0, float(correct_attempts))
    return random.betavariate(a, b)


# 课本/视频在仓库外：默认仓库同级 yuxi-knowledgebase，也可用 KNOWLEDGEBASE_DIR 指定绝对路径。
_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # server/routers/course_router.py
_KNOWLEDGEBASE_DIR = knowledgebase_dir()
_BOOKS_DIR = _KNOWLEDGEBASE_DIR / "books"
_VIDEOS_DIR = _KNOWLEDGEBASE_DIR / "videos"

# PDF 课本 id → knowledgebase 下 MinerU 导出目录，包含 _page_*_Figure_*.jpeg。
# 文件名内页码与伴读页码差 1：伴读显示页 = 文件名页码 + 1。
_BOOK_FIGURES_SUBDIR_BY_BOOK_ID: dict[str, str] = {
    "ComputerNetworking-TopDown-v8-2021": "ComputerNetworking-TopDown",
}
_FIGURE_FILENAME_RE = re.compile(r"^_page_(\d+)_(.+)\.(jpe?g|png)$", re.IGNORECASE)


def _book_figures_root(book_id: str) -> Path | None:
    sub = _BOOK_FIGURES_SUBDIR_BY_BOOK_ID.get(book_id)
    if not sub:
        return None
    p = _KNOWLEDGEBASE_DIR / sub
    return p if p.is_dir() else None


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


# 单独归类到「复习」章（展示在列表最后），与文件名是否含 Chapter 无关
_REVIEW_VIDEO_STEM = "Review"
# 排序用：大于任意常规章节号，保证「复习」在最后一章
_REVIEW_CHAPTER_SORT_KEY = 9999


def _list_videos() -> list[dict]:
    """扫描 videos 目录（含子目录）下的 .mp4，按文件名中的 Chapter 数字分组，返回 chapters 列表。"""
    root = _VIDEOS_DIR
    if not root.is_dir():
        return []
    chapter_re = re.compile(r"Chapter\s*(\d+)", re.IGNORECASE)
    by_chapter: dict[int, list[dict]] = {}
    review_videos: list[dict] = []
    for path in root.rglob("*.mp4"):
        try:
            stat = path.stat()
            stem = path.stem
            name = path.name
            if stem == _REVIEW_VIDEO_STEM:
                review_videos.append({"id": stem, "name": name, "size": stat.st_size})
                continue
            m = chapter_re.search(stem)
            ch = int(m.group(1)) if m else 0
            if ch not in by_chapter:
                by_chapter[ch] = []
            by_chapter[ch].append({"id": stem, "name": name, "size": stat.st_size})
        except (OSError, ValueError):
            continue
    for vlist in by_chapter.values():
        vlist.sort(key=lambda x: x["name"])
    review_videos.sort(key=lambda x: x["name"])
    chapters: list[dict] = [{"chapter": ch, "videos": vlist} for ch, vlist in sorted(by_chapter.items())]
    if review_videos:
        chapters.append(
            {
                "chapter": _REVIEW_CHAPTER_SORT_KEY,
                "chapter_label": "复习",
                "videos": review_videos,
            }
        )
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
    """视频文件流，支持 Range 便于拖动进度。不带 filename，避免 Content-Disposition: attachment 导致远程播放失败。"""
    path = _resolve_video_path(video_id)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="视频不存在")
    return FileResponse(
        path,
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
        },
    )


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
# pdf_book_id：对应课本伴读中的 PDF（yuxi-knowledgebase/books 下文件名不含扩展名），用于页码跳转
COURSE_KNOWLEDGE_BASES = [
    {"id": "computer_networking", "name": "计算机网络", "pdf_book_id": "ComputerNetworking-TopDown-v8-2021"},
]

# 课程 Milvus：未启用系统重排序时的向量召回条数；筛选用「重排或向量意义下的全局 top1 所在页
# + 本批候选中出现过的页码 ±1 迭代相邻」闭包
COURSE_MILVUS_RECALL_TOP_K = 8
# 启用重排序时：先向量召回本池大小 → 重排模型精排 → 再交 top1 + 相邻页（final_top_k 与本值相同，避免先截断再扩页）
COURSE_MILVUS_RERANK_POOL = 48


class CourseChatRequest(BaseModel):
    query: str
    thread_id: str | None = None
    meta: dict = {}
    enable_web_search: bool | None = None  # 本次对话是否启用网络搜索，不传则用智能体/部门配置
    knowledge_base: str | None = None  # 课程知识库 id，如 "computer_networking" 表示先检索《计算机网络》课本再作答
    # 与 /api/chat/image/upload 返回字段一致：纯 base64，不含 data: 前缀；需搭配多模态对话模型（如硅基流动 Qwen-VL 等）
    image_content: str | None = None
    image_mime_type: str | None = None  # 如 image/jpeg、image/png，缺省按 image/jpeg


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

    prompt = """根据下面用户的第一条问题和助手的第一次回复，生成一句简短的对话标题（不超过20字，
不要引号、不要 markdown、不要“标题：”等前缀）。只输出标题内容。"""
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


def _course_query_tokens(query: str) -> list[str]:
    """用于检索加权的查询词（略去过短 token）。"""
    return [t for t in re.split(r"[\s,，;；、]+", (query or "").strip()) if len(t) >= 2][:16]


def _course_chunk_sort_score(query: str, item: dict) -> float:
    """排序用分数：若 Milvus 已做重排序则仅用 rerank_score，否则用向量分 + 轻量位置加权。"""
    rs = item.get("rerank_score")
    if rs is not None:
        try:
            return float(rs)
        except (TypeError, ValueError):
            pass
    return _course_chunk_retrieval_score(query, item)


def _course_chunk_retrieval_score(query: str, item: dict) -> float:
    """
    在向量相似度基础上做轻量加权：优先 query 词出现在段首/前部，或出现在小节标题行（# / 1.2 样式）。
    """
    base = float(item.get("score", 0.0))
    content = (item.get("content") or "").strip()
    if not content:
        return base
    q_tokens = _course_query_tokens(query)
    if not q_tokens:
        return base
    head_len = max(600, min(len(content), len(content) // 3 + 400))
    head = content[:head_len].lower()
    hits = sum(1 for t in q_tokens if t.lower() in head)
    position_boost = 0.025 * (hits / len(q_tokens))
    heading_boost = 0.0
    for line in content.split("\n")[:14]:
        ln = line.lower().strip()
        if ln.startswith("#") or re.match(r"^\d+\.\d+", ln):
            if any(t.lower() in ln for t in q_tokens):
                heading_boost = 0.04
                break
    return base + position_boost + heading_boost


def _course_chunks_top1_and_adjacent_pages(query: str, chunks: list[dict]) -> list[dict]:
    """
    在 Milvus 召回的一批候选内（若已重排序则按 rerank_score，否则按向量检索分）：
    1）先排序，每页（book_page>=0）只保留一条最高分块；
    2）取全局最高分块为 top1；若其无有效页码，只返回该条；
    3）否则在「本批候选中出现过的页码」中，迭代加入与已选集合相差 1 的页（7→8→9 闭包）。
    返回块按课本页码升序排列。
    """
    if not chunks:
        return []
    ranked = sorted(chunks, key=lambda c: _course_chunk_sort_score(query, c), reverse=True)

    best_by_page: dict[int, dict] = {}
    best_orphans: dict[str, dict] = {}

    for c in ranked:
        meta = c.get("metadata") or {}
        bp = meta.get("book_page", -1)
        if isinstance(bp, int) and bp >= 0:
            if bp not in best_by_page:
                best_by_page[bp] = c
        else:
            cid = meta.get("chunk_id") or str(id(c))
            if cid not in best_orphans:
                best_orphans[cid] = c

    representatives: list[dict] = list(best_by_page.values()) + list(best_orphans.values())
    representatives.sort(key=lambda c: _course_chunk_sort_score(query, c), reverse=True)
    top1 = representatives[0]

    meta1 = top1.get("metadata") or {}
    bp1 = meta1.get("book_page", -1)
    if not isinstance(bp1, int) or bp1 < 0:
        return [top1]

    candidate_pages = set(best_by_page.keys())
    selected: set[int] = {bp1}
    while True:
        added = False
        for p in candidate_pages:
            if p in selected:
                continue
            if any(abs(p - s) == 1 for s in selected):
                selected.add(p)
                added = True
        if not added:
            break

    return [best_by_page[p] for p in sorted(selected)]


async def _get_course_knowledge_context(query: str, kb_id: str, current_user) -> tuple[str, list[int]]:
    """
    根据课程知识库 id 从 Milvus 检索上下文。无回退：找不到对应库或调用失败即报错。
    返回 (课本摘录, 命中的课本页码列表，升序去重)。
    """
    course_entry = next((c for c in COURSE_KNOWLEDGE_BASES if c.get("id") == kb_id), None)
    display_name = course_entry.get("name", "") if course_entry else ""
    if not display_name:
        raise HTTPException(
            status_code=400,
            detail=f"未知的课程知识库 id: {kb_id!r}，请选择有效的课程知识库",
        )

    user_info = {
        "role": getattr(current_user, "role", None),
        "department_id": getattr(current_user, "department_id", None),
    }
    result = await kb_manager.get_databases_by_user(user_info)
    databases = result.get("databases") or []
    milvus_db = next(
        (d for d in databases if (d.get("name") == display_name and (d.get("kb_type") or "").lower() == "milvus")),
        None,
    )
    if not milvus_db or not milvus_db.get("db_id"):
        raise HTTPException(
            status_code=503,
        detail=(
            f"课程知识库「{display_name}」对应的 Milvus 知识库未找到或不可用，请先在知识库管理中创建并导入课本"
            f"（名称须为「{display_name}」、类型为 Milvus）"
        ),
        )

    try:
        aq_kwargs: dict = {"final_top_k": COURSE_MILVUS_RECALL_TOP_K}
        reranker_id = (getattr(conf, "reranker", None) or "").strip()
        if getattr(conf, "enable_reranker", False) and reranker_id:
            aq_kwargs["use_reranker"] = True
            aq_kwargs["reranker_model"] = reranker_id
            aq_kwargs["recall_top_k"] = COURSE_MILVUS_RERANK_POOL
            aq_kwargs["final_top_k"] = COURSE_MILVUS_RERANK_POOL
        chunks = await kb_manager.aquery(query, milvus_db["db_id"], **aq_kwargs)
    except Exception as e:
        logger.exception("Milvus 课程知识库检索失败: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"课程知识库检索失败（Milvus 调用异常）: {e!s}",
        ) from e

    if not chunks:
        return "", []

    chunks = _course_chunks_top1_and_adjacent_pages(query, chunks)

    parts = []
    pages: list[int] = []
    total = 0
    max_chars = 8000
    for item in chunks:
        content = (item.get("content") or "").strip()
        if not content:
            continue
        meta = item.get("metadata") or {}
        source = meta.get("source", "")
        bp = meta.get("book_page", -1)
        page_line = ""
        if isinstance(bp, int) and bp > 0:
            pages.append(bp)
            page_line = f"（本段来自课本第 {bp} 页，仅供定位，不要在正文中写出页码）\n"
        block = f"【{source}】\n{page_line}{content}\n" if source else f"{page_line}{content}\n"
        if total + len(block) > max_chars:
            block = block[: max_chars - total]
        parts.append(block)
        total += len(block)
        if total >= max_chars:
            break
    uniq_pages = sorted(dict.fromkeys(pages))
    return ("\n".join(parts).strip() if parts else "", uniq_pages)


def _message_content_to_text(content) -> str:
    """将 LLM 返回的 content（str 或多段块列表）拼成纯文本。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    return str(content)


def _llm_answer_is_no_relevant(text: str) -> bool:
    """仅当模型明确给出否定相关时返回 True；用 \\b 避免 NOBODY、NOTE 等被 startswith('NO') 误判。"""
    raw = (text or "").strip()
    if not raw:
        return False
    if raw.startswith("否") or raw.startswith("不相关"):
        return True
    upper = raw.upper()
    return bool(re.match(r"^\s*(NO|NOT)\b", upper))


# 命中则跳过 fast 模型相关性判断，避免小模型不认识缩写（如 SDN）而误拦
# 词条覆盖 Kurose & Ross《自顶向下》各章：接入与物理介质、应用/传输/网络/链路/无线/安全等
_COURSE_QUERY_NETWORKING_HINT_RE = re.compile(
    r"(sdn|openflow|nfv|软件定义网络|网络功能虚拟化|"
    # --- Ch1 概论 / 接入 / 物理介质 / 核心 ---
    r"互联网|万维网|网页|浏览器|电子邮件|电子信箱|邮箱|域名|"
    r"端系统|主机|客户机|服务器|客户端|ISP|接入网|驻地网|宽带|"
    r"数据中心|云计算|分布式应用|套接字|socket接口|"
    r"分组交换|电路交换|报文|存储转发|分组|数据报|"
    r"时延|延迟|排队|丢包|吞吐量|吞吐率|带宽|传播|传输时延|处理时延|端到端|"
    r"协议栈|分层|体系结构|封装|解封装|"
    r"频分|时分|码分|波分|复用|多路复用|解复用|"
    r"调制解调|调制解调器|电缆调制解调|xDSL|\bdsl\b|"
    r"光纤|光缆|光通信|光网络|单模|多模|双绞线|同轴|铜线|"
    r"传输介质|物理介质|引导型|非引导型|有线|无线信道|"
    r"卫星|微波|地理同步|低轨|"
    r"fiber[- ]?optic|fibre[- ]?optic|\bfiber\b|\bfibre\b|"
    r"twisted[- ]?pair|coaxial|guided|unguided|"
    r"\bftth\b|\bhfc\b|\bpon\b|\baon\b|\bont\b|\bolt\b|docsis|\bcmts\b|dslam|"
    r"multimode|single[- ]?mode|dwdm|cwdm|"
    r"恶意软件|病毒|蠕虫|嗅探|欺骗|拒绝服务|"
    r"ietf|\brfc\b|ieee\s*802|"
    # --- Ch2 应用层 ---
    r"http|https|quic|web缓存|代理|cookie|"
    r"smtp|pop3|imap|mime|ftp|sftp|telnet|\bssh\b|nfs|"
    r"dns|域名系统|域名解析|权威|递归|本地域名|"
    r"p2p|对等网络|比特流|bittorrent|torrent|"
    r"dash|流媒体|cdn|内容分发|akamai|"
    r"mqtt|websocket|rtp\b|sip\b|html|uri\b|url\b|restful|"
    # --- Ch3 传输层 ---
    r"tcp/ip|\btcp\b|\budp\b|端口号|复用与分解|多路分解|"
    r"可靠传输|流水线|回退N|选择重传|\bgbn\b|\bsr\b|go[- ]?back|selective repeat|"
    r"校验和|序号|确认|重传|超时|往返|RTT|"
    r"三次握手|四次挥手|连接建立|连接释放|"
    r"流量控制|拥塞控制|慢启动|拥塞避免|快速重传|快速恢复|"
    r"aimd|\breno\b|\bcubic\b|\bbbr\b|ecn|sack|"
    # --- Ch4 网络层 数据面 ---
    r"ipv4|ipv6|ip地址|子网|子网掩码|超网|cidr|前缀|最长前缀|"
    r"默认网关|转发表|路由表|分片|mtu|"
    r"\bnat\b|网络地址转换|"
    r"middlebox|中间盒|"
    r"match[- ]?action|流表|通用转发|"
    # --- Ch5 控制面 / 路由 ---
    r"路由|路由器|路由选择|路由算法|"
    r"链路状态|距离向量|dijkstra|bellman[- ]?ford|"
    r"ospf|bgp|自治系统|域内|域间|"
    r"rip\b|eigrp|\bisis\b|"
    r"icmp|igmp|任播|组播|多播|广播|单播|anycast|multicast|"
    r"snmp|\bmib\b|netconf|yang|"
    r"mpls|vpn|\bgre\b|vxlan|"
    # --- Ch6 链路层 / 局域网 ---
    r"链路层|数据链路|帧|差错检测|差错纠正|纠错|检错|"
    r"奇偶|crc|循环冗余|汉明|"
    r"多路访问|随机接入|轮流|令牌|"
    r"csma|csma/cd|csma/ca|"
    r"tdma|fdma|cdma|"
    r"以太网|快速以太网|千兆以太网|万兆|"
    r"mac地址|mac层|arp|地址解析|"
    r"交换机|链路层交换机|透明桥|生成树|\bstp\b|vlan|虚拟局域网|"
    r"ppp|hdlc|"
    r"nic|网卡|"
    # --- Ch7 无线与移动 ---
    r"wi-?fi|无线局域网|wlan|802\.11|"
    r"蓝牙|bluetooth|个域网|"
    r"蜂窝|4g|5g|\blte\b|基站|毫微微|"
    r"移动性|漫游|切换|handoff|mobile ip|移动ip|"
    r"ofdm|mimo|"
    # --- Ch8 安全 ---
    r"ssl|tls|ipsec|ike|esp|\bah\b|"
    r"对称密钥|公钥|加密|解密|数字签名|消息完整性|"
    r"哈希|hmac|aes|rsa|sha[- ]?256|"
    r"pgp|"
    r"防火墙|入侵检测|入侵防御|ids|ips|waf|"
    r"vpn|"
    # --- 通用（与原有关键词合并） ---
    r"socket|"
    r"ddos|"
    r"网络安全|网络层|运输层|传输层|应用层|物理层|"
    r"协议|"
    r"拥塞|"
    r"计算机网络|自顶向下|计算机网络自顶向下|"
    r"kurose|ross)",
    re.I,
)


def _course_query_has_networking_keyword_hint(query: str) -> bool:
    return bool(_COURSE_QUERY_NETWORKING_HINT_RE.search(query or ""))


# 无网络术语时的「对话延续 / 元追问」用语：单独一句常被 fast 模型误判为不相关
_COURSE_DIALOGUE_FOLLOWUP_SUBSTRINGS: frozenset[str] = frozenset(
    {
        "没听懂",
        "听不懂",
        "听不太懂",
        "不太懂",
        "没太懂",
        "不明白",
        "不理解",
        "没理解",
        "还是不懂",
        "仍不懂",
        "不清楚",
        "没听明白",
        "看不太懂",
        "啥意思",
        "什么意思",
        "怎么理解",
        "如何理解",
        "举个例子",
        "举个栗子",
        "举例说明",
        "打个比方",
        "能举例",
        "能否举例",
        "再举",
        "多举几个",
        "总结一下",
        "归纳一下",
        "简要总结",
        "帮我总结",
        "概括一下",
        "简述",
        "列要点",
        "要点是什么",
        "再说一遍",
        "重复一遍",
        "重讲",
        "重新讲",
        "展开讲讲",
        "详细说说",
        "详细说明",
        "说详细点",
        "多讲一点",
        "接着说",
        "继续说",
        "还有呢",
        "然后呢",
        "对吗",
        "对不对",
        "是这样吗",
        "确认一下",
        "通俗",
        "白话",
        "简单点",
        "用人话",
        "易懂",
        "英文怎么说",
        "翻成英文",
        "补充一下",
        "再讲讲",
        "继续讲",
        "上面说的",
        "刚才说的",
        "你刚才",
        "之前说的",
        "前文",
        "紧接着",
        "那一点",
        "这一点",
        "为什么这么说",
        "什么意思呢",
        "展开",
        "接着问",
        "上文",
        "前面说的",
        "你前面",
        "你上面",
        "换句话说",
        "换言之",
        "你说错了",
        "说错了",
        "讲错了",
        "写错了",
        "表述有问题",
        "表述不对",
        "这句话",
        "这句",
        "哪里错",
        "哪儿错",
        "不对吧",
        "不是这个意思",
        "你刚才说",
        "纠正",
        "更正一下",
    }
)
_COURSE_DIALOGUE_FOLLOWUP_EN_SNIPPETS: frozenset[str] = frozenset(
    {
        "summarize",
        "summary",
        "give an example",
        "for example",
        "i don't understand",
        "i dont understand",
        "explain again",
        "more detail",
        "simpler terms",
    }
)


def _course_query_is_dialogue_followup(query: str) -> bool:
    """是否为针对上一轮讲解的追问、举例、总结等（通常不含网络术语）。"""
    q = (query or "").strip()
    if not q or len(q) > 100:
        return False
    if any(s in q for s in _COURSE_DIALOGUE_FOLLOWUP_SUBSTRINGS):
        return True
    low = q.lower()
    return any(s in low for s in _COURSE_DIALOGUE_FOLLOWUP_EN_SNIPPETS)


# 仅拦截明显违规/严重跑题；宁可漏拦也不要用宽泛关键词误杀课程追问
_COURSE_HARD_REJECT_RE = re.compile(
    r"(自杀|自残|割腕|如何杀人|怎么杀人|制作炸弹|炸弹制作|炸药配方|"
    r"冰毒|海洛因|可卡因|贩毒|儿童色情|"
    r"恐怖主义|制作枪支|如何制作武器)",
    re.I,
)


def _course_query_hard_reject(query: str) -> bool:
    return bool(_COURSE_HARD_REJECT_RE.search(query or ""))


async def _recent_course_dialogue(db: AsyncSession | None, thread_id: str | None) -> str:
    """取本线程最近若干轮用户/助手正文，供相关性判断看上下文。"""
    if db is None or not (thread_id or "").strip():
        return ""
    try:
        conv_repo = ConversationRepository(db)
        conv = await conv_repo.get_conversation_by_thread_id(thread_id.strip())
        if not conv:
            return ""
        result = await db.execute(
            select(Message.role, Message.content)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(12)
        )
        rows = list(reversed(result.all()))
    except Exception as e:
        logger.warning("读取课程对话上下文失败: %s", e)
        return ""
    lines: list[str] = []
    for role, content in rows:
        if role not in ("user", "assistant", "human", "ai"):
            continue
        text = " ".join((content or "").split())
        if not text:
            continue
        label = "用户" if role in ("user", "human") else "助手"
        lines.append(f"{label}: {text[:240]}")
    return "\n".join(lines[-8:])


async def _classify_course_query_relevance(
    query: str,
    *,
    db: AsyncSession | None = None,
    stats_user_id: int | None = None,
    thread_id: str | None = None,
) -> str:
    """
    返回 allow / off_topic / disallowed。
    网络术语命中则放行；严重违规词拒绝；其余交给小模型，且必须带上对话上下文。
    调用异常时视为 allow，避免误拦。
    """
    query = (query or "").strip()[:500]
    if not query:
        return "off_topic"
    if _course_query_hard_reject(query):
        return "disallowed"
    if _course_query_has_networking_keyword_hint(query):
        return "allow"

    history = await _recent_course_dialogue(db, thread_id)
    # 已有课程对话时，短追问（没听懂/什么意思/你说错了）直接放行，避免小模型只看当前句
    if history and _course_query_is_dialogue_followup(query):
        return "allow"

    from langchain_core.messages import HumanMessage, SystemMessage

    prompt = (
        "你是一个判断题助手。判断用户「当前问题」是否属于《计算机网络》课程对话。\n"
        "相关包括：网络协议与体系结构、TCP/IP、HTTP、DNS、路由与交换、SDN/NFV/OpenFlow、"
        "数据中心与云网络、无线与移动网络、网络安全、拥塞控制、Socket、QoS、CDN、P2P 等。\n"
        "必须结合「对话上下文」判断：若用户在追问上一轮讲解、纠正/质疑 AI 表述、要求举例、总结、"
        "重讲、翻译或表示没听懂，即使当前句没有网络术语，也一律 YES。\n"
        "仅当当前问题明显是另一门课、生活闲聊、或与网络课程完全无关，且无法解释为对上文的追问时，"
        "才回答 NO。不确定时回答 YES。\n"
        "只回答一个词：YES 或 NO。"
    )
    human = query
    if history:
        human = f"【对话上下文】\n{history}\n\n【当前问题】\n{query}"
    try:
        model = load_chat_model(conf.fast_model)
        msg_list = [
            SystemMessage(content=prompt),
            HumanMessage(content=human),
        ]
        resp = await model.ainvoke(msg_list)
        text = _message_content_to_text(
            resp.content if hasattr(resp, "content") else resp
        )
        if db is not None and stats_user_id is not None:
            inp, outp = extract_usage_from_lc_response(resp)
            await log_course_aux_llm_call(
                db,
                user_int_id=stats_user_id,
                agent_id=COURSE_RELEVANCE_AGENT_ID,
                model_spec=conf.fast_model,
                content=text[:500],
                input_tokens=inp,
                output_tokens=outp,
                source="course_query_relevance",
            )
        if _llm_answer_is_no_relevant(text):
            return "off_topic"
        return "allow"
    except Exception as e:
        logger.warning("课程问题相关性检测失败，视为相关: %s", e)
        return "allow"


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

    q_raw = (request.query or "").strip()
    has_image = bool((request.image_content or "").strip())
    if not q_raw and not has_image:
        raise HTTPException(status_code=400, detail="请输入文字问题或上传图片后再发送。")

    # 纯图片时补全默认问法，便于检索与模型理解；有文字时沿用用户原文
    query_for_llm = q_raw or "请结合《计算机网络》课本，说明附图在表达什么、图中各部分含义，并联系课本相关内容。"

    # 带图时跳过纯文本相关性模型（无法看图），视为课程场景内有效提问
    if not has_image:
        relevance = await _classify_course_query_relevance(
            q_raw,
            db=db,
            stats_user_id=current_user.id,
            thread_id=request.thread_id,
        )
        if relevance == "disallowed":
            raise HTTPException(
                status_code=400,
                detail="该问题涉及不当或违规内容，无法作答。",
            )
        if relevance == "off_topic":
            raise HTTPException(
                status_code=400,
                detail="您的问题与《计算机网络》课程内容无关。为节省资源，请仅在此处询问与计算机网络相关的问题（如协议、TCP/IP、HTTP、DNS、SDN、路由、网络安全等）。",
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
    # 已校验 kb_id 必选，检索课本并注入（仅图时用宽泛查询词召回课本摘录）
    retrieval_query = q_raw if q_raw else "计算机网络 协议 体系结构 课本"
    context, book_pages = await _get_course_knowledge_context(
        retrieval_query, kb_id, current_user
    )
    if context:
        config["course_knowledge_context"] = context
    if book_pages:
        config["course_book_pages"] = book_pages
    meta = request.meta or {}
    if "request_id" not in meta or not meta.get("request_id"):
        meta["request_id"] = str(uuid.uuid4())
    meta.update(
        {
            "query": query_for_llm,
            "agent_id": agent_id,
            "thread_id": thread_id,
            "user_id": current_user.id,
            "has_image": has_image,
        }
    )
    # 前端可传 meta.source（如 "reading"），写入对话 metadata，问答页列表会排除 source=reading

    return StreamingResponse(
        stream_agent_chat(
            agent_id=agent_id,
            query=query_for_llm,
            config=config,
            meta=meta,
            image_content=request.image_content.strip() if has_image else None,
            image_mime_type=(request.image_mime_type or "").strip() or None,
            current_user=current_user,
            db=db,
        ),
        media_type="application/json",
    )


# --- 课本列表 ---


@course.get("/books")
def list_books():
    """课本列表：课程资源目录 books 下的 PDF。"""
    items = _list_pdf_books()
    if not items:
        logger.warning(
            "课本列表为空: books_dir=%s is_dir=%s (大文件在仓库外，默认挂载仓库同级 yuxi-knowledgebase)",
            _BOOKS_DIR,
            _BOOKS_DIR.is_dir(),
        )
    return {"books": items}


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


_PAGE_CACHE_DIR = _PROJECT_ROOT / "saves" / "book_page_cache"


def _render_book_page_jpeg(path: Path, page_num: int, *, thumb: bool) -> bytes:
    """渲染一页为 JPEG，并按 PDF mtime 磁盘缓存。thumb 用于封面，避免列表页拉全幅图。"""
    zoom = 0.35 if thumb else 1.4
    quality = 70 if thumb else 78
    tag = "thumb" if thumb else "full"
    safe_stem = re.sub(r"[^A-Za-z0-9._-]", "_", path.stem)
    cache_dir = _PAGE_CACHE_DIR / safe_stem
    cache_file = cache_dir / f"{page_num}_{tag}.jpg"
    try:
        if cache_file.is_file() and cache_file.stat().st_mtime >= path.stat().st_mtime:
            return cache_file.read_bytes()
    except OSError:
        pass
    doc = fitz.open(path)
    try:
        if page_num > len(doc):
            raise HTTPException(status_code=404, detail="页码超出范围")
        page = doc[page_num - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        data = pix.tobytes(output="jpeg", jpg_quality=quality)
    finally:
        doc.close()
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(data)
    except OSError:
        pass
    return data


@course.get("/books/{book_id}/page/{page_num}")
def get_book_page_image(book_id: str, page_num: int, thumb: bool = False):
    """返回指定课本指定页的 JPEG（可缓存）。thumb=1 为封面缩略图。"""
    if page_num < 1:
        raise HTTPException(status_code=400, detail="页码从 1 开始")
    path = _resolve_book_path(book_id)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="课本不存在")
    try:
        data = _render_book_page_jpeg(path, page_num, thumb=thumb)
        return Response(
            content=data,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"无法渲染页面: {e!s}") from e


# --- 课本解析插图（与 md 中 ![](_page_N_...) 同源，不依赖 meta.json 坐标）---


@course.get("/books/{book_id}/figures")
def list_book_extracted_figures(book_id: str):
    """列出 knowledgebase 下该课本对应的 _page_* 插图及伴读页码映射（reader_page = extract_page + 1）。"""
    root = _book_figures_root(book_id)
    if not root:
        return {"figures": []}
    out: list[dict[str, Any]] = []

    def _sort_key(p: Path) -> tuple[int, str]:
        m = _FIGURE_FILENAME_RE.match(p.name)
        if not m:
            return (10**9, p.name)
        return (int(m.group(1)), p.name)

    try:
        for f in sorted(root.iterdir(), key=_sort_key):
            if not f.is_file():
                continue
            m = _FIGURE_FILENAME_RE.match(f.name)
            if not m:
                continue
            extract_page = int(m.group(1))
            stem_part = m.group(2)
            reader_page = extract_page + 1
            label = f"第{reader_page}页 · {stem_part.replace('_', ' ')}"
            out.append(
                {
                    "filename": f.name,
                    "extract_page": extract_page,
                    "reader_page": reader_page,
                    "label": label,
                }
            )
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"无法列出插图: {e!s}") from e
    return {"figures": out}


@course.get("/books/{book_id}/figure")
def get_book_extracted_figure(
    book_id: str,
    name: str = Query(..., description="插图文件名，如 _page_18_Figure_1.jpeg"),
):
    """返回课本解析目录中的单张插图（仅允许 _page_* 白名单文件名）。"""
    if not name or Path(name).name != name or ".." in name:
        raise HTTPException(status_code=400, detail="无效文件名")
    if not _FIGURE_FILENAME_RE.match(name):
        raise HTTPException(status_code=400, detail="非允许的课本插图文件名")
    root = _book_figures_root(book_id)
    if not root:
        raise HTTPException(status_code=404, detail="该课本无解析插图目录")
    path = (root / name).resolve()
    root_r = root.resolve()
    try:
        path.relative_to(root_r)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="插图不存在") from e
    if not path.is_file():
        raise HTTPException(status_code=404, detail="插图不存在")
    lower = name.lower()
    media = "image/png" if lower.endswith(".png") else "image/jpeg"
    return FileResponse(path, media_type=media, filename=name)


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
    前端传入的 (x,y,width,height) 为「页面图片」像素坐标，与 GET /books/{id}/page/{num}
    返回的图片尺寸一致（Matrix 2x），需转换为 PDF 坐标后裁剪。
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

            # 1) PDF 内置文字层（可选中复制的矢量 PDF，无渲染、无模型；扫描页通常为空）
            words = page.get_text("words", clip=clip)
            text = " ".join(w[4] for w in words).strip()
            used_engine: str | None = "pdf_text" if text else None

            # 2) 无文字层时再渲染选区图并走 OCR
            if not text:
                import tempfile

                from src.plugins.document_processor_base import OCRException
                from src.plugins.rapid_ocr_processor import get_course_reading_rapid_ocr_processor

                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip, alpha=False)
                img_bytes = pix.tobytes(output="png")
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp.write(img_bytes)
                    tmp.flush()
                    tmp_path = tmp.name
                try:
                    rapid = get_course_reading_rapid_ocr_processor()
                    rh = rapid.check_health()
                    if rh.get("status") == "healthy":
                        try:
                            text = (rapid.process_file(tmp_path) or "").strip()
                            if text:
                                used_engine = "rapid_ocr"
                        except OCRException as e:
                            if course_reading_paddle_ocr_enabled():
                                logger.warning("课本伴读 RapidOCR 失败，将尝试 PaddleOCR: {}", e)
                            else:
                                logger.warning("课本伴读 RapidOCR 失败: {}", e)
                    else:
                        if course_reading_paddle_ocr_enabled():
                            logger.info(
                                "课本伴读 RapidOCR 不可用: {}，将尝试 PaddleOCR",
                                rh.get("message"),
                            )
                        else:
                            logger.info("课本伴读 RapidOCR 不可用: {}", rh.get("message"))

                    if not text and course_reading_paddle_ocr_enabled():
                        from src.plugins.paddle_ocr_processor import get_course_reading_ocr_processor

                        paddle = get_course_reading_ocr_processor()
                        ph = paddle.check_health()
                        if ph.get("status") == "healthy":
                            try:
                                t2 = (paddle.process_file(tmp_path) or "").strip()
                                if t2:
                                    text = t2
                                    used_engine = "paddle_ocr"
                            except OCRException as e:
                                logger.warning("课本伴读 PaddleOCR 失败: {}", e)
                        else:
                            logger.info("课本伴读 PaddleOCR 不可用: {}", ph.get("message"))
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

            if text and used_engine:
                logger.info("课本伴读选区文本来源 {}，共 {} 字", used_engine, len(text))
            elif used_engine in ("rapid_ocr", "paddle_ocr"):
                logger.info("课本伴读 OCR 使用 {}，未识别到文本", used_engine)

            return {"success": True, "text": text}
        finally:
            doc.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("课本伴读 OCR 未捕获异常: {}", e)
        raise HTTPException(status_code=500, detail=f"OCR 失败: {e!s}") from e


# --- 课本伴读选区翻译（英译汉，不落库）---


class TranslateRequest(BaseModel):
    text: str


@course.post("/translate")
async def translate_text(
    body: TranslateRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
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
        inp, outp = extract_usage_from_lc_response(resp)
        await log_course_aux_llm_call(
            db,
            user_int_id=current_user.id,
            agent_id=COURSE_TRANSLATE_AGENT_ID,
            model_spec=conf.fast_model,
            content=translated,
            input_tokens=inp,
            output_tokens=outp,
            source="course_reading_translate",
        )
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
    question_type: str  # choice / multi_choice / short_answer / calculation
    knowledge_point: str
    chapter: int | None = None  # 章号 1–8，与 knowledge_point 一起时结合课本出题
    section_id: str | None = None  # 小节 id 如 "1.1"，不填则用整章


@course.post("/exercises/generate")
async def exercises_generate(
    body: ExerciseGenerateRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """根据题型和知识点生成一道题（不落库，提交答案时再记录）；可选章节时结合课本内容出题。"""
    if body.question_type not in _EXERCISE_QUESTION_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的题型：{body.question_type}")
    try:
        out = await generate_question(
            body.question_type,
            body.knowledge_point,
            chapter=body.chapter,
            section_id=body.section_id,
            db=db,
            stats_user_id=current_user.id,
        )
        return out
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class ExerciseQuizGenerateRequest(BaseModel):
    chapter: int  # 章号 1–8
    question_type_counts: dict[str, int]  # {"choice": 2, "multi_choice": 1, ...}
    knowledge_point_ids: list[str] = []  # 空表示使用该章节全部知识点


async def _build_exercise_quiz_plan(
    body: ExerciseQuizGenerateRequest,
    current_user: User,
    db: AsyncSession,
) -> list[dict[str, Any]]:
    """
    小测抽题位（题型 + 知识点），不调用 LLM。
    与 generate-quiz 相同的 Thompson Sampling 抽样逻辑，供前端逐题调用 /exercises/generate。
    """
    question_sequence: list[str] = []
    for q_type, count in (body.question_type_counts or {}).items():
        if q_type not in _EXERCISE_QUESTION_TYPES:
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

    q_stats = (
        select(
            ExerciseAttempt.knowledge_point,
            ExerciseAttempt.is_correct,
            ExerciseAttempt.created_at,
        )
        .where(
            ExerciseAttempt.user_id == current_user.id,
            ExerciseAttempt.chapter == str(body.chapter),
            ExerciseAttempt.knowledge_point.in_(eligible_titles),
        )
    )
    result = await db.execute(q_stats)
    stat_rows = result.all()
    wrong_cnt_by_title: dict[str, float] = {}
    correct_cnt_by_title: dict[str, float] = {}
    now = utc_now_naive()
    half_life = max(1.0, float(_EXERCISE_TS_HALF_LIFE_DAYS))
    decay_lambda = math.log(2.0) / half_life
    for row in stat_rows:
        title = str(row[0] or "").strip() or "未分类"
        is_correct = int(row[1] or 0)
        created_at = row[2]
        if created_at is None:
            decay_weight = 1.0
        else:
            delta_days = max(0.0, (now - created_at).total_seconds() / 86400.0)
            decay_weight = math.exp(-decay_lambda * delta_days)
        if is_correct == 1:
            correct_cnt_by_title[title] = correct_cnt_by_title.get(title, 0.0) + decay_weight
        else:
            wrong_cnt_by_title[title] = wrong_cnt_by_title.get(title, 0.0) + decay_weight

    plan: list[dict[str, Any]] = []
    remaining_kps = eligible_kps[:]
    for q_type in question_sequence:
        if not remaining_kps:
            remaining_kps = eligible_kps[:]
        kp = max(
            remaining_kps,
            key=lambda item: _sample_kp_score_with_thompson(
                min(
                    wrong_cnt_by_title.get(str(item.get("title") or "").strip() or "未分类", 0.0),
                    _EXERCISE_TS_DECAY_COUNT_CAP,
                ),
                min(
                    correct_cnt_by_title.get(str(item.get("title") or "").strip() or "未分类", 0.0),
                    _EXERCISE_TS_DECAY_COUNT_CAP,
                ),
            ),
        )
        remaining_kps = [item for item in remaining_kps if str(item.get("id")) != str(kp.get("id"))]
        plan.append(
            {
                "question_type": q_type,
                "knowledge_point": kp.get("title") or "",
                "knowledge_point_id": kp.get("id"),
                "section_id": kp.get("section_id"),
            }
        )
    return plan


@course.post("/exercises/quiz-plan")
async def exercises_quiz_plan(
    body: ExerciseQuizGenerateRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """返回小测题位（题型 + 知识点），不生成题干；前端可逐题 POST /exercises/generate 以边生成边展示。"""
    plan = await _build_exercise_quiz_plan(body, current_user, db)
    return {"plan": plan}


@course.post("/exercises/generate-quiz")
async def exercises_generate_quiz(
    body: ExerciseQuizGenerateRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """生成小测：一次生成多题（多种题型 + 数量）。知识点支持可选集合；未选时默认个性化抽取。"""

    slots = await _build_exercise_quiz_plan(body, current_user, db)

    questions: list[dict] = []
    for slot in slots:
        out = await generate_question(
            slot["question_type"],
            slot["knowledge_point"],
            chapter=body.chapter,
            section_id=slot.get("section_id"),
            db=db,
            stats_user_id=current_user.id,
        )
        out["knowledge_point_id"] = slot["knowledge_point_id"]
        out["knowledge_point"] = slot["knowledge_point"]
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
            db=db,
            stats_user_id=current_user.id,
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
