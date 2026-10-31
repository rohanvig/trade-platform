import yfinance as yf

from app.backtester.engine import BacktestEngine
from app.schemas.backtest import (
    BacktestMetricsSchema,
    BacktestRequest,
    BacktestResponse,
    EquityPointSchema,
    TradeSchema,
)
from app.strategies.registry import get_strategy


class BacktestService:
    """
    Coordinates fetching market data, configuring strategy, and running the simulation.
    """

    def run_backtest(self, request: BacktestRequest) -> BacktestResponse:
        sym = request.symbol.strip().upper()
        ticker = yf.Ticker(sym)
        df = ticker.history(period=request.period_range, interval=request.timeframe)

        if df.empty:
            raise ValueError(f"No market data found for symbol '{sym}'")

        strategy = get_strategy(request.strategy_name, **request.params)

        engine = BacktestEngine(
            initial_capital=request.initial_capital,
            commission_pct=request.commission_pct,
            slippage_pct=request.slippage_pct,
        )

        result = engine.run(strategy, df, symbol=sym)

        return BacktestResponse(
            symbol=result.symbol,
            strategy_name=result.strategy_name,
            parameters=result.parameters,
            metrics=BacktestMetricsSchema(
                initial_capital=result.metrics.initial_capital,
                final_equity=result.metrics.final_equity,
                net_profit=result.metrics.net_profit,
                total_return_pct=result.metrics.total_return_pct,
                cagr_pct=result.metrics.cagr_pct,
                max_drawdown_pct=result.metrics.max_drawdown_pct,
                sharpe_ratio=result.metrics.sharpe_ratio,
                sortino_ratio=result.metrics.sortino_ratio,
                win_rate_pct=result.metrics.win_rate_pct,
                profit_factor=result.metrics.profit_factor,
                total_trades=result.metrics.total_trades,
                winning_trades=result.metrics.winning_trades,
                losing_trades=result.metrics.losing_trades,
                average_trade_pnl=result.metrics.average_trade_pnl,
                best_trade_pnl=result.metrics.best_trade_pnl,
                worst_trade_pnl=result.metrics.worst_trade_pnl,
            ),
            equity_curve=[
                EquityPointSchema(
                    timestamp=p.timestamp,
                    equity=p.equity,
                    cash=p.cash,
                    holdings_value=p.holdings_value,
                    drawdown_pct=p.drawdown_pct,
                )
                for p in result.equity_curve
            ],
            trades=[
                TradeSchema(
                    id=t.id,
                    symbol=t.symbol,
                    entry_time=t.entry_time,
                    entry_price=t.entry_price,
                    exit_time=t.exit_time,
                    exit_price=t.exit_price,
                    quantity=t.quantity,
                    pnl=t.pnl,
                    pnl_percent=t.pnl_percent,
                    exit_reason=t.exit_reason.value,
                    commission=t.commission,
                )
                for t in result.trades
            ],
        )
