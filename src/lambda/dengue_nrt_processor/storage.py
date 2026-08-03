import hashlib
import time
from datetime import datetime, timezone
from typing import Any

from identity import new_patient_token


def _aws_error_code(error: Exception) -> str | None:
    response = getattr(error, "response", {})
    return response.get("Error", {}).get("Code")


def age_group(age: int) -> str:
    if age <= 9:
        return "00-09"
    if age <= 19:
        return "10-19"
    if age <= 29:
        return "20-29"
    if age <= 39:
        return "30-39"
    if age <= 49:
        return "40-49"
    if age <= 59:
        return "50-59"
    if age <= 69:
        return "60-69"
    if age <= 79:
        return "70-79"
    return "80+"


def minute_bucket(notification_at: str) -> str:
    parsed = datetime.fromisoformat(notification_at.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:00Z")


def aggregate_scopes(event: dict[str, Any], shard_count: int) -> list[str]:
    event_hash = hashlib.sha256(event["event_id"].encode("utf-8")).hexdigest()
    shard = int(event_hash[:8], 16) % shard_count
    shard_suffix = f"SHARD#{shard:02d}"
    unit = event["health_unit"]
    patient = event["patient"]

    return [
        f"GLOBAL#{shard_suffix}",
        f"STATE#{unit['state']}#{shard_suffix}",
        f"MUNICIPALITY#{unit['municipality_code']}#{shard_suffix}",
        f"UNIT#{unit['unit_id']}#{shard_suffix}",
        f"AGE_GROUP#{age_group(patient['age'])}#{shard_suffix}",
    ]


class NrtStore:
    def __init__(
        self,
        dynamodb_client: Any,
        token_table: str,
        history_table: str,
        indicators_table: str,
        idempotency_table: str,
        hmac_key_version: str,
        aggregate_shard_count: int = 8,
    ) -> None:
        self.client = dynamodb_client
        self.token_table = token_table
        self.history_table = history_table
        self.indicators_table = indicators_table
        self.idempotency_table = idempotency_table
        self.hmac_key_version = hmac_key_version
        self.aggregate_shard_count = aggregate_shard_count

    def get_or_create_patient_token(self, cpf_fingerprint: str) -> str:
        response = self.client.get_item(
            TableName=self.token_table,
            Key={"cpf_fingerprint": {"S": cpf_fingerprint}},
            ConsistentRead=True,
        )

        if response.get("Item"):
            return response["Item"]["patient_token"]["S"]

        patient_token = new_patient_token()
        now = datetime.now(timezone.utc).isoformat()
        expires_at = int(time.time()) + (365 * 24 * 60 * 60)

        try:
            self.client.put_item(
                TableName=self.token_table,
                Item={
                    "cpf_fingerprint": {"S": cpf_fingerprint},
                    "patient_token": {"S": patient_token},
                    "hmac_key_version": {"S": self.hmac_key_version},
                    "created_at": {"S": now},
                    "updated_at": {"S": now},
                    "expires_at": {"N": str(expires_at)},
                },
                ConditionExpression="attribute_not_exists(cpf_fingerprint)",
            )
            return patient_token
        except Exception as error:
            if _aws_error_code(error) != "ConditionalCheckFailedException":
                raise

        response = self.client.get_item(
            TableName=self.token_table,
            Key={"cpf_fingerprint": {"S": cpf_fingerprint}},
            ConsistentRead=True,
        )
        return response["Item"]["patient_token"]["S"]

    def persist_event(
        self,
        event: dict[str, Any],
        patient_token: str,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        now_epoch = int(time.time())
        event_id = event["event_id"]
        triage = event["triage"]
        unit = event["health_unit"]
        patient = event["patient"]
        bucket = minute_bucket(triage["notification_at"])
        risk_counter = f"risk_{triage['risk_level'].lower()}"

        transaction_items: list[dict[str, Any]] = [
            {
                "Put": {
                    "TableName": self.idempotency_table,
                    "Item": {
                        "event_id": {"S": event_id},
                        "processed_at": {"S": now},
                        "expires_at": {"N": str(now_epoch + (7 * 24 * 60 * 60))},
                    },
                    "ConditionExpression": "attribute_not_exists(event_id)",
                }
            },
            {
                "Put": {
                    "TableName": self.history_table,
                    "Item": {
                        "patient_token": {"S": patient_token},
                        "event_sort_key": {
                            "S": f"{triage['notification_at']}#{event_id}"
                        },
                        "event_id": {"S": event_id},
                        "triage_id": {"S": event["triage_id"]},
                        "event_time": {"S": event["event_time"]},
                        "notification_at": {"S": triage["notification_at"]},
                        "symptoms_start_date": {
                            "S": triage["symptoms_start_date"]
                        },
                        "disease_code": {"S": triage["disease_code"]},
                        "case_classification": {
                            "S": triage["case_classification"]
                        },
                        "risk_level": {"S": triage["risk_level"]},
                        "age": {"N": str(patient["age"])},
                        "age_group": {"S": age_group(patient["age"])},
                        "sex": {"S": patient["sex"]},
                        "unit_id": {"S": unit["unit_id"]},
                        "unit_name": {"S": unit["unit_name"]},
                        "municipality_code": {"S": unit["municipality_code"]},
                        "municipality_name": {"S": unit["municipality_name"]},
                        "state": {"S": unit["state"]},
                        "source_system": {"S": event["source_system"]},
                        "schema_version": {"S": event["schema_version"]},
                        "created_at": {"S": now},
                        "expires_at": {
                            "N": str(now_epoch + (90 * 24 * 60 * 60))
                        },
                    },
                    "ConditionExpression": (
                        "attribute_not_exists(patient_token) AND "
                        "attribute_not_exists(event_sort_key)"
                    ),
                }
            },
        ]

        for scope in aggregate_scopes(event, self.aggregate_shard_count):
            transaction_items.append(
                {
                    "Update": {
                        "TableName": self.indicators_table,
                        "Key": {
                            "scope_key": {"S": scope},
                            "minute_bucket": {"S": bucket},
                        },
                        "UpdateExpression": (
                            "SET updated_at = :updated_at, expires_at = :expires_at "
                            "ADD total_triages :one, #risk_counter :one"
                        ),
                        "ExpressionAttributeNames": {
                            "#risk_counter": risk_counter
                        },
                        "ExpressionAttributeValues": {
                            ":updated_at": {"S": now},
                            ":expires_at": {
                                "N": str(now_epoch + (30 * 24 * 60 * 60))
                            },
                            ":one": {"N": "1"},
                        },
                    }
                }
            )

        try:
            self.client.transact_write_items(
                TransactItems=transaction_items,
            )
            return True
        except Exception as error:
            if _aws_error_code(error) != "TransactionCanceledException":
                raise

        duplicate = self.client.get_item(
            TableName=self.idempotency_table,
            Key={"event_id": {"S": event_id}},
            ConsistentRead=True,
        )
        if duplicate.get("Item"):
            return False
        raise RuntimeError("Transaction was cancelled without an idempotency record.")
