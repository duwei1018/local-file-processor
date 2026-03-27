from __future__ import annotations

from typing import Callable, Optional


_DEFAULT_PROMPT = """请对以下文档内容进行摘要，要求：
1. 摘要长度不超过 {max_length} 字
2. 保留核心要点和关键信息
3. 使用简洁清晰的语言
4. 直接输出摘要内容，不需要任何标题或说明

文档标题：{title}
文档内容：
{content}"""


def summarize_document(
    content: str,
    title: str = "",
    max_length: int = 500,
    client: Optional[Callable] = None,
    model: str = "moonshot-v1-32k",
    prompt_template: Optional[str] = None,
) -> str:
    if client is None:
        return content[:max_length]

    tmpl = prompt_template or _DEFAULT_PROMPT
    prompt = tmpl.format(
        title=title or "无标题",
        content=content[:6000],
        max_length=max_length,
    )

    try:
        summary = client(prompt, model)
        return (summary or "").strip()
    except Exception as e:
        return content[:max_length]
