# Research & Technical Discovery — Crypto Options Architecture

## 1. Domain Discovery: Crypto Options (Deribit vs. Standard Financials)

### 1.1 Exchange Standards & Market Dominance
- **Deribit** accounts for >85% of crypto options open interest and volume globally across BTC and ETH.
- **Contract Specifications**:
  - **Asset Classes**: BTC and ETH.
  - **Option Type**: European-style cash-settled options (exercise occurs exclusively at expiration).
  - **Settlement Currency**:
    - Deribit standard options are "inverse" / coin-margined (settled in BTC for BTC options, ETH for ETH options).
    - Deribit USDC options are linear (settled in USDC).
    - For initial V1 personal workstation simplicity and consistent USD-denominated risk modeling, portfolio balances and position sizing calculations will be normalized to USD value while tracking underlying coin contract units (e.g. 1.0 contract = 1 BTC or 1 ETH).
  - **Deribit Public API**:
    - Free public REST and WebSocket endpoints require **no API keys** for market data, instrument metadata, active orderbooks, historical index data, and live options chains.
    - Rate limits: 20 requests/second for unauthenticated public endpoints.

### 1.2 Quantitative Modeling: Black-76 vs. Black-Scholes
- Standard equity options use Black-Scholes-Merton on spot price with continuous dividend yield.
- Commodity and crypto options on Deribit trade relative to the **underlying synthetic forward price** ($F$), not the pure spot index ($S$), because of crypto basis/futures premiums:
  $$F = S \cdot e^{(r - q)T}$$
- The correct pricing and Greeks model for European crypto options is **Black-76**:
  - $d_1 = \frac{\ln(F / K) + \frac{1}{2}\sigma^2 T}{\sigma \sqrt{T}}$
  - $d_2 = d_1 - \sigma \sqrt{T}$
  - Call Price $C = e^{-rT} [F \cdot N(d_1) - K \cdot N(d_2)]$
  - Put Price $P = e^{-rT} [K \cdot N(-d_2) - F \cdot N(-d_1)]$
- **Implied Volatility (IV) Extraction**:
  - When IV is not directly quoted, solve using Newton-Raphson with Vega as derivative:
    $$\sigma_{n+1} = \sigma_n - \frac{C_{\text{model}}(\sigma_n) - C_{\text{market}}}{\nu(\sigma_n)}$$
    Fallback to Brent's method if Newton-Raphson step exits boundary $[0.001, 5.000]$ (crypto IV can exceed 200%).

### 1.3 Precision & Financial Correctness
- Floating point binary representations (`float`) introduce rounding errors in strike prices and premium sums.
- **Mandate**: Python `Decimal` with explicit rounding contexts (`ROUND_HALF_EVEN`) for all monetary values, strikes, lots, and fee calculations.
- Quantities: BTC (satoshi-level precision, 8 decimals), ETH (gwei/ether precision, 8 decimals), USD (cents or 4 decimal places for options ticks).

---

## 2. Existing Codebase Analysis & Reusability Assessment

| Subsystem | Existing State | Compatibility with Crypto Options | Adaptation Strategy |
| :--- | :--- | :--- | :--- |
| **Auth & Security** | JWT + Argon2, User model, Session handling | 100% Compatible | Keep as-is. Users own portfolios and orders. |
| **Market Data** | `yfinance` equity quotes and history | Incompatible for Crypto Options | Introduce an abstraction `MarketDataProvider` with a dedicated `DeribitMarketDataProvider` (for live BTC/ETH spot, forwards, and option chains) alongside historical candle fetchers. |
| **Technical Indicators** | SMA, EMA, RSI, MACD, ATR, Bollinger, VWAP written from scratch | 100% Compatible | Preserve indicator math. Extend with multi-timeframe candle inputs (1D, 4H, 1H). |
| **Order Model** | Equities oriented (symbol, side: BUY/SELL, type: MARKET/LIMIT/STOP) | 60% Compatible | Must support contract instrument types (`SPOT`, `PERP`, `OPTION`), expiry date, strike price, option type (`CALL`, `PUT`), contract multiplier, and multi-leg order groupings for debit spreads. |
| **Portfolio Model** | $100k cash + equity positions | 75% Compatible | Update `Position` to store instrument specifications, Greeks exposure (portfolio net Delta, Vega, Theta), and cash balances in USD. |
| **Risk Engine** | Minimal (cash check only) | Inadequate for Trading Safety | Implement a dedicated `RiskEngine` enforcing strict 1% account risk, maximum portfolio margin, options spread validation, and an emergency Kill Switch. |

