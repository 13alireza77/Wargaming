from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "db.sqlite3"

DJANGO_SECRET_KEY = "django-insecure--6)*6ro84fslumlt5y96hsxj1$jnukfz#y=sva&czjf)f0dm=a"
DJANGO_DEBUG = False
DJANGO_ALLOWED_HOSTS = ["185.218.139.25", "localhost", "127.0.0.1"]

DJANGO_INSTALLED_APPS = [
    # Unfold admin theme must come before django.contrib.admin.
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_json_widget",
    "orchestrator",
    "rest_framework",
]

DJANGO_MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

DJANGO_TEMPLATE_DIRS = []
DJANGO_LANGUAGE_CODE = "fa"
DJANGO_TIME_ZONE = "UTC"
DJANGO_STATIC_URL = "static/"
DJANGO_DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATA_DIR = PROJECT_ROOT / "data"
GEOGRAPHY_DATA_FILE = DATA_DIR / "geography" / "middle_east_geography.json"
PERSONNEL_DATA_FILE = DATA_DIR / "personnel" / "middle_east_personnel.json"
WEAPONS_DATA_FILE = DATA_DIR / "weapons" / "middle_east_weapons.json"

CHAT_API_URL = "http://localhost:8000/chat/api/chat/"

LLM_PROVIDER_NAME = "ollama"

LLM_PROVIDER_CONFIG = {
    "provider": LLM_PROVIDER_NAME,
    "ollama": {
        "base_url": "http://localhost:11434",
        "default_model": "gemma3:4b",
        "wargaming_model": "wargaming:unified",
        "timeout": 30,
    },
    "citome": {
        "base_url": "http://localhost:8000",
        "default_model": "citome-model",
        "timeout": 60,
        "api_key": None,
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-3.5-turbo",
        "timeout": 30,
        "api_key": None,
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "default_model": "claude-3-sonnet-20240229",
        "timeout": 30,
        "api_key": None,
    },
}

UNIFIED_LLM_GENERATION_CONFIG = {
    "request_timeout_seconds": 300,
    "temperature": 0.4,
    "top_p": 0.9,
    "num_predict": 600,
    "num_ctx": 6144,
    "repeat_penalty": 1.1,
    "conversation_history_limit": 4,
}

UNIFIED_LLM_TRAINING_CONFIG = {
    "custom_model_name": "wargaming:unified",
    "default_base_model": "gemma3:4b",
    "base_url": "http://localhost:11434",
    "ollama_healthcheck_timeout_seconds": 10,
    "ollama_pull_timeout_seconds": 600,
    "ollama_create_timeout_seconds": 600,
    "max_knowledge_chars": 12000,
    "temperature": 0.3,
    "top_p": 0.85,
    "top_k": 40,
    "repeat_penalty": 1.1,
    "num_ctx": 6144,
    "num_predict": 600,
}
