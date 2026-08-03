#!/usr/bin/env bash

set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-baip-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TERRAFORM_DIR="${REPOSITORY_ROOT}/infra/terraform/environments/dev"

usage() {
    cat <<'USAGE'
Usage: ./scripts/dengue_batch.sh <command>

Commands:
  start      Start a single-period or backfill batch.
  status     Show the most recent execution status.
  watch      Monitor the most recent execution until it finishes.
  history    List the ten most recent executions.
  manifest   Print the reconciliation manifest for the latest batch.
  validate   Run all Athena acceptance checks.

Optional environment variables:
  AWS_PROFILE  AWS CLI profile. Default: baip-dev
  AWS_REGION   AWS region. Default: us-east-1
  BATCH_ID     Batch used by start or manifest. Default: generated/latest.
  API_BASE_URL Required by start. HTTPS URL exposed by ngrok.
  LOAD_MODE    single or backfill. Default: single.
  GRANULARITY  month or day. Default: month.
  PROCESSING_DATE Processing date in YYYY-MM-DD. Default: current UTC date.
  REFERENCE_PERIOD Period used by single mode.
  START_PERIOD and END_PERIOD Interval used by backfill mode.
  FORCE        true to replace an existing extraction. Default: false.
  WATCH_INTERVAL_SECONDS Polling interval used by watch. Default: 300.
USAGE
}

require_command() {
    local command_name="$1"

    if ! command -v "${command_name}" >/dev/null 2>&1; then
        echo "Required command not found: ${command_name}" >&2
        exit 1
    fi
}

terraform_output() {
    terraform -chdir="${TERRAFORM_DIR}" output -raw "$1"
}

state_machine_arn() {
    terraform_output "dengue_batch_state_machine_arn"
}

latest_execution_field() {
    local field="$1"
    local machine_arn
    machine_arn="$(state_machine_arn)"

    aws stepfunctions list-executions \
        --state-machine-arn "${machine_arn}" \
        --max-results 1 \
        --profile "${AWS_PROFILE}" \
        --region "${AWS_REGION}" \
        --query "executions[0].${field}" \
        --output text
}

build_execution_input() {
    local load_mode="${LOAD_MODE:-single}"
    local api_base_url="${API_BASE_URL:-}"
    local granularity="${GRANULARITY:-month}"
    local processing_date="${PROCESSING_DATE:-$(date -u +%F)}"
    local force="${FORCE:-false}"

    if [[ -z "${api_base_url}" ]]; then
        echo "API_BASE_URL is required." >&2
        exit 1
    fi

    python3 - \
        "${load_mode}" "${api_base_url}" "${granularity}" \
        "${processing_date}" "${force}" \
        "${REFERENCE_PERIOD:-}" "${START_PERIOD:-}" "${END_PERIOD:-}" <<'PY'
import json
import sys

(
    load_mode,
    api_base_url,
    granularity,
    processing_date,
    force_value,
    reference_period,
    start_period,
    end_period,
) = sys.argv[1:]

if load_mode not in {"single", "backfill"}:
    raise SystemExit("LOAD_MODE must be single or backfill.")
if granularity not in {"month", "day"}:
    raise SystemExit("GRANULARITY must be month or day.")
if force_value.lower() not in {"true", "false"}:
    raise SystemExit("FORCE must be true or false.")

payload = {
    "api_base_url": api_base_url,
    "load_mode": load_mode,
    "granularity": granularity,
    "processing_date": processing_date,
    "force": force_value.lower() == "true",
}

if load_mode == "single":
    if not reference_period:
        raise SystemExit("REFERENCE_PERIOD is required for single mode.")
    payload["reference_period"] = reference_period
else:
    if not start_period or not end_period:
        raise SystemExit("START_PERIOD and END_PERIOD are required for backfill mode.")
    payload["start_period"] = start_period
    payload["end_period"] = end_period

print(json.dumps(payload, separators=(",", ":")))
PY
}

