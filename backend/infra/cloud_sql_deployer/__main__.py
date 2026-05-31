"""
Pulumi entry point for the Cloud SQL deployer.

Provisions one `gcp.sql.DatabaseInstance` (Postgres 18) — Enterprise Plus,
public IP enabled but with no authorized networks (Cloud Run reaches it over
the built-in Cloud SQL connector via Unix socket — see
`cloud_run_deployer/src/helpers/deploy_service.py`).

Application data lives in the default `postgres` database that Cloud SQL
auto-creates with the instance, and authenticates as the default `postgres`
admin user (whose password was set in the GCP UI when the instance was
created and lives in the GSM secret `DB_PASSWORD`). No `gcp.sql.Database` or
`gcp.sql.User` resources are managed here — adding either would require
managing the password lifecycle too, which we keep out of code state.

Exports `instance_connection_name` (`<project>:<region>:<instance>`) so
`cloud_run_deployer` can pull it via `pulumi.StackReference` and pass it to
`cloudsql_instances` on each service's template.
"""

from __future__ import annotations

import pulumi
import pulumi_gcp as gcp

config = pulumi.Config()
gcp_config = pulumi.Config("gcp")

project_id = gcp_config.require("project")
region = gcp_config.get("region") or "europe-west3"

instance_name = config.get("instanceName") or "prediction-market"
tier = config.get("tier") or "db-perf-optimized-N-8"
edition = config.get("edition") or "ENTERPRISE_PLUS"
disk_size = config.get_int("diskSize") or 100

instance = gcp.sql.DatabaseInstance(
    "primary",
    name=instance_name,
    project=project_id,
    region=region,
    database_version="POSTGRES_18",
    deletion_protection=True,
    settings=gcp.sql.DatabaseInstanceSettingsArgs(
        tier=tier,
        edition=edition,
        availability_type="ZONAL",
        disk_type="PD_SSD",
        disk_size=disk_size,
        disk_autoresize=False,
        # IAM database authentication: allows GCP identities to auth alongside
        # password auth (we still use password auth via DB_PASSWORD). Free for
        # later use; preserves what GCP set during instance creation.
        database_flags=[
            gcp.sql.DatabaseInstanceSettingsDatabaseFlagArgs(
                name="cloudsql.iam_authentication",
                value="on",
            ),
        ],
        backup_configuration=gcp.sql.DatabaseInstanceSettingsBackupConfigurationArgs(
            enabled=False,
            point_in_time_recovery_enabled=False,
            start_time="16:00",
        ),
        ip_configuration=gcp.sql.DatabaseInstanceSettingsIpConfigurationArgs(
            ipv4_enabled=True,
        ),
        # Match the free-trial default — re-asserting prevents Pulumi from
        # trying to clear it on refresh.
        enable_dataplex_integration=True,
        # `final_backup_config` is left unmanaged: the GCP-side default
        # (`enabled=false, retention_days=0`) clashes with the Pulumi schema's
        # `retention_days >= 1` validation, AND the API rejects any non-zero
        # retention when disabled. Ignored in `opts.ignore_changes` so refresh
        # drift doesn't trigger spurious updates.
    ),
    opts=pulumi.ResourceOptions(
        ignore_changes=["settings.finalBackupConfig"],
    ),
)

pulumi.export("instance_name", instance.name)
pulumi.export("instance_connection_name", instance.connection_name)
