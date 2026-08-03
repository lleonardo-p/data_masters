import sys
import unittest
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_DIR))

from identity import (  # noqa: E402
    InvalidCpfError,
    generate_cpf_fingerprint,
    normalize_cpf,
)


class FakeKmsClient:
    def generate_mac(self, **_kwargs: object) -> dict:
        return {"Mac": b"synthetic-mac"}


class NormalizeCpfTest(unittest.TestCase):
    def test_valid_formatted_cpf_is_normalized(self) -> None:
        self.assertEqual(normalize_cpf("900.433.096-82"), "90043309682")

    def test_invalid_checksum_is_rejected(self) -> None:
        with self.assertRaises(InvalidCpfError):
            normalize_cpf("90000000000")

    def test_fingerprint_is_returned_as_hex(self) -> None:
        fingerprint = generate_cpf_fingerprint(
            FakeKmsClient(),
            "arn:aws:kms:us-east-1:000000000000:key/test",
            "90043309682",
        )

        self.assertEqual(fingerprint, b"synthetic-mac".hex())


if __name__ == "__main__":
    unittest.main()
