"""Claude Code 세션 파서 테스트"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from work_journal.session_parser import (
    SessionInfo,
    SessionMessage,
    SessionAnalysis,
    get_all_session_indices,
    get_weekly_sessions,
    parse_session_messages,
    analyze_session,
)
from work_journal.github import get_week_range


# ===== 데이터클래스 테스트 =====


class TestSessionInfo:
    """SessionInfo 데이터클래스 테스트"""

    def test_create_session_info(self):
        """SessionInfo 기본 생성"""
        info = SessionInfo(
            session_id="abc123",
            first_prompt="프로젝트 구조 분석해줘",
            summary="프로젝트 구조를 분석했습니다",
            message_count=10,
            created=datetime(2026, 1, 20, 9, 0),
            modified=datetime(2026, 1, 20, 10, 30),
            project_path="/home/user/my-project",
            source="claude_code",
        )

        assert info.session_id == "abc123"
        assert info.first_prompt == "프로젝트 구조 분석해줘"
        assert info.message_count == 10
        assert info.source == "claude_code"

    def test_default_values(self):
        """기본값 확인"""
        info = SessionInfo(
            session_id="abc123",
            first_prompt="test",
            summary="test summary",
            message_count=1,
            created=datetime.now(),
            modified=datetime.now(),
            project_path="/test",
        )

        assert info.git_branch == ""
        assert info.source == "claude_code"

    def test_with_git_branch(self):
        """git_branch 필드 포함"""
        info = SessionInfo(
            session_id="abc123",
            first_prompt="test",
            summary="test",
            message_count=1,
            created=datetime.now(),
            modified=datetime.now(),
            project_path="/test",
            git_branch="feature/auth",
        )

        assert info.git_branch == "feature/auth"


class TestSessionMessage:
    """SessionMessage 데이터클래스 테스트"""

    def test_create_session_message(self):
        """SessionMessage 기본 생성"""
        msg = SessionMessage(
            message_id="msg001",
            session_id="abc123",
            timestamp=datetime(2026, 1, 20, 9, 0),
            role="user",
            content_text="파일을 읽어줘",
        )

        assert msg.role == "user"
        assert msg.content_text == "파일을 읽어줘"
        assert msg.tool_uses == []

    def test_with_tool_uses(self):
        """도구 사용 목록 포함"""
        msg = SessionMessage(
            message_id="msg002",
            session_id="abc123",
            timestamp=datetime.now(),
            role="assistant",
            content_text="파일을 읽겠습니다",
            tool_uses=["Read", "Grep", "Write"],
        )

        assert len(msg.tool_uses) == 3
        assert "Read" in msg.tool_uses


class TestSessionAnalysis:
    """SessionAnalysis 데이터클래스 테스트"""

    def test_create_session_analysis(self):
        """SessionAnalysis 기본 생성"""
        info = SessionInfo(
            session_id="abc123",
            first_prompt="test",
            summary="test",
            message_count=20,
            created=datetime.now(),
            modified=datetime.now(),
            project_path="/test",
        )

        analysis = SessionAnalysis(
            session_id="abc123",
            session_info=info,
            total_messages=20,
            user_messages=8,
            assistant_messages=12,
            tools_used={"Read": 5, "Write": 3, "Bash": 2},
            files_touched=["src/main.py", "tests/test_main.py"],
        )

        assert analysis.total_messages == 20
        assert analysis.tools_used["Read"] == 5
        assert len(analysis.files_touched) == 2

    def test_default_values(self):
        """기본값 확인"""
        info = SessionInfo(
            session_id="abc123",
            first_prompt="test",
            summary="test",
            message_count=1,
            created=datetime.now(),
            modified=datetime.now(),
            project_path="/test",
        )

        analysis = SessionAnalysis(
            session_id="abc123",
            session_info=info,
            total_messages=1,
            user_messages=1,
            assistant_messages=0,
            tools_used={},
            files_touched=[],
        )

        assert analysis.error_count == 0
        assert analysis.duration_minutes == 0.0
        assert analysis.topics == []


# ===== 함수 테스트 =====


class TestGetAllSessionIndices:
    """get_all_session_indices 함수 테스트"""

    def test_returns_list_of_session_info(self, tmp_path):
        """세션 인덱스 파싱하여 SessionInfo 목록 반환"""
        # 임시 sessions-index.json 생성
        project_dir = tmp_path / "project1"
        project_dir.mkdir()

        index_data = {
            "entries": [
                {
                    "sessionId": "sess001",
                    "firstPrompt": "프로젝트 분석",
                    "summary": "프로젝트를 분석했습니다",
                    "messageCount": 15,
                    "created": "2026-01-20T09:00:00.000Z",
                    "modified": "2026-01-20T10:30:00.000Z",
                    "projectPath": "/home/user/my-project",
                }
            ]
        }

        (project_dir / "sessions-index.json").write_text(
            json.dumps(index_data), encoding="utf-8"
        )

        with patch(
            "work_journal.session_parser.get_claude_projects_dirs",
            return_value=[project_dir],
        ):
            results = get_all_session_indices()

        assert len(results) == 1
        assert results[0].session_id == "sess001"
        assert results[0].first_prompt == "프로젝트 분석"
        assert results[0].message_count == 15
        assert results[0].project_path == "/home/user/my-project"

    def test_returns_empty_list_when_no_sessions(self, tmp_path):
        """세션 디렉토리가 비어있으면 빈 목록 반환"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch(
            "work_journal.session_parser.get_claude_projects_dirs",
            return_value=[empty_dir],
        ):
            results = get_all_session_indices()

        assert results == []

    def test_skips_invalid_json(self, tmp_path):
        """잘못된 JSON 파일은 건너뜀"""
        project_dir = tmp_path / "bad"
        project_dir.mkdir()

        (project_dir / "sessions-index.json").write_text(
            "not valid json", encoding="utf-8"
        )

        with patch(
            "work_journal.session_parser.get_claude_projects_dirs",
            return_value=[project_dir],
        ):
            results = get_all_session_indices()

        assert results == []

    def test_handles_missing_directory(self):
        """존재하지 않는 디렉토리 처리"""
        with patch(
            "work_journal.session_parser.get_claude_projects_dirs",
            return_value=[],
        ):
            results = get_all_session_indices()

        assert results == []


