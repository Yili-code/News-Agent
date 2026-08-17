import os
import re
import json
import logging
import html
import feedparser
import requests
import google.generativeai as genai
from datetime import datetime
from difflib import SequenceMatcher
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv(override=True)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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

def clean_html_tags(raw_html: str) -> str:
    if not raw_html:
        return ""
    clean_text = re.sub(r'<[^>]+>', '', raw_html)
    return html.unescape(clean_text).strip()

class NewsFetcher:
    def __init__(self, limit_per_source=3):
        self.limit = limit_per_source

    def fetch_news(self):
        logging.info("開始擷取科技新聞...")
        aggregated_news = []

        for category, feeds in NEWS_SOURCES.items():
            for url in feeds:
                try:
                    parsed = feedparser.parse(url)
                    entries = parsed.entries[:self.limit]
                    
                    source_title = parsed.feed.title if 'title' in parsed.feed else url
                    
                    for entry in entries:
                        raw_summary = entry.get("summary", "") or entry.get("description", "")
                        cleaned_summary = clean_html_tags(raw_summary)[:500]
                        
                        aggregated_news.append({
                            "category": category,
                            "source": source_title,
                            "title": entry.get("title", "No Title"),
                            "link": entry.get("link", ""),
                            "summary": cleaned_summary
                        })
                except Exception as e:
                    logging.error(f"擷取 {url} 時發生錯誤: {e}")

        logging.info(f"成功擷取 {len(aggregated_news)} 篇新聞。")
        return aggregated_news

