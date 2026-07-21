# Deployment guide

Deploy the Agentic Knowledge Worker as a **live site a recruiter can use** — zero cost.

**Stack:** Neon (Postgres + pgvector) · Render (FastAPI backend) · Vercel (Next.js frontend).

Every document uploaded on the live site is chunked, embedded, and stored in Neon, so it
**persists** and is queryable by anyone visiting the site (shared knowledge base).

```
Recruiter's browser
      │  https
      ▼
Vercel (Next.js)  ──https/wss──►  Render (FastAPI)  ──TLS──►  Neon (Postgres + pgvector)
```

---

## Part 0 — Bonus: run locally WITHOUT Docker

You don't need local Docker at all once you have a Neon database. Point your local backend
at Neon and everything runs:

```bash
# in backend/.env (or the repo-root .env), set:
DATABASE_URL=postgresql://<user>:<pass>@<host>.neon.tech/ragdb?sslmode=require
```

The app auto-normalizes this for the async driver and enables SSL — no `postgresql+asyncpg`
edits needed. Then `uvicorn app.main:app --reload` + `npm run dev` as usual. (This is the
clean way around a broken local Docker/WSL setup.)

---

## Part 1 — Database (Neon)

1. Sign up free at **[neon.tech](https://neon.tech)** (GitHub login works).
2. **Create a project** → it creates a database. Name it `ragdb` (or keep the default).
3. Neon supports pgvector out of the box — the app runs `CREATE EXTENSION IF NOT EXISTS
   vector` automatically on first boot, so there's nothing to install.
4. Copy the **connection string** from the dashboard. It looks like:
   ```
   postgresql://alex:AbC123@ep-cool-forest-12345.us-east-2.aws.neon.tech/ragdb?sslmode=require
   ```
   Keep it handy — both the backend and your local `.env` use it verbatim.

> Neon free tier auto-suspends after ~5 min idle but wakes in under a second. The backend
> uses `pool_pre_ping` so a dropped idle connection is transparently recycled.

---

## Part 2 — Backend (Render)

1. Push this repo to GitHub (see the end of this doc if you haven't set up git yet).
2. Sign up at **[render.com](https://render.com)** with GitHub.
3. **New → Blueprint** → pick this repo. Render reads [`render.yaml`](../render.yaml) and
   creates the Docker web service automatically.
4. When prompted, fill in the environment variables (they're marked `sync: false` so Render
   asks for them):

   | Variable | Value |
   |----------|-------|
   | `DATABASE_URL` | your Neon connection string from Part 1 |
   | `GROQ_API_KEY` | your Groq key (`gsk_…`) |
   | `GOOGLE_API_KEY` | your Gemini key |
   | `CORS_ORIGINS` | leave blank for now — you'll set it after Part 3 |
   | `JWT_SECRET_KEY` | Render auto-generates this — leave it |

5. Deploy. First build takes a few minutes (Docker image). When it's live you'll get a URL
   like `https://agentic-knowledge-worker-api.onrender.com`.
6. Verify: open `https://<your-render-url>/health` → should return `{"status":"ok"}`.

> **Cold start:** Render's free tier sleeps after 15 min of no traffic; the next request
> takes ~50s to wake. See "Keep it warm" below to avoid this during a recruiter demo.

---

## Part 3 — Frontend (Vercel)

1. Sign up at **[vercel.com](https://vercel.com)** with GitHub.
2. **Add New → Project** → import this repo.
3. **Important — set the Root Directory to `frontend`** (this repo has both backend and
   frontend; Vercel must build only `frontend`). Framework preset auto-detects **Next.js**.
4. Under **Environment Variables**, add:

   | Variable | Value |
   |----------|-------|
   | `NEXT_PUBLIC_API_URL` | your Render backend URL, e.g. `https://agentic-knowledge-worker-api.onrender.com` |

   (No trailing slash. This is baked in at build time, so it must be set before/at deploy.)
5. Deploy. You'll get a URL like `https://your-app.vercel.app`.

---

## Part 4 — Connect them (CORS)

The backend must allow the browser origin of your Vercel site, or every request fails with
`Failed to fetch`.

1. In **Render → your service → Environment**, set:
   ```
   CORS_ORIGINS = https://your-app.vercel.app
   ```
   (Use your real Vercel URL. Multiple origins allowed, comma-separated.)
2. Save → Render redeploys. Done.

> In production (`APP_ENV=production`) the backend uses this strict allowlist. In local dev
> it allows any `localhost` port automatically, so you never hit CORS locally.

Open `https://your-app.vercel.app`, upload a document, ask a question. That's your live demo.

---

## Keep it warm (optional but recommended for demos)

So a recruiter never hits the ~50s Render cold start:

1. Sign up at **[uptimerobot.com](https://uptimerobot.com)** (free).
2. Add an **HTTP(s) monitor** pinging `https://<your-render-url>/health` every **10 minutes**.

This keeps the backend awake during your active job-search window at no cost.

---

## What is and isn't deployed

- **Deployed:** frontend (Vercel), backend API (Render), database (Neon).
- **Not deployed:** the MCP server — it's a *local* tool for Claude Desktop / Cursor, not a
  web service. Run it locally when you want to demo the MCP integration (see
  [MCP_CLIENT.md](MCP_CLIENT.md)).
- **Optional:** Langfuse tracing stays off unless you set its keys — no deployment impact.

## Cost summary

| Service | Free tier | Enough for a demo? |
|---------|-----------|--------------------|
| Neon | 0.5 GB storage, autosuspend | Yes — thousands of chunks |
| Render | 750 hrs/mo, sleeps when idle | Yes (with keep-warm ping) |
| Vercel | 100 GB bandwidth/mo | Yes, comfortably |
| Groq / Gemini | Free API tiers | Yes (daily token caps apply) |

**Total: $0/month.**

---

## First-time git setup (if you haven't pushed yet)

The repo currently isn't its own git project. From `project_1/`:

```bash
git init
git add .
git commit -m "Agentic Knowledge Worker"
git branch -M main
git remote add origin https://github.com/<you>/agentic-knowledge-worker.git
git push -u origin main
```

`.gitignore` already excludes `.env`, `venv/`, and `node_modules/`, so your keys and
dependencies won't be committed. **Double-check** `git status` shows no `.env` before pushing.
