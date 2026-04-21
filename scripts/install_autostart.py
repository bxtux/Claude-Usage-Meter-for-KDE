from __future__ import annotations

from pathlib import Path
import sys

DESKTOP_PATH = Path.home() / ".config" / "autostart" / "claude-usage-meter.desktop"


def build_desktop_entry(python_exec: str) -> str:
    return f"""[Desktop Entry]
Type=Application
Name=Claude Usage Meter
Comment=Monitor Claude session usage
Exec={python_exec} -m claude_usage_meter
Terminal=false
X-GNOME-Autostart-enabled=true
"""


def main() -> None:
    DESKTOP_PATH.parent.mkdir(parents=True, exist_ok=True)
    python_exec = sys.executable
    DESKTOP_PATH.write_text(build_desktop_entry(python_exec), encoding="utf-8")
    print(f"Autostart installed: {DESKTOP_PATH}")


if __name__ == "__main__":
    main()
