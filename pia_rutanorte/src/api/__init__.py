"""Capa de presentación (FastAPI). ``uvicorn src.api:app`` y ``uvicorn src.api.main:app`` son equivalentes."""
from src.api.main import app

__all__ = ["app"]
