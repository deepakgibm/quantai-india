import React from 'react';
import { RefreshCw } from 'lucide-react';

interface ActionButtonProps {
  onClick: () => void;
  loading?: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
  label: string;
  loadingLabel?: string;
  variant?: 'primary' | 'secondary' | 'danger';
  fullWidth?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

const variantClasses: Record<string, string> = {
  primary: 'bg-gradient-to-r from-brand-600 to-purple-600 hover:from-brand-500 hover:to-purple-500 text-white shadow-lg shadow-brand-600/20',
  secondary: 'bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200',
  danger: 'bg-gradient-to-r from-red-700 to-rose-700 hover:from-red-600 hover:to-rose-600 text-white',
};

const sizeClasses: Record<string, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2.5 text-xs',
  lg: 'px-5 py-3 text-sm',
};

/**
 * Unified action / run button for all workspace mode panels.
 * Replaces 5+ duplicated gradient button patterns.
 */
const ActionButton: React.FC<ActionButtonProps> = ({
  onClick,
  loading = false,
  disabled = false,
  icon,
  label,
  loadingLabel,
  variant = 'primary',
  fullWidth = true,
  size = 'md',
}) => (
  <button
    onClick={onClick}
    disabled={loading || disabled}
    className={`
      ${fullWidth ? 'w-full' : ''}
      ${sizeClasses[size]}
      ${variantClasses[variant]}
      flex items-center justify-center gap-2
      rounded-lg font-bold tracking-wider uppercase
      transition-all duration-200
      disabled:opacity-50 disabled:cursor-not-allowed
    `}
  >
    {loading ? (
      <RefreshCw size={14} className="animate-spin" />
    ) : (
      icon && <span className="opacity-80">{icon}</span>
    )}
    {loading ? (loadingLabel ?? `Running…`) : label}
  </button>
);

export default ActionButton;
