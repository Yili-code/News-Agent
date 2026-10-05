# Contributing to News Agent

News Agent is intentionally small. Contributions are most useful when they improve reliability, source quality, first-run clarity, or the precision of the generated brief without turning the project into a general-purpose publishing platform.

## Before opening an issue

- Search existing issues for the same symptom.
- Remove API keys, bot tokens, chat IDs, usernames, and private message content.
- For a feed problem, include the public feed URL, the time of the failure, and the relevant redacted log line.
- For generated content, distinguish an unsupported factual claim from a style preference and link the source item when possible.

Use the bug report form for reproducible failures and the improvement form for a proposed change with a clear user problem.

## Local setup

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m unittest -v
```

Activation commands differ by shell; see the main [README](README.md#quick-start). Tests must not require live Gemini or Telegram credentials.

## Pull requests

Keep each pull request focused and explain:

1. The user-visible problem.
2. Why the change belongs in this repository's scope.
3. How you verified it.
4. Any behavior, cost, security, or scheduling trade-off.

Before submitting:

```bash
python -m unittest -v
python -m py_compile news_agent.py qa_agent.py test_news_agent.py
```

Do not commit `.env`, credentials, private chat data, or full Telegram update payloads. Avoid claims about accuracy, cost, delivery guarantees, or adoption unless the pull request includes evidence that can be independently checked.

## Current boundaries

- Primary delivery is one configured Telegram chat.
- The digest pipeline uses six RSS feeds and Gemini.
- `news_history.json` is a small rolling state file, not a database.
- The scheduled Q&A workflow does not yet provide durable update-offset persistence across runners.
- License selection and the first stable release remain maintainer decisions.
