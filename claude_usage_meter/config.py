from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

CONFIG_DIR = Path.home() / ".config" / "claude-usage-meter"
CONFIG_PATH = CONFIG_DIR / "config.toml"


@dataclass(slots=True)
class AppConfig:
    refresh_seconds: int = 120
    threshold_percent: int = 80
    always_on_top: bool = True
    play_sound: bool = True
    chromium_executable: str = "/snap/bin/chromium"
    profile_dir: str = "~/claude-usage-meter-profile"
    headless: bool = False

    @property
    def profile_dir_expanded(self) -> Path:
        return Path(self.profile_dir).expanduser()


DEFAULT_CONFIG = AppConfig()
LEGACY_PROFILE_DIR = "~/.config/chromium"
LEGACY_PROFILE_DIR_2 = "~/.config/claude-usage-meter/chromium-profile"
LEGACY_CHROMIUM_EXECUTABLE = ""


def _to_toml(config: AppConfig) -> str:
    return (
        f"refresh_seconds = {config.refresh_seconds}\n"
        f"threshold_percent = {config.threshold_percent}\n"
        f"always_on_top = {'true' if config.always_on_top else 'false'}\n"
        f"play_sound = {'true' if config.play_sound else 'false'}\n"
        f"chromium_executable = \"{config.chromium_executable}\"\n"
        f"profile_dir = \"{config.profile_dir}\"\n"
        f"headless = {'true' if config.headless else 'false'}\n"
    )


def ensure_config_file(path: Path = CONFIG_PATH) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_to_toml(DEFAULT_CONFIG), encoding="utf-8")


def save_config(config: AppConfig, path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_to_toml(config), encoding="utf-8")


def load_config(path: Path = CONFIG_PATH) -> AppConfig:
    ensure_config_file(path)
    with path.open("rb") as f:
        data = tomllib.load(f)

    profile_dir = str(data.get("profile_dir", DEFAULT_CONFIG.profile_dir))
    migrated = False
    chromium_executable = str(data.get("chromium_executable", DEFAULT_CONFIG.chromium_executable))
    # Migrate legacy default that conflicts with a running Chromium instance.
    if profile_dir in (LEGACY_PROFILE_DIR, LEGACY_PROFILE_DIR_2):
        profile_dir = DEFAULT_CONFIG.profile_dir
        migrated = True
    # Migrate old Playwright-browser default back to system Chromium.
    if chromium_executable == LEGACY_CHROMIUM_EXECUTABLE:
        chromium_executable = DEFAULT_CONFIG.chromium_executable
        migrated = True

    config = AppConfig(
        refresh_seconds=max(1, int(data.get("refresh_seconds", DEFAULT_CONFIG.refresh_seconds))),
        threshold_percent=max(1, min(100, int(data.get("threshold_percent", DEFAULT_CONFIG.threshold_percent)))),
        always_on_top=bool(data.get("always_on_top", DEFAULT_CONFIG.always_on_top)),
        play_sound=bool(data.get("play_sound", DEFAULT_CONFIG.play_sound)),
        chromium_executable=chromium_executable,
        profile_dir=profile_dir,
        headless=bool(data.get("headless", DEFAULT_CONFIG.headless)),
    )
    if migrated:
        save_config(config, path)
    return config
