from datetime import timezone
import pandas as pd

from app.indicators.momentum import calculate_rsi
from app.strategies.base import BaseStrategy, SignalEvent, SignalType


class RSIMeanReversionStrategy(BaseStrategy):
    """
    RSI Mean-Reversion Strategy.
    - BUY when RSI dips into oversold territory (RSI < oversold_threshold).
    - SELL when RSI surges into overbought territory (RSI > overbought_threshold).
    """

    name = "RSI_MEAN_REVERSION"
    description = "Trades oversold pullbacks (BUY) and overbought reversals (SELL) using Relative Strength Index"
    default_params = {
        "period": 14,
        "oversold_threshold": 30.0,
        "overbought_threshold": 70.0,
        "stop_loss_pct": 2.5,
        "take_profit_pct": 5.0,
    }

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalEvent]:
        period = int(self.params["period"])
        oversold = float(self.params["oversold_threshold"])
        overbought = float(self.params["overbought_threshold"])
        stop_loss_pct = float(self.params.get("stop_loss_pct", 0))
        take_profit_pct = float(self.params.get("take_profit_pct", 0))

        if len(df) <= period:
            return []

        rsi_series = calculate_rsi(df["Close"], period=period)
        signals: list[SignalEvent] = []

        in_oversold = False
        in_overbought = False

        for idx, (timestamp, row) in enumerate(df.iterrows()):
            val = rsi_series.iloc[idx]
            if pd.isna(val):
                continue

            price = float(row["Close"])
            ts = (
                timestamp.to_pydatetime().replace(tzinfo=timezone.utc)
                if timestamp.tzinfo is None
                else timestamp.to_pydatetime()
            )

            # Check Oversold entry (BUY)
            if val <= oversold and not in_oversold:
                in_oversold = True
                in_overbought = False
                sl = self.calculate_stop_loss(price, SignalType.BUY, stop_loss_pct)
                tp = self.calculate_take_profit(price, SignalType.BUY, take_profit_pct)
                signals.append(
                    SignalEvent(
                        timestamp=ts,
                        symbol=symbol.upper(),
                        signal=SignalType.BUY,
                        price=round(price, 4),
                        stop_loss=sl,
                        take_profit=tp,
                        reason=f"RSI({period}) touched oversold at {round(val, 2)} <= {oversold}",
                        metadata={"rsi": round(float(val), 2)},
                    )
                )
            elif val > oversold:
                in_oversold = False

            # Check Overbought entry (SELL)
            if val >= overbought and not in_overbought:
                in_overbought = True
                in_oversold = False
                sl = self.calculate_stop_loss(price, SignalType.SELL, stop_loss_pct)
                tp = self.calculate_take_profit(price, SignalType.SELL, take_profit_pct)
                signals.append(
                    SignalEvent(
                        timestamp=ts,
                        symbol=symbol.upper(),
                        signal=SignalType.SELL,
                        price=round(price, 4),
                        stop_loss=sl,
                        take_profit=tp,
                        reason=f"RSI({period}) touched overbought at {round(val, 2)} >= {overbought}",
                        metadata={"rsi": round(float(val), 2)},
                    )
                )
            elif val < overbought:
                in_overbought = False

        return signals
