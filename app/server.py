"""Entry point for uvicorn:  uvicorn app.server:app --reload"""
from .main import create_app

app = create_app()
