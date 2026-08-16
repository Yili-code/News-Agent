import json
import logging
import os
import time
from datetime import datetime, timezone

import google.generativeai as genai
import requests
from dotenv import load_dotenv

import news_agent  # 確保 news_agent.py 內有提供對應的調用函式

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv(override=True)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


class TelegramQA:
    def __init__(self):
        self.state_file = "telegram_last_update_id.json"

        if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY]):
            raise ValueError("缺少必要的環境變數 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY)")

        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-3.5-flash-lite')
        self.base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

    def load_last_update_id(self) -> int:
        """讀取上次處理到的 update_id"""
        if not os.path.exists(self.state_file):
            return 0
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("last_update_id", 0)
        except Exception as e:
            logging.warning(f"讀取狀態檔失敗: {e}")
            return 0

    def save_last_update_id(self, update_id: int):
        """保存最後處理的 update_id"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump({"last_update_id": update_id}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.warning(f"保存狀態檔失敗: {e}")

    def fetch_new_messages(self):
        """從 Telegram 擷取所有未處理的私訊訊息"""
        last_update_id = self.load_last_update_id()
        offset = last_update_id + 1 if last_update_id > 0 else 0

        try:
            response = requests.get(
                f"{self.base_url}/getUpdates",
                params={"offset": offset, "limit": 100, "timeout": 10, "allowed_updates": ["message"]},
                timeout=15,
            )
            response.raise_for_status()
            updates = response.json().get("result", [])
        except Exception as e:
            logging.error(f"獲取 Telegram 訊息失敗: {e}")
            return []

        messages = []
        max_update_id = last_update_id

        for update in updates:
            current_update_id = update.get("update_id", 0)
            if current_update_id > max_update_id:
                max_update_id = current_update_id

            msg = update.get("message")
            if not msg:
                continue

            if msg.get("from", {}).get("is_bot"):
                continue

            chat_id = str(msg.get("chat", {}).get("id", ""))
            
            if str(TELEGRAM_CHAT_ID) and chat_id != str(TELEGRAM_CHAT_ID):
                continue

            text = msg.get("text") or msg.get("caption") or ""
            if not text.strip():
                continue

            messages.append({
                "chat_id": chat_id,
                "message_id": msg.get("message_id"),
                "text": text,
                "from": msg.get("from", {}).get("first_name", "User"),
            })

        if max_update_id > last_update_id:
            self.save_last_update_id(max_update_id)

        return messages

    def analyze_intent(self, user_text: str, user_name: str) -> dict | None:
        """分析意圖並透過 Response Schema 強制回傳合法 JSON"""
        
        # 1. 定義標準 JSON Schema
        intent_schema = {
            "type": "OBJECT",
            "properties": {
                "intent": {
                    "type": "STRING",
                    "enum": ["TRIGGER_NEWS", "GENERAL_CHAT"]
                },
                "reply": {
                    "type": "STRING",
                    "description": "給使用者的即時回應文字，1-2 句話"
                }
            },
            "required": ["intent", "reply"]
        }

        # 2. Prompt 移除模稜兩可的語法範例，專注於任務說明
        prompt = f"""
你現在是「JARVIS」，頂尖數位管家。

人設與應對邏輯：
* 風格：冷靜、極簡、精確、自信，帶有英式幽默。
* 稱呼：稱呼對方為 Sir。
* 語言：繁體中文，技術術語直接使用英文（不加括號中文翻譯）。
* 絕不講客套話或廢話（如「隨時聽候您的差遣」、「很高興為您服務」）。
* 當使用者僅輸入招呼語（如「你好」、「Hi」）時，只需給出幹練的一句話確認在線。
* 回應訊息控制在 1-2 句話內，直擊重點。

意圖判斷規則：
* 若使用者要求看新聞、傳送新聞、即時新聞，intent 為 "TRIGGER_NEWS"。
* 若為一般對話或閒聊，intent 為 "GENERAL_CHAT"。

使用者 ({user_name}) 對你說：
{user_text}
"""
        try:
            # 3. 傳入 response_schema 讓 Gemini 在底層強迫符合 Schema
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": intent_schema
                }
            )
            return json.loads(response.text.strip())
        except Exception as e:
            logging.error(f"Gemini API 解析失敗: {e}")
            return None

    def post_reply(self, chat_id: str, reply_text: str, reply_to_message_id: int = None):
        """推送回答至 Telegram"""
        if not reply_text:
            return

        payload = {"chat_id": chat_id, "text": reply_text, "disable_web_page_preview": True}
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        try:
            response = requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=20)
            response.raise_for_status()
            logging.info(f"已成功回覆")
        except Exception as e:
            logging.error(f"推播回答至 Telegram 失敗: {e}")


def main():
    qa_agent = TelegramQA()
    logging.info("Jarvis 已啟動，開始監聽私人訊息...")

    while True:
        try:
            new_msgs = qa_agent.fetch_new_messages()
            for msg in new_msgs:
                logging.info(f"收到來自{msg['from']}的訊息: {msg['text']}")
                
                # 1. 進行意圖分析
                result = qa_agent.analyze_intent(msg["text"], msg["from"])
                if not result:
                    continue

                intent = result.get("intent")
                reply = result.get("reply")

                # 2. 先推送即時回應（例如：「正在為您抓取最新新聞，Sir。」）
                if reply:
                    qa_agent.post_reply(msg["chat_id"], reply, msg["message_id"])

                # 3. 根據 Intent 派發任務 (Task Dispatching)
                if intent == "TRIGGER_NEWS":
                    logging.info("觸發 news_agent 執行...")
                    try:
                        # 呼叫 news_agent 模組內對應的進入點函式 (請確認 function 名稱)
                        news_content = news_agent.run_news_agent()
                        qa_agent.post_reply(msg["chat_id"], news_content)
                    except Exception as e:
                        logging.error(f"執行 news_agent 時發生錯誤: {e}")
                        qa_agent.post_reply(msg["chat_id"], "擷取新聞時發生異常，Sir。")

        except Exception as e:
            logging.error(f"監聽過程發生未預期錯誤: {e}")

        time.sleep(2)


if __name__ == "__main__":
    main()