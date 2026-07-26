import secrets
from collections.abc import Iterator
from datetime import date

import orjson
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from app.config import API_KEY, DATABASE_URL, FETCH_SIZE


def verify_api_key(provided_api_key: str | None) -> None:
    if not API_KEY:
        raise RuntimeError("API_KEY não foi configurada.")

    if provided_api_key is None or not secrets.compare_digest(
        provided_api_key,
        API_KEY,
    ):
        raise PermissionError("API key inválida.")


def healthcheck() -> bool:
    with psycopg.connect(DATABASE_URL) as connection:
        result = connection.execute("SELECT 1").fetchone()
        return result is not None and result[0] == 1


def source_columns(
    connection: psycopg.Connection,
) -> list[tuple[str, str]]:
    rows = connection.execute(
        """
        SELECT database_name, source_name
        FROM dengue_source.source_columns
        ORDER BY ordinal_position
        """
    ).fetchall()

    if not rows:
        raise RuntimeError(
            "Nenhum arquivo foi importado. Execute o serviço importer."
        )

    return [
        (row["database_name"], row["source_name"])
        for row in rows
    ]


def stream_notifications(
    start: date,
    end: date,
) -> Iterator[bytes]:
    connection = psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    )

    try:
        columns = source_columns(connection)

        selected_columns = sql.SQL(", ").join(
            sql.SQL("{} AS {}").format(
                sql.Identifier(database_name),
                sql.Identifier(source_name),
            )
            for database_name, source_name in columns
        )

        query = sql.SQL(
            """
            SELECT {}
            FROM dengue_source.notifications
            WHERE notification_date >= %s
              AND notification_date < %s
            ORDER BY notification_date, record_id
            """
        ).format(selected_columns)

        with connection.cursor(name="dengue_stream") as cursor:
            cursor.itersize = FETCH_SIZE
            cursor.execute(query, (start, end))

            for record in cursor:
                yield orjson.dumps(record) + b"\n"
    finally:
        connection.close()