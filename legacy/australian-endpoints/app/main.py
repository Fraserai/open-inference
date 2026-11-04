import hmac
import secrets
import time
from contextlib import asynccontextmanager
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import CATALOG_SOURCE, CONNECTION_MODELS, MODELS, PROVIDERS, STATIC, Settings
from .mock_provider import MockProvider
from .provider import AWSProvider, safe_error
from .service import DeploymentService
from .store import Store, digest


class DeploymentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=48, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    model: str
    provider: str
    lifetime_minutes: int = Field(default=60, ge=20, le=120)


class Login(BaseModel):
    token: str = Field(max_length=256)


class ChatInput(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str
    messages: list[dict] = Field(min_length=1, max_length=100)
    stream: bool = False
    max_tokens: int | None = Field(default=None, ge=1, le=4096)


def create_app(settings=None, provider=None, start_worker=True):
    settings = settings or Settings.from_env()
    store = Store(settings.database)
    with store.connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        old = db.execute("SELECT value FROM metadata WHERE key='mode'").fetchone()
        if old and old[0] != settings.mode:
            raise ValueError(
                "Use a separate DATABASE when changing PROVIDER_MODE; mock state cannot become live state"
            )
        db.execute("INSERT OR IGNORE INTO metadata VALUES ('mode',?)", (settings.mode,))
    provider = provider or (MockProvider() if settings.mode == "mock" else AWSProvider(settings))
    service = DeploymentService(store, provider, settings)
    sessions = {}

    @asynccontextmanager
    async def lifespan(app):
        if start_worker:
            service.start()
        yield
        service.close()

    app = FastAPI(title="Australian Endpoints", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.store, app.state.service, app.state.provider = store, service, provider
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=[urlsplit(settings.public_url).hostname, "testserver"]
    )

    @app.middleware("http")
    async def guard(request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin != settings.public_url:
                return JSONResponse(
                    {"error": {"message": "Cross-origin writes are not allowed"}}, status_code=403
                )
        # Bound bodies, including chunked requests, before JSON parsing.
        if request.method in {"POST", "PUT", "PATCH"}:
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 262144:
                    return JSONResponse({"error": {"message": "Request exceeds 256 KiB"}}, status_code=413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse(
            {
                "error": {
                    "message": str(exc.detail),
                    "type": "invalid_request_error",
                    "code": str(exc.status_code),
                }
            },
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Do not echo credential/prompt input in validation responses.
        return JSONResponse(
            {"error": {"message": "Invalid request fields", "type": "invalid_request_error"}}, status_code=422
        )

    def admin(request: Request):
        if settings.mode == "mock" and request.client and request.client.host in {"127.0.0.1", "::1"}:
            return  # Local demo only; never enabled in aws mode.
        bearer = request.headers.get("authorization", "").removeprefix("Bearer ")
        session = request.cookies.get("au_session", "")
        if (
            hmac.compare_digest(bearer, settings.admin_token)
            or sessions.get(digest(session), 0) > time.time()
        ):
            return
        raise HTTPException(401, "Sign in with the local admin token")

    def find(deployment_id):
        d = store.get(deployment_id)
        if not d:
            raise HTTPException(404, "Endpoint not found")
        return d

    def visible(d):
        return {k: v for k, v in d.items() if k not in {"key_hash", "request_id", "spec_hash"}} | {
            "mode": settings.mode,
            "base_url": f"{settings.public_url}/endpoints/{d['id']}/v1",
            "region": settings.region,
            "instance": None if d["model"].startswith("mock/") else "ml.g6.2xlarge",
            "events": store.events(d["id"]),
        }

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/healthz")
    def health():
        return {"ok": True, "mode": settings.mode}

    @app.get("/api/catalog")
    def catalog():
        return {
            "models": MODELS if settings.mode == "mock" else CONNECTION_MODELS,
            "source": CATALOG_SOURCE if settings.mode == "mock" else None,
            "providers": PROVIDERS,
            "mode": settings.mode,
            "deployments_enabled": settings.deployments_enabled if settings.mode == "aws" else True,
        }

    @app.post("/api/login")
    def login(data: Login):
        if not hmac.compare_digest(data.token, settings.admin_token):
            raise HTTPException(401, "Invalid admin token")
        now = time.time()
        for key, expiry in list(sessions.items()):
            if expiry <= now:
                sessions.pop(key, None)
        token = secrets.token_urlsafe(32)
        sessions[digest(token)] = now + 3600
        response = JSONResponse({"ok": True})
        response.set_cookie(
            "au_session",
            token,
            httponly=True,
            samesite="strict",
            secure=settings.public_url.startswith("https"),
            max_age=3600,
        )
        return response

    @app.get("/api/connection", dependencies=[Depends(admin)])
    def connection():
        return provider.preflight() | {"mode": settings.mode}

    @app.get("/api/deployments", dependencies=[Depends(admin)])
    def deployments():
        return [visible(d) for d in store.list()]

    @app.post("/api/deployments", status_code=202, dependencies=[Depends(admin)])
    def deploy(data: DeploymentInput, idempotency_key: str = Header(min_length=8, max_length=100)):
        if data.provider != "aws":
            raise HTTPException(422, "Only the AWS Sydney adapter is implemented in this release")
        model = next((m for m in MODELS + CONNECTION_MODELS if m["id"] == data.model), None)
        if not model:
            raise HTTPException(422, "Select a supported Hugging Face model")
        if settings.mode == "aws":
            if not settings.deployments_enabled:
                raise HTTPException(403, "Live deployment is disabled. No paid resource was created.")
            if model not in CONNECTION_MODELS:
                raise HTTPException(
                    422, "This model is mock-only: repository, licence, runtime and GPU sizing are unverified"
                )
            if not provider.preflight()["ready"]:
                raise HTTPException(409, "Connect AWS and resolve connection checks before deploying")
        with service.lock:
            try:
                d = store.create(data.model_dump(), model["revision"], idempotency_key, settings.max_active)
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from exc
        return visible(d)

    @app.get("/api/deployments/{deployment_id}", dependencies=[Depends(admin)])
    def deployment(deployment_id: str):
        return visible(find(deployment_id))

    @app.delete("/api/deployments/{deployment_id}", dependencies=[Depends(admin)])
    def delete(deployment_id: str):
        find(deployment_id)
        service.delete(deployment_id)
        return visible(find(deployment_id))

    @app.post("/api/deployments/{deployment_id}/key", dependencies=[Depends(admin)])
    def key(deployment_id: str):
        with service.lock:
            d = find(deployment_id)
            if d["state"] != "ready":
                raise HTTPException(409, "Endpoint is not ready")
            return {
                "api_key": store.issue_key(deployment_id, settings.mode),
                "mode": settings.mode,
                "base_url": visible(d)["base_url"],
            }

    def endpoint_auth(deployment_id: str, request: Request):
        d = find(deployment_id)
        value = request.headers.get("authorization", "")
        if (
            not value.startswith("Bearer ")
            or not d["key_hash"]
            or not hmac.compare_digest(digest(value[7:]), d["key_hash"])
        ):
            raise HTTPException(401, "Invalid endpoint API key")
        if d["state"] != "ready" or d["expires"] <= time.time():
            raise HTTPException(503, "Endpoint is not ready")
        return d

    @app.get("/endpoints/{deployment_id}/v1/models")
    def models(d: Annotated[dict, Depends(endpoint_auth)]):
        return {
            "object": "list",
            "data": [
                {
                    "id": d["model"],
                    "object": "model",
                    "created": int(d["created"]),
                    "owned_by": d["model"].split("/")[0],
                }
            ],
        }

    @app.post("/endpoints/{deployment_id}/v1/chat/completions")
    def chat(data: ChatInput, d: Annotated[dict, Depends(endpoint_auth)]):
        if data.model != d["model"]:
            raise HTTPException(400, "The model must match this endpoint's deployed model")
        body = data.model_dump(exclude_none=True)
        body.setdefault("max_tokens", 512)
        try:
            result = provider.invoke(d, body)
        except Exception as exc:
            raise HTTPException(502, safe_error(exc)) from exc
        headers = {"X-Inference-Mode": settings.mode}
        if not data.stream:
            return JSONResponse(result, headers=headers)

        def stream():
            try:
                for event in result:
                    if "PayloadPart" in event:
                        yield event["PayloadPart"]["Bytes"]
                    else:
                        yield b'data: {"error":{"message":"Upstream stream failed"}}\n\n'
                        return
            except Exception:  # noqa: BLE001 -- convert arbitrary transport failures into a safe SSE error
                yield b'data: {"error":{"message":"Upstream connection ended"}}\n\n'
            finally:
                result.close()

        return StreamingResponse(stream(), media_type="text/event-stream", headers=headers)

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
