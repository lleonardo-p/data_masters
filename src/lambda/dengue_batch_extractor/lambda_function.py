import base64
import json
import logging
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import boto3
from boto3.s3.transfer import TransferConfig

from contract import (
    build_api_url,
    build_backfill_periods,
    build_s3_keys,
    parse_event,
)
from streaming import AuditedGzipReader


LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

S3_CLIENT = boto3.client("s3")
SECRETS_CLIENT = boto3.client("secretsmanager")

DESTINATION_BUCKET = os.environ["DESTINATION_BUCKET"]
DESTINATION_PREFIX = os.getenv(
    "DESTINATION_PREFIX",
    "staging/opendatasus/dengue",
)
API_KEY_SECRET_ARN = os.environ["API_KEY_SECRET_ARN"]
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
ALLOWED_API_HOST_SUFFIXES = tuple(
    suffix.strip()
    for suffix in os.getenv(
        "ALLOWED_API_HOST_SUFFIXES",
        ".ngrok-free.app,.ngrok-free.dev",
    ).split(",")
    if suffix.strip()
)

TRANSFER_CONFIG = TransferConfig(
    multipart_threshold=8 * 1024 * 1024,
    multipart_chunksize=8 * 1024 * 1024,
    max_concurrency=1,
    use_threads=False,
)

_API_KEY: str | None = None


def get_api_key() -> str:
    global _API_KEY

    if _API_KEY is not None:
        return _API_KEY

    response = SECRETS_CLIENT.get_secret_value(
        SecretId=API_KEY_SECRET_ARN,
    )

    if "SecretString" in response:
        value = response["SecretString"]
    else:
        value = base64.b64decode(response["SecretBinary"]).decode("utf-8")

    value = value.strip()

    if not value:
        raise ValueError("The dengue source API key secret is empty.")

    _API_KEY = value
    return value


def manifest_exists(bucket: str, key: str) -> bool:
    response = S3_CLIENT.list_objects_v2(
        Bucket=bucket,
        Prefix=key,
        MaxKeys=1,
    )

    return any(
        item.get("Key") == key
        for item in response.get("Contents", [])
    )


def lambda_handler(event, context):
    if event.get("operation") == "plan_backfill":
        periods = build_backfill_periods(
            str(event.get("granularity", "")).lower(),
            str(event.get("start_period", "")),
            str(event.get("end_period", "")),
        )
        return {
            "status": "PLANNED",
            "load_mode": "backfill",
            "granularity": str(event["granularity"]).lower(),
            "processing_date": str(event["processing_date"]),
            "start_period": str(event["start_period"]),
            "end_period": str(event["end_period"]),
            "period_count": len(periods),
            "periods": periods,
        }

    request = parse_event(
        event,
        allowed_host_suffixes=ALLOWED_API_HOST_SUFFIXES,
    )
    data_key, manifest_key = build_s3_keys(
        request,
        DESTINATION_PREFIX,
    )
    batch_id = getattr(context, "aws_request_id", "manual")

    if not request.force and manifest_exists(
        DESTINATION_BUCKET,
        manifest_key,
    ):
        LOGGER.info(
            json.dumps(
                {
                    "event": "dengue_extraction_skipped",
                    "batch_id": batch_id,
                    "reason": "completed_manifest_already_exists",
                    "s3_uri": f"s3://{DESTINATION_BUCKET}/{data_key}",
                }
            )
        )
        return {
            "status": "SKIPPED",
            "batch_id": batch_id,
            "environment": ENVIRONMENT,
            "granularity": request.granularity,
            "reference_period": request.reference_period,
            "processing_date": request.processing_date,
            "s3_uri": f"s3://{DESTINATION_BUCKET}/{data_key}",
            "manifest_uri": (
                f"s3://{DESTINATION_BUCKET}/{manifest_key}"
            ),
        }

    api_url = build_api_url(request)
    started_at = datetime.now(timezone.utc)
    http_request = Request(
        api_url,
        headers={
            "Accept": "application/x-ndjson",
            "Accept-Encoding": "gzip",
            "User-Agent": "baip-dengue-batch-extractor/1.0",
            "X-API-Key": get_api_key(),
            "ngrok-skip-browser-warning": "true",
        },
        method="GET",
    )

    LOGGER.info(
        json.dumps(
            {
                "event": "dengue_extraction_started",
                "batch_id": batch_id,
                "granularity": request.granularity,
                "reference_period": request.reference_period,
                "processing_date": request.processing_date,
                "destination": (
                    f"s3://{DESTINATION_BUCKET}/{data_key}"
                ),
                "started_at": started_at.isoformat(),
            }
        )
    )

    try:
        with urlopen(http_request, timeout=840) as response:
            content_encoding = response.headers.get(
                "Content-Encoding",
                "",
            ).lower()

            if content_encoding != "gzip":
                raise ValueError(
                    "The source API response was not gzip encoded."
                )

            audited_reader = AuditedGzipReader(response)

            S3_CLIENT.upload_fileobj(
                audited_reader,
                DESTINATION_BUCKET,
                data_key,
                ExtraArgs={
                    "ContentType": "application/x-ndjson",
                    "ContentEncoding": "gzip",
                    "Metadata": {
                        "batch-id": batch_id,
                        "granularity": request.granularity,
                        "reference-period": request.reference_period,
                        "processing-date": request.processing_date,
                        "source-system": "dengue-source-api",
                    },
                },
                Config=TRANSFER_CONFIG,
            )
    except HTTPError as error:
        raise RuntimeError(
            f"Source API returned HTTP {error.code}."
        ) from error
    except URLError as error:
        raise RuntimeError(
            f"Could not connect to the source API: {error.reason}."
        ) from error

    completed_at = datetime.now(timezone.utc)
    head = S3_CLIENT.head_object(
        Bucket=DESTINATION_BUCKET,
        Key=data_key,
    )
    manifest = {
        "status": "SUCCEEDED",
        "batch_id": batch_id,
        "environment": ENVIRONMENT,
        "granularity": request.granularity,
        "reference_period": request.reference_period,
        "processing_date": request.processing_date,
        "record_count": audited_reader.record_count,
        "compressed_bytes": audited_reader.compressed_bytes,
        "compressed_sha256": audited_reader.sha256_hex,
        "s3_bucket": DESTINATION_BUCKET,
        "s3_key": data_key,
        "s3_etag": head["ETag"].strip('"'),
        "source_host": request.api_base_url,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": round(
            (completed_at - started_at).total_seconds(),
            3,
        ),
    }

    S3_CLIENT.put_object(
        Bucket=DESTINATION_BUCKET,
        Key=manifest_key,
        Body=json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
        ContentType="application/json",
    )

    LOGGER.info(
        json.dumps(
            {
                "event": "dengue_extraction_finished",
                **manifest,
            }
        )
    )

    return {
        **manifest,
        "s3_uri": f"s3://{DESTINATION_BUCKET}/{data_key}",
        "manifest_uri": (
            f"s3://{DESTINATION_BUCKET}/{manifest_key}"
        ),
    }
