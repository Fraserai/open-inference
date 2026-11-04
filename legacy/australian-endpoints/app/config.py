import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    admin_token: str
    database: str = "state/endpoints.sqlite3"
    public_url: str = "http://127.0.0.1:8787"
    region: str = "ap-southeast-2"
    execution_role: str = ""
    image: str = (
        "763104351884.dkr.ecr.ap-southeast-2.amazonaws.com/vllm:0.20.2-gpu-py312-cu130-ubuntu22.04-sagemaker"
    )
    mode: str = "mock"
    deployments_enabled: bool = False
    max_active: int = 1
    poll_seconds: float = 15

    def __post_init__(self):
        if self.mode not in {"mock", "aws"}:
            raise ValueError("PROVIDER_MODE must be mock or aws")
        if len(self.admin_token) < 32:
            raise ValueError("ADMIN_TOKEN must contain at least 32 characters")
        if self.region != "ap-southeast-2":
            raise ValueError("This release only deploys to AWS Sydney (ap-southeast-2)")
        url = urlsplit(self.public_url)
        if url.scheme != "https" and not (
            url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1"}
        ):
            raise ValueError("PUBLIC_URL must use HTTPS except on localhost")
        if url.path not in {"", "/"} or url.query or url.fragment or url.username:
            raise ValueError("PUBLIC_URL must be a bare origin")
        if ".dkr.ecr.ap-southeast-2.amazonaws.com/" not in self.image:
            raise ValueError("The container registry must be in Sydney")

    @classmethod
    def from_env(cls):
        from dotenv import load_dotenv

        load_dotenv()
        return cls(
            admin_token=os.environ.get("ADMIN_TOKEN", ""),
            database=os.environ.get("DATABASE", "state/endpoints.sqlite3"),
            public_url=os.environ.get("PUBLIC_URL", "http://127.0.0.1:8787").rstrip("/"),
            mode=os.environ.get("PROVIDER_MODE", "mock"),
            execution_role=os.environ.get("AWS_EXECUTION_ROLE_ARN", ""),
            region=os.environ.get("AWS_REGION", "ap-southeast-2"),
            deployments_enabled=os.environ.get("ENABLE_DEPLOYMENTS", "false").lower() == "true",
        )


