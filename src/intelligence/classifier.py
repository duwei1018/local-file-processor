from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, Optional


_DEFAULT_PROMPT = """你是一个文档分类助手。请根据以下文档内容，给出分类结果。

文档标题：{title}
文件类型：{file_type}
文档内容（前2000字）：
{content}

请返回以下 JSON 格式（不要有任何其他文字）：
{{
  "category": "类别名称（如：技术文档、合同协议、财务报告、学术论文、新闻报道、会议记录、说明书、其他）",
  "tags": ["标签1", "标签2", "标签3"],
  "language": "zh 或 en 或 mixed",
  "confidence": 0.9,
  "reason": "一句话说明分类理由"
}}"""


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Extract first JSON block
    m = re.search(r"\{[\s\S]+\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}


def classify_file(
    content: str,
    title: str = "",
    file_type: str = "",
    client: Optional[Callable] = None,
    model: str = "moonshot-v1-8k",
    prompt_template: Optional[str] = None,
) -> Dict[str, Any]:
    if client is None:
        return {"category": "未知", "tags": [], "confidence": 0.0, "reason": "no client"}

    tmpl = prompt_template or _DEFAULT_PROMPT
    prompt = tmpl.format(
        title=title or "无标题",
        file_type=file_type or "unknown",
        content=content[:2000],
    )

    try:
        raw = client(prompt, model)
        result = _extract_json(raw)
        result.setdefault("category", "其他")
        result.setdefault("tags", [])
        result.setdefault("confidence", 0.0)
        return result
    except Exception as e:
        return {"category": "其他", "tags": [], "confidence": 0.0, "error": str(e)}
