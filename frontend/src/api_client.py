import os

import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")


def backend_health() -> dict[str, str]:
    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=3.0)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return {"status": "error", "detail": str(exc)}
