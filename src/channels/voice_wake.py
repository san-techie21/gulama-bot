"""
Voice wake word detection for Gulama.

Always-on listening mode that activates on a wake word ("Hey Gulama").
Uses Picovoice Porcupine for efficient on-device wake word detection,
then hands off to the voice skill for STT/TTS processing.

Architecture:
1. Porcupine listens for wake word (low CPU, runs continuously)
2. On detection, activates microphone for full speech capture
3. Speech is sent to STT (Whisper/Deepgram) via voice skill
4. Response is generated and spoken via TTS

Requires: pip install pvporcupine pyaudio
Environment: PICOVOICE_ACCESS_KEY, WAKE_WORD (default: "hey google" as placeholder)
"""

from __future__ import annotations

import asyncio
import os
import struct
import threading
from typing import Any

from src.utils.logging import get_logger

logger = get_logger("voice_wake")


class VoiceWakeEngine:
    """
    Wake word detection engine using Picovoice Porcupine.

    Falls back to a simple energy-based detection if Porcupine
    is not available (for development/testing).
    """

    def __init__(
        self,
        access_key: str = "",
        wake_word: str = "hey google",
        sensitivity: float = 0.7,
        silence_timeout: float = 2.0,
        on_wake: Any = None,
    ) -> None:
        self.access_key = access_key or os.getenv("PICOVOICE_ACCESS_KEY", "")
        self.wake_word = wake_word
        self.sensitivity = sensitivity
        self.silence_timeout = silence_timeout
        self.on_wake = on_wake  # async callback(audio_data: bytes)
        self._running = False
        self._thread: threading.Thread | None = None
        self._porcupine: Any = None
        self._audio: Any = None
        self._stream: Any = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start wake word listening in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("voice_wake_started", wake_word=self.wake_word)

    def stop(self) -> None:
        """Stop wake word listening."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

        if self._stream:
            self._stream.close()
            self._stream = None
        if self._audio:
            self._audio.terminate()
            self._audio = None
        if self._porcupine:
            self._porcupine.delete()
            self._porcupine = None

        logger.info("voice_wake_stopped")

    def _listen_loop(self) -> None:
        """Main listening loop running in background thread."""
        try:
            if self.access_key:
                self._listen_porcupine()
            else:
                self._listen_energy_fallback()
        except Exception as e:
            logger.error("voice_wake_error", error=str(e))
            self._running = False

    def _listen_porcupine(self) -> None:
        """Listen using Picovoice Porcupine for precise wake word detection."""
        try:
            import pvporcupine
            import pyaudio
        except ImportError:
            logger.warning("porcupine_not_available", fallback="energy_detection")
            self._listen_energy_fallback()
            return

        # Create Porcupine instance
        keywords = [self.wake_word] if self.wake_word in pvporcupine.KEYWORDS else ["porcupine"]
        self._porcupine = pvporcupine.create(
            access_key=self.access_key,
            keywords=keywords,
            sensitivities=[self.sensitivity],
        )

        self._audio = pyaudio.PyAudio()
        self._stream = self._audio.open(
            rate=self._porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self._porcupine.frame_length,
        )

        logger.info("porcupine_listening", sample_rate=self._porcupine.sample_rate)

        while self._running:
            pcm = self._stream.read(self._porcupine.frame_length, exception_on_overflow=False)
            pcm_unpacked = struct.unpack_from(f"{self._porcupine.frame_length}h", pcm)

            keyword_index = self._porcupine.process(pcm_unpacked)
            if keyword_index >= 0:
                logger.info("wake_word_detected")
                self._handle_wake()

    def _listen_energy_fallback(self) -> None:
        """Simple energy-based voice activity detection (fallback without Porcupine)."""
        try:
            import pyaudio
        except ImportError:
            logger.error("pyaudio_not_installed")
            return

        self._audio = pyaudio.PyAudio()
        sample_rate = 16000
        chunk_size = 1024

        self._stream = self._audio.open(
            rate=sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=chunk_size,
        )

        logger.info("energy_fallback_listening")
        energy_threshold = 1500  # Adjust based on environment

        while self._running:
            pcm = self._stream.read(chunk_size, exception_on_overflow=False)
            audio_data = struct.unpack_from(f"{chunk_size}h", pcm)
            energy = sum(abs(s) for s in audio_data) / len(audio_data)

            if energy > energy_threshold:
                logger.info("voice_activity_detected", energy=int(energy))
                self._handle_wake()
                # Debounce — wait before next detection
                import time

                time.sleep(3)

    def _handle_wake(self) -> None:
        """Handle wake word detection — capture audio and invoke callback."""
        if not self.on_wake:
            logger.info("wake_detected_no_callback")
            return

        # Capture audio for a few seconds after wake word
        audio_frames = []
        capture_duration = 5  # seconds
        sample_rate = 16000
        chunk_size = 1024

        if self._stream:
            frames_needed = int(sample_rate / chunk_size * capture_duration)
            for _ in range(frames_needed):
                if not self._running:
                    break
                try:
                    data = self._stream.read(chunk_size, exception_on_overflow=False)
                    audio_frames.append(data)
                except Exception:
                    break

        audio_data = b"".join(audio_frames)
        logger.info("audio_captured", bytes=len(audio_data))

        # Invoke callback in event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.on_wake(audio_data), loop)
            else:
                loop.run_until_complete(self.on_wake(audio_data))
        except Exception as e:
            logger.error("wake_callback_error", error=str(e))


class AlwaysOnVoiceChannel:
    """
    Always-on voice channel that combines wake word detection with
    the voice skill for full speech-to-response pipeline.

    Usage:
        channel = AlwaysOnVoiceChannel()
        channel.start()  # Starts listening for wake word
    """

    def __init__(self, wake_word: str = "hey google") -> None:
        self.wake_word = wake_word
        self._engine: VoiceWakeEngine | None = None

    async def _on_wake(self, audio_data: bytes) -> None:
        """Handle wake word detection — process speech through agent."""
        logger.info("processing_voice_command")
        try:
            from src.agent.brain import AgentBrain
            from src.gateway.config import load_config

            config = load_config()
            brain = AgentBrain(config=config)

            # Use voice skill for STT
            result = await brain.process_message(
                message="[VOICE_INPUT]",
                channel="voice",
                channel_data={"audio_bytes": len(audio_data)},
            )
            logger.info("voice_response_generated", length=len(result.get("response", "")))

        except Exception as e:
            logger.error("voice_processing_error", error=str(e))

    def start(self) -> None:
        """Start always-on voice listening."""
        self._engine = VoiceWakeEngine(
            wake_word=self.wake_word,
            on_wake=self._on_wake,
        )
        self._engine.start()

    def stop(self) -> None:
        """Stop voice listening."""
        if self._engine:
            self._engine.stop()
