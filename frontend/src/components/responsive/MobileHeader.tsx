import { Logo } from '../Header/Logo';
import { RealtimeStatus } from '../RealtimeStatus';
import { Menu, Search, X } from 'lucide-react';
import { SearchBar } from '../Header/SearchBar';
import { useState } from 'react';

interface MobileHeaderProps {
  onMenuToggle: () => void;
  onTickerSelect: (ticker: string) => void;
  isOpen: boolean;
}

export function MobileHeader({ onMenuToggle, onTickerSelect, isOpen }: MobileHeaderProps) {
  const [showSearch, setShowSearch] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-40 flex flex-col bg-slate-950/90 backdrop-blur-md border-b border-slate-800/60">
      
      {/* Mini Ticker Tape */}
      <div className="bg-slate-950 border-b border-slate-900 overflow-hidden h-7 flex items-center">
        <div className="flex gap-6 whitespace-nowrap ticker-scroll px-4">
          {[
            { t: 'AAPL', p: 192.53, c: 1.23 }, { t: 'TSLA', p: 248.42, c: -2.15 },
            { t: 'NVDA', p: 875.39, c: 3.47 }, { t: 'MSFT', p: 415.20, c: 0.89 },
          ].map((item, i) => (
            <span key={i} className="inline-flex items-center gap-1.5 text-[10px] font-data">
              <span className="text-slate-400 font-semibold">{item.t}</span>
              <span className={item.c >= 0 ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                {item.c >= 0 ? '+' : ''}{item.c.toFixed(2)}%
              </span>
            </span>
          ))}
        </div>
      </div>

      {/* Main Header Bar */}
      <div className="px-4 h-14 flex items-center justify-between gap-3">
        {/* Left hamburger toggle */}
        <button
          onClick={onMenuToggle}
          className="p-2 -ml-2 text-slate-400 hover:text-white rounded-lg active:bg-slate-800/40"
        >
          {isOpen ? <X size={20} /> : <Menu size={20} />}
        </button>

        {/* Center Logo */}
        {!showSearch && (
          <div className="flex-1 flex justify-start pl-1">
            <Logo />
          </div>
        )}

        {/* Dynamic Search Bar Toggle */}
        {showSearch ? (
          <div className="flex-1 flex items-center gap-2">
            <SearchBar onSelect={(t) => { onTickerSelect(t); setShowSearch(false); }} />
            <button 
              onClick={() => setShowSearch(false)}
              className="text-slate-400 text-xs font-bold uppercase tracking-wider px-2 py-1 rounded"
            >
              Cancel
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2.5">
            <RealtimeStatus />
            <button
              onClick={() => setShowSearch(true)}
              className="p-2 text-slate-400 hover:text-white rounded-lg active:bg-slate-800/40"
            >
              <Search size={18} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
