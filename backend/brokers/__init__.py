"""Broker factory — switch brokers with one config flag."""

import logging
from brokers.fyers_broker import FyersBroker
from brokers.base import BrokerInterface

log = logging.getLogger("BrokerFactory")


def get_broker(config) -> BrokerInterface:
    name = config.get("broker", "fyers").lower()
    if name == "fyers":
        return FyersBroker(config)
    raise ValueError(f"Unknown broker: {name}")
