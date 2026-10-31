from datetime import timezone
import pandas as pd

from app.indicators.momentum import calculate_macd
from app.strategies.base import BaseStrategy, SignalEvent, SignalType


class MACDCrossoverStrategy(BaseStrategy):
    """
    MACD Line & Signal Line Crossover Strategy.
    - BUY when MACD line crosses above Signal line (Bullish momentum).
    - SELL when MACD line crosses below Signal line (Bearish momentum).
    """

    name = "MACD_CROSSOVER"
    description = "Trades momentum shifts when the MACD line crosses its 9-period Signal line"
    default_params = {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
        "stop_loss_pct": 2.0,
        "take_profit_pct": 4.0,
    }

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalEvent]:
        fast = int(self.params["fast_period"])
        slow = int(self.params["slow_period"])
        sig = int(self.params["signal_period"])
        stop_loss_pct = float(self.params.get("stop_loss_pct", 0))
        take_profit_pct = float(self.params.get("take_profit_pct", 0))

        if len(df) < slow + sig:
            return []

        macd_df = calculate_macd(df["Close"], fast_period=fast, slow_period=slow, signal_period=sig)
        signals: list[SignalEvent] = []

        prev_state = None

        for idx, (timestamp, row) in enumerate(df.iterrows()):
            m_val = macd_df["macd"].iloc[idx]
            s_val = macd_df["signal"].iloc[idx]

            if pd.isna(m_val) or pd.isna(s_val):
                continue

            current_state = 1 if m_val > s_val else (-1 if m_val < s_val else 0)

            if prev_state is not None and current_state != prev_state and current_state != 0:
                price = float(row["Close"])
                ts = (
                    timestamp.to_pydatetime().replace(tzinfo=timezone.utc)
                    if timestamp.tzinfo is None
                    else timestamp.to_pydatetime()
                )

                if current_state == 1:
                    signal_type = SignalType.BUY
                    reason = f"MACD line ({round(m_val, 3)}) crossed above Signal line ({round(s_val, 3)})"
                else:
                    signal_type = SignalType.SELL
                    reason = f"MACD line ({round(m_val, 3)}) crossed below Signal line ({round(s_val, 3)})"

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
                            "macd": round(float(m_val), 4),
                            "signal": round(float(s_val), 4),
                        },
                    )
                )

            prev_state = current_state

        return signals
