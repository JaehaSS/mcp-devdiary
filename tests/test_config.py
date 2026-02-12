"""Config 모듈 테스트"""

import os
from unittest.mock import patch

import pytest

from work_journal.config import Config


class TestConfig:
    """Config 클래스 테스트"""

    def test_from_env_with_valid_token(self):
        """유효한 토큰으로 설정 로드"""
        env_vars = {
            "GITHUB_TOKEN": "ghp_test_token_12345",
            "GITHUB_USERNAME": "testuser",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

        assert config.github_token == "ghp_test_token_12345"
        assert config.default_username == "testuser"

    def test_from_env_without_github_token_raises(self):
        """GITHUB_TOKEN 없으면 에러"""
        # conftest의 autouse fixture를 우회하기 위해 싱글톤 초기화
        import work_journal.config as config_module
        config_module._config = None

        # load_dotenv도 mock해서 .env 파일 로드 방지
        with patch("work_journal.config.load_dotenv"):
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(ValueError) as exc_info:
                    Config.from_env()

        assert "GITHUB_TOKEN" in str(exc_info.value)

    def test_default_username_is_optional(self):
        """GITHUB_USERNAME은 선택사항"""
        env_vars = {
            "GITHUB_TOKEN": "ghp_test_token",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

        assert config.default_username is None

    def test_config_dataclass_fields(self):
        """Config 필드 테스트"""
        config = Config(
            github_token="token",
            default_username="user",
        )

        assert config.github_token == "token"
        assert config.default_username == "user"

    def test_config_default_values(self):
        """기본값 테스트"""
        config = Config(github_token="token")

        assert config.default_username is None
