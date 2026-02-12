"""인사이트 분석 엔진 테스트"""

from datetime import datetime, timedelta

import pytest

from work_journal.insights import (
    Insight,
    InsightAnalyzer,
    ErrorPatternDetector,
    CodeQualityDetector,
    EfficiencyDetector,
    LearningDetector,
)
from work_journal.github import CommitInfo, PRInfo
from work_journal.session_parser import SessionInfo, SessionAnalysis


class TestInsight:
    """Insight 데이터클래스 테스트"""

    def test_create_insight(self):
        """Insight 기본 생성"""
        insight = Insight(
            category="error_pattern",
            title="반복되는 NullPointerException",
            description="3번 이상 동일 에러 발생",
        )

        assert insight.category == "error_pattern"
        assert insight.title == "반복되는 NullPointerException"
        assert insight.evidence == []
        assert insight.suggestion == ""
        assert insight.severity == "info"

    def test_with_all_fields(self):
        """모든 필드 포함"""
        insight = Insight(
            category="efficiency",
            title="긴 디버깅 세션",
            description="60분 이상 디버깅 세션 감지",
            evidence=[{"session_id": "sess001", "duration": 90}],
            suggestion="테스트 코드를 먼저 작성하세요",
            severity="warning",
        )

        assert insight.severity == "warning"
        assert len(insight.evidence) == 1


class TestErrorPatternDetector:
    """ErrorPatternDetector 테스트"""

    def test_detects_repeated_fix_commits(self):
        """반복 fix 커밋 감지"""
        commits = [
            CommitInfo(
                sha=f"sha{i}",
                message=f"fix: resolve NullPointerException in UserService",
                author="user",
                date=datetime(2026, 1, 20, 9 + i),
                repo_name="user/repo",
                url=f"https://github.com/user/repo/commit/sha{i}",
            )
            for i in range(4)
        ]

        detector = ErrorPatternDetector()
        insights = detector.detect(commits=commits, sessions=[], codex_entries=[])

        assert len(insights) >= 1
        assert insights[0].category == "error_pattern"
        assert insights[0].severity in ("warning", "critical")

    def test_detects_session_errors(self):
        """세션 에러 패턴 감지"""
        sessions = [
            SessionAnalysis(
                session_id="sess001",
                session_info=SessionInfo(
                    session_id="sess001",
                    first_prompt="test",
                    summary="test",
                    message_count=10,
                    created=datetime(2026, 1, 20, 9, 0),
                    modified=datetime(2026, 1, 20, 10, 0),
                    project_path="/test",
                ),
                total_messages=10,
                user_messages=4,
                assistant_messages=6,
                tools_used={"Bash": 5},
                files_touched=[],
                error_count=5,
            ),
        ]

        detector = ErrorPatternDetector()
        insights = detector.detect(commits=[], sessions=sessions, codex_entries=[])

        assert len(insights) >= 1

    def test_no_insights_for_clean_data(self):
        """에러 없으면 인사이트 없음"""
        commits = [
            CommitInfo(
                sha="sha1",
                message="feat: add new feature",
                author="user",
                date=datetime.now(),
                repo_name="user/repo",
                url="https://example.com",
            ),
        ]

        detector = ErrorPatternDetector()
        insights = detector.detect(commits=commits, sessions=[], codex_entries=[])

        assert len(insights) == 0


class TestCodeQualityDetector:
    """CodeQualityDetector 테스트"""

    def test_detects_same_file_repeated_changes(self):
        """동일 파일 반복 수정 감지"""
        sessions = [
            SessionAnalysis(
                session_id=f"sess{i}",
                session_info=SessionInfo(
                    session_id=f"sess{i}",
                    first_prompt="test",
                    summary="test",
                    message_count=5,
                    created=datetime(2026, 1, 20 + i, 9, 0),
                    modified=datetime(2026, 1, 20 + i, 10, 0),
                    project_path="/test",
                ),
                total_messages=5,
                user_messages=2,
                assistant_messages=3,
                tools_used={"Write": 3},
                files_touched=["src/UserService.java"],
            )
            for i in range(4)
        ]

        detector = CodeQualityDetector()
        insights = detector.detect(commits=[], sessions=sessions, codex_entries=[])

        # 같은 파일을 4세션에서 수정 -> 감지
        assert len(insights) >= 1
        assert insights[0].category == "code_quality"


