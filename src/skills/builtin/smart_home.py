"""
Smart home integration skill for Gulama.

Connects to Home Assistant via its REST API / WebSocket API.
Supports controlling lights, switches, climate, media, and more.

Requires:
- Home Assistant instance running (local or cloud)
- Long-lived access token from HA
- HA_URL and HA_TOKEN env vars

Requires: pip install httpx
"""

from __future__ import annotations

import os
from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("smart_home")


class SmartHomeSkill(BaseSkill):
    """
    Home Assistant integration skill.

    Actions:
    - list_devices: List all devices/entities
    - get_state: Get state of an entity
    - turn_on: Turn on an entity (light, switch, etc.)
    - turn_off: Turn off an entity
    - set_state: Set specific state (brightness, temperature, etc.)
    - call_service: Call any HA service
    - list_automations: List HA automations
    """

    def __init__(self) -> None:
        self._ha_url: str = ""
        self._ha_token: str = ""
        self._configured = False

    def _load_config(self) -> None:
        """Lazy-load Home Assistant config."""
        if self._configured:
            return
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        self._ha_url = os.getenv("HA_URL", "http://homeassistant.local:8123")
        self._ha_token = os.getenv("HA_TOKEN", "")
        self._configured = True

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="smart_home",
            description="Control smart home devices via Home Assistant",
            version="1.0.0",
            author="gulama",
            required_actions=[ActionType.NETWORK_REQUEST],
            is_builtin=True,
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "smart_home",
                "description": (
                    "Control smart home devices via Home Assistant. "
                    "Actions: list_devices, get_state, turn_on, turn_off, set_state, call_service"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "list_devices",
                                "get_state",
                                "turn_on",
                                "turn_off",
                                "set_state",
                                "call_service",
                                "list_automations",
                            ],
                            "description": "Smart home action to perform",
                        },
                        "entity_id": {
                            "type": "string",
                            "description": "Entity ID (e.g., light.living_room, switch.fan)",
                        },
                        "domain": {
                            "type": "string",
                            "description": "Entity domain filter (e.g., light, switch, climate)",
                        },
                        "service": {
                            "type": "string",
                            "description": "HA service to call (for call_service action)",
                        },
                        "service_data": {
                            "type": "object",
                            "description": "Data for the service call (brightness, temperature, etc.)",
                        },
                    },
                    "required": ["action"],
                },
            },
        }

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Execute a smart home action."""
        action = kwargs.get("action", "list_devices")

        dispatch = {
            "list_devices": self._list_devices,
            "get_state": self._get_state,
            "turn_on": self._turn_on,
            "turn_off": self._turn_off,
            "set_state": self._set_state,
            "call_service": self._call_service,
            "list_automations": self._list_automations,
        }

        handler = dispatch.get(action)
        if not handler:
            return SkillResult(
                success=False,
                output="",
                error=f"Unknown smart home action: {action}",
            )

        self._load_config()

        if not self._ha_token:
            return SkillResult(
                success=False,
                output="",
                error="Home Assistant not configured. Set HA_URL and HA_TOKEN env vars.",
            )

        try:
            return await handler(**{k: v for k, v in kwargs.items() if k != "action"})
        except ImportError:
            return SkillResult(
                success=False,
                output="",
                error="httpx is required. Install: pip install httpx",
            )
        except Exception as e:
            logger.error("smart_home_error", action=action, error=str(e))
            return SkillResult(success=False, output="", error=f"Smart home error: {str(e)[:300]}")

    async def _ha_request(self, method: str, path: str, json_data: dict | None = None) -> dict:
        """Make a request to the Home Assistant API."""
        import httpx

        url = f"{self._ha_url}/api{path}"
        headers = {
            "Authorization": f"Bearer {self._ha_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=json_data or {})
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json() if response.text else {}

    async def _list_devices(self, domain: str = "", **_: Any) -> SkillResult:
        """List all entities/devices."""
        states = await self._ha_request("GET", "/states")

        if domain:
            states = [s for s in states if s.get("entity_id", "").startswith(f"{domain}.")]

        if not states:
            return SkillResult(success=True, output="No devices found.")

        lines = []
        for state in states[:50]:  # Limit to 50
            entity_id = state.get("entity_id", "")
            friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)
            current_state = state.get("state", "unknown")
            lines.append(f"  {entity_id}: {friendly_name} — {current_state}")

        return SkillResult(
            success=True,
            output=f"Devices ({len(states)} total):\n" + "\n".join(lines),
            metadata={"count": len(states)},
        )

    async def _get_state(self, entity_id: str = "", **_: Any) -> SkillResult:
        """Get state of a specific entity."""
        if not entity_id:
            return SkillResult(success=False, output="", error="entity_id is required")

        state = await self._ha_request("GET", f"/states/{entity_id}")

        friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)
        current_state = state.get("state", "unknown")
        attrs = state.get("attributes", {})

        lines = [
            f"Entity: {entity_id}",
            f"Name: {friendly_name}",
            f"State: {current_state}",
        ]

        # Add relevant attributes
        for key in (
            "brightness",
            "color_temp",
            "temperature",
            "humidity",
            "current_temperature",
            "fan_mode",
            "media_title",
        ):
            if key in attrs:
                lines.append(f"{key}: {attrs[key]}")

        return SkillResult(success=True, output="\n".join(lines))

    async def _turn_on(
        self, entity_id: str = "", service_data: dict | None = None, **_: Any
    ) -> SkillResult:
        """Turn on an entity."""
        if not entity_id:
            return SkillResult(success=False, output="", error="entity_id is required")

        domain = entity_id.split(".")[0]
        data = {"entity_id": entity_id}
        if service_data:
            data.update(service_data)

        await self._ha_request("POST", f"/services/{domain}/turn_on", data)
        return SkillResult(success=True, output=f"Turned on: {entity_id}")

    async def _turn_off(self, entity_id: str = "", **_: Any) -> SkillResult:
        """Turn off an entity."""
        if not entity_id:
            return SkillResult(success=False, output="", error="entity_id is required")

        domain = entity_id.split(".")[0]
        await self._ha_request("POST", f"/services/{domain}/turn_off", {"entity_id": entity_id})
        return SkillResult(success=True, output=f"Turned off: {entity_id}")

    async def _set_state(
        self,
        entity_id: str = "",
        service_data: dict | None = None,
        **_: Any,
    ) -> SkillResult:
        """Set state with specific attributes (brightness, temp, etc)."""
        if not entity_id:
            return SkillResult(success=False, output="", error="entity_id is required")
        if not service_data:
            return SkillResult(success=False, output="", error="service_data is required")

        domain = entity_id.split(".")[0]
        data = {"entity_id": entity_id}
        data.update(service_data)

        await self._ha_request("POST", f"/services/{domain}/turn_on", data)
        return SkillResult(
            success=True,
            output=f"Set {entity_id}: {service_data}",
        )

    async def _call_service(
        self,
        service: str = "",
        entity_id: str = "",
        service_data: dict | None = None,
        **_: Any,
    ) -> SkillResult:
        """Call any Home Assistant service."""
        if not service:
            return SkillResult(
                success=False, output="", error="service is required (e.g., 'light/toggle')"
            )

        parts = service.split("/")
        if len(parts) != 2:
            return SkillResult(
                success=False,
                output="",
                error="service format: 'domain/service' (e.g., 'light/toggle')",
            )

        domain, svc = parts
        data = {}
        if entity_id:
            data["entity_id"] = entity_id
        if service_data:
            data.update(service_data)

        await self._ha_request("POST", f"/services/{domain}/{svc}", data)
        return SkillResult(success=True, output=f"Called service: {service}")

    async def _list_automations(self, **_: Any) -> SkillResult:
        """List Home Assistant automations."""
        states = await self._ha_request("GET", "/states")
        automations = [s for s in states if s.get("entity_id", "").startswith("automation.")]

        if not automations:
            return SkillResult(success=True, output="No automations found.")

        lines = []
        for auto in automations:
            entity_id = auto.get("entity_id", "")
            name = auto.get("attributes", {}).get("friendly_name", entity_id)
            state = auto.get("state", "unknown")
            lines.append(f"  {entity_id}: {name} — {state}")

        return SkillResult(
            success=True,
            output=f"Automations ({len(automations)}):\n" + "\n".join(lines),
        )
