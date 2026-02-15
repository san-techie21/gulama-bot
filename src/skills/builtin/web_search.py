"""
Built-in web search skill for Gulama.

Provides web browsing capabilities:
- Search the web via DuckDuckGo (no API key needed)
- Fetch and parse web pages
- Extract text content from URLs

All network requests go through the egress filter.
"""

from __future__ import annotations

from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("web_search")


class WebSearchSkill(BaseSkill):
    """Web search and page fetching."""

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="web_search",
            description="Search the web and fetch web pages",
            version="0.1.0",
            author="gulama",
            required_actions=[ActionType.NETWORK_REQUEST],
            is_builtin=True,
        )

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Execute a web operation."""
        operation = kwargs.get("operation", "search")
        query = kwargs.get("query", "")
        url = kwargs.get("url", "")

        match operation:
            case "search":
                if not query:
                    return SkillResult(
                        success=False, output="", error="Query is required for search"
                    )
                return await self._search(query)
            case "fetch":
                if not url:
                    return SkillResult(success=False, output="", error="URL is required for fetch")
                return await self._fetch(url)
            case _:
                return SkillResult(
                    success=False,
                    output="",
                    error=f"Unknown operation: {operation}",
                )

    async def _search(self, query: str, max_results: int = 5) -> SkillResult:
        """Search the web using DuckDuckGo."""
        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(f"**{r['title']}**\n{r['href']}\n{r['body']}\n")

            if not results:
                return SkillResult(success=True, output="No results found.")

            return SkillResult(
                success=True,
                output="\n---\n".join(results),
                metadata={"result_count": len(results)},
            )

        except ImportError:
            return SkillResult(
                success=False,
                output="",
                error="duckduckgo_search package not installed. Run: pip install duckduckgo-search",
            )
        except Exception as e:
            return SkillResult(success=False, output="", error=str(e))

    async def _fetch(self, url: str) -> SkillResult:
        """Fetch and extract text from a URL."""
        # Validate URL
        from src.security.input_validator import InputValidator

        validator = InputValidator()
        result = validator.validate_url(url)
        if not result.valid:
            return SkillResult(
                success=False,
                output="",
                error=result.blocked_reason,
            )

        # Check egress filter
        from src.security.egress_filter import EgressFilter

        egress = EgressFilter()
        decision = egress.check_request(url=url, method="GET")
        if not decision.allowed:
            return SkillResult(
                success=False,
                output="",
                error=f"Blocked by egress filter: {decision.reason}",
            )

        try:
            import httpx

            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Gulama/0.1"})
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "")
                if "text/html" in content_type:
                    # Extract text from HTML
                    text = self._extract_text(resp.text)
                else:
                    text = resp.text

                # Limit output size
                if len(text) > 10000:
                    text = text[:10000] + "\n\n[Truncated — content too long]"

                return SkillResult(
                    success=True,
                    output=text,
                    metadata={"url": url, "status_code": resp.status_code},
                )

        except ImportError:
            return SkillResult(
                success=False,
                output="",
                error="httpx package not installed. Run: pip install httpx",
            )
        except Exception as e:
            return SkillResult(success=False, output="", error=str(e))

    @staticmethod
    def _extract_text(html: str) -> str:
        """Extract readable text from HTML."""
        try:
            from html.parser import HTMLParser

            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text_parts = []
                    self._skip = False

                def handle_starttag(self, tag, attrs):
                    if tag in ("script", "style", "nav", "footer", "header"):
                        self._skip = True

                def handle_endtag(self, tag):
                    if tag in ("script", "style", "nav", "footer", "header"):
                        self._skip = False
                    if tag in ("p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li"):
                        self.text_parts.append("\n")

                def handle_data(self, data):
                    if not self._skip:
                        self.text_parts.append(data.strip())

            extractor = TextExtractor()
            extractor.feed(html)
            return " ".join(extractor.text_parts).strip()
        except Exception:
            # Fallback: strip all tags
            import re

            return re.sub(r"<[^>]+>", " ", html).strip()

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web or fetch a web page. Operations: search, fetch",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["search", "fetch"],
                            "description": "search = web search, fetch = get page content",
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query (for search operation)",
                        },
                        "url": {
                            "type": "string",
                            "description": "URL to fetch (for fetch operation)",
                        },
                    },
                    "required": ["operation"],
                },
            },
        }
