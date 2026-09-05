# Testing Plan

## Philosophy

This project follows a standard test pyramid: many fast unit tests, a solid layer of integration tests against the real API surface (with an in-memory DB), and a thin layer of end-to-end browser tests for the critical user journeys. Unit tests should never require a database or a browser; integration tests should never require a real browser; only E2E tests spin up the full stack.

## Backend (pytest)

### Unit tests (no DB, no HTTP) — pure logic in isolation

| File | Covers |
|---|---|
| `tests/test_security.py` | Password hashing (bcrypt salting/verification), JWT access/refresh token creation, decoding, tampering detection |
| `tests/test_alert_rules.py` | Threshold-based vitals alert rules (BP, glucose, SpO2, heart rate) — every severity boundary |
| `tests/test_ai_engine.py` | Synthetic data generation properties, trained-model inference shape, missing-feature/unknown-disease/untrained-model error paths, relative risk ranking (a high-risk profile must score above a low-risk one) |

These are the tests most worth running first on any change — they're fast (no DB fixture setup) and catch logic regressions closest to the source.

### Integration tests (in-memory SQLite + fakeredis, full HTTP stack via FastAPI's TestClient)

| File | Covers |
|---|---|
| `tests/test_health.py` | App boots, `/health` responds |
| `tests/test_auth.py` | Registration (success/duplicate/weak password), login, `/me`, refresh, logout/revocation |
| `tests/test_patients_and_medications.py` | Admin user management, RBAC boundaries, medical history write restrictions, patient adds own medication → logs a dose |
| `tests/test_predictions.py` | Insufficient-data guard rail, patient-triggered AI prediction, other-patient RBAC block, prediction history, recommendations present and capped |
| `tests/test_recommendation_engine.py` | Cap/priority ordering, dynamic behavior (different inputs -> different output, determinism), safety rule (no medication dosage language) across all three diseases |
| `tests/test_vitals_and_alerts.py` | Vitals ingestion + validation, threshold-triggered alerts, AI-triggered alerts (exercises the real trained models), alert lifecycle RBAC (admin-only), notification creation, alert deduplication (no repeat alert while unresolved; new alert after resolution), emergency contact notification (critical-only, contact-on-file gating), forecast in the trends response |
| `tests/test_reports_and_audit.py` | Audit log visibility, PDF report generation (byte-level `%PDF` check) |
| `tests/test_account.py` | Admin-created patient accounts, self-service password change |
| `tests/test_admin_edit.py` | Admin editing of patient profile and user identity fields |
| `tests/test_disease_workflow.py` | Admin-assigned primary condition, disease assessments, explainable-AI prediction reasons |

**Why SQLite instead of Postgres for these:** speed and zero external dependencies — anyone can run `pytest` with no Docker running. The tradeoff is real: SQLite doesn't enforce everything Postgres does (e.g. some constraint/JSONB behaviors differ). A smaller set of true Postgres-backed tests, run in CI against the `postgres:16-alpine` service container (see `.github/workflows/ci.yml`), would close that gap — not yet built out, listed under Known Gaps below.

### Running the backend suite

```bash
cd backend
pip install -r requirements.txt
pytest -v                    # full suite
pytest tests/test_security.py -v   # single file
pytest -k "alert" -v         # by keyword
pytest --cov=app --cov-report=term-missing   # with coverage (pytest-cov not yet in requirements — add if desired)
```

## Frontend (Vitest + React Testing Library)

### Unit / component tests

| File | Covers |
|---|---|
| `src/utils/vitalsStatus.test.ts` | Pure status-threshold logic (kept in sync with the backend's alert thresholds by design) |
| `src/services/tokenStorage.test.ts` | Token persistence, partial updates, clearing |
| `src/components/ui/VitalReadout.test.tsx` | Renders label/value/unit correctly, applies the right color class per status |

### Running

```bash
cd frontend
npm install
npm run test          # vitest run — single pass, CI-friendly
npm run test:watch    # interactive
```

### What's not yet covered (see Known Gaps)

`AuthContext` (login/logout/session-restore flow) and `apiClient`'s refresh-on-401 interceptor are the two highest-value untested pieces on the frontend — both involve async state and mocked HTTP calls, which is more setup than the samples above. Recommended next addition.

## End-to-End (Playwright)

E2E tests run against a **live, fully running stack** (`docker-compose up`) — they are the only layer that exercises real browser behavior, real network calls, and the real Postgres/Redis containers together.

| File | Covers |
|---|---|
| `e2e/auth.spec.ts` | Full registration → login → dashboard flow; incorrect-credentials error state; unauthenticated redirect |
| `e2e/patient-dashboard.spec.ts` | Sidebar navigation between sections; logout clears the session and re-blocks protected routes |

Each test is self-contained — it registers its own fresh patient account (unique email per run) rather than depending on seeded fixture data, so the suite can run against a freshly-migrated, empty database.

### Running

```bash
cd frontend
npx playwright install --with-deps   # one-time browser download
docker-compose up -d                  # start the full stack from repo root
npm run test:e2e
```

## CI Integration

`.github/workflows/ci.yml` currently runs the backend pytest suite (against real Postgres/Redis service containers) and the frontend lint/Vitest/build steps in parallel jobs on every push/PR. Playwright E2E is **not** yet wired into CI — it needs the full docker-compose stack up first, which is a heavier CI job (build all images, wait for healthchecks, then run browsers). Recommended as a separate, slower "e2e" workflow triggered on merge to `main` rather than every PR.

## Known Gaps / Recommended Next Steps

- **Postgres-specific backend tests**: a handful of tests that run against real Postgres (not SQLite) to verify JSONB fields, enum constraints, and cascade behavior actually work as modeled.
- **Frontend `AuthContext` and `apiClient` interceptor tests**: mock `authApi`/axios and assert the token-refresh-then-retry behavior and session-expired-forces-logout behavior directly, not just indirectly through E2E.
- **Coverage reporting**: `pytest-cov` (backend) and Vitest's built-in `--coverage` (frontend) aren't wired into CI yet — useful once the suite is large enough that "what's untested" stops being obvious from the file list above.
- **Playwright in CI**: wire the E2E job described above once the team is ready for the added CI runtime cost.
- **Load/performance testing**: not attempted — out of scope for a Final Year Project, but worth a line item if this ever heads toward real deployment (the AI inference path in particular, run inline per vitals submission, is the first place I'd load-test — see the disclosed tradeoff in `app/services/vitals_service.py`).
