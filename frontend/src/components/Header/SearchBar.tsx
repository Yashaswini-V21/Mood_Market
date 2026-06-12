import { useState, useRef, useEffect } from 'react';
import { Search, X, TrendingUp } from 'lucide-react';
import { Input } from '../base/Input';

const POPULAR = ['AAPL', 'MSFT', 'TSLA', 'NVDA', 'GOOGL', 'META', 'AMZN', 'SPY', 'QQQ', 'GME'];

interface SearchBarProps {
  onSelect: (ticker: string) => void;
}

export function SearchBar({ onSelect }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const results = query
    ? POPULAR.filter(t => t.startsWith(query.toUpperCase()))
    : POPULAR.slice(0, 5);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={ref} className="relative w-full max-w-sm">
      <Input
        id="ticker-search"
        placeholder="Search ticker… AAPL, TSLA"
        value={query}
        onChange={e => { setQuery(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        icon={<Search size={15} />}
        iconRight={query ? (
          <button onClick={() => { setQuery(''); setOpen(false); }} className="hover:text-slate-300">
            <X size={14} />
          </button>
        ) : undefined}
        className="pr-8"
      />

      {open && (
        <div className="absolute top-full mt-1.5 left-0 right-0 z-50 glass-strong rounded-xl overflow-hidden shadow-glass animate-slide-up">
          <div className="px-3 py-2 border-b border-slate-700/50">
            <span className="text-[11px] text-slate-500 uppercase tracking-wider">
              {query ? 'Results' : 'Popular'}
            </span>
          </div>
          {results.length === 0 && (
            <div className="px-3 py-3 text-sm text-slate-500">No results for "{query}"</div>
          )}
          {results.map(t => (
            <button
              key={t}
              className="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-slate-800/60 transition-colors"
              onClick={() => { onSelect(t); setQuery(t); setOpen(false); }}
            >
              <TrendingUp size={14} className="text-cyan-400 shrink-0" />
              <span className="font-data font-medium text-sm text-slate-200">{t}</span>
              <span className="ml-auto text-xs text-slate-500">Stock</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
