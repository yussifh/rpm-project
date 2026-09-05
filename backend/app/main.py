"""
Application entrypoint.

Design decisions:
- CORS is restricted to configured origins only (never "*") since this
  system handles protected health information (PHI).
- API versioning via /api/v1 prefix so breaking changes later can ship
  as /api/v2 without disrupting existing clients.
- A dedicated /health endpoint is provided for Docker healthchecks and
  deployment platforms (Render) to verify liveness.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import DomainError

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="AI-Integrated Remote Patient Monitoring System for Chronic Disease Management",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.exception_handler(DomainError)
def domain_error_handler(request: Request, exc: DomainError):
    """
    Safety net: any DomainError NOT explicitly caught and translated inside
    a route (see app/api/v1/auth.py for the deliberate, specific translations)
    falls back to a generic 400 here, rather than leaking a raw 500 traceback
    to the client. Routes should still prefer catching known exceptions
    explicitly so they can pick the most accurate status code.
    """
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health", tags=["System"])
def health_check():
    """Liveness/readiness probe used by Docker and deployment platforms."""
    return {"status": "ok", "environment": settings.ENVIRONMENT}
