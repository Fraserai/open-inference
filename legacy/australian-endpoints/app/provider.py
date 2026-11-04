"""AWS Sydney only. No simulated provider in the application runtime."""

import json
import re

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


class ProviderError(RuntimeError):
    pass


def safe_error(exc):
    # Never persist raw exception text: cloud errors can echo request bodies.
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "AWS error")
        return f"AWS {code}. Check IAM, Sydney quota/capacity, and the SageMaker console."
    if isinstance(exc, ProviderError):
        return str(exc)
    return f"Provider operation failed ({type(exc).__name__}); retry or inspect AWS."


class AWSProvider:
    def __init__(self, settings, session=None):
        self.settings = settings
        self.session = session or boto3.Session(region_name=settings.region)
        self.clients = {}

    def client(self, name):
        if name not in self.clients:
            self.clients[name] = self.session.client(
                name,
                region_name=self.settings.region,
                config=Config(
                    connect_timeout=5,
                    read_timeout=75 if name == "sagemaker-runtime" else 15,
                    retries={"mode": "standard", "max_attempts": 2},
                ),
            )
        return self.clients[name]

    def preflight(self):
        checks = []
        role = self.settings.execution_role
        if not re.fullmatch(r"arn:aws:iam::\d{12}:role/[A-Za-z0-9_+=,.@/\-]+", role):
            checks.append(
                {
                    "ok": False,
                    "label": "SageMaker execution role",
                    "detail": "Set AWS_EXECUTION_ROLE_ARN on the server.",
                }
            )
        else:
            checks.append(
                {
                    "ok": True,
                    "label": "SageMaker execution role",
                    "detail": "Configured; PassRole is checked by AWS during deployment.",
                }
            )
        try:
            credentials = self.session.get_credentials()
            if credentials is None:
                raise ProviderError("Connect an AWS profile, SSO session, or workload role on the server.")
            identity = self.client("sts").get_caller_identity()
            self.client("sagemaker").list_endpoints(MaxResults=1)
            checks.append(
                {
                    "ok": True,
                    "label": "AWS connection",
                    "detail": f"Account {identity['Account']} · Sydney API reachable",
                }
            )
        except Exception as exc:  # noqa: BLE001 -- return safe connection status without exposing cloud errors
            checks.append({"ok": False, "label": "AWS connection", "detail": safe_error(exc)})
        checks.append(
            {
                "ok": self.settings.deployments_enabled,
                "label": "Live deployment switch",
                "detail": "Enabled"
                if self.settings.deployments_enabled
                else "Set ENABLE_DEPLOYMENTS=true after reviewing AWS charges.",
            }
        )
        return {
            "ready": all(c["ok"] for c in checks),
            "checks": checks,
            "note": "GPU quota, capacity and image availability are verified when AWS provisions the endpoint. No resources were created by this check.",
        }

    def describe(self, kind, name):
        key = {"model": "ModelName", "endpoint_config": "EndpointConfigName", "endpoint": "EndpointName"}[
            kind
        ]
        try:
            return getattr(self.client("sagemaker"), "describe_" + kind)(**{key: name})
        except ClientError as exc:
            error = exc.response.get("Error", {})
            # ValidationException has many meanings; only absence is safe to suppress.
            message = error.get("Message", "").lower()
            if error.get("Code") == "ResourceNotFound" or (
                error.get("Code") == "ValidationException"
                and any(s in message for s in ["could not find", "does not exist", "not found"])
            ):
                return None
            raise

    def ensure_model(self, d):
        if self.describe("model", d["id"]):
            return
        self.client("sagemaker").create_model(
            ModelName=d["id"],
            ExecutionRoleArn=self.settings.execution_role,
            PrimaryContainer={
                "Image": self.settings.image,
                "Environment": {
                    "HF_MODEL_ID": d["model"],
                    "SM_VLLM_REVISION": d["revision"],
                    "SM_VLLM_HOST": "0.0.0.0",
                    "SM_VLLM_TENSOR_PARALLEL_SIZE": "1",
                    "SM_VLLM_MAX_MODEL_LEN": "8192",
                    "SM_VLLM_MAX_NUM_SEQS": "4",
                    "SM_VLLM_GPU_MEMORY_UTILIZATION": "0.85",
                    "SM_VLLM_ENABLE_AUTO_TOOL_CHOICE": "true",
                    "SM_VLLM_TOOL_CALL_PARSER": "hermes",
                },
            },
            Tags=[{"Key": "ManagedBy", "Value": "AustralianEndpoints"}],
        )

    def ensure_config(self, d):
        if self.describe("endpoint_config", d["id"]):
            return
        self.client("sagemaker").create_endpoint_config(
            EndpointConfigName=d["id"],
            ProductionVariants=[
                {
                    "VariantName": "primary",
                    "ModelName": d["id"],
                    "InstanceType": "ml.g6.2xlarge",
                    "InitialInstanceCount": 1,
                    "InitialVariantWeight": 1,
                    "VolumeSizeInGB": 60,
                    "ContainerStartupHealthCheckTimeoutInSeconds": 900,
                    "ModelDataDownloadTimeoutInSeconds": 900,
                }
            ],
            Tags=[{"Key": "ManagedBy", "Value": "AustralianEndpoints"}],
        )

    def ensure_endpoint(self, d):
        if self.describe("endpoint", d["id"]):
            return
        self.client("sagemaker").create_endpoint(
            EndpointName=d["id"],
            EndpointConfigName=d["id"],
            Tags=[
                {"Key": "ManagedBy", "Value": "AustralianEndpoints"},
                {"Key": "ExpiresAtEpoch", "Value": str(int(d["expires"]))},
            ],
        )

    def status(self, d):
        item = self.describe("endpoint", d["id"])
        return item["EndpointStatus"] if item else "Missing"

    def invoke(self, d, body):
        args = {
            "EndpointName": d["id"],
            "ContentType": "application/json",
            "Body": json.dumps(body).encode(),
            "CustomAttributes": "route=/v1/chat/completions",
        }
        if body.get("stream"):
            return self.client("sagemaker-runtime").invoke_endpoint_with_response_stream(**args)["Body"]
        response = self.client("sagemaker-runtime").invoke_endpoint(**args, Accept="application/json")
        try:
            return json.loads(response["Body"].read())
        finally:
            response["Body"].close()

    def smoke(self, d):
        response = self.invoke(
            d,
            {
                "model": d["model"],
                "messages": [{"role": "user", "content": "Reply with the word ready."}],
                "max_tokens": 32,
                "chat_template_kwargs": {"enable_thinking": False},
            },
        )
        if not response.get("choices") or not response["choices"][0].get("message", {}).get("content"):
            raise ProviderError("The model has not returned a valid chat completion yet.")

    def cleanup(self, d):
        endpoint = self.describe("endpoint", d["id"])
        if endpoint:
            if endpoint["EndpointStatus"] != "Deleting":
                self.client("sagemaker").delete_endpoint(EndpointName=d["id"])
            return False  # Confirm absence on a subsequent reconciliation.
        for kind, parameter in [("endpoint_config", "EndpointConfigName"), ("model", "ModelName")]:
            if self.describe(kind, d["id"]):
                getattr(self.client("sagemaker"), "delete_" + kind)(**{parameter: d["id"]})
        return not self.describe("endpoint_config", d["id"]) and not self.describe("model", d["id"])
