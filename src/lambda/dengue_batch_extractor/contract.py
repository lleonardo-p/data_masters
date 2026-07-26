import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import urlencode, urlparse


MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")
DAY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class ExtractionRequest:
    api_base_url: str
    granularity: str
    reference_period: str
    processing_date: str
    force: bool


def _validate_period(granularity: str, value: str) -> str:
    if granularity == "month":
        if not MONTH_PATTERN.fullmatch(value):
            raise ValueError(
                "reference_period must use YYYY-MM for month granularity."
            )

        datetime.strptime(value, "%Y-%m")
        return value

    if not DAY_PATTERN.fullmatch(value):
        raise ValueError(
            "reference_period must use YYYY-MM-DD for day granularity."
        )

    date.fromisoformat(value)
    return value


def _validate_processing_date(value: str) -> str:
    if not DAY_PATTERN.fullmatch(value):
        raise ValueError("processing_date must use YYYY-MM-DD.")

    date.fromisoformat(value)
    return value


def _validate_api_url(
    value: str,
    allowed_host_suffixes: tuple[str, ...],
) -> str:
    parsed = urlparse(value)

    if parsed.scheme != "https":
        raise ValueError("api_base_url must use HTTPS.")

    if not parsed.hostname:
        raise ValueError("api_base_url must contain a hostname.")

    if parsed.query or parsed.fragment or parsed.params:
        raise ValueError(
            "api_base_url must not contain query, fragment or path parameters."
        )

    if parsed.path not in {"", "/"}:
        raise ValueError("api_base_url must not contain a path.")

    hostname = parsed.hostname.lower()

    if not any(
        hostname.endswith(suffix.lower())
        for suffix in allowed_host_suffixes
    ):
        raise ValueError("api_base_url hostname is not allowed.")

    return value.rstrip("/")


def parse_event(
    event: dict,
    allowed_host_suffixes: tuple[str, ...],
    current_date: date | None = None,
) -> ExtractionRequest:
    if not isinstance(event, dict):
        raise ValueError("The Lambda event must be a JSON object.")

    granularity = str(event.get("granularity", "")).lower()

    if granularity not in {"month", "day"}:
        raise ValueError("granularity must be month or day.")

    reference_period = _validate_period(
        granularity,
        str(event.get("reference_period", "")),
    )

    processing_date = event.get("processing_date")

    if processing_date is None:
        processing_date = (
            current_date
            or datetime.now(timezone.utc).date()
        ).isoformat()
    else:
        processing_date = _validate_processing_date(str(processing_date))

    force = event.get("force", False)

    if not isinstance(force, bool):
        raise ValueError("force must be a boolean.")

    return ExtractionRequest(
        api_base_url=_validate_api_url(
            str(event.get("api_base_url", "")),
            allowed_host_suffixes,
        ),
        granularity=granularity,
        reference_period=reference_period,
        processing_date=processing_date,
        force=force,
    )


def build_api_url(request: ExtractionRequest) -> str:
    if request.granularity == "month":
        endpoint = "/v1/dengue/monthly"
        query = {"periodo_notificacao": request.reference_period}
    else:
        endpoint = "/v1/dengue/daily"
        query = {"data_notificacao": request.reference_period}

    return f"{request.api_base_url}{endpoint}?{urlencode(query)}"


def build_s3_keys(
    request: ExtractionRequest,
    destination_prefix: str,
) -> tuple[str, str]:
    prefix = destination_prefix.strip("/")
    partition_path = (
        f"processing_date={request.processing_date}/"
        f"granularity={request.granularity}/"
        f"reference_period={request.reference_period}"
    )
    root = f"{prefix}/{partition_path}" if prefix else partition_path

    return (
        f"{root}/dengue.jsonl.gz",
        f"{root}/manifest.json",
    )