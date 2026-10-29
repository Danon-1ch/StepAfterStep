"""Настройки приложения. Все значения берутся из переменных окружения (файл .env)."""
import os


class Settings:
    # База данных. По умолчанию — файл SQLite (удобно запускать без Docker).
    # В Docker сюда подставляется адрес PostgreSQL.
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./shag.db")

    # YandexGPT (Yandex AI Studio, OpenAI-совместимый API).
    # Если ключа нет — бот работает в демо-режиме без нейросети.
    yandex_api_key: str = os.getenv("YANDEX_API_KEY", "")
    yandex_folder_id: str = os.getenv("YANDEX_FOLDER_ID", "")
    yandex_model: str = os.getenv("YANDEX_MODEL", "yandexgpt-lite/latest")
    yandex_base_url: str = os.getenv("YANDEX_BASE_URL", "https://ai.api.cloud.yandex.net/v1")

    # Папка с фронтендом: если указана, сервер раздаёт сайт сам (для запуска без Docker).
    static_dir: str = os.getenv("STATIC_DIR", "")

    # Ограничения
    max_message_length: int = int(os.getenv("MAX_MESSAGE_LENGTH", "1000"))
    max_messages_per_minute: int = int(os.getenv("MAX_MESSAGES_PER_MINUTE", "10"))
    history_messages_for_llm: int = int(os.getenv("HISTORY_MESSAGES_FOR_LLM", "10"))

    # Телефон доверия, который показывается в кризисной карточке.
    # Укажите проверенный номер для своего региона.
    helpline_phone: str = os.getenv("HELPLINE_PHONE", "")

    # Демо-клиника, которая создаётся при первом запуске
    demo_clinic_key: str = os.getenv("DEMO_CLINIC_KEY", "demo")
    demo_admin_token: str = os.getenv("DEMO_ADMIN_TOKEN", "demo-admin")
    # Телефон демо-клиники — заведомо ненастоящий, только для показа
    demo_clinic_phone: str = os.getenv("DEMO_CLINIC_PHONE", "+7 000 000-00-00")

    @property
    def llm_enabled(self) -> bool:
        return bool(self.yandex_api_key and self.yandex_folder_id)


settings = Settings()
