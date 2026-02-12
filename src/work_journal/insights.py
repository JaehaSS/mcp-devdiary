"""Insight analysis engine for work journal data."""

from dataclasses import dataclass, field
from collections import Counter
import re


@dataclass
class Insight:
    """Represents a detected insight from work journal data."""
    category: str       # "error_pattern" | "code_quality" | "efficiency" | "learning"
    title: str
    description: str
    evidence: list[dict] = field(default_factory=list)
    suggestion: str = ""
    severity: str = "info"  # "info" | "warning" | "critical"


class ErrorPatternDetector:
    """Detects error patterns in commits and sessions."""

    def detect(self, commits: list, sessions: list, codex_entries: list) -> list[Insight]:
        """Detect error patterns from commits and sessions."""
        insights = []

        # Analyze commits for repeated "fix:" patterns
        if commits:
            fix_keywords = []
            for commit in commits:
                msg = commit.message if hasattr(commit, 'message') else str(commit)
                if msg.lower().startswith("fix:"):
                    # Extract the text after "fix:" and clean it
                    fix_text = msg[4:].strip().lower()
                    # Extract key terms (first few words or significant keywords)
                    words = fix_text.split()[:3]  # Take first 3 words as key
                    if words:
                        fix_keywords.append(" ".join(words))

            # Count repeated fix patterns
            if fix_keywords:
                keyword_counts = Counter(fix_keywords)
                for keyword, count in keyword_counts.items():
                    if count >= 5:
                        insights.append(Insight(
                            category="error_pattern",
                            title=f"Repeated fix pattern: {keyword}",
                            description=f"The same issue has been fixed {count} times",
                            evidence=[{"type": "commit_pattern", "keyword": keyword, "count": count}],
                            suggestion="Consider addressing the root cause to prevent recurrence",
                            severity="critical"
                        ))
                    elif count >= 3:
                        insights.append(Insight(
                            category="error_pattern",
                            title=f"Recurring fix pattern: {keyword}",
                            description=f"This issue has been fixed {count} times",
                            evidence=[{"type": "commit_pattern", "keyword": keyword, "count": count}],
                            suggestion="Review the underlying implementation",
                            severity="warning"
                        ))

        # Analyze sessions for high error counts
        if sessions:
            for session in sessions:
                error_count = getattr(session, 'error_count', 0)
                if error_count >= 3:
                    session_id = getattr(session, 'session_id', 'unknown')
                    insights.append(Insight(
                        category="error_pattern",
                        title=f"High error count in session {session_id}",
                        description=f"Session had {error_count} errors",
                        evidence=[{"type": "session_errors", "session_id": session_id, "count": error_count}],
                        suggestion="Review error logs and consider adding error handling",
                        severity="warning"
                    ))

        return insights


class CodeQualityDetector:
    """Detects code quality issues from session patterns."""

    def detect(self, commits: list, sessions: list, codex_entries: list) -> list[Insight]:
        """Detect code quality issues from repeated file modifications."""
        insights = []

        if not sessions:
            return insights

        # Track files touched across sessions
        file_session_count = Counter()
        for session in sessions:
            files_touched = getattr(session, 'files_touched', [])
            for file in files_touched:
                file_session_count[file] += 1

        # Find files modified in 3+ sessions
        for file, count in file_session_count.items():
            if count >= 3:
                insights.append(Insight(
                    category="code_quality",
                    title=f"Frequently modified file: {file}",
                    description=f"This file was modified in {count} different sessions",
                    evidence=[{"type": "file_modifications", "file": file, "session_count": count}],
                    suggestion="Consider refactoring this file to improve stability",
                    severity="warning"
                ))

        return insights


class EfficiencyDetector:
    """Detects efficiency issues from session durations."""

    def detect(self, commits: list, sessions: list, codex_entries: list) -> list[Insight]:
        """Detect efficiency issues from long sessions."""
        insights = []

        if not sessions:
            return insights

        for session in sessions:
            duration = getattr(session, 'duration_minutes', 0)
            if duration > 60:
                session_id = getattr(session, 'session_id', 'unknown')
                insights.append(Insight(
                    category="efficiency",
                    title=f"Long session detected: {session_id}",
                    description=f"Session lasted {duration:.1f} minutes",
                    evidence=[{"type": "long_session", "session_id": session_id, "duration_minutes": duration}],
                    suggestion="Consider breaking down work into smaller tasks",
                    severity="warning"
                ))

        return insights


class LearningDetector:
    """Detects learning opportunities from technology usage."""

    TECH_KEYWORDS = {
        'graphql', 'websocket', 'docker', 'kubernetes', 'redis',
        'mongodb', 'postgresql', 'typescript', 'react', 'vue',
        'angular', 'svelte', 'rust', 'go', 'kotlin', 'swift',
        'terraform', 'ansible', 'jenkins', 'github actions',
        'aws', 'azure', 'gcp', 'lambda', 'microservices'
    }

    def detect(self, commits: list, sessions: list, codex_entries: list) -> list[Insight]:
        """Detect learning opportunities from technology keywords."""
        insights = []

        if not commits:
            return insights

        # Find technology keywords in commit messages
        found_techs = set()
        for commit in commits:
            msg = commit.message if hasattr(commit, 'message') else str(commit)
            msg_lower = msg.lower()

            for tech in self.TECH_KEYWORDS:
                if tech in msg_lower:
                    found_techs.add(tech)

        # Create insights for each unique technology
        for tech in sorted(found_techs):
            insights.append(Insight(
                category="learning",
                title=f"Technology used: {tech.title()}",
                description=f"Work involved {tech.title()} technology",
                evidence=[{"type": "technology", "name": tech}],
                suggestion=f"Document learnings about {tech.title()} for future reference",
                severity="info"
            ))

        return insights


class InsightAnalyzer:
    """Main analyzer that coordinates all detectors."""

    def __init__(self):
        self.detectors = [
            ErrorPatternDetector(),
            CodeQualityDetector(),
            EfficiencyDetector(),
            LearningDetector(),
        ]

    def analyze(self, commits, prs, sessions, codex_entries) -> list[Insight]:
        """Analyze all data sources and return sorted insights."""
        all_insights = []

        # Run all detectors
        for detector in self.detectors:
            insights = detector.detect(commits, sessions, codex_entries)
            all_insights.extend(insights)

        # Sort by severity: critical > warning > info
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        all_insights.sort(key=lambda x: severity_order.get(x.severity, 3))

        return all_insights
