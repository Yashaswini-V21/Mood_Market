import { Logo } from './Logo';
import { SearchBar } from './SearchBar';
import { UserMenu } from './UserMenu';
import { RealtimeStatus } from '../RealtimeStatus';
import { NotificationBell } from '../Notifications/NotificationCenter';
import { LayoutDashboard, GitCompare, TrendingUp } from 'lucide-react';

interface HeaderProps {
  onTickerSelect: (ticker: string) => void;
}

// Ticker tape data
const TAPE = [
  { t: 'AAPL', p: 192.53, c: 1.23 }, { t: 'TSLA', p: 248.42, c: -2.15 },
  { t: 'NVDA', p: 875.39, c: 3.47 }, { t: 'MSFT', p: 415.20, c: 0.89 },
  { t: 'META', p: 526.68, c: 2.31 }, { t: 'GOOGL', p: 172.90, c: -0.54 },
  { t: 'AMZN', p: 193.77, c: 1.02 }, { t: 'SPY',  p: 531.14, c: 0.37 },
  { t: 'GME',  p: 24.83,  c: 15.2  }, { t: 'MSTR', p: 1540.0, c: 9.3  },
];

const NAV_LINKS = [
  { label: 'Dashboard', hash: 'dashboard', icon: LayoutDashboard },
  { label: 'Compare',   hash: 'compare',   icon: GitCompare      },
  { label: 'Portfolio', hash: 'portfolio', icon: TrendingUp      },
];

export function Header({ onTickerSelect }: HeaderProps) {
  const currentHash = window.location.hash.replace('#', '') || 'landing';

  return (
    <header className="fixed top-0 left-0 right-0 z-40 flex flex-col">
      {/* Ticker tape */}
      <div className="bg-slate-950 border-b border-slate-800/60 overflow-hidden h-7 flex items-center">
        <div className="flex gap-8 whitespace-nowrap ticker-scroll px-4">
          {[...TAPE, ...TAPE].map((item, i) => (
            <button
              key={i}
              onClick={() => onTickerSelect(item.t)}
              className="inline-flex items-center gap-1.5 text-[11px] font-data hover:opacity-80 transition-opacity"
            >
              <span className="text-slate-300 font-medium">{item.t}</span>
              <span className="text-slate-400">{item.p.toFixed(2)}</span>
              <span className={item.c >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                {item.c >= 0 ? '+' : ''}{item.c.toFixed(2)}%
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Main header bar */}
      <div className="glass-strong border-b border-slate-800/60 px-4 h-14 flex items-center gap-4">
        <Logo />

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-0.5 ml-2">
          {NAV_LINKS.map(link => {
            const Icon = link.icon;
            const isActive = currentHash === link.hash;
            return (
              <a
                key={link.hash}
                href={`#${link.hash}`}
                id={`nav-${link.hash}`}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-slate-800 text-white border border-slate-700'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <Icon size={12} />
                {link.label}
              </a>
            );
          })}
        </nav>

        {/* Center search */}
        <div className="flex-1 flex justify-center px-4">
          <SearchBar onSelect={onTickerSelect} />
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-2">
          <RealtimeStatus />
          <NotificationBell />
          <UserMenu />
        </div>
      </div>
    </header>
  );
}

/* clean architecture alignment */