class TestGetWeeklySessions:
    """get_weekly_sessions 함수 테스트"""

    def test_filters_sessions_by_week(self, tmp_path):
        """주간 범위로 세션 필터링"""
        start, end = get_week_range(0)

        # 이번 주 세션
        within_week = start + timedelta(days=1)
        # 지난 주 세션
        outside_week = start - timedelta(days=3)

        project_dir = tmp_path / "project1"
        project_dir.mkdir()

        index_data = {
            "entries": [
                {
                    "sessionId": "in_range",
                    "firstPrompt": "이번주 세션",
                    "summary": "이번주",
                    "messageCount": 5,
                    "created": within_week.isoformat(),
                    "modified": within_week.isoformat(),
                    "projectPath": "/test",
                },
                {
                    "sessionId": "out_range",
                    "firstPrompt": "지난주 세션",
                    "summary": "지난주",
                    "messageCount": 3,
                    "created": outside_week.isoformat(),
                    "modified": outside_week.isoformat(),
                    "projectPath": "/test",
                },
            ]
        }

        (project_dir / "sessions-index.json").write_text(
            json.dumps(index_data), encoding="utf-8"
        )

        with patch(
            "work_journal.session_parser.get_claude_projects_dirs",
            return_value=[project_dir],
        ):
            results = get_weekly_sessions(week_offset=0)

        assert len(results) == 1
        assert results[0].session_id == "in_range"

    def test_project_filter(self, tmp_path):
        """프로젝트 필터 적용"""
        start, _ = get_week_range(0)
        within_week = start + timedelta(days=1)

        project_dir = tmp_path / "project1"
        project_dir.mkdir()

        index_data = {
            "entries": [
                {
                    "sessionId": "match",
                    "firstPrompt": "test",
                    "summary": "test",
                    "messageCount": 5,
                    "created": within_week.isoformat(),
                    "modified": within_week.isoformat(),
                    "projectPath": "/home/user/my-project",
                },
                {
                    "sessionId": "no_match",
                    "firstPrompt": "test",
                    "summary": "test",
                    "messageCount": 3,
                    "created": within_week.isoformat(),
                    "modified": within_week.isoformat(),
                    "projectPath": "/home/user/other-project",
                },
            ]
        }

        (project_dir / "sessions-index.json").write_text(
            json.dumps(index_data), encoding="utf-8"
        )

        with patch(
            "work_journal.session_parser.get_claude_projects_dirs",
            return_value=[project_dir],
        ):
            results = get_weekly_sessions(week_offset=0, project_filter="my-project")

        assert len(results) == 1
        assert results[0].session_id == "match"


