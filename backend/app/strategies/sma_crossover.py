from datetime import timezone
import pandas as pd

from app.indicators.moving_averages import calculate_sma
from app.strategies.base import BaseStrategy, SignalEvent, SignalType


class SMACrossoverStrategy(BaseStrategy):
    """
    Dual Simple Moving Average (SMA) Crossover Strategy.
    - BUY when Fast SMA crosses above Slow SMA (Golden Cross).
    - SELL when Fast SMA crosses below Slow SMA (Death Cross).
    """

    name = "SMA_CROSSOVER"
    description = "Trades Golden Cross (Fast crosses above Slow) and Death Cross (Fast crosses below Slow)"
    default_params = {
        "fast_period": 10,
        "slow_period": 30,
        "stop_loss_pct": 2.0,     # 2% stop-loss
        "take_profit_pct": 5.0,   # 5% take-profit
    }

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalEvent]:
        fast_period = int(self.params["fast_period"])
        slow_period = int(self.params["slow_period"])
        stop_loss_pct = float(self.params.get("stop_loss_pct", 0))
        take_profit_pct = float(self.params.get("take_profit_pct", 0))

        if fast_period >= slow_period:
            raise ValueError("fast_period must be smaller than slow_period")
        if len(df) < slow_period:
            return []

        fast_sma = calculate_sma(df["Close"], period=fast_period)
        slow_sma = calculate_sma(df["Close"], period=slow_period)

        signals: list[SignalEvent] = []

        # Track previous crossover state (1 = fast > slow, -1 = fast < slow)
        prev_state = None

        for idx, (timestamp, row) in enumerate(df.iterrows()):
            f_val = fast_sma.iloc[idx]
            s_val = slow_sma.iloc[idx]

            if pd.isna(f_val) or pd.isna(s_val):
                continue

            current_state = 1 if f_val > s_val else (-1 if f_val < s_val else 0)

            # Detect crossover
            if prev_state is not None and current_state != prev_state and current_state != 0:
                price = float(row["Close"])
                ts = (
                    timestamp.to_pydatetime().replace(tzinfo=timezone.utc)
                    if timestamp.tzinfo is None
                    else timestamp.to_pydatetime()
                )

                if current_state == 1:
                    # Fast crossed above Slow -> BUY
                    signal_type = SignalType.BUY
                    reason = f"Fast SMA({fast_period}) crossed above Slow SMA({slow_period})"
                else:
                    # Fast crossed below Slow -> SELL
                    signal_type = SignalType.SELL
                    reason = f"Fast SMA({fast_period}) crossed below Slow SMA({slow_period})"

                sl = self.calculate_stop_loss(price, signal_type, stop_loss_pct)
                tp = self.calculate_take_profit(price, signal_type, take_profit_pct)

                signals.append(
                    SignalEvent(
                        timestamp=ts,
                        symbol=symbol.upper(),
                        signal=signal_type,
                        price=round(price, 4),
                        stop_loss=sl,
                        take_profit=tp,
                        reason=reason,
                        metadata={
                            "fast_sma": round(float(f_val), 4),
                            "slow_sma": round(float(s_val), 4),
                        },
                    )
                )

            prev_state = current_state

        return signals
