#!/usr/bin/env bash

set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-baip-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TERRAFORM_DIR="${REPOSITORY_ROOT}/infra/terraform/environments/dev"

require_command() {
    local command_name="$1"

    if ! command -v "${command_name}" >/dev/null 2>&1; then
        echo "Required command not found: ${command_name}" >&2
        exit 1
    fi
}

require_command aws
require_command terraform

AWS_ACCOUNT_ID="$(
    aws sts get-caller-identity \
        --profile "${AWS_PROFILE}" \
        --region "${AWS_REGION}" \
        --query 'Account' \
        --output text
)"

if ! DATA_SET_ID="$(
    terraform -chdir="${TERRAFORM_DIR}" \
        output -raw quicksight_dengue_data_set_id 2>/dev/null
)"; then
    echo "QuickSight dengue dataset is not enabled in Terraform state." >&2
    exit 1
fi

if [[ -z "${DATA_SET_ID}" || "${DATA_SET_ID}" == "null" ]]; then
    echo "No QuickSight dengue dataset was found in Terraform outputs." >&2
    echo "Enable enable_quicksight_dengue and apply Terraform first." >&2
    exit 1
fi

ingestion_id="batch-$(date -u +%Y%m%dT%H%M%SZ)"

echo "Starting SPICE ingestion for ${DATA_SET_ID}..."

aws quicksight create-ingestion \
    --aws-account-id "${AWS_ACCOUNT_ID}" \
    --data-set-id "${DATA_SET_ID}" \
    --ingestion-id "${ingestion_id}" \
    --profile "${AWS_PROFILE}" \
    --region "${AWS_REGION}" \
    --output json >/dev/null

while true; do
    status="$(
        aws quicksight describe-ingestion \
            --aws-account-id "${AWS_ACCOUNT_ID}" \
            --data-set-id "${DATA_SET_ID}" \
            --ingestion-id "${ingestion_id}" \
            --profile "${AWS_PROFILE}" \
            --region "${AWS_REGION}" \
            --query 'Ingestion.IngestionStatus' \
            --output text
    )"

    case "${status}" in
        COMPLETED)
            echo "SPICE ingestion completed for ${DATA_SET_ID}."
            break
            ;;
        FAILED|CANCELLED)
            error_info="$(
                aws quicksight describe-ingestion \
                    --aws-account-id "${AWS_ACCOUNT_ID}" \
                    --data-set-id "${DATA_SET_ID}" \
                    --ingestion-id "${ingestion_id}" \
                    --profile "${AWS_PROFILE}" \
                    --region "${AWS_REGION}" \
                    --query 'Ingestion.ErrorInfo' \
                    --output json
            )"
            echo "SPICE ingestion ${status} for ${DATA_SET_ID}: ${error_info}" >&2
            exit 1
            ;;
        *)
            echo "${DATA_SET_ID}: ${status}"
            sleep 10
            ;;
    esac
done

echo "The dengue QuickSight dataset was refreshed successfully."
