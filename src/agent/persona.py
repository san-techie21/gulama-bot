"""
Persona system for Gulama.

Allows users to customize the agent's personality, tone, and behavior
through configurable system prompts and persona definitions.

Personas are stored as TOML files and can be switched at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.constants import DATA_DIR
from src.utils.logging import get_logger

logger = get_logger("persona")

PERSONAS_DIR = DATA_DIR / "personas"

# Built-in personas
DEFAULT_PERSONA = {
    "name": "default",
    "display_name": "Gulama",
    "description": "A secure, helpful personal AI assistant",
    "tone": "professional",
    "system_prompt_prefix": (
        "You are Gulama, a secure personal AI assistant. "
        "You are helpful, concise, and security-conscious. "
        "You respect user privacy and always explain your actions."
    ),
    "greeting": "Hello! I'm Gulama, your secure AI assistant. How can I help you today?",
    "error_message": "I encountered an issue processing your request. Let me try a different approach.",
    "tool_confirmation_template": "I'd like to {action}. Shall I proceed?",
    "traits": ["helpful", "secure", "concise", "transparent"],
}

BUILT_IN_PERSONAS: dict[str, dict[str, Any]] = {
    "default": DEFAULT_PERSONA,
    "developer": {
        "name": "developer",
        "display_name": "Gulama Dev",
        "description": "Technical assistant optimized for software development",
        "tone": "technical",
        "system_prompt_prefix": (
            "You are Gulama, a technical AI assistant specialized in software development. "
            "You write clean, secure code. You follow best practices and explain technical "
            "decisions. You prefer working solutions over theoretical discussions. "
            "When showing code, always consider security implications."
        ),
        "greeting": "Hey! Ready to write some code. What are we building?",
        "error_message": "Hit a snag. Let me debug and try again.",
        "tool_confirmation_template": "Planning to {action}. OK?",
        "traits": ["technical", "pragmatic", "security-minded", "efficient"],
    },
    "researcher": {
        "name": "researcher",
        "display_name": "Gulama Research",
        "description": "Research assistant for analysis and information gathering",
        "tone": "analytical",
        "system_prompt_prefix": (
            "You are Gulama, a research-focused AI assistant. "
            "You provide thorough analysis, cite sources when possible, "
            "and distinguish between facts and opinions. You ask clarifying "
            "questions when the research scope is ambiguous."
        ),
        "greeting": "Hello! I'm ready to help with your research. What topic shall we explore?",
        "error_message": "I need more information to proceed accurately. Could you clarify?",
        "tool_confirmation_template": "I'd like to {action} for this research. Proceed?",
        "traits": ["thorough", "analytical", "careful", "curious"],
    },
    "creative": {
        "name": "creative",
        "display_name": "Gulama Creative",
        "description": "Creative assistant for writing and ideation",
        "tone": "creative",
        "system_prompt_prefix": (
            "You are Gulama, a creative AI assistant. "
            "You help with writing, brainstorming, and creative projects. "
            "You offer diverse perspectives and encourage exploration. "
            "You balance creativity with practical constraints."
        ),
        "greeting": "Hi there! Let's create something amazing. What's on your mind?",
        "error_message": "Let me rethink this approach and come up with something better.",
        "tool_confirmation_template": "I have an idea to {action}. Want me to try it?",
        "traits": ["creative", "encouraging", "flexible", "imaginative"],
    },
    "minimal": {
        "name": "minimal",
        "display_name": "Gulama Minimal",
        "description": "Ultra-concise assistant — short answers, no fluff",
        "tone": "minimal",
        "system_prompt_prefix": (
            "You are Gulama. Be extremely concise. "
            "Answer in as few words as possible. "
            "No pleasantries, no filler. Just the answer."
        ),
        "greeting": "Ready.",
        "error_message": "Error. Retrying.",
        "tool_confirmation_template": "{action}?",
        "traits": ["concise", "direct", "efficient"],
    },
}


@dataclass
class Persona:
    """Represents an agent persona configuration."""

    name: str
    display_name: str = "Gulama"
    description: str = ""
    tone: str = "professional"
    system_prompt_prefix: str = ""
    greeting: str = "Hello! How can I help?"
    error_message: str = "Something went wrong."
    tool_confirmation_template: str = "I'd like to {action}. Shall I proceed?"
    traits: list[str] = field(default_factory=list)
    custom_instructions: str = ""

    def build_system_prompt(self, context: dict[str, Any] | None = None) -> str:
        """Build the full system prompt with persona prefix and context."""
        parts = [self.system_prompt_prefix]

        if self.custom_instructions:
            parts.append(f"\nAdditional instructions: {self.custom_instructions}")

        if context:
            context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
            parts.append(f"\nCurrent context:\n{context_str}")

        return "\n".join(parts)

    def format_confirmation(self, action: str) -> str:
        """Format a tool confirmation message."""
        return self.tool_confirmation_template.format(action=action)

    def to_dict(self) -> dict[str, Any]:
        """Serialize persona to dictionary."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "tone": self.tone,
            "system_prompt_prefix": self.system_prompt_prefix,
            "greeting": self.greeting,
            "error_message": self.error_message,
            "tool_confirmation_template": self.tool_confirmation_template,
            "traits": self.traits,
            "custom_instructions": self.custom_instructions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Persona:
        """Create persona from dictionary."""
        return cls(
            name=data.get("name", "custom"),
            display_name=data.get("display_name", "Gulama"),
            description=data.get("description", ""),
            tone=data.get("tone", "professional"),
            system_prompt_prefix=data.get("system_prompt_prefix", ""),
            greeting=data.get("greeting", "Hello! How can I help?"),
            error_message=data.get("error_message", "Something went wrong."),
            tool_confirmation_template=data.get(
                "tool_confirmation_template", "I'd like to {action}. Shall I proceed?"
            ),
            traits=data.get("traits", []),
            custom_instructions=data.get("custom_instructions", ""),
        )


