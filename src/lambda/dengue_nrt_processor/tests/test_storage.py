import json
import sys
import unittest
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_DIR))

from storage import NrtStore, age_group, aggregate_scopes, minute_bucket  # noqa: E402


class FakeDynamoDbClient:
    def __init__(self) -> None:
        self.transaction_items = []

    def transact_write_items(self, TransactItems: list) -> None:
        self.transaction_items = TransactItems


class StorageHelpersTest(unittest.TestCase):
    def test_age_groups(self) -> None:
        self.assertEqual(age_group(9), "00-09")
        self.assertEqual(age_group(35), "30-39")
        self.assertEqual(age_group(85), "80+")

    def test_minute_bucket(self) -> None:
        self.assertEqual(
            minute_bucket("2026-08-03T17:06:49Z"),
            "2026-08-03T17:06:00Z",
        )

    def test_scopes_are_sharded(self) -> None:
        event = {
            "event_id": "event-1",
            "patient": {"age": 35},
            "health_unit": {
                "state": "SP",
                "municipality_code": "3550308",
                "unit_id": "CNES-SIM-0001",
            },
        }

        scopes = aggregate_scopes(event, shard_count=8)

        self.assertEqual(len(scopes), 5)
        self.assertTrue(all("#SHARD#" in scope for scope in scopes))

    def test_persistence_does_not_propagate_direct_pii(self) -> None:
        client = FakeDynamoDbClient()
        store = NrtStore(
            dynamodb_client=client,
            token_table="tokens",
            history_table="history",
            indicators_table="indicators",
            idempotency_table="idempotency",
            hmac_key_version="v1",
        )
        event = {
            "event_id": "ddcc7628-98ac-4c12-99bb-8030263dc129",
            "event_time": "2026-08-03T17:06:49Z",
            "triage_id": "TRIAGE-20260803-test",
            "source_system": "hospital_simulator",
            "schema_version": "1.0",
            "patient": {
                "cpf": "90043309682",
                "full_name": "Paciente Sintetico",
                "age": 35,
                "sex": "F",
                "phone": "+5500000000000",
                "email": "patient@example.invalid",
            },
            "triage": {
                "notification_at": "2026-08-03T17:06:49Z",
                "symptoms_start_date": "2026-08-01",
                "disease_code": "A90",
                "case_classification": "SUSPECTED",
                "risk_level": "YELLOW",
            },
            "health_unit": {
                "unit_id": "CNES-SIM-0001",
                "unit_name": "Hospital Simulado",
                "municipality_code": "3550308",
                "municipality_name": "Sao Paulo",
                "state": "SP",
            },
        }

        inserted = store.persist_event(event, "pt_synthetic")
        serialized_writes = json.dumps(client.transaction_items)

        self.assertTrue(inserted)
        self.assertEqual(len(client.transaction_items), 7)
        self.assertNotIn("90043309682", serialized_writes)
        self.assertNotIn("Paciente Sintetico", serialized_writes)
        self.assertNotIn("+5500000000000", serialized_writes)
        self.assertNotIn("patient@example.invalid", serialized_writes)


if __name__ == "__main__":
    unittest.main()
