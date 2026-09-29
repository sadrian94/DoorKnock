# DoorKnock System Prerequisites and Supporting Services

Traditional Chinese original: [prerequisites-ZH.md](prerequisites-ZH.md)

This document describes the runtime requirements, core dependencies, and Model Context Protocol (MCP) server configuration for DoorKnock.

---

## 1. Core runtime

| Component | Required version / specification | Purpose |
| :--- | :--- | :--- |
| **Python** | 3.12+ (managed with `uv`) | Backend FastAPI application, AI tailoring engine, and CLI tools. |
| **Go** | 1.22+ (`go version`) | Runs the official native Go implementation of `github-mcp-server`. |
| **Node.js** | 20+ (npm) | Frontend Vite, React, and TypeScript application. |
| **Typst** | `typst==0.15.0` (Python binding) | Core document-layout compiler for the Tailor workflow, with sub-millisecond PDF compilation. |
| **LinkedIn MCP runtime** | `uvx` (Patchright Chromium) | Runs `mcp-server-linkedin` natively and shares the local signed-in browser profile. |
| **Gemini API** | `GEMINI_API_KEY` in `.env` | Model service for in-depth job-description analysis and strategy for resumes and cover letters. |

---

## 2. Optional Sepia agent skill

DoorKnock does not bundle or copy the third-party Sepia skills. If you want Sepia-assisted writing workflows, install the complete package from the [upstream Sepia repository](https://github.com/Nanako0129/sepia) and follow its current installation and license instructions. The upstream project is MIT licensed ([license](https://github.com/Nanako0129/sepia/blob/main/LICENSE)).

For Codex CLI, the upstream currently documents:

~~~sh
codex plugin marketplace add Nanako0129/sepia
codex plugin add sepia@sepia
~~~

For agents supported by the Skills CLI, the upstream also documents:

~~~sh
npx skills add Nanako0129/sepia -g
~~~

Install the complete package rather than an individual wrapper; the operation-specific entries depend on the canonical Sepia skill. Check the upstream README for updates and instructions for other agents.

---

## 3. LinkedIn MCP server (`linkedin-mcp-server`)

> **Repository:** [stickerdaniel/linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server)
>
> **Configuration path:** `~/.gemini/config/mcp_config.json` (also supports `.vscode/mcp.json`)

### 3.1 Server configuration (recommended native `uvx` mode)

~~~json
"linkedin-mcp-server": {
  "command": "uvx",
  "args": [
    "mcp-server-linkedin@latest"
  ],
  "env": {
    "UV_HTTP_TIMEOUT": "300",
    "PYTHONIOENCODING": "utf-8"
  }
}
~~~

### 3.2 Roles and capabilities

- **People and decision-maker research:** 19 dedicated tools, including `search_people`, `get_person_profile`, `get_company_profile`, `get_company_employees`, and `get_company_posts`.
- **Finding authentic conversation hooks:** Extract current technical challenges from recent posts by managers or peers to inform a relevant cold outreach opening.

### 3.3 Runtime requirements and precautions

1. **Benefits of native `uvx` execution:**
   - Compared with Docker, native `uvx` shares the host user's persistent profile at `~/.linkedin-mcp/profile`. This reduces container startup overhead and the risk of Docker stalls on Windows.
   - On first use, it downloads Patchright Chromium in the background to `~/.linkedin-mcp/patchright-browsers`.
2. **Check authentication and sign in:**
   - Check the sign-in status:

     ~~~powershell
     $env:PYTHONIOENCODING="utf-8"; uvx mcp-server-linkedin@latest --status
     ~~~

   - If you are not signed in or your cookies have expired, start an interactive browser sign-in:

     ~~~powershell
     uvx mcp-server-linkedin@latest --login
     ~~~

   - You can also import an existing session from your everyday browser:

     ~~~powershell
     uvx mcp-server-linkedin@latest --import-from-browser auto
     ~~~
3. **Fail-closed safety rule:**
   - Never send a message or connection request without confirmation. Generate a draft first and require the user to approve it.

---

## 4. GitHub MCP server (`github-mcp-server`)

> **Official source:** [github/github-mcp-server](https://github.com/github/github-mcp-server), the official Go-based GitHub MCP server
>
> **Configuration path:** `~/.gemini/config/mcp_config.json` (also supports `.vscode/mcp.json`)

### 4.1 Server configuration (native Go binary)

~~~json
"github-mcp-server": {
  "command": "github-mcp-server",
  "args": [
    "stdio"
  ],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "<YOUR_GITHUB_PERSONAL_ACCESS_TOKEN>"
  }
}
~~~

### 4.2 Roles and capabilities

- **Project evidence review:** Inspect public code repositories to substantiate project claims when preparing resumes and cover letters.
- **Commit and file search, plus security scanning:** The server includes 82 tools across modules such as `repos`, `issues`, `pull_requests`, `actions`, and `code_security`.

### 4.3 Installation and token requirements

- **Install the binary:** Download a Windows x86_64 binary from GitHub Releases or use `go install`:

  ~~~powershell
  go install github.com/github/github-mcp-server/cmd/github-mcp-server@latest
  ~~~

- **Obtain a token and grant permissions:**
  - If GitHub CLI (`gh`) is installed, you can retrieve its existing authorization with `gh auth token`.
  - For a manually created personal access token (PAT), grant at least `repo`, `workflow`, `read:org`, and `gist` permissions.
- **Verify the token scopes:**

  ~~~powershell
  github-mcp-server list-scopes
  ~~~

---

## 5. Candidate single source of truth

DoorKnock follows a strict anti-hallucination rule: generated documents must be grounded entirely in local evidence.

1. **`workspace/master_resume/master_evidence.yaml`:**
   - The candidate's evidence record, including verified experience, projects, education, skills, and supporting claims.
2. **`workspace/profile.yaml`:**
   - Candidate-specific identity, contact, and other profile fields supplied by the user.

---

## 6. Prerequisites checklist

Before running the full DoorKnock workflow, use these commands to check the application and MCP services:

~~~powershell
# 1. Verify the backend and Typst compilation environment
uv run pytest tests

# 2. Build the frontend
cd frontend && npm run build

# 3. Check LinkedIn MCP server status and session
$env:PYTHONIOENCODING="utf-8"; uvx mcp-server-linkedin@latest --status

# 4. Check the GitHub MCP server and token scopes (82 tools)
github-mcp-server list-scopes
~~~
