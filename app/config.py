import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-chat")
    TEMPERATURE: float = 0.0          # 客服场景要稳定
    MAX_HISTORY_TURNS: int = 10       # 最多保留最近10轮对话

    def validate(self):
        if not self.LLM_API_KEY:
            raise ValueError("请在 .env 中配置 LLM_API_KEY")

settings = Settings()
settings.validate()