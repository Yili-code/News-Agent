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

# 設定新聞來源
NEWS_SOURCES = {
    "半導體與 AI 晶片架構": [
        "https://www.semianalysis.com/feed"
    ],
    "AI 巨頭內幕與商業獨家": [
        "https://www.theinformation.com/feed"
    ],
    "AI Agent、新創融資與產品動態": [
        "https://techcrunch.com/category/artificial-intelligence/feed/"
    ],
    "企業級 AI 應用與 LLM 模型評測": [
        "https://venturebeat.com/category/ai/feed/"
    ],
    "模型技術細節與硬體解析": [
        "https://feeds.arstechnica.com/arstechnica/index"
    ],
    "前沿論文、RSI 自我迭代與 AGI 趨勢": [
        "https://www.technologyreview.com/feed/"
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
        你現在是我的「科技日報 Agent」，我是一個電機系的學生。

        【嚴格禁止事項與歷史紀錄】
        1. 避免重複：以下是過去幾天已經報告過的主題摘要：
        {history_text}
        請絕對不要報告與上述相似或重複的新聞，請尋找全新的突破。

        請閱讀以下今天的科技新聞，並撰寫一份專業的科技日報。
        
        【篩選與撰寫嚴格準則】
        1. 數量與挑選邏輯：每天「只挑選一件」對「電機系學生」最有幫助的新聞。不管今天的新聞多寡或影響力大小，請務必挑出一篇最好的來播報。
        2. 連結格式：如果有引用新聞，連結只能顯示文字標題 `[標題](連結)`，絕對不可以出現任何圖片。若是自行分享論文，請盡量提供真實的論文名稱或可搜尋的關鍵字。
        3. 內容呈現：我希望你給的內容是直接擷取網站的內容，但篇幅上不要超過我給你的字數限制，你要自己斟酌與取捨，並讓內容看起來自然流暢。

        【輸出排版格式與可讀性要求】（請嚴格遵循以下格式，不要有任何開場白）
        1. 字數與分段：總字數控制在 400 字內（可依實際新聞長度增減）。適時分段與縮排，提升可讀性。
        2. 專業中文表達（嚴格執行）：內文敘述請盡量使用純中文。**【絕對禁止】** 在任何中文名詞後面加上括號附註英文！絕對不可以出現類似 `稀疏激活 (Sparse Activation)`、`路由器 (Router)`、`延展性 (Scalability)` 的寫法。請直接寫「稀疏激活」、「路由器」、「延展性」即可。對於產業通用的技術縮寫（如 GPU, AI, MoE, HBM），請直接單獨寫英文（例如寫 MoE 即可，絕對不要寫 `MoE (Mixture-of-Experts)`）。

        [參考來源標題](連結)

        今日新聞資料：
        {news_text}
        """

        try:
            response = self.model.generate_content(prompt)
            logging.info("日報生成完成。")
            
            # 每天必定有新聞，直接儲存至歷史紀錄
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
