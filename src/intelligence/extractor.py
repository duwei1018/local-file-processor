from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, Optional


_DEFAULT_SCHEMA_HINT = """请提取以下字段（如果存在）：
- date: 文档日期或创建时间
- author: 作者或机构
- key_entities: 关键人名、公司名、地名等（列表）
- key_topics: 主要话题或主题（列表）
- action_items: 待办事项或行动计划（列表）
- financial_figures: 财务数据或金额（列表）
- conclusions: 主要结论或决定（列表）"""

_DEFAULT_PROMPT = """你是一个结构化信息提取助手。请从以下文档中提取关键结构化信息。

文档标题：{title}
文档内容（前3000字）：
{content}

提取要求：
{schema_hint}

请以 JSON 格式返回提取结果（不要有任何其他文字，字段值为空时使用 null 或空列表）："""


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]+\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}


def extract_structured_data(
    content: str,
    title: str = "",
    schema_hint: str = "",
    client: Optional[Callable] = None,
    model: str = "moonshot-v1-32k",
) -> Dict[str, Any]:
    if client is None:
        return {}

    prompt = _DEFAULT_PROMPT.format(
        title=title or "无标题",
        content=content[:3000],
        schema_hint=schema_hint or _DEFAULT_SCHEMA_HINT,
    )

    try:
        raw = client(prompt, model)
        return _extract_json(raw)
    except Exception as e:
        return {"error": str(e)}
