"""Gulama built-in skills — file manager, shell, web search, notes, browser, email, calendar, code exec."""

from src.skills.builtin.browser import BrowserSkill
from src.skills.builtin.calendar_skill import CalendarSkill
from src.skills.builtin.code_exec import CodeExecSkill
from src.skills.builtin.email_skill import EmailSkill
from src.skills.builtin.file_manager import FileManagerSkill
from src.skills.builtin.notes import NotesSkill
from src.skills.builtin.shell_exec import ShellExecSkill
from src.skills.builtin.web_search import WebSearchSkill

__all__ = [
    "BrowserSkill",
    "CalendarSkill",
    "CodeExecSkill",
    "EmailSkill",
    "FileManagerSkill",
    "NotesSkill",
    "ShellExecSkill",
    "WebSearchSkill",
]
