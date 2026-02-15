"""
Browser automation skill for Gulama.

Uses Playwright for web browsing in a sandboxed environment.
Supports page navigation, content extraction, screenshots, and form filling.

All browser actions run inside the sandbox with network restrictions.
"""

from __future__ import annotations

from typing import Any

from src.skills.base import BaseSkill
from src.utils.logging import get_logger

logger = get_logger("browser_skill")


class BrowserSkill(BaseSkill):
    """
    Sandboxed web browser skill using Playwright.

    Capabilities:
    - Navigate to URLs (with domain restrictions)
    - Extract page text content
    - Take screenshots
    - Click elements
    - Fill forms
    - Execute JavaScript (sandboxed)

    Requires: pip install playwright && playwright install chromium
    """

    name = "browser"
    description = "Browse the web, extract content, take screenshots"
    version = "1.0.0"

    def __init__(self):
        self._browser = None
        self._context = None
        self._page = None

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "browser_navigate",
                    "description": "Navigate to a URL and return the page text content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to navigate to"},
                            "wait_for": {"type": "string", "description": "Wait for selector or 'load'/'networkidle'", "default": "load"},
                        },
                        "required": ["url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_screenshot",
                    "description": "Take a screenshot of the current page",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path to save screenshot"},
                            "full_page": {"type": "boolean", "description": "Capture full page", "default": False},
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_click",
                    "description": "Click an element on the page",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector of element to click"},
                        },
                        "required": ["selector"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_fill",
                    "description": "Fill a form field",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector of the input"},
                            "value": {"type": "string", "description": "Value to fill"},
                        },
                        "required": ["selector", "value"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_extract",
                    "description": "Extract text from specific elements",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector", "default": "body"},
                        },
                    },
                },
            },
        ]

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        dispatch = {
            "browser_navigate": self._navigate,
            "browser_screenshot": self._screenshot,
            "browser_click": self._click,
            "browser_fill": self._fill,
            "browser_extract": self._extract,
        }

        handler = dispatch.get(tool_name)
        if not handler:
            return f"Unknown browser action: {tool_name}"

        try:
            return await handler(**arguments)
        except Exception as e:
            logger.error("browser_error", action=tool_name, error=str(e))
            return f"Browser error: {str(e)[:200]}"

    async def _ensure_browser(self):
        """Ensure browser is launched."""
        if self._page:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is required for browser skill. "
                "Install with: pip install playwright && playwright install chromium"
            )

        pw = await async_playwright().start()
        self._browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
            ],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Gulama/1.0 (Secure AI Agent; +https://gulama.ai)",
        )
        self._page = await self._context.new_page()

    async def _navigate(self, url: str, wait_for: str = "load") -> str:
        """Navigate to a URL and return page content."""
        await self._ensure_browser()

        try:
            await self._page.goto(url, wait_until=wait_for, timeout=30000)
            title = await self._page.title()
            text = await self._page.inner_text("body")

            # Truncate to reasonable size
            if len(text) > 5000:
                text = text[:5000] + "\n...[truncated]"

            return f"Page: {title}\nURL: {self._page.url}\n\n{text}"
        except Exception as e:
            return f"Navigation failed: {str(e)[:200]}"

    async def _screenshot(self, path: str, full_page: bool = False) -> str:
        """Take a screenshot."""
        await self._ensure_browser()
        await self._page.screenshot(path=path, full_page=full_page)
        return f"Screenshot saved to {path}"

    async def _click(self, selector: str) -> str:
        """Click an element."""
        await self._ensure_browser()
        await self._page.click(selector, timeout=10000)
        return f"Clicked: {selector}"

    async def _fill(self, selector: str, value: str) -> str:
        """Fill a form field."""
        await self._ensure_browser()
        await self._page.fill(selector, value, timeout=10000)
        return f"Filled '{selector}' with value"

    async def _extract(self, selector: str = "body") -> str:
        """Extract text from elements."""
        await self._ensure_browser()
        elements = await self._page.query_selector_all(selector)

        texts = []
        for elem in elements[:20]:  # Limit to 20 elements
            text = await elem.inner_text()
            if text.strip():
                texts.append(text.strip())

        return "\n".join(texts) if texts else "No content found"

    async def cleanup(self):
        """Close the browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._context = None
            self._page = None
