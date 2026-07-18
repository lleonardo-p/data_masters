#!/usr/bin/env bash

set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-baip-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ATHENA_CATALOG="${ATHENA_CATALOG:-AwsDataCatalog}"
ATHENA_DATABASE="${ATHENA_DATABASE:-baip_dev_gold}"
ATHENA_WORKGROUP="${ATHENA_WORKGROUP:-baip-dev-workgroup}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VIEWS_DIR="${REPOSITORY_ROOT}/src/athena/dengue/views"

if [[ ! -d "${VIEWS_DIR}" ]]; then
    echo "Views directory not found: ${VIEWS_DIR}" >&2
    exit 1
fi

shopt -s nullglob
sql_files=("${VIEWS_DIR}"/*.sql)

if (( ${#sql_files[@]} == 0 )); then
    echo "No view SQL files found in: ${VIEWS_DIR}" >&2
    exit 1
fi

for sql_file in "${sql_files[@]}"; do
    echo "Deploying $(basename "${sql_file}")..."

    query_execution_id="$(
        aws athena start-query-execution \
            --query-string "$(<"${sql_file}")" \
            --query-execution-context \
                "Catalog=${ATHENA_CATALOG},Database=${ATHENA_DATABASE}" \
            --work-group "${ATHENA_WORKGROUP}" \
            --region "${AWS_REGION}" \
            --profile "${AWS_PROFILE}" \
            --query "QueryExecutionId" \
            --output text
    )"

    while true; do
        state="$(
            aws athena get-query-execution \
                --query-execution-id "${query_execution_id}" \
                --region "${AWS_REGION}" \
                --profile "${AWS_PROFILE}" \
                --query "QueryExecution.Status.State" \
                --output text
        )"

        case "${state}" in
            SUCCEEDED)
                echo "Created view from $(basename "${sql_file}")."
                break
                ;;
            FAILED|CANCELLED)
                reason="$(
                    aws athena get-query-execution \
                        --query-execution-id "${query_execution_id}" \
                        --region "${AWS_REGION}" \
                        --profile "${AWS_PROFILE}" \
                        --query "QueryExecution.Status.StateChangeReason" \
                        --output text
                )"
                echo "Athena execution ${state}: ${reason}" >&2
                exit 1
                ;;
            *)
                sleep 2
                ;;
        esac
    done
done

echo "All dengue analytical views were deployed successfully."
