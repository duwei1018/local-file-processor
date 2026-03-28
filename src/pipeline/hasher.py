# -*- coding: utf-8 -*-
"""
Content hashing utilities for deduplication.

Provides:
- `normalize_text(text, lowercase=True)`
- `hash_text(text, algorithm='sha256', salt=None, length=None, output='hex')`
- `fingerprint(obj, algorithm='sha256', **hash_kwargs)` accepts str/dict and returns canonical hash

Small CLI for quick checks.
"""
from __future__ import annotations

import hashlib
import base64
import json
import html as _html
import re
from typing import Any, Optional

_RE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+")
_RE_WS = re.compile(r"\s+")


def normalize_text(text: Optional[str], lowercase: bool = True) -> str:
    """Normalize text for stable hashing.

    - Unescape HTML entities
    - Remove control characters
    - Collapse whitespace to single spaces
    - Strip leading/trailing whitespace
    - Optionally lowercase
    """
    if text is None:
        return ""
    s = str(text)
    s = _html.unescape(s)
    s = _RE_CONTROL.sub("", s)
    s = _RE_WS.sub(" ", s).strip()
    if lowercase:
        s = s.lower()
    return s


def hash_text(
    text: Any,
    algorithm: str = "sha256",
    salt: Optional[str] = None,
    length: Optional[int] = None,
    output: str = "hex",
    encoding: str = "utf-8",
) -> str:
    """Compute a stable hash for given text-like input.

    Args:
        text: input (str or bytes or object with __str__)
        algorithm: hashlib algorithm name (e.g., 'sha256', 'sha1')
        salt: optional salt string prepended to input
        length: optional truncation length for the returned string
        output: 'hex' (default) or 'base64' (urlsafe, no padding)
        encoding: encoding used when converting str -> bytes

    Returns:
        hex or base64 urlsafe digest (string)
    """
    if isinstance(text, bytes):
        data = text
    else:
        data = str(text).encode(encoding)

    h = hashlib.new(algorithm)
    if salt:
        h.update(str(salt).encode(encoding))
    h.update(data)
    digest = h.digest()

    if output == "hex":
        out = h.hexdigest()
    elif output == "base64":
        out = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    else:
        raise ValueError("unsupported output format: %r" % (output,))

    if length is not None:
        return out[:length]
    return out


def fingerprint(obj: Any, algorithm: str = "sha256", **hash_kwargs) -> str:
    """Canonicalize `obj` and return its content hash.

    - If `obj` is a dict or list, marshal to compact JSON with sorted keys.
    - Otherwise convert to str.

    hash_kwargs are passed to `hash_text`.
    """
    if isinstance(obj, (dict, list)):
        # canonical JSON: ensure consistent ordering and separators
        canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    else:
        canonical = str(obj)

    # preserve case for structured objects by default; callers can pass lowercase=True when normalizing
    canonical = normalize_text(canonical, lowercase=False)
    return hash_text(canonical, algorithm=algorithm, **hash_kwargs)


__all__ = ["normalize_text", "hash_text", "fingerprint"]


# Simple CLI for quick checks
if __name__ == "__main__":
    import argparse
    from pathlib import Path

    p = argparse.ArgumentParser(description="Compute content hashes for deduplication")
    p.add_argument("--file", "-f", help="file to read and hash")
    p.add_argument("--text", "-t", help="text to hash")
    p.add_argument("--algo", default="sha256", help="hash algorithm (default: sha256)")
    p.add_argument("--base64", dest="base64", action="store_true", help="output base64 urlsafe (no padding)")
    p.add_argument("--length", type=int, help="truncate output to this length")
    args = p.parse_args()

    if args.file:
        data = Path(args.file).read_bytes()
        # hash bytes directly
        out = hash_text(data, algorithm=args.algo, output=("base64" if args.base64 else "hex"), length=args.length)
    else:
        txt = args.text or ""
        out = hash_text(normalize_text(txt), algorithm=args.algo, output=("base64" if args.base64 else "hex"), length=args.length)

    print(out)
