import json
import logging
import os
from typing import Any

import boto3

from identity import InvalidCpfError
from service import NrtQueryService, RequestError


LOGGER = logging.getLogger()
LOGGER.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

DYNAMODB_CLIENT = boto3.client("dynamodb")
KMS_CLIENT = boto3.client("kms")
SERVICE = NrtQueryService(
    dynamodb_client=DYNAMODB_CLIENT,
    kms_client=KMS_CLIENT,
    token_table=os.environ["TOKEN_TABLE_NAME"],
    history_table=os.environ["HISTORY_TABLE_NAME"],
    indicators_table=os.environ["INDICATORS_TABLE_NAME"],
    hmac_key_arn=os.environ["HMAC_KEY_ARN"],
    shard_count=int(os.environ.get("AGGREGATE_SHARD_COUNT", "8")),
)


def response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/json; charset=utf-8",
            "cache-control": "no-store",
            "x-content-type-options": "nosniff",
        },
        "body": json.dumps(body, ensure_ascii=False, separators=(",", ":")),
    }


def _json_body(event: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError as error:
        raise RequestError("Request body must be valid JSON.") from error
    if not isinstance(value, dict):
        raise RequestError("Request body must be a JSON object.")
    return value


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    request = event.get("requestContext", {}).get("http", {})
    method = request.get("method", "")
    path = event.get("rawPath", "")

    try:
        if method == "GET" and path == "/health":
            return response(200, {"status": "up", "service": "dengue-nrt-api"})

        if method == "GET" and path == "/v1/indicators":
            query = event.get("queryStringParameters") or {}
            result = SERVICE.indicators(
                scope_type=query.get("scope_type"),
                scope_value=query.get("scope_value"),
                start=query.get("start"),
                end=query.get("end"),
                window_minutes=query.get("window_minutes"),
            )
            LOGGER.info(
                "indicators_read scope_type=%s scope_value=%s start=%s end=%s",
                result["scope_type"],
                result["scope_value"],
                result["start"],
                result["end"],
            )
            return response(200, result)

        if method == "POST" and path == "/v1/patients/history":
            body = _json_body(event)
            cpf = body.get("cpf")
            if not isinstance(cpf, str) or not cpf.strip():
                raise RequestError("cpf is required.")
            try:
                limit = int(body.get("limit", 50))
            except (TypeError, ValueError) as error:
                raise RequestError("limit must be an integer.") from error

            result = SERVICE.patient_history(
                cpf=cpf,
                limit=limit,
                next_token=body.get("next_token"),
            )
            LOGGER.info(
                "patient_history_read found=%s event_count=%s",
                result["found"],
                len(result["events"]),
            )
            return response(200, result)

        return response(404, {"error": "route_not_found"})
    except (InvalidCpfError, RequestError) as error:
        return response(400, {"error": "invalid_request", "message": str(error)})
    except Exception:
        LOGGER.exception("nrt_api_request_failed method=%s path=%s", method, path)
        return response(500, {"error": "internal_error"})
