import React from 'react';

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
}

/**
 * Reusable empty state placeholder used in all 6 workspace mode panels.
 */
const EmptyState: React.FC<EmptyStateProps> = ({ icon, title, description, action }) => (
  <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
    <div className="text-slate-600 mb-4 animate-pulse">{icon}</div>
    <h3 className="text-white font-bold text-lg mb-1">{title}</h3>
    <p className="text-slate-400 text-sm max-w-sm">{description}</p>
    {action && <div className="mt-6">{action}</div>}
  </div>
);

export default EmptyState;
