import threading
import time

from .provider import safe_error


class DeploymentService:
    def __init__(self, store, provider, settings):
        self.store, self.provider, self.settings = store, provider, settings
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True, name="deployment-reconciler")
        self.thread.start()

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=2)

    def run(self):
        while not self.stop.is_set():
            self.tick()
            self.stop.wait(1 if self.settings.mode == "mock" else self.settings.poll_seconds)

    def tick(self):
        with self.lock:
            for deployment in self.store.list():
                if deployment["state"] in {"deleted", "failed"}:
                    continue
                self.reconcile(deployment)

    def reconcile(self, d):
        if time.time() >= d["expires"] and d["state"] != "deleting":
            self.store.update(d["id"], state="deleting", key_hash=None, key_prefix=None)
            self.store.event(d["id"], "Lifetime reached; cleanup requested")
            d["state"] = "deleting"
        try:
            if d["state"] == "deleting":
                if self.provider.cleanup(d):
                    self.store.update(
                        d["id"], state="failed" if d["error"] else "deleted", cleanup_error=None
                    )
                    self.store.event(d["id"], "Cleanup confirmed")
                return
            if d["state"] == "ready":
                # Reconcile out-of-band deletion or failure too.
                if self.provider.status(d) != "InService":
                    self.store.update(
                        d["id"], state="deleting", error="Endpoint is no longer in service", key_hash=None
                    )
                return
            if self.settings.mode == "aws" and not self.settings.deployments_enabled:
                return  # Paused queued work must not create resources after a restart.
            operations = [
                self.provider.ensure_model,
                self.provider.ensure_config,
                self.provider.ensure_endpoint,
            ]
            messages = [
                "Model configuration prepared",
                "Sydney GPU configuration prepared",
                "Endpoint provisioning requested",
            ]
            if d["phase"] < 3:
                operations[d["phase"]](d)
                self.store.update(d["id"], state="provisioning", phase=d["phase"] + 1, failure_count=0)
                self.store.event(d["id"], messages[d["phase"]])
                return
            status = self.provider.status(d)
            if status == "InService":
                self.provider.smoke(d)
                self.store.update(d["id"], state="ready", phase=4, failure_count=0)
                self.store.event(
                    d["id"],
                    "Mock endpoint ready"
                    if self.settings.mode == "mock"
                    else "Model response verified; endpoint ready",
                )
            elif status in {"Failed", "OutOfService", "Missing"}:
                self.store.update(d["id"], state="deleting", error=f"AWS endpoint status: {status}")
                self.store.event(d["id"], "Deployment failed; cleanup requested")
        except Exception as exc:  # noqa: BLE001 -- persist cleanup/retry state for every provider failure
            message = safe_error(exc)
            if d["state"] == "deleting":
                self.store.update(d["id"], cleanup_error=message)
            elif d["failure_count"] >= 2:
                self.store.update(d["id"], state="deleting", error=message, key_hash=None)
                self.store.event(d["id"], "Deployment could not be verified; cleanup requested")
            else:
                self.store.update(d["id"], failure_count=d["failure_count"] + 1)
                self.store.event(d["id"], message + " Retrying.")

    def delete(self, deployment_id):
        with self.lock:
            d = self.store.get(deployment_id)
            if d and d["state"] not in {"deleted", "failed"}:
                self.store.update(deployment_id, state="deleting", key_hash=None, key_prefix=None)
                self.store.event(deployment_id, "Deletion requested; API key revoked")
