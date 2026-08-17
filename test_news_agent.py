import os
import tempfile
import unittest

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


if __name__ == '__main__':
    unittest.main()
