# Getting Started — OHS Remote Backend

This guide covers everything you need to get the project running locally from scratch. **Follow every section in order** — skipping ahead will not work, because the app refuses to start if any required environment variable is missing.

> **Docker is the only supported path.** Every command in this guide assumes you are running the stack through `docker-compose`. Local (non-Docker) development is intentionally not documented — the Docker setup is what we trust to produce a working environment on any machine.

---

## What you will need accounts for

Before you start, create (or get invited to) all of the following. Each one provides one or more values you will paste into `.env.docker`.

| Account | Used for | Signup |
|---|---|---|
| Google | Gmail App Password for sending email in dev | [https://myaccount.google.com](https://myaccount.google.com) |
| ngrok | Public tunnel so Stripe webhooks can reach your laptop | [https://dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup) |
| Stripe | Payment processing (use **Test mode** — ask the project lead for an invite to the shared project) | [https://dashboard.stripe.com](https://dashboard.stripe.com) |
| OpenAI | AI generation of Safe Job Procedure (SJP) content | [https://platform.openai.com](https://platform.openai.com) |

You will also need to install:

- **Docker Desktop** — [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
- **Git** — [https://git-scm.com/downloads](https://git-scm.com/downloads)

Nothing else is required on your host machine. Python, MySQL, and all system libraries live inside the Docker containers.

---

## Step 1 — Clone and Configure Environment Files

```bash
git clone <repo-url>
cd ohs_remote
```

The app uses two separate env files:

| File | Used by |
|---|---|
| `.env.docker` | The Docker containers (app + ngrok) |
| `.env` | Local development outside Docker |

Copy the examples:

```bash
cp .env.docker.example .env.docker
cp .env.example .env
```

For Docker development (the recommended approach), **you only need to edit `.env.docker`**. The sections below tell you exactly which values to fill in.

---

## Step 2 — Generate a Secret Key

The `SECRET_KEY` is required and has no default. Generate one with:

```bash
openssl rand -hex 32
```

Paste the output into `.env.docker`:

```env
SECRET_KEY=<paste output here>
```

---

## Step 3 — SMTP Setup (Gmail)

The app sends emails (order confirmations, document delivery) via SMTP. Gmail works well for development.

**Gmail does not accept your regular password — you must create an App Password.**

### How to get a Gmail App Password

1. Go to your Google Account: [https://myaccount.google.com](https://myaccount.google.com)
2. Navigate to **Security** → **2-Step Verification** (must be enabled first)
3. At the bottom of the 2-Step Verification page, click **App passwords**
   - Direct link: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Under "Select app" choose **Mail**, under "Select device" choose **Other** and type `OHS Remote`
5. Click **Generate** — copy the 16-character password shown

### Fill in `.env.docker`

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail-address@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx     # The 16-char App Password (spaces are fine)
SMTP_FROM_EMAIL=your-gmail-address@gmail.com
SMTP_FROM_NAME=OHS Remote Dev
```

> **Note:** `SMTP_FROM_EMAIL` should match `SMTP_USER` when using Gmail, otherwise Gmail may reject the send.

---

## Step 4 — ngrok Setup (Webhook Tunnel)

ngrok exposes your local app to the internet, which is required for Stripe to deliver payment webhook events to your machine.

### Install ngrok

- **macOS (Homebrew):**
  ```bash
  brew install ngrok/ngrok/ngrok
  ```
- **All platforms:** Download the binary from [https://ngrok.com/download](https://ngrok.com/download)

### Get your Auth Token

1. Create a free account at [https://dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup)
2. After logging in, go to **Your Authtoken**: [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)
3. Copy the token

### Fill in `.env.docker`

```env
NGROK_AUTHTOKEN=your_token_here
```

When you run `docker-compose up`, ngrok automatically starts and creates a public tunnel to your local app on port 8000.

### Find your current ngrok URL

Once running, open [http://localhost:4040](http://localhost:4040) in your browser. You will see something like:

```
https://abcd-1234-56ef.ngrok-free.app
```

**This URL changes every time you restart Docker.** You will need to update the Stripe webhook (Step 5) each time it changes.

### Add your ngrok URL to CORS

Also add your ngrok URL to `ALLOWED_ORIGINS` in `.env.docker` so the frontend can communicate through the tunnel:

```env
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080,https://abcd-1234-56ef.ngrok-free.app
```

---

## Step 5 — Stripe Setup

You have been invited to the shared Stripe project. Use the test mode keys (they start with `sk_test_` and `pk_test_`).

### Get your API Keys

1. Log in at [https://dashboard.stripe.com](https://dashboard.stripe.com)
2. Make sure you are in **Test mode** (toggle in the top-right corner)
3. Go to **Developers** → **API keys**: [https://dashboard.stripe.com/test/apikeys](https://dashboard.stripe.com/test/apikeys)
4. Copy the **Secret key** (`sk_test_...`) and **Publishable key** (`pk_test_...`)

### Create a Webhook Endpoint

Stripe needs to know where to send payment events. You must create a webhook pointing to your ngrok URL.

1. In the Stripe dashboard go to **Developers** → **Webhooks**: [https://dashboard.stripe.com/test/webhooks](https://dashboard.stripe.com/test/webhooks)
2. Click **Add endpoint**
3. Set the **Endpoint URL** to your ngrok URL + the webhook path:
   ```
   https://abcd-1234-56ef.ngrok-free.app/api/v1/payments/webhook
   ```
4. Under **Events to listen to**, select:
   - `checkout.session.completed`
   - `payment_intent.payment_failed`
5. Click **Add endpoint**
6. On the endpoint detail page, click **Reveal** under **Signing secret** and copy the `whsec_...` value

### Fill in `.env.docker`

```env
STRIPE_API_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Updating the Webhook URL after a restart

Every time Docker restarts, ngrok gets a new URL. You must update the webhook endpoint:

1. Open [http://localhost:4040](http://localhost:4040) to find the new ngrok URL
2. In the Stripe dashboard, go to **Developers** → **Webhooks**
3. Click your existing endpoint → **Update details**
4. Replace the URL with the new ngrok URL, keeping `/api/v1/payments/webhook` at the end
5. The `STRIPE_WEBHOOK_SECRET` (`whsec_...`) stays the same — do not regenerate it

---

## Step 6 — OpenAI API Key

The SJP (Safe Job Procedure) generation feature calls the OpenAI API. `OPENAI_API_KEY` is a **required** setting in `app/config.py` — the app will refuse to start without it, even if you do not plan on using SJP generation yourself.

### Get an API key

1. Go to [https://platform.openai.com](https://platform.openai.com) and sign in (or create an account)
2. Click your profile (top-right) → **View API keys**, or go directly to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
3. Click **Create new secret key**, give it a name like `ohs-remote-dev`, and copy the key — you will not be able to see it again
4. If your account has no free credit, add a small amount of prepaid credit at [https://platform.openai.com/settings/organization/billing](https://platform.openai.com/settings/organization/billing). The default model is `gpt-5-mini`, which is cheap — a few dollars lasts a long time in development.

### Fill in `.env.docker`

```env
OPENAI_API_KEY=sk-...
```

The other `LLM_*` variables in `.env.docker` have sensible defaults — leave them commented out unless you have a reason to change them.

---

## Step 7 — Start the App

Once all values are filled in `.env.docker`, start everything:

```bash
docker-compose up --build
```

This starts three containers:
- **mysql** — MySQL 8.0 database (port 3307)
- **app** — FastAPI backend (port 8000), runs migrations automatically on startup
- **ngrok** — Public tunnel (dashboard at port 4040)

### Verify it's working

| URL | What it is |
|---|---|
| http://localhost:8000/docs | Swagger API docs |
| http://localhost:8000/api/v1/health | Health check |
| http://localhost:4040 | ngrok dashboard (shows your public URL) |

### Useful Docker commands

```bash
docker-compose logs -f app       # Follow app logs
docker-compose logs -f ngrok     # Follow ngrok logs
docker-compose down              # Stop all containers
docker-compose up                # Start again (no rebuild)
docker-compose up --build        # Rebuild after dependency changes
```

---

## Step 8 — Seed the Database

Alembic migrations run automatically when the `app` container starts. You only need to seed the initial list of plans one time, after the containers are up:

```bash
docker-compose exec app python scripts/seed_plans.py
```

This creates the available service plans (Basic, Comprehensive, Industry-Specific) in the database. Running it a second time is safe — it is idempotent.

---

## Summary of `.env.docker` Values to Fill In

| Variable | Where to get it |
|---|---|
| `SECRET_KEY` | `openssl rand -hex 32` |
| `SMTP_USER` | Your Gmail address |
| `SMTP_PASSWORD` | Gmail App Password ([link](https://myaccount.google.com/apppasswords)) |
| `SMTP_FROM_EMAIL` | Same as `SMTP_USER` |
| `NGROK_AUTHTOKEN` | ngrok dashboard ([link](https://dashboard.ngrok.com/get-started/your-authtoken)) |
| `STRIPE_API_KEY` | Stripe dashboard → Developers → API keys ([link](https://dashboard.stripe.com/test/apikeys)) |
| `STRIPE_PUBLISHABLE_KEY` | Same page as above |
| `STRIPE_WEBHOOK_SECRET` | Stripe dashboard → Developers → Webhooks → your endpoint → Signing secret |
| `OPENAI_API_KEY` | OpenAI dashboard → API keys ([link](https://platform.openai.com/api-keys)) |
| `ALLOWED_ORIGINS` | Add your ngrok URL from [http://localhost:4040](http://localhost:4040) after starting |

Everything else in `.env.docker` is pre-configured for local development and does not need to be changed.

---

## Troubleshooting

### App fails to start — missing environment variable

The app will refuse to start if any required variable is missing or still set to a placeholder like `...`. Check the Docker logs:

```bash
docker-compose logs app
```

Look for a `ValidationError` from Pydantic — it will name the missing field.

### Can't connect to the database

```bash
docker-compose ps          # Check all containers are running
docker-compose restart mysql
```

Also check that `DATABASE_URL` in `.env.docker` is set to the internal Docker hostname:
```env
DATABASE_URL=mysql+pymysql://ohs_dev_user:ohs_dev_password@mysql:3306/ohs_remote_dev
```

### Email not sending

- Confirm 2-Step Verification is enabled on your Google account
- Confirm you used the App Password (not your regular Gmail password)
- The App Password is 16 characters, spaces are irrelevant — `xxxx xxxx xxxx xxxx` and `xxxxxxxxxxxxxxxx` are the same

### Stripe webhook not receiving events

- Confirm the ngrok container is running: check [http://localhost:4040](http://localhost:4040)
- Confirm the webhook URL in Stripe includes the full path: `.../api/v1/payments/webhook`
- After restarting Docker, always update the webhook URL in the Stripe dashboard
- In the Stripe dashboard, the webhook page shows recent delivery attempts and their status — use this to debug

### ngrok tunnel not starting

- Verify `NGROK_AUTHTOKEN` is set correctly in `.env.docker`
- Confirm the token is from your account at [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)
- Free ngrok accounts allow one active tunnel at a time — close any other running ngrok sessions

### OpenAI errors when generating an SJP

- Confirm `OPENAI_API_KEY` is set and starts with `sk-`
- Check your OpenAI billing — new accounts without credit get `insufficient_quota` errors
- Watch `docker-compose logs -f app` while triggering the SJP endpoint to see the exact error from the OpenAI SDK

---

For a full catalogue of failure modes and fixes, see **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)**.
