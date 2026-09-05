# AI-Integrated Remote Patient Monitoring System

A remote patient monitoring platform for chronic disease management (Stroke,
Diabetes, Hypertension), combining real-time vitals tracking with AI-driven
risk prediction for early warning and clinical decision support.

## Key Features

- **Condition-based vitals workflow** — patient selects the condition(s)
  to monitor before entering vitals; the system shows only the fields
  those conditions' models need, runs a separate prediction per
  condition, and never blends conditions together.
- **Per-disease trained ML models** with algorithm comparison (Logistic
  Regression / Random Forest / Gradient Boosting, selected per disease by
  cross-validated ROC-AUC) rather than one hardcoded algorithm — see
  `MODEL_CARD.md`.
- **Predictive trend forecasting** — projects whether a vital is likely
  to cross a clinical threshold, and roughly when, if its current
  trajectory continues (e.g. "systolic BP may reach 180 mmHg in ~6 days
  at this rate"). This is the same category of feature marketed by
  commercial platforms like Biofourmis ("predicts a patient's disease
  trajectory days in advance") — implemented here transparently: the
  regression basis, confidence score (R²), and the exact rule that
  suppresses the forecast when confidence is too low are all visible,
  rather than a black-box number. See `app/services/trend_analysis.py`
  and the "Predictive Trend Forecasting" section of `MODEL_CARD.md`.
- **AI Health Assistant** — LLM-backed chat that explains the patient's
  own vitals, predictions, trends, and forecasts in plain language, under
  hard rules against diagnosis, medication advice, or inventing data; a
  deterministic (non-LLM) emergency override handles active critical
  alerts so that path never depends on a network call succeeding.
- **Full explainability** — every prediction ships with plain-language
  reasons and a feature-importance breakdown; every trend and forecast
  ships with the statistical basis behind it, not just a conclusion.
- **Clinical recommendations, generated per prediction, not static text**
  — each risk prediction ships with a short (max 4), prioritized list of
  patient-specific recommendations derived from that prediction's own
  risk factors, trend, and medication adherence — see
  `app/services/recommendation_engine.py`. Deterministic and rule-based
  (not an LLM call, so it's fast, reproducible, and auditable — every
  recommendation traces to a specific rule and a specific input value),
  and hard-blocked from ever suggesting a medication start/stop/dosage
  change — only lifestyle, self-monitoring, and professional-referral
  guidance.
- **Alert deduplication** — a still-unresolved issue doesn't re-alert on
  every subsequent reading; a fresh alert only fires again once the
  existing one is resolved. Directly addresses the precision/recall
  tradeoff documented in `MODEL_CARD.md` (rare-event models favor recall,
  so without deduplication a sustained borderline reading would otherwise
  generate a new alert on every single submission).
- **Emergency contact notification** — a CRITICAL alert (not every alert —
  see `emergency_contact_service.py` for why) triggers a notification to
  the patient's emergency contact, if one is on file, matching a real
  feature of commercial RPM platforms (e.g. Tellihealth notifying family
  on a dangerous hypoglycemic event). Delivery is currently simulated
  (logged + audited) rather than wired to a real SMS/email provider — see
  that module's docstring for the intentional integration point.

## Tech Stack

| Layer          | Technology                                             |
|----------------|---------------------------------------------------------|
| Frontend       | React, TypeScript, Vite, Tailwind CSS                   |
| Backend        | Python, FastAPI                                         |
| AI             | Scikit-learn, Pandas, NumPy, Joblib                      |
| Database       | PostgreSQL (SQLAlchemy ORM), Redis (cache)               |
| Auth           | JWT, OAuth2, bcrypt, RBAC                                |
| Charts         | Chart.js, Recharts                                       |
| Testing        | pytest (backend), Vitest + Playwright (frontend)         |
| Deployment     | Docker, Docker Compose, Render, GitHub Actions           |

## System Users

- **Administrator** — manages patients, ML datasets/models/training, system oversight, audit logs
- **Patient** — submits vitals, views personal health analytics and AI risk predictions, receives alerts

## Project Structure

```
rpm-project/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/v1/           # Route handlers (versioned)
│   │   ├── core/             # Config, security utilities
│   │   ├── db/               # DB session, Redis client
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic layer
│   │   ├── repositories/     # Data-access layer
│   │   ├── ai_engine/        # ML models + inference pipeline
│   │   └── main.py           # App entrypoint
│   └── tests/                # pytest suite
├── frontend/                 # React + TypeScript SPA
│   └── src/
│       ├── components/       # Reusable UI components
│       ├── pages/            # Route-level pages
│       ├── features/         # Feature-scoped modules (vitals, alerts, etc.)
│       ├── context/          # Auth/global React context
│       ├── services/         # API client layer
│       ├── hooks/            # Custom React hooks
│       ├── routes/           # Route definitions + guards
│       └── types/            # Shared TypeScript types
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Local Development

1. Copy environment template:
   ```bash
   cp .env.example .env
   ```
2. Start all services:
   ```bash
   docker-compose up --build
   ```
3. Access:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API health check: http://localhost:8000/health

See **[DEPLOYMENT.md](./DEPLOYMENT.md)** for production deployment (self-hosted Docker Compose or Render), **[TESTING.md](./TESTING.md)** for the full test strategy and how to run each suite, and **[MODEL_CARD.md](./MODEL_CARD.md)** for the AI models' data provenance, evaluation metrics, and known limitations.

## Architecture Principles

- **Clean Architecture**: Router → Service → Repository → Database layering keeps business logic independent of frameworks and I/O.
- **SOLID**: each service/repository has a single responsibility; AI models are swappable without touching API code.
- **RBAC-first security**: role checks enforced at the dependency-injection layer, before requests reach business logic.
- **Auditability**: all state-changing operations are logged — a healthcare-domain requirement, not an afterthought.

## Project Status

🚧 Under active development as a Final Year Computer Science Project. Built module-by-module; see project roadmap for sequencing.
