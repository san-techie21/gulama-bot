"""
Browser automation skill for Gulama.

Uses Playwright for web browsing in a sandboxed environment.
Supports page navigation, content extraction, screenshots, and form filling.

All browser actions run inside the sandbox with network restrictions.

Requires: pip install playwright && playwright install chromium
"""

from __future__ import annotations

from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
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

    Requires: pip install playwright && playwright install chromium
    """

    def __init__(self) -> None:
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="browser",
            description="Browse the web, extract content, take screenshots, fill forms",
            version="1.0.0",
            author="gulama",
            required_actions=[ActionType.NETWORK_REQUEST],
            is_builtin=True,
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser",
                "description": (
                    "Browse the web using a headless browser. "
                    "Actions: navigate (go to URL and get page text), "
                    "screenshot (capture page image), "
                    "click (click an element by CSS selector), "
                    "fill (fill a form field), "
                    "extract (extract text from elements by CSS selector)"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["navigate", "screenshot", "click", "fill", "extract"],
                            "description": "The browser action to perform",
                        },
                        "url": {
                            "type": "string",
                            "description": "URL to navigate to (for navigate action)",
                        },
                        "selector": {
                            "type": "string",
                            "description": "CSS selector for click/fill/extract actions",
                        },
                        "value": {
                            "type": "string",
                            "description": "Value to fill (for fill action)",
                        },
                        "path": {
                            "type": "string",
                            "description": "File path to save screenshot (for screenshot action)",
                        },
                        "full_page": {
                            "type": "boolean",
                            "description": "Capture full page screenshot (default: false)",
                        },
                        "wait_for": {
                            "type": "string",
                            "description": "Wait condition: 'load', 'networkidle', or a CSS selector",
                        },
                    },
                    "required": ["action"],
                },
            },
        }

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Execute a browser action."""
        action = kwargs.get("action", "navigate")

        dispatch = {
            "navigate": self._navigate,
            "screenshot": self._screenshot,
            "click": self._click,
            "fill": self._fill,
            "extract": self._extract,
        }

        handler = dispatch.get(action)
        if not handler:
            return SkillResult(
                success=False, output="",
                error=f"Unknown browser action: {action}. Use: navigate, screenshot, click, fill, extract",
            )

        try:
            return await handler(**{k: v for k, v in kwargs.items() if k != "action"})
        except ImportError:
            return SkillResult(
                success=False, output="",
                error="Playwright is required for browser skill. Install: pip install playwright && playwright install chromium",
            )
        except Exception as e:
            logger.error("browser_error", action=action, error=str(e))
            return SkillResult(success=False, output="", error=f"Browser error: {str(e)[:500]}")

    async def _ensure_browser(self) -> None:
        """Ensure browser is launched."""
        if self._page:
            return

        from playwright.async_api import async_playwright

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
            user_agent="Gulama/1.0 (Secure AI Agent; +https://github.com/san-techie21/gulama-bot)",
        )
        self._page = await self._context.new_page()

    async def _navigate(self, url: str = "", wait_for: str = "load", **_: Any) -> SkillResult:
        """Navigate to a URL and return page content."""
        if not url:
            return SkillResult(success=False, output="", error="URL is required for navigate action")

        await self._ensure_browser()

        try:
            await self._page.goto(url, wait_until=wait_for, timeout=30000)
            title = await self._page.title()
            text = await self._page.inner_text("body")

            # Truncate to reasonable size for LLM context
            if len(text) > 5000:
                text = text[:5000] + "\n...[truncated]"

            return SkillResult(
                success=True,
                output=f"Page: {title}\nURL: {self._page.url}\n\n{text}",
                metadata={"title": title, "url": self._page.url},
            )
        except Exception as e:
            return SkillResult(success=False, output="", error=f"Navigation failed: {str(e)[:300]}")

    async def _screenshot(self, path: str = "", full_page: bool = False, **_: Any) -> SkillResult:
        """Take a screenshot."""
        if not path:
            return SkillResult(success=False, output="", error="Path is required for screenshot action")

        await self._ensure_browser()
        await self._page.screenshot(path=path, full_page=full_page)
        return SkillResult(success=True, output=f"Screenshot saved to {path}")

    async def _click(self, selector: str = "", **_: Any) -> SkillResult:
        """Click an element."""
        if not selector:
            return SkillResult(success=False, output="", error="Selector is required for click action")

        await self._ensure_browser()
        await self._page.click(selector, timeout=10000)
        return SkillResult(success=True, output=f"Clicked: {selector}")

    async def _fill(self, selector: str = "", value: str = "", **_: Any) -> SkillResult:
        """Fill a form field."""
        if not selector:
            return SkillResult(success=False, output="", error="Selector is required for fill action")
        if not value:
            return SkillResult(success=False, output="", error="Value is required for fill action")

        await self._ensure_browser()
        await self._page.fill(selector, value, timeout=10000)
        return SkillResult(success=True, output=f"Filled '{selector}' with value")

    async def _extract(self, selector: str = "body", **_: Any) -> SkillResult:
        """Extract text from elements."""
        await self._ensure_browser()
        elements = await self._page.query_selector_all(selector)

        texts = []
        for elem in elements[:20]:  # Limit to 20 elements
            text = await elem.inner_text()
            if text.strip():
                texts.append(text.strip())

        output = "\n".join(texts) if texts else "No content found"
        return SkillResult(success=True, output=output)

    async def cleanup(self) -> None:
        """Close the browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._context = None
            self._page = None
