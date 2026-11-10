'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  TrendingUp, TrendingDown, Activity, FlaskConical,
  Zap, BarChart2, ArrowRight, DollarSign
} from 'lucide-react';
import { market, QuoteData } from '@/lib/api';

const WATCHLIST = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'];

const features = [
  {
    icon: Activity,
    title: 'Live Market Data',
    desc: 'Real-time quotes, OHLCV history, and symbol search powered by yfinance.',
    href: '/market',
    color: '#4f9cf9',
  },
  {
    icon: BarChart2,
    title: 'Technical Indicators',
    desc: 'SMA, EMA, RSI, MACD, Bollinger Bands, ATR, and VWAP — computed from scratch.',
    href: '/indicators',
    color: '#a855f7',
  },
  {
    icon: Zap,
    title: 'Strategy Signals',
    desc: 'Generate BUY/SELL signals from SMA Crossover, RSI Mean Reversion, or MACD Crossover.',
    href: '/strategies',
    color: '#f59e0b',
  },
  {
    icon: FlaskConical,
    title: 'Backtesting Engine',
    desc: 'Event-driven bar-by-bar simulator with slippage, commissions, Sharpe, and Max Drawdown.',
    href: '/backtest',
    color: '#22c55e',
  },
  {
    icon: TrendingUp,
    title: 'Paper Trading',
    desc: 'Virtual $100k portfolio. Execute market orders, manage positions, and track P&L live.',
    href: '/portfolio',
    color: '#ef4444',
  },
  {
    icon: DollarSign,
    title: 'Order Management',
    desc: 'Full CRUD for orders with filtering, pagination, and instant execution support.',
    href: '/orders',
    color: '#06b6d4',
  },
];

export default function DashboardPage() {
  const [quotes, setQuotes] = useState<Record<string, QuoteData | null>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled(WATCHLIST.map((sym) => market.quote(sym))).then((results) => {
      const map: Record<string, QuoteData | null> = {};
      results.forEach((r, i) => {
        map[WATCHLIST[i]] = r.status === 'fulfilled' ? r.value : null;
      });
      setQuotes(map);
      setLoading(false);
    });
  }, []);

  return (
    <>
      {/* Hero */}
      <div className="page-header" style={{ flexDirection: 'column', alignItems: 'flex-start', marginBottom: 36 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <span className="badge badge-blue">v1.0 · Live</span>
          <span className="badge badge-green">56 Tests Passing</span>
        </div>
        <h1 className="page-title" style={{ fontSize: '2.4rem', lineHeight: 1.1 }}>
          Welcome to AlgoDesk
        </h1>
        <p className="page-subtitle" style={{ fontSize: '0.95rem', maxWidth: 540, marginTop: 6 }}>
          A full-stack algorithmic trading platform — live market data, technical analysis,
          strategy engine, backtesting simulator, and paper trading portfolio.
        </p>
        <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
          <Link href="/backtest" className="btn btn-primary btn-lg">
            <FlaskConical size={18} /> Run Backtest
          </Link>
          <Link href="/market" className="btn btn-secondary btn-lg">
            <Activity size={18} /> Market Data
          </Link>
        </div>
      </div>

      {/* Watchlist */}
      <div style={{ marginBottom: 36 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: '0.78rem' }}>
            📈 Watchlist
          </h2>
          <Link href="/market" className="btn btn-ghost btn-sm">
            View All <ArrowRight size={13} />
          </Link>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
          {WATCHLIST.map((sym) => {
            const q = quotes[sym];
            const up = q && q.change_percent >= 0;
            return (
              <Link key={sym} href={`/market?symbol=${sym}`} style={{ textDecoration: 'none' }}>
                <div className="stat-card" style={{ cursor: 'pointer' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ fontWeight: 800, fontSize: '1rem', color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>{sym}</div>
                      {loading ? (
                        <div style={{ marginTop: 8 }}>
                          <div className="spinner" style={{ width: 16, height: 16 }} />
                        </div>
                      ) : q ? (
                        <>
                          <div className="stat-value" style={{ fontSize: '1.3rem', marginTop: 6 }}>
                            ${q.price.toFixed(2)}
                          </div>
                          <div className={`stat-change ${up ? 'up' : 'down'}`} style={{ marginTop: 6 }}>
                            {up ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                            {up ? '+' : ''}{q.change_percent.toFixed(2)}%
                          </div>
                        </>
                      ) : (
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: 8 }}>Unavailable</div>
                      )}
                    </div>
                    {q && (
                      <div style={{
                        padding: '4px 8px',
                        borderRadius: 4,
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        background: up ? 'var(--green-glow)' : 'var(--red-glow)',
                        color: up ? 'var(--green-text)' : 'var(--red-text)',
                      }}>
                        {up ? '+' : ''}{q.change.toFixed(2)}
                      </div>
                    )}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Features grid */}
      <div>
        <div style={{ marginBottom: 14 }}>
          <h2 style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            🚀 Platform Features
          </h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>
          {features.map(({ icon: Icon, title, desc, href, color }) => (
            <Link key={href} href={href} style={{ textDecoration: 'none' }}>
              <div className="card" style={{ height: '100%', cursor: 'pointer', transition: 'all 0.25s ease' }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLDivElement).style.borderColor = color + '60';
                  (e.currentTarget as HTMLDivElement).style.boxShadow = `0 0 24px ${color}20`;
                  (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-3px)';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLDivElement).style.borderColor = '';
                  (e.currentTarget as HTMLDivElement).style.boxShadow = '';
                  (e.currentTarget as HTMLDivElement).style.transform = '';
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                  <div style={{
                    width: 40, height: 40, borderRadius: 10,
                    background: `${color}20`,
                    border: `1px solid ${color}40`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0,
                  }}>
                    <Icon size={20} color={color} />
                  </div>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)' }}>{title}</h3>
                </div>
                <p style={{ fontSize: '0.83rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>{desc}</p>
                <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 4, color, fontSize: '0.78rem', fontWeight: 600 }}>
                  Explore <ArrowRight size={13} />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </>
  );
}
