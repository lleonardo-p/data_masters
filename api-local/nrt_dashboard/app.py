import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import boto3
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


BRAZILIAN_STATES = (
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
)
RISK_FIELDS = (
    "risk_blue",
    "risk_green",
    "risk_yellow",
    "risk_orange",
    "risk_red",
)

API_BASE_URL = os.environ.get("NRT_API_BASE_URL", "").rstrip("/")
AWS_PROFILE = os.environ.get("AWS_PROFILE", "baip-dev")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DEFAULT_WINDOW_MINUTES = int(os.environ.get("DASHBOARD_WINDOW_MINUTES", "60"))
REFRESH_SECONDS = int(os.environ.get("DASHBOARD_REFRESH_SECONDS", "120"))


st.set_page_config(
    page_title="BAIP | Monitoramento NRT",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.8rem; padding-bottom: 2rem;}
    [data-testid="stMetric"] {
        background: #f7fafc;
        border: 1px solid #dce6ef;
        border-radius: 12px;
        padding: 14px;
    }
    .state-card {
        background: #ffffff;
        border: 1px solid #dce6ef;
        border-left: 5px solid #2389b9;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(22, 47, 69, 0.08);
        margin-bottom: 12px;
        padding: 14px 16px;
    }
    .state-card.first {border-left-color: #b91c1c;}
    .state-card.second {border-left-color: #ef4444;}
    .state-card-position {
        color: #64748b;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .state-card-value {
        color: #172b3a;
        font-size: 1.15rem;
        font-weight: 700;
        margin-top: 4px;
        white-space: nowrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def aws_session() -> boto3.Session:
    return boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)


def signed_get(url: str) -> dict[str, Any]:
    session = aws_session()
    credentials = session.get_credentials()
    if credentials is None:
        raise RuntimeError(f"Credenciais do profile {AWS_PROFILE!r} não encontradas.")

    request = AWSRequest(method="GET", url=url)
    SigV4Auth(
        credentials.get_frozen_credentials(),
        "execute-api",
        AWS_REGION,
    ).add_auth(request)

    response = requests.get(
        url,
        headers=dict(request.headers.items()),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def state_indicators(state: str, window_minutes: int) -> dict[str, Any]:
    query = urlencode(
        {
            "scope_type": "STATE",
            "scope_value": state,
            "window_minutes": window_minutes,
        }
    )
    payload = signed_get(f"{API_BASE_URL}/v1/indicators?{query}")
    totals = payload.get("totals", {})
    return {
        "uf": state,
        "total_triages": int(totals.get("total_triages", 0)),
        **{field: int(totals.get(field, 0)) for field in RISK_FIELDS},
    }


def load_state_ranking(window_minutes: int) -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(state_indicators, state, window_minutes): state
            for state in BRAZILIAN_STATES
        }
        for future in as_completed(futures):
            state = futures[future]
            try:
                rows.append(future.result())
            except Exception:
                failures.append(state)

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame, sorted(failures)

    frame = frame.sort_values(
        ["total_triages", "uf"],
        ascending=[False, True],
    ).reset_index(drop=True)
    frame.insert(0, "posicao", frame.index + 1)
    return frame, sorted(failures)


def ranking_chart(ranking: pd.DataFrame) -> go.Figure:
    plot_frame = ranking.sort_values("total_triages", ascending=True)
    colors = [
        "#B91C1C" if position == 1 else "#EF4444" if position == 2 else "#2389B9"
        for position in plot_frame["posicao"]
    ]
    fixed_labels = [
        f"{state} | {total:,} {'triagem' if total == 1 else 'triagens'}"
        for state, total in zip(
            plot_frame["uf"],
            plot_frame["total_triages"],
        )
    ]

    figure = go.Figure(
        go.Bar(
            x=plot_frame["total_triages"],
            y=plot_frame["uf"],
            orientation="h",
            marker_color=colors,
            text=fixed_labels,
            textposition="inside",
            insidetextanchor="end",
            textfont=dict(color="#FFFFFF", size=16, weight="bold"),
            constraintext="none",
            customdata=plot_frame[["posicao"]],
            hovertemplate=(
                "<b>%{y}</b><br>Posição: %{customdata[0]}"
                "<br>Triagens: %{x:,}<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        title="10 UFs com mais triagens no período",
        xaxis_title="Quantidade de triagens",
        yaxis_title="",
        height=520,
        margin=dict(l=30, r=70, t=70, b=40),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#172B3A"),
        showlegend=False,
        uniformtext_minsize=13,
        uniformtext_mode="show",
    )
    figure.update_xaxes(showgrid=True, gridcolor="#E8EEF3", rangemode="tozero")
    return figure


def show_state_cards(ranking: pd.DataFrame) -> None:
    records = ranking.head(10).to_dict("records")

    for start in range(0, len(records), 5):
        row = records[start : start + 5]
        columns = st.columns(5)
        for column, item in zip(columns, row):
            position = int(item["posicao"])
            card_class = "first" if position == 1 else "second" if position == 2 else ""
            total = int(item["total_triages"])
            label = "triagem" if total == 1 else "triagens"
            column.markdown(
                f"""
                <div class="state-card {card_class}">
                    <div class="state-card-position">{position}º lugar</div>
                    <div class="state-card-value">{item['uf']} | {total:,} {label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


st.title("BAIP — Monitoramento NRT de dengue")
st.caption(
    "Triagens processadas em tempo quase real. "
    "As duas UFs com maior volume recebem destaque em vermelho."
)

window_minutes = st.selectbox(
    "Período analisado",
    options=(15, 30, 60, 180, 360, 720, 1440),
    index=(15, 30, 60, 180, 360, 720, 1440).index(DEFAULT_WINDOW_MINUTES)
    if DEFAULT_WINDOW_MINUTES in (15, 30, 60, 180, 360, 720, 1440)
    else 2,
    format_func=lambda value: f"Últimos {value // 60} h" if value >= 60 else f"Últimos {value} min",
)


@st.fragment(run_every=f"{REFRESH_SECONDS}s")
def dashboard() -> None:
    if not API_BASE_URL:
        st.error("NRT_API_BASE_URL não foi configurada no contêiner.")
        return

    with st.spinner("Consultando indicadores das UFs..."):
        ranking, failures = load_state_ranking(window_minutes)

    if failures:
        st.warning("Não foi possível consultar: " + ", ".join(failures))
    if ranking.empty:
        st.error("A API não retornou indicadores estaduais.")
        return

    active_states = ranking[ranking["total_triages"] > 0]
    top_states = active_states.head(10)
    total_triages = int(ranking["total_triages"].sum())
    critical_triages = int(ranking["risk_orange"].sum() + ranking["risk_red"].sum())

    first, second, third = st.columns(3)
    first.metric("Triagens no período", f"{total_triages:,}")
    second.metric("UFs com atividade", len(active_states))
    third.metric("Risco laranja ou vermelho", f"{critical_triages:,}")

    if top_states.empty:
        st.info(
            "Nenhuma triagem foi registrada no período selecionado. "
            "Publique novos eventos ou amplie a janela de consulta."
        )
    else:
        show_state_cards(top_states)
        st.plotly_chart(
            ranking_chart(top_states),
            use_container_width=True,
            config={"displayModeBar": False},
        )
        st.dataframe(
            top_states[
                [
                    "posicao",
                    "uf",
                    "total_triages",
                    "risk_green",
                    "risk_yellow",
                    "risk_orange",
                    "risk_red",
                ]
            ].rename(
                columns={
                    "posicao": "Posição",
                    "uf": "UF",
                    "total_triages": "Triagens",
                    "risk_green": "Verde",
                    "risk_yellow": "Amarelo",
                    "risk_orange": "Laranja",
                    "risk_red": "Vermelho",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )

    updated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")
    st.caption(
        f"Atualizado em {updated_at}. Atualização automática a cada "
        f"{REFRESH_SECONDS} segundos."
    )


dashboard()
