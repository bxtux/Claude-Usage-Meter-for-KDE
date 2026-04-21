from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMenu,
    QProgressBar,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .config import AppConfig
from .models import AlertState, UsageSnapshot
from .notifier import Notifier
from .worker import UsageMonitorThread


class MeterWindow(QMainWindow):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._notifier = Notifier(play_sound=config.play_sound)
        self._alert_state = AlertState()

        self.setWindowTitle("Claude Usage Meter")
        if config.always_on_top:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.session_label = QLabel("Session actuelle")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.percent_label = QLabel("0 % utilises")
        self.reset_label = QLabel("Reinitialisation: n/a")
        self.status_label = QLabel("Demarrage...")

        layout.addWidget(self.session_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.percent_label)
        layout.addWidget(self.reset_label)
        layout.addWidget(self.status_label)

        self.setCentralWidget(root)
        self.resize(360, 150)

        self.worker = UsageMonitorThread(config)
        self.worker.snapshot_signal.connect(self.on_snapshot)
        self.worker.status_signal.connect(self.on_status)

        self._init_tray()

    def _init_tray(self) -> None:
        icon = QIcon.fromTheme("utilities-system-monitor")
        if icon.isNull():
            icon_path = Path(__file__).parent / "icon.png"
            if icon_path.exists():
                icon = QIcon(str(icon_path))

        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("Claude Usage Meter")

        menu = QMenu()
        self.action_toggle = QAction("Afficher / Masquer", self)
        self.action_refresh = QAction("Forcer refresh", self)
        self.action_quit = QAction("Quitter", self)

        self.action_toggle.triggered.connect(self.toggle_visibility)
        self.action_refresh.triggered.connect(self.force_refresh)
        self.action_quit.triggered.connect(self.quit_app)

        menu.addAction(self.action_toggle)
        menu.addAction(self.action_refresh)
        menu.addSeparator()
        menu.addAction(self.action_quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.toggle_visibility()

    def toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()

    def force_refresh(self) -> None:
        self.worker.request_refresh()
        self.status_label.setText("Refresh force demande...")

    def on_status(self, text: str) -> None:
        self.status_label.setText(text)

    def on_snapshot(self, snapshot: UsageSnapshot) -> None:
        self.progress.setValue(snapshot.percent_used)
        self.percent_label.setText(f"{snapshot.percent_used} % utilises")
        self.reset_label.setText(snapshot.reset_text)
        self.status_label.setText(
            f"Derniere mise a jour: {snapshot.fetched_at.strftime('%H:%M:%S')}"
            if snapshot.source_ok
            else f"Source indisponible ({snapshot.fetched_at.strftime('%H:%M:%S')})"
        )
        self.tray.setToolTip(f"Claude session: {snapshot.percent_used}%")

        if self._alert_state.should_fire(snapshot.percent_used, self._config.threshold_percent):
            self._notifier.notify_threshold(snapshot.percent_used, snapshot.reset_text)

    def start(self) -> None:
        self.show()
        self.worker.start()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.hide()
        event.ignore()

    def quit_app(self) -> None:
        self.worker.stop()
        self.worker.wait(4000)
        QApplication.instance().quit()


def start_app(config: AppConfig) -> int:
    app = QApplication([])
    QApplication.setQuitOnLastWindowClosed(False)

    window = MeterWindow(config)
    window.start()
    return app.exec()
