# mcp-devdiary

**GitHub 활동과 AI 에이전트 세션을 자동 수집하여 구조화된 주간 업무일지를 생성하는 MCP 서버**

[English](./README.md)

---

- GitHub 커밋, PR, Claude Code 세션, Codex 기록을 자동 수집
- 개발 활동으로부터 주간 리포트, 타임라인, 인사이트 생성
- 축적된 작업 데이터에서 이력서용 성과 문장 자동 생성
- 오픈소스, 로컬 환경에서 실행

> mcp-devdiary은 알아서 작성되는 개인 개발 일지입니다.
> GitHub와 로컬 AI 에이전트 기록에 연결되어, MCP를 통해 구조화된 데이터를 제공합니다.
> Claude가 이 데이터를 바탕으로 주간 요약, 패턴 분석, 이력서 문장을 작성해줍니다.

## MCP 도구

mcp-devdiary은 [Model Context Protocol](https://modelcontextprotocol.io/)을 통해 7개의 도구를 제공합니다:

| 도구                         | 설명                                                  |
| ---------------------------- | ----------------------------------------------------- |
| `get_commits`                | 주간 GitHub 커밋 조회 (통계 포함)                     |
| `get_weekly_activity`        | 주간 통합 활동 조회 (커밋 + PR + 에이전트 세션)       |
| `get_activity_for_resume`    | 이력서 작성용 다주간 활동 데이터                      |
| `get_agent_sessions`         | Claude Code, Codex 세션 기록 조회                     |
| `get_weekly_timeline`        | 모든 활동을 시간순으로 통합한 타임라인                |
| `get_enriched_weekly_report` | few-shot 예시와 포맷 가이드를 포함한 풀 리포트 데이터 |
| `get_weekly_insights`        | 패턴 분석 및 개선 제안                                |

## 빠른 시작

### 사전 요구사항

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (권장) 또는 pip
- [GitHub Personal Access Token](https://github.com/settings/tokens) (`repo`, `read:user` 권한)

### 1. uvx로 설치 (권장)

```bash
uvx --from git+https://github.com/JaehaSS/mcp-devdiary.git mcp-devdiary
```

### 2. 또는 직접 클론하여 설치

```bash
git clone https://github.com/JaehaSS/mcp-devdiary.git
cd mcp-devdiary
uv sync
```

### 3. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열고 GitHub 토큰을 입력하세요:

```
GITHUB_TOKEN=ghp_여기에_토큰_입력
GITHUB_USERNAME=깃허브_사용자명
```

### 4. 서버 실행

```bash
uv run mcp-devdiary
```

## MCP 클라이언트 연동

### Claude Desktop

Claude Desktop 설정 파일에 다음을 추가하세요:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mcp-devdiary": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/JaehaSS/mcp-devdiary.git", "mcp-devdiary"],
      "env": {
        "GITHUB_TOKEN": "ghp_여기에_토큰_입력",
        "GITHUB_USERNAME": "사용자명"
      }
    }
  }
}
```

### Claude Code

Claude Code MCP 설정 (`.claude/settings.json` 또는 프로젝트 레벨)에 추가:

```json
{
  "mcpServers": {
    "mcp-devdiary": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/JaehaSS/mcp-devdiary.git", "mcp-devdiary"],
      "env": {
        "GITHUB_TOKEN": "ghp_여기에_토큰_입력",
        "GITHUB_USERNAME": "사용자명"
      }
    }
  }
}
```

## 사용 예시

연결 후 Claude에게 이렇게 물어보세요:

- **"이번 주 업무 정리해줘"** — `get_enriched_weekly_report`로 구조화된 주간 요약 생성
- **"지난주에 뭐 했지?"** — `get_weekly_activity`를 `week_offset=-1`로 호출
- **"최근 한 달 이력서 성과 문장 만들어줘"** — `get_activity_for_resume`를 `weeks_range=4`로 호출
- **"내 코딩 패턴 분석해줘"** — `get_weekly_insights`로 활동 패턴 분석
- **"이번 주 타임라인 보여줘"** — `get_weekly_timeline`으로 시간순 조회

## 데이터 소스

| 소스            | 수집 내용                               | 방법                                |
| --------------- | --------------------------------------- | ----------------------------------- |
| **GitHub**      | 커밋, Pull Request                      | GitHub REST API (PyGitHub)          |
| **Claude Code** | 세션 기록 (프롬프트, 메시지, 도구 사용) | 로컬 `~/.claude/projects/` 디렉토리 |
| **Codex**       | CLI 상호작용 기록                       | 로컬 `~/.codex/history.jsonl` 파일  |

> [!IMPORTANT]
> 모든 데이터는 로컬에 유지됩니다. 이 서버는 로컬 머신과 GitHub API에서만 데이터를 읽습니다.
> 어떤 제3자 서비스에도 데이터를 전송하지 않습니다.

## 환경변수

| 변수                   | 필수 | 설명                                                 |
| ---------------------- | ---- | ---------------------------------------------------- |
| `GITHUB_TOKEN`         | O    | GitHub Personal Access Token                         |
| `GITHUB_USERNAME`      | X    | 기본 GitHub 사용자명                                 |
| `CLAUDE_SESSIONS_PATH` | X    | Claude Code 세션 경로 (기본: `~/.claude/projects/`)  |
| `CODEX_HISTORY_PATH`   | X    | Codex 히스토리 경로 (기본: `~/.codex/history.jsonl`) |
| `REPORTS_DIR`          | X    | 주간 리포트 출력 디렉토리 (기본: `reports/weekly`)   |

## 프로젝트 구조

```
mcp-devdiary/
├── src/work_journal/
│   ├── server.py          # MCP 서버 및 도구 핸들러
│   ├── github.py          # GitHub API 연동
│   ├── session_parser.py  # Claude Code 세션 파서
│   ├── codex_parser.py    # Codex 히스토리 파서
│   ├── timeline.py        # 통합 타임라인 빌더
│   ├── insights.py        # 패턴 분석 및 인사이트
│   ├── few_shot.py        # Few-shot 예시 로더
│   ├── formatter.py       # 마크다운 출력 포매터
│   └── config.py          # 설정 관리
├── tests/                 # 테스트 (109개)
├── reports/               # 생성된 주간 리포트
├── pyproject.toml
└── .env.example
```

## 개발

```bash
# 개발 의존성 설치
uv sync --group dev

# 테스트 실행
uv run pytest

# 상세 출력으로 테스트
uv run pytest -v
```

## 기술 스택

- **[FastMCP](https://github.com/jlowin/fastmcp)** — MCP 서버 프레임워크
- **[PyGitHub](https://pygithub.readthedocs.io/)** — GitHub API 클라이언트
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** — 환경변수 관리
