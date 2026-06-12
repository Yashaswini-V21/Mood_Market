import { useState } from 'react';
import { TrendingUp, TrendingDown, BarChart2 } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Card, CardHeader, CardTitle } from '../base/Card';
import { Badge, ConfidenceBadge } from '../base/Badge';

interface ForecastCardProps { ticker: string }

// Mini sparkline data
const genSparkline = () => {
  let p = 192;
  return Array.from({ length: 24 }, (_, i) => {
    p += (Math.random() - 0.48) * 3;
    return { t: `${i}h`, price: +p.toFixed(2) };
  });
};

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass px-2.5 py-1.5 rounded-lg text-xs font-data text-slate-200 shadow-glass">
      ${payload[0].value.toFixed(2)}
    </div>
  );
};

export function ForecastCard({ ticker }: ForecastCardProps) {
  const [data] = useState(genSparkline);
  const current  = data[data.length - 4]?.price ?? 192;
  const predicted = +(current * 1.023).toFixed(2);
  const delta   = +(predicted - current).toFixed(2);
  const pct     = +((delta / current) * 100).toFixed(2);
  const isUp    = delta >= 0;
  const conf    = 63;

  return (
    <Card variant={isUp ? 'bullish' : 'bearish'} glow className="animate-fade-in">
      <CardHeader>
        <div className="flex items-center gap-2">
          <BarChart2 size={15} className="text-cyan-400" />
          <CardTitle>Price Forecast</CardTitle>
        </div>
        <Badge variant={isUp ? 'bullish' : 'bearish'}>4h outlook</Badge>
      </CardHeader>

      {/* Prices row */}
      <div className="flex items-end gap-4 mb-3">
        <div>
          <div className="text-xs text-slate-500 mb-0.5">Current</div>
          <div className="font-data text-xl font-bold text-white">${current.toFixed(2)}</div>
        </div>
        <div className="flex flex-col items-center pb-1 text-slate-600">
          {isUp ? <TrendingUp size={18} className="text-emerald-400" /> : <TrendingDown size={18} className="text-rose-400" />}
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-0.5">Predicted (4h)</div>
          <div className={`font-data text-xl font-bold ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
            ${predicted.toFixed(2)}
          </div>
        </div>
        <div className="ml-auto text-right">
          <div className="text-xs text-slate-500 mb-0.5">Delta</div>
          <div className={`font-data text-sm font-bold ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
            {isUp ? '+' : ''}{pct}%
          </div>
        </div>
      </div>

      {/* Sparkline */}
      <div className="h-24 -mx-1 mb-3">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id={`fg-${ticker}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={isUp ? '#10B981' : '#EF4444'} stopOpacity={0.3} />
                <stop offset="95%" stopColor={isUp ? '#10B981' : '#EF4444'} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="t" hide />
            <YAxis domain={['auto', 'auto']} hide />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone" dataKey="price"
              stroke={isUp ? '#10B981' : '#EF4444'}
              strokeWidth={1.5}
              fill={`url(#fg-${ticker})`}
              animationDuration={500}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Confidence bar */}
      <div>
        <div className="flex justify-between text-xs mb-1.5">
          <span className="text-slate-500">Model Confidence</span>
          <ConfidenceBadge value={conf} />
        </div>
        <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${conf}%`, backgroundColor: isUp ? '#10B981' : '#EF4444' }}
          />
        </div>
        <div className="flex justify-between text-[10px] text-slate-600 mt-1">
          <span>Historical accuracy: 68.4%</span>
          <span className="font-data">Informer model</span>
        </div>
      </div>
    </Card>
  );
}
