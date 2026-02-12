"""Claude Code session parser module.

Parses Claude Code session data from ~/.claude/projects/*/sessions-index.json
and associated JSONL files to extract session information, messages, and analytics.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .github import get_week_range


@dataclass
class SessionInfo:
    """Information about a Claude Code session."""

    session_id: str
    first_prompt: str
    summary: str
    message_count: int
    created: datetime
    modified: datetime
    project_path: str
    git_branch: str = ""
    source: str = "claude_code"


@dataclass
class SessionMessage:
    """Individual message within a session."""

    message_id: str
    session_id: str
    timestamp: datetime
    role: str  # "user" | "assistant"
    content_text: str
    tool_uses: list[str] = field(default_factory=list)


@dataclass
class SessionAnalysis:
    """Analytics data for a session."""

    session_id: str
    session_info: SessionInfo
    total_messages: int
    user_messages: int
    assistant_messages: int
    tools_used: dict[str, int]
    files_touched: list[str]
    error_count: int = 0
    duration_minutes: float = 0.0
    topics: list[str] = field(default_factory=list)


def _parse_iso_timestamp(iso_str: str) -> datetime:
    """Parse ISO 8601 timestamp to naive datetime.

    Handles 'Z' suffix and timezone info by converting to UTC then removing tzinfo.
    """
    # Replace 'Z' with '+00:00' for proper parsing
    if iso_str.endswith('Z'):
        iso_str = iso_str[:-1] + '+00:00'

    dt = datetime.fromisoformat(iso_str)

    # Convert to naive datetime (strip timezone info)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)

    return dt


def get_claude_projects_dirs() -> list[Path]:
    """Discover all project directories under ~/.claude/projects/.

    Returns:
        List of Path objects for each project directory. Empty list if base directory doesn't exist.
    """
    claude_projects = Path.home() / ".claude" / "projects"

    if not claude_projects.exists():
        return []

    # Return all subdirectories
    return [d for d in claude_projects.iterdir() if d.is_dir()]


def get_all_session_indices() -> list[SessionInfo]:
    """Scan all project directories for sessions-index.json and parse entries.

    Returns:
        List of SessionInfo objects. Skips invalid JSON gracefully.
    """
    sessions = []

    for project_dir in get_claude_projects_dirs():
        index_file = project_dir / "sessions-index.json"

        if not index_file.exists():
            continue

        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            entries = data.get('entries', [])

            for entry in entries:
                try:
                    session_info = SessionInfo(
                        session_id=entry['sessionId'],
                        first_prompt=entry.get('firstPrompt', ''),
                        summary=entry.get('summary', ''),
                        message_count=entry.get('messageCount', 0),
                        created=_parse_iso_timestamp(entry['created']),
                        modified=_parse_iso_timestamp(entry['modified']),
                        project_path=entry.get('projectPath', ''),
                    )
                    sessions.append(session_info)
                except (KeyError, ValueError) as e:
                    # Skip malformed entries
                    continue

        except (json.JSONDecodeError, IOError):
            # Skip files with invalid JSON or read errors
            continue

    return sessions


def get_weekly_sessions(
    week_offset: int = 0,
    project_filter: str | None = None
) -> list[SessionInfo]:
    """Filter sessions by week range.

    Args:
        week_offset: Week offset (0=this week, -1=last week, etc.)
        project_filter: Optional substring to match against project_path

    Returns:
        List of SessionInfo objects within the specified week.
    """
    start, end = get_week_range(week_offset)
    all_sessions = get_all_session_indices()

    filtered = []
    for session in all_sessions:
        # Check week range (use created timestamp)
        if not (start <= session.created <= end):
            continue

        # Check project filter if provided
        if project_filter and project_filter not in session.project_path:
            continue

        filtered.append(session)

    return filtered


def parse_session_messages(file_path: str, session_id: str) -> list[SessionMessage]:
    """Parse JSONL file containing session messages.

    Args:
        file_path: Path to JSONL file
        session_id: Session ID to associate with messages

    Returns:
        List of SessionMessage objects. Skips invalid lines gracefully.
    """
    messages = []
    file_path_obj = Path(file_path)

    if not file_path_obj.exists():
        return messages

    try:
        with open(file_path_obj, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)

                    role = data.get('type', '')
                    if role not in ('user', 'assistant'):
                        continue

                    message_id = data.get('uuid', '')
                    timestamp_str = data.get('timestamp', '')

                    if not timestamp_str:
                        continue

                    timestamp = _parse_iso_timestamp(timestamp_str)

                    # Extract content text and tool uses
                    content_blocks = data.get('message', {}).get('content', [])
                    text_parts = []
                    tool_uses = []

                    for block in content_blocks:
                        if block.get('type') == 'text':
                            text_parts.append(block.get('text', ''))
                        elif block.get('type') == 'tool_use':
                            tool_name = block.get('name', '')
                            if tool_name:
                                tool_uses.append(tool_name)

                    content_text = '\n'.join(text_parts)

                    message = SessionMessage(
                        message_id=message_id,
                        session_id=session_id,
                        timestamp=timestamp,
                        role=role,
                        content_text=content_text,
                        tool_uses=tool_uses,
                    )
                    messages.append(message)

                except (json.JSONDecodeError, KeyError, ValueError):
                    # Skip malformed lines
                    continue

    except IOError:
        # Return empty list on read errors
        pass

    return messages


def analyze_session(info: SessionInfo, jsonl_path: str) -> SessionAnalysis:
    """Analyze a session by parsing its messages.

    Args:
        info: SessionInfo object
        jsonl_path: Path to the session's JSONL file

    Returns:
        SessionAnalysis object with computed metrics.
    """
    messages = parse_session_messages(jsonl_path, info.session_id)

    user_count = 0
    assistant_count = 0
    tools_used: dict[str, int] = {}
    files_touched: list[str] = []
    error_count = 0

    for msg in messages:
        if msg.role == 'user':
            user_count += 1
        elif msg.role == 'assistant':
            assistant_count += 1

        # Count tool uses
        for tool in msg.tool_uses:
            tools_used[tool] = tools_used.get(tool, 0) + 1

    # Calculate duration
    duration_minutes = 0.0
    if len(messages) >= 2:
        first_ts = messages[0].timestamp
        last_ts = messages[-1].timestamp
        duration_seconds = (last_ts - first_ts).total_seconds()
        duration_minutes = duration_seconds / 60.0

    # Parse JSONL again to check for errors and extract files
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)

                    # Check for tool_result errors
                    content_blocks = data.get('message', {}).get('content', [])
                    for block in content_blocks:
                        if block.get('type') == 'tool_result':
                            if block.get('is_error', False):
                                error_count += 1

                        # Extract files from Write/Edit tool uses
                        if block.get('type') == 'tool_use':
                            tool_name = block.get('name', '')
                            tool_input = block.get('input', {})

                            if tool_name in ('Write', 'Edit') and 'file_path' in tool_input:
                                file_path = tool_input['file_path']
                                if file_path not in files_touched:
                                    files_touched.append(file_path)

                except (json.JSONDecodeError, KeyError):
                    continue

    except IOError:
        pass

    return SessionAnalysis(
        session_id=info.session_id,
        session_info=info,
        total_messages=len(messages),
        user_messages=user_count,
        assistant_messages=assistant_count,
        tools_used=tools_used,
        files_touched=files_touched,
        error_count=error_count,
        duration_minutes=duration_minutes,
    )
