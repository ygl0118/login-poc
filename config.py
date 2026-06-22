"""集中讀取設定，憑證與環境相關參數一律來自環境變數 / .env，程式碼零硬編碼。"""
import os

from dotenv import load_dotenv

# 載入專案根目錄的 .env（若存在）。CI 中可直接以環境變數注入而不需要 .env 檔。
load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _get_int(name: str, default: int) -> int:
    val = os.getenv(name)
    try:
        return int(val) if val is not None else default
    except ValueError:
        return default


# --- 設定值 ---
BASE_URL = os.getenv("BASE_URL", "https://swag.live/?lang=zh-TW")
USERNAME = os.getenv("LOGIN_USERNAME")
PASSWORD = os.getenv("LOGIN_PASSWORD")
WRONG_PASSWORD = os.getenv("WRONG_PASSWORD", "definitely_wrong_password_000")

HEADLESS = _get_bool("HEADLESS", True)
SLOW_MO = _get_int("SLOW_MO", 0)
DEFAULT_TIMEOUT = _get_int("DEFAULT_TIMEOUT", 15000)


def validate() -> None:
    """測試啟動前檢查必要設定，讓設定錯誤『快速失敗』而非以假值掩蓋。"""
    missing = [
        name
        for name, value in (
            ("BASE_URL", BASE_URL),
            ("LOGIN_USERNAME", USERNAME),
            ("LOGIN_PASSWORD", PASSWORD),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "缺少必要環境變數: "
            + ", ".join(missing)
            + "。請參考 .env.example 設定 .env，或在 CI 以環境變數注入。"
        )
