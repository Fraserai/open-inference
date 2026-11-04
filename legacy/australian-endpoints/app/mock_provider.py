"""Explicit local simulation. Never constructs an AWS client or makes network calls."""

import json
import time


class MockStream:
    def __init__(self, deployment):
        self.deployment = deployment

    def __iter__(self):
        for text in ["This is a ", "mock response. ", "No GPU or model is running."]:
            chunk = {
                "id": "chatcmpl-mock-" + self.deployment["id"],
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": self.deployment["model"],
                "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
            }
            yield {"PayloadPart": {"Bytes": ("data: " + json.dumps(chunk) + "\n\n").encode()}}
        chunk["choices"] = [{"index": 0, "delta": {}, "finish_reason": "stop"}]
        yield {"PayloadPart": {"Bytes": ("data: " + json.dumps(chunk) + "\n\n").encode()}}
        yield {"PayloadPart": {"Bytes": b"data: [DONE]\n\n"}}

    def close(self):
        pass


class MockProvider:
    def preflight(self):
        return {
            "ready": True,
            "checks": [
                {"ok": True, "label": "Local simulation", "detail": "No AWS connection. No GPU. No charges."}
            ],
            "note": "Deployment and model responses are simulated. The local API and its key authentication are real.",
        }

    def ensure_model(self, d):
        pass

    def ensure_config(self, d):
        pass

    def ensure_endpoint(self, d):
        pass

    def status(self, d):
        return "InService"

    def smoke(self, d):
        pass

    def cleanup(self, d):
        return True

    def invoke(self, d, body):
        if body.get("stream"):
            return MockStream(d)
        return {
            "id": "chatcmpl-mock-" + d["id"],
            "object": "chat.completion",
            "created": int(time.time()),
            "model": d["model"],
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "This is a mock response. No GPU or Hugging Face model is running.",
                    },
                    "finish_reason": "stop",
                }
            ],
        }
