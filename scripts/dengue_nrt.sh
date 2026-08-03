#!/usr/bin/env bash

set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-baip-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TERRAFORM_DIR="${REPOSITORY_ROOT}/infra/terraform/environments/dev"

terraform_output() {
    terraform -chdir="${TERRAFORM_DIR}" output -raw "$1"
}

api_url() {
    terraform_output dengue_nrt_api_url
}

load_aws_credentials() {
    local exports
    exports="$(
        aws configure export-credentials \
            --profile "${AWS_PROFILE}" \
            --format env
    )"
    eval "${exports}"
    export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
}

signed_curl_arguments() {
    CURL_AUTH=(
        --aws-sigv4 "aws:amz:${AWS_REGION}:execute-api"
        --user "${AWS_ACCESS_KEY_ID}:${AWS_SECRET_ACCESS_KEY}"
    )
    if [[ -n "${AWS_SESSION_TOKEN:-}" ]]; then
        CURL_AUTH+=(--header "x-amz-security-token: ${AWS_SESSION_TOKEN}")
    fi
}

show_indicators() {
    local scope_type scope_value window_minutes
    scope_type="${SCOPE_TYPE:-GLOBAL}"
    scope_value="${SCOPE_VALUE:-}"
    window_minutes="${WINDOW_MINUTES:-60}"

    load_aws_credentials
    signed_curl_arguments

    CURL_QUERY=(
        --get
        --data-urlencode "scope_type=${scope_type}"
        --data-urlencode "window_minutes=${window_minutes}"
    )
    if [[ -n "${scope_value}" ]]; then
        CURL_QUERY+=(--data-urlencode "scope_value=${scope_value}")
    fi
    if [[ -n "${START:-}" ]]; then
        CURL_QUERY+=(--data-urlencode "start=${START}")
    fi
    if [[ -n "${END:-}" ]]; then
        CURL_QUERY+=(--data-urlencode "end=${END}")
    fi

    curl --fail --show-error --silent \
        "${CURL_AUTH[@]}" \
        "${CURL_QUERY[@]}" \
        "$(api_url)/v1/indicators" |
        python3 -m json.tool
}

show_patient_history() {
    local cpf limit payload
    cpf="${CPF:-}"
    limit="${LIMIT:-50}"

    if [[ -z "${cpf}" ]]; then
        echo "Informe um CPF sintético: make nrt-history CPF=90088005780" >&2
        exit 1
    fi

    payload="$(python3 - "${cpf}" "${limit}" <<'PY'
import json
import sys

print(json.dumps({"cpf": sys.argv[1], "limit": int(sys.argv[2])}))
PY
)"

    load_aws_credentials
    signed_curl_arguments

    curl --fail --show-error --silent \
        "${CURL_AUTH[@]}" \
        --header "content-type: application/json" \
        --request POST \
        --data "${payload}" \
        "$(api_url)/v1/patients/history" |
        python3 -m json.tool
}

show_logs() {
    echo "Processador NRT"
    aws logs tail \
        /aws/lambda/baip-dev-dengue-nrt-processor \
        --since "${SINCE:-10m}" \
        --profile "${AWS_PROFILE}" \
        --region "${AWS_REGION}"

    echo "API NRT"
    aws logs tail \
        /aws/lambda/baip-dev-dengue-nrt-api \
        --since "${SINCE:-10m}" \
        --profile "${AWS_PROFILE}" \
        --region "${AWS_REGION}"
}

case "${1:-}" in
    health)
        curl --fail --show-error --silent "$(api_url)/health" | python3 -m json.tool
        ;;
    indicators)
        show_indicators
        ;;
    history)
        show_patient_history
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "Uso: $0 health|indicators|history|logs" >&2
        exit 1
        ;;
esac
