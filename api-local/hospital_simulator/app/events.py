import hashlib
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any


FIRST_NAMES = (
    "Ana",
    "Beatriz",
    "Carla",
    "Daniel",
    "Eduardo",
    "Fernanda",
    "Gabriel",
    "Helena",
    "Igor",
    "Juliana",
)

LAST_NAMES = (
    "Almeida",
    "Barbosa",
    "Cardoso",
    "Dias",
    "Ferreira",
    "Gomes",
    "Lima",
    "Mendes",
    "Oliveira",
    "Pereira",
)

HEALTH_UNITS = (
    {
        "unit_id": "CNES-SIM-0001",
        "unit_name": "Hospital Municipal Simulado Centro",
        "municipality_code": "3550308",
        "municipality_name": "Sao Paulo",
        "state": "SP",
    },
    {
        "unit_id": "CNES-SIM-0002",
        "unit_name": "Unidade de Pronto Atendimento Simulada Norte",
        "municipality_code": "3304557",
        "municipality_name": "Rio de Janeiro",
        "state": "RJ",
    },
    {
        "unit_id": "CNES-SIM-0003",
        "unit_name": "Hospital Regional Simulado",
        "municipality_code": "3106200",
        "municipality_name": "Belo Horizonte",
        "state": "MG",
    },
    {
        "unit_id": "CNES-SIM-0004",
        "unit_name": "Unidade de Saude Simulada Sul",
        "municipality_code": "5300108",
        "municipality_name": "Brasilia",
        "state": "DF",
    },
    {
        "unit_id": "CNES-SIM-0005",
        "unit_name": "Hospital Municipal Simulado Leste",
        "municipality_code": "4106902",
        "municipality_name": "Curitiba",
        "state": "PR",
    },
)

SEX_VALUES = ("F", "M", "UNKNOWN")
SEX_WEIGHTS = (0.49, 0.49, 0.02)
RISK_LEVELS = ("BLUE", "GREEN", "YELLOW", "ORANGE", "RED")
RISK_WEIGHTS = (0.08, 0.47, 0.30, 0.12, 0.03)


def _cpf_check_digit(digits: list[int], weights: range) -> int:
    remainder = sum(digit * weight for digit, weight in zip(digits, weights)) % 11
    return 0 if remainder < 2 else 11 - remainder


def synthetic_cpf(rng: random.Random) -> str:
    """Create a checksum-valid identifier used only by this simulator."""
    base = [9, 0, 0] + [rng.randint(0, 9) for _ in range(6)]
    first_digit = _cpf_check_digit(base, range(10, 1, -1))
    second_digit = _cpf_check_digit(
        [*base, first_digit],
        range(11, 1, -1),
    )
    return "".join(str(value) for value in [*base, first_digit, second_digit])


def _safe_email(full_name: str, identifier: str) -> str:
    local_part = full_name.lower().replace(" ", ".")
    return f"{local_part}.{identifier[-4:]}@example.invalid"


def _event_suffix(event_id: str) -> str:
    return hashlib.sha256(event_id.encode("utf-8")).hexdigest()[:12]


def build_triage_event(
    rng: random.Random,
    now: datetime | None = None,
) -> dict[str, Any]:
    event_time = now or datetime.now(timezone.utc)
    event_id = str(uuid.uuid4())
    suffix = _event_suffix(event_id)
    cpf = synthetic_cpf(rng)
    full_name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    symptoms_start_date = event_time.date() - timedelta(days=rng.randint(0, 7))

    return {
        "event_id": event_id,
        "event_type": "TRIAGE_REGISTERED",
        "schema_version": "1.0",
        "event_time": event_time.isoformat().replace("+00:00", "Z"),
        "source_system": "hospital_simulator",
        "triage_id": f"TRIAGE-{event_time:%Y%m%d}-{suffix}",
        "patient": {
            "cpf": cpf,
            "full_name": full_name,
            "age": rng.randint(1, 95),
            "sex": rng.choices(SEX_VALUES, weights=SEX_WEIGHTS, k=1)[0],
            "phone": f"+550000000{rng.randint(1000, 9999)}",
            "email": _safe_email(full_name, cpf),
        },
        "triage": {
            "notification_at": event_time.isoformat().replace("+00:00", "Z"),
            "disease_code": "A90",
            "case_classification": "SUSPECTED",
            "risk_level": rng.choices(
                RISK_LEVELS,
                weights=RISK_WEIGHTS,
                k=1,
            )[0],
            "symptoms_start_date": symptoms_start_date.isoformat(),
        },
        "health_unit": dict(rng.choice(HEALTH_UNITS)),
    }
