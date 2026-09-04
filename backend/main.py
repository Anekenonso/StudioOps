from fastapi import FastAPI
from backend.api.routes import router as api_router

app = FastAPI(title="StudioOps API - Phase 1")

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
