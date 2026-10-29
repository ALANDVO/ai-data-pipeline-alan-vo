from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    jwt_secret: str = "change-me-in-production"
    jwt_expiry_minutes: int = 60
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o"
    # OIDC/Keycloak settings
    oidc_issuer_url: str = "http://localhost:8080/realms/pipeline-realm"
    oidc_client_id: str = "pipeline-frontend"
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = "http://localhost:8000/api/auth/callback"
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_redirect_uri: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "us-east-1"
    s3_bucket_name: str = ""
    gcs_bucket_name: str = ""
    gcs_service_account_json: str = ""
    bigquery_project: str = ""
    bigquery_dataset: str = ""
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "analytics"
    postgres_user: str = "etl"
    postgres_password: str = ""

    class Config:
        env_prefix = ""

settings = Settings(
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8000")),
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    jwt_secret=os.getenv("JWT_SECRET", "change-me-in-production"),
    jwt_expiry_minutes=int(os.getenv("JWT_EXPIRY_MINUTES", "60")),
    llm_api_key=os.getenv("LLM_API_KEY", ""),
    llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
    llm_model=os.getenv("LLM_MODEL", "gpt-4o"),
    oidc_issuer_url=os.getenv("OIDC_ISSUER_URL", "http://localhost:8080/realms/pipeline-realm"),
    oidc_client_id=os.getenv("OIDC_CLIENT_ID", "pipeline-frontend"),
    oidc_client_secret=os.getenv("OIDC_CLIENT_SECRET", ""),
    oidc_redirect_uri=os.getenv("OIDC_REDIRECT_URI", "http://localhost:8000/api/auth/callback"),
    oauth_client_id=os.getenv("OAUTH_CLIENT_ID", ""),
    oauth_client_secret=os.getenv("OAUTH_CLIENT_SECRET", ""),
    oauth_redirect_uri=os.getenv("OAUTH_REDIRECT_URI", ""),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
    aws_default_region=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    s3_bucket_name=os.getenv("S3_BUCKET_NAME", ""),
    gcs_bucket_name=os.getenv("GCS_BUCKET_NAME", ""),
    gcs_service_account_json=os.getenv("GCS_SERVICE_ACCOUNT_JSON", ""),
    bigquery_project=os.getenv("BIGQUERY_PROJECT", ""),
    bigquery_dataset=os.getenv("BIGQUERY_DATASET", ""),
    postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
    postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
    postgres_db=os.getenv("POSTGRES_DB", "analytics"),
    postgres_user=os.getenv("POSTGRES_USER", "etl"),
    postgres_password=os.getenv("POSTGRES_PASSWORD", ""),
)
