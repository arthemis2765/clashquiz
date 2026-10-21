"""Fixtures de test : base SQLite jetable (aucune connexion à PostgreSQL)."""
import os
import sys
import tempfile

_DB_FILE = os.path.join(tempfile.mkdtemp(), "test_clashquiz.sqlite")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_FILE}"
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.rate_limit import register_limiter, solo_start_limiter  # noqa: E402
from app.websocket.manager import question_cache  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_database():
    """Base vide + 2 thèmes de 20 questions (4 par niveau) avant chaque test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    question_cache.invalidate()
    solo_start_limiter._hits.clear()
    register_limiter._hits.clear()

    db = SessionLocal()
    try:
        for slug, name in (("geo", "Géographie"), ("tech", "Technologie")):
            category = models.Category(name=name, slug=slug, active=True)
            db.add(category)
            db.flush()
            for difficulty in range(1, 6):
                for i in range(4):
                    db.add(models.Question(
                        category_id=category.id,
                        prompt_label=f"{slug} d{difficulty} q{i} ?",
                        answer=f"Reponse {slug}{difficulty}{i}",
                        hint_type=models.HintType.text,
                        difficulty=difficulty,
                    ))
        db.commit()
    finally:
        db.close()
    yield


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def make_player(client):
    def _make(pseudo="Joueur"):
        res = client.post("/api/players/register", json={"pseudo": pseudo})
        assert res.status_code == 200, res.text
        data = res.json()
        return {"player_id": data["id"], "device_token": data["device_token"]}
    return _make


@pytest.fixture()
def solo(client):
    """Petit assistant pour piloter une partie solo dans les tests."""
    class Solo:
        def __init__(self, auth, category="geo"):
            self.auth = auth
            res = client.post("/api/solo/start", json={**auth, "category_slug": category})
            assert res.status_code == 200, res.text
            data = res.json()
            self.run_id = data["state"]["run_id"]
            self.question = data["question"]
            self.state = data["state"]

        def current_answer(self):
            db = SessionLocal()
            try:
                run = db.get(models.SoloRun, __import__("uuid").UUID(self.run_id))
                return db.get(models.Question, run.current_question_id).answer
            finally:
                db.close()

        def answer(self, text, number=None):
            res = client.post("/api/solo/answer", json={
                **self.auth, "run_id": self.run_id,
                "question_number": number if number is not None else self.question["number"],
                "answer": text,
            })
            if res.status_code == 200:
                data = res.json()
                self.state = data["state"]
                self.question = data["question"] or self.question
            return res

        def right(self):
            return self.answer(self.current_answer())

        def wrong(self):
            return self.answer("zzz")

        def expire(self):
            """Force l'échéance de la question en cours (sans attendre 15 s)."""
            db = SessionLocal()
            try:
                run = db.get(models.SoloRun, __import__("uuid").UUID(self.run_id))
                run.question_deadline = 1.0
                db.commit()
            finally:
                db.close()
    return Solo
