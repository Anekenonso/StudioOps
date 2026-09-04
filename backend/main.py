from fastapi import FastAPI
from backend.api.routes import router as api_router
import os

# Load local .env in development if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # python-dotenv not installed or .env not present; proceed silently
    pass

app = FastAPI(title="StudioOps API - Phase 1")

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
