import os
import tempfile

# Point the app at a throwaway database before anything imports app.config.
# TEST_DATABASE_URL runs the suite against another database, e.g. a throwaway local Postgres
# (tables are dropped and recreated per test, so never point it at real data).
_tmpdir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{_tmpdir}/test.db"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"
# Keep tests independent of the developer's backend/.env (load_dotenv won't override these).
os.environ["ADMIN_EMAILS"] = "mhatre.anushka.work@gmail.com"
os.environ["ADMIN_INITIAL_PASSWORD"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.llm.provider import LLMResponse, ToolCall, set_provider  # noqa: E402
from app.main import app  # noqa: E402


class FakeProvider:
    """Returns scripted responses; records what it was sent."""

    def __init__(self, script: list[LLMResponse]):
        self.script = list(script)
        self.calls: list[dict] = []

    def complete(self, **kwargs) -> LLMResponse:
        self.calls.append(kwargs)
        resp = self.script.pop(0)
        if resp.assistant_content is None:
            resp.assistant_content = [{"type": "text", "text": resp.text or "..."}] + [
                {"type": "tool_use", "id": c.id, "name": c.name, "input": c.input}
                for c in resp.tool_calls
            ]
        return resp


def text_reply(text: str) -> LLMResponse:
    return LLMResponse(text=text, tool_calls=[], stop_reason="end_turn")


def tool_reply(name: str, args: dict, call_id: str = "t1", text: str = "") -> LLMResponse:
    return LLMResponse(text=text, tool_calls=[ToolCall(call_id, name, args)], stop_reason="tool_use")


@pytest.fixture
def fake_llm():
    def install(*script: LLMResponse) -> FakeProvider:
        provider = FakeProvider(list(script))
        set_provider(provider)
        return provider
    yield install
    set_provider(None)


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


ONBOARDING = {
    "preferred_name": "Buddy",
    "date_of_birth": "1995-06-15",
    "sex": "male",
    "height_cm": 180,
    "weight_kg": 80,
    "unit_system": "metric",
    "timezone": "Asia/Kolkata",
    "goal_type": "weight_loss",
    "activity_level": "moderate",
}


def make_user(client: TestClient, email: str = "me@example.com") -> dict:
    r = client.post("/api/auth/register", json={"email": email, "password": "password123", "consent": True})
    assert r.status_code == 201, r.text
    r = client.post("/api/profile/onboarding", json=ONBOARDING)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def user(client):
    return make_user(client)
