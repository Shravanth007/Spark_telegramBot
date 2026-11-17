# Personal AI Telegram Bot

A self-hosted Telegram bot that acts as your personal AI assistant. Deployed on Vercel serverless — no server to maintain, runs 24/7 for free.

**What it can do:**
- GitHub — manage repos, issues, PRs, branches, commits, collaborators, releases (26 tools)
- Gmail — read, send, search, reply, forward, archive, draft emails (17 tools)
- Web — search the internet (DuckDuckGo, no API key), summarize any URL
- Notes — save, retrieve, and delete personal notes

**How it works:** You message the bot on Telegram → Vercel receives it → the LLM decides which tool to call → tools execute against GitHub/Gmail APIs → results come back to the LLM → you get a natural language reply.

---

## Architecture

```
User (Telegram)
     ↓
/api/webhook  (Vercel serverless)
     ↓
agent.py  ←→  OpenRouter LLM
     ↓              ↑
Tool Routing     Tool Results
     ↓
tools/
├── github_tool.py   (GitHub REST API)
├── gmail_tool.py    (Gmail API via OAuth2)
├── web_tool.py      (DuckDuckGo + URL fetch)
└── notes_tool.py    (stored in Vercel KV)
     ↓
Vercel KV (Redis) — stores Gmail tokens + notes
```

### Tool Routing

Every user message is inspected for category keywords before hitting the LLM. Instead of sending all 49 tool definitions on every request, the agent routes to only the relevant subset:

- Message contains "issue", "pr", "repo" → GitHub tools only
- Message contains "email", "inbox", "gmail" → Gmail tools only
- Message contains "search", "article", "https://" → Web tools only
- Message contains "note", "notes", "save note" → Notes tools only
- No keywords matched → all tools sent (LLM decides)

On subsequent rounds within the same agent loop (when the LLM is chaining tool calls), all tools are available so the LLM can freely cross categories.

### Agent Loop

```
User message
    → Build messages (system + history + user)
    → Route tools by keyword
    → Call LLM
    → LLM returns tool_calls?
        YES → execute tools → append results → loop (up to 5 rounds)
        NO  → return text reply → save to history
```

Multi-turn conversation history is kept in-memory per chat ID (last 20 messages). It resets on Vercel cold starts, which is fine for a personal bot.

---

## Prerequisites

You need accounts on these services (all free):

| Service | Purpose | Cost |
|---|---|---|
| Telegram | Bot interface | Free |
| OpenRouter | LLM API (free models) | Free |
| GitHub | Code/repo management | Free |
| Google Cloud | Gmail OAuth | Free |
| Vercel | Hosting + KV storage | Free |

---

## Step-by-Step Setup

### 1. Telegram Bot Token

