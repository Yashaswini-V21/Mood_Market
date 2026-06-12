import { useState } from 'react';
import { TrendingUp, TrendingDown, Plus, Star, ArrowUpDown, X } from 'lucide-react';
import { clsx } from 'clsx';
import { Button } from '../base/Button';

interface WatchItem {
  ticker: string;
  price: number;
  change: number;
  sentiment: 'bullish' | 'bearish' | 'neutral';
}

const DEFAULT_WATCHLIST: WatchItem[] = [
  { ticker: 'AAPL',  price: 192.53, change:  1.23, sentiment: 'bullish'  },
  { ticker: 'MSFT',  price: 415.20, change:  0.89, sentiment: 'bullish'  },
  { ticker: 'TSLA',  price: 248.42, change: -2.15, sentiment: 'bearish'  },
  { ticker: 'GOOGL', price: 172.90, change: -0.54, sentiment: 'neutral'  },
  { ticker: 'NVDA',  price: 875.39, change:  3.47, sentiment: 'bullish'  },
  { ticker: 'META',  price: 526.68, change:  2.31, sentiment: 'bullish'  },
  { ticker: 'GME',   price:  24.83, change: 15.20, sentiment: 'bullish'  },
  { ticker: 'AMZN',  price: 193.77, change:  1.02, sentiment: 'neutral'  },
];

const sentimentDot: Record<string, string> = {
  bullish: 'bg-emerald-400',
  bearish: 'bg-rose-400',
  neutral: 'bg-slate-500',
};

interface LeftSidebarProps {
  selected: string;
  onSelect: (ticker: string) => void;
}

export function LeftSidebar({ selected, onSelect }: LeftSidebarProps) {
  const [watchlist, setWatchlist] = useState(DEFAULT_WATCHLIST);
  const [adding, setAdding] = useState(false);
  const [newTicker, setNewTicker] = useState('');
  const [sort, setSort] = useState<'alpha' | 'change' | 'sentiment'>('change');

  const sorted = [...watchlist].sort((a, b) => {
    if (sort === 'alpha')     return a.ticker.localeCompare(b.ticker);
    if (sort === 'change')    return Math.abs(b.change) - Math.abs(a.change);
    return 0;
  });

  const addTicker = () => {
    const t = newTicker.toUpperCase().trim();
    if (t && !watchlist.find(w => w.ticker === t)) {
      setWatchlist(prev => [...prev, { ticker: t, price: 0, change: 0, sentiment: 'neutral' }]);
    }
    setNewTicker(''); setAdding(false);
  };

  return (
    <aside className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/60">
        <div className="flex items-center gap-2">
          <Star size={14} className="text-amber-400 fill-amber-400" />
          <span className="text-sm font-semibold text-slate-200">Watchlist</span>
          <span className="text-xs text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded-md">
            {watchlist.length}
          </span>
        </div>
        <button
          id="sort-watchlist-btn"
          onClick={() => setSort(s => s === 'alpha' ? 'change' : s === 'change' ? 'sentiment' : 'alpha')}
          className="btn-icon" title={`Sort: ${sort}`}
        >
          <ArrowUpDown size={13} />
        </button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto py-2">
        {sorted.map(item => (
          <button
            key={item.ticker}
            id={`watchlist-${item.ticker}`}
            onClick={() => onSelect(item.ticker)}
            className={clsx(
              'w-full flex items-center gap-3 px-4 py-2.5 text-left transition-all duration-150',
              selected === item.ticker
                ? 'bg-slate-800/80 border-l-2 border-cyan-500'
                : 'hover:bg-slate-800/40 border-l-2 border-transparent'
            )}
          >
            {/* Sentiment dot */}
            <span className={clsx('w-2 h-2 rounded-full shrink-0', sentimentDot[item.sentiment])} />

            {/* Ticker */}
            <span className="font-data font-semibold text-sm text-slate-200 w-12">{item.ticker}</span>

            {/* Price & change */}
            <div className="ml-auto text-right">
              <div className="font-data text-xs text-slate-400">${item.price.toFixed(2)}</div>
              <div className={clsx(
                'font-data text-xs font-medium flex items-center gap-0.5 justify-end',
                item.change >= 0 ? 'text-emerald-400' : 'text-rose-400'
              )}>
                {item.change >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                {item.change >= 0 ? '+' : ''}{item.change.toFixed(2)}%
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Add ticker */}
      <div className="px-4 py-3 border-t border-slate-800/60">
        {adding ? (
          <div className="flex gap-2">
            <input
              autoFocus
              placeholder="AAPL"
              value={newTicker}
              onChange={e => setNewTicker(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addTicker()}
              className="input flex-1 h-8 text-xs font-data uppercase"
            />
            <button onClick={addTicker} className="btn-primary btn h-8 px-3 text-xs">Add</button>
            <button onClick={() => setAdding(false)} className="btn-icon h-8 w-8"><X size={13} /></button>
          </div>
        ) : (
          <Button variant="ghost" size="sm" className="w-full gap-1.5" onClick={() => setAdding(true)}>
            <Plus size={14} /> Add Ticker
          </Button>
        )}
      </div>
    </aside>
  );
}
