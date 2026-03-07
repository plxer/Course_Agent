"""习题生成与批改服务：调用 LLM 出题（含简答得分点）与判题（对/错 + 解析）。"""

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

GENERATE_SYSTEM = """你是一位《计算机网络》课程出题老师。请根据用户选择的题型和知识点，生成一道题目。

要求：
1. 题目内容清晰，难度适中。
2. 若是选择题：给出题目和选项（A/B/C/D），以及正确答案（单字母，如 A）。
3. 若是填空题：给出含空白的题目，以及正确答案（可多个空，用 | 分隔）。
4. 若是简答题：必须设置「得分点」。在输出中列出 scoring_points 数组，每个元素是一条得分要点（关键词或短语），批改时将按是否覆盖这些要点给分。题目和标准答案也要给出。

请严格按以下 JSON 格式输出（不要输出其他内容、不要用 markdown 代码块包裹）：
{"question_type":"choice|fill|short_answer","content":"题目正文","correct_answer":"正确答案","scoring_points":[]}

简答题时 scoring_points 必须为非空数组，例如 ["要点1","要点2"]。选择题和填空题的 scoring_points 为空数组。"""

GRADE_SYSTEM = """你是一位《计算机网络》课程批改老师。根据题目、标准答案、得分点（若有）和用户答案，判断对错并给出解析。

要求：
1. 选择题/填空题：与标准答案一致或等价即为对。
2. 简答题：根据 scoring_points 得分点判断。用户答案若覆盖大部分得分点（核心意思正确）则判对，否则判错。请给出简明解析，指出对错原因。

请严格按以下 JSON 格式输出（不要输出其他内容、不要用 markdown 代码块包裹）：
{"is_correct":1或0,"explanation":"解析内容"}

is_correct 只能是 1（对）或 0（错）。"""


async def generate_question(question_type: str, knowledge_point: str) -> dict:
    """
    根据题型和知识点生成一道题。
    返回 {"content", "correct_answer", "scoring_points": []}，失败抛异常。
    """
    model = load_chat_model(conf.default_model)
    prompt = f"题型：{question_type}，知识点：{knowledge_point}\n请生成一道题。"
    messages = [
        {"role": "system", "content": GENERATE_SYSTEM},
        {"role": "user", "content": prompt},
    ]
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

    return {
        "question_type": q_type,
        "content": content,
        "correct_answer": correct_answer,
        "scoring_points": scoring_points,
    }


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
