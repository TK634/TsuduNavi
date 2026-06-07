"""
月謝リマインドバッチジョブ。

実行方法:
  python -m app.jobs.payment_check

crontab 設定例（毎朝 9:00）:
  0 9 * * * cd /path/to/juku-agent && python -m app.jobs.payment_check >> logs/payment.log 2>&1
"""

import asyncio
import logging
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from app.agents.payment_reminder import run_payment_reminders

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    start = datetime.now()
    logger.info("=== 月謝リマインドチェック開始 ===")

    try:
        sent_count = await run_payment_reminders()
        logger.info("月謝リマインド完了: %d件送信", sent_count)
    except Exception:
        logger.exception("月謝リマインドでエラーが発生しました")

    elapsed = (datetime.now() - start).total_seconds()
    logger.info("=== 月謝リマインドチェック完了 (%.1f秒) ===", elapsed)


if __name__ == "__main__":
    asyncio.run(main())
