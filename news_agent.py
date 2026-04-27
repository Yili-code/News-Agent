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

    def generate_daily_report(self, news_items):
        """
        將新聞餵給 Gemini 模型，產生具備首席架構師視角的日報。
        """
        logging.info("開始生成 AI 架構師日報...")
        
        # 將新聞轉換為文本以供 prompt 使用
        news_text = ""
        for i, item in enumerate(news_items, 1):
            news_text += f"[{i}] {item['category']} - {item['source']}\n"
            news_text += f"標題: {item['title']}\n"
            news_text += f"連結: {item['link']}\n"
            news_text += f"摘要: {item['summary']}\n\n"

        prompt = f"""
        你現在是我的「雙核心 AI 科技日報 Agent」。
        你的靈魂融合了：
        1. Anthropic 首席工程師：專精於極度節能且精準的 Agent 系統與 LLM 演進。
        2. NVIDIA/Apple 首席資深架構師 (Principal Architect)：專注於下一代 AI 晶片研發，崇尚「第一原理思考」。
        你的終極目標是：引導我在十年後帶領團隊設計出打敗競爭對手的 AI 晶片與系統。

        請閱讀以下今天的科技新聞，並撰寫一份專業的科技日報。
        
        【輸出格式與技術要求】
        1. 語氣：極度專業、深邃、使用「我們 (We)」來探討架構，口吻如同向高階工程團隊進行 Daily Stand-up 匯報。
        2. 列點式掃描 (Quick Scan)：在開頭快速歸納今天的 3-5 個最關鍵重點。
        3. 深度分析長文 (Deep Dive)：挑選最具代表性的新聞，從「底層硬體架構 (Silicon/Memory/Bandwidth)」與「系統層影響 (Agentic Workflow/Scaling Laws)」的角度進行毒辣的評論與第一原理分析。
        4. 請附上參考的新聞來源連結。
        5. 輸出請使用 Markdown 格式。為了適應 Discord 傳送，請將內容結構化並保持在適當長度。

        今日新聞資料：
        {news_text}
        """

        try:
            response = self.model.generate_content(prompt)
            logging.info("日報生成完成。")
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
