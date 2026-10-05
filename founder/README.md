# 拾題 · Founder Morning

YiLi 的個人創業研究工具。每日 15 分鐘，週日 30 分鐘：公開來源 → 偏好篩選 → 中文拆解 → 私人網站與 Telegram。Production runtime 使用 Google Cloud Run、Firestore、Vertex AI 與 Secret Manager，和 News Agent 的憑證、資料及排程分開。

## 已實作

- HN Ask/Show、Product Hunt Atom、DEV 公開 API；單一來源失敗可降級。
- 近七天候選、已讀期別去重、明確偏好排序、保留陌生主題。
- 中文分析區分來源描述、推論、收費假設、未知、反證與具體行動；AI 格式或引用 ID 不合格時只顯示原文。
- 私人登入、30 天 HttpOnly session、登出撤銷、登入限流、跨站寫入阻擋。
- SQLite 本機預覽、Firestore production persistence、Telegram delivery claim，避免可確認的重複發送。
- GitHub Actions 預備、發送、補跑；未設定 `FOUNDER_ENABLED=true` 時不執行。

## 本機體驗

需要 Python 3.12+。在 repository 根目錄執行：

```powershell
python -m pip install -r founder/requirements.txt
python founder/pipeline.py --local-output founder/.local/issue.json
python founder/app.py
```

開啟 <http://127.0.0.1:8787>，本機登入碼是 `morning-local`。可用 `APP_KEY` 覆寫。本機資料存在已忽略的 `founder/.local/state.sqlite3`，不連接 Firestore，也不會自行發送 Telegram。沒有 production identity 時，來源預覽仍可使用，但 AI 分析保持未完成。

## Google Cloud architecture

```text
GitHub Actions pipeline
        ↓ job token
Cloud Run service ── Vertex AI / Gemini
        ↓
named Firestore database: founder-morning
        ↓
private web session + Telegram delivery
```

Cloud Run 對外公開的是登入外殼與 HTTP endpoints；研究內容仍受 application session 保護。Runtime service account 只需要 Firestore、Vertex AI 與指定 Secret Manager secrets 的權限。

## 一次性 Google Cloud 設定

以下範例使用既有 project `yili-chronos-prod`、region `asia-east1`，並用獨立 named database 與 service name 隔離 Founder Morning：

```text
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com secretmanager.googleapis.com aiplatform.googleapis.com
gcloud firestore databases create --database=founder-morning --location=asia-east1 --type=firestore-native --delete-protection
gcloud run deploy founder-morning --source founder --region asia-east1 --allow-unauthenticated
```

Production 需要四個 Secret Manager values：

| Secret | 用途 |
|---|---|
| `founder-app-key` | 私人網站登入碼 |
| `founder-job-token` | GitHub Actions 呼叫 internal endpoints |
| `founder-telegram-bot-token` | 專用 Telegram bot token |
| `founder-telegram-chat-id` | YiLi 的 private chat ID |

Cloud Run variables：

| Variable | Value |
|---|---|
| `GOOGLE_CLOUD_PROJECT` | `yili-chronos-prod` |
| `FIRESTORE_DATABASE` | `founder-morning` |
| `VERTEX_LOCATION` | `global` |
| `AI_MODEL` | `gemini-2.5-flash` |
| `SITE_URL` | deployed Cloud Run HTTPS URL |

不要把 secret values 放進 repository、Docker image、deploy command history 或 GitHub variables。若要撤銷所有網站 sessions，刪除 named Firestore database 內的 `sessions` collection documents。

## GitHub Actions 啟用

設定：

| 類型 | 名稱 | 值 |
|---|---|---|
| Repository variable | `FOUNDER_URL` | Cloud Run HTTPS URL |
| Repository secret | `FOUNDER_JOB_TOKEN` | 與 `founder-job-token` 相同 |
| Repository variable | `FOUNDER_ENABLED` | `true` 才啟用 |

在 Actions → Founder Morning 手動執行一次，會準備日報並嘗試傳送 Telegram。確認 chat ID 指向自己後再啟用。排程為台灣 05:37 準備、06:07 發送、06:37 補跑；GitHub 可能延遲。

## 驗證

```text
python -m pytest -p no:cacheprovider -q
python founder/pipeline.py --local-output founder/.local/issue.json
```

自動驗證涵蓋未授權存取、session 撤銷、登入限流、來源去重、引用 ID 驗證、跨站寫入、feedback persistence、Telegram readability 與 delivery claim。正式上線仍需分別驗證 Cloud Run `/api/health`、Firestore write/read、Vertex AI output、Telegram delivery，以及七天排程紀錄。

## 邊界

- 初期來源偏科技族群。週報按主題聚合，不代表不同產品已證明同一個需求。
- AI 引用 ID 驗證只確認引用存在，不能保證每句推論成立；必須讀原文。
- 應用每天最多六次 AI 分析呼叫；Vertex AI 仍受 project quota 與計費設定限制。
- Telegram `unknown` 或停留在 `sending` 代表可能已送達，先確認對話再人工處理 delivery document；外部服務無法保證 exactly-once。
- 網站與 API 是單人私人使用。job token 可管理研究資料，務必保密。
- 尚無自動資料清理；以個人三個月試用為初版範圍，長期運行前檢查 Firestore usage 與費用。
