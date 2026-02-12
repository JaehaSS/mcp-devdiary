"""MCP 서버 통합 테스트"""

import json
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
from fastmcp import Client

from work_journal.server import mcp
from work_journal.github import CommitInfo, PRInfo


def parse_tool_result(result):
    """call_tool 결과에서 데이터 추출"""
    # CallToolResult의 content에서 텍스트 추출 후 JSON 파싱
    if hasattr(result, "content") and result.content:
        text = result.content[0].text
        return json.loads(text)
    return result


@pytest.fixture
async def client():
    """MCP 클라이언트 픽스처"""
    async with Client(transport=mcp) as mcp_client:
        yield mcp_client


class TestListTools:
    """MCP 도구 목록 테스트"""

    async def test_has_get_commits_tool(self, client):
        """get_commits 도구 존재 확인"""
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]

        assert "get_commits" in tool_names

    async def test_has_get_weekly_activity_tool(self, client):
        """get_weekly_activity 도구 존재 확인"""
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]

        assert "get_weekly_activity" in tool_names

    async def test_has_get_activity_for_resume_tool(self, client):
        """get_activity_for_resume 도구 존재 확인"""
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]

        assert "get_activity_for_resume" in tool_names

    async def test_tool_count(self, client):
        """도구 개수 확인 (기존 3 + 신규 4 = 7)"""
        tools = await client.list_tools()

        assert len(tools) == 7


@pytest.fixture
def mock_commits():
    """테스트용 커밋 데이터"""
    return [
        CommitInfo(
            sha="abc1234",
            message="feat: add feature",
            author="testuser",
            date=datetime(2024, 1, 15, 10, 30),
            repo_name="user/repo",
            url="https://github.com/user/repo/commit/abc1234",
            additions=100,
            deletions=20,
        ),
        CommitInfo(
            sha="def5678",
            message="fix: bug fix",
            author="testuser",
            date=datetime(2024, 1, 16, 14, 0),
            repo_name="user/repo",
            url="https://github.com/user/repo/commit/def5678",
            additions=30,
            deletions=10,
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
            created_at=datetime(2024, 1, 14),
            merged_at=datetime(2024, 1, 16),
            repo_name="user/repo",
            url="https://github.com/user/repo/pull/1",
            additions=150,
            deletions=50,
        ),
    ]


class TestGetCommits:
    """get_commits 도구 테스트"""

    async def test_returns_period(self, client, mock_commits):
        """기간 정보 반환 확인"""
        with patch("work_journal.server.get_weekly_commits", return_value=mock_commits):
            raw_result = await client.call_tool("get_commits", {
                "username": "testuser",
            })
            result = parse_tool_result(raw_result)

        assert "period" in result
        assert "start" in result["period"]
        assert "end" in result["period"]

    async def test_returns_commits(self, client, mock_commits):
        """커밋 목록 반환 확인"""
        with patch("work_journal.server.get_weekly_commits", return_value=mock_commits):
            raw_result = await client.call_tool("get_commits", {
                "username": "testuser",
            })
            result = parse_tool_result(raw_result)

        assert "commits" in result
        assert len(result["commits"]) == 2
        assert result["commits"][0]["sha"] == "abc1234"

    async def test_returns_total_commits(self, client, mock_commits):
        """총 커밋 수 반환 확인"""
        with patch("work_journal.server.get_weekly_commits", return_value=mock_commits):
            raw_result = await client.call_tool("get_commits", {
                "username": "testuser",
            })
            result = parse_tool_result(raw_result)

        assert result["total_commits"] == 2

    async def test_returns_summary_statistics(self, client, mock_commits):
        """요약 통계 반환 확인"""
        with patch("work_journal.server.get_weekly_commits", return_value=mock_commits):
            raw_result = await client.call_tool("get_commits", {
                "username": "testuser",
            })
            result = parse_tool_result(raw_result)

        assert "summary" in result
        assert result["summary"]["total_additions"] == 130
        assert result["summary"]["total_deletions"] == 30

    async def test_week_offset_parameter(self, client, mock_commits):
        """week_offset 파라미터 전달 확인"""
        with patch("work_journal.server.get_weekly_commits", return_value=mock_commits) as mock_fn:
            await client.call_tool("get_commits", {
                "username": "testuser",
                "week_offset": -1,
            })

        mock_fn.assert_called_once_with("testuser", None, -1)

    async def test_repos_parameter(self, client, mock_commits):
        """repos 파라미터 전달 확인"""
        with patch("work_journal.server.get_weekly_commits", return_value=mock_commits) as mock_fn:
            await client.call_tool("get_commits", {
                "username": "testuser",
                "repos": ["user/repo1", "user/repo2"],
            })

        mock_fn.assert_called_once_with("testuser", ["user/repo1", "user/repo2"], 0)


