import os
import json
import logging
import feedparser
import requests
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 載入環境變數 (本地端測試使用)
load_dotenv()

# 設定新聞來源 (L1, L2, L3)
NEWS_SOURCES = {
    "L1_Hardware_Silicon": [
        "https://www.servethehome.com/feed/",
        "https://semiwiki.com/feed/"
    ],
    "L2_AI_Software": [
        "https://bair.berkeley.edu/blog/feed.xml", # BAIR Blog (Alternative for top AI research)
        "https://techcrunch.com/category/artificial-intelligence/feed/"
    ],
    "L3_Ecosystem_Business": [
        "https://stratechery.com/feed/",
        "https://www.theverge.com/rss/index.xml"
    ]
}

class NewsFetcher:
    def __init__(self, limit_per_source=3):
        self.limit = limit_per_source

    def fetch_news(self):
        """
        從定義的 RSS Feeds 擷取新聞，每家來源最多取 Top 3。
        """
        logging.info("開始擷取科技新聞 RSS...")
        aggregated_news = []

        for category, feeds in NEWS_SOURCES.items():
            for url in feeds:
                try:
                    parsed = feedparser.parse(url)
                    entries = parsed.entries[:self.limit]
                    
                    source_title = parsed.feed.title if 'title' in parsed.feed else url
                    
                    for entry in entries:
                        aggregated_news.append({
                            "category": category,
                            "source": source_title,
                            "title": entry.get("title", "No Title"),
                            "link": entry.get("link", ""),
                            "summary": entry.get("summary", "")[:500] # 取前500字元避免過長
                        })
                except Exception as e:
                    logging.error(f"擷取 {url} 時發生錯誤: {e}")

        logging.info(f"成功擷取 {len(aggregated_news)} 篇新聞。")
        return aggregated_news

class AgentBrain:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("找不到 GEMINI_API_KEY，請確認環境變數設定。")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.history_file = "news_history.json"

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"讀取歷史紀錄失敗: {e}")
        return []

    def save_history(self, report_text):
        history = self.load_history()
        # 儲存前 200 字作為摘要即可，避免檔案過大
        summary = report_text[:200].replace('\n', ' ')
        history.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "summary": summary
        })
        # 只保留最近 10 次紀錄
        history = history[-10:]
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"儲存歷史紀錄失敗: {e}")

    def generate_daily_report(self, news_items):
        """
        將新聞餵給 Gemini 模型，產生具備首席架構師視角的日報。
        """
        logging.info("開始生成 AI 架構師日報...")
        
        # 讀取歷史紀錄
        past_history = self.load_history()
        history_text = "\n".join([f"- {h['date']}: {h['summary']}" for h in past_history])
        if not history_text:
            history_text = "無"

        # 將新聞轉換為文本以供 prompt 使用
        news_text = ""
        for i, item in enumerate(news_items, 1):
            news_text += f"[{i}] {item['category']} - {item['source']}\n"
            news_text += f"標題: {item['title']}\n"
            news_text += f"連結: {item['link']}\n"
            news_text += f"摘要: {item['summary']}\n\n"

        prompt = f"""
        你現在是我的「三核心 AI 科技日報 Agent」。
        你的靈魂完美融合了三位頂尖專家的思維模型：
        1. Anthropic 首席 AI 系統工程師：你深諳 Scaling Laws 的極限，專精於 Transformer 底層優化、MoE (Mixture of Experts) 設計、以及極度節能且精準的 Agentic Workflow 建構。
        2. NVIDIA/Apple 首席資深架構師 (Principal Architect)：你是晶片層級的偏執狂，崇尚「第一原理思考」。你透徹理解先進封裝 (CoWoS)、HBM 記憶體牆、NVLink 互連架構以及 PPA (功耗、效能、面積) 的極致權衡。
        3. 矽谷科技巨頭技術長 (CTO) 與產業戰略家：你具備宏觀的生態系思維，能敏銳洞察開源戰略、地緣政治、供應鏈重組與商業模式變革如何重塑全球科技產業的長遠格局。

        【個人說話風格 (口頭禪)】
        你的講話帶有強烈的個人風格：
        1. 結尾極度愛用「的部分」：在講解技術、架構或解釋原因時，你經常會在句尾加上「的部分」（例如：「以上就是該架構會比較快原因的部分」、「這邊是記憶體架構的部分」）。
        2. 教授般的收尾：在某些段落解釋完畢後，你偶爾會像大學教授一樣，加上一句：「以上有問題嗎？沒有問題的話我們看下一章」。

        【嚴格禁止事項與歷史紀錄】
        1. 避免重複：以下是過去幾天已經報告過的主題摘要：
        {history_text}
        請絕對不要報告與上述相似或重複的新聞（例如某公司又宣稱短時間 tape-out 等），請尋找全新的突破。
        2. 停止科普基礎常識：針對電機系讀者，絕對不要解釋以下基礎名詞：SOC、EDA、RTL、PPA、製程節點 (Process Node)、臺積電 CoWoS / 3D Fabric 等先進封裝技術、HBM、Memory Wall。這些都是基本常識。你唯一需要科普的是問世不到一兩年的「全新」技術。

        請閱讀以下今天的科技新聞，並撰寫一份專業的科技日報。
        
        【篩選與撰寫嚴格準則】
        1. 數量限制：每天「只挑選一件」真正具備「重大影響力」或「技術突破」的關鍵新聞。
        2. 提升內容品質與實質內涵：拒絕空泛的公關行銷廢話（例如「展望聚焦於未來製程節點的演進」、「持續提升 PPA」等大家都知道的常識）。報告必須聚焦於「紮實的技術細節」，例如：新架構解決了什麼瓶頸？新材料有什麼物理特性突破？具體的論文數據為何？
        3. 寧缺勿濫與主動分享論文：如果今天提供的新聞全部都是空泛的行銷話語或沒有具體技術細節，請「完全放棄」這些新聞，當天不要發一般的新聞內容。取而代之，請利用你的知識，主動分享並科普一篇近期（近一兩年內）在「固態電子、電池技術、電波領域或 AI 底層硬體架構」的「最新突破性論文」或「全新技術」，進行深度的技術探討。
        4. 連結格式：如果有引用新聞，連結只能顯示文字標題 `[標題](連結)`，絕對不可以出現任何圖片。若是自行分享論文，請盡量提供真實的論文名稱或可搜尋的關鍵字。

        【輸出排版格式與可讀性要求】（請嚴格遵循以下格式，不要有任何開場白）
        1. 分段與留白：內容請分成 2 到 3 個簡短的段落，段落之間務必留空行，不要將文字擠成一團。
        2. 重點強調：重要的名詞、數據、技術突破點，請務必使用 **粗體** 標示，讓讀者能一眼抓住重點。

        **今日重點（技術突破 / 最新論文分享）:**
        (直接切入事實描述，以 2~3 段式呈現，適度留白並使用粗體強調關鍵字。包含具體技術細節、數據或新技術的物理/架構特性，並說明此技術的顛覆性與實質影響)

        **技術科普 (Technical Deep Dive):**
        - **[全新技術名詞/論文核心概念]**: (針對 EE 讀者的原理解釋，僅限非基礎常識的全新技術)

        [參考來源標題](連結) (若有相關來源，或自行分享的論文名稱)

        今日新聞資料：
        {news_text}
        """

        try:
            response = self.model.generate_content(prompt)
            logging.info("日報生成完成。")
            
            # 若不是無新聞，則儲存至歷史紀錄
            if "今日無具備重大影響力之新聞" not in response.text:
                self.save_history(response.text)

            return response.text
        except Exception as e:
            logging.error(f"Gemini API 呼叫失敗: {e}")
            raise

