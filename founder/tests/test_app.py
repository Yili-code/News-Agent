import os
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

from founder import app as founder_app
from founder.storage import SQLiteStore


def issue(date="2026-10-05"):
    return {
        "date": date,
        "kind": "daily",
        "headline": "Three source-backed opportunities",
        "status": "source_only",
        "sources": [{"name": "HN", "ok": True, "count": 1}],
        "signals": [
            {
                "id": "HN:1",
                "title": "A founder problem",
                "topic": "Founder",
                "url": "https://example.com/item",
                "excerpt": "A bounded excerpt",
            }
        ],
    }


class FounderAppTests(unittest.TestCase):
    def setUp(self):
        test_dir = Path(__file__).resolve().parents[1] / ".local" / "tests"
        test_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = test_dir / f"{uuid.uuid4().hex}.sqlite3"
        self.store = SQLiteStore(self.db_path)
        founder_app.store = self.store
        self.env = patch.dict(
            os.environ,
            {"APP_KEY": "private-test-key", "JOB_TOKEN": "jobs-test-key"},
            clear=False,
        )
        self.env.start()
        founder_app.app.config.update(TESTING=True)
        self.client = founder_app.app.test_client()

    def tearDown(self):
        self.env.stop()
        self.store.close()
        self.db_path.unlink(missing_ok=True)

    def job_headers(self):
        return {"Authorization": "Bearer jobs-test-key"}

    def login(self):
        response = self.client.post("/api/login", json={"key": "private-test-key"})
        self.assertEqual(response.status_code, 200)

    def test_health_and_private_state(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        self.assertEqual(self.client.get("/api/state").status_code, 401)
        self.login()
        self.assertEqual(self.client.get("/api/state").status_code, 200)

    def test_job_token_does_not_grant_browser_session(self):
        response = self.client.get("/api/state", headers=self.job_headers())
        self.assertEqual(response.status_code, 401)

    def test_issue_feedback_and_logout_persist(self):
        self.assertEqual(
            self.client.post("/internal/issues", json=issue(), headers=self.job_headers()).status_code,
            200,
        )
        self.login()
        feedback = {"id": "HN:1", "reaction": "research", "saved": True, "note": "Interview next"}
        self.assertEqual(self.client.post("/api/feedback", json=feedback).status_code, 200)
        state = self.client.get("/api/state").get_json()
        self.assertEqual(state["feedback"][0]["note"], "Interview next")
        self.assertEqual(self.client.post("/api/logout").status_code, 200)
        self.assertEqual(self.client.get("/api/state").status_code, 401)

    def test_cross_origin_write_and_login_rate_limit(self):
        denied = self.client.post(
            "/api/login", json={"key": "private-test-key"}, headers={"Origin": "https://evil.example"}
        )
        self.assertEqual(denied.status_code, 403)
        for _ in range(10):
            self.assertEqual(self.client.post("/api/login", json={"key": "wrong"}).status_code, 401)
        self.assertEqual(self.client.post("/api/login", json={"key": "wrong"}).status_code, 429)

    def test_delivery_is_claimed_once(self):
        self.client.post("/internal/issues", json=issue(), headers=self.job_headers())
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "fake", "TELEGRAM_CHAT_ID": "123"}), patch(
            "founder.app.requests.post"
        ) as post:
            post.return_value = Mock(status_code=200)
            post.return_value.json.return_value = {"ok": True}
            first = self.client.post("/internal/deliver", json={"date": "2026-10-05"}, headers=self.job_headers())
            second = self.client.post("/internal/deliver", json={"date": "2026-10-05"}, headers=self.job_headers())
        self.assertEqual(first.get_json()["status"], "sent")
        self.assertEqual(second.get_json()["status"], "already_claimed")
        self.assertEqual(post.call_count, 1)

    def test_ai_schema_rejects_unknown_citations(self):
        value = {
            "cards": [
                {
                    "id": "HN:1",
                    "decision": "SAVE",
                    "evidence_ids": ["invented"],
                    **{
                        key: "需要驗證"
                        for key in [
                            "title_zh",
                            "problem",
                            "audience",
                            "alternative",
                            "inference",
                            "unknown",
                            "action",
                            "why",
                            "monetization",
                            "counterevidence",
                        ]
                    },
                }
            ]
        }
        self.assertFalse(founder_app.valid_analysis(value, issue()["signals"]))
        value["cards"][0]["evidence_ids"] = ["HN:1"]
        self.assertTrue(founder_app.valid_analysis(value, issue()["signals"]))
        value["cards"][0]["decision"] = "MAYBE"
        self.assertFalse(founder_app.valid_analysis(value, issue()["signals"]))

    def test_telegram_source_only_tells_user_not_to_read_every_link(self):
        output = founder_app.format_telegram_issue(issue(), "https://founder.example")
        self.assertIn("拾題 / 2026-10-05", output)
        self.assertIn("今日結論：分析尚未完成，先不要逐篇閱讀。", output)
        self.assertIn("1. 【待判斷】A founder problem\n來源：https://example.com/item", output)
        self.assertIn("https://founder.example", output)

    def test_telegram_analyzed_issue_leads_with_one_action(self):
        analyzed = issue()
        analyzed["status"] = "analyzed"
        analyzed["signals"][0]["analysis"] = {
            "title_zh": "值得追蹤的創業問題",
            "decision": "ACT",
            "why": "能驗證目前產品是否解決真實需求。",
            "action": "訪談一位目標使用者並記下一句原話。",
        }

        output = founder_app.format_telegram_issue(analyzed, "https://founder.example")

        self.assertIn("今日只做一件事：執行 #1 的下一步；其餘先略過。", output)
        self.assertIn("1. 【ACT】值得追蹤的創業問題", output)
        self.assertIn("為什麼：能驗證目前產品是否解決真實需求。", output)
        self.assertIn("下一步：訪談一位目標使用者並記下一句原話。", output)

    def test_telegram_analyzed_issue_can_recommend_save_or_skip_all(self):
        analyzed = issue()
        analyzed["status"] = "analyzed"
        analyzed["signals"][0]["analysis"] = {
            "title_zh": "可留待日後追蹤",
            "decision": "SAVE",
            "why": "方向相關，但現在沒有立即驗證價值。",
            "action": "保存到候選題目。",
        }
        self.assertIn("今天不必立即行動；若有餘裕，只保存 #1。", founder_app.format_telegram_issue(analyzed))

        analyzed["signals"][0]["analysis"].update(decision="SKIP", action="不需處理")
        self.assertIn("今天沒有值得投入的題目，全部略過即可。", founder_app.format_telegram_issue(analyzed))


if __name__ == "__main__":
    unittest.main()
