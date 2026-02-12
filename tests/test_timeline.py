"""통합 타임라인 빌더 테스트"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from work_journal.timeline import (
    TimelineEvent,
    build_weekly_timeline,
)
from work_journal.github import CommitInfo, PRInfo
from work_journal.session_parser import SessionInfo
from work_journal.codex_parser import CodexEntry


class TestTimelineEvent:
    """TimelineEvent 데이터클래스 테스트"""

    def test_create_timeline_event(self):
        """TimelineEvent 기본 생성"""
        event = TimelineEvent(
            timestamp=datetime(2026, 1, 20, 9, 0),
            source="github_commit",
            title="feat: add feature",
            detail="user/repo +100/-20",
            project="user/repo",
        )

        assert event.source == "github_commit"
        assert event.title == "feat: add feature"
        assert event.metadata == {}

    def test_with_metadata(self):
        """metadata 포함"""
        event = TimelineEvent(
            timestamp=datetime(2026, 1, 20, 9, 0),
            source="claude_session",
            title="프로젝트 분석 세션",
            detail="15 messages, 30분",
            project="my-project",
            metadata={"session_id": "abc123"},
        )

        assert event.metadata["session_id"] == "abc123"


class TestBuildWeeklyTimeline:
    """build_weekly_timeline 함수 테스트"""

    @pytest.fixture
    def mock_commits(self):
        return [
            CommitInfo(
                sha="abc1234",
                message="feat: add auth",
                author="testuser",
                date=datetime(2026, 1, 20, 10, 0),
                repo_name="user/backend",
                url="https://github.com/user/backend/commit/abc1234",
                additions=100,
                deletions=20,
            ),
        ]

    @pytest.fixture
    def mock_prs(self):
        return [
            PRInfo(
                number=1,
                title="feat: auth system",
                state="closed",
                created_at=datetime(2026, 1, 20, 11, 0),
                merged_at=datetime(2026, 1, 21, 9, 0),
                repo_name="user/backend",
                url="https://github.com/user/backend/pull/1",
                additions=150,
                deletions=50,
            ),
        ]

    @pytest.fixture
    def mock_sessions(self):
        return [
            SessionInfo(
                session_id="sess001",
                first_prompt="인증 기능 구현",
                summary="인증 기능 구현 세션",
                message_count=20,
                created=datetime(2026, 1, 20, 9, 0),
                modified=datetime(2026, 1, 20, 10, 30),
                project_path="/home/user/backend",
            ),
        ]

    @pytest.fixture
    def mock_codex(self):
        return [
            CodexEntry(
                session_id="codex001",
                timestamp=datetime(2026, 1, 20, 14, 0),
                text="테스트 코드 작성",
            ),
        ]

    def test_combines_all_sources(
        self, mock_commits, mock_prs, mock_sessions, mock_codex
    ):
        """모든 소스를 통합"""
        with patch(
            "work_journal.timeline.get_weekly_commits",
            return_value=mock_commits,
        ), patch(
            "work_journal.timeline.get_weekly_prs",
            return_value=mock_prs,
        ), patch(
            "work_journal.timeline.get_weekly_sessions",
            return_value=mock_sessions,
        ), patch(
            "work_journal.timeline.get_weekly_codex_entries",
            return_value=mock_codex,
        ):
            result = build_weekly_timeline(username="testuser", week_offset=0)

        assert "events" in result
        assert "statistics" in result
        # 커밋 1 + PR 1 + 세션 1 + Codex 1 = 4
        assert len(result["events"]) == 4

    def test_events_sorted_by_timestamp(
        self, mock_commits, mock_prs, mock_sessions, mock_codex
    ):
        """이벤트가 시간순으로 정렬"""
        with patch(
            "work_journal.timeline.get_weekly_commits",
            return_value=mock_commits,
        ), patch(
            "work_journal.timeline.get_weekly_prs",
            return_value=mock_prs,
        ), patch(
            "work_journal.timeline.get_weekly_sessions",
            return_value=mock_sessions,
        ), patch(
            "work_journal.timeline.get_weekly_codex_entries",
            return_value=mock_codex,
        ):
            result = build_weekly_timeline(username="testuser", week_offset=0)

        events = result["events"]
        timestamps = [e["timestamp"] for e in events]
        assert timestamps == sorted(timestamps)

    def test_statistics_by_source(
        self, mock_commits, mock_prs, mock_sessions, mock_codex
    ):
        """소스별 통계 포함"""
        with patch(
            "work_journal.timeline.get_weekly_commits",
            return_value=mock_commits,
        ), patch(
            "work_journal.timeline.get_weekly_prs",
            return_value=mock_prs,
        ), patch(
            "work_journal.timeline.get_weekly_sessions",
            return_value=mock_sessions,
        ), patch(
            "work_journal.timeline.get_weekly_codex_entries",
            return_value=mock_codex,
        ):
            result = build_weekly_timeline(username="testuser", week_offset=0)

        stats = result["statistics"]
        assert "by_source" in stats
        assert stats["by_source"]["github_commit"] == 1
        assert stats["by_source"]["github_pr"] == 1
        assert stats["by_source"]["claude_session"] == 1
        assert stats["by_source"]["codex_entry"] == 1

    def test_handles_empty_data(self):
        """데이터가 없는 경우"""
        with patch(
            "work_journal.timeline.get_weekly_commits",
            return_value=[],
        ), patch(
            "work_journal.timeline.get_weekly_prs",
            return_value=[],
        ), patch(
            "work_journal.timeline.get_weekly_sessions",
            return_value=[],
        ), patch(
            "work_journal.timeline.get_weekly_codex_entries",
            return_value=[],
        ):
            result = build_weekly_timeline(username="testuser", week_offset=0)

        assert result["events"] == []
        assert result["statistics"]["by_source"] == {}

    def test_includes_period(self, mock_commits, mock_prs, mock_sessions, mock_codex):
        """기간 정보 포함"""
        with patch(
            "work_journal.timeline.get_weekly_commits",
            return_value=mock_commits,
        ), patch(
            "work_journal.timeline.get_weekly_prs",
            return_value=mock_prs,
        ), patch(
            "work_journal.timeline.get_weekly_sessions",
            return_value=mock_sessions,
        ), patch(
            "work_journal.timeline.get_weekly_codex_entries",
            return_value=mock_codex,
        ):
            result = build_weekly_timeline(username="testuser", week_offset=0)

        assert "period" in result
        assert "start" in result["period"]
        assert "end" in result["period"]
