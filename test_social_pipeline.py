import json
import unittest
from unittest.mock import patch

from social.pipeline import configure_utf8_output, parse_json_response, select_candidate


class _Models:
    def __init__(self, payload):
        self.payload = payload
        self.last_contents = ""

    def generate_content(self, model, contents):
        self.last_contents = contents
        return type("Response", (), {"text": json.dumps(self.payload, ensure_ascii=False)})()


class _Brain:
    model_name = "test-model"

    def __init__(self, payload):
        self.client = type("Client", (), {"models": _Models(payload)})()

    @staticmethod
    def dedupe_news_items(items):
        return items


class SocialPipelineTests(unittest.TestCase):
    def test_configures_utf8_output_for_windows_dry_runs(self):
        class Output:
            def __init__(self):
                self.options = None

            def reconfigure(self, **options):
                self.options = options

        output = Output()
        with patch("social.pipeline.sys.stdout", output):
            configure_utf8_output()

        self.assertEqual(output.options, {"encoding": "utf-8", "errors": "backslashreplace"})

    def setUp(self):
        self.items = [{
            "category": "AI",
            "source": "Example",
            "title": "A useful change",
            "link": "https://example.com/change",
            "summary": "The source says a specific workflow changed.",
        }]

    def test_parses_fenced_json(self):
        self.assertEqual(parse_json_response('```json\n{"selected_number":0}\n```')["selected_number"], 0)

    def test_model_can_decline_all_candidates(self):
        brain = _Brain({"selected_number": 0, "fact_summary": "", "question_one": "", "question_two": ""})
        self.assertIsNone(select_candidate(self.items, brain))

    def test_selected_candidate_keeps_source_and_questions(self):
        brain = _Brain({
            "selected_number": 1,
            "fact_summary": "來源支持的事實。",
            "question_one": "哪個地方讓你停下來？",
            "question_two": "它改變了哪個產品判斷？",
        })
        candidate = select_candidate(self.items, brain)
        self.assertEqual(candidate["url"], self.items[0]["link"])
        self.assertEqual(len(candidate["id"]), 24)
        self.assertIn("不可假裝讀過全文", brain.client.models.last_contents)

    def test_invalid_selection_is_rejected(self):
        brain = _Brain({
            "selected_number": 2,
            "fact_summary": "事實",
            "question_one": "問題一",
            "question_two": "問題二",
        })
        with self.assertRaises(ValueError):
            select_candidate(self.items, brain)


if __name__ == "__main__":
    unittest.main()
