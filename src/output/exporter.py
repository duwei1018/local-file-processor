from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


def _safe_filename(name: str) -> str:
    name = re.sub(r'[/\\:*?"<>|]', "_", name)
    return name.strip()[:100]


def _frontmatter(meta: Dict[str, Any]) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        elif isinstance(v, str) and "\n" in v:
            lines.append(f'{k}: |')
            for line in v.splitlines():
                lines.append(f"  {line}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


class FileExporter:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export_document(
        self,
        title: str,
        content: str,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        structured_data: Optional[Dict[str, Any]] = None,
        folder: Optional[str] = None,
    ) -> str:
        target_dir = os.path.join(self.output_dir, folder) if folder else self.output_dir
        os.makedirs(target_dir, exist_ok=True)

        fm_data: Dict[str, Any] = {"title": title}
        if tags:
            fm_data["tags"] = tags
        if metadata:
            for k in ("file_type", "file_path", "author", "page_count"):
                if metadata.get(k):
                    fm_data[k] = metadata[k]
        fm_data["processed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        sections = [_frontmatter(fm_data), f"\n# {title}\n"]

        if summary:
            sections.append("## 摘要\n")
            sections.append(summary + "\n")

        if structured_data:
            sections.append("\n## 结构化信息\n")
            sections.append("```json")
            sections.append(json.dumps(structured_data, ensure_ascii=False, indent=2))
            sections.append("```\n")

        sections.append("\n## 原文内容\n")
        sections.append(content)

        filename = _safe_filename(title) + ".md"
        filepath = os.path.join(target_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(sections))

        return filepath

    def export_from_store(self, store, limit: int = 50) -> List[str]:
        docs = store.list_documents(limit=limit)
        paths = []
        for doc in docs:
            try:
                meta = json.loads(doc.get("metadata") or "{}")
                tags_raw = doc.get("tags") or "[]"
                tags = json.loads(tags_raw) if isinstance(tags_raw, str) else tags_raw

                path = self.export_document(
                    title=doc.get("title", "Untitled"),
                    content=doc.get("content", ""),
                    summary=doc.get("summary"),
                    tags=tags,
                    metadata={
                        "file_type": doc.get("file_type"),
                        "file_path": doc.get("file_path"),
                        "author": doc.get("author"),
                        "page_count": meta.get("page_count"),
                    },
                    folder=doc.get("file_type") or "other",
                )
                paths.append(path)
                print(f"  [export] {doc.get('title', 'Untitled')} → {path}")
            except Exception as e:
                print(f"  [export error] doc_id={doc.get('id')}: {e}")
        return paths
