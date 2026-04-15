# Troubleshooting

Symptoms and fixes for the failure modes you are most likely to hit on this project. Start at the top — the early sections cover the things that break most often during first-time setup.

If none of this helps, grab the output of `docker-compose logs --tail=200 app` and `docker-compose ps` before asking for help.

---

## 1. App refuses to start — `ValidationError` from Pydantic

**Symptom** — `docker-compose up` brings up MySQL, then the `app` container exits with a traceback that ends in something like:

```
pydantic_core._pydantic_core.ValidationError: 3 validation errors for Settings
openai_api_key
  Field required [type=missing, ...]
stripe_webhook_secret
  Field required [type=missing, ...]
```

**Cause** — `app/config.py` declares every required setting as `Field(...)` with no default. The app fails fast at startup if any of them is missing or left as a placeholder like `...` or `sk_test_...`.

**Fix** — Open `.env.docker` and confirm every variable listed below has a real value:

- `SECRET_KEY` — generate with `openssl rand -hex 32`
- `DATABASE_URL` — must be `mysql+pymysql://ohs_dev_user:ohs_dev_password@mysql:3306/ohs_remote_dev` for Docker mode
- `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`
- `STRIPE_API_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`
- `OPENAI_API_KEY`

After editing the env file, restart the container:

```bash
docker-compose up -d --force-recreate app
```

`docker-compose restart app` alone is sometimes not enough — compose only re-reads `env_file:` on container creation.

---

## 2. Port conflict — `address already in use`

**Symptom** —

```
Error response from daemon: Ports are not available: listen tcp 0.0.0.0:8000: bind: address already in use
```

**Cause** — Another process on your laptop is holding port 8000, 3307, or 4040.

**Fix** —

```bash
lsof -i :8000        # find the offending process
kill -9 <PID>
```

Most commonly this is a previous `docker-compose` run that did not shut down cleanly. `docker-compose down` usually resolves it.

---

## 3. "Can't connect to MySQL server on 'mysql'"

**Symptom** — `app` container logs a connection error on startup.

**Possible causes and fixes:**

1. **MySQL has not finished initializing yet.** First-run MySQL takes ~20–30 seconds. The `app` service has `depends_on: mysql: condition: service_healthy`, so this should not actually happen. If it does, wait and try again.
2. **Wrong `DATABASE_URL` in `.env.docker`** — inside the Docker network the host is `mysql` (the service name), not `localhost`:
   ```env
   DATABASE_URL=mysql+pymysql://ohs_dev_user:ohs_dev_password@mysql:3306/ohs_remote_dev
   ```
3. **DB volume got into a weird state** (e.g. you renamed the DB or user in compose and the old data is still there). Nuke it:
   ```bash
   docker-compose down -v
   docker-compose up --build
   ```
   **Warning:** `down -v` deletes the MySQL volume and all data in it. You will need to re-run `python scripts/seed_plans.py` afterwards.

---

## 4. Alembic — "Target database is not up to date" or migration head conflicts

**Symptom** — Alembic refuses to run because there are multiple heads, or because the DB is on a revision that does not exist in `alembic/versions/`.

**Fix (multiple heads, typical after a merge)** —

```bash
docker-compose exec app alembic heads     # shows all heads
docker-compose exec app alembic merge -m "merge heads" <head_a> <head_b>
docker-compose exec app alembic upgrade head
```

**Fix (fresh DB is easier if you have no local data you care about)** —

```bash
docker-compose down -v
docker-compose up --build
docker-compose exec app python scripts/seed_plans.py
```

---

## 5. Gmail rejects SMTP authentication

**Symptom** — Sending an email errors with `535-5.7.8 Username and Password not accepted` or `Application-specific password required`.

**Cause** — Gmail does not accept your regular account password for SMTP. You must use a 16-character **App Password**.

**Fix** —

1. Enable 2-Step Verification on your Google account if you haven't already.
2. Generate an App Password at https://myaccount.google.com/apppasswords (pick **Mail** / **Other**).
3. Paste the 16-character password into `SMTP_PASSWORD` in `.env.docker` (spaces are optional — `xxxx xxxx xxxx xxxx` and `xxxxxxxxxxxxxxxx` are treated the same).
4. Make sure `SMTP_FROM_EMAIL` matches `SMTP_USER` — Gmail rejects mismatched From addresses.
5. Restart the app: `docker-compose up -d --force-recreate app`.