class TestGetWeeklyActivity:
    """get_weekly_activity 도구 테스트"""

    async def test_returns_combined_data(self, client, mock_commits, mock_prs):
        """커밋 + PR 통합 데이터 반환 확인"""
        with patch("work_journal.server.get_weekly_commits", return_value=mock_commits), \
             patch("work_journal.server.get_weekly_prs", return_value=mock_prs):
            raw_result = await client.call_tool("get_weekly_activity", {
                "username": "testuser",
            })
            result = parse_tool_result(raw_result)

        assert "statistics" in result
        assert result["statistics"]["total_commits"] == 2
        assert result["statistics"]["total_prs"] == 1

    async def test_returns_commits_by_repo(self, client, mock_commits, mock_prs):
        """저장소별 커밋 그룹화 확인"""
        with patch("work_journal.server.get_weekly_commits", return_value=mock_commits), \
             patch("work_journal.server.get_weekly_prs", return_value=mock_prs):
            raw_result = await client.call_tool("get_weekly_activity", {
                "username": "testuser",
            })
            result = parse_tool_result(raw_result)

        assert "commits_by_repo" in result
        assert "user/repo" in result["commits_by_repo"]

    async def test_returns_pull_requests(self, client, mock_commits, mock_prs):
        """PR 목록 반환 확인"""
        with patch("work_journal.server.get_weekly_commits", return_value=mock_commits), \
             patch("work_journal.server.get_weekly_prs", return_value=mock_prs):
            raw_result = await client.call_tool("get_weekly_activity", {
                "username": "testuser",
            })
            result = parse_tool_result(raw_result)

        assert "pull_requests" in result
        assert len(result["pull_requests"]) == 1
        assert result["pull_requests"][0]["merged"] is True


class TestGetActivityForResume:
    """get_activity_for_resume 도구 테스트"""

    async def test_returns_overall_statistics(self, client, mock_commits, mock_prs):
        """전체 통계 반환 확인"""
        with patch("work_journal.server.get_weekly_commits", return_value=mock_commits), \
             patch("work_journal.server.get_weekly_prs", return_value=mock_prs):
            raw_result = await client.call_tool("get_activity_for_resume", {
                "username": "testuser",
                "weeks_range": 1,
            })
            result = parse_tool_result(raw_result)

        assert "overall_statistics" in result
        assert "total_commits" in result["overall_statistics"]

    async def test_returns_repo_statistics(self, client, mock_commits, mock_prs):
        """저장소별 통계 반환 확인"""
        with patch("work_journal.server.get_weekly_commits", return_value=mock_commits), \
             patch("work_journal.server.get_weekly_prs", return_value=mock_prs):
            raw_result = await client.call_tool("get_activity_for_resume", {
                "username": "testuser",
                "weeks_range": 1,
            })
            result = parse_tool_result(raw_result)

        assert "repo_statistics" in result

    async def test_returns_notable_prs(self, client, mock_commits, mock_prs):
        """주요 PR 반환 확인"""
        with patch("work_journal.server.get_weekly_commits", return_value=mock_commits), \
             patch("work_journal.server.get_weekly_prs", return_value=mock_prs):
            raw_result = await client.call_tool("get_activity_for_resume", {
                "username": "testuser",
                "weeks_range": 1,
            })
            result = parse_tool_result(raw_result)

        assert "notable_prs" in result

    async def test_weeks_range_parameter(self, client, mock_commits, mock_prs):
        """weeks_range 파라미터 동작 확인"""
        with patch("work_journal.server.get_weekly_commits", return_value=mock_commits) as mock_commits_fn, \
             patch("work_journal.server.get_weekly_prs", return_value=mock_prs):
            await client.call_tool("get_activity_for_resume", {
                "username": "testuser",
                "weeks_range": 4,
            })

        # 4주간 데이터를 가져오므로 4번 호출
        assert mock_commits_fn.call_count == 4
