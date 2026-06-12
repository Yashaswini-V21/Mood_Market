import { ButtonHTMLAttributes, ReactNode } from 'react';
import { clsx } from 'clsx';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'warning';
type Size = 'sm' | 'md' | 'lg' | 'icon';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

export function Button({ children, className, variant = 'ghost', size = 'md', loading, disabled, ...props }: ButtonProps) {
  const variantClass: Record<Variant, string> = {
    primary:   'btn-primary',
    secondary: 'btn-ghost border-slate-700',
    ghost:     'btn-ghost',
    danger:    'btn-secondary',
    warning:   'btn bg-amber-600 hover:bg-amber-500 text-white focus:ring-amber-500 active:scale-95',
  };
  const sizeClass: Record<Size, string> = {
    sm:   'h-8 px-3 text-xs',
    md:   'h-10 px-4 text-sm',
    lg:   'h-11 px-6 text-base',
    icon: 'h-9 w-9 px-0',
  };

  return (
    <button
      className={clsx('btn', variantClass[variant], sizeClass[size], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : children}
    </button>
  );
}
