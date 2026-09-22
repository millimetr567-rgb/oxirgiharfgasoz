"""
Konfiguratsiya moduli.
Tizim sozlamalari, Gemini API parametrlari va o'yin qoidalarini boshqaradi.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Loyihaning asosiy papkasi
BASE_DIR = Path(__file__).resolve().parent

# .env faylini yuklash
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# Gemini API sozlamalari
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Gemini modeli (sukut bo'yicha eng tezkor va barqaror model)
DEFAULT_MODEL = "gemini-2.5-flash"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip()

# O'yin sozlamalari
TURN_TIME_LIMIT = 7  # Har bir navbat uchun 7 soniya
API_TIMEOUT_SECONDS = 10  # AI so'rovi uchun kutish vaqti
API_MAX_RETRIES = 2  # Qayta urinishlar soni

# Ma'lumotlar bazasi yo'llari
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "library_words.db"
JSON_WORDS_PATH = DATA_DIR / "library_words.json"


def is_api_configured() -> bool:
    """API kalit sozlanganligini tekshirish."""
    return bool(GEMINI_API_KEY and len(GEMINI_API_KEY) > 10)


def update_api_key(new_key: str):
    """Yangi API kalitni xotirada va .env faylida yangilash."""
    global GEMINI_API_KEY
    GEMINI_API_KEY = new_key.strip()
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

    # .env fayliga xavfsiz saqlash
    env_content = f"# Google Gemini API kaliti\nGEMINI_API_KEY={GEMINI_API_KEY}\nGEMINI_MODEL={GEMINI_MODEL}\n"
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(env_content)
