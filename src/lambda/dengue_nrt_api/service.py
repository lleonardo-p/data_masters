import base64
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from identity import generate_cpf_fingerprint, normalize_cpf


RISK_COUNTERS = (
    "risk_blue",
    "risk_green",
    "risk_yellow",
    "risk_orange",
    "risk_red",
)
SCOPE_TYPES = {"GLOBAL", "STATE", "MUNICIPALITY", "UNIT", "AGE_GROUP"}


class RequestError(ValueError):
    pass


def _deserialize_item(item: dict[str, Any]) -> dict[str, Any]:
    def deserialize(value: dict[str, Any]) -> Any:
        if "S" in value:
            return value["S"]
        if "N" in value:
            number = Decimal(value["N"])
            return int(number) if number % 1 == 0 else float(number)
        if "BOOL" in value:
            return value["BOOL"]
        if "NULL" in value:
            return None
        if "L" in value:
            return [deserialize(element) for element in value["L"]]
        if "M" in value:
            return {key: deserialize(element) for key, element in value["M"].items()}
        raise ValueError("Unsupported DynamoDB attribute type.")

    return {key: deserialize(value) for key, value in item.items()}


def _encode_next_token(key: dict[str, Any] | None) -> str | None:
    if not key:
        return None
    payload = json.dumps(key, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


def _decode_next_token(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        decoded = base64.urlsafe_b64decode(value.encode("ascii"))
        key = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeError, json.JSONDecodeError) as error:
        raise RequestError("next_token is invalid.") from error

    if not isinstance(key, dict):
        raise RequestError("next_token is invalid.")
    return key


def _minute(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise RequestError("start and end must be ISO-8601 timestamps.") from error

    if parsed.tzinfo is None:
        raise RequestError("start and end must contain a timezone.")
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:00Z")


def indicator_window(
    start: str | None,
    end: str | None,
    window_minutes: str | None,
    now: datetime | None = None,
) -> tuple[str, str]:
    if bool(start) != bool(end):
        raise RequestError("start and end must be provided together.")

    if start and end:
        start_bucket = _minute(start)
        end_bucket = _minute(end)
    else:
        try:
            minutes = int(window_minutes or "2")
        except ValueError as error:
            raise RequestError("window_minutes must be an integer.") from error
        if minutes < 1 or minutes > 1440:
            raise RequestError("window_minutes must be between 1 and 1440.")

        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        end_bucket = current.strftime("%Y-%m-%dT%H:%M:00Z")
        start_bucket = (current - timedelta(minutes=minutes - 1)).strftime(
            "%Y-%m-%dT%H:%M:00Z"
        )

    if start_bucket > end_bucket:
        raise RequestError("start must be earlier than or equal to end.")
    return start_bucket, end_bucket


def scope_base(scope_type: str | None, scope_value: str | None) -> str:
    normalized_type = (scope_type or "GLOBAL").strip().upper()
    if normalized_type not in SCOPE_TYPES:
        raise RequestError("scope_type is invalid.")

    if normalized_type == "GLOBAL":
        if scope_value:
            raise RequestError("scope_value is not allowed for GLOBAL.")
        return "GLOBAL"

    value = (scope_value or "").strip().upper()
    if not value or "#" in value:
        raise RequestError("scope_value is required and cannot contain '#'.")
    return f"{normalized_type}#{value}"


class NrtQueryService:
    def __init__(
        self,
        dynamodb_client: Any,
        kms_client: Any,
        token_table: str,
        history_table: str,
        indicators_table: str,
        hmac_key_arn: str,
        shard_count: int = 8,
    ) -> None:
        self.dynamodb = dynamodb_client
        self.kms = kms_client
        self.token_table = token_table
        self.history_table = history_table
        self.indicators_table = indicators_table
        self.hmac_key_arn = hmac_key_arn
        self.shard_count = shard_count

    def indicators(
        self,
        scope_type: str | None,
        scope_value: str | None,
        start: str | None,
        end: str | None,
        window_minutes: str | None,
    ) -> dict[str, Any]:
        base = scope_base(scope_type, scope_value)
        start_bucket, end_bucket = indicator_window(
            start,
            end,
            window_minutes,
        )
        totals = {"total_triages": 0, **{key: 0 for key in RISK_COUNTERS}}
        minute_totals: dict[str, dict[str, int]] = {}

        for shard in range(self.shard_count):
            scope_key = f"{base}#SHARD#{shard:02d}"
            last_key = None
            while True:
                arguments: dict[str, Any] = {
                    "TableName": self.indicators_table,
                    "KeyConditionExpression": (
                        "scope_key = :scope AND "
                        "minute_bucket BETWEEN :start AND :end"
                    ),
                    "ExpressionAttributeValues": {
                        ":scope": {"S": scope_key},
                        ":start": {"S": start_bucket},
                        ":end": {"S": end_bucket},
                    },
                    "ConsistentRead": False,
                }
                if last_key:
                    arguments["ExclusiveStartKey"] = last_key

                response = self.dynamodb.query(**arguments)
                for raw_item in response.get("Items", []):
                    item = _deserialize_item(raw_item)
                    minute = item["minute_bucket"]
                    minute_values = minute_totals.setdefault(
                        minute,
                        {"total_triages": 0, **{key: 0 for key in RISK_COUNTERS}},
                    )
                    for counter in totals:
                        value = int(item.get(counter, 0))
                        totals[counter] += value
                        minute_values[counter] += value

                last_key = response.get("LastEvaluatedKey")
                if not last_key:
                    break

        return {
            "scope_type": base.split("#", 1)[0],
            "scope_value": None if base == "GLOBAL" else base.split("#", 1)[1],
            "start": start_bucket,
            "end": end_bucket,
            "totals": totals,
            "series": [
                {"minute": minute, **minute_totals[minute]}
                for minute in sorted(minute_totals)
            ],
        }

    def patient_history(
        self,
        cpf: str,
        limit: int,
        next_token: str | None,
    ) -> dict[str, Any]:
        if limit < 1 or limit > 100:
            raise RequestError("limit must be between 1 and 100.")

        normalized = normalize_cpf(cpf)
        fingerprint = generate_cpf_fingerprint(
            self.kms,
            self.hmac_key_arn,
            normalized,
        )
        token_response = self.dynamodb.get_item(
            TableName=self.token_table,
            Key={"cpf_fingerprint": {"S": fingerprint}},
            ConsistentRead=True,
        )
        token_item = token_response.get("Item")
        if not token_item:
            return {"found": False, "events": [], "next_token": None}

        patient_token = token_item["patient_token"]["S"]
        arguments: dict[str, Any] = {
            "TableName": self.history_table,
            "KeyConditionExpression": "patient_token = :token",
            "ExpressionAttributeValues": {":token": {"S": patient_token}},
            "ScanIndexForward": False,
            "Limit": limit,
            "ConsistentRead": True,
        }
        exclusive_start_key = _decode_next_token(next_token)
        if exclusive_start_key:
            arguments["ExclusiveStartKey"] = exclusive_start_key

        response = self.dynamodb.query(**arguments)
        events = []
        for raw_item in response.get("Items", []):
            item = _deserialize_item(raw_item)
            item.pop("patient_token", None)
            item.pop("event_sort_key", None)
            item.pop("expires_at", None)
            events.append(item)

        return {
            "found": True,
            "events": events,
            "next_token": _encode_next_token(response.get("LastEvaluatedKey")),
        }
