#!/usr/bin/env python3
"""local-file-processor — CLI entry point."""

from __future__ import annotations

import os
import sys

import click
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── output directory helpers ──────────────────────────────────────────────────

_PRIMARY_OUT = os.environ.get(
    "OUTPUT_DIR",
    os.path.expanduser("~/Desktop/local-file-processor output"),
)
_NAS_OUT = os.environ.get(
    "OUTPUT_DIR_NAS",
    os.path.expanduser(
        "~/Library/CloudStorage/SynologyDrive-duwei/行业研究/local-file-processor output"
    ),
)


def _sync_to_nas(src_dir: str, dst_dir: str) -> None:
    """Mirror src_dir → dst_dir using rsync (best-effort, never fails loudly)."""
    import subprocess
    try:
        if not os.path.isdir(src_dir):
            return
        os.makedirs(dst_dir, exist_ok=True)
        result = subprocess.run(
            ["rsync", "-a", "--delete", f"{src_dir}/", f"{dst_dir}/"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            click.echo(f"[sync] NAS updated: {dst_dir}")
        else:
            click.echo(f"[sync] rsync warning: {result.stderr.strip()[:120]}", err=True)
    except FileNotFoundError:
        click.echo("[sync] rsync not found — skipping NAS sync", err=True)
    except Exception as e:
        click.echo(f"[sync] NAS sync failed: {e}", err=True)


def _db_path(ctx_obj: dict) -> str:
    return ctx_obj.get("db_path") or os.environ.get("DB_PATH", "db/local_files.duckdb")


def _get_store(db_path: str):
    from src.pipeline.store import DuckDBStore
    return DuckDBStore(db_path)


def _get_ingestor(db_path: str):
    from src.pipeline.ingest import FileIngestor
    return FileIngestor(db_path)


def _get_llm_client():
    from src.intelligence.client import make_client_from_env
    try:
        return make_client_from_env()
    except ValueError as e:
        click.echo(f"[error] {e}", err=True)
        sys.exit(1)


def _get_embedder():
    backend = os.environ.get("LLM_BACKEND", "kimi").lower()
    from src.intelligence.embedder import Embedder
    if backend == "ollama":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        model = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")
        return Embedder(api_key="ollama", base_url=base_url, model=model)
    else:
        api_key = os.environ.get("KIMI_API_KEY")
        if not api_key:
            click.echo("[error] KIMI_API_KEY not set in .env", err=True)
            sys.exit(1)
        model = os.environ.get("EMBEDDING_MODEL", "moonshot-v1-embedding")
        return Embedder(api_key=api_key, model=model)


# ── CLI root ─────────────────────────────────────────────────────────────────

@click.group()
@click.option("--db-path", default=None, help="DuckDB file path")
@click.pass_context
def cli(ctx, db_path):
    ctx.ensure_object(dict)
    if db_path:
        ctx.obj["db_path"] = db_path


# ── db commands ───────────────────────────────────────────────────────────────

@cli.group()
def db():
    """Database operations."""


@db.command("init")
@click.option("--sql-path", default=None, help="Path to init.sql")
@click.pass_context
def db_init(ctx, sql_path):
    """Create tables and install VSS extension."""
    db_path = _db_path(ctx.obj)
    sql_path = sql_path or os.path.join(BASE_DIR, "db", "init.sql")
    store = _get_store(db_path)
    store.create_tables(sql_path)
    store.load_vss_extension()
    store.close()
    click.echo(f"[ok] Database initialized: {db_path}")


@db.command("build-index")
@click.pass_context
def db_build_index(ctx):
    """Build HNSW vector index on embeddings."""
    store = _get_store(_db_path(ctx.obj))
    store.load_vss_extension()
    store.build_hnsw_index()
    store.close()


@db.command("stats")
@click.pass_context
def db_stats(ctx):
    """Show row counts for all tables."""
    store = _get_store(_db_path(ctx.obj))
    for table in ("documents", "file_chunks", "embeddings", "events"):
        try:
            row = store.fetch_one(f"SELECT COUNT(*) AS n FROM {table}")
            click.echo(f"  {table:20s} {row['n']} rows")
        except Exception as e:
            click.echo(f"  {table:20s} error: {e}")
    store.close()


# ── ingest command ────────────────────────────────────────────────────────────

@cli.command("ingest")
@click.argument("path")
@click.option("--recursive/--no-recursive", default=True)
@click.option("--ext", default=None, help="Comma-separated extensions, e.g. .pdf,.md")
@click.option("--force", is_flag=True, help="Re-ingest even if duplicate")
@click.pass_context
def ingest_cmd(ctx, path, recursive, ext, force):
    """Parse and store files (no AI processing)."""
    db_path = _db_path(ctx.obj)
    extensions = [e.strip() for e in ext.split(",")] if ext else None

    ingestor = _get_ingestor(db_path)
    if os.path.isfile(path):
        doc_id, is_dup = ingestor.ingest_file(path, force=force)
        status = "duplicate" if is_dup else f"doc_id={doc_id}"
        click.echo(f"[ingest] {os.path.basename(path)} → {status}")
    else:
        results = ingestor.ingest_directory(path, recursive=recursive, extensions=extensions, force=force)
        new = sum(1 for _, dup in results if not dup)
        dup = sum(1 for _, d in results if d)
        click.echo(f"[done] {new} new, {dup} duplicates")
    ingestor.close()


# ── process command ───────────────────────────────────────────────────────────

@cli.command("process")
@click.option("--limit", default=20, show_default=True)
@click.option("--skip-embed", is_flag=True)
@click.option("--skip-classify", is_flag=True)
@click.option("--skip-summarize", is_flag=True)
@click.option("--skip-extract", is_flag=True)
@click.pass_context
def process_cmd(ctx, limit, skip_embed, skip_classify, skip_summarize, skip_extract):
    """Run AI processing on unprocessed documents."""
    from src.intelligence.classifier import classify_file
    from src.intelligence.summarizer import summarize_document
    from src.intelligence.extractor import extract_structured_data

    db_path = _db_path(ctx.obj)
    store = _get_store(db_path)
    llm = _get_llm_client()

    llm_model_fast = os.environ.get("LLM_MODEL_FAST", "moonshot-v1-8k")
    llm_model_large = os.environ.get("LLM_MODEL_LARGE", "moonshot-v1-32k")

    docs = store.get_unprocessed_documents(limit=limit)
    click.echo(f"Processing {len(docs)} documents...")

    for doc in docs:
        doc_id = doc["id"]
        title = doc.get("title", "")
        content = doc.get("content", "")
        file_type = doc.get("file_type", "")
        click.echo(f"  → [{doc_id}] {title[:60]}")

        if not skip_classify:
            result = classify_file(content, title, file_type, llm, llm_model_fast)
            store.update_document_tags(doc_id, result.get("tags", []))
            store.insert_event(doc_id, "classify", result)
            click.echo(f"     classify: {result.get('category')} {result.get('tags', [])[:3]}")

        if not skip_summarize:
            summary = summarize_document(content, title, client=llm, model=llm_model_large)
            store.update_document_summary(doc_id, summary)
            store.insert_event(doc_id, "summarize", {"length": len(summary)})
            click.echo(f"     summary: {summary[:80]}…")

        if not skip_extract:
            extracted = extract_structured_data(content, title, client=llm, model=llm_model_large)
            store.insert_event(doc_id, "extract", extracted)
            click.echo(f"     extract: {list(extracted.keys())}")

        if not skip_embed:
            embedder = _get_embedder()
            chunks = store.get_chunks_for_document(doc_id)
            unembedded = [c for c in chunks if True]  # embed all chunks for this doc
            texts = [c["text"] for c in unembedded]
            if texts:
                vectors = embedder.embed_batch(texts)
                for chunk, vector in zip(unembedded, vectors):
                    store.insert_embedding(chunk["id"], doc_id, vector)
                store.insert_event(doc_id, "embed", {"chunk_count": len(texts)})
                click.echo(f"     embedded: {len(texts)} chunks")

    store.close()
    click.echo("[done]")


# ── search command ────────────────────────────────────────────────────────────

@cli.command("search")
@click.argument("query")
@click.option("--top-k", default=5, show_default=True)
@click.option("--file-type", default=None)
@click.option("--hnsw", is_flag=True, help="Use HNSW index")
@click.pass_context
def search_cmd(ctx, query, top_k, file_type, hnsw):
    """Semantic search over embedded chunks."""
    from src.retrieval.semantic_search import SemanticSearch

    store = _get_store(_db_path(ctx.obj))
    embedder = _get_embedder()
    searcher = SemanticSearch(store, embedder)

    if hnsw:
        results = searcher.search_with_hnsw(query, top_k=top_k)
    else:
        results = searcher.search(query, top_k=top_k, filter_file_type=file_type)

    if not results:
        click.echo("No results found.")
    else:
        click.echo(f"\nTop {len(results)} results for: '{query}'\n")
        for i, r in enumerate(results, 1):
            click.echo(f"{'─'*60}")
            click.echo(f"#{i}  [{r.get('file_type','')}] {r.get('title','')}")
            click.echo(f"    score: {r.get('score', 0):.4f}  |  {r.get('file_path','')}")
            text = (r.get("text") or "")[:200].replace("\n", " ")
            click.echo(f"    {text}…")

    store.close()


# ── watch command ─────────────────────────────────────────────────────────────

@cli.command("watch")
@click.argument("dir_path", default=None, required=False)
@click.option("--recursive/--no-recursive", default=True)
@click.option("--ext", default=None)
@click.option("--process", "run_ai", is_flag=True, help="Run AI after each ingest")
@click.pass_context
def watch_cmd(ctx, dir_path, recursive, ext, run_ai):
    """Watch a directory and ingest new files automatically."""
    from src.watcher.file_watcher import FileWatcher

    watch_dir = dir_path or os.environ.get("WATCH_DIR", "input")
    if not os.path.isdir(watch_dir):
        click.echo(f"[error] Directory not found: {watch_dir}", err=True)
        sys.exit(1)

    db_path = _db_path(ctx.obj)
    ingestor = _get_ingestor(db_path)
    llm = _get_llm_client() if run_ai else None
    extensions = [e.strip() for e in ext.split(",")] if ext else None

    watcher = FileWatcher(
        watch_dir=watch_dir,
        ingestor=ingestor,
        recursive=recursive,
        extensions=extensions,
        run_ai=run_ai,
        llm_client=llm,
    )
    watcher.run_forever()
    ingestor.close()


# ── export command ────────────────────────────────────────────────────────────

@cli.command("export")
@click.option("--output-dir", default=None)
@click.option("--limit", default=50, show_default=True)
@click.pass_context
def export_cmd(ctx, output_dir, limit):
    """Export processed documents to Markdown."""
    from src.output.exporter import FileExporter

    out = output_dir or _PRIMARY_OUT
    store = _get_store(_db_path(ctx.obj))
    exporter = FileExporter(out)
    paths = exporter.export_from_store(store, limit=limit)
    click.echo(f"[done] Exported {len(paths)} files to {out}")
    store.close()
    _sync_to_nas(out, _NAS_OUT)


# ── organize command ─────────────────────────────────────────────────────────

@cli.command("organize")
@click.argument("src_dir")
@click.option("--output-dir", "-o", default=None,
              help="Destination root (default: <src_dir>/organized/)")
@click.option("--mode", default="by-category",
              type=click.Choice(["by-category", "by-type"]),
              show_default=True,
              help="by-category: classify by content; by-type: classify by extension")
@click.option("--action", default="copy",
              type=click.Choice(["copy", "move"]),
              show_default=True,
              help="copy (safe) or move files")
@click.option("--subdir-by-type", is_flag=True,
              help="In by-category mode, also create extension sub-folders")
@click.option("--no-recursive", is_flag=True,
              help="Do not walk subdirectories")
@click.option("--ext", default=None,
              help="Comma-separated extensions to process, e.g. .pdf,.md")
@click.option("--llm", "use_llm", is_flag=True,
              help="Use LLM for classification instead of rule-based")
def organize_cmd(src_dir, output_dir, mode, action, subdir_by_type,
                 no_recursive, ext, use_llm):
    """Classify and organize files into category folders.

    \b
    Examples:
      # Rule-based category folders (offline, fast)
      python main.py organize input/

      # Extension folders
      python main.py organize input/ --mode by-type

      # Move instead of copy, with type sub-folders
      python main.py organize input/ --action move --subdir-by-type

      # LLM-powered classification
      python main.py organize input/ --llm

      # Specify output directory
      python main.py organize input/ -o sorted/
    """
    from src.organizer import FileOrganizer

    if not os.path.isdir(src_dir):
        click.echo(f"[error] Directory not found: {src_dir}", err=True)
        sys.exit(1)

    out = output_dir or _PRIMARY_OUT
    extensions = [e.strip() for e in ext.split(",")] if ext else None

    llm_client = None
    llm_classify_fn = None
    if use_llm:
        llm_client = _get_llm_client()
        from src.intelligence.classifier import classify_file
        llm_classify_fn = classify_file
        click.echo("[info] Using LLM classification")

    organizer = FileOrganizer(
        output_dir=out,
        mode=mode,
        subdir_by_type=subdir_by_type,
        action=action,
        recursive=not no_recursive,
        extensions=extensions,
        llm_classify_fn=llm_classify_fn,
        llm_client=llm_client,
    )

    click.echo(f"Organizing '{src_dir}' → '{out}' (mode={mode}, action={action})...")
    summary = organizer.organize_directory(src_dir)

    # Print per-file results
    for r in summary.results:
        src_rel = os.path.relpath(r.src, src_dir)
        dst_rel = os.path.relpath(r.dst, out) if r.success else "—"
        status = "ok" if r.success else "fail"
        click.echo(f"  [{status}] {src_rel}")
        if r.success:
            click.echo(f"        → {r.category}/{os.path.basename(r.dst)}")
        else:
            click.echo(f"        error: {r.error}")

    # Summary
    click.echo("")
    click.echo(f"Done: {summary.succeeded} ok, {summary.failed} failed  "
               f"(total {summary.total})")
    click.echo("")
    click.echo("Category breakdown:")
    for cat, count in summary.by_category().items():
        click.echo(f"  {cat:16s} {count}")

    # Sync organized output to NAS
    nas_out = os.environ.get("OUTPUT_DIR_NAS", _NAS_OUT)
    _sync_to_nas(out, nas_out)


# ── convert command ──────────────────────────────────────────────────────────

@cli.command("convert")
@click.argument("input_path")
@click.argument("to_format")
@click.option("--output", "-o", default=None, help="Output file path (default: same dir, new extension)")
def convert_cmd(input_path, to_format, output):
    """Convert a file between formats (pdf/md/docx/txt).

    \b
    Examples:
      python main.py convert report.pdf md
      python main.py convert notes.md docx
      python main.py convert data.docx pdf -o /tmp/data.pdf
    """
    from src.converter import get_converter, supported_pairs

    if not os.path.isfile(input_path):
        click.echo(f"[error] File not found: {input_path}", err=True)
        sys.exit(1)

    from_ext = os.path.splitext(input_path)[1].lower()
    to_ext = to_format if to_format.startswith(".") else f".{to_format.lower()}"

    if output is None:
        base = os.path.splitext(input_path)[0]
        output = base + to_ext

    try:
        converter = get_converter(from_ext, to_ext)
    except ValueError as e:
        click.echo(f"[error] {e}", err=True)
        pairs = supported_pairs()
        click.echo("Supported conversions:", err=True)
        for f, t in sorted(pairs):
            click.echo(f"  {f} → {t}", err=True)
        sys.exit(1)

    result = converter.convert(input_path, output)
    if result.success:
        click.echo(f"[ok] {result.message}")
    else:
        click.echo(f"[error] {result.message}", err=True)
        sys.exit(1)


# ── run command (full pipeline) ───────────────────────────────────────────────

@cli.command("run")
@click.argument("path")
@click.option("--output-dir", default=None)
@click.option("--recursive/--no-recursive", default=True)
@click.option("--limit", default=20, show_default=True)
@click.pass_context
def run_cmd(ctx, path, output_dir, recursive, limit):
    """Full pipeline: ingest → process → export."""
    ctx.invoke(ingest_cmd, path=path, recursive=recursive, ext=None, force=False)
    ctx.invoke(process_cmd, limit=limit, skip_embed=False, skip_classify=False,
               skip_summarize=False, skip_extract=False)
    ctx.invoke(export_cmd, output_dir=output_dir, limit=limit)


if __name__ == "__main__":
    cli()
