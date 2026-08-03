import json
import logging
import os
from typing import Any

import boto3

from contract import ContractError, validate_triage_event
from identity import generate_cpf_fingerprint, normalize_cpf
from storage import NrtStore


LOGGER = logging.getLogger("dengue_nrt_processor")
LOGGER.setLevel(os.getenv("LOG_LEVEL", "INFO"))

KMS_CLIENT = boto3.client("kms")
DYNAMODB_CLIENT = boto3.client("dynamodb")

HMAC_KEY_ARN = os.environ["HMAC_KEY_ARN"]
STORE = NrtStore(
    dynamodb_client=DYNAMODB_CLIENT,
    token_table=os.environ["TOKEN_TABLE_NAME"],
    history_table=os.environ["HISTORY_TABLE_NAME"],
    indicators_table=os.environ["INDICATORS_TABLE_NAME"],
    idempotency_table=os.environ["IDEMPOTENCY_TABLE_NAME"],
    hmac_key_version=os.getenv("HMAC_KEY_VERSION", "v1"),
    aggregate_shard_count=int(os.getenv("AGGREGATE_SHARD_COUNT", "8")),
)


def process_record(record: dict[str, Any]) -> None:
    message_id = str(record.get("messageId", "unknown"))
    event_id = "unknown"

    try:
        event = validate_triage_event(json.loads(record["body"]))
        event_id = event["event_id"]
        normalized_cpf = normalize_cpf(event["patient"]["cpf"])
        fingerprint = generate_cpf_fingerprint(
            KMS_CLIENT,
            HMAC_KEY_ARN,
            normalized_cpf,
        )
        patient_token = STORE.get_or_create_patient_token(fingerprint)
        inserted = STORE.persist_event(event, patient_token)

        LOGGER.info(
            "triage_processed message_id=%s event_id=%s result=%s",
            message_id,
            event_id,
            "inserted" if inserted else "duplicate",
        )
    except (json.JSONDecodeError, ContractError, ValueError):
        LOGGER.warning(
            "triage_rejected message_id=%s event_id=%s reason=invalid_contract",
            message_id,
            event_id,
        )
        raise
    except Exception:
        LOGGER.exception(
            "triage_failed message_id=%s event_id=%s",
            message_id,
            event_id,
        )
        raise


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    failures = []

    for record in event.get("Records", []):
        try:
            process_record(record)
        except Exception:
            failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failures}
