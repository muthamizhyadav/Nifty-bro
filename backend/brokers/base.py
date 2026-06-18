"""
BROKER ABSTRACTION
==================
Every broker (Fyers, Upstox, future Zerodha) implements this contract.
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict, Any


class BrokerInterface(ABC):
    @abstractmethod
    async def connect(self, on_tick: Callable[[Dict[str, Any]], None]) -> None: pass

    @abstractmethod
    async def disconnect(self) -> None: pass

    @abstractmethod
    async def subscribe(self, instrument: str) -> None: pass

    @abstractmethod
    def get_quote(self, instrument: str) -> Dict[str, Any]: pass

    @abstractmethod
    def get_historical_candles(self, instrument: str, timeframe: str,
                                from_date: str, to_date: str) -> list: pass

    @abstractmethod
    def get_option_chain(self, underlying: str, expiry: Optional[str] = None) -> Optional[list]: pass

    @abstractmethod
    def get_vix(self) -> Optional[float]: pass

    @abstractmethod
    def place_order(self, instrument: str, direction: str, quantity: int,
                     order_type: str = "LIMIT", price: float = 0,
                     product: str = "INTRADAY") -> Optional[str]: pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool: pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> str: pass

    @abstractmethod
    def get_positions(self) -> list: pass

    @abstractmethod
    def get_funds(self) -> Dict[str, float]: pass

    @abstractmethod
    def format_instrument(self, symbol: str, expiry: Optional[str] = None) -> str: pass
