from __future__ import annotations

import os
from typing import Any, override

from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from settings.helpers import get_secret


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DB_USER: SecretStr = SecretStr("")
    DB_PASSWORD: SecretStr = SecretStr("")
    DB_HOST: SecretStr = SecretStr("")
    DB_PORT: SecretStr = SecretStr("")
    DB_NAME: SecretStr = SecretStr("")
    DB_SSLMODE: SecretStr = SecretStr("")

    OPENAI_API_KEY: SecretStr = SecretStr("")

    QDRANT_API_KEY: SecretStr = SecretStr("")
    QDRANT_ENDPOINT: SecretStr = SecretStr("")

    GCP_PROJECT_ID: str | None = None
    GCP_REGION: str | None = None
    GCS_RAW_BUCKET: str | None = None
    TASK_RUNNER_SA_EMAIL: str | None = None
    POLYMARKET_SERVICE_URL: str | None = None
    LLM_SERVICE_URL: str | None = None

    @property
    def is_remote(self) -> bool:
        """True when running on Cloud Run (service or job)."""
        return bool(os.environ.get("K_SERVICE") or os.environ.get("CLOUD_RUN_JOB"))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        sslmode = self.DB_SSLMODE.get_secret_value() or "require"
        return f"postgresql+psycopg://{self.DB_USER.get_secret_value()}:{self.DB_PASSWORD.get_secret_value()}@{self.DB_HOST.get_secret_value()}:{self.DB_PORT.get_secret_value()}/{self.DB_NAME.get_secret_value()}?sslmode={sslmode}"  # noqa: E501

    @override
    def model_post_init(self, context: Any) -> None:
        """Load secrets from GCP Secret Manager when running remotely."""
        if not self.is_remote:
            return

        self.fill_secret_gcp("DB_HOST")
        self.fill_secret_gcp("DB_PORT")
        self.fill_secret_gcp("DB_NAME")
        self.fill_secret_gcp("DB_USER")
        self.fill_secret_gcp("DB_PASSWORD")
        self.fill_secret_gcp("DB_SSLMODE")
        self.fill_secret_gcp("OPENAI_API_KEY")
        self.fill_secret_gcp("QDRANT_API_KEY")
        self.fill_secret_gcp("QDRANT_ENDPOINT")

    def fill_secret_gcp(self, name: str) -> None:
        """Populate ``self.<name>`` from GSM if currently empty.

        The GSM secret id matches the field name.
        """
        current: SecretStr = getattr(self, name)
        if current.get_secret_value() != "":
            return

        object.__setattr__(
            self,
            name,
            SecretStr(get_secret(secret_id=name, project_id=self.GCP_PROJECT_ID)),
        )
