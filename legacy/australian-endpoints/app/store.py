import hashlib
import json
import os
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = path
        self.lock = threading.RLock()
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS deployments (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, model TEXT NOT NULL, revision TEXT NOT NULL,
              provider TEXT NOT NULL, state TEXT NOT NULL, phase INTEGER NOT NULL DEFAULT 0,
              created REAL NOT NULL, expires REAL NOT NULL, updated REAL NOT NULL,
              error TEXT, cleanup_error TEXT, key_hash TEXT, key_prefix TEXT,
              request_id TEXT NOT NULL UNIQUE, spec_hash TEXT NOT NULL,
              failure_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, deployment_id TEXT NOT NULL,
              at REAL NOT NULL, message TEXT NOT NULL
            );
            """)
        os.chmod(path, 0o600)

    @contextmanager
    def connect(self):
        with self.lock:
            db = sqlite3.connect(self.path, timeout=10)
            db.row_factory = sqlite3.Row
            try:
                with db:
                    yield db
            finally:
                db.close()

    def list(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM deployments ORDER BY created DESC")]

    def get(self, deployment_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM deployments WHERE id=?", (deployment_id,)).fetchone()
            return dict(row) if row else None

    def create(self, spec, revision, request_id, maximum):
        now = time.time()
        spec_hash = digest(json.dumps(spec, sort_keys=True))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM deployments WHERE request_id=?", (request_id,)).fetchone()
            if old:
                if old["spec_hash"] != spec_hash:
                    raise ValueError("This request ID already belongs to another deployment specification")
                return dict(old)
            count = db.execute(
                "SELECT count(*) FROM deployments WHERE state NOT IN ('deleted','failed')"
            ).fetchone()[0]
            if count >= maximum:
                raise ValueError("Delete your existing endpoint before deploying another one")
            deployment_id = "au-" + secrets.token_hex(10)
            db.execute(
                """INSERT INTO deployments
              (id,name,model,revision,provider,state,created,expires,updated,request_id,spec_hash)
              VALUES (?,?,?,?,?,'queued',?,?,?,?,?)""",
                (
                    deployment_id,
                    spec["name"],
                    spec["model"],
                    revision,
                    spec["provider"],
                    now,
                    now + spec["lifetime_minutes"] * 60,
                    now,
                    request_id,
                    spec_hash,
                ),
            )
            db.execute(
                "INSERT INTO events(deployment_id,at,message) VALUES(?,?,?)",
                (deployment_id, now, "Deployment queued in Sydney"),
            )
        return self.get(deployment_id)

    def update(self, deployment_id, **values):
        allowed = {"state", "phase", "error", "cleanup_error", "key_hash", "key_prefix", "failure_count"}
        if not set(values) <= allowed:
            raise ValueError("Invalid update")
        values["updated"] = time.time()
        with self.connect() as db:
            db.execute(
                "UPDATE deployments SET " + ",".join(f"{k}=?" for k in values) + " WHERE id=?",
                (*values.values(), deployment_id),
            )

    def event(self, deployment_id, message):
        with self.connect() as db:
            db.execute(
                "INSERT INTO events(deployment_id,at,message) VALUES(?,?,?)",
                (deployment_id, time.time(), message),
            )

    def events(self, deployment_id):
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT at,message FROM events WHERE deployment_id=? ORDER BY id", (deployment_id,)
                )
            ]

    def issue_key(self, deployment_id, mode="mock"):
        key = ("au_mock_" if mode == "mock" else "au_sk_") + secrets.token_urlsafe(32)
        self.update(deployment_id, key_hash=digest(key), key_prefix=key[:14])
        self.event(deployment_id, "API key issued; previous key revoked")
        return key
