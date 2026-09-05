# Deployment Guide

Three deployment paths are supported: local development (Docker Compose), self-hosted production (Docker Compose, prod images), and Render (managed platform, via `render.yaml`).

## 1. Local Development

```bash
cp .env.example .env          # fill in real values, especially JWT_SECRET_KEY
docker-compose up --build
```

- Frontend (Vite dev server, hot reload): http://localhost:5173
- Backend: http://localhost:8000, docs at http://localhost:8000/docs
- Health check: http://localhost:8000/health

Run migrations and seed the first admin (containers must be up):

```bash
docker-compose exec backend alembic upgrade head
docker-compose exec backend python -m scripts.seed_admin --email admin@example.com --full-name "System Admin"
```

Train the AI models (required before predictions work — see Module 5):

```bash
docker-compose exec backend python -m app.ai_engine.train
```

## 2. Self-Hosted Production (Docker Compose)

Uses `docker-compose.prod.yml` — multi-stage images (`Dockerfile.prod` for both services), no source bind-mounts, Nginx serving the built frontend, Gunicorn+Uvicorn workers for the backend.

```bash
cp .env.example .env   # production secrets — see Environment Variables below
docker-compose -f docker-compose.prod.yml up -d --build
```

Migrations run automatically on backend container start (`entrypoint.sh` runs `alembic upgrade head` before starting Gunicorn — see backend/entrypoint.sh). Seed the first admin the same way as above, just against the prod compose file:

```bash
docker-compose -f docker-compose.prod.yml exec backend python -m scripts.seed_admin --email admin@example.com --full-name "System Admin"
docker-compose -f docker-compose.prod.yml exec backend python -m app.ai_engine.train
```

Put a reverse proxy (Caddy, Traefik, or Nginx on the host) in front of ports 80/8000 for TLS termination — this compose file does not handle HTTPS itself.

## 3. Render (Managed Platform)

`render.yaml` at the repo root is a Render **Blueprint** — connect the repo in the Render dashboard as a Blueprint and it provisions:
- `rpm-postgres` — managed Postgres
- `rpm-redis` — managed Redis (Key Value)
- `rpm-backend` — Docker web service built from `backend/Dockerfile.prod`
- `rpm-frontend` — static site built from `frontend/` via `npm run build`

Steps:
1. Push this repo to GitHub.
2. In Render: **New > Blueprint**, connect the repo. Render reads `render.yaml` and provisions everything.
3. After the first deploy, Render assigns real `*.onrender.com` URLs to `rpm-backend` and `rpm-frontend`. Go back into `render.yaml` (or just edit the env vars directly in the Render dashboard for a quicker fix) and update:
   - `rpm-backend`'s `BACKEND_CORS_ORIGINS` → the real frontend URL
   - `rpm-frontend`'s `VITE_API_BASE_URL` → the real backend URL + `/api/v1`
4. Redeploy both services so the URL updates take effect (frontend needs a rebuild since Vite inlines env vars at build time, not runtime).
5. Open a **Shell** on the `rpm-backend` service in the Render dashboard and run:
   ```bash
   python -m scripts.seed_admin --email admin@example.com --full-name "System Admin"
   python -m app.ai_engine.train
   ```
   Migrations already ran automatically (same `entrypoint.sh` as the Docker Compose path).

**CI-gated deploys (optional, alternative to Render's own auto-deploy-on-push):** `.github/workflows/ci.yml` has a `deploy` job that only runs after both test jobs pass on `main`, and calls Render's per-service **Deploy Hook** URLs. To use this instead of (or in addition to) Render's native auto-deploy:
1. In Render, open each service's Settings → Deploy Hook, copy the URL.
2. In GitHub, add repo secrets `RENDER_BACKEND_DEPLOY_HOOK` and `RENDER_FRONTEND_DEPLOY_HOOK` with those URLs.
3. If you want CI to be the *only* trigger (not also Render's native auto-deploy racing it), disable auto-deploy in each Render service's settings.

## Environment Variables Reference

| Variable | Used by | Notes |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Docker Compose only | Render provisions Postgres itself; `DATABASE_URL` is injected automatically |
| `DATABASE_URL` | Backend | Full connection string; Render fills this in automatically via `fromDatabase` |
| `REDIS_URL` | Backend | Same — Render fills this in via `fromService` |
| `JWT_SECRET_KEY` | Backend | **Must** be a long random value in production. Render's `generateValue: true` handles this for you; for Docker Compose, generate one yourself (`openssl rand -hex 32`) — never reuse the `.env.example` placeholder |
| `JWT_ALGORITHM` | Backend | `HS256`, rarely needs changing |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | Backend | Session lifetime tuning |
| `BACKEND_CORS_ORIGINS` | Backend | JSON array string, e.g. `["https://your-frontend.com"]` — must match the frontend's real origin exactly |
| `VITE_API_BASE_URL` | Frontend (build-time) | Baked into the static bundle at build — changing it requires a rebuild, not just a restart |

## Security Checklist Before Going Live

- [ ] `JWT_SECRET_KEY` is a real random secret, not the `.env.example` placeholder
- [ ] `BACKEND_CORS_ORIGINS` is locked to your actual frontend origin(s), never `["*"]`
- [ ] Database credentials are not the Compose defaults (`rpm_user` / `rpm_password`)
- [ ] TLS/HTTPS is terminated somewhere in front of both services (Render does this automatically; self-hosted needs a reverse proxy)
- [ ] The first admin was created via `scripts/seed_admin.py`, not by any other means
- [ ] AI models have been trained (`python -m app.ai_engine.train`) — predictions will fail with a clear `ModelNotTrainedError` otherwise, not a silent wrong answer
- [ ] Reminder: the shipped AI models are trained on **synthetic data** (see `app/ai_engine/feature_schema.py` docstring) — this is a demonstration pipeline, not a clinically validated one. Do not present prediction output as medical advice without retraining on a real, ethically-sourced clinical dataset and clinician review.
