"""
Voice agent pipeline skill for Gulama.

Provides speech-to-text (STT) and text-to-speech (TTS) capabilities:
- STT: OpenAI Whisper (local or API), Deepgram, Google
- TTS: ElevenLabs v3 Expressive, OpenAI TTS, Google TTS

Requires:
- For Whisper STT: pip install openai-whisper (local) or openai (API)
- For ElevenLabs TTS: pip install elevenlabs
- For Google TTS: pip install gTTS
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("voice_skill")


class VoiceSkill(BaseSkill):
    """
    Voice pipeline skill — speech-to-text and text-to-speech.

    Actions:
    - transcribe: Convert audio file to text (STT)
    - speak: Convert text to audio file (TTS)
    - list_voices: List available TTS voices
    """

    def __init__(self) -> None:
        self._stt_backend: str = "whisper_api"
        self._tts_backend: str = "elevenlabs"
        self._configured = False

    def _load_config(self) -> None:
        """Lazy-load voice config from environment."""
        if self._configured:
            return
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        self._stt_backend = os.getenv("VOICE_STT_BACKEND", "whisper_api")
        self._tts_backend = os.getenv("VOICE_TTS_BACKEND", "elevenlabs")
        self._configured = True

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="voice",
            description="Speech-to-text and text-to-speech voice pipeline",
            version="1.0.0",
            author="gulama",
            required_actions=[ActionType.NETWORK_REQUEST, ActionType.FILE_WRITE],
            is_builtin=True,
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "voice",
                "description": (
                    "Voice pipeline for speech-to-text and text-to-speech. "
                    "Actions: transcribe (audio→text), speak (text→audio), list_voices"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["transcribe", "speak", "list_voices"],
                            "description": "Voice action to perform",
                        },
                        "audio_path": {
                            "type": "string",
                            "description": "Path to audio file (for transcribe action)",
                        },
                        "text": {
                            "type": "string",
                            "description": "Text to convert to speech (for speak action)",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Output file path for generated audio (for speak action)",
                        },
                        "voice_id": {
                            "type": "string",
                            "description": "Voice ID or name (for speak action, default: auto)",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language code (default: en)",
                        },
                    },
                    "required": ["action"],
                },
            },
        }

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Execute a voice action."""
        action = kwargs.get("action", "transcribe")

        dispatch = {
            "transcribe": self._transcribe,
            "speak": self._speak,
            "list_voices": self._list_voices,
        }

        handler = dispatch.get(action)
        if not handler:
            return SkillResult(
                success=False,
                output="",
                error=f"Unknown voice action: {action}. Use: transcribe, speak, list_voices",
            )

        self._load_config()

        try:
            return await handler(**{k: v for k, v in kwargs.items() if k != "action"})
        except ImportError as e:
            return SkillResult(
                success=False,
                output="",
                error=f"Missing dependency: {str(e)}. Install required packages.",
            )
        except Exception as e:
            logger.error("voice_error", action=action, error=str(e))
            return SkillResult(success=False, output="", error=f"Voice error: {str(e)[:300]}")

    async def _transcribe(
        self,
        audio_path: str = "",
        language: str = "en",
        **_: Any,
    ) -> SkillResult:
        """Convert audio to text using Whisper."""
        if not audio_path:
            return SkillResult(success=False, output="", error="audio_path is required")

        if not Path(audio_path).exists():
            return SkillResult(
                success=False, output="", error=f"Audio file not found: {audio_path}"
            )

        if self._stt_backend == "whisper_local":
            return await self._transcribe_whisper_local(audio_path, language)
        elif self._stt_backend == "whisper_api":
            return await self._transcribe_whisper_api(audio_path, language)
        elif self._stt_backend == "deepgram":
            return await self._transcribe_deepgram(audio_path, language)
        else:
            return SkillResult(
                success=False,
                output="",
                error=f"Unknown STT backend: {self._stt_backend}",
            )

    async def _transcribe_whisper_local(self, audio_path: str, language: str) -> SkillResult:
        """Transcribe using local Whisper model."""
        import whisper

        model = whisper.load_model("base")
        result = model.transcribe(audio_path, language=language)
        text = result.get("text", "").strip()

        return SkillResult(
            success=True,
            output=text,
            metadata={"backend": "whisper_local", "language": language},
        )

    async def _transcribe_whisper_api(self, audio_path: str, language: str) -> SkillResult:
        """Transcribe using OpenAI Whisper API."""
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return SkillResult(
                success=False,
                output="",
                error=(
                    "Voice features require an API key. "
                    "For Whisper/OpenAI TTS: set OPENAI_API_KEY. "
                    "For ElevenLabs TTS: set ELEVENLABS_API_KEY. "
                    "For Deepgram STT: set DEEPGRAM_API_KEY. "
                    "Add the key to your .env file or run 'gulama setup'."
                ),
            )

        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(audio_path, "rb") as f:
                response = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    data={"model": "whisper-1", "language": language},
                    files={"file": (Path(audio_path).name, f, "audio/mpeg")},
                )

            if response.status_code != 200:
                return SkillResult(
                    success=False,
                    output="",
                    error=f"Whisper API error: {response.status_code}",
                )

            text = response.json().get("text", "").strip()
            return SkillResult(
                success=True,
                output=text,
                metadata={"backend": "whisper_api", "language": language},
            )

    async def _transcribe_deepgram(self, audio_path: str, language: str) -> SkillResult:
        """Transcribe using Deepgram API."""
        api_key = os.getenv("DEEPGRAM_API_KEY", "")
        if not api_key:
            return SkillResult(
                success=False,
                output="",
                error=(
                    "Deepgram speech-to-text requires DEEPGRAM_API_KEY. "
                    "Set it in your .env file. Get a key at https://console.deepgram.com/. "
                    "Alternatively, set VOICE_STT_BACKEND=whisper and use OPENAI_API_KEY."
                ),
            )

        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(audio_path, "rb") as f:
                response = await client.post(
                    "https://api.deepgram.com/v1/listen",
                    headers={
                        "Authorization": f"Token {api_key}",
                        "Content-Type": "audio/mpeg",
                    },
                    params={"model": "nova-2", "language": language},
                    content=f.read(),
                )

            if response.status_code != 200:
                return SkillResult(
                    success=False,
                    output="",
                    error=f"Deepgram API error: {response.status_code}",
                )

            data = response.json()
            text = (
                data.get("results", {})
                .get("channels", [{}])[0]
                .get("alternatives", [{}])[0]
                .get("transcript", "")
            )
            return SkillResult(
                success=True,
                output=text,
                metadata={"backend": "deepgram", "language": language},
            )

    async def _speak(
        self,
        text: str = "",
        output_path: str = "",
        voice_id: str = "",
        language: str = "en",
        **_: Any,
    ) -> SkillResult:
        """Convert text to speech."""
        if not text:
            return SkillResult(success=False, output="", error="text is required for speak action")

        if not output_path:
            output_path = os.path.join(tempfile.gettempdir(), "gulama_tts_output.mp3")

        if self._tts_backend == "elevenlabs":
            return await self._speak_elevenlabs(text, output_path, voice_id)
        elif self._tts_backend == "openai":
            return await self._speak_openai(text, output_path, voice_id)
        elif self._tts_backend == "gtts":
            return await self._speak_gtts(text, output_path, language)
        else:
            return SkillResult(
                success=False,
                output="",
                error=f"Unknown TTS backend: {self._tts_backend}",
            )

    async def _speak_elevenlabs(self, text: str, output_path: str, voice_id: str) -> SkillResult:
        """Text-to-speech using ElevenLabs."""
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not api_key:
            return SkillResult(success=False, output="", error="ELEVENLABS_API_KEY not set")

        voice = voice_id or "21m00Tcm4TlvDq8ikWAM"  # Default: Rachel

        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text[:5000],
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                },
            )

            if response.status_code != 200:
                return SkillResult(
                    success=False,
                    output="",
                    error=f"ElevenLabs API error: {response.status_code}",
                )

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(response.content)

            return SkillResult(
                success=True,
                output=f"Audio saved to {output_path} ({len(response.content)} bytes)",
                metadata={"backend": "elevenlabs", "voice": voice, "path": output_path},
            )

    async def _speak_openai(self, text: str, output_path: str, voice_id: str) -> SkillResult:
        """Text-to-speech using OpenAI."""
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return SkillResult(
                success=False,
                output="",
                error=(
                    "Voice features require an API key. "
                    "For Whisper/OpenAI TTS: set OPENAI_API_KEY. "
                    "For ElevenLabs TTS: set ELEVENLABS_API_KEY. "
                    "For Deepgram STT: set DEEPGRAM_API_KEY. "
                    "Add the key to your .env file or run 'gulama setup'."
                ),
            )

        voice = voice_id or "alloy"

        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "tts-1",
                    "input": text[:4096],
                    "voice": voice,
                },
            )

            if response.status_code != 200:
                return SkillResult(
                    success=False,
                    output="",
                    error=f"OpenAI TTS error: {response.status_code}",
                )

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(response.content)

            return SkillResult(
                success=True,
                output=f"Audio saved to {output_path}",
                metadata={"backend": "openai", "voice": voice, "path": output_path},
            )

    async def _speak_gtts(self, text: str, output_path: str, language: str) -> SkillResult:
        """Text-to-speech using Google TTS (gTTS, free)."""
        from gtts import gTTS

        tts = gTTS(text=text[:5000], lang=language)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        tts.save(output_path)

        return SkillResult(
            success=True,
            output=f"Audio saved to {output_path}",
            metadata={"backend": "gtts", "language": language, "path": output_path},
        )

    async def _list_voices(self, **_: Any) -> SkillResult:
        """List available TTS voices."""
        voices = {
            "elevenlabs": [
                "Rachel (21m00Tcm4TlvDq8ikWAM) — warm, conversational",
                "Domi (AZnzlk1XvdvUeBnXmlld) — confident, assertive",
                "Bella (EXAVITQu4vr4xnSDxMaL) — soft, gentle",
                "Antoni (ErXwobaYiN019PkySvjV) — deep, warm",
                "Josh (TxGEqnHWrfWFTfGW9XjX) — deep, narration",
            ],
            "openai": [
                "alloy — neutral, balanced",
                "echo — deep, warm",
                "fable — expressive, British",
                "onyx — deep, authoritative",
                "nova — warm, friendly",
                "shimmer — gentle, soft",
            ],
            "gtts": [
                "Uses Google Translate TTS (free, limited voices)",
                "Language codes: en, es, fr, de, ja, ko, zh-CN, etc.",
            ],
        }

        lines = [f"Current TTS backend: {self._tts_backend}\n"]
        for backend, voice_list in voices.items():
            lines.append(f"[{backend}]")
            for v in voice_list:
                lines.append(f"  {v}")
            lines.append("")

        return SkillResult(success=True, output="\n".join(lines))
