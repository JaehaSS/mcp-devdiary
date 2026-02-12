"""Few-Shot 리포트 로더 테스트"""

from pathlib import Path
from unittest.mock import patch

import pytest

from work_journal.few_shot import (
    FewShotLoader,
)


class TestFewShotLoader:
    """FewShotLoader 클래스 테스트"""

    @pytest.fixture
    def sample_reports_dir(self, tmp_path):
        """테스트용 리포트 디렉토리"""
        reports_dir = tmp_path / "reports" / "weekly"
        reports_dir.mkdir(parents=True)

        # 리포트 파일 생성
        (reports_dir / "2026-W01_12-29_01-04.md").write_text(
            "# 주간 업무일지: 2026년 1주차\n\n> **작성자:** Test\n\n## 주요 작업 내역\n\n### repo1\n\n| 커밋 | 내용 | 변경 |\n\n## 핵심 성과\n\n### 1. 기능 구현\n\n**What:** 기능 A 구현\n**Why:** 필요\n**How:** 방법\n\n## 기술 스택\n`Python`\n",
            encoding="utf-8",
        )
        (reports_dir / "2026-W02_01-05_01-11.md").write_text(
            "# 주간 업무일지: 2026년 2주차\n\n> **작성자:** Test\n\n## 주요 작업 내역\n\n### repo2\n\n| 커밋 | 내용 | 변경 |\n\n## 핵심 성과\n\n### 1. 리팩토링\n\n**What:** 코드 개선\n**Why:** 유지보수\n**How:** 패턴 적용\n\n## 기술 스택\n`Java`\n",
            encoding="utf-8",
        )
        (reports_dir / "2026-W03_01-12_01-18.md").write_text(
            "# 주간 업무일지: 2026년 3주차\n\n> **작성자:** Test\n\n## 주요 작업 내역\n\n### repo3\n\n| 커밋 | 내용 | 변경 |\n\n## 핵심 성과\n\n### 1. 버그 수정\n\n**What:** 에러 해결\n**Why:** 운영 이슈\n**How:** 디버깅\n\n## 기술 스택\n`React`\n",
            encoding="utf-8",
        )

        return reports_dir

    def test_load_examples_returns_recent_reports(self, sample_reports_dir):
        """최신 리포트 로드"""
        loader = FewShotLoader(reports_dir=str(sample_reports_dir))

        examples = loader.load_examples(count=2)

        assert len(examples) == 2
        # 최신 순서 (W03, W02)
        assert "3주차" in examples[0]
        assert "2주차" in examples[1]

    def test_load_examples_respects_count(self, sample_reports_dir):
        """count 파라미터 동작"""
        loader = FewShotLoader(reports_dir=str(sample_reports_dir))

        examples = loader.load_examples(count=1)

        assert len(examples) == 1

    def test_load_examples_respects_max_chars(self, sample_reports_dir):
        """max_chars 제한 동작"""
        loader = FewShotLoader(reports_dir=str(sample_reports_dir))

        examples = loader.load_examples(count=3, max_chars=100)

        # max_chars를 초과하면 트리밍
        total_chars = sum(len(e) for e in examples)
        assert total_chars <= 100

    def test_load_examples_handles_empty_dir(self, tmp_path):
        """빈 디렉토리 처리"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        loader = FewShotLoader(reports_dir=str(empty_dir))
        examples = loader.load_examples()

        assert examples == []

    def test_load_examples_handles_missing_dir(self):
        """존재하지 않는 디렉토리"""
        loader = FewShotLoader(reports_dir="/nonexistent/path")
        examples = loader.load_examples()

        assert examples == []

    def test_extract_format_guide(self, sample_reports_dir):
        """포맷 가이드 추출"""
        loader = FewShotLoader(reports_dir=str(sample_reports_dir))

        guide = loader.extract_format_guide()

        assert isinstance(guide, str)
        assert len(guide) > 0
        # 포맷 가이드에 핵심 섹션명 포함 여부
        assert "주요 작업 내역" in guide or "핵심 성과" in guide or "기술 스택" in guide
