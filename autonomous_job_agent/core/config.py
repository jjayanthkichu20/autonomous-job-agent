"""System configuration and operational settings for the Autonomous Multi-Agent Suite."""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR = STORAGE_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class SystemConfig:
    # Autonomous Submission Constraints
    auto_apply_min_relevance: float = float(os.getenv("AUTO_APPLY_MIN_RELEVANCE", "0.75"))
    manual_review_relevance_threshold: float = float(os.getenv("MANUAL_REVIEW_THRESHOLD", "0.65"))
    max_daily_applications_per_candidate: int = 15
    company_cooldown_days: int = 30
    
    # Security & Encryption
    master_encryption_key: Optional[str] = os.getenv("MASTER_ENCRYPTION_KEY", "default-insecure-dev-key-change-in-prod-32b!")
    kms_key_id: Optional[str] = os.getenv("KMS_KEY_ID")
    
    # Crawler and Rate Limiting
    crawler_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    request_delay_seconds: float = 2.5
    rate_limit_jitter_seconds: float = 1.0
    proxy_gateway_url: Optional[str] = os.getenv("PROXY_GATEWAY_URL")
    
    # LLM Inference
    llm_model_frontier: str = os.getenv("LLM_MODEL_FRONTIER", "gemini-1.5-pro")
    llm_model_fast: str = os.getenv("LLM_MODEL_FAST", "gemini-1.5-flash")
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # Paths
    storage_path: Path = STORAGE_DIR
    artifacts_path: Path = ARTIFACTS_DIR
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{STORAGE_DIR / 'agent_suite.db'}")

config = SystemConfig()
