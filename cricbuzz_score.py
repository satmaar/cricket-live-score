"""Capture the latest score card rendered on Cricbuzz."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


CRICBUZZ_URL = "https://www.cricbuzz.com/"
# Verified on Cricbuzz's rendered home page: this class is used for score text.
SCORE_SELECTOR = ".cb-lv-scrs-col"
DEFAULT_TIMEOUT_MS = 15_000
DEFAULT_SCREENSHOT = Path("score.png")


def find_score_text(texts: Iterable[str]) -> str | None:
    """Return the first nonempty score text, with whitespace normalized."""
    for text in texts:
        normalized = " ".join(text.split())
        if normalized:
            return normalized
    return None


def capture_score(
    *, headless: bool = False, screenshot_path: Path = DEFAULT_SCREENSHOT,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> str | None:
    """Load the page, wait for a score card, and save a screenshot.

    Returns ``None`` if Cricbuzz has no rendered score card before the timeout.
    The browser is always closed, including on navigation or screenshot errors.
    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            page = browser.new_page()
            page.goto(CRICBUZZ_URL, wait_until="domcontentloaded", timeout=timeout_ms)
            score = None
            try:
                locator = page.locator(SCORE_SELECTOR)
                locator.first.wait_for(state="visible", timeout=timeout_ms)
                score = find_score_text(locator.all_inner_texts())
            except PlaywrightTimeoutError:
                pass
            page.screenshot(path=str(screenshot_path), full_page=True)
            return score
        finally:
            browser.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print the latest Cricbuzz score and save a screenshot."
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="run Chromium without a visible window (default: headed)",
    )
    parser.add_argument(
        "--screenshot", type=Path, default=DEFAULT_SCREENSHOT,
        help="screenshot output path (default: score.png)",
    )
    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT_MS,
        help="navigation and score wait timeout in milliseconds",
    )
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be a positive number of milliseconds")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        score = capture_score(
            headless=args.headless,
            screenshot_path=args.screenshot,
            timeout_ms=args.timeout,
        )
    except Exception as exc:
        print(f"Unable to capture Cricbuzz score: {exc}", file=sys.stderr)
        return 1

    if score is None:
        print("No match score is currently available on Cricbuzz.")
        print(f"Saved screenshot: {args.screenshot}")
        return 0
    print(score)
    print(f"Saved screenshot: {args.screenshot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
