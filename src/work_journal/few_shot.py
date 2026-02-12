"""Few-shot report loader for weekly work journal generation."""

from pathlib import Path


class FewShotLoader:
    """Load existing weekly reports as few-shot examples."""

    def __init__(self, reports_dir: str = "reports/weekly"):
        """Initialize the loader.

        Args:
            reports_dir: Directory containing weekly report markdown files
        """
        self.reports_dir = reports_dir

    def load_examples(self, count: int = 2, max_chars: int = 4000) -> list[str]:
        """Load most recent report examples.

        Args:
            count: Number of reports to load (default: 2)
            max_chars: Maximum total characters across all reports (default: 4000)

        Returns:
            List of report content strings, newest first. Empty list if no reports found.

        Process:
            1. Scan reports_dir for *.md files
            2. Sort by filename (reverse - newest first)
            3. Select top `count` files
            4. Read each file content
            5. Trim to stay within max_chars total
            6. Return list of report content strings (newest first)
        """
        reports_path = Path(self.reports_dir)

        # Handle missing directory
        if not reports_path.exists():
            return []

        # Find all markdown files
        md_files = sorted(reports_path.glob("*.md"), reverse=True)

        # Handle empty directory
        if not md_files:
            return []

        # Select top count files
        selected_files = md_files[:count]

        # Read files and accumulate content
        examples = []
        total_chars = 0

        for file_path in selected_files:
            try:
                content = file_path.read_text(encoding="utf-8")

                # Check if adding this report would exceed max_chars
                if total_chars + len(content) > max_chars:
                    # Calculate remaining space
                    remaining = max_chars - total_chars
                    if remaining > 0:
                        # Truncate this report to fit
                        examples.append(content[:remaining])
                    break

                examples.append(content)
                total_chars += len(content)

            except Exception:
                # Skip files that can't be read
                continue

        return examples

    def extract_format_guide(self) -> str:
        """Extract format guide from existing reports.

        Returns:
            A text string describing the report format structure.
            If no reports found, returns a default format guide.

        Process:
            - Read 1-2 reports and extract the common structure
            - Identify section headers (주요 작업 내역, 핵심 성과, 기술 스택, etc.)
            - Identify the What/Why/How/Impact pattern
            - Identify table format for commits
        """
        # Try to load 1-2 example reports
        examples = self.load_examples(count=2)

        if not examples:
            # Return default format guide if no reports exist
            return self._default_format_guide()

        # Analyze the first report to extract structure
        report = examples[0]

        # Extract common sections
        sections = []
        lines = report.split('\n')

        for line in lines:
            stripped = line.strip()
            # Look for markdown headers
            if stripped.startswith('#'):
                sections.append(stripped)

        # Build format guide based on found sections
        guide_parts = ["주간 업무 리포트 형식 가이드:\n"]

        # Check for common section keywords
        has_main_tasks = any('주요 작업' in s or '작업 내역' in s for s in sections)
        has_achievements = any('핵심 성과' in s or '성과' in s for s in sections)
        has_tech_stack = any('기술 스택' in s or '스택' in s for s in sections)

        if has_main_tasks:
            guide_parts.append("- 주요 작업 내역 섹션: 주간 커밋 및 PR 활동 요약")

        if has_achievements:
            guide_parts.append("- 핵심 성과 섹션: What/Why/How/Impact 패턴으로 구조화")
            guide_parts.append("  * What: 무엇을 했는가")
            guide_parts.append("  * Why: 왜 했는가")
            guide_parts.append("  * How: 어떻게 했는가")
            guide_parts.append("  * Impact: 어떤 영향이 있는가")

        if has_tech_stack:
            guide_parts.append("- 기술 스택 섹션: 사용된 기술 및 도구 목록")

        # Check for table format
        if '|' in report:
            guide_parts.append("- 표 형식: 마크다운 테이블 사용 (커밋 내역 등)")

        return '\n'.join(guide_parts)

    def _default_format_guide(self) -> str:
        """Return default format guide when no reports exist."""
        return """주간 업무 리포트 형식 가이드:

- 주요 작업 내역 섹션: 주간 커밋 및 PR 활동 요약
- 핵심 성과 섹션: What/Why/How/Impact 패턴으로 구조화
  * What: 무엇을 했는가
  * Why: 왜 했는가
  * How: 어떻게 했는가
  * Impact: 어떤 영향이 있는가
- 기술 스택 섹션: 사용된 기술 및 도구 목록
- 표 형식: 마크다운 테이블 사용 (커밋 내역 등)
"""
