# AI Hardware Digest

Daily email digest of arXiv papers on AI hardware, ML systems, accelerators, and adjacent topics. Runs on GitHub Actions, ranked by Gemini 2.5 Flash. **$0/month, end to end.**

## Why it's free

| Component        | Service                  | Cost                                       |
|------------------|--------------------------|--------------------------------------------|
| Paper source     | arXiv API                | Free, no key needed                        |
| LLM ranking      | Google Gemini 2.5 Flash  | Free tier: ~1,500 req/day (we use 1/day)   |
| Email delivery   | Gmail SMTP               | Free                                       |
| Scheduling/hosting | GitHub Actions         | Free for public repos; 2,000 min/mo private |

The Gemini free tier on AI Studio doesn't require a credit card or data-sharing opt-in. As long as you stay under 1,500 requests/day on Gemini 2.5 Flash, you pay nothing. This digest makes **one** request per day.

## How it works

1. **Fetch** — Pulls the last 48h of submissions from `cs.AR`, `cs.DC`, `cs.NE`, `cs.LG`, `cs.AI`, `cs.PF`, `cs.OS`, `eess.SP`.
2. **Keyword filter** — Drops papers with no hardware/systems keywords. Generous to keep recall high.
3. **LLM rank** — Sends remaining candidates to Gemini in one batched call. Each paper gets a 0-10 relevance score and a one-line summary.
4. **Email** — Top 10 scoring ≥5 get HTML-formatted into a Gmail digest.
5. **Dedupe** — `seen.json` is committed back to the repo so the same paper never appears twice.

## Setup

### 1. Push this repo to your GitHub

### 2. Get a Gemini API key (free)

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with a Google account
3. Click "Create API key" → choose "Create API key in new project"
4. Copy the key (starts with `AIza...`)

No credit card. No billing setup. Just a key.

### 3. Create a Gmail app password

You need a Gmail app password (not your regular Google password). Requires 2FA on your account.

1. Go to https://myaccount.google.com/apppasswords
2. Generate one for "Mail" — you get a 16-char string like `abcd efgh ijkl mnop`
3. Copy it (spaces are fine, both work)

### 4. Add GitHub secrets

Repo → Settings → Secrets and variables → Actions → New repository secret. Add:

- `GEMINI_API_KEY` — your Gemini key from step 2
- `GMAIL_ADDRESS` — the Gmail you'll send from
- `GMAIL_APP_PASSWORD` — the 16-char app password from step 3
- `RECIPIENT_EMAIL` — where to send the digest (omit to send to yourself)

### 5. Adjust the schedule

`.github/workflows/digest.yml` runs at 14:00 UTC daily. Edit the cron line:
- `0 14 * * *` = 7am PT / 10am ET (during PDT)
- `0 13 * * *` = 6am PT / 9am ET (during PST)

### 6. Test it

Push to GitHub, then Actions → "Daily AI Hardware Digest" → "Run workflow". Check your inbox.

## Running locally

```bash
export GEMINI_API_KEY=AIza...
export GMAIL_ADDRESS=you@gmail.com
export GMAIL_APP_PASSWORD="abcd efgh ijkl mnop"

# Test without sending email
python -m digest.main --dry-run

# Send for real
python -m digest.main
```

No `pip install` needed — uses Python stdlib only.

## Tuning

- **Scope** — Edit `CATEGORIES` in `digest/fetch.py` to add/remove arXiv categories.
- **Keywords** — Edit `HARDWARE_KEYWORDS` in `digest/keyword_filter.py`. Be generous; the LLM ranker does the precise sorting.
- **Top N / threshold** — Tweak `--top-n` and the `score >= 5` cutoff in `digest/rank.py`.
- **Prompt** — Edit `SYSTEM_PROMPT` in `digest/rank.py` to bias toward what you care about most (e.g. more weight on neuromorphic, less on LLM serving).
- **Switch model** — Want a different LLM? `digest/rank.py` is a single file; swap the endpoint and request body for any provider with a free tier (Mistral, Groq, OpenRouter free models, etc.).

## Why these choices

- **GitHub Actions** over local cron: laptop sleep won't kill it, and the run history is visible.
- **Gmail SMTP** over Gmail API: no OAuth, no token refresh, one secret.
- **arXiv API** directly: no key, generous rate limits, clean Atom XML.
- **Gemini 2.5 Flash** for ranking: free tier with no card, smart enough for relevance scoring, fast.
- **Keyword pre-filter + LLM rank**: keyword pass is free and kills 70%+ of noise; LLM handles judgment calls.
- **stdlib only**: no dependencies means nothing to break when packages update.

## A note on free tiers

The Gemini free tier terms (as of May 2026) allow Google to use your API inputs to improve their models. For a digest that sends paper abstracts (already public on arXiv), this is fine. If you'd rather keep prompts private, you can switch to paid Gemini, Claude, or run a local model via Ollama — see `digest/rank.py`.
