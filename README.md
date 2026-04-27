# News AI Agent (自動化科技日報)

這是一個基於 Google Gemini 2.5 Flash 模型驅動的自動化 AI 科技日報系統。代理人 (Agent) 擁有「Anthropic 首席工程師」與「NVIDIA/Apple 資深架構師」的雙核心視角，旨在以第一原理深度分析每日最新的科技與半導體新聞。

## 系統架構

- **新聞擷取 (NewsFetcher)**：透過 RSS 抓取 L1 (硬體/半導體)、L2 (AI 軟體/模型)、L3 (科技生態/商業) 三大領域的新聞，並限制每家來源最多擷取 3 篇。
- **推論核心 (AgentBrain)**：將擷取到的新聞摘要交由 Gemini 2.5 Flash 處理，並以架構師的口吻產生深度分析長文與重點掃描。
- **推播機制 (DiscordNotifier)**：將生成的日報拆分成符合 Discord 字數限制的區塊，推播至指定的 Discord 頻道。
- **自動化 (GitHub Actions)**：每天早上 08:00 (UTC+8) 自動執行上述流程，完全無需人工介入。

## 本地端測試與開發

若您希望在本地端執行此程式：

1. **安裝依賴套件**：
   ```bash
   pip install -r requirements.txt
   ```

2. **設定環境變數**：
   在專案根目錄下建立 `.env` 檔案，並填寫以下資訊：
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
   ```
   *(注意：`.env` 檔案已加入 `.gitignore`，請勿將金鑰 Push 到 GitHub 上。)*

3. **執行程式**：
   ```bash
   python news_agent.py
   ```

## 部署至 GitHub Actions

本專案已配置好 GitHub Actions (`.github/workflows/daily_news.yml`)。要讓自動化流程順利運作，請確保在您的 GitHub Private Repository 中設定了以下 **Repository Secrets**：

1. 前往 Repo 的 `Settings` > `Secrets and variables` > `Actions`。
2. 點擊 `New repository secret`，分別加入：
   - `GEMINI_API_KEY`：您的 Gemini API 金鑰。
   - `DISCORD_WEBHOOK_URL`：您用來接收日報的 Discord Webhook 網址。

設定完成後，您可以至 **Actions** 分頁中手動觸發 (Run workflow)，或等待系統在每日定時自動為您送上最新的科技日報。
