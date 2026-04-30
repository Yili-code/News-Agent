# News AI Agent (自動化科技日報) 🚀

這是一個基於 Google Gemini 2.5 Flash 模型驅動的自動化 AI 科技日報系統。
歷經多次架構升級，目前的 Agent 具備了獨特的 **「三核心 (Tri-Core)」** 頂尖科技主管人格，旨在為電機系 (EE) 讀者提供最具備影響力與深度的技術洞察。

## 🧠 靈魂設定 (Tri-Core Persona)

本 Agent 完美融合了三位頂尖專家的思維模型：
1. **Anthropic 首席 AI 系統工程師**：深諳 Scaling Laws，專精於 Transformer 底層優化、MoE (Mixture of Experts) 設計、以及節能精準的 Agentic Workflow 建構。
2. **NVIDIA/Apple 首席資深架構師**：晶片層級的偏執狂，透徹理解先進封裝 (CoWoS)、HBM 記憶體牆、NVLink 互連架構以及 PPA (功耗、效能、面積) 的極致權衡。
3. **矽谷科技巨頭技術長 (CTO) 與產業戰略家**：具備宏觀生態系思維，洞察開源戰略、地緣政治、供應鏈重組與商業模式變革對全球科技格局的長遠影響。

## ⚙️ 系統特色與嚴格準則

- **每日唯一精選 (寧缺勿濫)**：每天系統會在眾多來源中，只挑選「一件」最具備重大影響力或技術突破的時事進行深度報導。如果當日無重大新聞，將直接休眠，拒絕發送瑣碎內容。
- **數據與事實驅動**：嚴格禁止公關廢話。報導必須基於具體的硬體規格 (如功耗、傳輸速率) 或具體的產業事件 (如建廠、法規、開源發布)。
- **深度影響力分析**：不只描述事實，更會點評該事件為何重要、是否顛覆現有技術典範，或如何改變產業鏈格局。
- **EE 專屬技術科普 (Technical Background)**：針對內文出現的專有名詞 (如 PCIe 5.0, Kioxia BG8, TSMC N2 等)，自動提供專屬於 EE 背景讀者的底層技術與規格科普。
- **每日思考題 (Daily Architect Challenge)**：在日報尾端提出一項底層硬體、晶片設計或系統架構相關的思考任務，引導讀者持續深化技術視野。

## 🏗️ 系統架構

1. **新聞擷取 (NewsFetcher)**：透過 RSS 抓取 L1 (硬體/半導體)、L2 (AI 軟體/模型)、L3 (科技生態/商業) 三大領域的新聞。
2. **推論核心 (AgentBrain)**：套用嚴格的提示詞與過濾機制，使用 Gemini 2.5 Flash 進行重組與深度分析。
3. **Discord 推播 (DiscordNotifier)**：將生成的精美 Markdown 格式報告，推送至指定的 Discord 頻道。
4. **自動化執行 (GitHub Actions)**：每天早上 08:00 (UTC+8) 自動執行，完全無伺服器 (Serverless) 且免人工介入。

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

本專案已配置好 GitHub Actions (`.github/workflows/daily_news.yml`)。
請確保在您的 GitHub Private Repository 中設定了以下 **Repository Secrets**：
- `GEMINI_API_KEY`
- `DISCORD_WEBHOOK_URL`

設定完成後，系統即會在每日定時為您送上由三位矽谷高管為您準備的科技日報！
