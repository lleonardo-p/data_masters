from datetime import datetime
from typing import Any


ALLOWED_RISK_LEVELS = {"BLUE", "GREEN", "YELLOW", "ORANGE", "RED"}
ALLOWED_SEX_VALUES = {"F", "M", "UNKNOWN"}


class ContractError(ValueError):
    """Raised when an event does not comply with the triage contract."""


def _required_dict(container: dict[str, Any], field: str) -> dict[str, Any]:
    value = container.get(field)
    if not isinstance(value, dict):
        raise ContractError(f"{field} must be an object.")
    return value


def _required_string(container: dict[str, Any], field: str) -> str:
    value = container.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be a non-empty string.")
    return value.strip()


def _parse_iso_datetime(value: str, field: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError(f"{field} must be an ISO-8601 datetime.") from error


def validate_triage_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise ContractError("Event must be a JSON object.")

    if _required_string(event, "event_type") != "TRIAGE_REGISTERED":
        raise ContractError("event_type must be TRIAGE_REGISTERED.")

    if _required_string(event, "schema_version") != "1.0":
        raise ContractError("schema_version must be 1.0.")

    if _required_string(event, "source_system") != "hospital_simulator":
        raise ContractError("source_system is not allowed.")

    _required_string(event, "event_id")
    _required_string(event, "triage_id")
    _parse_iso_datetime(_required_string(event, "event_time"), "event_time")

    patient = _required_dict(event, "patient")
    _required_string(patient, "cpf")
    _required_string(patient, "full_name")
    _required_string(patient, "phone")
    _required_string(patient, "email")

    age = patient.get("age")
    if not isinstance(age, int) or isinstance(age, bool) or not 0 <= age <= 120:
        raise ContractError("patient.age must be an integer between 0 and 120.")

    sex = _required_string(patient, "sex")
    if sex not in ALLOWED_SEX_VALUES:
        raise ContractError("patient.sex is invalid.")

    triage = _required_dict(event, "triage")
    _parse_iso_datetime(
        _required_string(triage, "notification_at"),
        "triage.notification_at",
    )
    _required_string(triage, "symptoms_start_date")

    if _required_string(triage, "disease_code") != "A90":
        raise ContractError("triage.disease_code must be A90.")

    if _required_string(triage, "case_classification") != "SUSPECTED":
        raise ContractError("triage.case_classification must be SUSPECTED.")

    risk_level = _required_string(triage, "risk_level")
    if risk_level not in ALLOWED_RISK_LEVELS:
        raise ContractError("triage.risk_level is invalid.")

    health_unit = _required_dict(event, "health_unit")
    for field in (
        "unit_id",
        "unit_name",
        "municipality_code",
        "municipality_name",
        "state",
    ):
        _required_string(health_unit, field)

    return event
