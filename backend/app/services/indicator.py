from datetime import timezone
import math
import pandas as pd
import yfinance as yf

from app.indicators import (
    calculate_atr,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    calculate_vwap,
)
from app.schemas.indicator import (
    BollingerBandsResponse,
    BollingerBandsValuePoint,
    IndicatorValuePoint,
    MACDResponse,
    MACDValuePoint,
    SingleIndicatorResponse,
)


def _clean_val(val: float | None) -> float | None:
    if val is None or math.isnan(val) or math.isinf(val):
        return None
    return round(float(val), 4)


class IndicatorService:
    """
    Orchestrates historical price data retrieval and applies technical indicators
    formatted for charting time-series.
    """

    def _get_history_df(
        self,
        symbol: str,
        timeframe: str = "1d",
        period_range: str = "6mo",
    ) -> pd.DataFrame:
        sym = symbol.strip().upper()
        ticker = yf.Ticker(sym)
        df = ticker.history(period=period_range, interval=timeframe)
        if df.empty:
            raise ValueError(f"No market data available for '{sym}'")
        return df

    def get_sma(
        self,
        symbol: str,
        period: int = 20,
        timeframe: str = "1d",
        period_range: str = "6mo",
    ) -> SingleIndicatorResponse:
        df = self._get_history_df(symbol, timeframe, period_range)
        sma = calculate_sma(df["Close"], period=period)

        points = [
            IndicatorValuePoint(
                timestamp=idx.to_pydatetime().replace(tzinfo=timezone.utc)
                if idx.tzinfo is None
                else idx.to_pydatetime(),
                value=_clean_val(val),
            )
            for idx, val in sma.items()
        ]

        return SingleIndicatorResponse(
            symbol=symbol.upper(),
            indicator="SMA",
            params={"period": period, "timeframe": timeframe},
            points=points,
        )

    def get_ema(
        self,
        symbol: str,
        period: int = 20,
        timeframe: str = "1d",
        period_range: str = "6mo",
    ) -> SingleIndicatorResponse:
        df = self._get_history_df(symbol, timeframe, period_range)
        ema = calculate_ema(df["Close"], period=period)

        points = [
            IndicatorValuePoint(
                timestamp=idx.to_pydatetime().replace(tzinfo=timezone.utc)
                if idx.tzinfo is None
                else idx.to_pydatetime(),
                value=_clean_val(val),
            )
            for idx, val in ema.items()
        ]

        return SingleIndicatorResponse(
            symbol=symbol.upper(),
            indicator="EMA",
            params={"period": period, "timeframe": timeframe},
            points=points,
        )

    def get_rsi(
        self,
        symbol: str,
        period: int = 14,
        timeframe: str = "1d",
        period_range: str = "6mo",
    ) -> SingleIndicatorResponse:
        df = self._get_history_df(symbol, timeframe, period_range)
        rsi = calculate_rsi(df["Close"], period=period)

        points = [
            IndicatorValuePoint(
                timestamp=idx.to_pydatetime().replace(tzinfo=timezone.utc)
                if idx.tzinfo is None
                else idx.to_pydatetime(),
                value=_clean_val(val),
            )
            for idx, val in rsi.items()
        ]

        return SingleIndicatorResponse(
            symbol=symbol.upper(),
            indicator="RSI",
            params={"period": period, "timeframe": timeframe},
            points=points,
        )

    def get_macd(
        self,
        symbol: str,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        timeframe: str = "1d",
        period_range: str = "6mo",
    ) -> MACDResponse:
        df = self._get_history_df(symbol, timeframe, period_range)
        macd_df = calculate_macd(
            df["Close"],
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period,
        )

        points = [
            MACDValuePoint(
                timestamp=idx.to_pydatetime().replace(tzinfo=timezone.utc)
                if idx.tzinfo is None
                else idx.to_pydatetime(),
                macd=_clean_val(row["macd"]),
                signal=_clean_val(row["signal"]),
                histogram=_clean_val(row["histogram"]),
            )
            for idx, row in macd_df.iterrows()
        ]

        return MACDResponse(
            symbol=symbol.upper(),
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period,
            points=points,
        )

    def get_bollinger_bands(
        self,
        symbol: str,
        period: int = 20,
        std_multiplier: float = 2.0,
        timeframe: str = "1d",
        period_range: str = "6mo",
    ) -> BollingerBandsResponse:
        df = self._get_history_df(symbol, timeframe, period_range)
        bb_df = calculate_bollinger_bands(
            df["Close"],
            period=period,
            std_multiplier=std_multiplier,
        )

        points = [
            BollingerBandsValuePoint(
                timestamp=idx.to_pydatetime().replace(tzinfo=timezone.utc)
                if idx.tzinfo is None
                else idx.to_pydatetime(),
                upper=_clean_val(row["upper"]),
                middle=_clean_val(row["middle"]),
                lower=_clean_val(row["lower"]),
            )
            for idx, row in bb_df.iterrows()
        ]

        return BollingerBandsResponse(
            symbol=symbol.upper(),
            period=period,
            std_multiplier=std_multiplier,
            points=points,
        )

    def get_atr(
        self,
        symbol: str,
        period: int = 14,
        timeframe: str = "1d",
        period_range: str = "6mo",
    ) -> SingleIndicatorResponse:
        df = self._get_history_df(symbol, timeframe, period_range)
        atr = calculate_atr(df["High"], df["Low"], df["Close"], period=period)

        points = [
            IndicatorValuePoint(
                timestamp=idx.to_pydatetime().replace(tzinfo=timezone.utc)
                if idx.tzinfo is None
                else idx.to_pydatetime(),
                value=_clean_val(val),
            )
            for idx, val in atr.items()
        ]

        return SingleIndicatorResponse(
            symbol=symbol.upper(),
            indicator="ATR",
            params={"period": period, "timeframe": timeframe},
            points=points,
        )

    def get_vwap(
        self,
        symbol: str,
        timeframe: str = "1d",
        period_range: str = "1mo",
    ) -> SingleIndicatorResponse:
        df = self._get_history_df(symbol, timeframe, period_range)
        vwap = calculate_vwap(df["High"], df["Low"], df["Close"], df["Volume"])

        points = [
            IndicatorValuePoint(
                timestamp=idx.to_pydatetime().replace(tzinfo=timezone.utc)
                if idx.tzinfo is None
                else idx.to_pydatetime(),
                value=_clean_val(val),
            )
            for idx, val in vwap.items()
        ]

        return SingleIndicatorResponse(
            symbol=symbol.upper(),
            indicator="VWAP",
            params={"timeframe": timeframe, "period_range": period_range},
            points=points,
        )
