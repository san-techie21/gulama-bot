"""
Browser automation skill for Gulama.

Dual backend:
1. Playwright (low-level) — direct navigate, click, fill, screenshot, extract
2. browser-use (high-level) — natural language web browsing with LLM agent

All browser actions run inside the sandbox with network restrictions.

Requires:
  Base:  pip install playwright && playwright install chromium
  AI:    pip install browser-use  (optional, for natural language browsing)
"""

from __future__ import annotations

from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("browser_skill")


class BrowserSkill(BaseSkill):
    """
    Sandboxed web browser skill using Playwright + browser-use.

    Low-level actions (Playwright):
    - navigate: Go to URL, return page text
    - screenshot: Capture page image
    - click: Click element by CSS selector
    - fill: Fill form field
    - extract: Extract text from elements

    High-level actions (browser-use):
    - browse: Natural language web browsing (e.g., "search Google for weather")
    - research: Multi-step research task with extraction

    Requires: pip install playwright && playwright install chromium
    Optional: pip install browser-use  (for AI browsing)
    """

    def __init__(self) -> None:
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._browser_use_available: bool | None = None

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="browser",
            description="Browse the web, extract content, take screenshots, fill forms, and AI-powered natural language browsing",
            version="2.0.0",
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
                    "Low-level actions: navigate (go to URL), screenshot, click, fill, extract. "
                    "AI-powered actions: browse (natural language instruction like 'search Google for AI news'), "
                    "research (multi-step extraction task). "
                    "Use 'browse' for complex multi-step web interactions. "
                    "Use 'navigate' for simple page fetching."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "navigate", "screenshot", "click", "fill", "extract",
                                "browse", "research",
                            ],
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
                        "task": {
                            "type": "string",
                            "description": "Natural language instruction for browse/research actions (e.g., 'Go to Wikipedia and find the population of Tokyo')",
                        },
                        "max_steps": {
                            "type": "integer",
                            "description": "Maximum steps for AI browsing (default: 10)",
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
            "browse": self._browse,
            "research": self._research,
        }

        handler = dispatch.get(action)
        if not handler:
            return SkillResult(
                success=False, output="",
                error=f"Unknown browser action: {action}. Use: navigate, screenshot, click, fill, extract, browse, research",
            )

        try:
            return await handler(**{k: v for k, v in kwargs.items() if k != "action"})
        except ImportError as e:
            missing = str(e)
            if "browser_use" in missing or "browser-use" in missing:
                return SkillResult(
                    success=False, output="",
                    error="browser-use is required for AI browsing. Install: pip install browser-use",
                )
            return SkillResult(
                success=False, output="",
                error="Playwright is required for browser skill. Install: pip install playwright && playwright install chromium",
            )
        except Exception as e:
            logger.error("browser_error", action=action, error=str(e))
            return SkillResult(success=False, output="", error=f"Browser error: {str(e)[:500]}")

    # ── Low-level Playwright actions ────────────────────────────

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

    # ── High-level browser-use AI actions ───────────────────────

    def _check_browser_use(self) -> bool:
        """Check if browser-use library is available."""
        if self._browser_use_available is None:
            try:
                import browser_use  # noqa: F401
                self._browser_use_available = True
            except ImportError:
                self._browser_use_available = False
        return self._browser_use_available

    async def _browse(self, task: str = "", url: str = "", max_steps: int = 10, **_: Any) -> SkillResult:
        """
        AI-powered natural language web browsing.

        Uses browser-use library to execute complex multi-step browser tasks
        described in natural language. Falls back to simple navigate if
        browser-use is not installed.
        """
        if not task and not url:
            return SkillResult(
                success=False, output="",
                error="Either 'task' (natural language instruction) or 'url' is required for browse",
            )

        # If browser-use is not available, fall back to simple navigate
        if not self._check_browser_use():
            if url:
                return await self._navigate(url=url)
            return SkillResult(
                success=False, output="",
                error=(
                    "browser-use library is not installed. "
                    "Install: pip install browser-use\n"
                    "Alternatively, use action='navigate' with a URL for basic browsing."
                ),
            )

        try:
            import os
            from browser_use import Agent as BrowserAgent
            from langchain_openai import ChatOpenAI

            # Determine LLM for browser-use agent
            # browser-use works best with OpenAI/Anthropic models
            api_key = (
                os.getenv("OPENAI_API_KEY")
                or os.getenv("DEEPSEEK_API_KEY")
                or os.getenv("LLM_API_KEY", "")
            )

            model_name = os.getenv("BROWSER_USE_MODEL", "gpt-4o-mini")
            base_url = os.getenv("BROWSER_USE_API_BASE", None)

            llm_kwargs: dict[str, Any] = {
                "model": model_name,
                "api_key": api_key,
            }
            if base_url:
                llm_kwargs["base_url"] = base_url

            llm = ChatOpenAI(**llm_kwargs)

            # Build the task
            full_task = task
            if url:
                full_task = f"Go to {url}. Then: {task}" if task else f"Go to {url} and extract the main content."

            # Create and run the browser-use agent
            agent = BrowserAgent(
                task=full_task,
                llm=llm,
                max_actions_per_step=3,
            )

            result = await agent.run(max_steps=min(max_steps, 20))

            # Extract final result
            output_text = ""
            if hasattr(result, "final_result") and result.final_result:
                output_text = str(result.final_result)
            elif hasattr(result, "history") and result.history:
                # Collect text from action results
                for step in result.history[-3:]:  # Last 3 steps
                    if hasattr(step, "result") and step.result:
                        extracted = str(step.result)
                        if extracted and extracted != "None":
                            output_text += extracted + "\n"

            if not output_text:
                output_text = "Browse task completed but no text was extracted."

            # Truncate for LLM context
            if len(output_text) > 8000:
                output_text = output_text[:8000] + "\n...[truncated]"

            logger.info("browse_complete", task=task[:80], steps=max_steps)

            return SkillResult(
                success=True,
                output=output_text.strip(),
                metadata={"task": task[:100], "engine": "browser-use"},
            )

        except ImportError:
            return SkillResult(
                success=False, output="",
                error="browser-use dependencies missing. Install: pip install browser-use langchain-openai",
            )
        except Exception as e:
            logger.error("browse_error", task=task[:80], error=str(e))
            return SkillResult(success=False, output="", error=f"AI browse failed: {str(e)[:400]}")

    async def _research(self, task: str = "", max_steps: int = 15, **_: Any) -> SkillResult:
        """
        Multi-step research task with structured extraction.

        Uses browser-use to search, navigate multiple pages, and synthesize
        information. Optimized for research queries that require visiting
        multiple sources.
        """
        if not task:
            return SkillResult(
                success=False, output="",
                error="'task' is required for research action (e.g., 'Research the top 3 Python web frameworks and compare them')",
            )

        # Wrap as a structured research prompt
        research_task = (
            f"Research task: {task}\n\n"
            "Instructions:\n"
            "1. Search the web for relevant information\n"
            "2. Visit 2-3 authoritative sources\n"
            "3. Extract key facts and data points\n"
            "4. Compile a concise summary of findings"
        )

        return await self._browse(task=research_task, max_steps=min(max_steps, 25))

    async def cleanup(self) -> None:
        """Close the browser."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
            self._context = None
            self._page = None
