import sys
import unittest
from datetime import date
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT))

from contract import (  # noqa: E402
    build_api_url,
    build_backfill_periods,
    build_s3_keys,
    parse_event,
)


ALLOWED_SUFFIXES = (".ngrok-free.app", ".ngrok-free.dev")


class ContractTest(unittest.TestCase):
    def test_month_request(self) -> None:
        request = parse_event(
            {
                "api_base_url": "https://example.ngrok-free.dev",
                "granularity": "month",
                "reference_period": "2024-01",
                "processing_date": "2026-07-26",
            },
            allowed_host_suffixes=ALLOWED_SUFFIXES,
        )

        self.assertEqual(request.granularity, "month")
        self.assertEqual(request.reference_period, "2024-01")
        self.assertFalse(request.force)

    def test_day_request_uses_current_date(self) -> None:
        request = parse_event(
            {
                "api_base_url": "https://example.ngrok-free.app/",
                "granularity": "day",
                "reference_period": "2024-01-01",
            },
            allowed_host_suffixes=ALLOWED_SUFFIXES,
            current_date=date(2026, 7, 26),
        )

        self.assertEqual(request.processing_date, "2026-07-26")
        self.assertEqual(
            request.api_base_url,
            "https://example.ngrok-free.app",
        )

    def test_month_api_url(self) -> None:
        request = parse_event(
            {
                "api_base_url": "https://example.ngrok-free.dev",
                "granularity": "month",
                "reference_period": "2024-01",
            },
            allowed_host_suffixes=ALLOWED_SUFFIXES,
            current_date=date(2026, 7, 26),
        )

        self.assertEqual(
            build_api_url(request),
            (
                "https://example.ngrok-free.dev/v1/dengue/monthly"
                "?periodo_notificacao=2024-01"
            ),
        )

    def test_s3_keys(self) -> None:
        request = parse_event(
            {
                "api_base_url": "https://example.ngrok-free.dev",
                "granularity": "day",
                "reference_period": "2024-01-01",
                "processing_date": "2026-07-26",
            },
            allowed_host_suffixes=ALLOWED_SUFFIXES,
        )

        self.assertEqual(
            build_s3_keys(
                request,
                "staging/opendatasus/dengue/",
            ),
            (
                "staging/opendatasus/dengue/"
                "processing_date=2026-07-26/"
                "granularity=day/"
                "reference_period=2024-01-01/dengue.jsonl.gz",
                "staging/opendatasus/dengue/"
                "processing_date=2026-07-26/"
                "granularity=day/"
                "reference_period=2024-01-01/manifest.json",
            ),
        )

    def test_http_url_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            parse_event(
                {
                    "api_base_url": "http://example.ngrok-free.dev",
                    "granularity": "month",
                    "reference_period": "2024-01",
                },
                allowed_host_suffixes=ALLOWED_SUFFIXES,
            )

    def test_unapproved_host_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "not allowed"):
            parse_event(
                {
                    "api_base_url": "https://example.com",
                    "granularity": "month",
                    "reference_period": "2024-01",
                },
                allowed_host_suffixes=ALLOWED_SUFFIXES,
            )

    def test_invalid_day_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_event(
                {
                    "api_base_url": "https://example.ngrok-free.dev",
                    "granularity": "day",
                    "reference_period": "2024-02-31",
                },
                allowed_host_suffixes=ALLOWED_SUFFIXES,
            )

    def test_month_backfill_periods(self) -> None:
        self.assertEqual(
            build_backfill_periods("month", "2024-11", "2025-02"),
            [
                {"reference_period": "2024-11"},
                {"reference_period": "2024-12"},
                {"reference_period": "2025-01"},
                {"reference_period": "2025-02"},
            ],
        )

    def test_day_backfill_periods(self) -> None:
        self.assertEqual(
            build_backfill_periods("day", "2024-01-30", "2024-02-01"),
            [
                {"reference_period": "2024-01-30"},
                {"reference_period": "2024-01-31"},
                {"reference_period": "2024-02-01"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
