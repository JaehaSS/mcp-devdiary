"""마크다운 포맷터 모듈 - 주간 로그 템플릿 적용"""

from datetime import datetime
from .github import CommitInfo, PRInfo, get_week_range


def format_weekly_log(
    username: str,
    commits: list[CommitInfo],
    prs: list[PRInfo],
    summary: str,
    week_offset: int = 0,
) -> str:
    """주간 로그 마크다운 생성

    Args:
        username: GitHub 사용자명
        commits: 커밋 정보 목록
        prs: PR 정보 목록
        summary: AI 생성 요약
        week_offset: 주차 오프셋

    Returns:
        마크다운 형식 문자열
    """
    start, end = get_week_range(week_offset)

    # 통계 계산
    total_additions = sum(c.additions for c in commits)
    total_deletions = sum(c.deletions for c in commits)
    repos = list(set(c.repo_name for c in commits))

    # 마크다운 생성
    md = f"""# 주간 업무일지

**기간:** {start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}
**작성자:** {username}
**생성일:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 📊 주간 통계

| 항목 | 수치 |
|------|------|
| 총 커밋 수 | {len(commits)} |
| 추가된 라인 | +{total_additions:,} |
| 삭제된 라인 | -{total_deletions:,} |
| 활동 저장소 | {len(repos)} |
| PR 수 | {len(prs)} |

---

## 📝 요약

{summary}

---

## 🔨 커밋 상세

"""

    # 저장소별 커밋 그룹화
    commits_by_repo: dict[str, list[CommitInfo]] = {}
    for c in commits:
        if c.repo_name not in commits_by_repo:
            commits_by_repo[c.repo_name] = []
        commits_by_repo[c.repo_name].append(c)

    for repo_name, repo_commits in commits_by_repo.items():
        md += f"### {repo_name}\n\n"
        for c in repo_commits:
            md += f"- **[{c.sha}]({c.url})** {c.message}\n"
            md += f"  - 📅 {c.date.strftime('%Y-%m-%d %H:%M')} | +{c.additions}/-{c.deletions}\n"
        md += "\n"

    # PR 섹션
    if prs:
        md += "---\n\n## 🔀 Pull Requests\n\n"
        for pr in prs:
            status = "✅ Merged" if pr.merged_at else ("🟢 Open" if pr.state == "open" else "🔴 Closed")
            md += f"- **[#{pr.number}]({pr.url})** {pr.title}\n"
            md += f"  - {status} | {pr.repo_name} | +{pr.additions}/-{pr.deletions}\n"
        md += "\n"

    md += "---\n\n*이 문서는 Work Journal System에 의해 자동 생성되었습니다.*\n"

    return md


def format_resume_section(
    bullets: list[str],
    position: str,
    period: str,
) -> str:
    """이력서 섹션 마크다운 생성

    Args:
        bullets: STAR 포맷 bullet 목록
        position: 지원 포지션
        period: 기간 문자열

    Returns:
        마크다운 형식 문자열
    """
    md = f"""## {position} 경력 기술서

**기간:** {period}

### 주요 성과

"""

    for bullet in bullets:
        md += f"- {bullet}\n"

    md += "\n---\n\n*Work Journal System으로 생성*\n"

    return md
