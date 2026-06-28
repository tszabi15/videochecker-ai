import React from 'react';
import { AlertCircle, WifiOff, RefreshCw } from 'lucide-react';

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
  variant?: 'error' | 'warning' | 'network';
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, onRetry, variant = 'error' }) => {
  const styles = {
    error: 'bg-red-950/50 border-red-500/50 text-red-300',
    warning: 'bg-amber-950/50 border-amber-500/50 text-amber-300',
    network: 'bg-rose-950/50 border-rose-500/50 text-rose-300',
  };

  const Icon = variant === 'network' ? WifiOff : AlertCircle;

  return (
    <div className={`p-4 rounded-xl border flex items-start gap-3 ${styles[variant]} animate-fade-in`}>
      <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-relaxed">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-medium transition-colors flex-shrink-0"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Retry
        </button>
      )}
    </div>
  );
};
