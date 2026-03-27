# -*- coding: utf-8 -*-
"""
HTML and text cleaning utilities for the pipeline.

Provides:
- clean_html(html: str) -> str      # remove scripts/styles/tags, unescape, normalize
- clean_text(text: str) -> str      # normalize whitespace, remove control chars

Designed to avoid external dependencies so it can run in minimal environments.
"""
from __future__ import annotations

import re
import html as _html
from typing import Optional


# Patterns
_RE_SCRIPT_STYLE = re.compile(r"(?is)<(script|style)[^>]*?>.*?</\1>")
_RE_TAGS = re.compile(r"(?s)<[^>]+>")
_RE_BR = re.compile(r"(?i)<br\s*/?>")
_RE_BLOCK_CLOSE = re.compile(r"(?i)</(p|div|li|h[1-6])>")
_RE_WHITESPACE = re.compile(r"[\t\r\n]+")
_RE_COLLAPSE_WS = re.compile(r"[ \u00A0]+")
_RE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+")


def _replace_block_tags_with_newline(html: str) -> str:
    # Convert <br> and block ends to newlines so we can preserve paragraph breaks
    s = _RE_BR.sub("\n", html)
    s = _RE_BLOCK_CLOSE.sub("\n", s)
    return s


def clean_html(html_source: str, keep_linebreaks: bool = True) -> str:
    """Clean an HTML string and return plain text.

    Steps:
    - remove <script> and <style> blocks
    - replace <br> and common block-end tags with newlines
    - strip remaining tags
    - unescape HTML entities
    - remove control characters and normalize whitespace

    Args:
        html_source: raw HTML string
        keep_linebreaks: if True, preserve paragraph/line breaks as newlines

    Returns:
        cleaned plain-text string
    """
    if not html_source:
        return ""

    s = html_source
    # remove script/style content
    s = _RE_SCRIPT_STYLE.sub("", s)
    # replace some block tags with newlines to preserve structure
    if keep_linebreaks:
        s = _replace_block_tags_with_newline(s)
    # remove all tags
    s = _RE_TAGS.sub("", s)
    # unescape html entities
    s = _html.unescape(s)
    # remove control characters except newline and space
    s = _RE_CONTROL.sub("", s)
    # normalize whitespace: convert mixed whitespace to single spaces or newlines
    if keep_linebreaks:
        # collapse runs of whitespace/newline to single newline, then collapse multiple newlines
        s = re.sub(r"\n[ \t\n\r\f\v]*\n+", "\n\n", s)
        # collapse tabs and spaces around newlines
        s = re.sub(r"[ \t]+\n", "\n", s)
        s = re.sub(r"\n[ \t]+", "\n", s)
        # collapse remaining sequences of spaces
        s = _RE_COLLAPSE_WS.sub(" ", s)
    else:
        s = _RE_WHITESPACE.sub(" ", s)
        s = _RE_COLLAPSE_WS.sub(" ", s)

    return s.strip()


def clean_text(text: str, preserve_newlines: bool = False) -> str:
    """Clean plain text by removing control characters and normalizing whitespace.

    Args:
        text: input text
        preserve_newlines: if True, keep newline characters; otherwise collapse to spaces

    Returns:
        cleaned text
    """
    if not text:
        return ""

    s = text
    # unescape any HTML entities that may appear in text
    s = _html.unescape(s)
    # remove control chars
    s = _RE_CONTROL.sub("", s)
    if preserve_newlines:
        # normalize different newline forms, collapse multiple blank lines
        s = s.replace('\r\n', '\n').replace('\r', '\n')
        s = re.sub(r"\n{3,}", "\n\n", s)
        # collapse spaces/tabs
        s = _RE_COLLAPSE_WS.sub(" ", s)
        # remove spaces around newlines
        s = re.sub(r"[ \t]+\n", "\n", s)
        s = re.sub(r"\n[ \t]+", "\n", s)
    else:
        s = _RE_WHITESPACE.sub(" ", s)
        s = _RE_COLLAPSE_WS.sub(" ", s)

    return s.strip()


def normalize_whitespace(text: str) -> str:
    """Utility: collapse multiple spaces and normalize whitespace to single spaces."""
    if not text:
        return ""
    s = _RE_WHITESPACE.sub(" ", text)
    s = _RE_COLLAPSE_WS.sub(" ", s)
    return s.strip()


# Simple CLI/demo usage when run directly
if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Clean HTML or text from stdin or file")
    ap.add_argument("path", nargs="?", help="file path to read (defaults to stdin)")
    ap.add_argument("--html", action="store_true", help="treat input as HTML")
    ap.add_argument("--preserve-newlines", action="store_true", help="preserve newlines in output")
    args = ap.parse_args()

    if args.path:
        data = open(args.path, "r", encoding="utf-8").read()
    else:
        import sys

        data = sys.stdin.read()

    if args.html:
        out = clean_html(data, keep_linebreaks=args.preserve_newlines)
    else:
        out = clean_text(data, preserve_newlines=args.preserve_newlines)

    print(out)
