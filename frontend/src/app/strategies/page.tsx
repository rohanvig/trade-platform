'use client';

import { useState, useEffect } from 'react';
import { Zap, TrendingUp, TrendingDown, Minus, Search } from 'lucide-react';
import { strategies, StrategyResult, SignalEvent } from '@/lib/api';

const STRATEGY_LIST = [
  { id: 'SMACrossover', label: 'SMA Crossover', desc: 'Golden/death cross of two SMAs' },
  { id: 'RSIMeanReversion', label: 'RSI Mean Reversion', desc: 'Oversold buys, overbought sells on RSI' },
  { id: 'MACDCrossover', label: 'MACD Crossover', desc: 'Signal line crossover with MACD histogram' },
];

function SignalBadge({ type }: { type: string }) {
  if (type === 'BUY') return (
    <span className="badge badge-green" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      <TrendingUp size={11} /> BUY
    </span>
  );
  if (type === 'SELL') return (
    <span className="badge badge-red" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      <TrendingDown size={11} /> SELL
    </span>
  );
  return (
    <span className="badge badge-muted" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      <Minus size={11} /> HOLD
    </span>
  );
}

export default function StrategiesPage() {
  const [symbol, setSymbol] = useState('AAPL');
  const [input, setInput] = useState('AAPL');
  const [strategy, setStrategy] = useState('SMACrossover');
  const [result, setResult] = useState<StrategyResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [filterType, setFilterType] = useState<string>('ALL');

  const run = async () => {
    const sym = input.trim().toUpperCase();
    if (!sym) return;
    setSymbol(sym);
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await strategies.run(sym, strategy);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to run strategy');
    } finally {
      setLoading(false);
    }
  };

  const filteredSignals = result?.signals.filter((s) =>
    filterType === 'ALL' || s.signal_type === filterType
  ) ?? [];

  const latestSignal = result?.signals[result.signals.length - 1];

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Strategy Engine</h1>
          <p className="page-subtitle">Generate BUY/SELL/HOLD signals using algorithmic trading strategies</p>
        </div>
      </div>

      {/* Strategy selector cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginBottom: 20 }}>
        {STRATEGY_LIST.map((s) => (
          <button
            key={s.id}
            id={`strategy-${s.id}`}
            onClick={() => setStrategy(s.id)}
            style={{
              background: strategy === s.id ? 'var(--accent-blue-glow)' : 'var(--bg-card)',
              border: `1px solid ${strategy === s.id ? 'var(--border-active)' : 'var(--border-subtle)'}`,
              borderRadius: 'var(--radius-lg)',
              padding: '16px 18px',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'all 0.2s ease',
            }}
          >
            <div style={{ fontWeight: 700, color: strategy === s.id ? 'var(--accent-blue)' : 'var(--text-primary)', fontSize: '0.9rem', marginBottom: 4 }}>
              {s.label}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{s.desc}</div>
          </button>
        ))}
      </div>

      {/* Controls */}
      <div className="card" style={{ marginBottom: 20, padding: '16px 20px' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ marginBottom: 0, flex: 1, minWidth: 180 }}>
            <label className="form-label">Symbol</label>
            <div className="search-box">
              <Search size={14} className="search-icon" />
              <input
                id="strategy-symbol"
                className="search-input"
                placeholder="AAPL"
                value={input}
                onChange={(e) => setInput(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === 'Enter' && run()}
              />
            </div>
          </div>
          <button id="run-strategy" className="btn btn-primary" onClick={run} disabled={loading}>
            {loading ? <span className="spinner" style={{ width: 15, height: 15 }} /> : <Zap size={15} />}
            Run Strategy
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {result && (
        <>
          {/* Summary stats */}
          <div className="stats-grid" style={{ marginBottom: 20 }}>
            <div className="stat-card">
              <div className="stat-label">Total Signals</div>
              <div className="stat-value">{result.total_signals}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Buy Signals</div>
              <div className="stat-value" style={{ color: 'var(--green-text)' }}>{result.buy_signals}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Sell Signals</div>
              <div className="stat-value" style={{ color: 'var(--red-text)' }}>{result.sell_signals}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Latest Signal</div>
              <div style={{ marginTop: 8 }}>
                {latestSignal ? <SignalBadge type={latestSignal.signal_type} /> : '—'}
              </div>
              {latestSignal && (
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4 }}>
                  @ ${latestSignal.price.toFixed(2)}
                </div>
              )}
            </div>
          </div>

          {/* Signal table */}
          <div className="card">
            <div className="card-header">
              <h2 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Signals · {result.symbol} · {result.strategy}
              </h2>
              <div className="chart-tabs">
                {['ALL', 'BUY', 'SELL'].map((t) => (
                  <button key={t} className={`chart-tab${filterType === t ? ' active' : ''}`} onClick={() => setFilterType(t)}>
                    {t}
                  </button>
                ))}
              </div>
            </div>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Signal</th>
                    <th>Price</th>
                    <th>Stop Loss</th>
                    <th>Take Profit</th>
                    <th>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSignals.slice().reverse().map((sig: SignalEvent, i: number) => (
                    <tr key={i}>
                      <td className="mono muted">{sig.time.split('T')[0]}</td>
                      <td><SignalBadge type={sig.signal_type} /></td>
                      <td className="mono">${sig.price.toFixed(2)}</td>
                      <td className="mono" style={{ color: 'var(--red-text)' }}>{sig.stop_loss ? `$${sig.stop_loss.toFixed(2)}` : '—'}</td>
                      <td className="mono" style={{ color: 'var(--green-text)' }}>{sig.take_profit ? `$${sig.take_profit.toFixed(2)}` : '—'}</td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)', maxWidth: 240 }}>{sig.reason}</td>
                    </tr>
                  ))}
                  {filteredSignals.length === 0 && (
                    <tr>
                      <td colSpan={6} style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>No signals found</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {!result && !loading && !error && (
        <div className="empty-state">
          <div className="empty-icon"><Zap size={22} /></div>
          <div className="empty-title">No Strategy Run Yet</div>
          <div className="empty-sub">Select a strategy, enter a symbol, and click Run Strategy.</div>
        </div>
      )}
    </>
  );
}
