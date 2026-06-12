import { Zap, MessageSquare, Volume2, AlertTriangle } from 'lucide-react';
import { BarChart, Bar, XAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Card, CardHeader, CardTitle } from '../base/Card';
import { AlertBadge } from '../base/Badge';

interface HypeStormCardProps { ticker: string }

const MENTION_DATA = [
  { h: '18:00', v: 120 }, { h: '19:00', v: 145 }, { h: '20:00', v: 189 },
  { h: '21:00', v: 340 }, { h: '22:00', v: 870 }, { h: '23:00', v: 1240 },
  { h: '00:00', v: 960 }, { h: '01:00', v: 1380 },
];
const MAX_V = Math.max(...MENTION_DATA.map(d => d.v));

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass px-2.5 py-1.5 rounded-lg text-xs shadow-glass">
      <div className="text-slate-400">{label}</div>
      <div className="font-data font-semibold text-amber-400">{payload[0].value.toLocaleString()} mentions</div>
    </div>
  );
};

export function HypeStormCard({ ticker }: HypeStormCardProps) {
  const detected  = true;
  const volumePct = 340;
  const level     = 'HIGH' as const;

  return (
    <Card variant="warning" className="animate-fade-in">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Zap size={15} className="text-amber-400" />
          <CardTitle>Hype Storm Detection</CardTitle>
        </div>
        <AlertBadge level={level} />
      </CardHeader>

      {/* Status row */}
      <div className="flex items-center gap-3 p-3 rounded-lg bg-amber-500/8 border border-amber-500/20 mb-3">
        <AlertTriangle size={20} className="text-amber-400 shrink-0" />
        <div>
          <div className="text-sm font-semibold text-amber-300">
            {detected ? 'HYPE STORM DETECTED' : 'NO ANOMALY'}
          </div>
          <div className="text-xs text-slate-500">{ticker} — Volume +{volumePct}% above 30d baseline</div>
        </div>
      </div>

      {/* Mention chart */}
      <div className="h-20 -mx-1 mb-3">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={MENTION_DATA} barCategoryGap="20%">
            <XAxis dataKey="h" tick={{ fill: '#475569', fontSize: 9 }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
            <Bar dataKey="v" radius={[3, 3, 0, 0]}>
              {MENTION_DATA.map((d, i) => (
                <Cell key={i} fill={d.v === MAX_V ? '#F59E0B' : d.v > 400 ? '#D97706' : '#334155'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2 text-center">
        {[
          { icon: <Volume2 size={13} className="text-amber-400" />, label: 'Volume Spike', val: `+${volumePct}%` },
          { icon: <MessageSquare size={13} className="text-cyan-400" />, label: 'Mentions/hr', val: '1,380' },
          { icon: <Zap size={13} className="text-purple-400" />, label: 'Anomaly Score', val: '8.7/10' },
        ].map(s => (
          <div key={s.label} className="bg-slate-800/40 rounded-lg p-2">
            <div className="flex items-center justify-center mb-1">{s.icon}</div>
            <div className="font-data text-sm font-bold text-white">{s.val}</div>
            <div className="text-[10px] text-slate-500">{s.label}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}
