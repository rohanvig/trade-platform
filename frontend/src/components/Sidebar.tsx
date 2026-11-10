'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  TrendingUp,
  BarChart2,
  LineChart,
  Zap,
  FlaskConical,
  ClipboardList,
  LogOut,
  Activity,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

const navItems = [
  { label: 'Dashboard', href: '/', icon: LayoutDashboard },
  { label: 'Portfolio', href: '/portfolio', icon: TrendingUp },
  { label: 'Market', href: '/market', icon: Activity },
  { label: 'Indicators', href: '/indicators', icon: LineChart },
  { label: 'Strategies', href: '/strategies', icon: Zap },
  { label: 'Backtest', href: '/backtest', icon: FlaskConical },
  { label: 'Orders', href: '/orders', icon: ClipboardList },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const initials = user?.full_name
    ? user.full_name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
    : 'TU';

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-mark">
          <div className="sidebar-logo-icon">
            <BarChart2 size={18} color="white" />
          </div>
          <span className="sidebar-logo-text">AlgoDesk</span>
        </div>
        <div className="sidebar-logo-sub">Trading Platform</div>
      </div>

      {/* Main nav */}
      <div className="sidebar-section-label">Navigation</div>
      <nav className="sidebar-nav">
        {navItems.map(({ label, href, icon: Icon }) => {
          const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`sidebar-link${isActive ? ' active' : ''}`}
            >
              <Icon className="link-icon" size={16} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        {user ? (
          <div className="sidebar-user">
            <div className="sidebar-avatar">{initials}</div>
            <div className="sidebar-user-info">
              <div className="sidebar-user-name">{user.full_name}</div>
              <div className="sidebar-user-role">{user.email}</div>
            </div>
            <button
              onClick={logout}
              className="btn btn-ghost btn-icon"
              title="Logout"
              style={{ marginLeft: 'auto', flexShrink: 0 }}
            >
              <LogOut size={14} />
            </button>
          </div>
        ) : (
          <Link href="/auth" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
            Sign In
          </Link>
        )}
      </div>
    </aside>
  );
}
