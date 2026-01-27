from enum import Enum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)
    secret_key: str = Field(...)
    
    database_url: str = Field(...)
    
    data_dir: Path = Field(default=Path("/app/data"))
    use_s3: bool = Field(default=False)
    s3_bucket_name: str | None = Field(default=None)
    aws_region: str | None = Field(default=None)
    
    smtp_host: str = Field(...)
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(...)
    smtp_password: str = Field(...)
    smtp_from_email: str = Field(...)
    smtp_from_name: str = Field(default="OHS Remote")
    
    stripe_api_key: str = Field(...)
    stripe_webhook_secret: str = Field(...)
    
    allowed_origins: str = Field(default="http://localhost:3000,http://localhost:5173")
    
    log_level: str = Field(default="INFO")
    
    max_logo_size_mb: int = Field(default=5)
    allowed_logo_extensions: str = Field(default=".png,.jpg,.jpeg,.svg")
    
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: str | list[str]) -> str:
        if isinstance(v, list):
            return ",".join(v)
        return v
    
    @field_validator("allowed_logo_extensions", mode="before")
    @classmethod
    def parse_allowed_logo_extensions(cls, v: str | list[str]) -> str:
        if isinstance(v, list):
            return ",".join(v)
        return v
    
    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @property
    def logo_extensions(self) -> list[str]:
        return [ext.strip() for ext in self.allowed_logo_extensions.split(",")]
    
    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT
    
    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"
    
    @property
    def logos_dir(self) -> Path:
        return self.uploads_dir / "logos"
    
    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"
    
    @property
    def generated_documents_dir(self) -> Path:
        return self.documents_dir / "generated"
    
    @property
    def preview_documents_dir(self) -> Path:
        return self.documents_dir / "previews"


settings = Settings()
