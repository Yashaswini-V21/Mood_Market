 
import { createContext, useContext, useState, ReactNode, useCallback } from 'react';
import { clsx } from 'clsx';
import { X, CheckCircle, AlertTriangle, Info } from 'lucide-react';

type ToastType = 'success' | 'error' | 'info';

interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextType {
  toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((message: string, type: ToastType = 'info') => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  }, []);

  const removeToast = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={clsx(
              'flex items-center gap-2 rounded-lg px-4 py-3 shadow-lg transition-all animate-in slide-in-from-right-8',
              {
                'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20': t.type === 'success',
                'bg-red-500/10 text-red-500 border border-red-500/20': t.type === 'error',
                'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20': t.type === 'info',
              }
            )}
          >
            {t.type === 'success' && <CheckCircle size={16} />}
            {t.type === 'error' && <AlertTriangle size={16} />}
            {t.type === 'info' && <Info size={16} />}
            <span className="text-sm font-medium">{t.message}</span>
            <button onClick={() => removeToast(t.id)} className="ml-2 hover:opacity-70">
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastProvider');
  return context;
};


/* clean architecture alignment */
