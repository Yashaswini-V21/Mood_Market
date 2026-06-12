import { clsx } from 'clsx';

interface WatchItem {
  ticker: string;
  price: number;
  change: number;
  sentiment: 'bullish' | 'bearish' | 'neutral';
}

const TICKERS: WatchItem[] = [
  { ticker: 'AAPL',  price: 192.53, change:  1.23, sentiment: 'bullish'  },
  { ticker: 'MSFT',  price: 415.20, change:  0.89, sentiment: 'bullish'  },
  { ticker: 'TSLA',  price: 248.42, change: -2.15, sentiment: 'bearish'  },
  { ticker: 'GOOGL', price: 172.90, change: -0.54, sentiment: 'neutral'  },
  { ticker: 'NVDA',  price: 875.39, change:  3.47, sentiment: 'bullish'  },
  { ticker: 'META',  price: 526.68, change:  2.31, sentiment: 'bullish'  },
  { ticker: 'GME',   price:  24.83, change: 15.20, sentiment: 'bullish'  },
  { ticker: 'AMZN',  price: 193.77, change:  1.02, sentiment: 'neutral'  },
];

const sentimentColors = {
  bullish: 'bg-emerald-400',
  bearish: 'bg-rose-400',
  neutral: 'bg-slate-500',
};

interface MobileWatchlistProps {
  selectedTicker: string;
  onTickerSelect: (ticker: string) => void;
}

export function MobileWatchlist({ selectedTicker, onTickerSelect }: MobileWatchlistProps) {
  return (
    <div className="md:hidden w-full overflow-hidden py-2.5 border-b border-slate-900 bg-slate-900/10">
      <div className="flex gap-2.5 overflow-x-auto px-4 scrollbar-none scroll-smooth">
        {TICKERS.map((item) => {
          const isSelected = selectedTicker === item.ticker;
          const isPos = item.change >= 0;
          
          return (
            <button
              key={item.ticker}
              onClick={() => onTickerSelect(item.ticker)}
              className={clsx(
                'flex items-center gap-2 px-3.5 py-2 rounded-xl border shrink-0 transition-all duration-200 active:scale-95 text-xs font-semibold',
                isSelected 
                  ? 'border-cyan-500 bg-cyan-950/20 text-white' 
                  : 'border-slate-800/80 bg-slate-950/40 text-slate-400'
              )}
            >
              {/* Sentiment Dot */}
              <span className={clsx('w-1.5 h-1.5 rounded-full shrink-0', sentimentColors[item.sentiment])} />
              
              <span className="font-data font-bold uppercase">{item.ticker}</span>
              
              <span className="font-data text-slate-300 font-medium">${item.price.toFixed(2)}</span>
              
              <span className={clsx(
                'font-data text-[10px] font-bold flex items-center',
                isPos ? 'text-emerald-400' : 'text-rose-400'
              )}>
                {isPos ? '+' : ''}{item.change.toFixed(1)}%
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
