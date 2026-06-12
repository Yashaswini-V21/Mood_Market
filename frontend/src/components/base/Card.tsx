import { ReactNode, HTMLAttributes } from 'react';
import { clsx } from 'clsx';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  variant?: 'default' | 'bullish' | 'bearish' | 'warning' | 'hype';
  hover?: boolean;
  glow?: boolean;
}

export function Card({ children, className, variant = 'default', hover = true, glow = false, ...props }: CardProps) {
  return (
    <div
      className={clsx(
        'card animate-fade-in',
        hover && 'hover:border-slate-600/60',
        variant === 'bullish' && 'border-emerald-500/20',
        variant === 'bearish' && 'border-rose-500/20',
        variant === 'warning' && 'border-amber-500/20',
        variant === 'hype'    && 'border-purple-500/20',
        glow && variant === 'bullish' && 'glow-bullish',
        glow && variant === 'bearish' && 'glow-bearish',
        glow && variant === 'warning' && 'glow-warning',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx('flex items-center justify-between mb-3', className)} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={clsx('text-sm font-semibold text-slate-400 uppercase tracking-wider', className)} {...props}>
      {children}
    </h3>
  );
}
