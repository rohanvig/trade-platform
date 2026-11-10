'use client';

import { Suspense, useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { Search, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';
import { market, QuoteData, CandleData } from '@/lib/api';
import { createChart, IChartApi, CandlestickSeries, HistogramSeries } from 'lightweight-charts';

const PERIODS = ['1mo', '3mo', '6mo', '1y', '2y'];
const POPULAR = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX'];

function MarketPageContent() {
  const searchParams = useSearchParams();
  const [symbol, setSymbol] = useState(searchParams.get('symbol') || 'AAPL');
  const [input, setInput] = useState(searchParams.get('symbol') || 'AAPL');
  const [period, setPeriod] = useState('3mo');
  const [quote, setQuote] = useState<QuoteData | null>(null);
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const chartRef = useRef<HTMLDivElement>(null);
  const chartApi = useRef<IChartApi | null>(null);

  const fetchData = useCallback(async (sym: string, per: string) => {
    setLoading(true);
    setError('');
    try {
      const [q, h] = await Promise.all([
        market.quote(sym),
        market.history(sym, per, '1d'),
      ]);
      setQuote(q);
      setCandles(h.candles);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(symbol, period);
  }, [symbol, period, fetchData]);

  // Build / update chart
  useEffect(() => {
    if (!chartRef.current || candles.length === 0) return;

    if (!chartApi.current) {
      chartApi.current = createChart(chartRef.current, {
        layout: { background: { color: 'transparent' }, textColor: '#7fa8d4' },
        grid: { vertLines: { color: 'rgba(79,156,249,0.06)' }, horzLines: { color: 'rgba(79,156,249,0.06)' } },
        crosshair: { mode: 1 },
        rightPriceScale: { borderColor: 'rgba(79,156,249,0.15)' },
        timeScale: { borderColor: 'rgba(79,156,249,0.15)', timeVisible: true },
        height: 340,
      });
    }

    const chart = chartApi.current;
    chart.applyOptions({ width: chartRef.current.clientWidth });

    chart.removeSeries(chart.getSeries()[0]);
    chart.removeSeries(chart.getSeries()[0]);

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    });

    const volSeries = chart.addSeries(HistogramSeries, {
      color: 'rgba(79,156,249,0.3)',
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

    const parsed = candles.map((c) => ({
      time: c.time.split('T')[0] as `${number}-${number}-${number}`,
      open: c.open, high: c.high, low: c.low, close: c.close,
    }));
    candleSeries.setData(parsed);
    volSeries.setData(candles.map((c) => ({ time: c.time.split('T')[0] as `${number}-${number}-${number}`, value: c.volume, color: c.close >= c.open ? 'rgba(34,197,94,0.35)' : 'rgba(239,68,68,0.35)' })));
    chart.timeScale().fitContent();

    const ro = new ResizeObserver(() => {
      if (chartRef.current && chartApi.current) {
        chartApi.current.applyOptions({ width: chartRef.current.clientWidth });
      }
    });
    ro.observe(chartRef.current);
    return () => ro.disconnect();
  }, [candles]);

  const handleSearch = () => {
    const sym = input.trim().toUpperCase();
    if (sym) setSymbol(sym);
  };

  const up = quote && quote.change_percent >= 0;

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Market Data</h1>
          <p className="page-subtitle">Real-time quotes and OHLCV candlestick history</p>
        </div>
      </div>

      {/* Search */}
      <div className="card" style={{ marginBottom: 20, padding: '16px 20px' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div className="search-box" style={{ flex: 1, minWidth: 200 }}>
            <Search size={15} className="search-icon" />
            <input
              id="symbol-input"
              className="search-input"
              placeholder="Enter ticker symbol (e.g. AAPL)"
              value={input}
              onChange={(e) => setInput(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>
          <button id="search-btn" className="btn btn-primary" onClick={handleSearch}>
            <Search size={15} /> Search
          </button>
          <button id="refresh-btn" className="btn btn-ghost btn-icon" onClick={() => fetchData(symbol, period)} title="Refresh">
            <RefreshCw size={15} />
          </button>
        </div>

        {/* Popular */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 12 }}>
          {POPULAR.map((sym) => (
            <button
              key={sym}
              onClick={() => { setInput(sym); setSymbol(sym); }}
              className={`btn btn-sm ${sym === symbol ? 'btn-primary' : 'btn-ghost'}`}
            >
              {sym}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Quote stat cards */}
      {quote && (
        <div className="stats-grid" style={{ marginBottom: 20 }}>
          {[
            { label: 'Price', value: `$${quote.price.toFixed(2)}` },
            { label: 'Change', value: `${up ? '+' : ''}${quote.change_percent.toFixed(2)}%`, color: up ? 'var(--green-text)' : 'var(--red-text)' },
            { label: 'Day High', value: `$${(quote.day_high ?? quote.price).toFixed(2)}` },
            { label: 'Day Low', value: `$${(quote.day_low ?? quote.price).toFixed(2)}` },
            { label: 'Volume', value: (quote.volume / 1e6).toFixed(1) + 'M' },
            { label: '52w High', value: `$${(quote.fifty_two_week_high ?? quote.price).toFixed(2)}` },
          ].map(({ label, value, color }) => (
            <div key={label} className="stat-card">
              <div className="stat-label">{label}</div>
              <div className="stat-value" style={{ fontSize: '1.2rem', color: color ?? 'var(--text-primary)' }}>{value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Chart */}
      <div className="chart-container" style={{ marginBottom: 20 }}>
        <div className="chart-header">
          <div>
            <span style={{ fontWeight: 800, fontSize: '1.1rem', color: 'var(--text-primary)' }}>{symbol}</span>
            {quote?.name && <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginLeft: 8 }}>{quote.name}</span>}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {quote && (
              <span className={`stat-change ${up ? 'up' : 'down'}`}>
                {up ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                {up ? '+' : ''}{quote.change_percent.toFixed(2)}%
              </span>
            )}
            <div className="chart-tabs">
              {PERIODS.map((p) => (
                <button key={p} className={`chart-tab${period === p ? ' active' : ''}`} onClick={() => setPeriod(p)}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="chart-body">
          {loading ? (
            <div className="loading-state" style={{ height: 340 }}>
              <div className="spinner" />
              <span>Loading chart data…</span>
            </div>
          ) : (
            <div ref={chartRef} style={{ width: '100%', height: 340 }} />
          )}
        </div>
      </div>
    </>
  );
}

export default function MarketPage() {
  return (
    <Suspense fallback={<div className="loading-state"><div className="spinner" /></div>}>
      <MarketPageContent />
    </Suspense>
  );
}
