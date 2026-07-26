import hashlib
import zlib


AUDIT_CHUNK_SIZE = 1024 * 1024


class AuditedGzipReader:
    def __init__(self, source):
        self.source = source
        self.compressed_bytes = 0
        self.record_count = 0
        self.sha256 = hashlib.sha256()
        self.decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        self.finalized = False

    def readable(self) -> bool:
        return True

    def _count_records(self, compressed_chunk: bytes) -> None:
        pending = compressed_chunk

        while True:
            decompressed = self.decompressor.decompress(
                pending,
                AUDIT_CHUNK_SIZE,
            )
            self.record_count += decompressed.count(b"\n")

            if self.decompressor.unconsumed_tail:
                pending = self.decompressor.unconsumed_tail
                continue

            if len(decompressed) == AUDIT_CHUNK_SIZE:
                pending = b""
                continue

            break

    def read(self, size: int = -1) -> bytes:
        chunk = self.source.read(size)

        if chunk:
            self.compressed_bytes += len(chunk)
            self.sha256.update(chunk)
            self._count_records(chunk)
            return chunk

        if not self.finalized:
            remaining = self.decompressor.flush()
            self.record_count += remaining.count(b"\n")
            self.finalized = True

            if not self.decompressor.eof:
                raise ValueError("The gzip response ended before its trailer.")

        return b""

    @property
    def sha256_hex(self) -> str:
        return self.sha256.hexdigest()
