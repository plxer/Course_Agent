"""习题生成与批改服务：调用 LLM 出题（含简答得分点）与判题（对/错 + 详细解析），结合课本内容。"""

import json
import re

from sqlalchemy.ext.asyncio import AsyncSession

from src import config as conf
from src.agents.common import load_chat_model
from src.utils.logging_config import logger

QUESTION_TYPES = [
    ("choice", "单选题"),
    ("multi_choice", "多选题"),
    ("short_answer", "简答题"),
    ("calculation", "计算题"),
]

QUESTION_TYPE_LABELS = dict(QUESTION_TYPES)

GENERATE_SYSTEM = """你是一位《计算机网络》课程出题老师。请根据用户选择的题型和知识点，结合提供的课本片段内容出题。

要求：
1. 题目内容清晰，难度适中，必须基于所给课本内容命题，不要脱离课本编造。
2. 若是单选题：content 只写题干（不包含选项）；必须输出 options 数组，包含 4 个选项，格式为 ["A. 选项一内容", "B. 选项二内容", "C. 选项三内容", "D. 选项四内容"]；correct_answer 为单字母 "A"/"B"/"C"/"D"。
3. 若是多选题：content 只写题干；options 同上 4 个选项；必须有至少 2 个正确选项；correct_answer 为逗号分隔的大写字母且按字母序排列，例如 "A,C" 或 "B,C,D"（仅含 A–D）。
4. 若是简答题：必须设置「得分点」。在输出中列出 scoring_points 数组，每个元素是一条得分要点（关键词或短语），批改时将按是否覆盖这些要点给分。题目和标准答案也要给出。
5. 若是计算题：给出需计算或推导的题目，correct_answer 写明标准数值或表达式结果（可含简要单位）；以计算过程与结果为主，scoring_points 可为空数组。

请严格按以下 JSON 格式输出（不要输出其他内容、不要用 markdown 代码块包裹）：
单选题：{"question_type":"choice","content":"题干（不含选项）","options":["A. ...","B. ...","C. ...","D. ..."],"correct_answer":"A","scoring_points":[]}
多选题：{"question_type":"multi_choice","content":"题干（不含选项）","options":["A. ...","B. ...","C. ...","D. ..."],"correct_answer":"A,C","scoring_points":[]}
简答题：{"question_type":"short_answer","content":"题目正文","correct_answer":"参考答案","scoring_points":["要点1","要点2"]}
计算题：{"question_type":"calculation","content":"题目正文","correct_answer":"标准结果","scoring_points":[]}

简答题时 scoring_points 必须为非空数组。单选题、多选题的 scoring_points 为空数组。计算题的 scoring_points 可为空数组。"""

GRADE_SYSTEM = """你是一位《计算机网络》课程批改老师。根据题目、标准答案、得分点（若有）和用户答案，判断对错并给出详细解析。

要求：
1. 单选题：与标准答案一致或等价即为对。
2. 多选题：将标准答案与用户答案均视为选项字母集合（忽略顺序、大小写）；两者集合完全一致则判对，否则判错。
3. 简答题：根据 scoring_points 得分点判断。用户答案若覆盖大部分得分点（核心意思正确）则判对，否则判错。
4. 计算题：用户答案的数值或结论与标准答案在数学上等价或合理近似（考虑单位与有效数字）则判对，否则判错。
5. 解析必须详细，包含：（1）正确答案是什么；（2）考查的知识点/考点；（3）为什么其他选项错误或常见易错点（若为单选题或多选题）；（4）简要延伸或总结。用中文书写，条理清晰。
6. 解析内容可使用 Markdown 格式（如 **加粗**、列表等），便于阅读。

请严格按以下 JSON 格式输出（不要输出其他内容、不要用 markdown 代码块包裹）：
{"is_correct":1或0,"explanation":"详细解析内容"}

is_correct 只能是 1（对）或 0（错）。"""


