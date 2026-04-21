from __future__ import annotations

from .config import load_config
from .ui import start_app


def run() -> int:
    config = load_config()
    return start_app(config)
