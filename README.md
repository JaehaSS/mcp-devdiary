# mcp-devdiary

**An MCP server that automatically collects your GitHub activity and AI agent sessions to generate structured weekly work logs.**

[한국어 문서 (Korean)](./README_KO.md)

---

- Automatically collects commits, PRs, Claude Code sessions, and Codex entries
- Generates weekly reports, timelines, and insights from your development activity
- Produces resume-ready bullet points from accumulated work data
- Free and open-source, runs locally on your machine

> You can think of mcp-devdiary as a personal engineering diary that writes itself.
> It connects to your GitHub and local AI agent history, then serves structured data via MCP
> so that Claude can summarize your week, spot patterns, and draft resume bullets for you.

## MCP Tools

mcp-devdiary exposes 7 tools through the [Model Context Protocol](https://modelcontextprotocol.io/):

| Tool                         | Description                                               |
| ---------------------------- | --------------------------------------------------------- |
| `get_commits`                | Fetch weekly GitHub commits with statistics               |
| `get_weekly_activity`        | Combined weekly activity (commits + PRs + agent sessions) |
| `get_activity_for_resume`    | Multi-week activity data for resume bullet generation     |
| `get_agent_sessions`         | Claude Code and Codex session history                     |
| `get_weekly_timeline`        | Unified chronological timeline of all activity            |
| `get_enriched_weekly_report` | Full report data with few-shot examples and format guide  |
| `get_weekly_insights`        | Pattern analysis with actionable suggestions              |

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A [GitHub Personal Access Token](https://github.com/settings/tokens) with `repo` and `read:user` scopes

### 1. Install via uvx (Recommended)

```bash
uvx --from git+https://github.com/JaehaSS/mcp-devdiary.git mcp-devdiary
```

### 2. Or clone and install manually

```bash
git clone https://github.com/JaehaSS/mcp-devdiary.git
cd mcp-devdiary
uv sync
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your GitHub token:

```
GITHUB_TOKEN=ghp_your_token_here
GITHUB_USERNAME=your-github-username
```

### 4. Run the server

```bash
uv run mcp-devdiary
```

## Integration with MCP Clients

### Claude Desktop

Add the following to your Claude Desktop configuration file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mcp-devdiary": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/JaehaSS/mcp-devdiary.git", "mcp-devdiary"],
      "env": {
        "GITHUB_TOKEN": "ghp_your_token_here",
        "GITHUB_USERNAME": "your-username"
      }
    }
  }
}
```

### Claude Code

Add to your Claude Code MCP settings (`.claude/settings.json` or project-level):

```json
{
  "mcpServers": {
    "mcp-devdiary": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/JaehaSS/mcp-devdiary.git", "mcp-devdiary"],
      "env": {
        "GITHUB_TOKEN": "ghp_your_token_here",
        "GITHUB_USERNAME": "your-username"
      }
    }
  }
}
```

## Usage Examples

Once connected, you can ask Claude:

- **"Summarize my work this week"** — Uses `get_enriched_weekly_report` to generate a structured weekly summary
- **"What did I do last week?"** — Uses `get_weekly_activity` with `week_offset=-1`
- **"Generate resume bullets for the past month"** — Uses `get_activity_for_resume` with `weeks_range=4`
- **"Show me my coding patterns"** — Uses `get_weekly_insights` to analyze activity patterns
- **"Show my timeline for this week"** — Uses `get_weekly_timeline` for a chronological view

## Data Sources

| Source          | What's collected                                | How                                   |
| --------------- | ----------------------------------------------- | ------------------------------------- |
| **GitHub**      | Commits, Pull Requests                          | GitHub REST API via PyGitHub          |
| **Claude Code** | Session history (prompts, messages, tool usage) | Local `~/.claude/projects/` directory |
| **Codex**       | CLI interaction history                         | Local `~/.codex/history.jsonl` file   |

> [!IMPORTANT]
> All data stays local. This server reads from your local machine and GitHub API only.
> No data is sent to any third-party service.

## Environment Variables

| Variable               | Required | Description                                                       |
| ---------------------- | -------- | ----------------------------------------------------------------- |
| `GITHUB_TOKEN`         | Yes      | GitHub Personal Access Token                                      |
| `GITHUB_USERNAME`      | No       | Default GitHub username                                           |
| `CLAUDE_SESSIONS_PATH` | No       | Custom Claude Code sessions path (default: `~/.claude/projects/`) |
| `CODEX_HISTORY_PATH`   | No       | Custom Codex history path (default: `~/.codex/history.jsonl`)     |
| `REPORTS_DIR`          | No       | Weekly report output directory (default: `reports/weekly`)        |

## Project Structure

```
mcp-devdiary/
├── src/work_journal/
│   ├── server.py          # MCP server & tool handlers
│   ├── github.py          # GitHub API integration
│   ├── session_parser.py  # Claude Code session parser
│   ├── codex_parser.py    # Codex history parser
│   ├── timeline.py        # Unified timeline builder
│   ├── insights.py        # Pattern analysis & insights
│   ├── few_shot.py        # Few-shot example loader
│   ├── formatter.py       # Markdown output formatter
│   └── config.py          # Configuration management
├── tests/                 # Test suite (109 tests)
├── reports/               # Generated weekly reports
├── pyproject.toml
└── .env.example
```

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run tests with verbose output
uv run pytest -v
```

## Tech Stack

- **[FastMCP](https://github.com/jlowin/fastmcp)** — MCP server framework
- **[PyGitHub](https://pygithub.readthedocs.io/)** — GitHub API client
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** — Environment variable management