---

## 6. Stripe webhook never fires

**Symptom** — You complete a Stripe Checkout successfully but the order stays in `draft` / `pending`, no document is generated, no email is sent.

**Checks, in order:**

1. **Is ngrok running?** Open http://localhost:4040 — you should see a live `https://*.ngrok-free.app` forwarding URL. If the page is blank, check `docker-compose logs -f ngrok` for an auth error (fix by putting a valid `NGROK_AUTHTOKEN` in `.env.docker`).
2. **Is the Stripe webhook endpoint pointing at the current ngrok URL?** The ngrok URL rotates on every restart. Update it at https://dashboard.stripe.com/test/webhooks → your endpoint → **Update details**. The URL must end with `/api/v1/payments/webhook`.
3. **Is the webhook signing secret correct?** In Stripe, click your endpoint → **Reveal** under **Signing secret** and confirm it matches `STRIPE_WEBHOOK_SECRET` in `.env.docker`. This value **does not change** when you update the endpoint URL — don't regenerate it.
4. **Look at Stripe's delivery log.** In the Stripe dashboard, on the webhook endpoint page, you can see every delivery attempt and the HTTP response your backend returned. A `400` with "signature verification failed" means the signing secret is wrong; a connection error means ngrok is not forwarding.

---

## 7. OpenAI / SJP generation errors

**Symptom** — Triggering an SJP generation returns 500, or the job transitions to `failed`. App logs show an error from the `openai` SDK.

**Common causes:**

- **`Invalid API key`** — `OPENAI_API_KEY` is wrong or unset. It should start with `sk-`. Paste a fresh one from https://platform.openai.com/api-keys.
- **`insufficient_quota`** — your OpenAI account has no credit. Add some at https://platform.openai.com/settings/organization/billing. The default `gpt-5-mini` model is cheap but not free.
- **`model not found`** — someone has pinned `LLM_MODEL` to a model your key cannot access. Remove or update the override in `.env.docker`.
- **Timeouts / network errors** — transient, retry. If it keeps happening, check `LLM_MAX_CONCURRENT_REQUESTS`.

---

## 8. Code changes not taking effect

**Symptom** — You edit a `.py` file but the behavior on http://localhost:8000 is unchanged.

**Fixes, in order:**

1. **Check the reloader actually fired.** `docker-compose logs -f app` should print `WARNING: WatchFiles detected changes in ...` every time you save.
2. **Make sure the file is mounted.** `app/`, `alembic/`, `scripts/`, `data/`, and `templates/` are bind-mounted. Files outside those paths require a rebuild.
3. **Did you change `requirements.txt`?** New packages are not in the image yet. Rebuild:
   ```bash
   docker-compose up --build
   ```
4. **Force a clean restart:**
   ```bash
   docker-compose restart app
   ```

---

## 9. `ModuleNotFoundError` or stale Python packages

**Symptom** — The app worked yesterday, someone pulled new code, and now it errors on import at startup.

**Cause** — Their change added a dependency you haven't built locally.

**Fix** —

```bash
docker-compose up --build
```

---

## 10. File permission errors writing to `data/`

**Symptom** — Document generation errors with `PermissionError: [Errno 13]` when saving a logo or a generated DOCX.

**Fix** — The `data/` directory is bind-mounted from your host. Make sure it exists and is writeable by Docker:

```bash
mkdir -p data/uploads/logos data/documents/generated data/documents/previews
chmod -R u+rwX data/
```

On Linux you may also need to match the container's user ID — on macOS and Windows this is handled by Docker Desktop automatically.

---

## 11. Running out of disk space

**Symptom** — Docker builds fail with `no space left on device`, or your laptop's free space keeps shrinking.

**Fix** —

```bash
docker system df          # see how much Docker is using
docker system prune       # remove stopped containers, unused networks, dangling images
docker system prune -a    # also remove unused images (more aggressive)
```

Do **not** run `docker volume prune` unless you are prepared to lose your MySQL data volume.

---

## 12. "Nothing works, start over"

The nuclear option. Wipes the DB but rebuilds everything cleanly:

```bash
docker-compose down -v
docker system prune -f
docker-compose up --build
docker-compose exec app python scripts/seed_plans.py
```

If this doesn't get you to a healthy state, the problem is in your environment (Docker Desktop not running, `.env.docker` malformed, etc.) — post logs and ask.
