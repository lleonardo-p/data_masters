#!/usr/bin/env bash

set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-baip-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_DIR="${REPOSITORY_ROOT}/api-local"
TERRAFORM_DIR="${REPOSITORY_ROOT}/infra/terraform/environments/dev"

compose() {
    docker compose --project-directory "${COMPOSE_DIR}" \
        --file "${COMPOSE_DIR}/compose.yaml" "$@"
}

terraform_output() {
    terraform -chdir="${TERRAFORM_DIR}" output -raw "$1"
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Comando obrigatório não encontrado: $1" >&2
        exit 1
    fi
}

require_env_file() {
    if [[ ! -f "${COMPOSE_DIR}/.env" ]]; then
        echo "Arquivo ausente: ${COMPOSE_DIR}/.env" >&2
        echo "Crie-o a partir de api-local/.env.example." >&2
        exit 1
    fi
}

tunnel_url() {
    local attempt response url

    for attempt in {1..20}; do
        response="$(curl --silent --show-error http://localhost:4040/api/tunnels 2>/dev/null || true)"
        if [[ -n "${response}" ]]; then
            url="$(python3 -c '
import json
import sys

try:
    tunnels = json.load(sys.stdin).get("tunnels", [])
except json.JSONDecodeError:
    tunnels = []

urls = [
    item.get("public_url", "")
    for item in tunnels
    if item.get("public_url", "").startswith("https://")
]
print(urls[0] if urls else "")
' <<<"${response}")"
            if [[ -n "${url}" ]]; then
                printf '%s\n' "${url}"
                return
            fi
        fi
        sleep 1
    done

    echo "O túnel HTTPS do ngrok não está disponível." >&2
    echo "Execute: make tunnel-up" >&2
    exit 1
}

check_environment() {
    require_command aws
    require_command curl
    require_command docker
    require_command python3
    require_command terraform
    require_env_file

    docker info >/dev/null
    aws sts get-caller-identity \
        --profile "${AWS_PROFILE}" \
        --region "${AWS_REGION}" \
        --query '{Account:Account,Arn:Arn}' \
        --output table
    terraform -chdir="${TERRAFORM_DIR}" output >/dev/null
    echo "Ambiente pronto para a demonstração."
}

publish_nrt_events() {
    local count interval queue_url
    count="${COUNT:-10}"
    interval="${INTERVAL:-3}"
    queue_url="$(terraform_output dengue_nrt_queue_url)"

    NRT_SQS_QUEUE_URL="${queue_url}" \
    NRT_MAX_EVENTS="${count}" \
    NRT_EVENT_INTERVAL_SECONDS="${interval}" \
    AWS_PROFILE="${AWS_PROFILE}" \
    AWS_REGION="${AWS_REGION}" \
        compose --profile nrt run --rm --no-TTY hospital-simulator
}

show_queue_status() {
    local main_queue_url dlq_url
    main_queue_url="$(terraform_output dengue_nrt_queue_url)"
    dlq_url="$(terraform_output dengue_nrt_dlq_url)"

    echo "Fila principal"
    aws sqs get-queue-attributes \
        --queue-url "${main_queue_url}" \
        --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible \
        --profile "${AWS_PROFILE}" \
        --region "${AWS_REGION}" \
        --output table

    echo "DLQ"
    aws sqs get-queue-attributes \
        --queue-url "${dlq_url}" \
        --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible \
        --profile "${AWS_PROFILE}" \
        --region "${AWS_REGION}" \
        --output table
}

start_nrt_dashboard() {
    local api_base_url
    api_base_url="$(terraform_output dengue_nrt_api_url)"

    NRT_API_BASE_URL="${api_base_url}" \
    DASHBOARD_WINDOW_MINUTES="${WINDOW_MINUTES:-60}" \
    DASHBOARD_REFRESH_SECONDS="${REFRESH_SECONDS:-120}" \
    AWS_PROFILE="${AWS_PROFILE}" \
    AWS_REGION="${AWS_REGION}" \
        compose --profile dashboard up \
            --detach \
            --build \
            --force-recreate \
            nrt-dashboard

    echo "Dashboard NRT disponível em: http://localhost:8501"
}

main() {
    case "${1:-}" in
        check)
            check_environment
            ;;
        source-up)
            require_env_file
            compose up --detach db api
            ;;
        source-import)
            require_env_file
            compose --profile tools run --rm importer /data
            ;;
        source-health)
            curl --fail --show-error http://localhost:8000/health | python3 -m json.tool
            compose ps db api
            ;;
        tunnel-up)
            require_env_file
            compose --profile tunnel up --detach ngrok
            tunnel_url
            ;;
        tunnel-url)
            tunnel_url
            ;;
        tunnel-health)
            curl --fail --show-error "$(tunnel_url)/health" | python3 -m json.tool
            ;;
        hospital-build)
            require_env_file
            compose --profile nrt build hospital-simulator
            ;;
        nrt-publish)
            require_env_file
            publish_nrt_events
            ;;
        nrt-queues)
            show_queue_status
            ;;
        nrt-dashboard-up)
            require_env_file
            start_nrt_dashboard
            ;;
        nrt-dashboard-health)
            curl --fail --show-error http://localhost:8501/_stcore/health
            ;;
        nrt-dashboard-logs)
            compose --profile dashboard logs --follow nrt-dashboard
            ;;
        down)
            require_env_file
            compose --profile tools --profile tunnel --profile nrt --profile dashboard down
            ;;
        *)
            echo "Comando inválido: ${1:-}" >&2
            exit 1
            ;;
    esac
}

main "$@"
