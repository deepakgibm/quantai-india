"""
Bot Alert Service

Sends Telegram notifications for high-conviction signals.
Graceful no-op if TELEGRAM_BOT_TOKEN is not configured.
"""

import logging
import httpx
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


class AlertService:
    """
    Sends signal alerts to Telegram.
    
    Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in config.
    If not configured, all methods are silent no-ops.
    """

    def __init__(self):
        from config import settings
        self.bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        self.chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.bot_token and self.chat_id)

        if not self.enabled:
            logger.info("AlertService: Telegram not configured (no-op mode)")

    async def send_telegram_alert(
        self,
        signals: List[Dict],
        market_trend: Optional[Dict] = None,
        run_id: str = "",
    ) -> bool:
        """
        Send a formatted alert for STRONG conviction signals.

        Args:
            signals: List of signal dicts (from BotSignal.to_dict())
            market_trend: Market trend dict
            run_id: Bot run identifier

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        # Filter to STRONG conviction only
        strong = [s for s in signals if s.get("conviction") == "STRONG"]
        if not strong:
            logger.info("AlertService: No STRONG signals to alert")
            return False

        message = self._format_message(strong, market_trend, run_id)
        return await self._send_message(message)

    def _format_message(
        self,
        signals: List[Dict],
        market_trend: Optional[Dict],
        run_id: str,
    ) -> str:
        """Format signals into a clean Telegram message."""
        buy = [s for s in signals if s["signal_type"] == "BUY"]
        sell = [s for s in signals if s["signal_type"] == "SELL"]

        trend_emoji = "🟢" if market_trend and market_trend.get("trend") == "BULLISH" else "🔴"
        trend_label = market_trend.get("trend", "UNKNOWN") if market_trend else "UNKNOWN"

        lines = [
            f"⚡ *QuantAI Signal Bot*  (Run: `{run_id}`)",
            "",
            f"{trend_emoji} *Market Trend:* {trend_label}",
        ]

        if market_trend:
            nifty_close = market_trend.get("last_close", 0)
            momentum = market_trend.get("momentum", 0)
            m_emoji = "📈" if momentum > 0 else "📉"
            lines.append(f"   NIFTY 50: {nifty_close:,.0f}  {m_emoji} {momentum:+.1f}%")

        lines.append("")

        if buy:
            lines.append(f"🟢 *BUY Signals ({len(buy)}):*")
            for s in buy[:10]:  # cap at 10
                pcr_tag = f" PCR:{s['pcr_value']:.2f}" if s.get("pcr_value") else ""
                lines.append(
                    f"  • *{s['symbol']}*  ₹{s['current_price']:,.1f}  "
                    f"↑{s['price_change_pct']:+.1f}%  "
                    f"Corr:{s['correlation']:.2f}{pcr_tag}"
                )
            lines.append("")

        if sell:
            lines.append(f"🔴 *SELL Signals ({len(sell)}):*")
            for s in sell[:10]:
                pcr_tag = f" PCR:{s['pcr_value']:.2f}" if s.get("pcr_value") else ""
                lines.append(
                    f"  • *{s['symbol']}*  ₹{s['current_price']:,.1f}  "
                    f"↓{s['price_change_pct']:+.1f}%  "
                    f"Corr:{s['correlation']:.2f}{pcr_tag}"
                )
            lines.append("")

        lines.append("_All signals are STRONG conviction._")
        return "\n".join(lines)

    async def _send_message(self, text: str) -> bool:
        """Send a message via Telegram Bot API."""
        url = f"{TELEGRAM_API}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info("AlertService: Telegram alert sent successfully")
                    return True
                else:
                    logger.warning(f"AlertService: Telegram API returned {resp.status_code}: {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"AlertService: Failed to send Telegram alert: {e}")
            return False
