import os
from dataclasses import dataclass


TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    aws_region: str
    sqs_queue_url: str | None
    event_interval_seconds: float
    max_events: int
    dry_run: bool
    random_seed: str | None
    log_level: str


def load_settings() -> Settings:
    interval = float(os.getenv("EVENT_INTERVAL_SECONDS", "3"))
    max_events = int(os.getenv("MAX_EVENTS", "0"))
    dry_run = os.getenv("DRY_RUN", "false").strip().lower() in TRUE_VALUES
    queue_url = os.getenv("SQS_QUEUE_URL", "").strip() or None

    if interval <= 0:
        raise ValueError("EVENT_INTERVAL_SECONDS must be greater than zero.")

    if max_events < 0:
        raise ValueError("MAX_EVENTS must be zero or greater.")

    if not dry_run and not queue_url:
        raise ValueError("SQS_QUEUE_URL is required when DRY_RUN=false.")

    return Settings(
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        sqs_queue_url=queue_url,
        event_interval_seconds=interval,
        max_events=max_events,
        dry_run=dry_run,
        random_seed=os.getenv("RANDOM_SEED", "").strip() or None,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
