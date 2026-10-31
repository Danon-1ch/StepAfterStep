import os
import sys
import tempfile
from pathlib import Path

# Тесты всегда работают на отдельной временной базе и без YandexGPT (демо-режим)
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["YANDEX_API_KEY"] = ""
os.environ["YANDEX_FOLDER_ID"] = ""
os.environ["MAX_MESSAGES_PER_MINUTE"] = "1000"
os.environ["MAX_MESSAGES_PER_MINUTE_PER_IP"] = "1000"
os.environ["MAX_NEW_SESSIONS_PER_MINUTE"] = "1000"
os.environ["DEMO_ADMIN_TOKEN"] = "demo-admin"
os.environ["STATIC_DIR"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def session_id(client):
    return client.post("/api/sessions", json={"clinic_key": "demo"}).json()["session_id"]
