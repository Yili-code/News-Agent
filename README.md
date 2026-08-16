# News Agent

一個新聞聚合與 Q&A 系統，提供科技資訊聚合、日報生成、以及 Discord 互動功能。

## 功能概覽

### 1. **新聞聚合與每日簡報** (`news_agent.py`)
- 自動從 6 個高質量 RSS 源聚合新聞
- 生成每日新聞簡報
- 去重機制，避免重複報導相同主題
- 通過 Telegram Bot 推送每日簡報
- 保留新聞歷史記錄，自動保存最近 10 次簡報

### 2. **Discord 互動** (`qa_agent.py`)
- 監控 Discord 頻道中提及「阿福」的提問
- 生成回答並推送到頻道
- 過濾已回答的問題，避免重複回應
- 支持 24 小時時間窗口內的消息檢索

### 3. **API 連接測試** (`test_key.py`)
- 測試 API 連接
- 驗證設定的有效性

## 新聞來源

系統聚合以下 6 個科技新聞源：

| 分類 | 來源 |
|-----|------|
| 科技產業 | SemiAnalysis |
| 科技新聞 | The Information |
| 科技創新 | TechCrunch |
| 商業科技 | VentureBeat |
| 技術深度 | ArsTechnica |
| 科技前沿 | MIT Technology Review |

## 安裝步驟

### 前置需求
- Python 3.8+
- API 密鑰（用於內容生成）
- Telegram Bot Token 與 Chat ID（可選，用於推送功能）
- Discord Bot Token 與 Channel ID（可選，用於互動功能）

### 1. 克隆或下載項目
```bash
cd news_agent
```

### 2. 安裝依賴
```bash
pip install -r requirements.txt
```

### 3. 配置環境變數

在項目根目錄創建 `.env` 文件：

```env
GEMINI_API_KEY=your_api_key_here
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here
```

### 4. 測試連接（可選）
```bash
python test_key.py
```

## 使用方法

### 生成每日簡報
```bash
python news_agent.py
```

該命令將：
1. 從所有 RSS 源聚合最新新聞（每個源最多 3 條）
2. 生成簡報
3. 通過 Telegram 推送
4. 保存摘要到歷史記錄

### 監控 Discord
```bash
python qa_agent.py
```

該命令將：
1. 獲取 Discord 頻道最近 24 小時內的消息
2. 識別提及「阿福」的提問
3. 生成回答
4. 推送回答到 Discord

### 推薦的定時執行

使用系統的任務排程工具（如 cron 或 Windows Task Scheduler）定時執行：

**Windows (Task Scheduler):**
```
Program: python.exe
Arguments: C:\path\to\news_agent.py
Schedule: Daily at 08:00 AM
```

**Linux/macOS (cron):**
```bash
0 8 * * * cd /path/to/news_agent && python news_agent.py
0 */2 * * * cd /path/to/news_agent && python qa_agent.py
```

## 📄 文件結構

```
news_agent/
├── news_agent.py          # 新聞聚合與簡報
├── qa_agent.py            # Discord 互動
├── test_key.py            # 連接測試
├── news_history.json      # 簡報歷史記錄（自動生成）
├── requirements.txt       # Python 依賴
└── README.md             # 本文件
```

## 🔧 配置說明

### news_agent.py 配置

- **`limit_per_source`**：每個 RSS 源每次獲取的新聞數量，默認為 3
- **歷史記錄**：自動保留最近 10 次簡報摘要
- **Telegram 推送**：支持 HTML 格式，如解析失敗則自動降級為純文字

### qa_agent.py 配置

- **`max_hours_back`**：查詢消息的時間窗口，默認為 24 小時
- **過濾重複**：排除已回答的問題
- **新聞過濾**：排除每日新聞簡報

## 🔐 安全建議

- **環境變數管理**：API 密鑰等敏感信息應存儲在 `.env` 文件中，避免在代碼中硬編碼
- **`.env` 文件保護**：將 `.env` 添加到 `.gitignore`，避免提交到版本控制系統
- **密鑰輪換**：定期更新 API 密鑰和 Bot Token

## 🐛 故障排除

### Telegram 推送失敗
- 確認 `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHAT_ID` 正確
- 檢查 Bot 是否已添加到目標頻道並擁有發送消息權限

### Discord 消息讀取失敗
- 確認 `DISCORD_BOT_TOKEN` 和 `DISCORD_CHANNEL_ID` 正確
- 確保 Bot 在 Discord 伺服器中擁有讀取和發送消息的權限

### API 連接失敗
- 確認 API 密鑰有效
- 檢查網絡連接

### 中文顯示亂碼
- 確保終端編碼為 UTF-8（尤其是 Windows PowerShell）
- 檢查 Telegram/Discord 客戶端的字體設置

## 📦 依賴說明

| 套件 | 版本 | 用途 |
|------|------|------|
| google-generativeai | 0.8.3 | API 調用 |
| requests | 2.32.3 | HTTP 請求（Telegram/Discord API） |
| feedparser | 6.0.11 | RSS 源解析 |
| python-dotenv | 1.0.1 | 環境變數管理 |

## 📝 日誌

程式使用 Python logging 記錄執行情況：

- **INFO**：正常操作流程
- **WARNING**：非關鍵問題
- **ERROR**：關鍵錯誤

日誌格式：`[時間戳] - [日誌等級] - [消息內容]`

## 📄 許可證

本項目采用 MIT 許可證。

---

**最後更新**：2026-08-16
