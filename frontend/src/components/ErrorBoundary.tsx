import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      const isChunkError = this.state.error?.name === 'ChunkLoadError' || 
                           this.state.error?.message?.includes('Failed to fetch dynamically imported module') ||
                           this.state.error?.message?.includes('importing');

      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-950 p-6 font-sans">
          <div className="max-w-md w-full bg-slate-900 border border-rose-500/20 rounded-2xl p-6 text-center shadow-xl shadow-rose-950/10">
            <div className="inline-flex p-3 rounded-full bg-rose-500/10 text-rose-400 mb-4 animate-pulse">
              <AlertTriangle size={32} />
            </div>
            
            <h2 className="text-xl font-bold text-white mb-2 font-display">
              {isChunkError ? 'Update Available' : 'Something went wrong'}
            </h2>
            
            <p className="text-sm text-slate-400 mb-6">
              {isChunkError 
                ? 'A new version of QuantAI was deployed. Please reload to load the latest application assets.'
                : 'An unexpected rendering error occurred. You can reload the page to try again.'}
            </p>

            <button
              onClick={this.handleReload}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white rounded-xl font-semibold transition-all shadow-lg shadow-brand-500/20 active:scale-[0.98]"
            >
              <RefreshCw size={16} />
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return (this as React.Component<Props, State>).props.children;
  }
}
