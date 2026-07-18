#!/usr/bin/env bash

set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-baip-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ATHENA_CATALOG="${ATHENA_CATALOG:-AwsDataCatalog}"
ATHENA_DATABASE="${ATHENA_DATABASE:-baip_dev_gold}"
ATHENA_WORKGROUP="${ATHENA_WORKGROUP:-baip-dev-workgroup}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VALIDATION_DIR="${REPOSITORY_ROOT}/src/athena/dengue/validation"

if [[ ! -d "${VALIDATION_DIR}" ]]; then
    echo "Validation directory not found: ${VALIDATION_DIR}" >&2
    exit 1
fi

shopt -s nullglob
sql_files=("${VALIDATION_DIR}"/*.sql)

if (( ${#sql_files[@]} == 0 )); then
    echo "No validation SQL files found in: ${VALIDATION_DIR}" >&2
    exit 1
fi

failed_checks=0

for sql_file in "${sql_files[@]}"; do
    echo "Running $(basename "${sql_file}")..."

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

    check_name="$(
        aws athena get-query-results \
            --query-execution-id "${query_execution_id}" \
            --region "${AWS_REGION}" \
            --profile "${AWS_PROFILE}" \
            --query "ResultSet.Rows[1].Data[0].VarCharValue" \
            --output text
    )"
    passed="$(
        aws athena get-query-results \
            --query-execution-id "${query_execution_id}" \
            --region "${AWS_REGION}" \
            --profile "${AWS_PROFILE}" \
            --query "ResultSet.Rows[1].Data[1].VarCharValue" \
            --output text
    )"
    details="$(
        aws athena get-query-results \
            --query-execution-id "${query_execution_id}" \
            --region "${AWS_REGION}" \
            --profile "${AWS_PROFILE}" \
            --query "ResultSet.Rows[1].Data[2].VarCharValue" \
            --output text
    )"

    if [[ "${passed}" == "true" ]]; then
        echo "PASS ${check_name}: ${details}"
    else
        echo "FAIL ${check_name}: ${details}" >&2
        failed_checks=$((failed_checks + 1))
    fi
done

if (( failed_checks > 0 )); then
    echo "${failed_checks} Athena acceptance check(s) failed." >&2
    exit 1
fi

echo "All Athena dengue acceptance checks passed."
