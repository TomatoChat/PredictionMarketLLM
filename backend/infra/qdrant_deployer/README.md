# qdrant_deployer

Pulumi stack that manages the **Qdrant Cloud cluster** (control plane) as IaC,
for parity with `cloud_run_deployer` / `queue_deployer` / `cron_deployer`.

## Scope — read this first

This stack manages the **cluster** (and a database API key). It does **NOT**
manage **collections** ("tables"). Collections are data-plane objects defined in
[`backend/qdrant/schema.py`](../../qdrant/schema.py) and reconciled by:

```bash
PYTHONPATH=backend python -m qdrant.sync
```

which runs automatically as the `qdrant_sync` job in
[`.github/workflows/deploy.yml`](../../../.github/workflows/deploy.yml). To add or
change a collection, edit `schema.py` + its `COLLECTIONS` registry — not this stack.

## One-time setup

The Qdrant Cloud provider is a **Terraform-bridged** Pulumi provider, so its
Python SDK is generated locally (not on PyPI):

```bash
cd backend/infra/qdrant_deployer
python -m venv .venv && .venv/bin/pip install -r requirements.txt
pulumi package add terraform-provider registry.terraform.io/qdrant/qdrant-cloud
# ^ generates the pulumi_qdrant_cloud SDK under ./sdks and wires it as a dependency
```

Provider auth + stack config:

```bash
pulumi stack init prd            # creates Pulumi.prd.yaml (+ encryption salt)
export QDRANT_CLOUD_API_KEY=...  # account-level Qdrant Cloud API key (provider auth)
pulumi config set accountId <qdrant-cloud-account-id>
pulumi config set cloudProvider gcp
pulumi config set cloudRegion europe-west3
# optional: pulumi config set packageId <id>   (else the first package for the region)
```

> Confirm the exact provider config keys (`accountId`, auth env var) and the
> data-source / resource symbol names in [`__main__.py`](./__main__.py) against
> the SDK that `pulumi package add` generates — they come from the bridged
> Terraform provider and may differ slightly from the placeholders here.

## ⚠️ Import the existing cluster before the first `pulumi up`

A cluster already exists (the live `QDRANT_ENDPOINT`). If you `pulumi up` on an
empty stack, Pulumi will **create a second cluster and orphan your data**. Import
it first so Pulumi adopts the existing resource:

```bash
pulumi import qdrant-cloud:index/accountsCluster:AccountsCluster markets-cluster <cluster-id>
```

(Find `<cluster-id>` in the Qdrant Cloud console.)

## Deploy

```bash
pulumi up --yes --refresh --stack prd
```

This stack is **intentionally not yet wired into the deploy workflow** — auto
`pulumi up` is unsafe until the existing cluster is imported. Once imported and
verified, add a `qdrant_deployer` job to `deploy.yml` mirroring the other stacks.
