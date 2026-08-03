import random
import unittest
from datetime import datetime, timezone

from app.events import build_triage_event, synthetic_cpf


def cpf_is_valid(value: str) -> bool:
    if len(value) != 11 or not value.isdigit():
        return False

    digits = [int(character) for character in value]
    first_sum = sum(
        digit * weight for digit, weight in zip(digits[:9], range(10, 1, -1))
    )
    first_remainder = first_sum % 11
    first_digit = 0 if first_remainder < 2 else 11 - first_remainder

    second_sum = sum(
        digit * weight
        for digit, weight in zip(digits[:10], range(11, 1, -1))
    )
    second_remainder = second_sum % 11
    second_digit = 0 if second_remainder < 2 else 11 - second_remainder

    return digits[-2:] == [first_digit, second_digit]


class SyntheticCpfTest(unittest.TestCase):
    def test_generated_cpf_has_valid_checksum(self) -> None:
        cpf = synthetic_cpf(random.Random("test"))

        self.assertTrue(cpf_is_valid(cpf))
        self.assertTrue(cpf.startswith("900"))


class BuildTriageEventTest(unittest.TestCase):
    def test_event_follows_v1_contract(self) -> None:
        now = datetime(2026, 8, 3, 15, 30, tzinfo=timezone.utc)
        event = build_triage_event(random.Random("test"), now=now)

        self.assertEqual(event["event_type"], "TRIAGE_REGISTERED")
        self.assertEqual(event["schema_version"], "1.0")
        self.assertEqual(event["source_system"], "hospital_simulator")
        self.assertEqual(event["event_time"], "2026-08-03T15:30:00Z")
        self.assertEqual(event["triage"]["disease_code"], "A90")
        self.assertEqual(event["triage"]["case_classification"], "SUSPECTED")
        self.assertTrue(event["patient"]["email"].endswith("@example.invalid"))
        self.assertTrue(event["health_unit"]["unit_id"].startswith("CNES-SIM-"))


if __name__ == "__main__":
    unittest.main()
