from __future__ import annotations

from scnai.config import ensure_env_loaded

ensure_env_loaded()

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from scnai.api.routes import router
from scnai.config import load_settings
from scnai.services.ado import build_wit_client
from scnai.services.embedder import build_embedding_client

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    app.state.settings = settings
    app.state.wit_client = build_wit_client(settings)
    app.state.embedding_client = build_embedding_client(settings)
    yield


app = FastAPI(
    title="SCNAI",
    description="Azure DevOps user stories: Azure OpenAI embeddings + DBSCAN clustering.",
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "scnai", "docs": "/docs", "openapi": "/openapi.json"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("scnai.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
