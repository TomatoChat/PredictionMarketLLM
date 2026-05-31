# Cloud SQL Deployer (Pulumi)

Provisions the project's Cloud SQL Postgres instance.

Only one stack today: `prd`.

## What it deploys

| Resource | Pulumi type | Notes |
|---|---|---|
| Postgres 18 instance | `gcp:sql:DatabaseInstance` | Enterprise Plus, `db-perf-optimized-N-8` (8 vCPU / 64 GB / 100 GB SSD) — matches the 30-day free trial. Downgrade after the trial by editing `cloud-sql-deployer:tier` (e.g. to `db-perf-optimized-N-2`) and re-running `pulumi up`. Zonal, daily backup at 03:00, deletion protection ON. Public IP enabled but no authorized networks — Cloud Run reaches it via the built-in Cloud SQL connector (Unix socket `/cloudsql/<instance>`). |

Application data lives in the default `postgres` database (auto-created with the instance) and authenticates as the default `postgres` admin user. The admin password is set in the GCP UI at instance-creation time and lives in the GSM secret `DB_PASSWORD`. No `gcp.sql.Database` or `gcp.sql.User` resources are managed by this stack — keeping the password out of Pulumi state means rotations are a GCP-side action.

## Exports

- `instance_name`
- `instance_connection_name` — `<project>:<region>:<instance>`. Consumed by `cloud_run_deployer` via `pulumi.StackReference` to mount as `cloudsql_instances` on each service.

## Deploy

CI auto-deploys on push to `main` touching this deployer — see [.github/workflows/deploy.yml](../../../.github/workflows/deploy.yml) (the `cloud_sql_deployer` job, which runs **before** `cloud_run_deployer` and `alembic_migrate`).

Locally:

```bash
cd backend/infra/cloud_sql_deployer
python -m venv .venv
.venv/bin/pip install -r requirements.txt

pulumi stack select prd
pulumi up
```

Set the `DB_*` secrets in Secret Manager once (the password is the one you typed into the GCP UI when creating the instance):

```bash
INSTANCE=$(pulumi stack output instance_connection_name)
echo -n "/cloudsql/$INSTANCE" | gcloud secrets versions add DB_HOST --data-file=-
echo -n "5432"                | gcloud secrets versions add DB_PORT --data-file=-
echo -n "postgres"            | gcloud secrets versions add DB_NAME --data-file=-
echo -n "postgres"            | gcloud secrets versions add DB_USER --data-file=-
echo -n "<your password>"     | gcloud secrets versions add DB_PASSWORD --data-file=-
echo -n "disable"             | gcloud secrets versions add DB_SSLMODE --data-file=-
```

Stack-config keys (in [Pulumi.prd.yaml](Pulumi.prd.yaml)):

| Key | Required | Notes |
|---|---|---|
| `gcp:project` | yes | GCP project ID. |
| `gcp:region` | no | Defaults to `europe-west3`. |
| `cloud-sql-deployer:instanceName` | no | Default `prediction-market` (per-project — `stg` will live in its own GCP project, so no env suffix needed). |
| `cloud-sql-deployer:tier` | no | Default `db-perf-optimized-N-8` (Enterprise Plus 8 vCPU — matches the 30-day free trial). |
| `cloud-sql-deployer:edition` | no | Default `ENTERPRISE_PLUS`. Set to `ENTERPRISE` if downgrading. |
| `cloud-sql-deployer:diskSize` | no | Default `100` GB. |
