# Private Social Editor

Private Social Editor turns one source-grounded news candidate into an optional, personal Threads and LinkedIn post. It is deliberately not an autonomous content bot:

1. A scheduled Python job selects at most one candidate.
2. Telegram asks YiLi two story-specific questions.
3. Workers AI decides whether the response contains a useful personal angle.
4. It skips, asks at most one follow-up, or creates two restrained drafts.
5. Nothing is published until YiLi presses an explicit approval button.

No response means no post. An ambiguous publishing result is recorded as `unknown` and is not retried automatically.

Only one conversation can be active at a time. A scheduled run returns `busy` instead of replacing an unanswered question or unapproved draft; inactive conversations expire after 20 hours when the next candidate arrives.

## Architecture

```text
GitHub Actions
  social/pipeline.py
    ├─ existing RSS fetcher and history deduplication
    ├─ Gemini candidate selection
    └─ authenticated candidate submission
                  ↓
Cloudflare Worker + Workers AI + D1
    ├─ Telegram webhook interview
    ├─ editorial decision and revision
    ├─ explicit approval gate
    └─ Threads / LinkedIn publishers
```

The service stores source metadata, YiLi's response, drafts, workflow state, processed Telegram update IDs, and platform publication receipts. It does not store API tokens in D1.

## Local verification

Node 24 and Python dependencies from the repository root are required.

```powershell
node --check social/worker.mjs
node --test social/tests/worker.test.mjs
python -m unittest -v test_social_pipeline.py
```

To inspect candidate selection without contacting Telegram or either social platform:

```powershell
python social/pipeline.py --dry-run
```

This still makes live RSS and Gemini calls. It only prevents the candidate from being submitted to the Worker.

## Cloudflare setup

Copy `social/wrangler.example.toml` to `social/wrangler.toml`, create a D1 database, insert its ID, and apply the migration. Keep `wrangler.toml` and `.dev.vars` local.

Configure these Worker secrets:

| Secret | Purpose |
| --- | --- |
| `JOB_TOKEN` | Authenticates the scheduled candidate submission |
| `TELEGRAM_BOT_TOKEN` | Sends questions and receives callback actions |
| `TELEGRAM_OWNER_CHAT_ID` | Rejects messages and actions from every other chat |
| `TELEGRAM_WEBHOOK_SECRET` | Verifies Telegram webhook requests |
| `THREADS_ACCESS_TOKEN` | Publishes only after approval |
| `LINKEDIN_ACCESS_TOKEN` | Publishes only after approval |
| `LINKEDIN_PERSON_URN` | Identifies the authenticated LinkedIn member |

Set `LINKEDIN_VERSION` in `wrangler.toml` to a currently supported `YYYYMM` API version. Access-token lifetime and renewal differ by platform and must be monitored rather than assumed permanent.

The Threads app needs the official content-publishing permission, and the LinkedIn app needs permission to post for the authenticated member (`w_member_social`). Confirm the granted scopes from the real access tokens; creating an app alone does not prove publication access.

Deploy the Worker, then register this webhook URL with Telegram:

```text
https://YOUR-WORKER.workers.dev/telegram/webhook
```

When calling Telegram `setWebhook`, send the same random value as `secret_token` that was stored in `TELEGRAM_WEBHOOK_SECRET`. Do not put the bot token, webhook secret, or platform access tokens in the repository, command output, screenshots, or GitHub variables.

## GitHub Actions setup

The `social_editor.yml` workflow stays disabled unless the repository variable `SOCIAL_EDITOR_ENABLED` is exactly `true`.

Configure:

| Type | Name | Value |
| --- | --- | --- |
| Variable | `SOCIAL_EDITOR_ENABLED` | `true` only after the end-to-end test |
| Variable | `SOCIAL_EDITOR_URL` | Worker HTTPS origin |
| Secret | `SOCIAL_EDITOR_JOB_TOKEN` | Same value as Worker `JOB_TOKEN` |
| Secret | `GEMINI_API_KEY` | Candidate selection only |

The schedule runs at 07:30 in Taiwan (`23:30` UTC on the previous date). GitHub Actions schedules may be delayed.

## Required live checks before enabling the schedule

1. Confirm `/health` returns `{"ok":true}`.
2. Register the Telegram webhook with its secret token.
3. Submit one candidate manually and confirm it reaches the private owner chat only.
4. Reply with an uninterested answer and confirm no draft or publication is created.
5. Reply with a meaningful answer, inspect both drafts, and press `skip`.
6. Use non-production test text to approve Threads only; verify the returned Threads post manually.
7. Repeat for LinkedIn only and verify the LinkedIn post manually.
8. Approve both once and confirm D1 contains one publication receipt per platform.
9. Only then set `SOCIAL_EDITOR_ENABLED=true`.

Local and mocked tests do not prove that OAuth scopes, current API versions, token renewal, Telegram delivery, or public post creation work with the real accounts.

## Editorial boundaries

- One candidate per scheduled run.
- At most one follow-up question.
- No generated personal experience or stronger conclusion than the response supports.
- Threads draft: at most 500 characters.
- LinkedIn draft: at most 1,600 characters.
- No forced headings, lists, calls to action, hashtags, emoji, or motivational ending.
- Drafts live in D1; social platforms are contacted only after approval.
- Platform results are independent. Partial success is reported as partial success.
