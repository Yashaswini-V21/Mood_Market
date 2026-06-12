import { SignalType } from '../../types/trading';
import { clsx } from 'clsx';
import { ShieldCheck, ShieldAlert, AlertTriangle, ArrowUpRight, ArrowDownRight, HelpCircle } from 'lucide-react';

interface SignalBadgeProps {
  type: SignalType;
  className?: string;
}

export function SignalBadge({ type, className }: SignalBadgeProps) {
  // Styles mapping based on SignalType
  const colorMap: Record<SignalType, { bg: string; text: string; border: string; icon: any }> = {
    'STRONG BUY': {
      bg: 'bg-emerald-950/40',
      text: 'text-emerald-300',
      border: 'border-emerald-500/40',
      icon: ArrowUpRight
    },
    'BUY': {
      bg: 'bg-emerald-950/20',
      text: 'text-emerald-400',
      border: 'border-emerald-500/20',
      icon: ShieldCheck
    },
    'BUY WITH CAUTION': {
      bg: 'bg-amber-950/20',
      text: 'text-amber-400',
      border: 'border-amber-500/20',
      icon: AlertTriangle
    },
    'NEUTRAL': {
      bg: 'bg-slate-900/40',
      text: 'text-slate-400',
      border: 'border-slate-800',
      icon: HelpCircle
    },
    'SELL': {
      bg: 'bg-rose-950/20',
      text: 'text-rose-400',
      border: 'border-rose-500/20',
      icon: ArrowDownRight
    },
    'STRONG SELL': {
      bg: 'bg-rose-950/40',
      text: 'text-rose-300',
      border: 'border-rose-500/40',
      icon: ShieldAlert
    }
  };

  const current = colorMap[type] || colorMap['NEUTRAL'];
  const Icon = current.icon;

  return (
    <span className={clsx(
      'flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-[11px] font-extrabold uppercase tracking-widest',
      current.bg,
      current.text,
      current.border,
      className
    )}>
      <Icon size={12} className="shrink-0 animate-pulse" />
      {type}
    </span>
  );
}
