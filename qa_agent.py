import os
import requests
import logging
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

class DiscordQA:
    def __init__(self):
        self.bot_token = os.environ.get("DISCORD_BOT_TOKEN")
        self.channel_id = os.environ.get("DISCORD_CHANNEL_ID")
        self.api_key = os.environ.get("GEMINI_API_KEY")
        
        if not all([self.bot_token, self.channel_id, self.api_key]):
            raise ValueError("缺少必要的環境變數 (DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID, GEMINI_API_KEY)")
            
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json"
        }

    def fetch_recent_messages(self, hours_back=8):
        """讀取最近的訊息"""
        url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages?limit=30"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            messages = response.json()
            
            # 過濾時間與機器人本身的訊息
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            user_messages = []
            
            for msg in messages:
                # 判斷是否為機器人發送的
                if msg.get('author', {}).get('bot'):
                    continue
                    
                # Discord 時間為 ISO format (e.g. 2026-05-12T04:25:00.000000+00:00)
                msg_time = datetime.fromisoformat(msg['timestamp'])
                if msg_time > cutoff_time:
                    author = msg['author']['username']
                    content = msg['content']
                    user_messages.append(f"{author}: {content}")
                    
            return user_messages
        except Exception as e:
            logging.error(f"獲取 Discord 訊息失敗: {e}")
            return []

    def check_and_answer_questions(self, messages):
        """判斷是否有問題並使用 Gemini 回答"""
        if not messages:
            logging.info("沒有收到任何新的讀者訊息。")
            return None
            
        chat_log = "\n".join(messages)
        prompt = f"""
        你現在是「三核心 AI 科技日報 Agent」，這是一個具備首席工程師、資深晶片架構師與技術長 (CTO) 視野的角色。
        
        以下是最近幾小時內讀者在頻道中的對話紀錄：
        {chat_log}
        
        任務：
        1. 判斷對話中是否包含對「今天的新聞、技術、學術論文或任何科技知識」的提問。
        2. 如果【沒有任何提問】或是只是閒聊，請嚴格只輸出「NO_QUESTIONS」，不要有任何其他文字。
        3. 如果【有提問】，請以你「三核心」的專業角色，針對他們的問題給出精煉、具體、基於第一原理的解答。
           - 語氣：專業、深邃、自信，直接切入技術本質。
           - 排版要求：為了高可讀性，請分成 2~3 個簡短段落，段落之間務必留空行。重要的名詞、數據請用 **粗體** 標示，讓讀者能一眼抓住重點。
        """
        
        try:
            response = self.model.generate_content(prompt)
            reply = response.text.strip()
            
            if reply == "NO_QUESTIONS":
                logging.info("讀者沒有提出問題，無需回覆。")
                return None
            return reply
        except Exception as e:
            logging.error(f"Gemini API 呼叫失敗: {e}")
            return None

    def post_reply(self, reply_text):
        """將回答推送到 Discord"""
        if not reply_text:
            return
            
        url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages"
        payload = {"content": f"**💡 架構師的答疑時間**\n\n{reply_text}"}
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            logging.info("成功回覆讀者的問題！")
        except Exception as e:
            logging.error(f"推播回答至 Discord 失敗: {e}")

def main():
    try:
        logging.info("開始檢查讀者提問...")
        qa_agent = DiscordQA()
        # 往前看 8 小時內的訊息 (涵蓋 08:00~12:00, 12:00~18:00, 18:00~22:00)
        recent_msgs = qa_agent.fetch_recent_messages(hours_back=8)
        
        if recent_msgs:
            logging.info(f"找到 {len(recent_msgs)} 則讀者訊息，開始分析...")
            reply = qa_agent.check_and_answer_questions(recent_msgs)
            qa_agent.post_reply(reply)
        else:
            logging.info("近期沒有讀者發言。")
            
        logging.info("Q&A 檢查完畢。")
    except Exception as e:
        logging.error(f"Q&A 代理程式執行期間發生錯誤: {e}")

if __name__ == "__main__":
    main()
