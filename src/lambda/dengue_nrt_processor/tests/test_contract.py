import sys
import unittest
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_DIR))

from contract import ContractError, validate_triage_event  # noqa: E402


def valid_event() -> dict:
    return {
        "event_id": "ddcc7628-98ac-4c12-99bb-8030263dc129",
        "event_type": "TRIAGE_REGISTERED",
        "schema_version": "1.0",
        "event_time": "2026-08-03T17:00:00Z",
        "source_system": "hospital_simulator",
        "triage_id": "TRIAGE-20260803-test",
        "patient": {
            "cpf": "90043309682",
            "full_name": "Paciente Sintetico",
            "age": 35,
            "sex": "F",
            "phone": "+5500000000000",
            "email": "patient@example.invalid",
        },
        "triage": {
            "notification_at": "2026-08-03T17:00:00Z",
            "disease_code": "A90",
            "case_classification": "SUSPECTED",
            "risk_level": "YELLOW",
            "symptoms_start_date": "2026-08-01",
        },
        "health_unit": {
            "unit_id": "CNES-SIM-0001",
            "unit_name": "Hospital Simulado",
            "municipality_code": "3550308",
            "municipality_name": "Sao Paulo",
            "state": "SP",
        },
    }


class ContractTest(unittest.TestCase):
    def test_valid_contract_is_accepted(self) -> None:
        event = valid_event()
        self.assertIs(validate_triage_event(event), event)

    def test_missing_cpf_is_rejected(self) -> None:
        event = valid_event()
        del event["patient"]["cpf"]

        with self.assertRaises(ContractError):
            validate_triage_event(event)


if __name__ == "__main__":
    unittest.main()