start_batch() {
    local machine_arn running_count batch_id execution_arn execution_input suffix
    machine_arn="$(state_machine_arn)"

    running_count="$(
        aws stepfunctions list-executions \
            --state-machine-arn "${machine_arn}" \
            --status-filter RUNNING \
            --max-results 1 \
            --profile "${AWS_PROFILE}" \
            --region "${AWS_REGION}" \
            --query 'length(executions)' \
            --output text
    )"

    if [[ "${running_count}" != "0" ]]; then
        echo "A dengue batch execution is already running:" >&2
        aws stepfunctions list-executions \
            --state-machine-arn "${machine_arn}" \
            --status-filter RUNNING \
            --max-results 1 \
            --profile "${AWS_PROFILE}" \
            --region "${AWS_REGION}" \
            --query 'executions[].{Name:name,Started:startDate}' \
            --output table >&2
        exit 2
    fi

    execution_input="$(build_execution_input)"
    if [[ "${LOAD_MODE:-single}" == "backfill" ]]; then
        suffix="backfill-${START_PERIOD}-${END_PERIOD}"
    else
        suffix="${GRANULARITY:-month}-${REFERENCE_PERIOD}"
    fi
    suffix="${suffix//:/-}"
    batch_id="${BATCH_ID:-dengue-${suffix}-$(date -u +%Y%m%dT%H%M%SZ)}"
    execution_arn="$(
        aws stepfunctions start-execution \
            --state-machine-arn "${machine_arn}" \
            --name "${batch_id}" \
            --input "${execution_input}" \
            --profile "${AWS_PROFILE}" \
            --region "${AWS_REGION}" \
            --query executionArn \
            --output text
    )"

    echo "Batch started."
    echo "batch_id=${batch_id}"
    echo "execution_arn=${execution_arn}"
    echo "Next: make batch-watch"
}

show_status() {
    local execution_arn
    execution_arn="$(latest_execution_field executionArn)"

    if [[ -z "${execution_arn}" || "${execution_arn}" == "None" ]]; then
        echo "No dengue batch execution was found." >&2
        exit 1
    fi

    aws stepfunctions describe-execution \
        --execution-arn "${execution_arn}" \
        --profile "${AWS_PROFILE}" \
        --region "${AWS_REGION}" \
        --query '{Name:name,Status:status,Started:startDate,Finished:stopDate,Error:error,Cause:cause}' \
        --output table
}

watch_execution() {
    local execution_arn status interval
    execution_arn="$(latest_execution_field executionArn)"
    interval="${WATCH_INTERVAL_SECONDS:-300}"

    if [[ -z "${execution_arn}" || "${execution_arn}" == "None" ]]; then
        echo "No dengue batch execution was found." >&2
        exit 1
    fi

    while true; do
        status="$(
            aws stepfunctions describe-execution \
                --execution-arn "${execution_arn}" \
                --profile "${AWS_PROFILE}" \
                --region "${AWS_REGION}" \
                --query status \
                --output text
        )"
        echo "$(date '+%Y-%m-%d %H:%M:%S') | ${status}"
        if [[ "${status}" != "RUNNING" ]]; then
            break
        fi
        sleep "${interval}"
    done
}

show_history() {
    local machine_arn
    machine_arn="$(state_machine_arn)"

    aws stepfunctions list-executions \
        --state-machine-arn "${machine_arn}" \
        --max-results 10 \
        --profile "${AWS_PROFILE}" \
        --region "${AWS_REGION}" \
        --query 'executions[].{Name:name,Status:status,Started:startDate,Finished:stopDate}' \
        --output table
}

show_manifest() {
    local batch_id logs_bucket manifest_uri
    batch_id="${BATCH_ID:-$(latest_execution_field name)}"

    if [[ -z "${batch_id}" || "${batch_id}" == "None" ]]; then
        echo "No batch was found for manifest lookup." >&2
        exit 1
    fi

    logs_bucket="$(terraform_output logs_bucket_name)"
    manifest_uri="s3://${logs_bucket}/pipeline-runs/dengue-batch/reconciliation/batch_id=${batch_id}/reconciliation.json"

    echo "Manifest: ${manifest_uri}" >&2
    aws s3 cp \
        "${manifest_uri}" \
        - \
        --profile "${AWS_PROFILE}" \
        --region "${AWS_REGION}"
}

run_validation() {
    AWS_PROFILE="${AWS_PROFILE}" \
    AWS_REGION="${AWS_REGION}" \
        "${SCRIPT_DIR}/run_athena_dengue_acceptance.sh"
}

main() {
    local command_name="${1:-}"

    case "${command_name}" in
        help|-h|--help|"")
            usage
            return
            ;;
    esac

    require_command aws
    require_command python3
    require_command terraform

    case "${command_name}" in
        start)
            start_batch
            ;;
        status)
            show_status
            ;;
        watch)
            watch_execution
            ;;
        history)
            show_history
            ;;
        manifest)
            show_manifest
            ;;
        validate)
            run_validation
            ;;
        *)
            echo "Unknown command: ${command_name}" >&2
            usage >&2
            exit 1
            ;;
    esac
}

main "$@"