class TestParseSessionMessages:
    """parse_session_messages 함수 테스트"""

    def test_parses_jsonl_messages(self, tmp_path):
        """JSONL 파일에서 메시지 파싱"""
        session_file = tmp_path / "session.jsonl"
        messages = [
            {
                "type": "user",
                "uuid": "msg001",
                "timestamp": "2026-01-20T09:00:00.000Z",
                "message": {
                    "content": [{"type": "text", "text": "파일을 읽어줘"}],
                },
            },
            {
                "type": "assistant",
                "uuid": "msg002",
                "timestamp": "2026-01-20T09:01:00.000Z",
                "message": {
                    "content": [
                        {"type": "text", "text": "파일을 읽겠습니다"},
                        {"type": "tool_use", "name": "Read"},
                    ],
                },
            },
        ]

        lines = [json.dumps(m) for m in messages]
        session_file.write_text("\n".join(lines), encoding="utf-8")

        results = parse_session_messages(str(session_file), "sess001")

        assert len(results) == 2
        assert results[0].role == "user"
        assert results[0].content_text == "파일을 읽어줘"
        assert results[1].role == "assistant"
        assert results[1].tool_uses == ["Read"]

    def test_handles_empty_file(self, tmp_path):
        """빈 파일 처리"""
        session_file = tmp_path / "empty.jsonl"
        session_file.write_text("", encoding="utf-8")

        results = parse_session_messages(str(session_file), "sess001")

        assert results == []

    def test_handles_nonexistent_file(self):
        """존재하지 않는 파일 처리"""
        results = parse_session_messages("/nonexistent/path.jsonl", "sess001")

        assert results == []

    def test_skips_invalid_lines(self, tmp_path):
        """잘못된 JSON 라인 건너뜀"""
        session_file = tmp_path / "partial.jsonl"
        lines = [
            json.dumps({
                "type": "user",
                "uuid": "msg001",
                "timestamp": "2026-01-20T09:00:00.000Z",
                "message": {
                    "content": [{"type": "text", "text": "hello"}],
                },
            }),
            "not valid json {{{",
            json.dumps({
                "type": "assistant",
                "uuid": "msg002",
                "timestamp": "2026-01-20T09:01:00.000Z",
                "message": {
                    "content": [{"type": "text", "text": "world"}],
                },
            }),
        ]
        session_file.write_text("\n".join(lines), encoding="utf-8")

        results = parse_session_messages(str(session_file), "sess001")

        assert len(results) == 2

    def test_extracts_tool_result_errors(self, tmp_path):
        """tool_result 에러 감지"""
        session_file = tmp_path / "errors.jsonl"
        messages = [
            {
                "type": "assistant",
                "uuid": "msg001",
                "timestamp": "2026-01-20T09:00:00.000Z",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Bash"},
                        {"type": "tool_result", "is_error": True},
                    ],
                },
            },
        ]

        lines = [json.dumps(m) for m in messages]
        session_file.write_text("\n".join(lines), encoding="utf-8")

        results = parse_session_messages(str(session_file), "sess001")

        assert len(results) == 1


