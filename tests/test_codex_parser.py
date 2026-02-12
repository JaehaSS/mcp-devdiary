"""Codex 세션 파서 테스트"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from work_journal.codex_parser import (
    CodexEntry,
    get_weekly_codex_entries,
)
from work_journal.github import get_week_range


class TestCodexEntry:
    """CodexEntry 데이터클래스 테스트"""

    def test_create_codex_entry(self):
        """CodexEntry 기본 생성"""
        entry = CodexEntry(
            session_id="codex001",
            timestamp=datetime(2026, 1, 20, 9, 0),
            text="프로젝트 구조를 분석해줘",
            source="codex",
        )

        assert entry.session_id == "codex001"
        assert entry.text == "프로젝트 구조를 분석해줘"
        assert entry.source == "codex"

    def test_default_source(self):
        """기본 소스 값"""
        entry = CodexEntry(
            session_id="codex001",
            timestamp=datetime.now(),
            text="test",
        )

        assert entry.source == "codex"


class TestGetWeeklyCodexEntries:
    """get_weekly_codex_entries 함수 테스트"""

    def test_parses_codex_history(self, tmp_path):
        """Codex history.jsonl 파싱"""
        start, end = get_week_range(0)
        within_week = start + timedelta(days=1)
        ts = within_week.timestamp()

        history_file = tmp_path / "history.jsonl"
        entries = [
            {"ts": ts, "prompt": "테스트 코드 작성해줘"},
            {"ts": ts + 3600, "prompt": "버그 수정해줘"},
        ]
        lines = [json.dumps(e) for e in entries]
        history_file.write_text("\n".join(lines), encoding="utf-8")

        with patch(
            "work_journal.codex_parser.get_codex_history_path",
            return_value=str(history_file),
        ):
            results = get_weekly_codex_entries(week_offset=0)

        assert len(results) == 2
        assert results[0].text == "테스트 코드 작성해줘"
        assert results[0].source == "codex"

    def test_filters_by_week(self, tmp_path):
        """주간 필터링 확인"""
        start, end = get_week_range(0)
        within_week = start + timedelta(days=2)
        outside_week = start - timedelta(days=5)

        history_file = tmp_path / "history.jsonl"
        entries = [
            {"ts": within_week.timestamp(), "prompt": "이번주 항목"},
            {"ts": outside_week.timestamp(), "prompt": "지난주 항목"},
        ]
        lines = [json.dumps(e) for e in entries]
        history_file.write_text("\n".join(lines), encoding="utf-8")

        with patch(
            "work_journal.codex_parser.get_codex_history_path",
            return_value=str(history_file),
        ):
            results = get_weekly_codex_entries(week_offset=0)

        assert len(results) == 1
        assert results[0].text == "이번주 항목"

    def test_handles_missing_file(self):
        """파일이 없는 경우 빈 목록 반환"""
        with patch(
            "work_journal.codex_parser.get_codex_history_path",
            return_value="/nonexistent/history.jsonl",
        ):
            results = get_weekly_codex_entries(week_offset=0)

        assert results == []

    def test_handles_empty_file(self, tmp_path):
        """빈 파일 처리"""
        history_file = tmp_path / "history.jsonl"
        history_file.write_text("", encoding="utf-8")

        with patch(
            "work_journal.codex_parser.get_codex_history_path",
            return_value=str(history_file),
        ):
            results = get_weekly_codex_entries(week_offset=0)

        assert results == []

    def test_skips_invalid_lines(self, tmp_path):
        """잘못된 JSON 라인 건너뜀"""
        start, _ = get_week_range(0)
        within_week = start + timedelta(days=1)

        history_file = tmp_path / "history.jsonl"
        lines = [
            json.dumps({"ts": within_week.timestamp(), "prompt": "valid"}),
            "invalid json",
            json.dumps({"ts": within_week.timestamp(), "prompt": "also valid"}),
        ]
        history_file.write_text("\n".join(lines), encoding="utf-8")

        with patch(
            "work_journal.codex_parser.get_codex_history_path",
            return_value=str(history_file),
        ):
            results = get_weekly_codex_entries(week_offset=0)

        assert len(results) == 2
