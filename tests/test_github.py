"""GitHub 모듈 테스트"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from work_journal.github import (
    CommitInfo,
    PRInfo,
    get_week_range,
    get_commits_for_repo,
)


class TestGetWeekRange:
    """get_week_range 함수 테스트"""

    def test_current_week_returns_monday_to_sunday(self):
        """이번 주 범위가 월요일~일요일인지 확인"""
        start, end = get_week_range(0)

        # 시작일은 월요일
        assert start.weekday() == 0
        # 종료일은 일요일
        assert end.weekday() == 6
        # 시작일은 00:00:00
        assert start.hour == 0 and start.minute == 0 and start.second == 0
        # 종료일은 23:59:59
        assert end.hour == 23 and end.minute == 59 and end.second == 59

    def test_last_week_offset(self):
        """지난주(-1) 오프셋 테스트"""
        current_start, _ = get_week_range(0)
        last_start, last_end = get_week_range(-1)

        # 지난주 시작일은 이번주 시작일보다 7일 전
        assert current_start - last_start == timedelta(days=7)

    def test_two_weeks_ago_offset(self):
        """2주 전(-2) 오프셋 테스트"""
        current_start, _ = get_week_range(0)
        two_weeks_start, _ = get_week_range(-2)

        assert current_start - two_weeks_start == timedelta(days=14)

    def test_week_range_is_7_days(self):
        """주간 범위가 정확히 7일인지 확인"""
        start, end = get_week_range(0)
        diff = end - start

        # 6일 23시간 59분 59초
        assert diff.days == 6
        assert diff.seconds == 23 * 3600 + 59 * 60 + 59


class TestCommitInfo:
    """CommitInfo 데이터클래스 테스트"""

    def test_create_commit_info(self):
        """CommitInfo 생성 테스트"""
        commit = CommitInfo(
            sha="abc1234",
            message="feat: add new feature",
            author="testuser",
            date=datetime.now(),
            repo_name="user/repo",
            url="https://github.com/user/repo/commit/abc1234",
            additions=100,
            deletions=50,
            files_changed=5,
        )

        assert commit.sha == "abc1234"
        assert commit.message == "feat: add new feature"
        assert commit.additions == 100
        assert commit.deletions == 50

    def test_default_values(self):
        """기본값 테스트"""
        commit = CommitInfo(
            sha="abc1234",
            message="test",
            author="user",
            date=datetime.now(),
            repo_name="user/repo",
            url="https://example.com",
        )

        assert commit.additions == 0
        assert commit.deletions == 0
        assert commit.files_changed == 0


class TestPRInfo:
    """PRInfo 데이터클래스 테스트"""

    def test_create_pr_info(self):
        """PRInfo 생성 테스트"""
        pr = PRInfo(
            number=123,
            title="feat: new feature",
            state="open",
            created_at=datetime.now(),
            merged_at=None,
            repo_name="user/repo",
            url="https://github.com/user/repo/pull/123",
            additions=200,
            deletions=100,
        )

        assert pr.number == 123
        assert pr.state == "open"
        assert pr.merged_at is None

    def test_merged_pr(self):
        """머지된 PR 테스트"""
        merged_at = datetime.now()
        pr = PRInfo(
            number=456,
            title="fix: bug fix",
            state="closed",
            created_at=datetime.now() - timedelta(days=1),
            merged_at=merged_at,
            repo_name="user/repo",
            url="https://github.com/user/repo/pull/456",
        )

        assert pr.merged_at == merged_at
        assert pr.state == "closed"


class TestGetCommitsForRepo:
    """get_commits_for_repo 함수 테스트"""

    def test_returns_empty_list_on_error(self):
        """에러 발생 시 빈 리스트 반환"""
        mock_repo = MagicMock()
        mock_repo.get_commits.side_effect = Exception("API Error")

        result = get_commits_for_repo(
            repo=mock_repo,
            username="testuser",
            since=datetime.now() - timedelta(days=7),
            until=datetime.now(),
        )

        assert result == []

    def test_parses_commits_correctly(self):
        """커밋 파싱 테스트"""
        mock_repo = MagicMock()
        mock_repo.full_name = "user/test-repo"

        mock_commit = MagicMock()
        mock_commit.sha = "abc1234567890"
        mock_commit.commit.message = "feat: test commit\n\ndetailed description"
        mock_commit.commit.author.name = "Test User"
        mock_commit.commit.author.date = datetime(2024, 1, 15, 10, 30)
        mock_commit.html_url = "https://github.com/user/test-repo/commit/abc1234"
        mock_commit.stats.additions = 50
        mock_commit.stats.deletions = 20
        mock_commit.files = ["file1.py", "file2.py"]

        mock_repo.get_commits.return_value = [mock_commit]

        result = get_commits_for_repo(
            repo=mock_repo,
            username="testuser",
            since=datetime.now() - timedelta(days=7),
            until=datetime.now(),
        )

        assert len(result) == 1
        assert result[0].sha == "abc1234"  # 앞 7자리만
        assert result[0].message == "feat: test commit"  # 첫 줄만
        assert result[0].additions == 50
        assert result[0].deletions == 20
        assert result[0].files_changed == 2
