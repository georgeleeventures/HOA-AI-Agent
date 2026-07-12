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

    # Vertex AI generation cost and reliability controls
    generative_model: str = "gemini-2.5-flash"
    embedding_model: str = "text-embedding-004"
    ai_timeout_seconds: int = 20
    ai_max_concurrency: int = 1
    ai_max_output_tokens: int = 768
    ai_clarification_max_output_tokens: int = 384
    ai_classification_max_output_tokens: int = 512
    ai_ocr_max_output_tokens: int = 4096
    rag_top_k: int = 4
    rag_max_context_chars: int = 10000

    # Application
    domain: str = "localhost"
    app_secret_key: str = "dev-secret-key-change-in-production"

    # Test mode — bypasses DKIM/DMARC verification for injected test emails
    test_mode: bool = False

    # Email provider: "gmail" or "resend"
    email_provider: str = "gmail"
    resend_api_key: str = ""
    email_webhook_secret: str = "change-me-in-production"

    # Central inbox for all inbound email (Resend path).
    # Residents send to this single address; HOA is resolved from sender email.
    housekeep_inbound_email: str = "hello@housekeep.click"
    # Domain used in the From: address on outbound replies.
    resend_sending_domain: str = "housekeep.click"

    # Confidence thresholds (cosine distance: lower = more similar)
    confidence_high_threshold: float = 0.35
    confidence_medium_threshold: float = 0.55
    admin_answer_threshold: float = 0.25

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