> **Tip:** You can use a temporary/throwaway email (e.g. [temp-mail.org](https://temp-mail.org)) to create a fresh Telegram account for the bot if you don't want to use your personal one.

1. Open Telegram and message **@BotFather**
2. Send `/newbot`
3. Choose a name and username (username must end in `bot`)
4. Copy the **bot token** — looks like `123456789:ABCdef...`

Save this as `TELEGRAM_BOT_TOKEN`.

**Get your Telegram chat ID:**
1. Message **@userinfobot** on Telegram
2. It will reply with your numeric chat ID (e.g. `987654321`)

Save this as `ALLOWED_CHAT_IDS` (comma-separated if multiple users).

---

### 2. OpenRouter API Key (Free LLM)

OpenRouter provides access to free LLM models — no credit card required for free tier.

1. Go to [openrouter.ai](https://openrouter.ai) and sign up
2. Go to **Keys** → **Create Key**
3. Copy the key — looks like `sk-or-v1-...`

Save this as `OPENROUTER_API_KEY`.

The bot uses these free models with automatic fallback:
- `nvidia/nemotron-3-super-120b-a12b:free`
- `meta-llama/llama-3.3-70b-instruct:free`
- `mistralai/mistral-small-3.1-24b-instruct:free`

---

### 3. GitHub Personal Access Token

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. Click **Generate new token (classic)**
3. Give it a name (e.g. "telegram-bot")
4. Select scopes: `repo` (full control of private repos) — this covers everything
5. Click **Generate token**
6. Copy the token — looks like `ghp_...`

Save this as `GITHUB_TOKEN`.

Also set `GITHUB_DEFAULT_USER` to your GitHub username (e.g. `johndoe`). This lets you say "list my repos" or "create issue in my-project" without always specifying the full `owner/repo`.

Optionally set `GITHUB_DEFAULT_REPO` if you have one repo you work with most (e.g. `johndoe/my-project`).

---

### 4. Google Cloud (Gmail OAuth2)

This is the most involved step. Gmail requires OAuth2 — the bot will never see your password.

#### 4a. Create a Google Cloud Project

> **Tip:** You can use a throwaway Google account here. The bot only needs access to the Gmail account that authorizes it via `/login`.

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown → **New Project**
3. Name it anything (e.g. `telegram-bot`) → **Create**

#### 4b. Enable the Gmail API

1. In your project, go to **APIs & Services → Library**
2. Search for **Gmail API**
3. Click **Enable**

#### 4c. Configure the OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. Choose **External** → **Create**
3. Fill in:
   - App name: anything (e.g. `My Telegram Bot`)
   - User support email: your email
   - Developer contact: your email
4. Click **Save and Continue** through Scopes (skip adding scopes here)
5. On the **Test users** step, click **Add users** and add the Gmail address you want the bot to access
6. Click **Save and Continue** → **Back to Dashboard**

#### 4d. Create OAuth2 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth 2.0 Client ID**
3. Application type: **Web application**
4. Name: anything
5. Under **Authorized redirect URIs**, add:
   ```
   https://your-app.vercel.app/api/oauth/callback
   ```
   (You'll fill in your actual Vercel URL after deploying — come back and update this)
6. Click **Create**
7. Copy the **Client ID** and **Client Secret**

Save these as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

---

### 5. Deploy to Vercel

#### 5a. Install Vercel CLI

```bash
npm install -g vercel
```

#### 5b. Clone / download this repo

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

#### 5c. Deploy

```bash
vercel --prod
```

Follow the prompts. After deployment, note your production URL:
```
https://your-app.vercel.app
```

---

### 6. Set Up Vercel KV (Redis)

The bot uses Vercel KV (powered by Upstash Redis) to store Gmail tokens and notes.

1. Go to your project in the **Vercel Dashboard**
2. Click **Storage** tab → **Create Database**
3. Choose **KV** → select a region → **Create**
4. Click **Connect Project** to link it to your deployment

Vercel automatically injects these environment variables into your project:
- `KV_REST_API_URL`
- `KV_REST_API_TOKEN`
- `KV_URL`
- `REDIS_URL`
- `KV_REST_API_READ_ONLY_TOKEN`

---

### 7. Set Environment Variables in Vercel

Go to your project in **Vercel Dashboard → Settings → Environment Variables** and add:

| Variable | Value | Notes |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | `123456789:ABCdef...` | From BotFather |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` | From openrouter.ai |
| `GITHUB_TOKEN` | `ghp_...` | GitHub PAT |
| `GITHUB_DEFAULT_USER` | `your-github-username` | Your GitHub username |
| `GITHUB_DEFAULT_REPO` | `username/repo` | Optional default repo |
| `GOOGLE_CLIENT_ID` | `....apps.googleusercontent.com` | From Google Cloud |
| `GOOGLE_CLIENT_SECRET` | `GOCSPX-...` | From Google Cloud |
| `BOT_BASE_URL` | `https://your-app.vercel.app` | No trailing slash |
| `ALLOWED_CHAT_IDS` | `987654321` | Your Telegram chat ID |

Set all of these to **All Environments** (Production, Preview, Development).

After adding them, redeploy:
```bash
vercel --prod
```

---

### 8. Update Google OAuth Redirect URI

Now that you have your Vercel URL:

1. Go back to **Google Cloud Console → APIs & Services → Credentials**
2. Edit your OAuth 2.0 Client ID
3. Under **Authorized redirect URIs**, add (or update):
   ```
   https://your-app.vercel.app/api/oauth/callback
   ```
4. Save

---

### 9. Register Telegram Webhook

Tell Telegram where to send messages:

```bash
curl "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook?url=https://your-app.vercel.app/api/webhook"
```

Expected response:
```json
{"ok": true, "result": true, "description": "Webhook was set"}
```

---

### 10. Connect Gmail

1. Open Telegram and message your bot
2. Send `/login`
3. The bot sends you a Google OAuth link — click it
4. Authorize in the browser (you'll see the Gmail account you added as a test user)
5. Google redirects back to your bot's callback URL
6. You get a Telegram confirmation: "Gmail connected successfully!"

---

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and feature list |
| `/login` | Connect your Gmail account |
| `/logout` | Disconnect Gmail |

For everything else, just type naturally:

```
list my repos
create issue titled Fix login bug in my-project
show open PRs in owner/repo
read my last 5 emails
search emails from alice
send email to bob@example.com about the meeting
save note: meeting at 3pm tomorrow
search for latest Python 3.13 features
summarize https://example.com/article
```

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from BotFather |
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key for LLM access |
| `GITHUB_TOKEN` | Yes | GitHub personal access token (repo scope) |
| `GITHUB_DEFAULT_USER` | Yes | Your GitHub username |
| `GITHUB_DEFAULT_REPO` | No | Default repo in `owner/repo` format |
| `GOOGLE_CLIENT_ID` | Yes (Gmail) | Google OAuth2 client ID |
| `GOOGLE_CLIENT_SECRET` | Yes (Gmail) | Google OAuth2 client secret |
| `BOT_BASE_URL` | Yes (Gmail) | Your Vercel URL, no trailing slash |
| `ALLOWED_CHAT_IDS` | No | Comma-separated Telegram chat IDs. Empty = allow all |
| `KV_REST_API_URL` | Yes | Auto-set by Vercel KV |
| `KV_REST_API_TOKEN` | Yes | Auto-set by Vercel KV |

---

## Project Structure

```
├── agent.py                  # LLM agent loop, tool routing, conversation memory
├── vercel.json               # Vercel routing config
├── requirements.txt          # Python dependencies
├── .env.example              # Template for environment variables
├── api/
│   ├── webhook.py            # Telegram webhook handler + bot commands
│   └── oauth/
│       └── callback.py       # Google OAuth2 redirect handler
└── tools/
    ├── __init__.py
    ├── github_tool.py        # GitHub REST API (26 tools)
    ├── gmail_tool.py         # Gmail API via OAuth2 (17 tools)
    ├── web_tool.py           # DuckDuckGo search + URL fetch
    ├── notes_tool.py         # Personal notes (stored in KV)
    └── kv_store.py           # Vercel KV (Redis) wrapper
```

---

## Customizing the Bot

### Change the bot's name / personality

Edit `SYSTEM_PROMPT` in `agent.py`. The prompt controls how the bot introduces itself, its tone, and its behavior rules.

### Add more free LLM models

Edit the `MODELS` list in `agent.py`. Any model available on OpenRouter can be added. Free models are marked `:free` in their model ID.

### Add new tools

1. Write the tool function in the appropriate `tools/` file (or create a new one)
2. Import it in `agent.py`
3. Add a tool definition to the `TOOLS` list (OpenAI function-calling format)
4. Add an entry to `TOOL_DISPATCH` mapping the tool name to the function
5. Add relevant keywords to `_ROUTE_KEYWORDS` so the router includes it

### Restrict access

Set `ALLOWED_CHAT_IDS` to a comma-separated list of Telegram chat IDs. Anyone not on the list gets "You are not authorized to use this bot." Leave empty to allow everyone.

---

## Troubleshooting

**Bot doesn't respond**
- Verify webhook is set: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
- Check Vercel function logs in the dashboard

**Gmail not working**
- Make sure you added your Gmail address as a test user in Google Cloud Console
- Verify `BOT_BASE_URL` is set correctly (no trailing slash)
- Verify the redirect URI in Google Cloud exactly matches `BOT_BASE_URL/api/oauth/callback`
- Send `/logout` then `/login` to re-authenticate

**GitHub errors**
- Verify `GITHUB_TOKEN` has `repo` scope
- Check the token hasn't expired (classic tokens can have expiry dates)

**LLM not responding**
- OpenRouter free models can have rate limits. The bot automatically tries the next model in the fallback list.
- Check `OPENROUTER_API_KEY` is set correctly in Vercel environment variables

**KV / notes not working**
- Make sure the Vercel KV store is linked to your project
- Redeploy after linking: `vercel --prod`

---


