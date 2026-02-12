"""Codex session parser module.

This module parses Codex AI CLI session history from ~/.codex/history.jsonl
and provides structured access to weekly session data.
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime

from work_journal.github import get_week_range


@dataclass
class CodexEntry:
    """Represents a single Codex session entry."""
    session_id: str
    timestamp: datetime
    text: str
    source: str = "codex"


def get_codex_history_path() -> str:
    """Return the path to Codex history file.

    Returns:
        str: Absolute path to ~/.codex/history.jsonl
    """
    return os.path.join(os.path.expanduser("~"), ".codex", "history.jsonl")


def get_weekly_codex_entries(week_offset: int = 0) -> list[CodexEntry]:
    """Get Codex entries for a specific week.

    Args:
        week_offset: Week offset (0=this week, -1=last week, etc.)

    Returns:
        List of CodexEntry objects sorted by timestamp
    """
    history_path = get_codex_history_path()

    # Handle missing file
    if not os.path.exists(history_path):
        return []

    # Get week range for filtering
    start_dt, end_dt = get_week_range(week_offset)

    entries = []

    try:
        with open(history_path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)

                    # Extract required fields
                    ts = data.get('ts')
                    prompt = data.get('prompt')

                    if ts is None or prompt is None:
                        continue

                    # Convert Unix timestamp to datetime
                    timestamp = datetime.fromtimestamp(ts)

                    # Filter by week range
                    if start_dt <= timestamp < end_dt:
                        entry = CodexEntry(
                            session_id=f"codex_{idx}",
                            timestamp=timestamp,
                            text=prompt,
                            source="codex"
                        )
                        entries.append(entry)

                except json.JSONDecodeError:
                    # Skip invalid JSON lines gracefully
                    continue
                except (ValueError, OSError):
                    # Skip invalid timestamp or other errors
                    continue

    except (IOError, OSError):
        # Handle file read errors
        return []

    # Sort by timestamp
    entries.sort(key=lambda x: x.timestamp)

    return entries
