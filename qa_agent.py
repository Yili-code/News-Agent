import json
import logging
import os
import time

import google.generativeai as genai
import requests
from dotenv import load_dotenv

import news_agent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv(override=True)
gemini_api_key = os.getenv("GEMINI_API_KEY")

def load_telegram_config():
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not all([telegram_bot_token, telegram_chat_id, gemini_api_key]):
        raise ValueError("缺少必要的環境變數 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY)")

    return {
        "gemini_api_key": gemini_api_key,
        "telegram_bot_token": telegram_bot_token,
        "telegram_chat_id": telegram_chat_id,
    }


class TelegramClient:
    def __init__(self, bot_token: str, chat_id: str):
        self.state_file = "telegram_last_update_id.json"
        self.chat_id = str(chat_id)
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def load_last_update_id(self) -> int:
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
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump({"last_update_id": update_id}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.warning(f"保存狀態檔失敗: {e}")

    def fetch_new_messages(self):
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
            print(update.get("update_id"), update.get("message", {}).get("text"))
            current_update_id = update.get("update_id", 0)
            if current_update_id > max_update_id:
                max_update_id = current_update_id

            msg = update.get("message")
            if not msg:
                continue

            if msg.get("from", {}).get("is_bot"):
                continue

            chat_id = str(msg.get("chat", {}).get("id", ""))
            if self.chat_id and chat_id != self.chat_id:
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
            logging.info("已成功回覆")
        except Exception as e:
            logging.error(f"推播回答至 Telegram 失敗: {e}")


class IntentAnalyzer:
    def __init__(self, gemini_api_key: str):
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-3.5-flash-lite')

    def analyze_intent(self, user_text: str, user_name: str) -> dict | None:
        """分析意圖並透過 Response Schema 強制回傳合法 JSON"""
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


class TelegramBot:
    def __init__(self, telegram_client: TelegramClient, intent_analyzer: IntentAnalyzer, news_runner=None):
        self.telegram_client = telegram_client
        self.intent_analyzer = intent_analyzer
        self.news_runner = news_runner or news_agent.run_news_agent

    def handle_message(self, msg: dict):
        logging.info(f"收到來自{msg['from']}的訊息: {msg['text']}")

        result = self.intent_analyzer.analyze_intent(msg["text"], msg["from"])
        if not result:
            return

        intent = result.get("intent")
        reply = result.get("reply")

        if reply:
            self.telegram_client.post_reply(msg["chat_id"], reply, msg["message_id"])

        if intent == "TRIGGER_NEWS":
            logging.info("觸發 news_agent 執行...")
            try:
                news_content = self.news_runner()
                self.telegram_client.post_reply(msg["chat_id"], news_content)
            except Exception as e:
                logging.error(f"執行 news_agent 時發生錯誤: {e}")
                self.telegram_client.post_reply(msg["chat_id"], "擷取新聞時發生異常，Sir。")

    def run(self, polling_interval: int = 2):
        logging.info("Jarvis 已啟動，開始監聽私人訊息...")

        while True:
            try:
                new_msgs = self.telegram_client.fetch_new_messages()
                for msg in new_msgs:
                    self.handle_message(msg)
            except Exception as e:
                logging.error(f"監聽過程發生未預期錯誤: {e}")

            time.sleep(polling_interval)


def main():
    config = load_telegram_config()
    telegram_client = TelegramClient(config["telegram_bot_token"], config["telegram_chat_id"])
    intent_analyzer = IntentAnalyzer(config["gemini_api_key"])
    bot = TelegramBot(telegram_client, intent_analyzer)
    bot.run()


if __name__ == "__main__":
    main()