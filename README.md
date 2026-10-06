# News Agent

[![CI](https://github.com/Yili-code/News-Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Yili-code/News-Agent/actions/workflows/ci.yml)

Turn six AI and software-engineering RSS feeds into one deduplicated, 30–45-second English brief delivered to Telegram with Gemini and GitHub Actions.

News Agent is a small, self-hosted Python automation for developers and technical founders who want one high-signal story instead of another long link list. It fetches RSS metadata, removes repeated topics, asks Gemini to select and explain one story, sends the result through the Telegram Bot API, and keeps a short local history for the next run.

> 中文簡介：從六個 AI、軟體工程與新創 RSS 來源擷取內容，去除近期重複主題，再由 Gemini 選出一則值得讀的新聞，整理成 30–45 秒可讀完的英文 Telegram brief。重點不是「收更多新聞」，而是每天少讀一點、理解更深一點。

## Who it is for

- Developers who want a compact AI and software-engineering news digest in Telegram.
- Technical founders who want technical context separated from business inference.
- Learners who want each story connected to an engineering or product decision.

This repository is designed for a single configured Telegram chat. It is not a multi-user newsletter platform, a full-article scraper, or a guarantee that every feed will be available on every run.

## Founder Morning

The repository also contains [`founder/`](founder/README.md), YiLi's private entrepreneurship-research companion. It collects public startup discussions, ranks them against explicit preferences, produces evidence-bounded Chinese analysis, and serves the result through Google Cloud Run and Telegram.

Founder Morning uses an isolated named Firestore database, Secret Manager credentials, and a separate Cloud Run service. Its workflow remains disabled unless `FOUNDER_ENABLED=true`; see [`founder/README.md`](founder/README.md) before configuring it.

## Private Social Editor

The repository also contains [`social/`](social/README.md), a private editorial workflow for Threads and LinkedIn. A scheduled job selects at most one source-grounded story, then Telegram asks YiLi for a genuine reaction. Workers AI may skip it, ask one follow-up, or prepare separate restrained drafts for each platform.

The editor never publishes merely because a model likes a story. A Telegram approval button is required for each publishing action, and no response means no post. Threads and LinkedIn results are stored independently so partial or ambiguous delivery is not represented as full success.

The workflow is disabled unless `SOCIAL_EDITOR_ENABLED=true`. Its Worker, D1 database, Telegram webhook, OAuth tokens, and deployment are separate from the existing digest and Founder Morning services.

## What it does

```text
6 RSS feeds
    ↓
fetch titles, links, and feed summaries
    ↓
filter hardware-only items + deduplicate recent topics
    ↓
Gemini selects one story and writes a structured English brief
    ↓
Telegram HTML message + 10-entry local history
```

The generated brief uses these sections when the source material supports them:

1. `What happened`
2. `Technical core`
3. `Founder perspective`
4. `Why this matters to me`
5. `One action today` — omitted when there is no useful 15-minute action

The prompt explicitly separates reported facts from inference and asks the model not to invent technical details, customer evidence, or revenue claims. Because this is still LLM-generated text based on RSS summaries, important claims should be checked against the linked article.

## News sources

| Focus | Feed |
| --- | --- |
| LLM and NLP research | arXiv `cs.CL` |
| AI industry reporting | The Information |
| AI products and funding | TechCrunch AI |
| Startup business models | TechCrunch Startups |
| Enterprise AI and model evaluation | VentureBeat AI |
| Software architecture and engineering | InfoQ |

`is_hardware_heavy()` removes an item only when it contains hardware or supply-chain terms without software or AI context. The Gemini prompt then gives software engineering, model architecture, agents, product applications, and defensible business implications higher priority.

## Quick start

### Requirements

- Python 3.10 or newer; CI currently runs on Python 3.11
- A [Gemini API key](https://ai.google.dev/gemini-api/docs/api-key)
- A Telegram bot token from [BotFather](https://core.telegram.org/bots/features#botfather)
- The target Telegram chat ID

Gemini usage and GitHub Actions usage are subject to their providers' current pricing and quotas. This project does not claim that every deployment is free.

### 1. Clone and install

```bash
git clone https://github.com/Yili-code/News-Agent.git
cd News-Agent
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS or Linux
source .venv/bin/activate
```

Then install the pinned dependencies:

```bash
python -m pip install -r requirements.txt
```

### 2. Configure credentials

Copy the checked-in example without replacing any existing `.env` file:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# macOS or Linux
cp .env.example .env
```

Fill in the three values:

```env
GEMINI_API_KEY=replace_with_your_key
TELEGRAM_BOT_TOKEN=replace_with_your_bot_token
TELEGRAM_CHAT_ID=replace_with_your_chat_id
```

To find the chat ID, send a message to your new bot and inspect the `chat.id` value returned by Telegram's [`getUpdates`](https://core.telegram.org/bots/api#getupdates) method. For a group, add the bot to the group and send a message there first.

### 3. Verify, then run

```bash
python -m unittest -v
python news_agent.py
```

The second command makes live RSS and Gemini requests and, when a new report is produced, sends a real message to the configured Telegram chat. There is currently no dry-run mode.

## Example output shape

The exact content changes with the selected source. A Telegram message looks like this:

```text
2026-09-28
Linked English article title

What happened
One or two source-grounded sentences.

Technical core
The main mechanism or engineering trade-off.

Founder perspective
One clearly labelled business implication or hypothesis.

Why this matters to me
One concrete product or engineering decision this helps clarify.
```

This is a format example, not a fabricated testimonial or a claim about a particular article. A real Telegram screenshot is intentionally not included until it can be captured from the current English-output version without exposing chat details.

## Automation with GitHub Actions

The repository contains five workflows:

| Workflow | Purpose | Trigger |
| --- | --- | --- |
| `ci.yml` | Run the test suite | Push to `main` and pull requests |
| `daily_news.yml` | Generate and send the digest | `00:00` and `08:00` UTC, plus manual runs |
| `qa_check.yml` | Poll the configured chat and react to news requests | Every 20 minutes, plus manual runs |
| `founder_morning.yml` | Prepare and deliver the private Founder Morning research issue | Disabled unless `FOUNDER_ENABLED=true`; manual or scheduled |
| `social_editor.yml` | Select one candidate for the private Telegram editorial workflow | Disabled unless `SOCIAL_EDITOR_ENABLED=true`; daily or manual |

For your fork:

1. Add `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID` under **Settings → Secrets and variables → Actions**.
2. Enable Actions for the repository.
3. Allow workflows to write repository contents if you want `daily_news.yml` to commit the updated `news_history.json`.
4. Run **Daily Tech News Agent** manually once before relying on the schedule.

GitHub scheduled workflows can start later than the stated cron time. The two digest times correspond to 08:00 and 16:00 in Taiwan (`Asia/Taipei`).

### Q&A status

`qa_agent.py` is an optional single-chat polling interface. It can classify a message as a news request and call the same digest pipeline. Run it locally with:

```bash
python qa_agent.py
```

The hosted `qa_check.yml` workflow is experimental: GitHub-hosted runners are temporary, while the update offset is stored in `telegram_last_update_id.json` and is not committed by that workflow. That boundary must be redesigned before the scheduled Q&A path should be described as durable or exactly-once.

## Configuration and project structure

```text
News-Agent/
├── .github/workflows/
│   ├── ci.yml                 # tests
│   ├── daily_news.yml         # scheduled digest
│   ├── qa_check.yml           # experimental Telegram polling
│   ├── founder_morning.yml     # private research workflow
│   └── social_editor.yml       # private editorial candidate schedule
├── .env.example               # credential names only
├── founder/                   # private Founder Morning app and pipeline
├── social/                    # private Telegram-to-social editorial workflow
├── news_agent.py              # fetch, filter, deduplicate, summarize, deliver
├── qa_agent.py                # optional Telegram request listener
├── news_history.json          # rolling 10-entry deduplication history
├── telegram_last_update_id.json
├── test_news_agent.py
└── requirements.txt
```

Useful customization points in `news_agent.py`:

- `NEWS_SOURCES`: RSS categories and URLs
- `NewsFetcher(limit_per_source=3)`: maximum entries read from each feed per run
- `HARDWARE_ONLY_KEYWORDS` and `SOFTWARE_AI_CONTEXT_KEYWORDS`: first-pass topic filter
- `AgentBrain.generate_daily_report()`: selection, structure, language, and length instructions
- `AgentBrain.history_file`: rolling history used by deduplication

## Known limitations

- Feed availability and feed summaries are controlled by third parties; one failed source does not stop the other sources.
- The agent reads RSS-provided metadata, not necessarily the full linked article.
- Deduplication is heuristic and only compares against the rolling 10-entry history.
- The history file stores only the first 200 characters of each generated report plus selected-source metadata.
- Telegram HTML falls back to plain text if Telegram rejects the markup.
- There is no dry-run, configurable feed file, package release, or stable public API yet.
- The Social Editor has mocked local coverage but no verified production Threads or LinkedIn publication yet.

## Contributing

Focused bug reports and small pull requests are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md), and use the repository's issue forms so a report includes enough evidence to reproduce.

Please never include API keys, bot tokens, private chat IDs, or unredacted Telegram screenshots in an issue or pull request.

## License

No open-source license has been selected yet. Until the maintainer chooses one, normal copyright restrictions apply. This is a real adoption constraint rather than an implied permission to reuse the code.
