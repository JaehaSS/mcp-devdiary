"""Formatter 모듈 테스트"""

from datetime import datetime

import pytest

from work_journal.github import CommitInfo, PRInfo
from work_journal.formatter import format_weekly_log, format_resume_section


class TestFormatWeeklyLog:
    """format_weekly_log 함수 테스트"""

    @pytest.fixture
    def sample_commits(self):
        """테스트용 커밋 데이터"""
        return [
            CommitInfo(
                sha="abc1234",
                message="feat: add user authentication",
                author="testuser",
                date=datetime(2024, 1, 15, 10, 30),
                repo_name="user/backend",
                url="https://github.com/user/backend/commit/abc1234",
                additions=150,
                deletions=30,
            ),
            CommitInfo(
                sha="def5678",
                message="fix: resolve login bug",
                author="testuser",
                date=datetime(2024, 1, 16, 14, 20),
                repo_name="user/backend",
                url="https://github.com/user/backend/commit/def5678",
                additions=20,
                deletions=10,
            ),
            CommitInfo(
                sha="ghi9012",
                message="docs: update README",
                author="testuser",
                date=datetime(2024, 1, 17, 9, 0),
                repo_name="user/frontend",
                url="https://github.com/user/frontend/commit/ghi9012",
                additions=50,
                deletions=5,
            ),
        ]

    @pytest.fixture
    def sample_prs(self):
        """테스트용 PR 데이터"""
        return [
            PRInfo(
                number=42,
                title="feat: implement login flow",
                state="closed",
                created_at=datetime(2024, 1, 14),
                merged_at=datetime(2024, 1, 16),
                repo_name="user/backend",
                url="https://github.com/user/backend/pull/42",
                additions=200,
                deletions=50,
            ),
        ]

    def test_generates_markdown(self, sample_commits, sample_prs):
        """마크다운 생성 확인"""
        result = format_weekly_log(
            username="testuser",
            commits=sample_commits,
            prs=sample_prs,
            summary="이번 주에 인증 기능을 구현했습니다.",
            week_offset=0,
        )

        assert "# 주간 업무일지" in result
        assert "**작성자:** testuser" in result

    def test_includes_statistics(self, sample_commits, sample_prs):
        """통계 포함 확인"""
        result = format_weekly_log(
            username="testuser",
            commits=sample_commits,
            prs=sample_prs,
            summary="요약 내용",
        )

        assert "총 커밋 수" in result
        assert "3" in result  # 3개의 커밋
        assert "추가된 라인" in result
        assert "삭제된 라인" in result

    def test_includes_summary(self, sample_commits, sample_prs):
        """요약 포함 확인"""
        summary_text = "이번 주 핵심 작업 내용입니다."
        result = format_weekly_log(
            username="testuser",
            commits=sample_commits,
            prs=sample_prs,
            summary=summary_text,
        )

        assert summary_text in result

    def test_groups_commits_by_repo(self, sample_commits, sample_prs):
        """저장소별 커밋 그룹화 확인"""
        result = format_weekly_log(
            username="testuser",
            commits=sample_commits,
            prs=sample_prs,
            summary="요약",
        )

        assert "### user/backend" in result
        assert "### user/frontend" in result

    def test_includes_commit_details(self, sample_commits, sample_prs):
        """커밋 상세 정보 포함 확인"""
        result = format_weekly_log(
            username="testuser",
            commits=sample_commits,
            prs=sample_prs,
            summary="요약",
        )

        assert "abc1234" in result
        assert "feat: add user authentication" in result
        assert "+150/-30" in result

    def test_includes_pr_section(self, sample_commits, sample_prs):
        """PR 섹션 포함 확인"""
        result = format_weekly_log(
            username="testuser",
            commits=sample_commits,
            prs=sample_prs,
            summary="요약",
        )

        assert "Pull Requests" in result
        assert "#42" in result
        assert "feat: implement login flow" in result
        assert "Merged" in result

    def test_no_pr_section_when_empty(self, sample_commits):
        """PR이 없으면 PR 섹션 없음"""
        result = format_weekly_log(
            username="testuser",
            commits=sample_commits,
            prs=[],
            summary="요약",
        )

        assert "Pull Requests" not in result

    def test_empty_commits(self):
        """커밋이 없는 경우"""
        result = format_weekly_log(
            username="testuser",
            commits=[],
            prs=[],
            summary="이번 주는 휴가였습니다.",
        )

        assert "총 커밋 수 | 0" in result
        assert "이번 주는 휴가였습니다." in result


class TestFormatResumeSection:
    """format_resume_section 함수 테스트"""

    def test_generates_markdown(self):
        """마크다운 생성 확인"""
        result = format_resume_section(
            bullets=[
                "사용자 인증 시스템을 구현하여 보안성 50% 향상",
                "CI/CD 파이프라인 구축으로 배포 시간 70% 단축",
            ],
            position="백엔드 개발자",
            period="2024.01 - 2024.03",
        )

        assert "## 백엔드 개발자 경력 기술서" in result
        assert "**기간:** 2024.01 - 2024.03" in result

    def test_includes_all_bullets(self):
        """모든 bullet 포함 확인"""
        bullets = [
            "성과 1",
            "성과 2",
            "성과 3",
        ]
        result = format_resume_section(
            bullets=bullets,
            position="개발자",
            period="2024",
        )

        for bullet in bullets:
            assert f"- {bullet}" in result

    def test_includes_header(self):
        """헤더 포함 확인"""
        result = format_resume_section(
            bullets=["성과"],
            position="풀스택 개발자",
            period="2024",
        )

        assert "주요 성과" in result
