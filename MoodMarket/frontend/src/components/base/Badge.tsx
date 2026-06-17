import { ReactNode } from 'react';
import { clsx } from 'clsx';
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Zap, ShieldAlert } from 'lucide-react';

type SentimentType = 'bullish' | 'bearish' | 'neutral' | 'warning' | 'hype' | 'critical';

interface BadgeProps {
  children: ReactNode;
  variant?: SentimentType;
  icon?: boolean;
  pulse?: boolean;
  className?: string;
}

const icons: Record<SentimentType, ReactNode> = {
  bullish:  <TrendingUp size={10} />,
  bearish:  <TrendingDown size={10} />,
  neutral:  <Minus size={10} />,
  warning:  <AlertTriangle size={10} />,
  hype:     <Zap size={10} />,
  critical: <ShieldAlert size={10} />,
};

export function Badge({ children, variant = 'neutral', icon = true, pulse = false, className }: BadgeProps) {
  return (
    <span className={clsx(
      `badge-${variant}`,
      pulse && variant === 'critical' && 'animate-pulse',
      className
    )}>
      {icon && icons[variant]}
      {children}
    </span>
  );
}

/** Confidence badge 0–100 */
export function ConfidenceBadge({ value }: { value: number }) {
  const variant = value >= 70 ? 'bullish' : value >= 45 ? 'warning' : 'bearish';
  return (
    <span className={clsx('badge', `badge-${variant}`)}>
      {value.toFixed(0)}% conf.
    </span>
  );
}

/** Alert level badge */
export function AlertBadge({ level }: { level: 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' }) {
  const map: Record<string, SentimentType> = {
    NONE: 'neutral', LOW: 'neutral', MEDIUM: 'warning', HIGH: 'hype', CRITICAL: 'critical'
  };
  return <Badge variant={map[level]} pulse={level === 'CRITICAL'}>{level}</Badge>;
}

/* clean architecture alignment */
