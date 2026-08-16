# News Agent

一個新聞聚合與每日科技簡報系統，現在專注於 Telegram 推送。

## 功能概覽

- 自動從 6 個科技新聞來源聚合新聞
- 依據歷史內容去重，避免重複主題
- 使用 Gemini 生成每日技術簡報
- 以 Telegram HTML 格式發送到指定聊天
- 保存最近 10 次簡報摘要到 `news_history.json`
- GitHub Actions 可定時執行

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

## 前置需求

- Python 3.8+
- Gemini API Key
- Telegram Bot Token
- Telegram Chat ID

## 安裝步驟

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 配置環境變數

在專案根目錄建立 `.env`：

```env
GEMINI_API_KEY=your_api_key_here
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 3. 執行

```bash
python news_agent.py
```

該命令會：
1. 抓取最新 RSS 新聞
2. 過濾與歷史相近內容
3. 生成每日科技簡報
4. 發送到 Telegram
5. 儲存摘要到歷史紀錄

## GitHub Actions

專案已經配置每日自動執行工作流，位置在：

- `.github/workflows/daily_news.yml`

它會在每日固定時間觸發，並將最新的 `news_history.json` 提交回儲存庫。

## 文件結構

```text
news_agent/
├── news_agent.py          # 新聞聚合與 Telegram 推送
├── news_history.json      # 簡報歷史記錄（自動生成）
├── requirements.txt       # Python 依賴
├── README.md              # 專案說明
├── .env                   # 本地環境變數（不要提交）
└── .github/
    └── workflows/
        └── daily_news.yml # 定時任務
```

## 配置說明

### `news_agent.py`

- `limit_per_source`：每個 RSS 源每次拉取的新聞數量，預設為 3
- `news_history.json`：保留最近 10 次摘要，做去重判斷
- Telegram 推送：支援 HTML 格式；若格式化失敗，會自動降級為純文字

## 安全建議

- 將 `.env` 保存在本地，不要上傳到版本控制
- 定期更新 Gemini API Key 和 Telegram Bot Token
- 不要在程式碼中直接寫死敏感資訊

## 故障排除

### Telegram 發送失敗

- 確認 `TELEGRAM_BOT_TOKEN` 與 `TELEGRAM_CHAT_ID` 正確
- 確認 Bot 已加入目標群組或聊天，且有發送訊息權限

### API 連線失敗

- 確認 `GEMINI_API_KEY` 有效
- 檢查網路連線是否正常

### 中文顯示問題

- 使用 UTF-8 編碼環境
- 確認 Telegram 客戶端支援顯示 HTML 內容

## 依賴套件

| 套件 | 版本 | 用途 |
|------|------|------|
| google-generativeai | 0.8.3 | Gemini API 調用 |
| requests | 2.32.3 | HTTP 請求 |
| feedparser | 6.0.11 | RSS 解析 |
| python-dotenv | 1.0.1 | 環境變數管理 |

## 日誌

程式透過 Python Logging 記錄執行情況：

- INFO：正常流程
- WARNING：非關鍵警告
- ERROR：關鍵錯誤

---

最後更新：2026-08-16
