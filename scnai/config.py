from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_DOTENV_INITIALIZED = False


def _load_dotenv() -> None:
    """Populate os.environ from .env (CWD first, then repo root for missing keys)."""
    global _DOTENV_INITIALIZED
    if _DOTENV_INITIALIZED:
        return
    # Process CWD (e.g. where you run `python -m scnai.main` or uvicorn)
    load_dotenv()
    # Repo root: parent of the `scnai` package directory
    repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(repo_root / ".env")
    _DOTENV_INITIALIZED = True


def ensure_env_loaded() -> None:
    """Load `.env` into ``os.environ``. Call early (e.g. before ``logging.basicConfig``)."""
    _load_dotenv()


def require_env(value: str | None, name: str) -> str:
    if value:
        return value
    raise RuntimeError(f"Missing required environment variable: {name}")


@dataclass(frozen=True)
class Settings:
    azdo_organization_url: str
    azdo_pat: str
    azure_openai_embedding_endpoint: str
    azure_openai_embedding_api_key: str
    azure_openai_embedding_deployment: str
    azure_openai_embedding_api_version: str
    embed_batch_size: int
    default_iteration_path: str
    cosmos_endpoint: str | None
    cosmos_key: str | None
    cosmos_database: str | None
    cosmos_container: str | None
    cosmos_embeddings_container: str | None
    cosmos_partition_key_field: str
    workbench_docx_template: str | None


def load_settings() -> Settings:
    _load_dotenv()
    return Settings(
        azdo_organization_url=os.getenv(
            "AZDO_ORGANIZATION_URL", "https://dev.azure.com/pomscorp"
        ),
        azdo_pat=os.getenv("AZDO_PAT"),
        azure_openai_embedding_endpoint=os.getenv(
            "AZURE_OPENAI_EMBEDDING_ENDPOINT"
        ),
        azure_openai_embedding_api_key=os.getenv(
            "AZURE_OPENAI_EMBEDDING_API_KEY"
        ),
        azure_openai_embedding_deployment=os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        ),
        azure_openai_embedding_api_version=os.getenv(
            "AZURE_OPENAI_EMBEDDING_API_VERSION"
        ),
        embed_batch_size=int(os.getenv("EMBED_BATCH_SIZE", "16")),
        default_iteration_path=os.getenv(
            "DEFAULT_ITERATION_PATH", r"POMS\POMSnet\Aquila\2026.1.0"
        ),
        cosmos_endpoint=os.getenv("COSMOS_ENDPOINT"),
        cosmos_key=os.getenv("COSMOS_KEY"),
        cosmos_database=os.getenv("COSMOS_DATABASE"),
        cosmos_container=os.getenv("COSMOS_CONTAINER"),
        cosmos_embeddings_container=os.getenv("COSMOS_EMBEDDINGS_CONTAINER"),
        cosmos_partition_key_field=os.getenv(
            "COSMOS_PARTITION_KEY_FIELD", "document_type"
        ),
        workbench_docx_template=os.getenv("WORKBENCH_DOCX_TEMPLATE"),
    )
