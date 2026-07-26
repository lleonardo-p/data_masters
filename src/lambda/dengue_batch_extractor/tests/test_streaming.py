import gzip
import io
import sys
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT))

from streaming import AuditedGzipReader


class AuditedGzipReaderTest(unittest.TestCase):
    def test_counts_records_and_preserves_compressed_bytes(self) -> None:
        source_data = (
            b'{"id":1}\n'
            b'{"id":2}\n'
            b'{"id":3}\n'
        )
        compressed_data = gzip.compress(source_data)
        reader = AuditedGzipReader(io.BytesIO(compressed_data))

        copied = b""

        while chunk := reader.read(7):
            copied += chunk

        self.assertEqual(copied, compressed_data)
        self.assertEqual(reader.record_count, 3)
        self.assertEqual(reader.compressed_bytes, len(compressed_data))
        self.assertEqual(len(reader.sha256_hex), 64)

    def test_rejects_truncated_gzip(self) -> None:
        compressed_data = gzip.compress(b'{"id":1}\n')[:-4]
        reader = AuditedGzipReader(io.BytesIO(compressed_data))

        with self.assertRaisesRegex(ValueError, "trailer"):
            while reader.read(5):
                pass


if __name__ == "__main__":
    unittest.main()
