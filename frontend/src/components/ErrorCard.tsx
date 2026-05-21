import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorCardProps {
  message: string;
  onRetry?: () => void;
  title?: string;
}

export const ErrorCard: React.FC<ErrorCardProps> = ({
  message,
  onRetry,
  title = 'Data Fetch Error'
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-6 min-h-[250px] rounded-xl border border-red-500/20 bg-slate-900/60 dark:bg-slate-950/40 backdrop-blur-md text-slate-100 shadow-xl shadow-red-950/5">
      <div className="w-12 h-12 rounded-full bg-red-950/30 border border-red-500/30 flex items-center justify-center mb-4 text-red-400">
        <AlertCircle size={24} />
      </div>
      <h3 className="font-display font-semibold text-base text-red-400 mb-1.5">{title}</h3>
      <p className="text-sm text-slate-400 dark:text-slate-400 max-w-md text-center mb-5 font-medium leading-relaxed">
        {message}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold border border-slate-700 transition-all hover:scale-[1.02] active:scale-[0.98] shadow-lg shadow-slate-950/20 group"
        >
          <RefreshCw size={14} className="text-slate-400 group-hover:text-slate-100 group-hover:rotate-180 transition-transform duration-500" />
          Retry Request
        </button>
      )}
    </div>
  );
};

export default ErrorCard;
