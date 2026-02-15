"""
Team collaboration for Gulama Enterprise.

Provides multi-user workspace support with:
- Team creation and management
- Shared memory spaces
- Shared skill access
- Audit trail per team member
- Role-based team permissions
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.utils.logging import get_logger

logger = get_logger("team")


@dataclass
class TeamMember:
    """A team member with a specific team role."""

    user_id: str
    team_role: str = "member"  # "owner", "admin", "member", "viewer"
    joined_at: str = ""
    invited_by: str = ""


@dataclass
class Team:
    """A Gulama team / workspace."""

    id: str
    name: str
    description: str = ""
    owner_id: str = ""
    created_at: str = ""
    members: dict[str, TeamMember] = field(default_factory=dict)  # user_id -> TeamMember
    settings: dict[str, Any] = field(default_factory=dict)
    shared_skills: list[str] = field(default_factory=list)
    is_active: bool = True


TEAM_ROLES = {
    "owner": {
        "can_manage_team": True,
        "can_invite": True,
        "can_remove": True,
        "can_manage_skills": True,
        "can_view_audit": True,
        "can_share_memory": True,
        "can_delete_team": True,
    },
    "admin": {
        "can_manage_team": True,
        "can_invite": True,
        "can_remove": True,
        "can_manage_skills": True,
        "can_view_audit": True,
        "can_share_memory": True,
        "can_delete_team": False,
    },
    "member": {
        "can_manage_team": False,
        "can_invite": False,
        "can_remove": False,
        "can_manage_skills": False,
        "can_view_audit": False,
        "can_share_memory": True,
        "can_delete_team": False,
    },
    "viewer": {
        "can_manage_team": False,
        "can_invite": False,
        "can_remove": False,
        "can_manage_skills": False,
        "can_view_audit": True,
        "can_share_memory": False,
        "can_delete_team": False,
    },
}


class TeamManager:
    """
    Manages teams and collaborative workspaces.

    Features:
    - Create/delete teams
    - Add/remove members with role-based permissions
    - Shared skill management
    - Team-scoped memory and audit logs
    - Invitation system
    """

    def __init__(self):
        self._teams: dict[str, Team] = {}
        self._user_teams: dict[str, set[str]] = {}  # user_id -> set of team_ids
        self._invitations: dict[str, dict[str, Any]] = {}  # invite_code -> details

    def create_team(self, name: str, owner_id: str, description: str = "") -> Team:
        """Create a new team."""
        team_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        team = Team(
            id=team_id,
            name=name,
            description=description,
            owner_id=owner_id,
            created_at=now,
            members={
                owner_id: TeamMember(
                    user_id=owner_id,
                    team_role="owner",
                    joined_at=now,
                )
            },
            settings={
                "shared_memory_enabled": True,
                "skill_sharing_enabled": True,
                "audit_visibility": "admin",  # "admin", "all"
                "max_members": 50,
            },
        )

        self._teams[team_id] = team
        self._user_teams.setdefault(owner_id, set()).add(team_id)

        logger.info("team_created", team_id=team_id, name=name, owner=owner_id)
        return team

    def get_team(self, team_id: str) -> Team | None:
        """Get a team by ID."""
        return self._teams.get(team_id)

    def add_member(
        self,
        team_id: str,
        user_id: str,
        role: str = "member",
        invited_by: str = "",
    ) -> TeamMember | None:
        """Add a member to a team."""
        team = self._teams.get(team_id)
        if not team:
            raise TeamError(f"Team not found: {team_id}")

        if role not in TEAM_ROLES:
            raise TeamError(f"Invalid team role: {role}")

        if user_id in team.members:
            raise TeamError(f"User {user_id} is already a member of team {team.name}")

        if len(team.members) >= team.settings.get("max_members", 50):
            raise TeamError(f"Team {team.name} has reached its member limit")

        member = TeamMember(
            user_id=user_id,
            team_role=role,
            joined_at=datetime.now(UTC).isoformat(),
            invited_by=invited_by,
        )

        team.members[user_id] = member
        self._user_teams.setdefault(user_id, set()).add(team_id)

        logger.info(
            "member_added",
            team=team.name,
            user=user_id,
            role=role,
            invited_by=invited_by,
        )
        return member

    def remove_member(self, team_id: str, user_id: str) -> None:
        """Remove a member from a team."""
        team = self._teams.get(team_id)
        if not team:
            raise TeamError(f"Team not found: {team_id}")

        if user_id not in team.members:
            raise TeamError(f"User {user_id} is not a member of team {team.name}")

        if team.members[user_id].team_role == "owner":
            raise TeamError("Cannot remove the team owner. Transfer ownership first.")

        del team.members[user_id]
        if user_id in self._user_teams:
            self._user_teams[user_id].discard(team_id)

        logger.info("member_removed", team=team.name, user=user_id)

    def update_member_role(self, team_id: str, user_id: str, new_role: str) -> None:
        """Update a team member's role."""
        team = self._teams.get(team_id)
        if not team:
            raise TeamError(f"Team not found: {team_id}")
        if user_id not in team.members:
            raise TeamError(f"User {user_id} not in team {team.name}")
        if new_role not in TEAM_ROLES:
            raise TeamError(f"Invalid team role: {new_role}")
        if team.members[user_id].team_role == "owner" and new_role != "owner":
            raise TeamError("Cannot demote the owner. Transfer ownership first.")

        old_role = team.members[user_id].team_role
        team.members[user_id].team_role = new_role
        logger.info(
            "member_role_updated",
            team=team.name,
            user=user_id,
            old_role=old_role,
            new_role=new_role,
        )

    def transfer_ownership(self, team_id: str, new_owner_id: str) -> None:
        """Transfer team ownership to another member."""
        team = self._teams.get(team_id)
        if not team:
            raise TeamError(f"Team not found: {team_id}")
        if new_owner_id not in team.members:
            raise TeamError(f"User {new_owner_id} is not a member of team {team.name}")

        old_owner = team.owner_id
        team.members[old_owner].team_role = "admin"
        team.members[new_owner_id].team_role = "owner"
        team.owner_id = new_owner_id

        logger.info(
            "ownership_transferred",
            team=team.name,
            old_owner=old_owner,
            new_owner=new_owner_id,
        )

    def create_invitation(self, team_id: str, invited_by: str, role: str = "member") -> str:
        """Create a team invitation code."""
        team = self._teams.get(team_id)
        if not team:
            raise TeamError(f"Team not found: {team_id}")

        code = str(uuid.uuid4())[:8].upper()
        self._invitations[code] = {
            "team_id": team_id,
            "invited_by": invited_by,
            "role": role,
            "created_at": datetime.now(UTC).isoformat(),
            "used": False,
        }

        logger.info("invitation_created", team=team.name, code=code)
        return code

    def accept_invitation(self, code: str, user_id: str) -> Team | None:
        """Accept a team invitation."""
        invite = self._invitations.get(code)
        if not invite or invite["used"]:
            raise TeamError("Invalid or already used invitation code")

        team_id = invite["team_id"]
        self.add_member(
            team_id,
            user_id,
            role=invite["role"],
            invited_by=invite["invited_by"],
        )

        invite["used"] = True
        return self._teams.get(team_id)

    def share_skill(self, team_id: str, skill_name: str) -> None:
        """Share a skill with the team."""
        team = self._teams.get(team_id)
        if not team:
            raise TeamError(f"Team not found: {team_id}")
        if skill_name not in team.shared_skills:
            team.shared_skills.append(skill_name)
            logger.info("skill_shared", team=team.name, skill=skill_name)

    def unshare_skill(self, team_id: str, skill_name: str) -> None:
        """Remove a shared skill from the team."""
        team = self._teams.get(team_id)
        if not team:
            raise TeamError(f"Team not found: {team_id}")
        if skill_name in team.shared_skills:
            team.shared_skills.remove(skill_name)

    def get_user_teams(self, user_id: str) -> list[dict[str, Any]]:
        """Get all teams a user belongs to."""
        team_ids = self._user_teams.get(user_id, set())
        result = []
        for tid in team_ids:
            team = self._teams.get(tid)
            if team and team.is_active:
                member = team.members.get(user_id)
                result.append(
                    {
                        "team_id": team.id,
                        "name": team.name,
                        "role": member.team_role if member else "unknown",
                        "member_count": len(team.members),
                    }
                )
        return result

    def check_team_permission(self, team_id: str, user_id: str, permission: str) -> bool:
        """Check if a user has a specific team permission."""
        team = self._teams.get(team_id)
        if not team:
            return False

        member = team.members.get(user_id)
        if not member:
            return False

        role_perms = TEAM_ROLES.get(member.team_role, {})
        return role_perms.get(permission, False)

    def list_teams(self) -> list[dict[str, Any]]:
        """List all active teams."""
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "owner_id": t.owner_id,
                "member_count": len(t.members),
                "created_at": t.created_at,
                "shared_skills": t.shared_skills,
            }
            for t in self._teams.values()
            if t.is_active
        ]

    def delete_team(self, team_id: str) -> None:
        """Soft-delete a team."""
        team = self._teams.get(team_id)
        if not team:
            raise TeamError(f"Team not found: {team_id}")

        team.is_active = False

        # Clean up user-team mappings
        for uid in team.members:
            if uid in self._user_teams:
                self._user_teams[uid].discard(team_id)

        logger.info("team_deleted", team_id=team_id, name=team.name)


class TeamError(Exception):
    """Raised for team-related errors."""

    pass
