import yfinance as yf

from app.schemas.strategy import (
    SignalResponse,
    StrategyMetadata,
    StrategyRunRequest,
    StrategyRunResponse,
)
from app.strategies.base import SignalType
from app.strategies.registry import get_strategy, list_strategies


class StrategyService:
    """
    Orchestrates algorithmic strategy execution against market price history.
    """

    def get_available_strategies(self) -> list[StrategyMetadata]:
        strategies = list_strategies()
        return [StrategyMetadata(**s) for s in strategies]

    def run_strategy(self, request: StrategyRunRequest) -> StrategyRunResponse:
        sym = request.symbol.strip().upper()
        ticker = yf.Ticker(sym)
        df = ticker.history(period=request.period_range, interval=request.timeframe)

        if df.empty:
            raise ValueError(f"No price history found for symbol '{sym}'")

        strategy = get_strategy(request.strategy_name, **request.params)
        raw_signals = strategy.generate_signals(df, symbol=sym)

        signal_responses = [
            SignalResponse(
                timestamp=s.timestamp,
                symbol=s.symbol,
                signal=s.signal,
                price=s.price,
                stop_loss=s.stop_loss,
                take_profit=s.take_profit,
                reason=s.reason,
                metadata=s.metadata,
            )
            for s in raw_signals
        ]

        buy_count = sum(1 for s in signal_responses if s.signal == SignalType.BUY)
        sell_count = sum(1 for s in signal_responses if s.signal == SignalType.SELL)
        latest = signal_responses[-1] if signal_responses else None

        return StrategyRunResponse(
            symbol=sym,
            strategy_name=strategy.name,
            total_signals=len(signal_responses),
            buy_signals=buy_count,
            sell_signals=sell_count,
            latest_signal=latest,
            signals=signal_responses,
        )
