"""통합 타임라인 빌더 모듈

GitHub 커밋/PR, Claude Code 세션, Codex 엔트리를 통합하여
시간순 타임라인을 생성합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime

from .github import (
    CommitInfo,
    PRInfo,
    get_weekly_commits,
    get_weekly_prs,
    get_week_range,
)
from .session_parser import SessionInfo, get_weekly_sessions
from .codex_parser import CodexEntry, get_weekly_codex_entries


@dataclass
class TimelineEvent:
    """타임라인 이벤트 데이터클래스"""

    timestamp: datetime
    source: str  # "github_commit" | "github_pr" | "claude_session" | "codex_entry"
    title: str
    detail: str
    project: str
    metadata: dict = field(default_factory=dict)


def _collect_commit_events(
    username: str, repos: list[str] | None, week_offset: int,
) -> list[TimelineEvent]:
    """GitHub 커밋을 타임라인 이벤트로 변환"""
    try:
        return [
            TimelineEvent(
                timestamp=c.date,
                source="github_commit",
                title=c.message,
                detail=f"{c.repo_name} +{c.additions}/-{c.deletions}",
                project=c.repo_name,
            )
            for c in get_weekly_commits(username, repos, week_offset)
        ]
    except Exception:
        return []


def _collect_pr_events(
    username: str, repos: list[str] | None, week_offset: int,
) -> list[TimelineEvent]:
    """GitHub PR을 타임라인 이벤트로 변환"""
    try:
        return [
            TimelineEvent(
                timestamp=pr.created_at,
                source="github_pr",
                title=pr.title,
                detail=f"#{pr.number} {pr.state}",
                project=pr.repo_name,
            )
            for pr in get_weekly_prs(username, repos, week_offset)
        ]
    except Exception:
        return []


def _collect_session_events(week_offset: int) -> list[TimelineEvent]:
    """Claude Code 세션을 타임라인 이벤트로 변환"""
    try:
        return [
            TimelineEvent(
                timestamp=s.created,
                source="claude_session",
                title=s.first_prompt,
                detail=f"{s.message_count} messages",
                project=s.project_path,
            )
            for s in get_weekly_sessions(week_offset)
        ]
    except Exception:
        return []


def _collect_codex_events(week_offset: int) -> list[TimelineEvent]:
    """Codex 엔트리를 타임라인 이벤트로 변환"""
    try:
        return [
            TimelineEvent(
                timestamp=e.timestamp,
                source="codex_entry",
                title=e.text[:80],
                detail=e.text,
                project="codex",
            )
            for e in get_weekly_codex_entries(week_offset)
        ]
    except Exception:
        return []


def _compute_statistics(events: list[TimelineEvent]) -> dict:
    """이벤트 목록에서 소스별/프로젝트별/일별 통계 계산"""
    by_source: dict[str, int] = {}
    by_project: dict[str, int] = {}
    by_day: dict[str, int] = {}

    for event in events:
        by_source[event.source] = by_source.get(event.source, 0) + 1
        by_project[event.project] = by_project.get(event.project, 0) + 1
        day_str = event.timestamp.strftime("%Y-%m-%d")
        by_day[day_str] = by_day.get(day_str, 0) + 1

    return {"by_source": by_source, "by_project": by_project, "by_day": by_day}


def build_weekly_timeline(
    username: str,
    week_offset: int = 0,
    repos: list[str] | None = None,
) -> dict:
    """주간 통합 타임라인 생성

    Args:
        username: GitHub 사용자명
        week_offset: 주차 오프셋 (0=이번주, -1=지난주...)
        repos: 특정 저장소 목록 (None이면 전체)

    Returns:
        기간, 이벤트 목록, 통계를 포함한 딕셔너리
    """
    events = (
        _collect_commit_events(username, repos, week_offset)
        + _collect_pr_events(username, repos, week_offset)
        + _collect_session_events(week_offset)
        + _collect_codex_events(week_offset)
    )
    events.sort(key=lambda e: e.timestamp)

    start, end = get_week_range(week_offset)

    return {
        "period": {
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
        },
        "events": [
            {
                "timestamp": e.timestamp.isoformat(),
                "source": e.source,
                "title": e.title,
                "detail": e.detail,
                "project": e.project,
            }
            for e in events
        ],
        "statistics": _compute_statistics(events),
    }
