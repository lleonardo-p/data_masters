import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_DIR))

from service import NrtQueryService, indicator_window, scope_base  # noqa: E402


class FakeKmsClient:
    def generate_mac(self, **_kwargs: object) -> dict:
        return {"Mac": b"synthetic-mac"}


class FakeDynamoClient:
    def __init__(self) -> None:
        self.queried_scopes: list[str] = []

    def get_item(self, **_kwargs: object) -> dict:
        return {"Item": {"patient_token": {"S": "pt_synthetic"}}}

    def query(self, **kwargs: object) -> dict:
        values = kwargs["ExpressionAttributeValues"]
        if ":scope" in values:
            scope = values[":scope"]["S"]
            self.queried_scopes.append(scope)
            shard_value = 2 if scope.endswith("00") else 3
            return {
                "Items": [
                    {
                        "scope_key": {"S": scope},
                        "minute_bucket": {"S": "2026-08-03T17:06:00Z"},
                        "total_triages": {"N": str(shard_value)},
                        "risk_yellow": {"N": str(shard_value)},
                    }
                ]
            }

        return {
            "Items": [
                {
                    "patient_token": {"S": "pt_synthetic"},
                    "event_sort_key": {"S": "2026-08-03T17:06:00Z#event-1"},
                    "event_id": {"S": "event-1"},
                    "risk_level": {"S": "YELLOW"},
                    "age": {"N": "22"},
                    "expires_at": {"N": "9999999999"},
                }
            ]
        }


class ScopeBaseTest(unittest.TestCase):
    def test_global_scope_is_default(self) -> None:
        self.assertEqual(scope_base(None, None), "GLOBAL")

    def test_state_scope_is_normalized(self) -> None:
        self.assertEqual(scope_base("state", "sp"), "STATE#SP")


class IndicatorWindowTest(unittest.TestCase):
    def test_default_two_minute_window(self) -> None:
        now = datetime(2026, 8, 3, 17, 7, 30, tzinfo=timezone.utc)
        self.assertEqual(
            indicator_window(None, None, None, now=now),
            ("2026-08-03T17:06:00Z", "2026-08-03T17:07:00Z"),
        )

    def test_explicit_window_is_normalized_to_utc_minute(self) -> None:
        self.assertEqual(
            indicator_window(
                "2026-08-03T14:00:30-03:00",
                "2026-08-03T14:02:59-03:00",
                None,
            ),
            ("2026-08-03T17:00:00Z", "2026-08-03T17:02:00Z"),
        )


class QueryServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dynamodb = FakeDynamoClient()
        self.service = NrtQueryService(
            dynamodb_client=self.dynamodb,
            kms_client=FakeKmsClient(),
            token_table="tokens",
            history_table="history",
            indicators_table="indicators",
            hmac_key_arn="arn:test",
            shard_count=2,
        )

    def test_indicator_shards_are_summed(self) -> None:
        result = self.service.indicators(
            scope_type="STATE",
            scope_value="SP",
            start="2026-08-03T17:06:00Z",
            end="2026-08-03T17:06:00Z",
            window_minutes=None,
        )

        self.assertEqual(result["totals"]["total_triages"], 5)
        self.assertEqual(result["totals"]["risk_yellow"], 5)
        self.assertEqual(
            self.dynamodb.queried_scopes,
            ["STATE#SP#SHARD#00", "STATE#SP#SHARD#01"],
        )

    def test_patient_history_does_not_return_internal_identifiers(self) -> None:
        result = self.service.patient_history(
            cpf="900.433.096-82",
            limit=50,
            next_token=None,
        )

        self.assertTrue(result["found"])
        self.assertNotIn("patient_token", result["events"][0])
        self.assertNotIn("event_sort_key", result["events"][0])
        self.assertNotIn("expires_at", result["events"][0])

if __name__ == "__main__":
    unittest.main()
