import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface QuotaBannerProps {
  countdownSeconds: number;
}

export const QuotaBanner: React.FC<QuotaBannerProps> = ({ countdownSeconds }) => {
  return (
    <div className="mb-8 p-5 rounded-2xl bg-amber-950/70 border border-amber-500/60 flex items-start gap-4 shadow-xl shadow-amber-950/40 animate-pulse">
      <AlertTriangle className="w-7 h-7 text-amber-400 shrink-0 mt-0.5" />
      <div>
        <h4 className="text-sm font-bold text-amber-200 mb-1.5 flex items-center gap-2">
          <span>⚠️ Google Free-Tier rate limit reached</span>
        </h4>
        <p className="text-xs text-amber-300/95 leading-relaxed font-medium">
          The system is automatically waiting for{' '}
          <span className="font-mono font-bold text-amber-200 px-1.5 py-0.5 bg-amber-900/60 rounded border border-amber-500/40">
            {countdownSeconds}s
          </span>{' '}
          before retrying. Do not close this page.
        </p>
      </div>
    </div>
  );
};
