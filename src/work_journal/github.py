"""GitHub API 연동 모듈 - 커밋/PR 데이터 수집"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from github import Github, Auth
from github.Repository import Repository
from github.Commit import Commit

from .config import get_config


@dataclass
class CommitInfo:
    """커밋 정보 데이터클래스"""

    sha: str
    message: str
    author: str
    date: datetime
    repo_name: str
    url: str
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0


@dataclass
class PRInfo:
    """PR 정보 데이터클래스"""

    number: int
    title: str
    state: str
    created_at: datetime
    merged_at: datetime | None
    repo_name: str
    url: str
    additions: int = 0
    deletions: int = 0


def get_github_client() -> Github:
    """GitHub 클라이언트 반환"""
    config = get_config()
    auth = Auth.Token(config.github_token)
    return Github(auth=auth)


def get_week_range(week_offset: int = 0) -> tuple[datetime, datetime]:
    """주간 범위 계산 (월요일 00:00 ~ 일요일 23:59)

    Args:
        week_offset: 0=이번주, -1=지난주, -2=2주전...

    Returns:
        (시작일, 종료일) 튜플
    """
    today = datetime.now()
    # 이번주 월요일 찾기
    monday = today - timedelta(days=today.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)

    # offset 적용
    start = monday + timedelta(weeks=week_offset)
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)

    return start, end



def get_commits_for_repo(
    repo: Repository,
    username: str,
    since: datetime,
    until: datetime,
) -> list[CommitInfo]:
    """특정 저장소의 커밋 조회"""
    commits = []

    try:
        for commit in repo.get_commits(author=username, since=since, until=until):
            commit_info = CommitInfo(
                sha=commit.sha[:7],
                message=commit.commit.message.split('\n')[0],  # 첫 줄만
                author=commit.commit.author.name,
                date=commit.commit.author.date,
                repo_name=repo.full_name,
                url=commit.html_url,
                additions=commit.stats.additions if commit.stats else 0,
                deletions=commit.stats.deletions if commit.stats else 0,
                files_changed=len(commit.files) if commit.files else 0,
            )
            commits.append(commit_info)
    except Exception:
        # 접근 권한 없는 저장소 등 무시
        pass

    return commits


def search_commits_by_author(
    gh: Github,
    username: str,
    since: datetime,
    until: datetime,
    repos: list[str] | None = None,
) -> list[CommitInfo]:
    """GitHub Search API로 커밋 검색 (조직 저장소 포함)

    Args:
        gh: GitHub 클라이언트
        username: GitHub 사용자명
        since: 시작일
        until: 종료일
        repos: 특정 저장소 목록 (None이면 전체)

    Returns:
        CommitInfo 목록
    """
    commits: list[CommitInfo] = []

    since_str = since.strftime('%Y-%m-%d')
    until_str = until.strftime('%Y-%m-%d')

    if repos:
        # 특정 저장소들만 검색
        for repo_name in repos:
            query = f"author:{username} repo:{repo_name} author-date:{since_str}..{until_str}"
            try:
                for commit in gh.search_commits(query=query):
                    commit_info = CommitInfo(
                        sha=commit.sha[:7],
                        message=commit.commit.message.split('\n')[0],
                        author=commit.commit.author.name,
                        date=commit.commit.author.date,
                        repo_name=commit.repository.full_name,
                        url=commit.html_url,
                        additions=commit.stats.additions if commit.stats else 0,
                        deletions=commit.stats.deletions if commit.stats else 0,
                        files_changed=commit.stats.total if commit.stats else 0,
                    )
                    commits.append(commit_info)
            except Exception:
                continue
    else:
        # 전체 검색 (조직 저장소 포함)
        query = f"author:{username} author-date:{since_str}..{until_str}"
        try:
            for commit in gh.search_commits(query=query):
                commit_info = CommitInfo(
                    sha=commit.sha[:7],
                    message=commit.commit.message.split('\n')[0],
                    author=commit.commit.author.name,
                    date=commit.commit.author.date,
                    repo_name=commit.repository.full_name,
                    url=commit.html_url,
                    additions=commit.stats.additions if commit.stats else 0,
                    deletions=commit.stats.deletions if commit.stats else 0,
                    files_changed=commit.stats.total if commit.stats else 0,
                )
                commits.append(commit_info)
        except Exception:
            pass

    return commits


def get_weekly_commits(
    username: str,
    repos: list[str] | None = None,
    week_offset: int = 0,
) -> list[CommitInfo]:
    """주간 커밋 조회 (조직 저장소 포함)

    Args:
        username: GitHub 사용자명
        repos: 특정 저장소 목록 (None이면 전체 - 조직 포함)
        week_offset: 0=이번주, -1=지난주...

    Returns:
        CommitInfo 목록
    """
    gh = get_github_client()
    since, until = get_week_range(week_offset)

    # GitHub Search API 사용 (조직 저장소 포함)
    all_commits = search_commits_by_author(gh, username, since, until, repos)

    # 날짜순 정렬
    all_commits.sort(key=lambda c: c.date, reverse=True)

    return all_commits


def get_weekly_prs(
    username: str,
    repos: list[str] | None = None,
    week_offset: int = 0,
) -> list[PRInfo]:
    """주간 PR 조회

    Args:
        username: GitHub 사용자명
        repos: 특정 저장소 목록
        week_offset: 0=이번주, -1=지난주...

    Returns:
        PRInfo 목록
    """
    gh = get_github_client()
    since, until = get_week_range(week_offset)

    all_prs: list[PRInfo] = []

    # 검색 쿼리로 PR 조회
    query = f"author:{username} is:pr created:{since.strftime('%Y-%m-%d')}..{until.strftime('%Y-%m-%d')}"

    if repos:
        for repo_name in repos:
            repo_query = f"{query} repo:{repo_name}"
            issues = gh.search_issues(repo_query)
            for issue in issues:
                pr = issue.as_pull_request()
                pr_info = PRInfo(
                    number=pr.number,
                    title=pr.title,
                    state=pr.state,
                    created_at=pr.created_at,
                    merged_at=pr.merged_at,
                    repo_name=repo_name,
                    url=pr.html_url,
                    additions=pr.additions,
                    deletions=pr.deletions,
                )
                all_prs.append(pr_info)
    else:
        issues = gh.search_issues(query)
        for issue in issues:
            pr = issue.as_pull_request()
            pr_info = PRInfo(
                number=pr.number,
                title=pr.title,
                state=pr.state,
                created_at=pr.created_at,
                merged_at=pr.merged_at,
                repo_name=issue.repository.full_name,
                url=pr.html_url,
                additions=pr.additions,
                deletions=pr.deletions,
            )
            all_prs.append(pr_info)

    # 날짜순 정렬
    all_prs.sort(key=lambda p: p.created_at, reverse=True)

    return all_prs
