"""설정 관리 모듈 - 환경변수 로드 및 설정"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Config:
    """애플리케이션 설정"""

    github_token: str
    default_username: str | None = None
    claude_sessions_base_path: str | None = None  # Claude Code 세션 경로
    codex_history_path: str | None = None  # Codex 히스토리 경로
    reports_dir: str | None = None  # 주간 리포트 디렉토리

    @classmethod
    def from_env(cls) -> "Config":
        """환경변수에서 설정 로드"""
        load_dotenv()

        github_token = os.getenv("GITHUB_TOKEN")

        if not github_token:
            raise ValueError("GITHUB_TOKEN 환경변수가 설정되지 않았습니다")

        # 경로 설정: 환경변수 또는 기본값 사용
        claude_sessions_path = os.getenv("CLAUDE_SESSIONS_PATH")
        if claude_sessions_path is None:
            claude_sessions_path = os.path.expanduser("~/.claude/projects/")

        codex_history_path = os.getenv("CODEX_HISTORY_PATH")
        if codex_history_path is None:
            codex_history_path = os.path.expanduser("~/.codex/history.jsonl")

        reports_dir = os.getenv("REPORTS_DIR")
        if reports_dir is None:
            reports_dir = "reports/weekly"

        return cls(
            github_token=github_token,
            default_username=os.getenv("GITHUB_USERNAME"),
            claude_sessions_base_path=claude_sessions_path,
            codex_history_path=codex_history_path,
            reports_dir=reports_dir,
        )


# 전역 설정 인스턴스 (lazy loading)
_config: Config | None = None


def get_config() -> Config:
    """설정 인스턴스 반환 (싱글톤)"""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
