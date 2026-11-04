from dataclasses import replace

import boto3
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI

from app.config import MODELS, Settings
from app.main import create_app
from app.mock_provider import MockProvider

TOKEN = "test-admin-" + "x" * 40


@pytest.fixture
def setup(tmp_path, monkeypatch):
    # The entire mock flow must work with all AWS client construction forbidden.
    monkeypatch.setattr(boto3, "Session", lambda *a, **k: pytest.fail("Mock mode touched AWS"))
    settings = Settings(admin_token=TOKEN, database=str(tmp_path / "mock.db"))
    app = create_app(settings, start_worker=False)
    with TestClient(app, headers={"Authorization": f"Bearer {TOKEN}"}) as client:
        yield app, client, settings


def deploy(app, client, request_id="request-123", model=None):
    r = client.post(
        "/api/deployments",
        headers={"Idempotency-Key": request_id},
        json={"name": "first-endpoint", "model": model or MODELS[0]["id"], "provider": "aws"},
    )
    assert r.status_code == 202, r.text
    d = r.json()
    for _ in range(4):
        app.state.service.tick()
    r = client.get("/api/deployments/" + d["id"])
    assert r.json()["state"] == "ready", r.text
    key = client.post("/api/deployments/" + d["id"] + "/key").json()["api_key"]
    return d, key


def test_complete_flow_and_sdk(setup):
    app, client, _ = setup
    catalog = client.get("/api/catalog").json()
    assert catalog["mode"] == "mock"
    assert len(catalog["providers"]) == 6
    assert sum(p["implemented"] for p in catalog["providers"]) == 1
    d, key = deploy(app, client)
    assert key.startswith("au_mock_")
    public = client.get("/api/deployments/" + d["id"])
    assert key not in public.text and "key_hash" not in public.text
    assert public.headers["cache-control"] == "no-store"
    sdk = OpenAI(api_key=key, base_url="http://testserver/endpoints/" + d["id"] + "/v1", http_client=client)
    assert sdk.models.list().data[0].id == d["model"]
    response = sdk.chat.completions.create(model=d["model"], messages=[{"role": "user", "content": "Hello"}])
    assert "mock response" in response.choices[0].message.content
    assert response.usage is None  # Unknown usage must never become zero usage.
    stream = sdk.chat.completions.create(
        model=d["model"], messages=[{"role": "user", "content": "Hi"}], stream=True
    )
    assert "No GPU" in "".join(c.choices[0].delta.content or "" for c in stream)


def test_key_rotation_and_deletion(setup):
    app, client, _ = setup
    d, key = deploy(app, client)
    url = "/endpoints/" + d["id"] + "/v1/models"
    assert client.get(url, headers={"Authorization": "Bearer wrong"}).status_code == 401
    new = client.post("/api/deployments/" + d["id"] + "/key").json()["api_key"]
    assert new != key
    assert client.get(url, headers={"Authorization": f"Bearer {key}"}).status_code == 401
    assert client.get(url, headers={"Authorization": f"Bearer {new}"}).status_code == 200
    client.delete("/api/deployments/" + d["id"])
    assert client.get(url, headers={"Authorization": f"Bearer {new}"}).status_code == 401
    app.state.service.tick()
    assert client.get("/api/deployments/" + d["id"]).json()["state"] == "deleted"


def test_idempotency_capacity_and_validation(setup):
    _app, client, _ = setup
    spec = {"name": "first-endpoint", "model": MODELS[0]["id"], "provider": "aws"}
    h = {"Idempotency-Key": "same-request"}
    first = client.post("/api/deployments", headers=h, json=spec)
    assert first.status_code == 202
    assert client.post("/api/deployments", headers=h, json=spec).json()["id"] == first.json()["id"]
    assert client.post("/api/deployments", headers=h, json=spec | {"name": "different"}).status_code == 409
    assert (
        client.post(
            "/api/deployments", headers={"Idempotency-Key": "different-request"}, json=spec
        ).status_code
        == 409
    )
    assert client.post("/api/deployments", headers=h, json=spec | {"provider": "firmus"}).status_code == 422
    assert (
        client.post("/api/deployments", headers=h, json=spec | {"model": "arbitrary/model"}).status_code
        == 422
    )
    assert client.post("/api/deployments", headers=h, json=spec | {"region": "us-east-1"}).status_code == 422
    assert client.post("/api/deployments/" + first.json()["id"] + "/key").status_code == 409


def test_restart_recovers_queued_work(setup):
    app, client, settings = setup
    r = client.post(
        "/api/deployments",
        headers={"Idempotency-Key": "restart-request"},
        json={"name": "restart", "model": MODELS[1]["id"], "provider": "aws"},
    )
    d = r.json()
    app.state.service.tick()
    restarted = create_app(settings, start_worker=False)
    for _ in range(4):
        restarted.state.service.tick()
    assert restarted.state.store.get(d["id"])["state"] == "ready"


def test_mock_database_cannot_be_live(setup):
    _, _, settings = setup
    with pytest.raises(ValueError, match="separate DATABASE"):
        create_app(replace(settings, mode="aws"), provider=MockProvider(), start_worker=False)


def test_live_switch_prevents_all_cloud_calls(tmp_path):
    class Forbidden:
        def __getattr__(self, name):
            pytest.fail("Disabled live mode called provider: " + name)

    app = create_app(
        Settings(admin_token=TOKEN, mode="aws", database=str(tmp_path / "live.db")),
        provider=Forbidden(),
        start_worker=False,
    )
    with TestClient(app, headers={"Authorization": f"Bearer {TOKEN}"}) as client:
        r = client.post(
            "/api/deployments",
            headers={"Idempotency-Key": "disabled-request"},
            json={"name": "blocked", "model": MODELS[0]["id"], "provider": "aws"},
        )
        assert r.status_code == 403
        assert app.state.store.list() == []


