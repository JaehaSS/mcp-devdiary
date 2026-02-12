#!/usr/bin/env python3
"""GitHub API 연결 테스트 스크립트

.env 파일의 토큰을 사용해 GitHub API 연결 및 커밋 내역을 확인합니다.

Usage:
    uv run python scripts/test_github_api.py
    uv run python scripts/test_github_api.py --username Jjaeha
    uv run python scripts/test_github_api.py --username Jjaeha --weeks 4
"""

import argparse
import os
import sys
from datetime import datetime, timedelta

from dotenv import load_dotenv
from github import Github, Auth, GithubException


def test_token_validity(token: str) -> tuple[bool, str]:
    """토큰 유효성 검사"""
    try:
        gh = Github(auth=Auth.Token(token))
        user = gh.get_user()
        # 사용자 정보 접근으로 API 호출 테스트
        login = user.login
        return True, f"토큰 유효! 인증된 사용자: {login}"
    except GithubException as e:
        msg = e.data.get('message', str(e)) if hasattr(e, 'data') else str(e)
        return False, f"토큰 인증 실패: {msg}"
    except Exception as e:
        return False, f"연결 오류: {str(e)}"


def get_week_range(week_offset: int = 0) -> tuple[datetime, datetime]:
    """주간 범위 계산 (월요일 ~ 일요일)"""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)

    start = monday + timedelta(weeks=week_offset)
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)

    return start, end


def get_commits(token: str, username: str, weeks: int = 1) -> list[dict]:
    """사용자의 커밋 내역 조회"""
    gh = Github(auth=Auth.Token(token))
    all_commits = []

    # 주간 범위 계산 (최근 N주)
    for week_offset in range(0, -weeks, -1):
        since, until = get_week_range(week_offset)
        print(f"\n조회 기간: {since.strftime('%Y-%m-%d')} ~ {until.strftime('%Y-%m-%d')}")

        # 사용자의 모든 저장소 조회
        try:
            user = gh.get_user(username)
            repos = list(user.get_repos())
            print(f"조회할 저장소 수: {len(repos)}")
            for repo in repos:
                print(f"    - {repo.full_name} (private: {repo.private})")

            for repo in repos:
                try:
                    commits = repo.get_commits(author=username, since=since, until=until)
                    for commit in commits:
                        commit_data = {
                            "sha": commit.sha[:7],
                            "message": commit.commit.message.split('\n')[0],
                            "date": commit.commit.author.date.strftime('%Y-%m-%d %H:%M'),
                            "repo": repo.full_name,
                            "url": commit.html_url,
                            "additions": commit.stats.additions if commit.stats else 0,
                            "deletions": commit.stats.deletions if commit.stats else 0,
                        }
                        all_commits.append(commit_data)
                except GithubException:
                    # 접근 권한 없는 저장소 무시
                    pass

        except GithubException as e:
            print(f"사용자 조회 실패: {e.data.get('message', str(e))}")

    return all_commits


def get_all_push_events(token: str, username: str) -> list[dict]:
    """사용자의 최근 Push 이벤트 조회 (모든 저장소 포함)"""
    gh = Github(auth=Auth.Token(token))
    events = []

    try:
        user = gh.get_user(username)
        for event in user.get_events():
            if event.type == "PushEvent":
                payload = event.payload
                for commit in payload.get("commits", []):
                    events.append({
                        "sha": commit["sha"][:7],
                        "message": commit["message"].split('\n')[0],
                        "date": event.created_at.strftime('%Y-%m-%d %H:%M'),
                        "repo": event.repo.name,
                    })
            if len(events) >= 50:  # 최대 50개
                break
    except GithubException as e:
        print(f"이벤트 조회 실패: {e}")

    return events


