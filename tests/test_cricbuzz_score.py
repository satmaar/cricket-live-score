"""Unit, browser-flow integration, performance, and regression checks."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class FakeTimeoutError(Exception):
    pass


class FakeLocator:
    def __init__(self, texts: list[str], timeout: bool = False):
        self.texts = texts
        self.timeout = timeout
        self.first = self
        self.wait_options = None

    def wait_for(self, **kwargs):
        self.wait_options = kwargs
        if self.timeout:
            raise FakeTimeoutError("score not found")

    def all_inner_texts(self):
        return self.texts


class FakePage:
    def __init__(self, texts: list[str], timeout: bool = False):
        self.locator_value = FakeLocator(texts, timeout)
        self.goto_args = None
        self.screenshot_args = None

    def goto(self, *args, **kwargs):
        self.goto_args = (args, kwargs)

    def locator(self, selector):
        self.selector = selector
        return self.locator_value

    def screenshot(self, **kwargs):
        self.screenshot_args = kwargs


class FakeBrowser:
    def __init__(self, page):
        self.page = page
        self.closed = False

    def new_page(self):
        return self.page

    def close(self):
        self.closed = True


class FakePlaywrightContext:
    def __init__(self, browser):
        self.browser = browser
        self.chromium = self
        self.launch_args = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def launch(self, **kwargs):
        self.launch_args = kwargs
        return self.browser


def load_module():
    fake_sync = types.ModuleType("playwright.sync_api")
    fake_sync.TimeoutError = FakeTimeoutError
    fake_sync.sync_playwright = lambda: None
    fake_package = types.ModuleType("playwright")
    fake_package.sync_api = fake_sync
    with patch.dict(sys.modules, {"playwright": fake_package, "playwright.sync_api": fake_sync}):
        spec = importlib.util.spec_from_file_location("cricbuzz_score_tested", ROOT / "cricbuzz_score.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


class CricbuzzScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = load_module()

    def test_unit_normalizes_score_and_ignores_empty_nodes(self):
        self.assertEqual(
            self.app.find_score_text(["  ", " IND 287/4\n (45.2 Ov) "]),
            "IND 287/4 (45.2 Ov)",
        )

    def test_unit_returns_none_for_empty_score_nodes(self):
        self.assertIsNone(self.app.find_score_text(["", "  \n"]))

    def test_integration_captures_score_with_headless_browser(self):
        page = FakePage(["IND 287/4 (45.2 Ov)"])
        browser = FakeBrowser(page)
        context = FakePlaywrightContext(browser)
        with patch.object(self.app, "sync_playwright", return_value=context):
            result = self.app.capture_score(
                headless=True, screenshot_path=Path("score.png"), timeout_ms=7000
            )
        self.assertEqual(result, "IND 287/4 (45.2 Ov)")
        self.assertEqual(context.launch_args, {"headless": True})
        self.assertEqual(page.goto_args[0], (self.app.CRICBUZZ_URL,))
        self.assertEqual(page.selector, self.app.SCORE_SELECTOR)
        self.assertEqual(page.locator_value.wait_options, {"state": "visible", "timeout": 7000})
        self.assertEqual(page.screenshot_args, {"path": "score.png", "full_page": True})
        self.assertTrue(browser.closed)

    def test_integration_no_score_still_saves_screenshot_and_closes_browser(self):
        page = FakePage([], timeout=True)
        browser = FakeBrowser(page)
        context = FakePlaywrightContext(browser)
        with patch.object(self.app, "sync_playwright", return_value=context):
            result = self.app.capture_score(headless=False)
        self.assertIsNone(result)
        self.assertEqual(context.launch_args, {"headless": False})
        self.assertIsNotNone(page.screenshot_args)
        self.assertTrue(browser.closed)

    def test_regression_success_and_no_live_score_messages(self):
        for return_value, expected in [
            ("NZ 185 (40.2 Ov)", "NZ 185 (40.2 Ov)\nSaved screenshot: score.png\n"),
            (None, "No match score is currently available on Cricbuzz.\nSaved screenshot: score.png\n"),
        ]:
            output = io.StringIO()
            with patch.object(self.app, "capture_score", return_value=return_value):
                with contextlib.redirect_stdout(output):
                    status = self.app.main([])
            self.assertEqual(status, 0)
            self.assertEqual(output.getvalue(), expected)

    def test_performance_score_extraction_10000_cards(self):
        samples = ["   ", "NZ 185 (40.2 Ov)"] * 20
        started = time.perf_counter()
        for _ in range(10_000):
            self.app.find_score_text(samples)
        self.assertLess(time.perf_counter() - started, 5.0)


if __name__ == "__main__":
    unittest.main()
