import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def normalize_zabbix_url(url):
    """
    Permite usar estas dos formas en el .env:

    ZABBIX_URL=http://10.57.1.213/zabbix
    o
    ZABBIX_URL=http://10.57.1.213/zabbix/api_jsonrpc.php
    """
    if not url:
        raise ValueError("La variable ZABBIX_URL no está definida en el archivo .env")

    url = url.rstrip("/")

    if url.endswith("api_jsonrpc.php"):
        return url

    return f"{url}/api_jsonrpc.php"


def get_required_env(name):
    """
    Obtiene una variable obligatoria del .env.
    Si no existe, detiene el programa con un mensaje claro.
    """
    value = os.getenv(name)

    if not value:
        raise ValueError(f"La variable {name} no está definida en el archivo .env")

    return value


def get_env_int(name, default):
    """
    Obtiene una variable numérica del .env.
    Si no existe o no es válida, usa el valor por defecto.
    """
    value = os.getenv(name)

    if not value:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def get_env_bool(name, default=False):
    """
    Convierte variables tipo true/false desde el .env.
    """
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in ["true", "1", "yes", "y"]


@dataclass(frozen=True)
class Settings:
    environment: str
    zabbix_url: str
    zabbix_api_url: str
    zabbix_token: str
    request_timeout_seconds: int
    host_search_limit: int
    group_host_analysis_limit: int
    default_problem_limit: int
    report_output_dir: str
    snapshot_output_dir: str
    report_dry_run: bool


settings = Settings(
    environment=os.getenv("ENVIRONMENT", "lab"),
    zabbix_url=get_required_env("ZABBIX_URL"),
    zabbix_api_url=normalize_zabbix_url(get_required_env("ZABBIX_URL")),
    zabbix_token=get_required_env("ZABBIX_TOKEN"),
    request_timeout_seconds=get_env_int("REQUEST_TIMEOUT_SECONDS", 30),
    host_search_limit=get_env_int("HOST_SEARCH_LIMIT", 50),
    group_host_analysis_limit=get_env_int("GROUP_HOST_ANALYSIS_LIMIT", 50),
    default_problem_limit=get_env_int("DEFAULT_PROBLEM_LIMIT", 100),
    report_output_dir=os.getenv("REPORT_OUTPUT_DIR", "output/reports"),
    snapshot_output_dir=os.getenv("SNAPSHOT_OUTPUT_DIR", "output/snapshots"),
    report_dry_run=get_env_bool("REPORT_DRY_RUN", True)
)