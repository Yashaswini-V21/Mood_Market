import { TrendingUp } from 'lucide-react';

export function Logo() {
  return (
    <div className="flex items-center gap-2.5 select-none">
      <div className="relative w-8 h-8">
        <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-emerald-500 to-cyan-500 opacity-90" />
        <TrendingUp size={18} className="absolute inset-0 m-auto text-white" />
      </div>
      <div className="leading-none">
        <div className="text-base font-bold text-white tracking-tight">MoodMarket</div>
        <div className="text-[10px] text-slate-500 tracking-widest uppercase">Alpha</div>
      </div>
    </div>
  );
}

/* clean architecture alignment */
