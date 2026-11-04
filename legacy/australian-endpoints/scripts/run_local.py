"""Start the no-cloud local sandbox. This launcher always forces mock mode."""

import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
state = ROOT / "state"
state.mkdir(mode=0o700, exist_ok=True)
token_file = state / "admin-token"
if not token_file.exists():
    token_file.write_text(secrets.token_urlsafe(40))
    token_file.chmod(0o600)
os.environ["ADMIN_TOKEN"] = token_file.read_text().strip()
os.environ["PROVIDER_MODE"] = "mock"
os.environ["ENABLE_DEPLOYMENTS"] = "false"
os.environ["PUBLIC_URL"] = "http://127.0.0.1:8787"
os.environ["DATABASE"] = str(state / "mock.sqlite3")

if __name__ == "__main__":
    import uvicorn

    print("Local mock sandbox: http://127.0.0.1:8787 — no AWS calls or paid resources")
    uvicorn.run("app.main:create_app", factory=True, host="127.0.0.1", port=8787, access_log=False)
