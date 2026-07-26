# -*- coding: utf-8 -*-

from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse, StreamingResponse

from app.database import (
    healthcheck,
    stream_notifications,
    verify_api_key,
)
from app.periods import day_range, parse_day, parse_month


app = FastAPI(
    title="API de Dados Públicos de Dengue",
    description=(
        "Fonte externa controlada para a extração Batch do projeto BAIP."
    ),
    version="1.0.0",
    default_response_class=ORJSONResponse,
)

app.add_middleware(
    GZipMiddleware,
    minimum_size=1024,
    compresslevel=5,
)


def require_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    try:
        verify_api_key(x_api_key)
    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error


@app.get("/health", tags=["operational"])
def get_health() -> dict[str, str]:
    try:
        database_status = "up" if healthcheck() else "down"
    except Exception:
        database_status = "down"

    if database_status == "down":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponível.",
        )

    return {
        "status": "up",
        "database": database_status,
    }


@app.get(
    "/v1/dengue/monthly",
    dependencies=[Depends(require_api_key)],
    tags=["dengue"],
)
def get_monthly_notifications(
    periodo_notificacao: Annotated[
        str,
        Query(
            description=(
                "Mês de notificação em YYYY-MM ou MM-YYYY."
            ),
            examples=["2024-01"],
        ),
    ],
) -> StreamingResponse:
    try:
        start, end = parse_month(periodo_notificacao)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return StreamingResponse(
        stream_notifications(start, end),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": (
                f'attachment; filename="dengue-{start:%Y-%m}.jsonl"'
            )
        },
    )


@app.get(
    "/v1/dengue/daily",
    dependencies=[Depends(require_api_key)],
    tags=["dengue"],
)
def get_daily_notifications(
    data_notificacao: Annotated[
        str,
        Query(
            description=(
                "Data de notificação em YYYY-MM-DD ou DD-MM-YYYY."
            ),
            examples=["2024-01-01"],
        ),
    ],
) -> StreamingResponse:
    try:
        reference_date = parse_day(data_notificacao)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    start, end = day_range(reference_date)

    return StreamingResponse(
        stream_notifications(start, end),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": (
                f'attachment; filename="dengue-'
                f'{reference_date:%Y-%m-%d}.jsonl"'
            )
        },
    )