def test_auth_origin_body_limit_and_no_validation_echo(setup):
    app, _, _ = setup
    with TestClient(app) as client:
        assert client.get("/api/deployments").status_code == 401
        assert client.post("/api/login", json={"token": "wrong"}).status_code == 401
        r = client.post("/api/login", json={"token": TOKEN}, headers={"Origin": "https://evil.example"})
        assert r.status_code == 403
        assert client.post("/api/login", json={"token": TOKEN}).status_code == 200
        assert client.get("/api/deployments").status_code == 200
        r = client.post("/api/login", json={"token": "sensitive-" * 100})
        assert r.status_code == 422 and "sensitive" not in r.text
        assert client.post("/api/login", content="a" * 262145).status_code == 413
        assert client.get("/", headers={"Host": "evil.example"}).status_code == 400


def test_failure_cleans_up_and_does_not_issue_key(setup):
    app, client, _ = setup

    class Failure(MockProvider):
        def ensure_config(self, d):
            raise RuntimeError("Secret upstream request body MUST NOT leak")

    app.state.service.provider = Failure()
    r = client.post(
        "/api/deployments",
        headers={"Idempotency-Key": "failure-request"},
        json={"name": "failure", "model": MODELS[0]["id"], "provider": "aws"},
    )
    for _ in range(6):
        app.state.service.tick()
    result = client.get("/api/deployments/" + r.json()["id"])
    assert result.json()["state"] == "failed"
    assert "MUST NOT" not in result.text
    assert client.post("/api/deployments/" + r.json()["id"] + "/key").status_code == 409


def test_wrong_model_and_expiry(setup):
    app, client, _ = setup
    d, key = deploy(app, client)
    headers = {"Authorization": f"Bearer {key}"}
    r = client.post(
        "/endpoints/" + d["id"] + "/v1/chat/completions",
        headers=headers,
        json={"model": MODELS[1]["id"], "messages": [{"role": "user", "content": "hello"}]},
    )
    assert r.status_code == 400
    with app.state.store.connect() as db:
        db.execute("UPDATE deployments SET expires=0 WHERE id=?", (d["id"],))
    assert client.get("/endpoints/" + d["id"] + "/v1/models", headers=headers).status_code == 503
    app.state.service.tick()
    assert app.state.store.get(d["id"])["state"] == "deleted"


def test_cross_endpoint_key_isolation(setup):
    app, client, _ = setup
    d, key = deploy(app, client)
    client.delete("/api/deployments/" + d["id"])
    app.state.service.tick()
    other, other_key = deploy(app, client, "another-request")
    assert key != other_key
    assert (
        client.get(
            "/endpoints/" + other["id"] + "/v1/models", headers={"Authorization": f"Bearer {key}"}
        ).status_code
        == 401
    )


def test_disabled_live_worker_does_not_resume_provisioning(tmp_path):
    class Forbidden(MockProvider):
        def ensure_model(self, d):
            pytest.fail("Disabled worker attempted paid provisioning")

    settings = Settings(admin_token=TOKEN, mode="aws", database=str(tmp_path / "live.db"))
    app = create_app(settings, provider=Forbidden(), start_worker=False)
    spec = {"name": "paused", "model": MODELS[0]["id"], "provider": "aws", "lifetime_minutes": 60}
    d = app.state.store.create(spec, MODELS[0]["revision"], "queued-before-pause", 1)
    app.state.service.tick()
    assert app.state.store.get(d["id"])["phase"] == 0


def test_supplied_shortlist_metadata_and_all_mock_deployments(setup):
    app, client, _ = setup
    catalog = client.get("/api/catalog").json()
    assert catalog["source"]["date"] == "2026-09-12"
    assert catalog["source"]["version"] == "4.3"
    assert len(catalog["models"]) == 14
    assert [m["score"] for m in catalog["models"]] == [45, 44, 42, 40, 40, 36, 34, 31, 30, 26, 23, 18, 15, 12]
    assert [m["name"] for m in catalog["models"] if m["estimated"]] == ["K2 Horizon 375B A23B"]
    for index, model in enumerate(catalog["models"]):
        assert model["hf_repository"] is None
        assert model["live_eligible"] is False
        d, key = deploy(app, client, f"shortlist-{index:02}", model=model["id"])
        assert d["instance"] is None
        response = client.post(
            "/endpoints/" + d["id"] + "/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model["id"], "messages": [{"role": "user", "content": "Hello"}]},
        )
        assert response.status_code == 200
        assert response.json()["model"] == model["id"]
        client.delete("/api/deployments/" + d["id"])
        app.state.service.tick()


def test_shortlist_cannot_reach_live_provider_even_when_enabled(tmp_path):
    class Forbidden:
        def __getattr__(self, name):
            pytest.fail("Unverified model reached live provider: " + name)

    app = create_app(
        Settings(admin_token=TOKEN, mode="aws", deployments_enabled=True, database=str(tmp_path / "live.db")),
        provider=Forbidden(),
        start_worker=False,
    )
    with TestClient(app, headers={"Authorization": f"Bearer {TOKEN}"}) as client:
        for model in MODELS:
            r = client.post(
                "/api/deployments",
                headers={"Idempotency-Key": "blocked-shortlist"},
                json={"name": "blocked", "model": model["id"], "provider": "aws"},
            )
            assert r.status_code == 422
        assert app.state.store.list() == []