class TestAnalyzeSession:
    """analyze_session 함수 테스트"""

    def test_computes_statistics(self, tmp_path):
        """세션 분석 통계 계산"""
        session_file = tmp_path / "session.jsonl"
        messages = [
            {
                "type": "user",
                "uuid": "msg001",
                "timestamp": "2026-01-20T09:00:00.000Z",
                "message": {
                    "content": [{"type": "text", "text": "파일 구조 확인해줘"}],
                },
            },
            {
                "type": "assistant",
                "uuid": "msg002",
                "timestamp": "2026-01-20T09:05:00.000Z",
                "message": {
                    "content": [
                        {"type": "text", "text": "확인하겠습니다"},
                        {"type": "tool_use", "name": "Read"},
                        {"type": "tool_use", "name": "Glob"},
                    ],
                },
            },
            {
                "type": "user",
                "uuid": "msg003",
                "timestamp": "2026-01-20T09:10:00.000Z",
                "message": {
                    "content": [{"type": "text", "text": "수정해줘"}],
                },
            },
            {
                "type": "assistant",
                "uuid": "msg004",
                "timestamp": "2026-01-20T09:30:00.000Z",
                "message": {
                    "content": [
                        {"type": "text", "text": "수정했습니다"},
                        {"type": "tool_use", "name": "Write"},
                        {"type": "tool_use", "name": "Read"},
                    ],
                },
            },
        ]

        lines = [json.dumps(m) for m in messages]
        session_file.write_text("\n".join(lines), encoding="utf-8")

        info = SessionInfo(
            session_id="sess001",
            first_prompt="파일 구조 확인해줘",
            summary="파일 구조를 확인하고 수정했습니다",
            message_count=4,
            created=datetime(2026, 1, 20, 9, 0),
            modified=datetime(2026, 1, 20, 9, 30),
            project_path="/test",
        )

        analysis = analyze_session(info, str(session_file))

        assert analysis.total_messages == 4
        assert analysis.user_messages == 2
        assert analysis.assistant_messages == 2
        assert analysis.tools_used["Read"] == 2
        assert analysis.tools_used["Write"] == 1
        assert analysis.tools_used["Glob"] == 1
        assert analysis.duration_minutes == pytest.approx(30.0, abs=1.0)

    def test_handles_missing_file(self):
        """파일 없는 경우 기본값 반환"""
        info = SessionInfo(
            session_id="sess001",
            first_prompt="test",
            summary="test",
            message_count=0,
            created=datetime.now(),
            modified=datetime.now(),
            project_path="/test",
        )

        analysis = analyze_session(info, "/nonexistent/path.jsonl")

        assert analysis.total_messages == 0
        assert analysis.user_messages == 0
        assert analysis.assistant_messages == 0
        assert analysis.tools_used == {}

    def test_error_counting(self, tmp_path):
        """에러 카운트"""
        session_file = tmp_path / "errors.jsonl"
        messages = [
            {
                "type": "assistant",
                "uuid": "msg001",
                "timestamp": "2026-01-20T09:00:00.000Z",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Bash"},
                        {"type": "tool_result", "is_error": True},
                        {"type": "tool_use", "name": "Bash"},
                        {"type": "tool_result", "is_error": True},
                    ],
                },
            },
            {
                "type": "assistant",
                "uuid": "msg002",
                "timestamp": "2026-01-20T09:05:00.000Z",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Read"},
                        {"type": "tool_result", "is_error": False},
                    ],
                },
            },
        ]

        lines = [json.dumps(m) for m in messages]
        session_file.write_text("\n".join(lines), encoding="utf-8")

        info = SessionInfo(
            session_id="sess001",
            first_prompt="test",
            summary="test",
            message_count=2,
            created=datetime(2026, 1, 20, 9, 0),
            modified=datetime(2026, 1, 20, 9, 5),
            project_path="/test",
        )

        analysis = analyze_session(info, str(session_file))

        assert analysis.error_count == 2
