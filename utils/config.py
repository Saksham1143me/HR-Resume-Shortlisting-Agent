import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

BASE_DIR = Path(__file__).parent
OUTPUTS_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "outputs")
CACHE_DIR = BASE_DIR / "cache"
LOGS_DIR = BASE_DIR / "logs"
OVERRIDE_LOG_PATH = LOGS_DIR / "overrides.json"

for d in [OUTPUTS_DIR, CACHE_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

LLM_MODEL: str = "gemini-2.5-flash"
LLM_TEMPERATURE: float = 0.0
LLM_MAX_TOKENS: int = 4096
LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", 3))
LLM_TIMEOUT: int = int(os.getenv("LLM_REQUEST_TIMEOUT", 60))


LLM_CACHE_ENABLED: bool = os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true"
LLM_CACHE_DB: str = str(CACHE_DIR / "llm_cache.db")

PII_MASK_SECRET: str = os.getenv("PII_MASK_SECRET", "change-me")

RUBRIC_WEIGHTS = {
    "skills_match":          0.30,
    "experience_relevance":  0.25,
    "education_certs":       0.15,
    "project_portfolio":     0.20,
    "communication_quality": 0.10,
}
assert abs(sum(RUBRIC_WEIGHTS.values()) - 1.0) < 1e-9, "Rubric weights must sum to 1.0"

SHORTLIST_THRESHOLD: float = 6.0
MAX_RESUMES_PER_RUN: int = int(os.getenv("MAX_RESUMES_PER_RUN", 50))

LANGSMITH_ENABLED: bool = bool(os.getenv("LANGCHAIN_API_KEY"))

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
logger.add(
    LOGS_DIR / "agent.log",
    level=LOG_LEVEL,
    rotation="10 MB",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} | {message}",
)

def validate_config() -> None:
    if not GOOGLE_API_KEY:
        raise EnvironmentError(
            "GOOGLE_API_KEY is not set. Copy .env.example → .env and add your key."
        )
    logger.info(f"Config loaded. Model={LLM_MODEL}, Cache={LLM_CACHE_ENABLED}")