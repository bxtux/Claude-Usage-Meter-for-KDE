from __future__ import annotations

from playwright.sync_api import sync_playwright

from .config import load_config
from .scraper import CLAUDE_USAGE_URL


def main() -> None:
    config = load_config()
    profile_dir = config.profile_dir_expanded
    profile_dir.mkdir(parents=True, exist_ok=True)

    print("Ouverture Chromium pour login Claude...")
    print("Connecte-toi sur claude.ai puis ferme la fenetre Chromium.")

    with sync_playwright() as p:
        executable_path = config.chromium_executable.strip() or None
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            executable_path=executable_path,
            headless=False,
            ignore_default_args=["--enable-automation"],
            args=[
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
                "--class=claude-usage-meter-browser",
                "--name=claude-usage-meter-browser",
            ],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(CLAUDE_USAGE_URL, wait_until="domcontentloaded", timeout=30000)

        browser = context.browser
        if browser is not None:
            browser.on("disconnected", lambda: print("Profil enregistre, fermeture detectee."))

        try:
            while True:
                if browser is not None and not browser.is_connected():
                    break
                page.wait_for_timeout(500)
        finally:
            try:
                context.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
