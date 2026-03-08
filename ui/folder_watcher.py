"""
Folder watcher: monitors a directory for new .xlsx files and emits a signal.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    Observer = None
    FileSystemEventHandler = object
    FileCreatedEvent = object


class XlsxCreatedHandler(FileSystemEventHandler):
    """Emits path when a new .xlsx file is created (handles renames/copies)."""

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() == ".xlsx":
            self._callback(str(path.resolve()))

    def on_moved(self, event):
        if event.is_directory:
            return
        path = Path(event.dest_path)
        if path.suffix.lower() == ".xlsx":
            self._callback(str(path.resolve()))


class FolderWatcher(QObject):
    """Watches a folder for new .xlsx files. Emits new_xlsx_added(path_str) from watcher thread."""

    new_xlsx_added = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._observer = None
        self._watch_path = None

    @property
    def is_available(self) -> bool:
        return HAS_WATCHDOG

    @property
    def is_watching(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    def start(self, folder: str | Path) -> bool:
        """Start watching the given folder. Returns True if started."""
        if not HAS_WATCHDOG:
            return False
        self.stop()
        path = Path(folder).resolve()
        if not path.is_dir():
            return False
        self._watch_path = path
        handler = XlsxCreatedHandler(lambda p: self.new_xlsx_added.emit(p))
        self._observer = Observer()
        self._observer.schedule(handler, str(path), recursive=False)
        self._observer.daemon = True
        self._observer.start()
        return True

    def stop(self) -> None:
        """Stop watching."""
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=2.0)
            except Exception:
                pass
            self._observer = None
        self._watch_path = None
