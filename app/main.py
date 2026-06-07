from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from app.webhook import router as webhook_router  # noqa: E402（dotenv後に読み込む）

app = FastAPI(
    title="TsuduNavi",
    description="TsuduNavi — LINE × Claude × Google Calendarで体験授業の予約を自動化するシステム",
    version="1.0.0",
)

app.include_router(webhook_router, prefix="/line", tags=["LINE"])


@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """ヘルスチェックエンドポイント"""
    return {"status": "ok"}
