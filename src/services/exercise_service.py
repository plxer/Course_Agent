"""习题生成与批改服务：调用 LLM 出题（含简答得分点）与判题（对/错 + 详细解析），结合课本内容。"""

import json
import re

from src import config as conf
from src.agents.common import load_chat_model
from src.utils.logging_config import logger

QUESTION_TYPES = [
    ("choice", "选择题"),
    ("fill", "填空题"),
    ("short_answer", "简答题"),
]

GENERATE_SYSTEM = """你是一位《计算机网络》课程出题老师。请根据用户选择的题型和知识点，结合提供的课本片段内容出题。

要求：
1. 题目内容清晰，难度适中，必须基于所给课本内容命题，不要脱离课本编造。
2. 若是选择题：content 只写题干（不包含选项）；必须输出 options 数组，包含 4 个选项，格式为 ["A. 选项一内容", "B. 选项二内容", "C. 选项三内容", "D. 选项四内容"]；correct_answer 为单字母 "A"/"B"/"C"/"D"。
3. 若是填空题：给出含空白的题目，以及正确答案（可多个空，用 | 分隔）。
4. 若是简答题：必须设置「得分点」。在输出中列出 scoring_points 数组，每个元素是一条得分要点（关键词或短语），批改时将按是否覆盖这些要点给分。题目和标准答案也要给出。

请严格按以下 JSON 格式输出（不要输出其他内容、不要用 markdown 代码块包裹）：
选择题：{"question_type":"choice","content":"题干（不含选项）","options":["A. ...","B. ...","C. ...","D. ..."],"correct_answer":"A","scoring_points":[]}
填空题/简答题：{"question_type":"fill|short_answer","content":"题目正文","correct_answer":"正确答案","scoring_points":[]}

简答题时 scoring_points 必须为非空数组。选择题和填空题的 scoring_points 为空数组。"""

GRADE_SYSTEM = """你是一位《计算机网络》课程批改老师。根据题目、标准答案、得分点（若有）和用户答案，判断对错并给出详细解析。

要求：
1. 选择题/填空题：与标准答案一致或等价即为对。
2. 简答题：根据 scoring_points 得分点判断。用户答案若覆盖大部分得分点（核心意思正确）则判对，否则判错。
3. 解析必须详细，包含：（1）正确答案是什么；（2）考查的知识点/考点；（3）为什么其他选项错误或常见易错点（若为选择题）；（4）简要延伸或总结。用中文书写，条理清晰。
4. 解析内容可使用 Markdown 格式（如 **加粗**、列表等），便于阅读。

请严格按以下 JSON 格式输出（不要输出其他内容、不要用 markdown 代码块包裹）：
{"is_correct":1或0,"explanation":"详细解析内容"}

is_correct 只能是 1（对）或 0（错）。"""


async def generate_question(
    question_type: str,
    knowledge_point: str,
    chapter: int | str | None = None,
    section_id: str | None = None,
) -> dict:
    """
    根据题型和知识点生成一道题；若提供 chapter/section_id 则结合课本该节内容出题。
    返回 {"content", "correct_answer", "scoring_points": [], "options": []}（选择题含 options），失败抛异常。
    """
    from src.services.textbook_service import get_textbook_excerpt, get_section_title

    textbook_excerpt = ""
    if chapter is not None and str(chapter).strip():
        textbook_excerpt = get_textbook_excerpt(chapter, section_id)
    textbook_used = bool(textbook_excerpt)
    if textbook_used:
        logger.info(
            "出题结合课本 chapter=%s section_id=%s excerpt_len=%d",
            chapter,
            section_id,
            len(textbook_excerpt),
        )
        prompt = f"""题型：{question_type}，知识点：{knowledge_point}

以下为课本中与该知识点相关的内容，请严格基于以下内容出题，不要脱离课本编造。

【课本内容】
{textbook_excerpt}

请生成一道题。"""
    else:
        prompt = f"题型：{question_type}，知识点：{knowledge_point}\n请生成一道题（可参考《计算机网络：自顶向下方法》）。"

    model = load_chat_model(conf.default_model)
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        msg_list = [
            SystemMessage(content=GENERATE_SYSTEM),
            HumanMessage(content=prompt),
        ]
        resp = await model.ainvoke(msg_list)
        text = resp.content if hasattr(resp, "content") else str(resp)
    except Exception as e:
        logger.exception("generate_question LLM call failed: %s", e)
        raise ValueError("出题失败，请稍后重试") from e

    out = _parse_json_from_response(text)
    if not out:
        raise ValueError("出题结果解析失败，请重试")

    q_type = out.get("question_type") or question_type
    content = out.get("content") or ""
    correct_answer = out.get("correct_answer") or ""
    scoring_points = out.get("scoring_points")
    if q_type == "short_answer" and (not scoring_points or not isinstance(scoring_points, list)):
        scoring_points = [correct_answer]
    if not isinstance(scoring_points, list):
        scoring_points = []

    options = out.get("options") if q_type == "choice" else []
    if q_type == "choice" and (not options or not isinstance(options, list)):
        options = []
    if q_type == "choice" and len(options) < 4:
        options = options + [f"{chr(65 + i)}. （未给出）" for i in range(len(options), 4)]

    result = {
        "question_type": q_type,
        "content": content,
        "correct_answer": correct_answer,
        "scoring_points": scoring_points,
        "options": options[:4] if q_type == "choice" else [],
        "textbook_used": textbook_used,
        "excerpt_length": len(textbook_excerpt) if textbook_used else 0,
    }
    if textbook_used and chapter is not None:
        result["chapter"] = int(chapter) if isinstance(chapter, str) else chapter
        result["section_id"] = section_id
        result["section_title"] = get_section_title(section_id)
        result["textbook_excerpt"] = textbook_excerpt[:8000]  # 供前端「详情」展示，截断避免响应过大
    return result


async def grade_answer(
    question_type: str,
    question_content: str,
    correct_answer: str,
    scoring_points: list,
    user_answer: str,
) -> dict:
    """
    批改用户答案。返回 {"is_correct": 0|1, "explanation": "..."}。
    """
    model = load_chat_model(conf.default_model)
    sp_str = json.dumps(scoring_points, ensure_ascii=False) if scoring_points else "[]"
    prompt = f"""题目类型：{question_type}
题目内容：{question_content}
标准答案：{correct_answer}
得分点（简答题用）：{sp_str}
用户答案：{user_answer}

请判断对错并给出解析。"""

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        msg_list = [
            SystemMessage(content=GRADE_SYSTEM),
            HumanMessage(content=prompt),
        ]
        resp = await model.ainvoke(msg_list)
        text = resp.content if hasattr(resp, "content") else str(resp)
    except Exception as e:
        logger.exception("grade_answer LLM call failed: %s", e)
        raise ValueError("批改失败，请稍后重试") from e

    out = _parse_json_from_response(text)
    if not out:
        raise ValueError("批改结果解析失败，请重试")

    is_correct = out.get("is_correct", 0)
    if is_correct not in (0, 1):
        is_correct = 1 if is_correct else 0
    explanation = out.get("explanation") or ""

    return {"is_correct": int(is_correct), "explanation": explanation}


def _parse_json_from_response(text: str) -> dict | None:
    """从 LLM 回复中提取 JSON 对象。"""
    if not text or not text.strip():
        return None
    text = text.strip()
    # 去掉可能的 markdown 代码块
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        text = m.group(1)
    else:
        start = text.find("{")
        if start >= 0:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        text = text[start : i + 1]
                        break
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
