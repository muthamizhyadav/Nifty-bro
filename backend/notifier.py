"""Telegram notifier — sends trade alerts to your phone."""

import logging
import requests

log = logging.getLogger("Notifier")


class Notifier:
    def __init__(self, config):
        self.token = config.get("telegram_bot_token", "")
        self.chat_id = config.get("telegram_chat_id", "")
        self.enabled = bool(self.token and self.chat_id)

    async def send(self, message: str):
        log.info(f"NOTIFY: {message[:80]}")
        if not self.enabled:
            return
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": self.chat_id, "text": message},
                timeout=5
            )
        except Exception as e:
            log.error(f"Telegram error: {e}")
