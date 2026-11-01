import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { Button } from './Button';

export interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: string;
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  footer,
  width = 'w-[440px]',
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-ink/20 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Drawer Surface - Full width sheet on mobile (<768px), overlay drawer on tablet/desktop */}
      <div className="fixed inset-y-0 right-0 flex max-w-full pl-0 sm:pl-10">
        <div
          className={`flex h-full w-screen sm:w-auto ${width} max-w-full sm:max-w-[90vw] flex-col border-l border-border bg-surface shadow-layer animate-in slide-in-from-right duration-200`}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border px-4 sm:px-5 py-3 sm:py-3.5">
            <div className="min-w-0 pr-2">
              <h3 className="text-sm font-semibold text-ink truncate">{title}</h3>
              {subtitle && <p className="text-xs text-ink-3 mt-0.5 truncate">{subtitle}</p>}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-10 w-10 sm:h-7 sm:w-7 p-0 flex items-center justify-center text-ink-3 hover:text-ink shrink-0"
              aria-label="Close drawer"
            >
              <X className="h-5 w-5 sm:h-4 sm:w-4" />
            </Button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-5 text-xs text-ink">{children}</div>

          {/* Footer */}
          {footer && (
            <div className="flex items-center justify-end gap-2 border-t border-border bg-surface-2/50 px-4 sm:px-5 py-3">
              {footer}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