class AgentBrain:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("找不到 GEMINI_API_KEY，請確認環境變數設定。")
        
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-3.5-flash-lite')
        self.history_file = "news_history.json"

    def load_history(self):
        if not os.path.exists(self.history_file):
            return []

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content:
                return []

            history = json.loads(content)
            if not isinstance(history, list):
                raise ValueError("history file is not a JSON list")
            return history
        except Exception as e:
            logging.error(f"讀取歷史紀錄失敗: {e}")
            try:
                backup_path = f"{self.history_file}.corrupt-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                os.replace(self.history_file, backup_path)
                logging.warning(f"已備份損壞的歷史紀錄到 {backup_path}")
            except Exception:
                pass
            return []

    def normalize_text(self, text):
        if not text:
            return ""
        clean = html.unescape(str(text))
        clean = re.sub(r'<[^>]+>', '', clean)
        clean = re.sub(r'[^\w\u4e00-\u9fff]+', '', clean.lower())
        return clean.strip()

    def dedupe_news_items(self, news_items, history=None):
        if history is None:
            history = self.load_history()

        history_links = set()
        history_titles = []

        for entry in history:
            if isinstance(entry, dict):
                link = (entry.get('link') or '').strip()
                if link:
                    history_links.add(link)

                for value in [entry.get('title'), entry.get('summary')]:
                    if value:
                        history_titles.append(self.normalize_text(value))
            elif isinstance(entry, str):
                history_titles.append(self.normalize_text(entry))

        deduped = []
        for item in news_items:
            link = (item.get('link') or '').strip()
            title = self.normalize_text(item.get('title'))
            summary = self.normalize_text(item.get('summary'))

            duplicate = False
            if link and link in history_links:
                duplicate = True

            if not duplicate:
                candidates = [title, summary]
                for candidate in candidates:
                    if not candidate:
                        continue
                    for historical in history_titles:
                        if not historical:
                            continue
                        if candidate == historical or candidate in historical or historical in candidate:
                            duplicate = True
                            break
                        if SequenceMatcher(None, candidate, historical).ratio() >= 0.8:
                            duplicate = True
                            break
                    if duplicate:
                        break

            if not duplicate:
                deduped.append(item)

        return deduped

    def save_history(self, report_text, source_item=None):
        history = self.load_history()
        summary = report_text[:200].replace('\n', ' ')

        record = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "summary": summary
        }

        if source_item:
            record.update({
                "title": source_item.get('title', ''),
                "link": source_item.get('link', ''),
                "category": source_item.get('category', ''),
                "source": source_item.get('source', '')
            })

        history.append(record)
        history = history[-10:]
        try:
            temp_path = f"{self.history_file}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, self.history_file)
        except Exception as e:
            logging.error(f"儲存歷史紀錄失敗: {e}")

    def generate_daily_report(self, news_items):
        logging.info("開始呼叫 Gemini 生成每日科技日報...")

        deduped_news = self.dedupe_news_items(news_items)
        if not deduped_news:
            logging.warning("所有新聞都與歷史重複，今日不發送新報導。")
            return ""

        past_history = self.load_history()
        history_text = "\n".join([
            f"- {h.get('date', 'unknown')}: {h.get('title') or h.get('summary', '')}"
            if isinstance(h, dict) else f"- {h}"
            for h in past_history
        ])
        if not history_text:
            history_text = "無"

        news_text = ""
        for i, item in enumerate(deduped_news, 1):
            news_text += f"[{i}] {item['category']} - {item['source']}\n"
            news_text += f"標題: {item['title']}\n"
            news_text += f"連結: {item['link']}\n"
            news_text += f"摘要: {item['summary']}\n\n"

        prompt = f"""你現在是我的「科技日報 Agent」。使用者是一位資工系學生，目標是跟緊時事並理解其突破與影響。

        ### 核心任務
        請閱讀底部的【今日新聞資料】，挑選「恰好一篇」最有價值的技術突破或架構創新，撰寫一份精煉的每日科技簡報。

        ### 篩選與撰寫準則
        1. **精確挑選**：不論資料量多少，每天只挑選 1 篇對資工系學生最具技術價值（如：系統架構、算法突破、硬體與模型協同優化）的新聞或論文。
        2. **去重機制**：絕對禁止播報與【歷史紀錄】重複或相似的主題：
        {history_text}
        3. **內容結構**：簡報必須嚴格包含以下四個區塊：
        - <b>[新聞標題與連結]</b>：以 <a href="URL">標題文字</a> 呈現。若無 URL，請給出論文名稱或關鍵字。
        - <b> 簡單說明 </b>： 用高中學歷都懂的方式一句話說明原本同樣目標的作法與最新的做法之間的差異、突破。
        - <b> 技術核心解析 </b>：直奔底層技術架構與實作突破，拒絕公關稿套話，適當進行換行。
        - <b> 新聞價值 </b>：精準說明「為什麼資工系學生需要理解這個觀點」，包含對系統底層、工程思維或實務開發的實質幫助。
        - <b>產業與未來影響</b>：簡單說明該突破對整體技術生態或商業落地帶來的連鎖反應。
        4. 將結果去 AI 化

        ### 輸出格式與排版規範 (最高優先級)
        1. **Telegram HTML 格式**：僅允許使用 <b>加粗</b>、<i>斜體</i>、<code>程式碼</code> 與 <a href="URL">超連結</a>，絕對禁止使用 Markdown 符號（如 ** 或 #）。
        2. **完全無廢話**：禁止任何開場白、招呼語或結語（如「好的，這是今天的...」），直接以新聞標題開始。
        3. **篇幅**：總字數控制在 400 字左右，簡潔乾淨。
        4. **專有名詞規範 (嚴格執行)**：
        - **絕對禁止括號翻譯**：嚴禁出現 `中文 (English)` 格式（如禁止寫 `稀疏激活 (Sparse Activation)` 或 `路由器 (Router)`）。中文名詞直接寫中文，英文名詞直接寫英文。
        - **技術縮寫與術語**：常見專有名詞與縮寫（如 GPU, MoE, CUDA, LLM, HBM, Architecture）直接使用英文，不需附帶中文註解。

        ---

        【今日新聞資料】
        {news_text}
        """

        try:
            response = self.model.generate_content(prompt)
            logging.info("Gemini 回應生成成功。")

            match = re.search(r'<a href="([^"]+)">([^<]+)</a>', response.text)
            selected_item = None
            if match:
                link = match.group(1)
                title = match.group(2)
                for item in deduped_news:
                    if item.get('link') == link or self.normalize_text(item.get('title')) == self.normalize_text(title):
                        selected_item = item
                        break

            self.save_history(response.text, source_item=selected_item)

            return response.text
        except Exception as e:
            logging.error(f"Gemini API 呼叫失敗: {e}")
            raise

def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False  
    } 

    response = requests.post(url, json=payload).json()
    
    if not response.get("ok"):
        logging.warning(f"Telegram HTML 解析失敗 ({response.get('description')})，嘗試發送純文字...")
        payload.pop("parse_mode", None)
        response = requests.post(url, json=payload).json()

    return response

def run_news_agent():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("缺少 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID 環境變數！")
        return False

    fetcher = NewsFetcher(limit_per_source=3)
    news_items = fetcher.fetch_news()

    if not news_items:
        logging.warning("今日無新聞可供處理。")
        return False

    brain = AgentBrain()
    report = brain.generate_daily_report(news_items)

    today_str = datetime.now().strftime("%Y-%m-%d")
    final_report = f"<b>Daily Brief ({today_str})</b>\n\n" + report

    result = send_telegram_message(final_report)

    if result.get("ok"):
        logging.info("今日排程執行完畢，成功發送至 Telegram。")
        return True

    logging.error(f"Telegram 訊息發送失敗: {result}")
    return False

def main():
    return run_news_agent()

if __name__ == "__main__":
    main()