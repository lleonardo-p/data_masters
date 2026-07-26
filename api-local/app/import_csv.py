import argparse
import csv
import gzip
import hashlib
import logging
import re
import sys
import unicodedata
from pathlib import Path

import psycopg
from psycopg import sql

from app.config import DATABASE_URL


LOGGER = logging.getLogger("dengue_csv_importer")


def normalize_column_name(column_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", column_name)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.strip().lower()
    normalized = re.sub(r"[^a-z0-9_]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def file_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()

    with file_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def read_header(file_path: Path) -> list[str]:
    with gzip.open(file_path, "rt", encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source)
        try:
            return next(reader)
        except StopIteration:
            raise ValueError(f"Arquivo vazio: {file_path}") from None


def ensure_schema(
    connection: psycopg.Connection,
    source_columns: list[str],
) -> list[str]:
    database_columns = [normalize_column_name(name) for name in source_columns]

    if any(not name for name in database_columns):
        raise ValueError("O cabeÃ§alho possui nome de coluna vazio ou invÃ¡lido.")

    if len(database_columns) != len(set(database_columns)):
        raise ValueError(
            "O cabeÃ§alho gera nomes duplicados apÃ³s a normalizaÃ§Ã£o."
        )

    if "dt_notific" not in database_columns:
        raise ValueError("A coluna obrigatÃ³ria DT_NOTIFIC nÃ£o foi encontrada.")

    connection.execute("CREATE SCHEMA IF NOT EXISTS dengue_source")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS dengue_source.source_columns (
            ordinal_position SMALLINT PRIMARY KEY,
            source_name TEXT NOT NULL UNIQUE,
            database_name TEXT NOT NULL UNIQUE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS dengue_source.imported_files (
            source_file_sha256 CHAR(64) PRIMARY KEY,
            source_file TEXT NOT NULL,
            imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            record_count BIGINT NOT NULL
        )
        """
    )

    existing_columns = connection.execute(
        """
        SELECT source_name, database_name
        FROM dengue_source.source_columns
        ORDER BY ordinal_position
        """
    ).fetchall()

    expected_columns = list(zip(source_columns, database_columns))

    if existing_columns and existing_columns != expected_columns:
        raise ValueError(
            "O cabeÃ§alho do arquivo difere do contrato jÃ¡ registrado no banco."
        )

    if not existing_columns:
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO dengue_source.source_columns (
                    ordinal_position,
                    source_name,
                    database_name
                )
                VALUES (%s, %s, %s)
                """,
                [
                    (position, source_name, database_name)
                    for position, (source_name, database_name) in enumerate(
                        expected_columns,
                        start=1,
                    )
                ],
            )

    source_definitions = sql.SQL(", ").join(
        sql.SQL("{} TEXT").format(sql.Identifier(column))
        for column in database_columns
    )
    connection.execute(
        sql.SQL(
            """
            CREATE TABLE IF NOT EXISTS dengue_source.notifications (
                record_id BIGINT GENERATED ALWAYS AS IDENTITY,
                {},
                notification_date DATE,
                source_file TEXT NOT NULL,
                source_file_sha256 CHAR(64) NOT NULL,
                ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (record_id)
            )
            """
        ).format(source_definitions)
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notifications_notification_date_record
        ON dengue_source.notifications (notification_date, record_id)
        """
    )

    return database_columns


def import_file(file_path: Path) -> None:
    source_columns = read_header(file_path)
    source_hash = file_sha256(file_path)

    with psycopg.connect(DATABASE_URL) as connection:
        database_columns = ensure_schema(connection, source_columns)

        already_imported = connection.execute(
            """
            SELECT 1
            FROM dengue_source.imported_files
            WHERE source_file_sha256 = %s
            """,
            (source_hash,),
        ).fetchone()

        if already_imported:
            LOGGER.info("Arquivo jÃ¡ importado; ignorando: %s", file_path.name)
            return

        temporary_table = sql.Identifier("dengue_import")
        source_identifiers = sql.SQL(", ").join(
            sql.Identifier(column) for column in database_columns
        )

        temporary_definitions = sql.SQL(", ").join(
            sql.SQL("{} TEXT").format(sql.Identifier(column))
            for column in database_columns
        )

        connection.execute(
            sql.SQL(
                """
                CREATE TEMP TABLE {} (
                    {}
                ) ON COMMIT DROP
                """
            ).format(
                temporary_table,
                temporary_definitions,
            )
        )

        copy_statement = sql.SQL(
            "COPY {} ({}) FROM STDIN "
            "WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')"
        ).format(temporary_table, source_identifiers)

        with gzip.open(file_path, "rb") as source:
            with connection.cursor().copy(copy_statement) as copy:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    copy.write(chunk)

        dt_notific = sql.Identifier("dt_notific")
        target_columns = sql.SQL(", ").join(
            [
                source_identifiers,
                sql.Identifier("notification_date"),
                sql.Identifier("source_file"),
                sql.Identifier("source_file_sha256"),
            ]
        )
        select_columns = sql.SQL(", ").join(
            [
                source_identifiers,
                sql.SQL(
                    "CASE WHEN {} ~ "
                    "'^(19|20)[0-9]{{2}}-(0[1-9]|1[0-2])-"
                    "(0[1-9]|[12][0-9]|3[01])$' "
                    "AND TO_CHAR(TO_DATE({}, 'YYYY-MM-DD'), 'YYYY-MM-DD') = {} "
                    "THEN TO_DATE({}, 'YYYY-MM-DD') ELSE NULL END"
                ).format(
                    dt_notific,
                    dt_notific,
                    dt_notific,
                    dt_notific,
                ),
                sql.Literal(file_path.name),
                sql.Literal(source_hash),
            ]
        )

        result = connection.execute(
            sql.SQL(
                """
                INSERT INTO dengue_source.notifications ({})
                SELECT {}
                FROM {}
                """
            ).format(target_columns, select_columns, temporary_table)
        )
        record_count = result.rowcount

        connection.execute(
            """
            INSERT INTO dengue_source.imported_files (
                source_file_sha256,
                source_file,
                record_count
            )
            VALUES (%s, %s, %s)
            """,
            (source_hash, file_path.name, record_count),
        )

        LOGGER.info(
            "ImportaÃ§Ã£o concluÃ­da: file=%s records=%s sha256=%s",
            file_path.name,
            record_count,
            source_hash,
        )


def resolve_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]

    if input_path.is_dir():
        return sorted(input_path.glob("*.csv.gz"))

    raise FileNotFoundError(f"Caminho nÃ£o encontrado: {input_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Importa arquivos DENGBR*.csv.gz no PostgreSQL."
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Arquivo .csv.gz ou diretÃ³rio que contÃ©m os arquivos.",
    )
    arguments = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    files = resolve_files(arguments.input_path)

    if not files:
        raise FileNotFoundError(
            f"Nenhum arquivo .csv.gz encontrado em {arguments.input_path}"
        )

    for file_path in files:
        import_file(file_path)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        LOGGER.exception("Falha na importaÃ§Ã£o.")
        sys.exit(1)