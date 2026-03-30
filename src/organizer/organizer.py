"""FileOrganizer — copy or move files into categorized subdirectories.

Two organization modes:
  by-type      group files by extension (.pdf / .docx / .md / .txt / other)
  by-category  group files by content category (rule-based or LLM)

Within each category folder an optional sub-level by extension is created
when ``subdir_by_type=True``.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .rule_classifier import RuleClassifier, CATEGORIES

# Supported file extensions (same as the parsers)
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}

# Map extension → friendly folder name used in by-type mode
_EXT_FOLDER: dict[str, str] = {
    ".pdf":  "PDF文档",
    ".docx": "Word文档",
    ".md":   "Markdown文档",
    ".txt":  "纯文本",
}


@dataclass
class OrganizeResult:
    src: str
    dst: str
    category: str
    moved: bool          # True = moved, False = copied
    success: bool
    error: str = ""


@dataclass
class OrganizeSummary:
    results: List[OrganizeResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failed(self) -> int:
        return self.total - self.succeeded

    def by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.results:
            counts[r.category] = counts.get(r.category, 0) + 1
        return dict(sorted(counts.items()))


class FileOrganizer:
    """Organize files from a source directory into a structured output directory.

    Args:
        output_dir:       Root destination directory.
        mode:             ``"by-type"`` or ``"by-category"``.
        subdir_by_type:   When mode is ``"by-category"``, also create an
                          extension sub-folder inside each category folder.
        action:           ``"copy"`` (default, safe) or ``"move"``.
        recursive:        Walk source directory recursively.
        extensions:       Whitelist of extensions to process (default: all 4).
        llm_classify_fn:  Optional callable ``(content, title, file_type) -> dict``
                          matching the signature of ``classify_file`` in
                          ``src/intelligence/classifier.py``. When provided,
                          LLM classification is used instead of rule-based.
        llm_client:       LLM client passed through to ``llm_classify_fn``.
        llm_model:        Model name passed through to ``llm_classify_fn``.
    """

    def __init__(
        self,
        output_dir: str,
        mode: str = "by-category",
        subdir_by_type: bool = False,
        action: str = "copy",
        recursive: bool = True,
        extensions: Optional[List[str]] = None,
        llm_classify_fn: Optional[Callable] = None,
        llm_client=None,
        llm_model: str = "moonshot-v1-8k",
    ):
        self.output_dir = os.path.abspath(output_dir)
        self.mode = mode
        self.subdir_by_type = subdir_by_type
        self.action = action
        self.recursive = recursive
        self.exts = {
            e.lower() if e.startswith(".") else f".{e.lower()}"
            for e in (extensions or list(SUPPORTED_EXTENSIONS))
        }
        self.rule_clf = RuleClassifier()
        self.llm_classify_fn = llm_classify_fn
        self.llm_client = llm_client
        self.llm_model = llm_model

    # ── public API ────────────────────────────────────────────────────────────

    def organize_directory(self, src_dir: str) -> OrganizeSummary:
        """Organize all matching files from ``src_dir``."""
        src_dir = os.path.abspath(src_dir)
        summary = OrganizeSummary()

        for root, dirs, files in os.walk(src_dir):
            # Skip the output directory itself to avoid recursive loops
            if os.path.abspath(root).startswith(self.output_dir):
                continue
            dirs.sort()
            for fname in sorted(files):
                ext = os.path.splitext(fname)[1].lower()
                if ext not in self.exts:
                    continue
                src_path = os.path.join(root, fname)
                result = self.organize_file(src_path)
                summary.results.append(result)
            if not self.recursive:
                break

        return summary

    def organize_file(self, src_path: str) -> OrganizeResult:
        """Classify and place a single file."""
        src_path = os.path.abspath(src_path)
        ext = os.path.splitext(src_path)[1].lower()

        try:
            category = self._classify(src_path)
            dst_dir = self._destination_dir(category, ext)
            os.makedirs(dst_dir, exist_ok=True)

            dst_path = self._unique_path(dst_dir, os.path.basename(src_path))

            if self.action == "move":
                shutil.move(src_path, dst_path)
                moved = True
            else:
                shutil.copy2(src_path, dst_path)
                moved = False

            return OrganizeResult(
                src=src_path, dst=dst_path,
                category=category, moved=moved, success=True,
            )
        except Exception as e:
            return OrganizeResult(
                src=src_path, dst="",
                category="其他", moved=False,
                success=False, error=str(e),
            )

    # ── internal ──────────────────────────────────────────────────────────────

    def _classify(self, file_path: str) -> str:
        if self.mode == "by-type":
            ext = os.path.splitext(file_path)[1].lower()
            return _EXT_FOLDER.get(ext, "其他格式")

        # by-category
        if self.llm_classify_fn is not None and self.llm_client is not None:
            return self._classify_llm(file_path)

        return self.rule_clf.classify_file(file_path)

    def _classify_llm(self, file_path: str) -> str:
        try:
            content = self.rule_clf._read_snippet(file_path, 2000)
            title = os.path.splitext(os.path.basename(file_path))[0]
            ext = os.path.splitext(file_path)[1].lstrip(".")
            result = self.llm_classify_fn(
                content, title, ext,
                client=self.llm_client,
                model=self.llm_model,
            )
            cat = result.get("category", "其他")
            # Normalize to known categories
            return cat if cat in CATEGORIES else "其他"
        except Exception:
            return self.rule_clf.classify_file(file_path)

    def _destination_dir(self, category: str, ext: str) -> str:
        base = os.path.join(self.output_dir, category)
        if self.subdir_by_type and self.mode == "by-category":
            sub = _EXT_FOLDER.get(ext, ext.lstrip(".").upper() or "其他格式")
            return os.path.join(base, sub)
        return base

    @staticmethod
    def _unique_path(directory: str, filename: str) -> str:
        """Return a non-conflicting path in directory for filename."""
        dst = os.path.join(directory, filename)
        if not os.path.exists(dst):
            return dst
        stem, ext = os.path.splitext(filename)
        i = 1
        while True:
            candidate = os.path.join(directory, f"{stem}_{i}{ext}")
            if not os.path.exists(candidate):
                return candidate
            i += 1
