from __future__ import annotations

import os
import time
from typing import List, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from ..parsers.registry import SUPPORTED_EXTENSIONS


class FileProcessorHandler(FileSystemEventHandler):
    def __init__(self, ingestor, extensions: List[str], run_ai: bool = False, llm_client=None):
        self.ingestor = ingestor
        self.extensions = set(e.lower() for e in extensions)
        self.run_ai = run_ai
        self.llm_client = llm_client
        self._processing: set = set()

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        self._handle(event.src_path, force=False)

    def on_modified(self, event: FileModifiedEvent) -> None:
        if event.is_directory:
            return
        self._handle(event.src_path, force=True)

    def _handle(self, path: str, force: bool) -> None:
        ext = os.path.splitext(path)[1].lower()
        if ext not in self.extensions:
            return
        if path in self._processing:
            return
        self._processing.add(path)
        try:
            time.sleep(0.5)  # brief wait for file write to complete
            doc_id, is_dup = self.ingestor.ingest_file(path, force=force)
            action = "duplicate" if is_dup else f"doc_id={doc_id}"
            print(f"[watcher] {os.path.basename(path)} → {action}")

            if self.run_ai and doc_id and not is_dup and self.llm_client:
                self._run_ai(doc_id)
        except Exception as e:
            print(f"[watcher error] {os.path.basename(path)}: {e}")
        finally:
            self._processing.discard(path)

    def _run_ai(self, doc_id: int) -> None:
        from ..intelligence.classifier import classify_file
        from ..intelligence.summarizer import summarize_document
        import os as _os

        store = self.ingestor.store
        doc = store.get_document(doc_id)
        if not doc:
            return

        content = doc.get("content", "")
        title = doc.get("title", "")
        file_type = doc.get("file_type", "")

        result = classify_file(content, title, file_type, self.llm_client)
        store.update_document_tags(doc_id, result.get("tags", []))
        store.insert_event(doc_id, "classify", result)

        summary = summarize_document(content, title, client=self.llm_client)
        store.update_document_summary(doc_id, summary)
        store.insert_event(doc_id, "summarize", {"length": len(summary)})


class FileWatcher:
    def __init__(
        self,
        watch_dir: str,
        ingestor,
        recursive: bool = True,
        extensions: Optional[List[str]] = None,
        run_ai: bool = False,
        llm_client=None,
    ):
        self.watch_dir = watch_dir
        self.recursive = recursive
        self.handler = FileProcessorHandler(
            ingestor,
            extensions or SUPPORTED_EXTENSIONS,
            run_ai=run_ai,
            llm_client=llm_client,
        )
        self.observer = Observer()
        self.observer.schedule(self.handler, watch_dir, recursive=recursive)

    def start(self) -> None:
        self.observer.start()

    def stop(self) -> None:
        self.observer.stop()
        self.observer.join()

    def run_forever(self) -> None:
        self.start()
        print(f"[watcher] Watching {self.watch_dir} — press Ctrl+C to stop")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
            print("[watcher] Stopped.")