async def generate_question(
    question_type: str,
    knowledge_point: str,
    chapter: int | str | None = None,
    section_id: str | None = None,
    db: AsyncSession | None = None,
    stats_user_id: int | None = None,
) -> dict:
    """
    根据题型和知识点生成一道题；若提供 chapter/section_id 则结合课本该节内容出题。
    返回 {"content", "correct_answer", "scoring_points": [], "options": []}（单选题含 options），失败抛异常。
    """
    from src.services.textbook_service import get_section_title, get_textbook_excerpt

    textbook_excerpt = ""
    if chapter is not None and str(chapter).strip():
        textbook_excerpt = get_textbook_excerpt(chapter, section_id)
    textbook_used = bool(textbook_excerpt)
    type_label = QUESTION_TYPE_LABELS.get(question_type, question_type)
    if textbook_used:
        logger.info(
            "出题结合课本 chapter={} section_id={} excerpt_len={}",
            chapter,
            section_id,
            len(textbook_excerpt),
        )
        prompt = f"""题型：{type_label}，知识点：{knowledge_point}

以下为课本中与该知识点相关的内容，请严格基于以下内容出题，不要脱离课本编造。

【课本内容】
{textbook_excerpt}

请生成一道题。"""
    else:
        prompt = f"题型：{type_label}，知识点：{knowledge_point}\n请生成一道题（可参考《计算机网络：自顶向下方法》）。"

    model = load_chat_model(conf.default_model)
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        msg_list = [
            SystemMessage(content=GENERATE_SYSTEM),
            HumanMessage(content=prompt),
        ]
        resp = await model.ainvoke(msg_list)
        text = resp.content if hasattr(resp, "content") else str(resp)
        if db is not None and stats_user_id is not None:
            from src.services.llm_usage_log_service import (
                COURSE_EXERCISE_AGENT_ID,
                extract_usage_from_lc_response,
                log_course_aux_llm_call,
            )

            inp, outp = extract_usage_from_lc_response(resp)
            await log_course_aux_llm_call(
                db,
                user_int_id=stats_user_id,
                agent_id=COURSE_EXERCISE_AGENT_ID,
                model_spec=conf.default_model,
                content=str(text)[:2000],
                input_tokens=inp,
                output_tokens=outp,
                source="exercise_generate",
            )
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
    if q_type == "calculation" and not isinstance(scoring_points, list):
        scoring_points = []
    if not isinstance(scoring_points, list):
        scoring_points = []

    options = out.get("options") if q_type in ("choice", "multi_choice") else []
    if q_type in ("choice", "multi_choice") and (not options or not isinstance(options, list)):
        options = []
    if q_type in ("choice", "multi_choice") and len(options) < 4:
        options = options + [f"{chr(65 + i)}. （未给出）" for i in range(len(options), 4)]

    if q_type == "multi_choice":
        correct_answer = _normalize_multi_choice_answer(correct_answer)

    result = {
        "question_type": q_type,
        "content": content,
        "correct_answer": correct_answer,
        "scoring_points": scoring_points,
        "options": options[:4] if q_type in ("choice", "multi_choice") else [],
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
    db: AsyncSession | None = None,
    stats_user_id: int | None = None,
) -> dict:
    """
    批改用户答案。返回 {"is_correct": 0|1, "explanation": "..."}。
    """
    model = load_chat_model(conf.default_model)
    sp_str = json.dumps(scoring_points, ensure_ascii=False) if scoring_points else "[]"
    type_label = QUESTION_TYPE_LABELS.get(question_type, question_type)
    prompt = f"""题目类型：{type_label}
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
        if db is not None and stats_user_id is not None:
            from src.services.llm_usage_log_service import (
                COURSE_EXERCISE_AGENT_ID,
                extract_usage_from_lc_response,
                log_course_aux_llm_call,
            )

            inp, outp = extract_usage_from_lc_response(resp)
            await log_course_aux_llm_call(
                db,
                user_int_id=stats_user_id,
                agent_id=COURSE_EXERCISE_AGENT_ID,
                model_spec=conf.default_model,
                content=str(text)[:2000],
                input_tokens=inp,
                output_tokens=outp,
                source="exercise_grade",
            )
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


def _normalize_multi_choice_answer(raw: str) -> str:
    letters = re.findall(r"[A-D]", str(raw).upper())
    return ",".join(sorted(set(letters)))


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