class PersonaManager:
    """
    Manages agent personas — loading, switching, and creating custom ones.
    """

    def __init__(self):
        self._personas: dict[str, Persona] = {}
        self._active_name: str = "default"
        self._load_builtins()

    def _load_builtins(self) -> None:
        """Load built-in personas."""
        for name, data in BUILT_IN_PERSONAS.items():
            self._personas[name] = Persona.from_dict(data)

    def load_custom_personas(self) -> int:
        """Load custom personas from the personas directory."""
        if not PERSONAS_DIR.exists():
            return 0

        count = 0
        for toml_file in PERSONAS_DIR.glob("*.toml"):
            try:
                import tomli
                with open(toml_file, "rb") as f:
                    data = tomli.load(f)
                persona_data = data.get("persona", data)
                persona = Persona.from_dict(persona_data)
                self._personas[persona.name] = persona
                count += 1
                logger.info("custom_persona_loaded", name=persona.name)
            except Exception as e:
                logger.warning(
                    "persona_load_failed",
                    file=str(toml_file),
                    error=str(e),
                )
        return count

    def save_custom_persona(self, persona: Persona) -> Path:
        """Save a custom persona to disk."""
        PERSONAS_DIR.mkdir(parents=True, exist_ok=True)
        filepath = PERSONAS_DIR / f"{persona.name}.toml"

        import tomli_w
        data = {"persona": persona.to_dict()}
        with open(filepath, "wb") as f:
            tomli_w.dump(data, f)

        self._personas[persona.name] = persona
        logger.info("persona_saved", name=persona.name, path=str(filepath))
        return filepath

    def get(self, name: str) -> Persona | None:
        """Get a persona by name."""
        return self._personas.get(name)

    @property
    def active(self) -> Persona:
        """Get the currently active persona."""
        return self._personas.get(self._active_name, self._personas["default"])

    def set_active(self, name: str) -> Persona:
        """Switch to a different persona."""
        if name not in self._personas:
            raise PersonaError(f"Persona '{name}' not found. Available: {self.list_names()}")
        self._active_name = name
        logger.info("persona_switched", name=name)
        return self._personas[name]

    def list_names(self) -> list[str]:
        """List all available persona names."""
        return sorted(self._personas.keys())

    def list_all(self) -> list[dict[str, Any]]:
        """List all personas with details."""
        return [
            {
                "name": p.name,
                "display_name": p.display_name,
                "description": p.description,
                "tone": p.tone,
                "active": p.name == self._active_name,
            }
            for p in self._personas.values()
        ]

    def create_custom(
        self,
        name: str,
        display_name: str | None = None,
        description: str = "",
        tone: str = "professional",
        system_prompt_prefix: str = "",
        custom_instructions: str = "",
    ) -> Persona:
        """Create a new custom persona."""
        if name in BUILT_IN_PERSONAS:
            raise PersonaError(f"Cannot overwrite built-in persona '{name}'")

        persona = Persona(
            name=name,
            display_name=display_name or name.title(),
            description=description,
            tone=tone,
            system_prompt_prefix=system_prompt_prefix or DEFAULT_PERSONA["system_prompt_prefix"],
            custom_instructions=custom_instructions,
        )
        self._personas[name] = persona
        return persona

    def delete_custom(self, name: str) -> bool:
        """Delete a custom persona."""
        if name in BUILT_IN_PERSONAS:
            raise PersonaError(f"Cannot delete built-in persona '{name}'")
        if name not in self._personas:
            return False

        del self._personas[name]
        if self._active_name == name:
            self._active_name = "default"

        # Delete file if exists
        filepath = PERSONAS_DIR / f"{name}.toml"
        if filepath.exists():
            filepath.unlink()

        logger.info("persona_deleted", name=name)
        return True


class PersonaError(Exception):
    """Raised for persona-related errors."""
    pass
