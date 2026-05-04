"""
根据 knowledgebase/videos/caption 下的字幕 JSON，调用智能体生成分段总结，
写入 knowledgebase/videos/summary/{video_id}.json，供前端「总结视频」使用。

用法（在项目根目录，建议在 api 容器内执行）：
  uv run python scripts/generate_video_summaries.py
  uv run python scripts/generate_video_summaries.py Review   # 仅处理指定 video_id（可多个）
  docker compose exec api uv run python scripts/generate_video_summaries.py
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path

# 确保可导入 src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage

from src import config as conf
from src.agents.common import load_chat_model
from src.utils import logger

_KNOWLEDGEBASE_DIR = Path(os.environ.get("KNOWLEDGEBASE_DIR", "knowledgebase")).resolve()
_CAPTION_DIR = _KNOWLEDGEBASE_DIR / "videos" / "caption"
_SUMMARY_DIR = _KNOWLEDGEBASE_DIR / "videos" / "summary"

# 匹配 "0:00~1:30 知识点" 或 "0:00 ~ 1:30 知识点"
SEGMENT_LINE_RE = re.compile(r"^\s*(\d+):(\d+)\s*~\s*(\d+):(\d+)\s+(.+)$", re.MULTILINE)


def _ms_to_mmss(ms: int) -> str:
    s = max(0, ms // 1000)
    m = s // 60
    s = s % 60
    return f"{m}:{s:02d}"


def _build_caption_text(caption: dict) -> str:
    """从 sentence_timestamps 生成带时间前缀的文本，便于模型分段。"""
    parts = []
    for seg in caption.get("sentence_timestamps") or []:
        start = int(seg.get("start") or 0)
        text = (seg.get("text") or "").strip()
        if text:
            parts.append(f"{_ms_to_mmss(start)} {text}")
    return "\n".join(parts) if parts else (caption.get("text") or "")


def _parse_segment_lines(text: str) -> list[dict]:
    """解析模型输出的「开始~结束 标题」行，返回 [{"start_sec", "end_sec", "title"}, ...]。"""
    segments = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = SEGMENT_LINE_RE.match(line)
        if m:
            m1, s1, m2, s2, title = m.groups()
            start_sec = int(m1) * 60 + int(s1)
            end_sec = int(m2) * 60 + int(s2)
            if end_sec <= start_sec:
                end_sec = start_sec + 1
            segments.append(
                {
                    "start_sec": start_sec,
                    "end_sec": end_sec,
                    "title": title.strip(),
                }
            )
    return _merge_segments_to_limit(segments, max_segments=20)


def _merge_segments_to_limit(segments: list[dict], max_segments: int = 20) -> list[dict]:
    """若分段过多则合并相邻段，使总数不超过 max_segments。"""
    if len(segments) <= max_segments:
        return segments
    n = (len(segments) + max_segments - 1) // max_segments
    merged = []
    for i in range(0, len(segments), n):
        chunk = segments[i : i + n]
        merged.append(
            {
                "start_sec": chunk[0]["start_sec"],
                "end_sec": chunk[-1]["end_sec"],
                "title": chunk[0]["title"],
            }
        )
    return merged


async def generate_summary_for_caption(video_id: str, caption_path: Path, model) -> list[dict] | None:
    """对单个字幕文件调用模型生成分段总结。"""
    with open(caption_path, encoding="utf-8") as f:
        caption = json.load(f)
    caption_text = _build_caption_text(caption)
    if not caption_text or len(caption_text) > 120000:
        logger.warning("字幕为空或过长，跳过 %s", video_id)
        return None

    system_prompt = """你是一个视频课程助手。根据以下视频字幕（每行前为 分:秒 时间），生成分段知识点总结。
要求：
- 段落不要过多，整段视频控制在约 10～20 段为宜，每段约 3～8 分钟，把相邻的小知识点合并成一段。
- 每段一行，格式严格为：开始时间~结束时间 知识点摘要。例如：0:00~5:30 绪论与Internet基本概念。
- 时间格式为 分:秒（如 5:30 表示 5 分 30 秒）。
- 只输出这些行，不要其他说明、不要编号、不要 markdown。"""

    user_content = f"视频：{video_id}\n\n字幕（时间 句子）：\n{caption_text[:100000]}"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    try:
        resp = await model.ainvoke(messages)
        out = (resp.content if hasattr(resp, "content") else str(resp)) or ""
        segments = _parse_segment_lines(out)
        if not segments:
            logger.warning("未解析到分段：%s", video_id)
            return None
        return segments
    except Exception as e:
        logger.exception("生成总结失败 %s: %s", video_id, e)
        return None


# 非单视频字幕的汇总文件，跳过
_CAPTION_SKIP_NAMES = frozenset({"all_results.json"})


async def main():
    if not _CAPTION_DIR.is_dir():
        logger.error("字幕目录不存在: %s", _CAPTION_DIR)
        return
    _SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    argv_ids = [a.strip() for a in sys.argv[1:] if a.strip()]
    if argv_ids:
        caption_files = []
        for vid in argv_ids:
            p = _CAPTION_DIR / f"{vid}.json"
            if p.is_file():
                caption_files.append(p)
            else:
                logger.warning("未找到字幕文件: %s", p)
        if not caption_files:
            logger.error("没有可处理的字幕文件")
            return
    else:
        caption_files = sorted(
            p
            for p in _CAPTION_DIR.glob("*.json")
            if p.name not in _CAPTION_SKIP_NAMES
        )
    if not caption_files:
        logger.info("未找到字幕文件: %s", _CAPTION_DIR)
        return

    model = load_chat_model(conf.fast_model)
    for caption_path in sorted(caption_files):
        video_id = caption_path.stem
        out_path = _SUMMARY_DIR / f"{video_id}.json"
        logger.info("处理: %s -> %s", video_id, out_path.name)
        segments = await generate_summary_for_caption(video_id, caption_path, model)
        if segments:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump({"segments": segments}, f, ensure_ascii=False, indent=2)
            logger.info("已写入 %d 段: %s", len(segments), out_path)
        else:
            logger.warning("跳过（无有效分段）: %s", video_id)


if __name__ == "__main__":
    asyncio.run(main())
