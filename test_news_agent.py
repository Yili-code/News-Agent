import os
import tempfile
import unittest
from types import SimpleNamespace

import news_agent


class NewsDeduplicationTests(unittest.TestCase):
    def setUp(self):
        os.environ['GEMINI_API_KEY'] = 'test-key'
        self.brain = news_agent.AgentBrain.__new__(news_agent.AgentBrain)
        self.brain.history_file = os.path.join(tempfile.gettempdir(), 'news_history_test.json')

    def test_filters_exact_duplicate_titles_and_links(self):
        history = [
            {"date": "2026-08-17", "title": "xAI Colossus 2 launch", "link": "https://example.com/colossus"},
            {"date": "2026-08-17", "summary": "xAI Colossus 2 launch and data center expansion."}
        ]
        items = [
            {"title": "xAI Colossus 2 launch", "link": "https://example.com/colossus", "summary": "duplicate"},
            {"title": "xAI Colossus 2 launch and data center expansion", "link": "https://example.com/other", "summary": "similar"},
            {"title": "New chip architecture breakthrough", "link": "https://example.com/new-chip", "summary": "fresh"},
        ]

        filtered = self.brain.dedupe_news_items(items, history)

        self.assertEqual([item['title'] for item in filtered], ['New chip architecture breakthrough'])

    def test_keeps_unique_items_when_history_missing(self):
        items = [
            {"title": "Alpha", "link": "https://example.com/a", "summary": "one"},
            {"title": "Beta", "link": "https://example.com/b", "summary": "two"},
        ]

        filtered = self.brain.dedupe_news_items(items, [])

        self.assertEqual([item['title'] for item in filtered], ['Alpha', 'Beta'])

    def test_filters_exact_same_article_from_same_source(self):
        items = [
            {"title": "Same title", "link": "https://example.com/same", "summary": "duplicate body", "source": "TechX"},
            {"title": "Same title", "link": "https://example.com/same", "summary": "duplicate body", "source": "TechX"},
            {"title": "Fresh title", "link": "https://example.com/fresh", "summary": "new content", "source": "TechX"},
        ]

        filtered = self.brain.dedupe_news_items(items, [])

        self.assertEqual([item['title'] for item in filtered], ['Same title', 'Fresh title'])
        self.assertEqual(len(filtered), 2)

    def test_daily_report_prompt_requires_concise_english_output(self):
        captured = {}

        class FakeModels:
            def generate_content(self, *, model, contents):
                captured['model'] = model
                captured['contents'] = contents
                return SimpleNamespace(text='<b>What happened</b>\nA concise report.')

        self.brain.client = SimpleNamespace(models=FakeModels())
        self.brain.model_name = 'test-model'
        news_items = [{
            'category': 'AI',
            'source': 'Example',
            'title': 'A useful model update',
            'link': 'https://example.com/model-update',
            'summary': 'The update reduces inference cost.',
        }]

        report = self.brain.generate_daily_report(news_items)

        self.assertEqual(report, '<b>What happened</b>\nA concise report.')
        self.assertEqual(captured['model'], 'test-model')
        self.assertIn('將整份簡報寫成自然、精確的英文', captured['contents'])
        self.assertIn('120–180 個英文單字', captured['contents'])
        self.assertIn('<b>Why this matters to me</b>', captured['contents'])


if __name__ == '__main__':
    unittest.main()
