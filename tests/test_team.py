"""Tests for the team collaboration system."""

from __future__ import annotations

import pytest

from src.security.team import TeamManager, TeamError


class TestTeamManager:
    """Tests for TeamManager."""

    def setup_method(self):
        self.tm = TeamManager()

    def test_create_team(self):
        """Creating a team should work."""
        team = self.tm.create_team("Engineering", "owner1", "The eng team")
        assert team.name == "Engineering"
        assert team.owner_id == "owner1"
        assert "owner1" in team.members
        assert team.members["owner1"].team_role == "owner"

    def test_add_member(self):
        """Adding a member to a team should work."""
        team = self.tm.create_team("Team1", "owner1")
        member = self.tm.add_member(team.id, "user2", role="member", invited_by="owner1")
        assert member is not None
        assert member.team_role == "member"
        assert "user2" in team.members

    def test_add_duplicate_member_fails(self):
        """Adding a user who's already a member should fail."""
        team = self.tm.create_team("Team2", "owner1")
        self.tm.add_member(team.id, "user2")
        with pytest.raises(TeamError, match="already a member"):
            self.tm.add_member(team.id, "user2")

    def test_remove_member(self):
        """Removing a member should work."""
        team = self.tm.create_team("Team3", "owner1")
        self.tm.add_member(team.id, "user2")
        self.tm.remove_member(team.id, "user2")
        assert "user2" not in team.members

    def test_remove_owner_fails(self):
        """Removing the team owner should fail."""
        team = self.tm.create_team("Team4", "owner1")
        with pytest.raises(TeamError, match="Cannot remove the team owner"):
            self.tm.remove_member(team.id, "owner1")

    def test_update_member_role(self):
        """Updating a member's role should work."""
        team = self.tm.create_team("Team5", "owner1")
        self.tm.add_member(team.id, "user2", role="member")
        self.tm.update_member_role(team.id, "user2", "admin")
        assert team.members["user2"].team_role == "admin"

    def test_transfer_ownership(self):
        """Transferring ownership should work."""
        team = self.tm.create_team("Team6", "owner1")
        self.tm.add_member(team.id, "user2")
        self.tm.transfer_ownership(team.id, "user2")
        assert team.owner_id == "user2"
        assert team.members["user2"].team_role == "owner"
        assert team.members["owner1"].team_role == "admin"

    def test_invitation_flow(self):
        """Creating and accepting an invitation should work."""
        team = self.tm.create_team("Team7", "owner1")
        code = self.tm.create_invitation(team.id, "owner1", role="member")
        assert len(code) == 8

        result = self.tm.accept_invitation(code, "invited_user")
        assert result is not None
        assert "invited_user" in team.members

    def test_invitation_reuse_fails(self):
        """Using the same invitation code twice should fail."""
        team = self.tm.create_team("Team8", "owner1")
        code = self.tm.create_invitation(team.id, "owner1")
        self.tm.accept_invitation(code, "user_a")

        with pytest.raises(TeamError, match="Invalid or already used"):
            self.tm.accept_invitation(code, "user_b")

    def test_share_skill(self):
        """Sharing a skill with the team should work."""
        team = self.tm.create_team("Team9", "owner1")
        self.tm.share_skill(team.id, "web_search")
        assert "web_search" in team.shared_skills

    def test_unshare_skill(self):
        """Unsharing a skill should work."""
        team = self.tm.create_team("Team10", "owner1")
        self.tm.share_skill(team.id, "web_search")
        self.tm.unshare_skill(team.id, "web_search")
        assert "web_search" not in team.shared_skills

    def test_get_user_teams(self):
        """Getting all teams for a user should work."""
        team1 = self.tm.create_team("A", "user1")
        team2 = self.tm.create_team("B", "user2")
        self.tm.add_member(team2.id, "user1")

        teams = self.tm.get_user_teams("user1")
        assert len(teams) == 2

    def test_check_team_permission(self):
        """Team permission checks should work."""
        team = self.tm.create_team("PermTeam", "owner1")
        self.tm.add_member(team.id, "viewer1", role="viewer")

        assert self.tm.check_team_permission(team.id, "owner1", "can_delete_team")
        assert not self.tm.check_team_permission(team.id, "viewer1", "can_delete_team")
        assert self.tm.check_team_permission(team.id, "viewer1", "can_view_audit")

    def test_delete_team(self):
        """Deleting a team should soft-delete it."""
        team = self.tm.create_team("DeleteMe", "owner1")
        self.tm.delete_team(team.id)
        assert not team.is_active
        assert self.tm.list_teams() == []

    def test_max_members_limit(self):
        """Adding members beyond the limit should fail."""
        team = self.tm.create_team("SmallTeam", "owner1")
        team.settings["max_members"] = 2
        self.tm.add_member(team.id, "user2")
        with pytest.raises(TeamError, match="member limit"):
            self.tm.add_member(team.id, "user3")
