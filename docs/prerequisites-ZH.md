# DoorKnock 系統前置需求與相依服務 (Prerequisites & Infrastructure)

本文檔記錄 DoorKnock 系統運作之前置需求、核心相依工具與 Model Context Protocol (MCP) 伺服器配置。

---

## 1. 核心運行環境 (Core Runtime)

| 組件 | 需求版本 / 規範 | 說明 |
| :--- | :--- | :--- |
| **Python** | 3.12+ (使用 `uv` 管理) | 後端 FastAPI、AI Tailor 引擎與 CLI 工具環境。 |
| **Go** | 1.22+ (`go version`) | 執行官方原生 Go 版 `github-mcp-server`。 |
| **Node.js** | 20+ (npm) | 前端 Vite + React + TypeScript 應用。 |
| **Typst** | `typst==0.15.0` (Python 綁定) | 鑄磚 (Frictionless Proof) 核心排版編譯引擎，支援次毫秒級 PDF 編譯。 |
| **LinkedIn MCP Runtime** | `uvx` (Patchright Chromium) | 原生執行 `mcp-server-linkedin`，共用本機已登入之 Profile。 |
| **Gemini API** | `GEMINI_API_KEY` (.env) | 驅動履歷與求職信深度 JD 分析與戰略調配之模型服務。 |

---

## 2. Optional Sepia Agent Skill

DoorKnock does not bundle or copy the third-party Sepia skills. If you want Sepia-assisted writing workflows, install the complete package from the [upstream Sepia repository](https://github.com/Nanako0129/sepia) and follow its current installation and license instructions. The upstream project is MIT licensed ([license](https://github.com/Nanako0129/sepia/blob/main/LICENSE)).

For Codex CLI, the upstream currently documents:

```sh
codex plugin marketplace add Nanako0129/sepia
codex plugin add sepia@sepia
```

For agents supported by the Skills CLI, the upstream also documents:

```sh
npx skills add Nanako0129/sepia -g
```

Install the complete package rather than an individual wrapper; the operation-specific entries depend on the canonical Sepia skill. Check the upstream README for updates and instructions for other agents.

---

## 3. LinkedIn MCP 伺服器 (`linkedin-mcp-server`)

> **倉庫來源**：[stickerdaniel/linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server)
>
> **配置位置**：`~/.gemini/config/mcp_config.json`（亦支援 `.vscode/mcp.json`）

### 3.1 伺服器配置（原生 uvx 推薦模式）
```json
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
```

### 3.2 角色與功能 (辨門 & 叩門)
- **人脈與決策者偵察**：`search_people`, `get_person_profile`, `get_company_profile`, `get_company_employees`, `get_company_posts` 等 19 個專用工具。
- **真實掛鉤提取**：從主管或同儕近期貼文提取真實技術挑戰，作為冷接觸 (Cold Outreach) 的破冰依據。

### 3.3 運行前置要件與注意事項
1. **原生 uvx 執行優勢**：
   - 相比 Docker 容器模式，原生 `uvx` 直接共用宿主機使用者的持久化 Profile（`~/.linkedin-mcp/profile`），大幅降低容器啟動開銷與 Windows 容器卡滯風險。
   - 第一次執行會自動在背景下載 Patchright Chromium（安裝於 `~/.linkedin-mcp/patchright-browsers`）。
2. **認證狀態檢查與登入**：
   - 檢查登入狀態：
     ```powershell
     $env:PYTHONIOENCODING="utf-8"; uvx mcp-server-linkedin@latest --status
     ```
   - 若尚未登入或 Cookie 失效，可開啟瀏覽器進行互動登入：
     ```powershell
     uvx mcp-server-linkedin@latest --login
     ```
   - 亦可直接從日常瀏覽器匯入現有 Session：
     ```powershell
     uvx mcp-server-linkedin@latest --import-from-browser auto
     ```
3. **安全防線 (Fail-Closed)**：
   - 嚴禁自動發送未經確認的訊息或好友申請；所有訊息必須先生成草稿經使用者確認。

---

## 4. GitHub MCP 伺服器 (`github-mcp-server`)

> **官方來源**：[github/github-mcp-server](https://github.com/github/github-mcp-server) (Official GitHub Go-based MCP Server)
>
> **配置位置**：`~/.gemini/config/mcp_config.json`（亦支援 `.vscode/mcp.json`）

### 4.1 伺服器配置（原生 Go 二進位檔）
```json
"github-mcp-server": {
  "command": "github-mcp-server",
  "args": [
    "stdio"
  ],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "<YOUR_GITHUB_PERSONAL_ACCESS_TOKEN>"
  }
}
```

### 4.2 角色與功能
- **專案佐證檢驗**：檢視公開程式碼庫，以佐證履歷或求職信中的專案主張。
- **真實 Commit、檔案檢索與安全性掃描**：內建 82 項工具，支援 `repos`、`issues`、`pull_requests`、`actions`、`code_security` 等完整模組。

### 4.3 前置需求維護
- **二進位檔安裝**：可直接由 GitHub Release 下載 Windows x86_64 二進位檔或使用 `go install`：
  ```powershell
  go install github.com/github/github-mcp-server/cmd/github-mcp-server@latest
  ```
- **Token 取得與權限要求**：
  - 若已安裝 GitHub CLI (`gh`)，可直接透過 `gh auth token` 取得現有授權。
  - 手動產生 PAT 時，需至少勾選 `repo`, `workflow`, `read:org`, `gist` 權限。
- **Token 驗證指令**：
  ```powershell
  github-mcp-server list-scopes
  ```

---

## 5. 候選人單一事實來源 (Strict Truth Anchor)

DoorKnock 嚴格貫徹「零捏造 (Anti-Hallucination)」準則，所有文書生成必須百分之百錨定於本地事實：

1. **`workspace/master_resume/master_evidence.yaml`**：
   - 候選人的證據紀錄，包含已核實的經歷、專案、教育、技能及相關主張。
2. **`workspace/profile.yaml`**：
   - 由使用者提供、只供本機使用的候選人身份、聯絡資料及其他個人檔案欄位。

---

## 6. 前置檢核清單 (Prerequisites Checklist)

在執行 DoorKnock 完整流程前，可執行以下指令確認系統與 MCP 就緒狀態：

```powershell
# 1. 驗證後端與 Typst 編譯環境
uv run pytest tests

# 2. 驗證前端建構
cd frontend && npm run build

# 3. 檢查 LinkedIn MCP 伺服器狀態與 Session
$env:PYTHONIOENCODING="utf-8"; uvx mcp-server-linkedin@latest --status

# 4. 檢查 GitHub MCP 伺服器與授權範圍 (82 項工具)
github-mcp-server list-scopes

```