def search_all_commits(token: str, username: str, since: datetime, until: datetime) -> list[dict]:
    """GitHub Search API로 모든 커밋 검색 (조직 저장소 포함)"""
    gh = Github(auth=Auth.Token(token))
    commits = []

    # Search API 쿼리: author로 검색하면 조직 저장소도 포함됨
    since_str = since.strftime('%Y-%m-%d')
    until_str = until.strftime('%Y-%m-%d')
    query = f"author:{username} author-date:{since_str}..{until_str}"

    print(f"    검색 쿼리: {query}")

    try:
        results = gh.search_commits(query=query)
        for commit in results:
            commits.append({
                "sha": commit.sha[:7],
                "message": commit.commit.message.split('\n')[0],
                "date": commit.commit.author.date.strftime('%Y-%m-%d %H:%M'),
                "repo": commit.repository.full_name,
                "url": commit.html_url,
                "additions": commit.stats.additions if commit.stats else 0,
                "deletions": commit.stats.deletions if commit.stats else 0,
            })
    except GithubException as e:
        msg = e.data.get('message', str(e)) if hasattr(e, 'data') else str(e)
        print(f"    검색 오류: {msg}")

    return commits


def main():
    parser = argparse.ArgumentParser(description="GitHub API 연결 테스트")
    parser.add_argument("--username", "-u", help="GitHub 사용자명", default=None)
    parser.add_argument("--weeks", "-w", type=int, default=1, help="조회할 주 수 (기본: 1)")
    args = parser.parse_args()

    # .env 로드
    load_dotenv()

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN이 .env 파일에 설정되지 않았습니다.")
        sys.exit(1)

    print("=" * 60)
    print("GitHub API 연결 테스트")
    print("=" * 60)

    # 1. 토큰 유효성 검사
    print("\n[1] 토큰 유효성 검사...")
    is_valid, message = test_token_validity(token)
    print(f"    {message}")

    if not is_valid:
        sys.exit(1)

    # 사용자명 결정
    username = args.username or os.getenv("GITHUB_USERNAME")
    if not username:
        # 토큰 소유자의 사용자명 사용
        gh = Github(auth=Auth.Token(token))
        username = gh.get_user().login
        print(f"\n    사용자명 미지정 - 토큰 소유자 사용: {username}")

    # 2. 커밋 내역 조회
    print(f"\n[2] 커밋 내역 조회 (최근 {args.weeks}주)...")
    print(f"    사용자: {username}")

    commits = get_commits(token, username, args.weeks)

    # 3. 결과 출력
    print("\n" + "=" * 60)
    print(f"조회 결과: 총 {len(commits)}개의 커밋")
    print("=" * 60)

    if commits:
        for i, commit in enumerate(commits[:20], 1):  # 최대 20개만 출력
            print(f"\n{i}. [{commit['sha']}] {commit['message']}")
            print(f"   저장소: {commit['repo']}")
            print(f"   날짜: {commit['date']}")
            print(f"   변경: +{commit['additions']} -{commit['deletions']}")

        if len(commits) > 20:
            print(f"\n... 외 {len(commits) - 20}개의 커밋")
    else:
        print("\n해당 기간에 커밋이 없습니다.")

    # 4. GitHub Search API로 조직 포함 전체 커밋 검색
    print("\n" + "=" * 60)
    print("[3] GitHub Search API - 조직 저장소 포함 전체 커밋 검색")
    print("=" * 60)

    since, until = get_week_range(0)  # 이번 주
    for week_offset in range(0, -args.weeks, -1):
        since, until = get_week_range(week_offset)
        print(f"\n기간: {since.strftime('%Y-%m-%d')} ~ {until.strftime('%Y-%m-%d')}")

        search_commits = search_all_commits(token, username, since, until)
        if search_commits:
            print(f"    발견된 커밋: {len(search_commits)}개")
            for commit in search_commits[:10]:
                print(f"    - [{commit['sha']}] {commit['message'][:50]}")
                print(f"      저장소: {commit['repo']} | {commit['date']}")
        else:
            print("    커밋 없음")

    # 5. Push Events 조회 (최근 활동 확인용)
    print("\n" + "=" * 60)
    print("[4] 최근 Push 이벤트 (활동 확인용)")
    print("=" * 60)

    events = get_all_push_events(token, username)
    if events:
        print(f"최근 Push 이벤트: {len(events)}개")
        for i, event in enumerate(events[:10], 1):
            print(f"\n{i}. [{event['sha']}] {event['message']}")
            print(f"   저장소: {event['repo']}")
            print(f"   날짜: {event['date']}")
    else:
        print("최근 Push 이벤트가 없습니다.")


if __name__ == "__main__":
    main()