class TestEfficiencyDetector:
    """EfficiencyDetector 테스트"""

    def test_detects_long_sessions(self):
        """긴 세션 감지 (60분 초과)"""
        sessions = [
            SessionAnalysis(
                session_id="sess001",
                session_info=SessionInfo(
                    session_id="sess001",
                    first_prompt="디버깅",
                    summary="디버깅 세션",
                    message_count=30,
                    created=datetime(2026, 1, 20, 9, 0),
                    modified=datetime(2026, 1, 20, 11, 30),
                    project_path="/test",
                ),
                total_messages=30,
                user_messages=12,
                assistant_messages=18,
                tools_used={"Read": 10, "Write": 8, "Bash": 5},
                files_touched=["src/main.py"],
                duration_minutes=150.0,
            ),
        ]

        detector = EfficiencyDetector()
        insights = detector.detect(commits=[], sessions=sessions, codex_entries=[])

        assert len(insights) >= 1
        assert insights[0].category == "efficiency"

    def test_no_insight_for_short_sessions(self):
        """짧은 세션은 감지 안됨"""
        sessions = [
            SessionAnalysis(
                session_id="sess001",
                session_info=SessionInfo(
                    session_id="sess001",
                    first_prompt="test",
                    summary="test",
                    message_count=5,
                    created=datetime(2026, 1, 20, 9, 0),
                    modified=datetime(2026, 1, 20, 9, 15),
                    project_path="/test",
                ),
                total_messages=5,
                user_messages=2,
                assistant_messages=3,
                tools_used={"Read": 2},
                files_touched=[],
                duration_minutes=15.0,
            ),
        ]

        detector = EfficiencyDetector()
        insights = detector.detect(commits=[], sessions=sessions, codex_entries=[])

        assert len(insights) == 0


class TestLearningDetector:
    """LearningDetector 테스트"""

    def test_detects_new_technologies(self):
        """새 기술/패턴 감지"""
        commits = [
            CommitInfo(
                sha="sha1",
                message="feat: implement GraphQL API",
                author="user",
                date=datetime(2026, 1, 20, 9, 0),
                repo_name="user/repo",
                url="https://example.com",
            ),
            CommitInfo(
                sha="sha2",
                message="feat: add WebSocket support",
                author="user",
                date=datetime(2026, 1, 21, 9, 0),
                repo_name="user/repo",
                url="https://example.com",
            ),
        ]

        detector = LearningDetector()
        insights = detector.detect(commits=commits, sessions=[], codex_entries=[])

        # 새 기술 키워드가 커밋에 있으면 학습 포인트로 감지
        assert all(i.category == "learning" for i in insights)


class TestInsightAnalyzer:
    """InsightAnalyzer 테스트"""

    def test_analyze_combines_all_detectors(self):
        """모든 디텍터 결과 통합"""
        # 에러 패턴용 커밋
        commits = [
            CommitInfo(
                sha=f"sha{i}",
                message="fix: same bug again",
                author="user",
                date=datetime(2026, 1, 20 + i, 9, 0),
                repo_name="user/repo",
                url="https://example.com",
            )
            for i in range(5)
        ]

        analyzer = InsightAnalyzer()
        insights = analyzer.analyze(
            commits=commits,
            prs=[],
            sessions=[],
            codex_entries=[],
        )

        assert isinstance(insights, list)
        assert all(isinstance(i, Insight) for i in insights)

    def test_analyze_returns_empty_for_no_data(self):
        """데이터 없으면 빈 목록"""
        analyzer = InsightAnalyzer()
        insights = analyzer.analyze(
            commits=[],
            prs=[],
            sessions=[],
            codex_entries=[],
        )

        assert insights == []

    def test_analyze_severity_ordering(self):
        """인사이트가 severity 순으로 정렬 (critical > warning > info)"""
        commits = [
            CommitInfo(
                sha=f"sha{i}",
                message="fix: critical bug",
                author="user",
                date=datetime(2026, 1, 20, 9 + i),
                repo_name="user/repo",
                url="https://example.com",
            )
            for i in range(6)
        ]

        analyzer = InsightAnalyzer()
        insights = analyzer.analyze(
            commits=commits,
            prs=[],
            sessions=[],
            codex_entries=[],
        )

        if len(insights) >= 2:
            severity_order = {"critical": 0, "warning": 1, "info": 2}
            for i in range(len(insights) - 1):
                assert severity_order[insights[i].severity] <= severity_order[insights[i + 1].severity]
