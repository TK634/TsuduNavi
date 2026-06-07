"""
毎日実行するバッチジョブ。

実行方法:
  python -m app.jobs.daily_check

crontab 設定例（毎朝 8:00）:
  0 8 * * * cd /path/to/juku-agent && python -m app.jobs.daily_check >> logs/daily.log 2>&1
"""

import asyncio
import logging
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from app.agents.churn_detector import run_churn_detection
from app.agents.trial_followup import run_trial_followups

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    start = datetime.now()
    logger.info("=== 日次チェック開始 ===")

    # ── 退塾リスク検知 ─────────────────────────────────────────────────────
    logger.info("退塾リスク検知を実行中...")
    try:
        risk_results = await run_churn_detection()
        high_count = sum(1 for r in risk_results if r.level == "high")
        medium_count = sum(1 for r in risk_results if r.level == "medium")
        logger.info(
            "退塾リスク検知完了: 全%d名 / high=%d名 / medium=%d名",
            len(risk_results),
            high_count,
            medium_count,
        )
    except Exception:
        logger.exception("退塾リスク検知でエラーが発生しました")

    # ── 体験フォローアップ ─────────────────────────────────────────────────
    logger.info("体験フォローアップを実行中...")
    try:
        followup_count = await run_trial_followups()
        logger.info("体験フォローアップ完了: %d件送信", followup_count)
    except Exception:
        logger.exception("体験フォローアップでエラーが発生しました")

    elapsed = (datetime.now() - start).total_seconds()
    logger.info("=== 日次チェック完了 (%.1f秒) ===", elapsed)


if __name__ == "__main__":
    asyncio.run(main())
