from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ExitReason(str, Enum):
    SIGNAL = "SIGNAL"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    END_OF_DATA = "END_OF_DATA"


@dataclass
class Trade:
    id: int
    symbol: str
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    quantity: int
    pnl: float
    pnl_percent: float
    exit_reason: ExitReason
    commission: float = 0.0


@dataclass
class EquityPoint:
    timestamp: datetime
    equity: float
    cash: float
    holdings_value: float
    drawdown_pct: float


@dataclass
class BacktestMetrics:
    initial_capital: float
    final_equity: float
    net_profit: float
    total_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    win_rate_pct: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    average_trade_pnl: float
    best_trade_pnl: float
    worst_trade_pnl: float


@dataclass
class BacktestResult:
    symbol: str
    strategy_name: str
    parameters: dict
    metrics: BacktestMetrics
    equity_curve: list[EquityPoint] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
