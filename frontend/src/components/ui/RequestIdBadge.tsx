import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

export interface RequestIdBadgeProps {
  requestId: string;
  label?: string;
  className?: string;
}

export const RequestIdBadge: React.FC<RequestIdBadgeProps> = ({
  requestId,
  label = 'Request ID',
  className = '',
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (navigator.clipboard) {
      navigator.clipboard.writeText(requestId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border border-border bg-surface-muted text-[11px] font-mono text-muted ${className}`}
      title={`Traceability reference: ${requestId}`}
    >
      <span className="text-[10px] uppercase font-semibold text-muted tracking-wider">
        {label}:
      </span>
      <span className="text-ink font-medium select-all">
        {requestId.length > 12 ? `${requestId.slice(0, 8)}...` : requestId}
      </span>
      <button
        type="button"
        onClick={handleCopy}
        className="text-muted hover:text-ink p-0.5 rounded transition-colors focus:outline-none"
        title="Copy Request ID to clipboard"
      >
        {copied ? (
          <Check className="w-3 h-3 text-ok" />
        ) : (
          <Copy className="w-3 h-3" />
        )}
      </button>
    </div>
  );
};

