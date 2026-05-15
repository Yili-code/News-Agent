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

    def fetch_recent_messages(self, max_hours_back=24):
        """讀取最近的訊息，只抓取在機器人上次發言「之後」的讀者訊息"""
        url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages?limit=50"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            messages = response.json()
            
            # Discord API 回傳的訊息是「由新到舊」排序
            # 找到機器人自己「最後一次發言」的時間
            last_bot_msg_time = None
            for msg in messages:
                if msg.get('author', {}).get('bot') and msg['author']['username'] == 'News AI Agent':
                    last_bot_msg_time = datetime.fromisoformat(msg['timestamp'])
                    break
            
            # 如果找不到機器人發言，或者機器人很久沒發言，最多往回看 24 小時
            fallback_cutoff = datetime.now(timezone.utc) - timedelta(hours=max_hours_back)
            cutoff_time = last_bot_msg_time if last_bot_msg_time and last_bot_msg_time > fallback_cutoff else fallback_cutoff
            
            user_messages = []
            
            # 反轉順序，變成「由舊到新」，比較符合對話邏輯
            for msg in reversed(messages):
                if msg.get('author', {}).get('bot'):
                    continue
                    
                msg_time = datetime.fromisoformat(msg['timestamp'])
                if msg_time > cutoff_time:
                    content = msg['content']
                    # 只處理有提到「阿福」的訊息
                    if "阿福" in content:
                        author = msg['author']['username']
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
        你現在是「阿福教授」，一位資深的電機系教授。
        
        【人物設定】
        1. 你的研究專長是 CIM (Computing-in-Memory) 以及 Testing。
        2. 你的態度：身為資深教授，你骨子裡帶有一點傲嬌與不耐煩，經常覺得學生問的問題「有點笨」。回話時常帶著一種「這不是常識嗎？」、「連這都不懂？」的微酸語氣。
        3. 專業預設：除非學生特別要求用通俗/簡單的方式解釋，否則你一律把發問者當作「電機系的大學生或研究生」，直接使用專業的硬體、電路、系統架構術語來解說。
        
        【個人說話風格 (口頭禪)】
        你的講話帶有強烈的個人風格：結尾極度愛用「的部分」：在講解技術、架構或解釋原因時，你經常會在句尾強行加上「的部分」（例如：「以上就是該架構會比較快原因的部分」、「這邊是測試機台的部分」）。
        
        以下是最近幾小時內讀者在頻道中的對話紀錄：
        {chat_log}
        
        任務：
        請針對讀者的發言給予回覆。不論他們是問問題、閒聊、還是提出無厘頭的要求。
        - 語氣：專業、深邃、自信，直接切入技術本質，但若遇到閒聊也能幽默應對。
        - 專業中文表達（嚴格執行）：內文敘述請盡量使用純中文。**【絕對禁止】** 在任何中文名詞後面加上括號附註英文！絕對不可以出現類似 `稀疏激活 (Sparse Activation)` 的寫法。請直接寫「稀疏激活」即可。對於產業通用的技術縮寫（如 GPU, AI, MoE），請直接單獨寫英文（例如寫 MoE 即可，絕對不要寫 `MoE (Mixture-of-Experts)`）。
        - 排版要求：簡短回答，一次說話不要超過30個字，如果真的需要使用超過30個字，請分多次傳訊息。重要的名詞、數據請用 **粗體** 標示。
        """
        
        try:
            response = self.model.generate_content(prompt)
            reply = response.text.strip()
            
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
        # 往前看最多 24 小時內的訊息，但會自動扣除機器人已經回覆過的部分
        recent_msgs = qa_agent.fetch_recent_messages(max_hours_back=24)
        
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
