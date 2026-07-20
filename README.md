# News AI Agent (電機系專屬自動化科技日報) 🚀

這是一個基於 Google Gemini 2.5 Flash 模型驅動的自動化 AI 科技日報系統。
目前的 Agent 定位已經全面升級為**「專為電機系 (EE) 學生打造的科技日報」**，旨在每天為您提供最具啟發性、最有幫助的技術突破與產業新聞。

## 🎯 專案定位與核心邏輯

本系統的核心設計理念是「對電機系學生到底有沒有幫助」：
1. **每日必報 (Unconditional Reporting)**：無論當天的新聞多寡或影響力大小，系統每天都會雷打不動地為您挑選出「最好的一篇」進行播報，確保您每天都有新知可以吸收。
2. **專屬挑選邏輯**：AI 在篩選新聞時，會自動過濾掉公關行銷廢話，聚焦於技術細節、晶片架構突破、模型底層設計或實務應用。
3. **純中文易讀排版**：嚴格限制輸出在 400 字以內，並採用純中文敘述（不會出現 `中文 (English)` 的冗餘括號），提升閱讀流暢度。

## 📰 嚴選新聞來源

本專案全面棄用一般的泛科技新聞，改用以下六大高含金量來源：
1. **SemiAnalysis**：專攻半導體產業、晶圓代工、HBM 記憶體與 AI 晶片架構。
2. **The Information**：矽谷獨家新聞天花板，掌握 AI 巨頭內幕與商業獨家。
3. **TechCrunch (AI 專區)**：AI Agent、新創融資與產品動態最前線。
4. **VentureBeat (AI 專區)**：企業級 AI 應用與 LLM 模型評測。
5. **Ars Technica**：模型技術細節與硬體深度解析。
6. **MIT Technology Review**：前沿論文、AGI 趨勢與技術長期影響。

## ⚙️ 系統操作與運作方式

1. **新聞擷取 (NewsFetcher)**：透過 Python 腳本自動抓取上述六大 RSS 來源。
2. **推論核心 (AgentBrain)**：將抓取到的新聞餵給 Gemini，AI 會根據歷史紀錄 (`news_history.json`) 避免重複，並嚴格選出一篇對電機系最有幫助的內容。
3. **Discord 推播 (DiscordNotifier)**：將生成的精簡報告推送至指定的 Discord 頻道。
4. **自動化執行 (GitHub Actions)**：透過 `.github/workflows` 進行每日排程自動執行，無需人工介入。

## 💻 本地端測試與開發

若您希望在本地端執行此程式：

1. **安裝依賴套件**：
   ```bash
   pip install -r requirements.txt
   ```

2. **設定環境變數**：
   在專案根目錄下建立 `.env` 檔案，並填寫以下資訊：
   ```env
   GEMINI_API_KEY="your_gemini_api_key_here"
   DISCORD_WEBHOOK_URL="your_discord_webhook_url_here"
   ```
   *(注意：`.env` 檔案已加入 `.gitignore`，請勿將金鑰 Push 到 GitHub 上。)*

3. **執行程式**：
   ```bash
   python news_agent.py
   ```

## ☁️ 部署至 GitHub Actions

本專案已配置好 GitHub Actions。
請確保在您的 GitHub Repository 中設定了以下 **Repository Secrets**：
- `GEMINI_API_KEY`
- `DISCORD_WEBHOOK_URL`

設定完成後，系統即會在每日定時為您送上專屬於電機系的科技日報！
