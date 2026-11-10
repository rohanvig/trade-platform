const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ─── helpers ────────────────────────────────────────────────────────────────

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth_token');
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface TokenResponse { access_token: string; token_type: string; }
export interface UserOut { id: number; email: string; full_name: string; }

export const auth = {
  register: (email: string, password: string, full_name: string) =>
    request<UserOut>('/api/v1/users/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name }),
    }),
  login: (email: string, password: string) =>
    request<TokenResponse>('/api/v1/users/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<UserOut>('/api/v1/users/me'),
};

// ─── Market Data ─────────────────────────────────────────────────────────────

export interface QuoteData {
  symbol: string;
  price: number;
  previous_close: number;
  change: number;
  change_percent: number;
  volume: number;
  market_cap?: number;
  day_high?: number;
  day_low?: number;
  fifty_two_week_high?: number;
  fifty_two_week_low?: number;
  name?: string;
  timestamp: string;
}

export interface CandleData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface HistoryData {
  symbol: string;
  interval: string;
  candles: CandleData[];
}

export const market = {
  quote: (symbol: string) =>
    request<QuoteData>(`/api/v1/market/quote?symbol=${encodeURIComponent(symbol)}`),
  history: (symbol: string, period = '3mo', interval = '1d') =>
    request<HistoryData>(
      `/api/v1/market/history?symbol=${encodeURIComponent(symbol)}&period=${period}&interval=${interval}`
    ),
  search: (q: string) =>
    request<{ results: Array<{ symbol: string; name: string }> }>(
      `/api/v1/market/search?q=${encodeURIComponent(q)}`
    ),
};

// ─── Indicators ──────────────────────────────────────────────────────────────

export interface IndicatorResult {
  symbol: string;
  indicator: string;
  values: Array<{ time: string; value?: number; [key: string]: unknown }>;
}

export const indicators = {
  sma: (symbol: string, period = 20) =>
    request<IndicatorResult>(`/api/v1/indicators/sma?symbol=${symbol}&period=${period}`),
  ema: (symbol: string, period = 20) =>
    request<IndicatorResult>(`/api/v1/indicators/ema?symbol=${symbol}&period=${period}`),
  rsi: (symbol: string, period = 14) =>
    request<IndicatorResult>(`/api/v1/indicators/rsi?symbol=${symbol}&period=${period}`),
  macd: (symbol: string) =>
    request<IndicatorResult>(`/api/v1/indicators/macd?symbol=${symbol}`),
  bollinger: (symbol: string, period = 20) =>
    request<IndicatorResult>(`/api/v1/indicators/bollinger?symbol=${symbol}&period=${period}`),
  atr: (symbol: string, period = 14) =>
    request<IndicatorResult>(`/api/v1/indicators/atr?symbol=${symbol}&period=${period}`),
  vwap: (symbol: string) =>
    request<IndicatorResult>(`/api/v1/indicators/vwap?symbol=${symbol}`),
};

// ─── Strategies ───────────────────────────────────────────────────────────────

export interface SignalEvent {
  time: string;
  signal_type: 'BUY' | 'SELL' | 'HOLD';
  symbol: string;
  price: number;
  stop_loss?: number;
  take_profit?: number;
  strategy: string;
  reason: string;
}

export interface StrategyResult {
  symbol: string;
  strategy: string;
  signals: SignalEvent[];
  total_signals: number;
  buy_signals: number;
  sell_signals: number;
}

export const strategies = {
  run: (symbol: string, strategy: string, params?: Record<string, unknown>) =>
    request<StrategyResult>('/api/v1/strategies/run', {
      method: 'POST',
      body: JSON.stringify({ symbol, strategy_name: strategy, params: params ?? {} }),
    }),
  list: () =>
    request<{ strategies: Array<{ name: string; description: string; params: Record<string, unknown> }> }>(
      '/api/v1/strategies/'
    ),
};

// ─── Backtesting ─────────────────────────────────────────────────────────────

export interface BacktestResult {
  symbol: string;
  strategy: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_equity: number;
  total_return_pct: number;
  cagr_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown_pct: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  equity_curve: Array<{ time: string; equity: number }>;
  trades: Array<{
    entry_time: string;
    exit_time?: string;
    direction: string;
    entry_price: number;
    exit_price?: number;
    quantity: number;
    pnl?: number;
    pnl_pct?: number;
  }>;
}

export const backtesting = {
  run: (payload: {
    symbol: string;
    strategy_name: string;
    start_date: string;
    end_date: string;
    initial_capital?: number;
    commission_pct?: number;
    slippage_pct?: number;
    params?: Record<string, unknown>;
  }) =>
    request<BacktestResult>('/api/v1/backtest/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};

// ─── Orders ───────────────────────────────────────────────────────────────────

export interface Order {
  id: number;
  symbol: string;
  side: 'BUY' | 'SELL';
  order_type: 'MARKET' | 'LIMIT' | 'STOP';
  quantity: number;
  price?: number;
  status: string;
  created_at: string;
  executed_at?: string;
}

export const orders = {
  list: (params?: { symbol?: string; side?: string; status?: string }) => {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return request<Order[]>(`/api/v1/orders${qs ? '?' + qs : ''}`);
  },
  create: (payload: Partial<Order>, execute = false) =>
    request<Order>(`/api/v1/orders?execute=${execute}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  execute: (id: number) =>
    request<Order>(`/api/v1/orders/${id}/execute`, { method: 'POST' }),
  cancel: (id: number) =>
    request<Order>(`/api/v1/orders/${id}/cancel`, { method: 'DELETE' }),
};

// ─── Portfolio ────────────────────────────────────────────────────────────────

export interface Portfolio {
  id: number;
  user_id: number;
  cash_balance: number;
  total_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  positions: Position[];
}

export interface Position {
  id: number;
  symbol: string;
  quantity: number;
  avg_entry_price: number;
  current_price?: number;
  market_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
}

export const portfolio = {
  get: () => request<Portfolio>('/api/v1/portfolio/'),
  reset: () => request<Portfolio>('/api/v1/portfolio/reset', { method: 'POST' }),
};
