import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export type ToastVariant = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  title: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
  requestId?: string;
}

export interface ToastContextValue {
  toast: (item: Omit<ToastItem, 'id'>) => string;
  dismiss: (id: string) => void;
  success: (title: string, description?: string) => string;
  error: (title: string, description?: string, requestId?: string) => string;
  warning: (title: string, description?: string) => string;
  info: (title: string, description?: string) => string;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (item: Omit<ToastItem, 'id'>) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      const newToast: ToastItem = { ...item, id };

      setToasts((prev) => [...prev, newToast]);

      const duration = item.duration ?? 4000;
      if (duration > 0) {
        setTimeout(() => {
          dismiss(id);
        }, duration);
      }

      return id;
    },
    [dismiss]
  );

  const success = useCallback(
    (title: string, description?: string) => toast({ title, description, variant: 'success' }),
    [toast]
  );

  const error = useCallback(
    (title: string, description?: string, requestId?: string) =>
      toast({ title, description, variant: 'error', duration: 7000, requestId }),
    [toast]
  );

  const warning = useCallback(
    (title: string, description?: string) => toast({ title, description, variant: 'warning' }),
    [toast]
  );

  const info = useCallback(
    (title: string, description?: string) => toast({ title, description, variant: 'info' }),
    [toast]
  );

  const contextValue = useMemo<ToastContextValue>(
    () => ({
      toast,
      dismiss,
      success,
      error,
      warning,
      info,
    }),
    [toast, dismiss, success, error, warning, info]
  );

  const getToastIcon = (variant?: ToastVariant) => {
    switch (variant) {
      case 'success':
        return <CheckCircle2 className="h-4 w-4 text-ok shrink-0 mt-0.5" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-bad shrink-0 mt-0.5" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-warn shrink-0 mt-0.5" />;
      case 'info':
      default:
        return <Info className="h-4 w-4 text-info shrink-0 mt-0.5" />;
    }
  };

  const getVariantStyles = (variant?: ToastVariant) => {
    switch (variant) {
      case 'success':
        return 'border-ok/30 bg-surface text-ink';
      case 'error':
        return 'border-bad/30 bg-surface text-ink';
      case 'warning':
        return 'border-warn/30 bg-surface text-ink';
      case 'info':
      default:
        return 'border-border bg-surface text-ink';
    }
  };

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      {/* Toast viewport */}
      <aside
        aria-label="Notifications"
        className="fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2 pointer-events-none"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role={t.variant === 'error' ? 'alert' : 'status'}
            className={twMerge(
              clsx(
                'pointer-events-auto flex items-start gap-2.5 rounded-ctl border p-3 shadow-layer animate-in slide-in-from-bottom-2 duration-150',
                getVariantStyles(t.variant)
              )
            )}
          >
            {getToastIcon(t.variant)}
            <div className="flex-1 overflow-hidden pr-1">
              <p className="text-xs font-semibold leading-tight">{t.title}</p>
              {t.description && (
                <p className="text-[11px] text-ink-2 mt-1 leading-normal">{t.description}</p>
              )}
              {t.requestId && (
                <div className="mt-1.5 flex items-center gap-1.5 text-[10px] text-ink-3 font-mono bg-surface-muted px-1.5 py-0.5 rounded border border-border w-fit">
                  <span>Req ID: {t.requestId.slice(0, 8)}...</span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (navigator.clipboard) {
                        navigator.clipboard.writeText(t.requestId!);
                      }
                    }}
                    className="hover:text-ink underline text-[10px]"
                    title="Copy full Request ID for support / debugging"
                  >
                    Copy
                  </button>
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={() => dismiss(t.id)}
              className="text-ink-3 hover:text-ink shrink-0 p-0.5 rounded-ctl focus:outline-none focus:ring-1 focus:ring-accent-600"
              aria-label="Dismiss notification"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </aside>
    </ToastContext.Provider>
  );
};

export const useToast = (): ToastContextValue => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

