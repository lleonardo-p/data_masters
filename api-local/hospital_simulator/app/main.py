import json
import logging
import random
import signal
import threading
from time import monotonic

from app.config import Settings, load_settings
from app.events import build_triage_event


LOGGER = logging.getLogger("hospital_simulator")
STOP_EVENT = threading.Event()


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def request_shutdown(signum: int, _frame: object) -> None:
    LOGGER.info("shutdown_requested signal=%s", signum)
    STOP_EVENT.set()


def publish_event(
    settings: Settings,
    sqs_client: object | None,
    event: dict[str, object],
) -> str:
    if settings.dry_run:
        return "dry-run"

    if sqs_client is None or settings.sqs_queue_url is None:
        raise RuntimeError("SQS client and queue URL are required.")

    response = sqs_client.send_message(
        QueueUrl=settings.sqs_queue_url,
        MessageBody=json.dumps(event, ensure_ascii=False, separators=(",", ":")),
        MessageAttributes={
            "event_type": {
                "DataType": "String",
                "StringValue": str(event["event_type"]),
            },
            "schema_version": {
                "DataType": "String",
                "StringValue": str(event["schema_version"]),
            },
            "source_system": {
                "DataType": "String",
                "StringValue": str(event["source_system"]),
            },
        },
    )
    return str(response["MessageId"])


def run() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    rng = random.Random(settings.random_seed)
    sqs_client = None

    if not settings.dry_run:
        import boto3

        sqs_client = boto3.client("sqs", region_name=settings.aws_region)

    LOGGER.info(
        "producer_started interval_seconds=%s max_events=%s dry_run=%s",
        settings.event_interval_seconds,
        settings.max_events or "unlimited",
        settings.dry_run,
    )

    published_count = 0

    while not STOP_EVENT.is_set():
        cycle_started_at = monotonic()
        event = build_triage_event(rng)
        message_id = publish_event(settings, sqs_client, event)
        published_count += 1

        # Logs contain only technical identifiers; PII is never logged.
        LOGGER.info(
            "triage_published event_id=%s triage_id=%s message_id=%s "
            "unit_id=%s risk_level=%s published_count=%s",
            event["event_id"],
            event["triage_id"],
            message_id,
            event["health_unit"]["unit_id"],
            event["triage"]["risk_level"],
            published_count,
        )

        if settings.max_events and published_count >= settings.max_events:
            break

        elapsed = monotonic() - cycle_started_at
        remaining = max(0.0, settings.event_interval_seconds - elapsed)
        STOP_EVENT.wait(remaining)

    LOGGER.info("producer_stopped published_count=%s", published_count)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    run()
