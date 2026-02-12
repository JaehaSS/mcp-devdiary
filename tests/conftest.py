"""pytest 공통 설정 및 픽스처"""

import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_env():
    """테스트용 환경변수 설정 (모든 테스트에 자동 적용)"""
    env_vars = {
        "GITHUB_TOKEN": "ghp_test_token_for_testing",
    }
    with patch.dict(os.environ, env_vars):
        # config 모듈의 싱글톤 초기화
        import work_journal.config as config_module
        config_module._config = None
        yield
        config_module._config = None
