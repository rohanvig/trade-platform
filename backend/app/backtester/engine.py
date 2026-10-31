from datetime import timezone
import math
import numpy as np
import pandas as pd

from app.backtester.models import (
    BacktestMetrics,
    BacktestResult,
    EquityPoint,
    ExitReason,
    Trade,
)
from app.strategies.base import BaseStrategy, SignalType


class BacktestEngine:
    """
    Event-driven bar-by-bar backtesting simulation engine.
    Simulates entry/exit orders, commissions, slippage, and intra-bar
    stop-loss and take-profit triggers against historical OHLCV data.
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission_pct: float = 0.1,  # 0.1% per trade
        slippage_pct: float = 0.05,    # 0.05% slippage
    ):
        self.initial_capital = float(initial_capital)
        self.commission_pct = float(commission_pct)
        self.slippage_pct = float(slippage_pct)

    def run(
        self,
        strategy: BaseStrategy,
        df: pd.DataFrame,
        symbol: str,
    ) -> BacktestResult:
        if df.empty:
            raise ValueError(f"Historical DataFrame for '{symbol}' is empty")

        # Normalize index to timezone-aware UTC datetime
        if df.index.tzinfo is None:
            df.index = df.index.tz_localize(timezone.utc)
        else:
            df.index = df.index.tz_convert(timezone.utc)

        # Generate strategy signals
        raw_signals = strategy.generate_signals(df, symbol)
        signals_by_time = {s.timestamp: s for s in raw_signals}

        cash = self.initial_capital
        position = 0  # Number of shares held
        trades: list[Trade] = []
        equity_curve: list[EquityPoint] = []
        peak_equity = self.initial_capital
        trade_counter = 0

        # Active trade state tracker
        active_entry_time = None
        active_entry_price = 0.0
        active_stop_loss = None
        active_take_profit = None
        active_entry_comm = 0.0

        for timestamp, row in df.iterrows():
            ts = timestamp.to_pydatetime()
            close_price = float(row["Close"])
            high_price = float(row["High"])
            low_price = float(row["Low"])
            open_price = float(row["Open"])

            # -------------------------------------------------------------
            # 1. Check intra-bar Stop Loss and Take Profit on active position
            # -------------------------------------------------------------
            if position > 0:
                triggered_exit = False
                exit_price = 0.0
                exit_reason = ExitReason.SIGNAL

                # Stop loss triggered if Low drops to or below stop loss
                if active_stop_loss is not None and low_price <= active_stop_loss:
                    triggered_exit = True
                    # If market gapped down below SL at open, fill at Open, otherwise fill at SL
                    exit_price = min(open_price, active_stop_loss)
                    exit_reason = ExitReason.STOP_LOSS

                # Take profit triggered if High reaches or exceeds take profit
                elif active_take_profit is not None and high_price >= active_take_profit:
                    triggered_exit = True
                    # If market gapped up above TP at open, fill at Open, otherwise fill at TP
                    exit_price = max(open_price, active_take_profit)
                    exit_reason = ExitReason.TAKE_PROFIT

                if triggered_exit:
                    trade_counter += 1
                    exit_comm = (position * exit_price) * (self.commission_pct / 100.0)
                    gross_pnl = (exit_price - active_entry_price) * position
                    total_comm = active_entry_comm + exit_comm
                    net_pnl = gross_pnl - total_comm
                    pnl_pct = (net_pnl / (position * active_entry_price)) * 100.0

                    cash += (position * exit_price) - exit_comm

                    trades.append(
                        Trade(
                            id=trade_counter,
                            symbol=symbol.upper(),
                            entry_time=active_entry_time,
                            entry_price=round(active_entry_price, 4),
                            exit_time=ts,
                            exit_price=round(exit_price, 4),
                            quantity=position,
                            pnl=round(net_pnl, 2),
                            pnl_percent=round(pnl_pct, 2),
                            exit_reason=exit_reason,
                            commission=round(total_comm, 2),
                        )
                    )

                    position = 0
                    active_entry_time = None
                    active_stop_loss = None
                    active_take_profit = None

            # -------------------------------------------------------------
            # 2. Check Strategy Signal at current bar
            # -------------------------------------------------------------
            signal_event = signals_by_time.get(ts)
            if signal_event:
                if signal_event.signal == SignalType.BUY and position == 0:
                    # Apply slippage on entry
                    exec_price = close_price * (1.0 + self.slippage_pct / 100.0)
                    # Allocate up to 98% of cash to leave buffer for commissions
                    affordable_shares = int((cash * 0.98) // exec_price)
                    if affordable_shares > 0:
                        position = affordable_shares
                        comm = (position * exec_price) * (self.commission_pct / 100.0)
                        cash -= (position * exec_price) + comm
                        active_entry_time = ts
                        active_entry_price = exec_price
                        active_entry_comm = comm
                        active_stop_loss = signal_event.stop_loss
                        active_take_profit = signal_event.take_profit

                elif signal_event.signal == SignalType.SELL and position > 0:
                    # Apply slippage on exit
                    trade_counter += 1
                    exec_price = close_price * (1.0 - self.slippage_pct / 100.0)
                    exit_comm = (position * exec_price) * (self.commission_pct / 100.0)
                    gross_pnl = (exec_price - active_entry_price) * position
                    total_comm = active_entry_comm + exit_comm
                    net_pnl = gross_pnl - total_comm
                    pnl_pct = (net_pnl / (position * active_entry_price)) * 100.0

                    cash += (position * exec_price) - exit_comm

                    trades.append(
                        Trade(
                            id=trade_counter,
                            symbol=symbol.upper(),
                            entry_time=active_entry_time,
                            entry_price=round(active_entry_price, 4),
                            exit_time=ts,
                            exit_price=round(exec_price, 4),
                            quantity=position,
                            pnl=round(net_pnl, 2),
                            pnl_percent=round(pnl_pct, 2),
                            exit_reason=ExitReason.SIGNAL,
                            commission=round(total_comm, 2),
                        )
                    )

                    position = 0
                    active_entry_time = None
                    active_stop_loss = None
                    active_take_profit = None

            # -------------------------------------------------------------
            # 3. Record Equity Progression
            # -------------------------------------------------------------
            holdings_val = position * close_price
            current_equity = cash + holdings_val
            peak_equity = max(peak_equity, current_equity)
            drawdown = ((peak_equity - current_equity) / peak_equity) * 100.0 if peak_equity > 0 else 0.0

            equity_curve.append(
                EquityPoint(
                    timestamp=ts,
                    equity=round(current_equity, 2),
                    cash=round(cash, 2),
                    holdings_value=round(holdings_val, 2),
                    drawdown_pct=round(drawdown, 2),
                )
            )

        # Close any open position at the end of the simulation
        if position > 0:
            trade_counter += 1
            last_price = float(df["Close"].iloc[-1])
            exit_comm = (position * last_price) * (self.commission_pct / 100.0)
            gross_pnl = (last_price - active_entry_price) * position
            total_comm = active_entry_comm + exit_comm
            net_pnl = gross_pnl - total_comm
            pnl_pct = (net_pnl / (position * active_entry_price)) * 100.0
            cash += (position * last_price) - exit_comm

            trades.append(
                Trade(
                    id=trade_counter,
                    symbol=symbol.upper(),
                    entry_time=active_entry_time,
                    entry_price=round(active_entry_price, 4),
                    exit_time=df.index[-1].to_pydatetime(),
                    exit_price=round(last_price, 4),
                    quantity=position,
                    pnl=round(net_pnl, 2),
                    pnl_percent=round(pnl_pct, 2),
                    exit_reason=ExitReason.END_OF_DATA,
                    commission=round(total_comm, 2),
                )
            )
            position = 0

        # Calculate performance metrics
        metrics = self._calculate_metrics(df, equity_curve, trades)

        return BacktestResult(
            symbol=symbol.upper(),
            strategy_name=strategy.name,
            parameters=strategy.params,
            metrics=metrics,
            equity_curve=equity_curve,
            trades=trades,
        )

    def _calculate_metrics(
        self,
        df: pd.DataFrame,
        equity_curve: list[EquityPoint],
        trades: list[Trade],
    ) -> BacktestMetrics:
        final_equity = equity_curve[-1].equity if equity_curve else self.initial_capital
        net_profit = final_equity - self.initial_capital
        total_return_pct = (net_profit / self.initial_capital) * 100.0

        # CAGR
        days = (df.index[-1] - df.index[0]).days
        if days >= 30:
            years = days / 365.25
            cagr = ((final_equity / self.initial_capital) ** (1.0 / years) - 1.0) * 100.0
        else:
            cagr = total_return_pct

        # Max Drawdown
        max_dd = max([p.drawdown_pct for p in equity_curve]) if equity_curve else 0.0

        # Win Rate & Profit Factor
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]
        win_rate = (len(winning_trades) / len(trades) * 100.0) if trades else 0.0

        gross_gains = sum(t.pnl for t in winning_trades)
        gross_losses = abs(sum(t.pnl for t in losing_trades))
        if gross_losses > 0:
            profit_factor = round(gross_gains / gross_losses, 2)
        elif gross_gains > 0:
            profit_factor = 999.0
        else:
            profit_factor = 0.0

        avg_trade = (sum(t.pnl for t in trades) / len(trades)) if trades else 0.0
        best_trade = max([t.pnl for t in trades]) if trades else 0.0
        worst_trade = min([t.pnl for t in trades]) if trades else 0.0

        # Sharpe & Sortino ratios based on daily returns
        equities = pd.Series([p.equity for p in equity_curve])
        daily_returns = equities.pct_change().dropna()

        sharpe = 0.0
        sortino = 0.0

        if len(daily_returns) > 1:
            mean_ret = daily_returns.mean()
            std_ret = daily_returns.std()

            if std_ret > 0:
                sharpe = float((mean_ret / std_ret) * math.sqrt(252))

            downside = daily_returns[daily_returns < 0]
            if len(downside) > 0:
                downside_std = downside.std()
                if downside_std > 0:
                    sortino = float((mean_ret / downside_std) * math.sqrt(252))

        return BacktestMetrics(
            initial_capital=round(self.initial_capital, 2),
            final_equity=round(final_equity, 2),
            net_profit=round(net_profit, 2),
            total_return_pct=round(total_return_pct, 2),
            cagr_pct=round(cagr, 2),
            max_drawdown_pct=round(max_dd, 2),
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sortino, 2),
            win_rate_pct=round(win_rate, 2),
            profit_factor=profit_factor,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            average_trade_pnl=round(avg_trade, 2),
            best_trade_pnl=round(best_trade, 2),
            worst_trade_pnl=round(worst_trade, 2),
        )