class DiscordNotifier:
    def __init__(self):
        self.webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
        if not self.webhook_url:
            raise ValueError("找不到 DISCORD_WEBHOOK_URL，請確認環境變數設定。")

    def send_message(self, content):
        """
        將報告發送至 Discord。考量到 Discord 訊息長度限制 (2000字元)，需進行分段傳送。
        """
        logging.info("開始推送至 Discord...")
        
        # 簡單的分段邏輯，以段落來分割避免切斷句子
        chunks = self._chunk_text(content, max_length=1900)
        
        for i, chunk in enumerate(chunks):
            payload = {"content": chunk}
            try:
                response = requests.post(self.webhook_url, json=payload)
                response.raise_for_status()
                logging.info(f"成功推送第 {i+1}/{len(chunks)} 段訊息。")
            except Exception as e:
                logging.error(f"Discord 推送失敗: {e}")
                raise

    def _chunk_text(self, text, max_length=1900):
        lines = text.split('\n')
        chunks = []
        current_chunk = ""
        
        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'
                
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

def main():
    try:
        # 1. 擷取新聞 (Limit: Top 3 per source)
        fetcher = NewsFetcher(limit_per_source=3)
        news_items = fetcher.fetch_news()
        
        if not news_items:
            logging.warning("今日無新聞可供處理。")
            return

        # 2. 生成日報
        brain = AgentBrain()
        report = brain.generate_daily_report(news_items)
        
        # 3. 加上日期標題
        today_str = datetime.now().strftime("%Y-%m-%d")
        final_report = f"# 🚀 AI & Silicon Architect Daily Brief ({today_str})\n\n" + report

        # 4. 推送 Discord
        notifier = DiscordNotifier()
        notifier.send_message(final_report)
        
        logging.info("今日排程執行完畢。")

    except Exception as e:
        logging.error(f"系統執行期間發生嚴重錯誤: {e}")
        # 如果有設定 webhook，也可以考慮將錯誤訊息推送到 Discord 讓開發者知道
        try:
            err_webhook = os.environ.get("DISCORD_WEBHOOK_URL")
            if err_webhook:
                requests.post(err_webhook, json={"content": f"⚠️ News Agent 執行失敗: {str(e)}"})
        except:
            pass

if __name__ == "__main__":
    main()
