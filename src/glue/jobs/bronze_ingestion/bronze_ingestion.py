import sys
from datetime import datetime, timezone

from awsglue.utils import getResolvedOptions


args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "ENVIRONMENT",
        "DATA_LAKE_BUCKET",
        "ARTIFACTS_BUCKET",
    ],
)

job_name = args["JOB_NAME"]
environment = args["ENVIRONMENT"]
data_lake_bucket = args["DATA_LAKE_BUCKET"]
artifacts_bucket = args["ARTIFACTS_BUCKET"]

print(
    {
        "event": "glue_job_started",
        "job_name": job_name,
        "environment": environment,
        "data_lake_bucket": data_lake_bucket,
        "artifacts_bucket": artifacts_bucket,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
)

print("Bronze ingestion placeholder executed successfully.")