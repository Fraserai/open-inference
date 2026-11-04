import io
import json
from unittest.mock import Mock

import boto3
import pytest
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from botocore.stub import ANY, Stubber

from app.config import CONNECTION_MODELS as MODELS
from app.config import Settings
from app.provider import AWSProvider


@pytest.fixture
def aws(tmp_path):
    # Explicit inert credentials; Stubber intercepts every request before networking.
    session = boto3.Session(
        aws_access_key_id="testing", aws_secret_access_key="testing", region_name="ap-southeast-2"
    )
    settings = Settings(
        admin_token="x" * 40,
        mode="aws",
        database=str(tmp_path / "test.db"),
        execution_role="arn:aws:iam::123456789012:role/SageMakerExecution",
    )
    return AWSProvider(settings, session=session)


def deployment():
    return {
        "id": "au-abcdef123456",
        "model": MODELS[0]["id"],
        "revision": MODELS[0]["revision"],
        "expires": 1900000000,
    }


def missing(stub, operation, expected):
    stub.add_client_error(
        operation,
        service_error_code="ValidationException",
        service_message="Could not find resource",
        expected_params=expected,
    )


def test_provision_payloads_and_region(aws):
    d = deployment()
    with Stubber(aws.client("sagemaker")) as stub:
        missing(stub, "describe_model", {"ModelName": d["id"]})
        stub.add_response(
            "create_model",
            {"ModelArn": "arn:aws:sagemaker:ap-southeast-2:123456789012:model/" + d["id"]},
            {
                "ModelName": d["id"],
                "ExecutionRoleArn": aws.settings.execution_role,
                "PrimaryContainer": {
                    "Image": aws.settings.image,
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
                "Tags": [{"Key": "ManagedBy", "Value": "AustralianEndpoints"}],
            },
        )
        missing(stub, "describe_endpoint_config", {"EndpointConfigName": d["id"]})
        stub.add_response(
            "create_endpoint_config",
            {"EndpointConfigArn": "arn:aws:sagemaker:ap-southeast-2:123456789012:endpoint-config/" + d["id"]},
            {
                "EndpointConfigName": d["id"],
                "ProductionVariants": [
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
                "Tags": ANY,
            },
        )
        missing(stub, "describe_endpoint", {"EndpointName": d["id"]})
        stub.add_response(
            "create_endpoint",
            {"EndpointArn": "arn:aws:sagemaker:ap-southeast-2:123456789012:endpoint/" + d["id"]},
            {"EndpointName": d["id"], "EndpointConfigName": d["id"], "Tags": ANY},
        )
        aws.ensure_model(d)
        aws.ensure_config(d)
        aws.ensure_endpoint(d)
        stub.assert_no_pending_responses()
    assert aws.client("sagemaker").meta.region_name == "ap-southeast-2"


def test_inference_route_and_response(aws):
    body = {"model": MODELS[0]["id"], "messages": [{"role": "user", "content": "hello"}]}
    response = {"choices": [{"message": {"role": "assistant", "content": "Ready"}}]}
    data = json.dumps(response).encode()
    with Stubber(aws.client("sagemaker-runtime")) as stub:
        stub.add_response(
            "invoke_endpoint",
            {"Body": StreamingBody(io.BytesIO(data), len(data)), "ContentType": "application/json"},
            {
                "EndpointName": deployment()["id"],
                "Body": json.dumps(body).encode(),
                "ContentType": "application/json",
                "CustomAttributes": "route=/v1/chat/completions",
                "Accept": "application/json",
            },
        )
        assert aws.invoke(deployment(), body) == response
        stub.assert_no_pending_responses()


def test_permission_error_is_not_absence(aws):
    with Stubber(aws.client("sagemaker")) as stub:
        stub.add_client_error(
            "describe_model",
            service_error_code="AccessDeniedException",
            expected_params={"ModelName": deployment()["id"]},
        )
        with pytest.raises(ClientError):
            aws.ensure_model(deployment())
        stub.assert_no_pending_responses()


def test_cleanup_does_not_claim_done_while_gpu_exists(aws):
    d = deployment()
    aws.describe = Mock(return_value={"EndpointStatus": "InService"})
    with Stubber(aws.client("sagemaker")) as stub:
        stub.add_response("delete_endpoint", {}, {"EndpointName": d["id"]})
        assert aws.cleanup(d) is False
        stub.assert_no_pending_responses()
    aws.describe = Mock(return_value=None)
    assert aws.cleanup(d) is True
