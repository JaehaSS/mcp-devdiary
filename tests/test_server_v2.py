"""MCP 서버 v2 통합 테스트 - 신규 도구 테스트"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastmcp import Client

from work_journal.server import mcp
from work_journal.github import CommitInfo, PRInfo, get_week_range
from work_journal.session_parser import SessionInfo, SessionAnalysis
from work_journal.codex_parser import CodexEntry
from work_journal.insights import Insight


def parse_tool_result(result):
    """call_tool 결과에서 데이터 추출"""
    if hasattr(result, "content") and result.content:
        text = result.content[0].text
        return json.loads(text)
    return result


@pytest.fixture
async def client():
    """MCP 클라이언트 픽스처"""
    async with Client(transport=mcp) as mcp_client:
        yield mcp_client


@pytest.fixture
def mock_sessions():
    """테스트용 세션 데이터"""
    return [
        SessionInfo(
            session_id="sess001",
            first_prompt="인증 기능 구현",
            summary="인증 기능을 구현했습니다",
            message_count=20,
            created=datetime(2026, 1, 20, 9, 0),
            modified=datetime(2026, 1, 20, 10, 30),
            project_path="/home/user/backend",
        ),
    ]


@pytest.fixture
def mock_codex_entries():
    """테스트용 Codex 데이터"""
    return [
        CodexEntry(
            session_id="codex001",
            timestamp=datetime(2026, 1, 20, 14, 0),
            text="테스트 코드 작성",
        ),
    ]


@pytest.fixture
def mock_commits():
    """테스트용 커밋 데이터"""
    return [
        CommitInfo(
            sha="abc1234",
            message="feat: add feature",
            author="testuser",
            date=datetime(2026, 1, 20, 10, 30),
            repo_name="user/repo",
            url="https://github.com/user/repo/commit/abc1234",
            additions=100,
            deletions=20,
        ),
    ]


@pytest.fixture
def mock_prs():
    """테스트용 PR 데이터"""
    return [
        PRInfo(
            number=1,
            title="feat: new feature",
            state="closed",
            created_at=datetime(2026, 1, 20),
            merged_at=datetime(2026, 1, 21),
            repo_name="user/repo",
            url="https://github.com/user/repo/pull/1",
            additions=150,
            deletions=50,
        ),
    ]


# ===== 도구 존재 테스트 =====


class TestNewTools:
    """신규 MCP 도구 존재 확인"""

    async def test_has_get_agent_sessions_tool(self, client):
        """get_agent_sessions 도구 존재 확인"""
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]

        assert "get_agent_sessions" in tool_names

    async def test_has_get_weekly_timeline_tool(self, client):
        """get_weekly_timeline 도구 존재 확인"""
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]

        assert "get_weekly_timeline" in tool_names

    async def test_has_get_enriched_weekly_report_tool(self, client):
        """get_enriched_weekly_report 도구 존재 확인"""
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]

        assert "get_enriched_weekly_report" in tool_names

    async def test_has_get_weekly_insights_tool(self, client):
        """get_weekly_insights 도구 존재 확인"""
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]

        assert "get_weekly_insights" in tool_names

    async def test_total_tool_count(self, client):
        """전체 도구 개수 확인 (기존 3 + 신규 4 = 7)"""
        tools = await client.list_tools()

        assert len(tools) == 7


# ===== get_agent_sessions 테스트 =====


class TestGetAgentSessions:
    """get_agent_sessions 도구 테스트"""

    async def test_returns_sessions(self, client, mock_sessions, mock_codex_entries):
        """세션 목록 반환"""
        with patch(
            "work_journal.server.get_weekly_sessions",
            return_value=mock_sessions,
        ), patch(
            "work_journal.server.get_weekly_codex_entries",
            return_value=mock_codex_entries,
        ):
            raw_result = await client.call_tool("get_agent_sessions", {
                "username": "testuser",
            })
            result = parse_tool_result(raw_result)

        assert "period" in result
        assert "claude_sessions" in result
        assert "codex_entries" in result
        assert "statistics" in result
        assert len(result["claude_sessions"]) == 1

    async def test_returns_statistics(self, client, mock_sessions, mock_codex_entries):
        """통계 정보 포함"""
        with patch(
            "work_journal.server.get_weekly_sessions",
            return_value=mock_sessions,
        ), patch(
            "work_journal.server.get_weekly_codex_entries",
            return_value=mock_codex_entries,
        ):
            raw_result = await client.call_tool("get_agent_sessions", {
                "username": "testuser",
            })
            result = parse_tool_result(raw_result)

        stats = result["statistics"]
        assert "total_claude_sessions" in stats
        assert "total_codex_entries" in stats
        assert stats["total_claude_sessions"] == 1
        assert stats["total_codex_entries"] == 1


# ===== get_weekly_timeline 테스트 =====


class TestGetWeeklyTimeline:
    """get_weekly_timeline 도구 테스트"""

    async def test_returns_timeline_events(
        self, client, mock_commits, mock_prs, mock_sessions, mock_codex_entries
    ):
        """타임라인 이벤트 반환"""
        with patch(
            "work_journal.server.build_weekly_timeline",
            return_value={
                "period": {"start": "2026-01-19", "end": "2026-01-25"},
                "events": [
                    {
                        "timestamp": "2026-01-20T09:00:00",
                        "source": "github_commit",
                        "title": "feat: add feature",
                        "detail": "user/repo +100/-20",
                        "project": "user/repo",
                    }
                ],
                "statistics": {
                    "by_source": {"github_commit": 1},
                    "by_project": {"user/repo": 1},
                    "by_day": {"2026-01-20": 1},
                },
            },
        ):
            raw_result = await client.call_tool("get_weekly_timeline", {
                "username": "testuser",
            })
            result = parse_tool_result(raw_result)

        assert "period" in result
        assert "events" in result
        assert "statistics" in result
        assert len(result["events"]) == 1


# ===== get_enriched_weekly_report 테스트 =====


class TestGetEnrichedWeeklyReport:
    """get_enriched_weekly_report 도구 테스트"""

    async def test_returns_enriched_data(
        self, client, mock_commits, mock_prs, mock_sessions
    ):
        """GitHub + 에이전트 + few-shot 통합 반환"""
        with patch(
            "work_journal.server.get_weekly_commits",
            return_value=mock_commits,
        ), patch(
            "work_journal.server.get_weekly_prs",
            return_value=mock_prs,
        ), patch(
            "work_journal.server.get_weekly_sessions",
            return_value=mock_sessions,
        ), patch(
            "work_journal.server.get_weekly_codex_entries",
            return_value=[],
        ), patch(
            "work_journal.server.FewShotLoader",
        ) as MockLoader:
            mock_loader = MockLoader.return_value
            mock_loader.load_examples.return_value = ["# 예시 리포트"]
            mock_loader.extract_format_guide.return_value = "포맷 가이드"

            raw_result = await client.call_tool("get_enriched_weekly_report", {
                "username": "testuser",
            })
            result = parse_tool_result(raw_result)

        assert "period" in result
        assert "github_activity" in result
        assert "agent_activity" in result
        assert "few_shot_examples" in result
        assert "report_format_guide" in result

    async def test_exclude_few_shot(
        self, client, mock_commits, mock_prs, mock_sessions
    ):
        """include_few_shot=False 시 few-shot 미포함"""
        with patch(
            "work_journal.server.get_weekly_commits",
            return_value=mock_commits,
        ), patch(
            "work_journal.server.get_weekly_prs",
            return_value=mock_prs,
        ), patch(
            "work_journal.server.get_weekly_sessions",
            return_value=mock_sessions,
        ), patch(
            "work_journal.server.get_weekly_codex_entries",
            return_value=[],
        ), patch(
            "work_journal.server.FewShotLoader",
        ) as MockLoader:
            mock_loader = MockLoader.return_value
            mock_loader.load_examples.return_value = []
            mock_loader.extract_format_guide.return_value = ""

            raw_result = await client.call_tool("get_enriched_weekly_report", {
                "username": "testuser",
                "include_few_shot": False,
            })
            result = parse_tool_result(raw_result)

        assert result["few_shot_examples"] == []


# ===== get_weekly_insights 테스트 =====


class TestGetWeeklyInsights:
    """get_weekly_insights 도구 테스트"""

    async def test_returns_insights(self, client, mock_commits, mock_prs):
        """인사이트 반환"""
        mock_insights = [
            Insight(
                category="error_pattern",
                title="반복 에러",
                description="동일 에러 반복",
                severity="warning",
            ),
        ]

        with patch(
            "work_journal.server.get_weekly_commits",
            return_value=mock_commits,
        ), patch(
            "work_journal.server.get_weekly_prs",
            return_value=mock_prs,
        ), patch(
            "work_journal.server.get_weekly_sessions",
            return_value=[],
        ), patch(
            "work_journal.server.get_weekly_codex_entries",
            return_value=[],
        ), patch(
            "work_journal.server.InsightAnalyzer",
        ) as MockAnalyzer:
            mock_analyzer = MockAnalyzer.return_value
            mock_analyzer.analyze.return_value = mock_insights

            raw_result = await client.call_tool("get_weekly_insights", {
                "username": "testuser",
            })
            result = parse_tool_result(raw_result)

        assert "period" in result
        assert "insights" in result
        assert len(result["insights"]) == 1
        assert result["insights"][0]["category"] == "error_pattern"


# ===== get_weekly_activity 확장 테스트 =====


class TestGetWeeklyActivityExtended:
    """get_weekly_activity 확장 (agent_sessions 필드) 테스트"""

    async def test_includes_agent_sessions(
        self, client, mock_commits, mock_prs, mock_sessions, mock_codex_entries
    ):
        """agent_sessions 필드 포함"""
        with patch(
            "work_journal.server.get_weekly_commits",
            return_value=mock_commits,
        ), patch(
            "work_journal.server.get_weekly_prs",
            return_value=mock_prs,
        ), patch(
            "work_journal.server.get_weekly_sessions",
            return_value=mock_sessions,
        ), patch(
            "work_journal.server.get_weekly_codex_entries",
            return_value=mock_codex_entries,
        ):
            raw_result = await client.call_tool("get_weekly_activity", {
                "username": "testuser",
            })
            result = parse_tool_result(raw_result)

        assert "agent_sessions" in result
        assert "claude_sessions" in result["agent_sessions"]
        assert result["agent_sessions"]["total_sessions"] == 1

    async def test_backward_compatible(self, client, mock_commits, mock_prs):
        """하위 호환성 유지 - 세션 파싱 실패해도 기존 필드 유지"""
        with patch(
            "work_journal.server.get_weekly_commits",
            return_value=mock_commits,
        ), patch(
            "work_journal.server.get_weekly_prs",
            return_value=mock_prs,
        ), patch(
            "work_journal.server.get_weekly_sessions",
            side_effect=Exception("파싱 실패"),
        ), patch(
            "work_journal.server.get_weekly_codex_entries",
            side_effect=Exception("파싱 실패"),
        ):
            raw_result = await client.call_tool("get_weekly_activity", {
                "username": "testuser",
            })
            result = parse_tool_result(raw_result)

        # 기존 필드는 정상 반환
        assert "statistics" in result
        assert "commits_by_repo" in result
        assert "pull_requests" in result
        # agent_sessions는 빈 상태로 graceful degradation
        assert "agent_sessions" in result
        assert result["agent_sessions"]["total_sessions"] == 0
