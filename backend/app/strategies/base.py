from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import pandas as pd


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class SignalEvent:
    timestamp: datetime
    symbol: str
    signal: SignalType
    price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    reason: str = ""
    metadata: dict = field(default_factory=dict)


class BaseStrategy(ABC):
    """
    Abstract Base Class for all quantitative strategies.
    Ensures standard signal generation interface, parameter validation,
    and stop-loss/take-profit calculation.
    """

    name: str = "BaseStrategy"
    description: str = "Base algorithmic trading strategy"
    default_params: dict = {}

    def __init__(self, **params):
        self.params = {**self.default_params, **params}

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalEvent]:
        """
        Takes an OHLCV DataFrame (with columns Open, High, Low, Close, Volume)
        and returns a list of SignalEvent instances.
        """
        pass

    def calculate_stop_loss(
        self,
        entry_price: float,
        side: SignalType,
        stop_loss_pct: float | None,
    ) -> float | None:
        if stop_loss_pct is None or stop_loss_pct <= 0:
            return None

        if side == SignalType.BUY:
            return round(entry_price * (1.0 - (stop_loss_pct / 100.0)), 4)
        elif side == SignalType.SELL:
            return round(entry_price * (1.0 + (stop_loss_pct / 100.0)), 4)
        return None

    def calculate_take_profit(
        self,
        entry_price: float,
        side: SignalType,
        take_profit_pct: float | None,
    ) -> float | None:
        if take_profit_pct is None or take_profit_pct <= 0:
            return None

        if side == SignalType.BUY:
            return round(entry_price * (1.0 + (take_profit_pct / 100.0)), 4)
        elif side == SignalType.SELL:
            return round(entry_price * (1.0 - (take_profit_pct / 100.0)), 4)
        return None
