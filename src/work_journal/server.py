"""mcp-devdiary 서버 메인 모듈 - MCP 도구 등록 및 실행"""

from fastmcp import FastMCP

from .github import get_weekly_commits, get_weekly_prs, CommitInfo, get_week_range
from .session_parser import get_weekly_sessions, analyze_session
from .codex_parser import get_weekly_codex_entries
from .timeline import build_weekly_timeline
from .few_shot import FewShotLoader
from .insights import InsightAnalyzer


# MCP 서버 인스턴스 생성
mcp = FastMCP("mcp-devdiary")


# ===== 내부 헬퍼 함수 =====


def _format_period(week_offset: int) -> dict:
    """주차 오프셋으로 기간 정보 딕셔너리 생성"""
    start, end = get_week_range(week_offset)
    return {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d")}


def _group_commits_by_repo(commits: list[CommitInfo]) -> dict[str, list]:
    """커밋을 저장소별로 그룹화하여 간략 정보로 변환"""
    result: dict[str, list] = {}
    for c in commits:
        if c.repo_name not in result:
            result[c.repo_name] = []
        result[c.repo_name].append({
            "sha": c.sha,
            "message": c.message,
            "date": c.date.strftime("%Y-%m-%d %H:%M"),
            "additions": c.additions,
            "deletions": c.deletions,
        })
    return result


def _fetch_sessions_safe(
    week_offset: int, project_filter: str | None = None,
) -> list:
    """세션 데이터를 안전하게 가져오기 (실패 시 빈 리스트)"""
    try:
        return get_weekly_sessions(week_offset, project_filter)
    except Exception:
        return []


def _fetch_codex_safe(week_offset: int) -> list:
    """Codex 엔트리를 안전하게 가져오기 (실패 시 빈 리스트)"""
    try:
        return get_weekly_codex_entries(week_offset)
    except Exception:
        return []


# ===== MCP 도구 핸들러 =====


@mcp.tool()
def get_commits(
    username: str,
    repos: list[str] | None = None,
    week_offset: int = 0,
) -> dict:
    """GitHub에서 주간 커밋을 조회합니다.

    Args:
        username: GitHub 사용자명
        repos: 특정 저장소 목록 (선택사항, 없으면 전체 조회)
        week_offset: 주차 오프셋 (0=이번주, -1=지난주, -2=2주전...)

    Returns:
        커밋 목록과 통계 정보
    """
    commits = get_weekly_commits(username, repos, week_offset)

    return {
        "period": _format_period(week_offset),
        "total_commits": len(commits),
        "commits": [
            {
                "sha": c.sha,
                "message": c.message,
                "author": c.author,
                "date": c.date.isoformat(),
                "repo": c.repo_name,
                "url": c.url,
                "additions": c.additions,
                "deletions": c.deletions,
            }
            for c in commits
        ],
        "summary": {
            "total_additions": sum(c.additions for c in commits),
            "total_deletions": sum(c.deletions for c in commits),
            "repos": list(set(c.repo_name for c in commits)),
        },
    }


@mcp.tool()
def get_weekly_activity(
    username: str,
    week_offset: int = 0,
    repos: list[str] | None = None,
) -> dict:
    """주간 GitHub 활동(커밋 + PR)을 조회합니다.

    커밋과 PR 데이터를 함께 수집하여 주간 업무일지 작성에 필요한
    모든 정보를 반환합니다. Claude가 이 데이터로 요약을 생성합니다.

    Args:
        username: GitHub 사용자명
        week_offset: 주차 오프셋 (0=이번주, -1=지난주...)
        repos: 특정 저장소 목록 (선택사항)

    Returns:
        커밋, PR, 통계 정보를 포함한 딕셔너리
    """
    commits = get_weekly_commits(username, repos, week_offset)
    prs = get_weekly_prs(username, repos, week_offset)
    sessions = _fetch_sessions_safe(week_offset)

    return {
        "username": username,
        "period": {**_format_period(week_offset), "week_offset": week_offset},
        "statistics": {
            "total_commits": len(commits),
            "total_prs": len(prs),
            "total_additions": sum(c.additions for c in commits),
            "total_deletions": sum(c.deletions for c in commits),
            "active_repos": list(set(c.repo_name for c in commits)),
        },
        "commits_by_repo": _group_commits_by_repo(commits),
        "pull_requests": [
            {
                "number": pr.number,
                "title": pr.title,
                "state": pr.state,
                "repo": pr.repo_name,
                "created_at": pr.created_at.strftime("%Y-%m-%d"),
                "merged": pr.merged_at is not None,
                "additions": pr.additions,
                "deletions": pr.deletions,
            }
            for pr in prs
        ],
        "agent_sessions": {
            "claude_sessions": [
                {
                    "session_id": s.session_id,
                    "first_prompt": s.first_prompt,
                    "summary": s.summary,
                    "message_count": s.message_count,
                    "created": s.created.isoformat(),
                    "project_path": s.project_path,
                }
                for s in sessions
            ],
            "total_sessions": len(sessions),
            "total_messages": sum(s.message_count for s in sessions),
        },
    }


@mcp.tool()
def get_activity_for_resume(
    username: str,
    weeks_range: int = 4,
    week_offset: int = 0,
    repos: list[str] | None = None,
) -> dict:
    """이력서 작성용 GitHub 활동 데이터를 조회합니다.

    지정된 기간의 GitHub 활동을 수집하여 이력서 성과 문장 작성에
    필요한 데이터를 반환합니다. Claude가 STAR 포맷으로 변환합니다.

    Args:
        username: GitHub 사용자명
        weeks_range: 분석할 주 수 (기본 4주)
        week_offset: 시작 주차 오프셋 (0=이번주부터)
        repos: 특정 저장소 목록 (선택사항)

    Returns:
        기간별 활동 요약 데이터
    """
    all_commits: list[CommitInfo] = []
    all_prs = []

    for i in range(weeks_range):
        offset = week_offset - i
        all_commits.extend(get_weekly_commits(username, repos, offset))
        all_prs.extend(get_weekly_prs(username, repos, offset))

    start, _ = get_week_range(week_offset - weeks_range + 1)
    _, end = get_week_range(week_offset)

    repo_stats: dict[str, dict] = {}
    for c in all_commits:
        if c.repo_name not in repo_stats:
            repo_stats[c.repo_name] = {
                "commits": 0, "additions": 0, "deletions": 0, "key_changes": [],
            }
        repo_stats[c.repo_name]["commits"] += 1
        repo_stats[c.repo_name]["additions"] += c.additions
        repo_stats[c.repo_name]["deletions"] += c.deletions
        if c.additions + c.deletions > 50:
            repo_stats[c.repo_name]["key_changes"].append(c.message)

    return {
        "username": username,
        "period": {
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
            "weeks": weeks_range,
        },
        "overall_statistics": {
            "total_commits": len(all_commits),
            "total_prs": len(all_prs),
            "merged_prs": sum(1 for pr in all_prs if pr.merged_at),
            "total_additions": sum(c.additions for c in all_commits),
            "total_deletions": sum(c.deletions for c in all_commits),
            "active_repos": len(repo_stats),
        },
        "repo_statistics": repo_stats,
        "notable_prs": [
            {
                "title": pr.title,
                "repo": pr.repo_name,
                "merged": pr.merged_at is not None,
                "changes": pr.additions + pr.deletions,
            }
            for pr in sorted(
                all_prs, key=lambda p: p.additions + p.deletions, reverse=True,
            )[:5]
        ],
    }


@mcp.tool()
def get_agent_sessions(
    username: str,
    week_offset: int = 0,
    project_filter: str | None = None,
) -> dict:
    """에이전트 세션(Claude Code, Codex)을 조회합니다.

    Args:
        username: GitHub 사용자명 (현재는 사용되지 않음)
        week_offset: 주차 오프셋 (0=이번주, -1=지난주...)
        project_filter: 프로젝트 경로 필터 (선택사항)

    Returns:
        Claude 세션, Codex 엔트리, 통계 정보를 포함한 딕셔너리
    """
    sessions = get_weekly_sessions(week_offset, project_filter)
    codex = get_weekly_codex_entries(week_offset)

    return {
        "period": _format_period(week_offset),
        "claude_sessions": [
            {
                "session_id": s.session_id,
                "first_prompt": s.first_prompt,
                "summary": s.summary,
                "message_count": s.message_count,
                "created": s.created.isoformat(),
                "modified": s.modified.isoformat(),
                "project_path": s.project_path,
            }
            for s in sessions
        ],
        "codex_entries": [
            {
                "session_id": e.session_id,
                "timestamp": e.timestamp.isoformat(),
                "text": e.text,
            }
            for e in codex
        ],
        "statistics": {
            "total_claude_sessions": len(sessions),
            "total_codex_entries": len(codex),
            "total_messages": sum(s.message_count for s in sessions),
        },
    }


@mcp.tool()
def get_weekly_timeline(
    username: str,
    week_offset: int = 0,
    repos: list[str] | None = None,
) -> dict:
    """주간 통합 타임라인을 조회합니다.

    GitHub 활동과 에이전트 세션을 시간순으로 통합한 타임라인을 반환합니다.

    Args:
        username: GitHub 사용자명
        week_offset: 주차 오프셋 (0=이번주, -1=지난주...)
        repos: 특정 저장소 목록 (선택사항)

    Returns:
        통합 타임라인 데이터
    """
    return build_weekly_timeline(username, week_offset, repos)


@mcp.tool()
def get_enriched_weekly_report(
    username: str,
    week_offset: int = 0,
    repos: list[str] | None = None,
    include_few_shot: bool = True,
) -> dict:
    """GitHub + 에이전트 활동 + few-shot 예시를 포함한 enriched 리포트 데이터를 반환합니다.

    주간 리포트 생성에 필요한 모든 데이터를 한 번에 제공합니다.
    GitHub 활동, 에이전트 세션, few-shot 예시, 포맷 가이드를 포함합니다.

    Args:
        username: GitHub 사용자명
        week_offset: 주차 오프셋 (0=이번주, -1=지난주...)
        repos: 특정 저장소 목록 (선택사항)
        include_few_shot: few-shot 예시 포함 여부 (기본값: True)

    Returns:
        enriched 리포트 데이터
    """
    commits = get_weekly_commits(username, repos, week_offset)
    prs = get_weekly_prs(username, repos, week_offset)
    sessions = _fetch_sessions_safe(week_offset)
    codex = _fetch_codex_safe(week_offset)

    few_shot_examples = []
    format_guide = ""
    if include_few_shot:
        loader = FewShotLoader()
        few_shot_examples = loader.load_examples(count=2)
        format_guide = loader.extract_format_guide()

    return {
        "period": _format_period(week_offset),
        "github_activity": {
            "commits_by_repo": _group_commits_by_repo(commits),
            "pull_requests": [
                {
                    "number": pr.number, "title": pr.title, "state": pr.state,
                    "repo": pr.repo_name, "merged": pr.merged_at is not None,
                }
                for pr in prs
            ],
            "statistics": {
                "total_commits": len(commits),
                "total_prs": len(prs),
                "total_additions": sum(c.additions for c in commits),
                "total_deletions": sum(c.deletions for c in commits),
            },
        },
        "agent_activity": {
            "claude_sessions": [
                {
                    "session_id": s.session_id, "first_prompt": s.first_prompt,
                    "summary": s.summary, "message_count": s.message_count,
                    "created": s.created.isoformat(), "project_path": s.project_path,
                }
                for s in sessions
            ],
            "statistics": {
                "total_sessions": len(sessions),
                "total_codex_entries": len(codex),
            },
        },
        "few_shot_examples": few_shot_examples,
        "report_format_guide": format_guide,
    }


@mcp.tool()
def get_weekly_insights(
    username: str,
    week_offset: int = 0,
    repos: list[str] | None = None,
) -> dict:
    """주간 인사이트를 분석합니다.

    주간 활동 데이터를 분석하여 패턴, 개선사항, 제안을 생성합니다.

    Args:
        username: GitHub 사용자명
        week_offset: 주차 오프셋 (0=이번주, -1=지난주...)
        repos: 특정 저장소 목록 (선택사항)

    Returns:
        인사이트 목록
    """
    commits = get_weekly_commits(username, repos, week_offset)
    prs = get_weekly_prs(username, repos, week_offset)
    sessions = _fetch_sessions_safe(week_offset)
    codex = _fetch_codex_safe(week_offset)

    analyzer = InsightAnalyzer()
    insights = analyzer.analyze(commits, prs, sessions, codex)

    return {
        "period": _format_period(week_offset),
        "insights": [
            {
                "category": i.category,
                "title": i.title,
                "description": i.description,
                "evidence": i.evidence,
                "suggestion": i.suggestion,
                "severity": i.severity,
            }
            for i in insights
        ],
    }


def main():
    """MCP 서버 실행"""
    mcp.run()


if __name__ == "__main__":
    main()
