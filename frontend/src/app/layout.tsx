import type { Metadata } from 'next';
import './globals.css';
import { AuthProvider } from '@/context/AuthContext';
import Sidebar from '@/components/Sidebar';

export const metadata: Metadata = {
  title: 'AlgoDesk – AI Trading Platform',
  description:
    'Professional algorithmic trading dashboard with real-time market data, technical indicators, strategy signals, backtesting, and paper trading portfolio management.',
  keywords: ['algorithmic trading', 'backtesting', 'technical indicators', 'paper trading', 'portfolio'],
  openGraph: {
    title: 'AlgoDesk',
    description: 'AI-Powered Algorithmic Trading Platform',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <div className="app-shell">
            <Sidebar />
            <div className="main-content">
              <div className="bg-glow" />
              <main className="page-content" style={{ position: 'relative', zIndex: 1 }}>
                {children}
              </main>
            </div>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
