"""Rule-based file classifier.

Classifies files into categories using filename patterns and content keywords,
without requiring an LLM. Fast and offline-capable.

Categories match the LLM classifier's output categories so results are
interchangeable between the two modes.
"""
from __future__ import annotations

import os
import re
from typing import Optional


# ── category definitions ──────────────────────────────────────────────────────

CATEGORIES = [
    "技术文档",
    "财务报告",
    "合同协议",
    "学术论文",
    "新闻报道",
    "会议记录",
    "说明书",
    "简历",
    "其他",
]

# (category, [filename keywords], [content keywords])
# All keywords are case-insensitive. First matching rule wins.
_RULES: list[tuple[str, list[str], list[str]]] = [
    (
        "财务报告",
        ["财报", "年报", "季报", "financial", "annual report", "earnings", "profit",
         "balance sheet", "income statement", "资产负债", "利润表", "现金流"],
        ["营业收入", "净利润", "毛利率", "每股收益", "资产负债表", "现金流量表",
         "revenue", "net profit", "ebitda", "eps", "dividend", "fiscal year",
         "财务数据", "归母净利润", "经营活动"],
    ),
    (
        "合同协议",
        ["合同", "协议", "agreement", "contract", "mou", "nda", "保密协议",
         "服务协议", "采购合同", "劳动合同", "租赁合同"],
        ["甲方", "乙方", "丙方", "签署", "违约", "赔偿", "签订", "协议书",
         "whereas", "party a", "party b", "hereinafter", "agreement shall",
         "indemnify", "termination", "confidential"],
    ),
    (
        "学术论文",
        ["论文", "paper", "thesis", "dissertation", "研究报告", "report"],
        ["摘要", "abstract", "关键词", "keywords", "参考文献", "references",
         "introduction", "methodology", "conclusion", "doi", "journal",
         "hypothesis", "experiment", "dataset", "peer review",
         "引言", "研究方法", "实验结果", "文献综述"],
    ),
    (
        "新闻报道",
        ["新闻", "news", "报道", "press release", "公告", "通报"],
        ["据报道", "记者", "消息人士", "编辑", "发布", "公告称", "announced",
         "according to", "reported by", "press release", "spokesperson",
         "今日", "昨日", "本报讯"],
    ),
    (
        "会议记录",
        ["会议", "meeting", "minutes", "纪要", "记录", "memo"],
        ["出席", "主持", "议题", "决议", "行动项", "下次会议",
         "attendees", "agenda", "action items", "minutes of", "resolved",
         "moved by", "seconded", "讨论结果", "会议决定"],
    ),
    (
        "说明书",
        ["说明书", "手册", "manual", "guide", "指南", "教程", "tutorial",
         "readme", "quickstart", "操作手册", "用户手册", "产品说明"],
        ["安装步骤", "使用方法", "注意事项", "警告", "installation",
         "getting started", "quick start", "step 1", "step 2",
         "requirements", "prerequisites", "configuration"],
    ),
    (
        "简历",
        ["简历", "resume", "cv", "curriculum vitae", "个人简历"],
        ["工作经历", "教育背景", "技能", "work experience", "education",
         "skills", "objective", "references available", "个人信息",
         "求职意向", "实习经历"],
    ),
    (
        "技术文档",
        ["技术", "technical", "spec", "specification", "架构", "design",
         "api", "接口", "开发", "development", "code", "源码", "实现"],
        ["function", "class", "module", "import", "api", "endpoint",
         "database", "schema", "algorithm", "architecture", "implement",
         "接口文档", "数据结构", "时序图", "流程图", "技术方案"],
    ),
]


class RuleClassifier:
    """Classify a file into a category using filename and content heuristics."""

    def classify_file(
        self,
        file_path: str,
        content: Optional[str] = None,
        read_bytes: int = 1500,
    ) -> str:
        """Return the best-matching category name.

        Args:
            file_path: Path to the file (used for filename-based rules).
            content:   Pre-read text content. If None, the file is opened and
                       the first ``read_bytes`` characters are read.
            read_bytes: How many bytes to read from the file when content is None.
        """
        name = os.path.basename(file_path).lower()
        stem = os.path.splitext(name)[0]

        # Load a snippet of content for keyword matching
        snippet = ""
        if content is not None:
            snippet = content[:read_bytes].lower()
        else:
            try:
                snippet = self._read_snippet(file_path, read_bytes)
            except Exception:
                pass

        return self._match(stem, snippet)

    # ── internal ──────────────────────────────────────────────────────────────

    def _read_snippet(self, file_path: str, read_bytes: int) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".pdf":
                return self._read_pdf_snippet(file_path, read_bytes)
            if ext == ".docx":
                return self._read_docx_snippet(file_path, read_bytes)
            # plain text / markdown
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(read_bytes).lower()
        except Exception:
            return ""

    @staticmethod
    def _read_pdf_snippet(file_path: str, read_bytes: int) -> str:
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += (page.extract_text() or "")
                if len(text) >= read_bytes:
                    break
            return text[:read_bytes].lower()
        except Exception:
            return ""

    @staticmethod
    def _read_docx_snippet(file_path: str, read_bytes: int) -> str:
        try:
            import docx
            doc = docx.Document(file_path)
            parts = []
            for para in doc.paragraphs:
                parts.append(para.text)
                if sum(len(p) for p in parts) >= read_bytes:
                    break
            return " ".join(parts)[:read_bytes].lower()
        except Exception:
            return ""

    @staticmethod
    def _match(name_stem: str, snippet: str) -> str:
        scores: dict[str, int] = {cat: 0 for cat in CATEGORIES}

        for category, name_kws, content_kws in _RULES:
            for kw in name_kws:
                if kw.lower() in name_stem:
                    scores[category] += 3  # filename match weights more
            for kw in content_kws:
                if kw.lower() in snippet:
                    scores[category] += 1

        best_cat = max(scores, key=lambda c: scores[c])
        if scores[best_cat] == 0:
            return "其他"
        return best_cat
