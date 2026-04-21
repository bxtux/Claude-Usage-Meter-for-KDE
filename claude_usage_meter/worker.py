from __future__ import annotations

from datetime import datetime
from threading import Event

from PySide6.QtCore import QThread, Signal

from .config import AppConfig
from .models import UsageSnapshot
from .scraper import ClaudeUsageScraper


class UsageMonitorThread(QThread):
    snapshot_signal = Signal(object)
    status_signal = Signal(str)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._stop_event = Event()
        self._force_event = Event()

    def request_refresh(self) -> None:
        self._force_event.set()

    def stop(self) -> None:
        self._stop_event.set()
        self._force_event.set()

    def run(self) -> None:
        scraper = ClaudeUsageScraper(
            chromium_executable=self._config.chromium_executable,
            profile_dir=self._config.profile_dir_expanded,
            headless=self._config.headless,
        )
        try:
            self.status_signal.emit("Initialisation Playwright...")
            scraper.start()
            self.status_signal.emit("Monitoring actif")

            while not self._stop_event.is_set():
                next_wait = self._config.refresh_seconds
                try:
                    snapshot = scraper.fetch_snapshot()
                except Exception as exc:
                    msg = f"Erreur scraping: {exc}"
                    self.status_signal.emit(msg)
                    snapshot = UsageSnapshot(
                        percent_used=0,
                        reset_text=msg,
                        fetched_at=datetime.now(),
                        source_ok=False,
                    )
                    # Retry faster after transient failures.
                    next_wait = min(10, self._config.refresh_seconds)
                self.snapshot_signal.emit(snapshot)
                if not snapshot.source_ok:
                    next_wait = min(10, next_wait)

                if self._force_event.wait(timeout=next_wait):
                    self._force_event.clear()

        except Exception as exc:
            self.status_signal.emit(f"Erreur initialisation navigateur: {exc}")
        finally:
            try:
                scraper.stop()
            except Exception:
                pass
