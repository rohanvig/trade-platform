'use client';

import { useState } from 'react';
import { BarChart2, Search } from 'lucide-react';
import { indicators, IndicatorResult } from '@/lib/api';

type IndicatorType = 'sma' | 'ema' | 'rsi' | 'macd' | 'bollinger' | 'atr' | 'vwap';

const INDICATOR_CONFIGS: Record<IndicatorType, { label: string; color: string; hasValues: boolean }> = {
  sma:      { label: 'Simple Moving Average (SMA)', color: '#4f9cf9', hasValues: true },
  ema:      { label: 'Exponential Moving Average (EMA)', color: '#a855f7', hasValues: true },
  rsi:      { label: 'RSI (Relative Strength Index)', color: '#f59e0b', hasValues: true },
  macd:     { label: 'MACD', color: '#22c55e', hasValues: false },
  bollinger: { label: 'Bollinger Bands', color: '#06b6d4', hasValues: false },
  atr:      { label: 'Average True Range (ATR)', color: '#ef4444', hasValues: true },
  vwap:     { label: 'VWAP', color: '#f97316', hasValues: true },
};

function ValueTable({ data, indicator }: { data: IndicatorResult; indicator: IndicatorType }) {
  const rows = data.values.slice(-30).reverse();
  const keys = rows[0] ? Object.keys(rows[0]).filter((k) => k !== 'time') : [];

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Date</th>
            {keys.map((k) => <th key={k}>{k.toUpperCase()}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              <td className="mono muted">{String(row.time).split('T')[0]}</td>
              {keys.map((k) => (
                <td key={k} className="mono">
                  {typeof row[k] === 'number' ? (row[k] as number).toFixed(4) : String(row[k] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function IndicatorsPage() {
  const [symbol, setSymbol] = useState('AAPL');
  const [input, setInput] = useState('AAPL');
  const [selectedIndicator, setSelectedIndicator] = useState<IndicatorType>('sma');
  const [period, setPeriod] = useState(20);
  const [result, setResult] = useState<IndicatorResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const run = async () => {
    const sym = input.trim().toUpperCase();
    if (!sym) return;
    setSymbol(sym);
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const fn = indicators[selectedIndicator as keyof typeof indicators] as (sym: string, period?: number) => Promise<IndicatorResult>;
      const res = await fn(sym, period);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to compute indicator');
    } finally {
      setLoading(false);
    }
  };

  const config = INDICATOR_CONFIGS[selectedIndicator];

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Technical Indicators</h1>
          <p className="page-subtitle">Compute SMA, EMA, RSI, MACD, Bollinger Bands, ATR, and VWAP from scratch</p>
        </div>
      </div>

      {/* Controls */}
      <div className="card" style={{ marginBottom: 20, padding: '20px 24px' }}>
        <div className="form-row" style={{ alignItems: 'flex-end', gap: 16 }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Symbol</label>
            <div className="search-box">
              <Search size={14} className="search-icon" />
              <input
                id="indicator-symbol"
                className="search-input"
                placeholder="AAPL"
                value={input}
                onChange={(e) => setInput(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === 'Enter' && run()}
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Indicator</label>
            <select
              id="indicator-type"
              className="form-select"
              value={selectedIndicator}
              onChange={(e) => setSelectedIndicator(e.target.value as IndicatorType)}
            >
              {(Object.keys(INDICATOR_CONFIGS) as IndicatorType[]).map((k) => (
                <option key={k} value={k}>{k.toUpperCase()} — {INDICATOR_CONFIGS[k].label.split(' (')[0]}</option>
              ))}
            </select>
          </div>

          {['sma', 'ema', 'rsi', 'bollinger', 'atr'].includes(selectedIndicator) && (
            <div className="form-group" style={{ marginBottom: 0, minWidth: 100 }}>
              <label className="form-label">Period</label>
              <input
                id="indicator-period"
                className="form-input"
                type="number"
                min={2}
                max={200}
                value={period}
                onChange={(e) => setPeriod(Number(e.target.value))}
              />
            </div>
          )}

          <button id="run-indicator" className="btn btn-primary" onClick={run} disabled={loading}>
            {loading ? <span className="spinner" style={{ width: 15, height: 15 }} /> : <BarChart2 size={15} />}
            Compute
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {result && (
        <div className="card">
          <div className="card-header">
            <div>
              <h2 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                <span style={{ color: config.color }}>{selectedIndicator.toUpperCase()}</span> · {symbol}
              </h2>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 2 }}>
                {result.values.length} data points computed · Showing last 30
              </p>
            </div>
            <span className="badge" style={{ background: `${config.color}20`, color: config.color, border: `1px solid ${config.color}40` }}>
              {config.label.split(' (')[0]}
            </span>
          </div>
          <ValueTable data={result} indicator={selectedIndicator} />
        </div>
      )}

      {!result && !loading && !error && (
        <div className="empty-state">
          <div className="empty-icon"><BarChart2 size={22} /></div>
          <div className="empty-title">No Data Yet</div>
          <div className="empty-sub">Select a symbol and indicator, then click Compute.</div>
        </div>
      )}
    </>
  );
}
