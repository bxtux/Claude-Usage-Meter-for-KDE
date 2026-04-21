from __future__ import annotations

from pathlib import Path
import re
import time
from typing import Any

from playwright.sync_api import BrowserContext, Error, Page, TimeoutError, sync_playwright

from .models import UsageSnapshot
from datetime import datetime

CLAUDE_USAGE_URL = "https://claude.ai/settings/usage"


class ClaudeUsageScraper:
    def __init__(self, chromium_executable: str, profile_dir: Path, headless: bool) -> None:
        self.chromium_executable = chromium_executable
        self.profile_dir = profile_dir
        self.headless = headless
        self._playwright = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._last_nav_ts = 0.0

    def start(self) -> None:
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        executable_path = self.chromium_executable.strip() or None
        try:
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                executable_path=executable_path,
                headless=self.headless,
                ignore_default_args=["--enable-automation"],
                args=[
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-blink-features=AutomationControlled",
                    "--class=claude-usage-meter-browser",
                    "--name=claude-usage-meter-browser",
                ],
            )
        except Error as exc:
            self.stop()
            msg = str(exc)
            if "ProcessSingleton" in msg or "SingletonLock" in msg:
                raise RuntimeError(
                    "Le profil Chromium est verrouille. Utilise un profil dedie ou lance "
                    "`claude-usage-meter-login` pour initialiser le profil de l'app."
                ) from exc
            raise RuntimeError(f"Echec du lancement Chromium: {exc}") from exc

        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = self._context.new_page()

        self._page.goto(CLAUDE_USAGE_URL, wait_until="domcontentloaded", timeout=30000)
        self._last_nav_ts = time.time()

    def stop(self) -> None:
        if self._context is not None:
            self._context.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._context = None
        self._playwright = None
        self._page = None

    def fetch_snapshot(self) -> UsageSnapshot:
        if self._page is None:
            raise RuntimeError("Scraper not started")
        if self._page.is_closed():
            raise RuntimeError("La page Chromium a ete fermee")

        now = time.time()
        current_url = self._page.url or ""
        # Important: do not force navigation on every poll (3s), otherwise
        # Cloudflare challenge can be reset continuously.
        if "claude.ai/settings/usage" not in current_url and now - self._last_nav_ts > 20:
            self._page.goto(CLAUDE_USAGE_URL, wait_until="domcontentloaded", timeout=30000)
            self._last_nav_ts = now

        payload: dict[str, Any] | None = self._evaluate_usage()
        if payload is None:
            # One fast retry when the execution context is transiently reset.
            self._page.wait_for_timeout(1200)
            payload = self._evaluate_usage()

        if payload is None:
            return UsageSnapshot(
                percent_used=0,
                reset_text="Aucune donnee recue.",
                fetched_at=datetime.now(),
                source_ok=False,
            )

        return UsageSnapshot(
            percent_used=max(0, min(100, int(payload.get("percent", 0)))),
            reset_text=str(payload.get("resetText", "")) or "Texte de reset indisponible",
            fetched_at=datetime.now(),
            source_ok=bool(payload.get("sourceOk", False)),
        )

    def _evaluate_usage(self) -> dict[str, Any] | None:
        if self._page is None:
            return None

        try:
            self._page.wait_for_selector("body", timeout=15000)
            self._page.wait_for_selector('[role="progressbar"]', timeout=8000)
        except TimeoutError:
            # If progress bars are absent, surface a clearer state.
            page_text = (self._page.inner_text("body") or "").lower()
            if "cloudflare" in page_text and ("verification" in page_text or "vérification" in page_text):
                return {
                    "percent": 0,
                    "resetText": "Verification Cloudflare en cours.",
                    "sourceOk": False,
                }
            return {
                "percent": 0,
                "resetText": "Barre d'usage introuvable (attente de la page Claude).",
                "sourceOk": False,
            }
        except Error as exc:
            if "Execution context was destroyed" in str(exc) or "frame was detached" in str(exc).lower():
                return None
            return self._fallback_locator_extract()

        try:
            payload = self._page.evaluate(
            """
() => {
  const pageText = (document.body?.innerText || '').toLowerCase();
  if (
    pageText.includes('cloudflare') &&
    (pageText.includes('verification') || pageText.includes('vérification'))
  ) {
    return {
      percent: 0,
      resetText: 'Verification Cloudflare en cours (valide la case une fois et attends).',
      sourceOk: false,
    };
  }

  const progressBars = [...document.querySelectorAll('[role="progressbar"]')];
  const sessionRegex = /(session actuelle|current session)/i;
  const resetRegex = /(reinitialisation|réinitialisation|reset)/i;

  function closestSessionContainer(el) {
    let node = el;
    for (let i = 0; i < 8 && node; i += 1) {
      const text = node.innerText || '';
      if (sessionRegex.test(text)) {
        return node;
      }
      node = node.parentElement;
    }
    return null;
  }

  function extractResetText(container) {
    if (!container) return '';
    const lines = (container.innerText || '')
      .split(/\n+/)
      .map((line) => line.trim())
      .filter(Boolean);
    const line = lines.find((x) => resetRegex.test(x));
    return line || '';
  }

  for (const bar of progressBars) {
    const container = closestSessionContainer(bar);
    if (!container) continue;

    const rawValue = bar.getAttribute('aria-valuenow');
    const parsed = rawValue ? Number.parseFloat(rawValue) : Number.NaN;
    const percent = Number.isFinite(parsed) ? Math.round(parsed) : null;
    if (percent === null) continue;

    return {
      percent,
      resetText: extractResetText(container),
      sourceOk: true,
    };
  }

  if (progressBars.length > 0) {
    const fallback = progressBars[0];
    const rawValue = fallback.getAttribute('aria-valuenow');
    const parsed = rawValue ? Number.parseFloat(rawValue) : Number.NaN;
    if (Number.isFinite(parsed)) {
      const fallbackContainer = closestSessionContainer(fallback) || fallback.parentElement;
      return {
        percent: Math.round(parsed),
        resetText: extractResetText(fallbackContainer),
        sourceOk: true,
      };
    }
  }

  return {
    percent: 0,
    resetText: 'Session non detectee (verifie la connexion Claude).',
    sourceOk: false,
  };
}
            """
        )
            return payload or self._fallback_locator_extract()
        except Error as exc:
            # Common transient during SPA/internal navigations.
            if "Execution context was destroyed" in str(exc) or "frame was detached" in str(exc).lower():
                return None
            return self._fallback_locator_extract()

    def _fallback_locator_extract(self) -> dict[str, Any]:
        if self._page is None:
            return {"percent": 0, "resetText": "Page absente.", "sourceOk": False}

        try:
            bar = self._page.locator('[role="progressbar"]').first
            bar.wait_for(state="attached", timeout=5000)
            raw = bar.get_attribute("aria-valuenow") or "0"
            percent = int(round(float(raw)))
        except Exception:
            percent = 0

        reset_text = "Texte de reset indisponible"
        try:
            reset_node = self._page.get_by_text(re.compile(r"Réinitialisation|Reinitialisation|Reset", re.I)).first
            text = reset_node.inner_text(timeout=4000).strip()
            if text:
                reset_text = text
        except Exception:
            pass

        return {
            "percent": max(0, min(100, percent)),
            "resetText": reset_text,
            "sourceOk": percent > 0 or "Réinitialisation" in reset_text or "Reinitialisation" in reset_text,
        }
