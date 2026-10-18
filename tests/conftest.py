"""Configuración de pytest: la app usa un Supabase simulado, nunca la base real.

Para correr las pruebas (desde la carpeta del repositorio):
    pip install pytest
    python -m pytest tests
"""
import os
import sys

import pytest

# Valores falsos para que realFlask.py no lea el .env ni se conecte a Supabase.
os.environ['SUPABASE_URL'] = 'http://127.0.0.1:9'
os.environ['SUPABASE_PUBLISHABLE_KEY'] = 'sb_publishable_pruebas'
os.environ['FLASK_SECRET_KEY'] = 'pruebas'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import realFlask  # noqa: E402
from tests.supabase_falso import con_datos_de_ejemplo  # noqa: E402


@pytest.fixture
def db(monkeypatch):
    base = con_datos_de_ejemplo()
    monkeypatch.setattr(realFlask, 'supabase', base)
    return base


@pytest.fixture
def cliente(db):
    realFlask.app.config['TESTING'] = True
    return realFlask.app.test_client()


@pytest.fixture
def admin(cliente):
    """Cliente con acceso a todo (la app todavía no tiene inicio de sesión)."""
    return cliente