CONNECTION_MODELS = [
    {
        "id": "Qwen/Qwen3-0.6B",
        "name": "Qwen3 0.6B",
        "parameters": "0.6B",
        "license": "Apache 2.0",
        "revision": "c1899de289a04d12100db370d81485cdf75e47ca",
        "description": "A small, fast model for validating your first endpoint.",
        "recommended": True,
    },
    {
        "id": "Qwen/Qwen3-4B",
        "name": "Qwen3 4B",
        "parameters": "4B",
        "license": "Apache 2.0",
        "revision": "1cfa9a7208912126459214e8b04321603b3df60c",
        "description": "More capacity for instruction following and everyday chat.",
        "recommended": False,
    },
]
# Transcribed from the user-supplied chart, not a live leaderboard fetch.
# mock/* values are local catalog IDs, never claimed Hugging Face repository IDs.
CATALOG_SOURCE = {
    "title": "Artificial Analysis Intelligence Index — Open Source Models",
    "date": "2026-09-12",
    "version": "4.3",
    "provenance": "User-supplied screenshot; date from filename",
    "scores": "Displayed integer scores, not unrounded source data",
}
MODELS = [
    {
        "id": "mock/glm-5-3",
        "name": "GLM-5.3",
        "evaluation_setting": "max",
        "score": 45,
        "chart_order": 1,
        "estimated": False,
        "revision": "",
        "hf_repository": None,
        "live_eligible": False,
    },
    {
        "id": "mock/kimi-k3",
        "name": "Kimi K3",
        "evaluation_setting": "max",
        "score": 44,
        "chart_order": 2,
        "estimated": False,
        "revision": "",
        "hf_repository": None,
        "live_eligible": False,
    },
    {
        "id": "mock/glm-5-3-flash",
        "name": "GLM-5.3-Flash",
        "evaluation_setting": "",
        "score": 42,
        "chart_order": 3,
        "estimated": False,
        "revision": "",
        "hf_repository": None,
        "live_eligible": False,
    },
    {
        "id": "mock/qwen3-8-2-4t-a95b",
        "name": "Qwen3.8 2.4T A95B",
        "evaluation_setting": "",
        "score": 40,
        "chart_order": 4,
        "estimated": False,
        "revision": "",
        "hf_repository": None,
        "live_eligible": False,
    },
    {
        "id": "mock/deepseek-v4-1-flash",
        "name": "DeepSeek V4.1 Flash",
        "evaluation_setting": "max",
        "score": 40,
        "chart_order": 5,
        "estimated": False,
        "revision": "",
        "hf_repository": None,
        "live_eligible": False,
    },
    {
        "id": "mock/deepseek-v4-pro-0813",
        "name": "DeepSeek V4 Pro 0813",
        "evaluation_setting": "max",
        "score": 36,
        "chart_order": 6,
        "estimated": False,
        "revision": "",
        "hf_repository": None,
        "live_eligible": False,
    },
    {
        "id": "mock/qwen3-8-27b",
        "name": "Qwen3.8 27B",
        "evaluation_setting": "xhigh",
        "score": 34,
        "chart_order": 7,
        "estimated": False,
        "revision": "",
        "hf_repository": None,
        "live_eligible": False,
    },
    {
        "id": "mock/k2-horizon-375b-a23b",
        "name": "K2 Horizon 375B A23B",
        "evaluation_setting": "",
        "score": 31,
        "chart_order": 8,
        "estimated": True,
        "revision": "",
        "hf_repository": None,
        "live_eligible": False,
    },
    {
        "id": "mock/minimax-m3",
        "name": "MiniMax-M3",
        "evaluation_setting": "",
        "score": 30,
        "chart_order": 9,
        "estimated": False,
        "revision": "",
        "hf_repository": None,
        "live_eligible": False,
    },
    {
        "id": "mock/inkling",
        "name": "Inkling",
        "evaluation_setting": "",
        "score": 26,
        "chart_order": 10,
        "estimated": False,
        "revision": "",
        "hf_repository": None,
        "live_eligible": False,
    },
    {
        "id": "mock/nemotron-3-ultra",
        "name": "Nemotron 3 Ultra",
        "evaluation_setting": "",
        "score": 23,
        "chart_order": 11,
        "estimated": False,
        "revision": "",
        "hf_repository": None,
        "live_eligible": False,
    },
    {
        "id": "mock/muse-glimmer",
        "name": "Muse Glimmer",
        "evaluation_setting": "high",
        "score": 18,
        "chart_order": 12,
        "estimated": False,
        "revision": "",
        "hf_repository": None,
        "live_eligible": False,
    },
    {
        "id": "mock/mistral-medium-3-5",
        "name": "Mistral Medium 3.5",
        "evaluation_setting": "",
        "score": 15,
        "chart_order": 13,
        "estimated": False,
        "revision": "",
        "hf_repository": None,
        "live_eligible": False,
    },
    {
        "id": "mock/gpt-oss-120b",
        "name": "gpt-oss-120B",
        "evaluation_setting": "high",
        "score": 12,
        "chart_order": 14,
        "estimated": False,
        "revision": "",
        "hf_repository": None,
        "live_eligible": False,
    },
]

PROVIDERS = [
    {
        "id": "aws",
        "name": "AWS Australia",
        "implemented": True,
        "location": "Sydney",
        "note": "SageMaker · ap-southeast-2",
    },
    *[
        {
            "id": key,
            "name": name,
            "implemented": False,
            "location": "Australia",
            "note": "Integration planned",
        }
        for key, name in [
            ("firmus", "Firmus AI"),
            ("sharon", "Sharon AI"),
            ("navigate", "Navigate Network"),
            ("amaze", "Amaze AI"),
            ("azure", "Microsoft Azure Australia"),
        ]
    ],
]
STATIC = Path(__file__).parent / "static"
