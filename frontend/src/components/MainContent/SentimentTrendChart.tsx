import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { SentimentDataPoint } from '../../types/sentiment';

interface SentimentTrendChartProps {
  trend: SentimentDataPoint[];
}

export function SentimentTrendChart({ trend }: SentimentTrendChartProps) {
  // Add some visual class styling based on score threshold
  const data = trend.map((d) => ({
    ...d,
    // Format hourly timestamps for labels
    timeLabel: new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  }));

  return (
    <div className="glass p-4 rounded-xl border border-slate-800/80 bg-slate-950/40">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          24h Sentiment Trend
        </h4>
        <div className="flex items-center gap-3 text-[10px] text-slate-500 font-semibold uppercase">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /> Bullish (&gt;60)</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-rose-500" /> Bearish (&lt;40)</span>
        </div>
      </div>

      <div className="h-40 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 5, left: -25, bottom: 5 }}>
            <XAxis 
              dataKey="timeLabel" 
              stroke="#64748b" 
              fontSize={9} 
              tickLine={false} 
              axisLine={false} 
            />
            <YAxis 
              domain={[0, 100]} 
              stroke="#64748b" 
              fontSize={9} 
              tickLine={false} 
              axisLine={false} 
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const p = payload[0].payload as SentimentDataPoint & { timeLabel: string };
                  const isPos = p.value >= 60;
                  const isNeg = p.value <= 40;
                  const valColor = isPos ? 'text-emerald-400' : isNeg ? 'text-rose-400' : 'text-amber-400';
                  
                  return (
                    <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded-lg shadow-xl backdrop-blur-md text-[10px] space-y-0.5">
                      <div className="text-slate-400 font-semibold">{p.timeLabel}</div>
                      <div className="font-bold">
                        Score: <span className={`font-data ${valColor}`}>{p.value}</span>
                      </div>
                      <div className="text-slate-400">
                        Volume: <span className="font-data text-white">{p.volume}</span>
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            {/* Draw double lines or single line with custom dot coloring */}
            <Line
              type="monotone"
              dataKey="value"
              stroke="url(#lineGrad)"
              strokeWidth={2}
              dot={{ r: 2, strokeWidth: 1, stroke: '#1e293b' }}
              activeDot={{ r: 4 }}
            />
            {/* Gradient definition for Recharts */}
            <defs>
              <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10B981" />
                <stop offset="40%" stopColor="#D97706" />
                <stop offset="100%" stopColor="#EF4444" />
              </linearGradient>
            </defs>
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
