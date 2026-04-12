from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://housekeep:changeme@localhost:5432/housekeep"

    # Gmail API
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_refresh_token: str = ""

    # Google Cloud / Vertex AI
    gcp_project_id: str = ""
    vertex_ai_location: str = "us-central1"

    # Application
    domain: str = "localhost"
    app_secret_key: str = "dev-secret-key-change-in-production"

    # Confidence thresholds (cosine distance: lower = more similar)
    confidence_high_threshold: float = 0.3
    confidence_medium_threshold: float = 0.5
    admin_answer_threshold: float = 0.25

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
