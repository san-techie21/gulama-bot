"""
Image generation skill for Gulama.

Supports multiple backends:
- OpenAI DALL-E 3 (API)
- Stable Diffusion (via API — Stability AI, Replicate, or local ComfyUI)
- Flux (via Replicate or local)

Requires: pip install httpx (for API calls)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("image_gen")


class ImageGenSkill(BaseSkill):
    """
    Image generation skill.

    Actions:
    - generate: Generate an image from a text prompt
    - edit: Edit an existing image (inpainting/outpainting)
    - variations: Create variations of an existing image
    """

    def __init__(self) -> None:
        self._backend: str = "dalle"
        self._configured = False

    def _load_config(self) -> None:
        """Lazy-load image gen config from environment."""
        if self._configured:
            return
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        self._backend = os.getenv("IMAGE_GEN_BACKEND", "dalle")
        self._configured = True

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="image_gen",
            description="Generate images from text prompts (DALL-E, Stable Diffusion, Flux)",
            version="1.0.0",
            author="gulama",
            required_actions=[ActionType.NETWORK_REQUEST, ActionType.FILE_WRITE],
            is_builtin=True,
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "image_gen",
                "description": (
                    "Generate images from text prompts. "
                    "Actions: generate (create image from prompt), "
                    "edit (modify existing image), variations (create variations)"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["generate", "edit", "variations"],
                            "description": "Image generation action",
                        },
                        "prompt": {
                            "type": "string",
                            "description": "Text prompt describing the desired image",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "File path to save the generated image",
                        },
                        "size": {
                            "type": "string",
                            "enum": ["256x256", "512x512", "1024x1024", "1024x1792", "1792x1024"],
                            "description": "Image size (default: 1024x1024)",
                        },
                        "quality": {
                            "type": "string",
                            "enum": ["standard", "hd"],
                            "description": "Image quality (default: standard)",
                        },
                        "style": {
                            "type": "string",
                            "enum": ["vivid", "natural"],
                            "description": "Image style for DALL-E (default: vivid)",
                        },
                        "image_path": {
                            "type": "string",
                            "description": "Path to source image (for edit/variations)",
                        },
                        "n": {
                            "type": "integer",
                            "description": "Number of images to generate (default: 1, max: 4)",
                        },
                    },
                    "required": ["action"],
                },
            },
        }

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Execute an image generation action."""
        action = kwargs.get("action", "generate")

        dispatch = {
            "generate": self._generate,
            "edit": self._edit,
            "variations": self._variations,
        }

        handler = dispatch.get(action)
        if not handler:
            return SkillResult(
                success=False,
                output="",
                error=f"Unknown image action: {action}. Use: generate, edit, variations",
            )

        self._load_config()

        try:
            return await handler(**{k: v for k, v in kwargs.items() if k != "action"})
        except ImportError:
            return SkillResult(
                success=False,
                output="",
                error="httpx is required for image generation. Install: pip install httpx",
            )
        except Exception as e:
            logger.error("image_gen_error", action=action, error=str(e))
            return SkillResult(success=False, output="", error=f"Image gen error: {str(e)[:300]}")

    async def _generate(
        self,
        prompt: str = "",
        output_path: str = "",
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid",
        n: int = 1,
        **_: Any,
    ) -> SkillResult:
        """Generate an image from a prompt."""
        if not prompt:
            return SkillResult(success=False, output="", error="prompt is required")

        if self._backend == "dalle":
            return await self._generate_dalle(prompt, output_path, size, quality, style, n)
        elif self._backend == "stability":
            return await self._generate_stability(prompt, output_path, size)
        elif self._backend == "replicate":
            return await self._generate_replicate(prompt, output_path)
        else:
            return SkillResult(
                success=False,
                output="",
                error=f"Unknown image backend: {self._backend}",
            )

    async def _generate_dalle(
        self,
        prompt: str,
        output_path: str,
        size: str,
        quality: str,
        style: str,
        n: int,
    ) -> SkillResult:
        """Generate image using OpenAI DALL-E 3."""
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return SkillResult(success=False, output="", error="OPENAI_API_KEY not set")

        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "dall-e-3",
                    "prompt": prompt[:4000],
                    "n": min(n, 1),  # DALL-E 3 supports n=1 only
                    "size": size,
                    "quality": quality,
                    "style": style,
                    "response_format": "b64_json" if output_path else "url",
                },
            )

            if response.status_code != 200:
                return SkillResult(
                    success=False,
                    output="",
                    error=f"DALL-E API error: {response.status_code} — {response.text[:200]}",
                )

            data = response.json()
            image_data = data.get("data", [{}])[0]
            revised_prompt = image_data.get("revised_prompt", prompt)

            if output_path and "b64_json" in image_data:
                import base64

                img_bytes = base64.b64decode(image_data["b64_json"])
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_bytes(img_bytes)
                return SkillResult(
                    success=True,
                    output=f"Image saved to {output_path}\nRevised prompt: {revised_prompt}",
                    metadata={"path": output_path, "revised_prompt": revised_prompt},
                )
            else:
                url = image_data.get("url", "")
                return SkillResult(
                    success=True,
                    output=f"Image URL: {url}\nRevised prompt: {revised_prompt}",
                    metadata={"url": url, "revised_prompt": revised_prompt},
                )

    async def _generate_stability(
        self,
        prompt: str,
        output_path: str,
        size: str,
    ) -> SkillResult:
        """Generate image using Stability AI."""
        api_key = os.getenv("STABILITY_API_KEY", "")
        if not api_key:
            return SkillResult(success=False, output="", error="STABILITY_API_KEY not set")

        import httpx

        w, h = (int(x) for x in size.split("x")) if "x" in size else (1024, 1024)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "text_prompts": [{"text": prompt[:2000], "weight": 1}],
                    "width": min(w, 1024),
                    "height": min(h, 1024),
                    "samples": 1,
                    "steps": 30,
                },
            )

            if response.status_code != 200:
                return SkillResult(
                    success=False,
                    output="",
                    error=f"Stability API error: {response.status_code}",
                )

            data = response.json()
            artifacts = data.get("artifacts", [])
            if not artifacts:
                return SkillResult(success=False, output="", error="No image generated")

            import base64

            img_bytes = base64.b64decode(artifacts[0]["base64"])

            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_bytes(img_bytes)
                return SkillResult(
                    success=True,
                    output=f"Image saved to {output_path}",
                    metadata={"path": output_path, "backend": "stability"},
                )

            return SkillResult(
                success=True,
                output=f"Image generated ({len(img_bytes)} bytes). Provide output_path to save.",
                metadata={"backend": "stability"},
            )

    async def _generate_replicate(self, prompt: str, output_path: str) -> SkillResult:
        """Generate image using Replicate (Flux, SDXL, etc)."""
        api_key = os.getenv("REPLICATE_API_TOKEN", "")
        if not api_key:
            return SkillResult(success=False, output="", error="REPLICATE_API_TOKEN not set")

        import httpx

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Create prediction
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "version": "black-forest-labs/flux-schnell",
                    "input": {"prompt": prompt[:2000]},
                },
            )

            if response.status_code not in (200, 201):
                return SkillResult(
                    success=False,
                    output="",
                    error=f"Replicate API error: {response.status_code}",
                )

            prediction = response.json()
            prediction_url = prediction.get("urls", {}).get("get", "")

            # Poll for completion (max 60s)
            import asyncio

            for _ in range(60):
                poll = await client.get(
                    prediction_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                status_data = poll.json()
                status = status_data.get("status")

                if status == "succeeded":
                    output_urls = status_data.get("output", [])
                    if output_urls:
                        img_url = output_urls[0] if isinstance(output_urls, list) else output_urls

                        if output_path:
                            img_resp = await client.get(img_url)
                            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                            Path(output_path).write_bytes(img_resp.content)
                            return SkillResult(
                                success=True,
                                output=f"Image saved to {output_path}",
                                metadata={"path": output_path, "backend": "replicate"},
                            )

                        return SkillResult(
                            success=True,
                            output=f"Image URL: {img_url}",
                            metadata={"url": img_url, "backend": "replicate"},
                        )

                elif status == "failed":
                    return SkillResult(
                        success=False,
                        output="",
                        error=f"Generation failed: {status_data.get('error', 'unknown')}",
                    )

                await asyncio.sleep(1)

            return SkillResult(success=False, output="", error="Generation timed out")

    async def _edit(self, **kwargs: Any) -> SkillResult:
        """Edit an existing image (DALL-E only)."""
        return SkillResult(
            success=False,
            output="",
            error="Image editing requires DALL-E 2 API. Use 'generate' with a descriptive prompt instead.",
        )

    async def _variations(self, **kwargs: Any) -> SkillResult:
        """Create variations of an image (DALL-E only)."""
        return SkillResult(
            success=False,
            output="",
            error="Image variations require DALL-E 2 API. Use 'generate' with a descriptive prompt instead.",
        )
