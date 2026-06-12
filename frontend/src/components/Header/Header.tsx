import { Logo } from './Logo';
import { SearchBar } from './SearchBar';
import { UserMenu } from './UserMenu';
import { RealtimeStatus } from '../RealtimeStatus';

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

export function Header({ onTickerSelect }: HeaderProps) {
  return (
    <header className="fixed top-0 left-0 right-0 z-40 flex flex-col">
      {/* Ticker tape */}
      <div className="bg-slate-950 border-b border-slate-800/60 overflow-hidden h-7 flex items-center">
        <div className="flex gap-8 whitespace-nowrap ticker-scroll px-4">
          {[...TAPE, ...TAPE].map((item, i) => (
            <span key={i} className="inline-flex items-center gap-1.5 text-[11px] font-data">
              <span className="text-slate-300 font-medium">{item.t}</span>
              <span className="text-slate-400">{item.p.toFixed(2)}</span>
              <span className={item.c >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                {item.c >= 0 ? '+' : ''}{item.c.toFixed(2)}%
              </span>
            </span>
          ))}
        </div>
      </div>

      {/* Main header bar */}
      <div className="glass-strong border-b border-slate-800/60 px-4 h-14 flex items-center gap-4">
        <Logo />

        {/* Center search */}
        <div className="flex-1 flex justify-center px-4">
          <SearchBar onSelect={onTickerSelect} />
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-3">
          <RealtimeStatus />
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
