import React, { memo, useMemo } from 'react';

/**
 * Skeleton Loading Component - Reusable loading placeholders
 * Provides consistent loading states across the application
 */

interface SkeletonProps {
    className?: string;
    animate?: boolean;
}

// Base skeleton block
export const Skeleton: React.FC<SkeletonProps> = memo(({ className = '', animate = true }) => (
    <div
        className={`bg-slate-200 dark:bg-slate-700 rounded ${animate ? 'animate-pulse' : ''} ${className}`}
    />
));

// Skeleton for text content
export const SkeletonText: React.FC<{ lines?: number; className?: string }> = memo(({ lines = 3, className = '' }) => (
    <div className={`space-y-2 ${className}`}>
        {Array.from({ length: lines }).map((_, i) => (
            <Skeleton
                key={i}
                className={`h-4 ${i === lines - 1 ? 'w-3/4' : 'w-full'}`}
            />
        ))}
    </div>
));

// Skeleton for metric cards (used in Dashboard)
export const SkeletonMetricCard: React.FC = memo(() => (
    <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg space-y-2 animate-pulse">
        <Skeleton className="h-3 w-16" animate={false} />
        <Skeleton className="h-6 w-24" animate={false} />
    </div>
));

// Skeleton for stock cards
export const SkeletonStockCard: React.FC = memo(() => (
    <div className="bg-slate-50 dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-700 animate-pulse">
        <div className="flex justify-between items-start mb-3">
            <div className="space-y-2">
                <Skeleton className="h-5 w-20" animate={false} />
                <Skeleton className="h-3 w-32" animate={false} />
            </div>
            <Skeleton className="h-6 w-16 rounded-full" animate={false} />
        </div>
        <div className="grid grid-cols-4 gap-2">
            {[1, 2, 3, 4].map(i => (
                <div key={i} className="bg-white dark:bg-slate-800 p-2 rounded-lg">
                    <Skeleton className="h-3 w-10 mx-auto mb-1" animate={false} />
                    <Skeleton className="h-4 w-14 mx-auto" animate={false} />
                </div>
            ))}
        </div>
    </div>
));

// Skeleton for chart areas
export const SkeletonChart: React.FC<{ height?: number }> = memo(({ height = 200 }) => (
    <div
        className="bg-slate-800 rounded-xl overflow-hidden animate-pulse"
        style={{ height }}
    >
        <div className="h-full flex items-end justify-around p-4 gap-1">
            {Array.from({ length: 12 }).map((_, i) => (
                <div
                    key={i}
                    className="bg-slate-700 rounded-t w-full"
                    style={{ height: `${30 + Math.random() * 50}%` }}
                />
            ))}
        </div>
    </div>
));

// Skeleton for table rows
export const SkeletonTableRow: React.FC<{ cols?: number }> = memo(({ cols = 5 }) => (
    <tr className="animate-pulse">
        {Array.from({ length: cols }).map((_, i) => (
            <td key={i} className="px-4 py-3">
                <Skeleton className="h-4 w-full" animate={false} />
            </td>
        ))}
    </tr>
));

// Loading overlay for async operations
export const LoadingOverlay: React.FC<{ message?: string }> = memo(({ message = 'Loading...' }) => (
    <div className="absolute inset-0 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm flex items-center justify-center z-10 rounded-xl">
        <div className="text-center">
            <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-sm text-slate-600 dark:text-slate-400">{message}</p>
        </div>
    </div>
));

export default {
    Skeleton,
    SkeletonText,
    SkeletonMetricCard,
    SkeletonStockCard,
    SkeletonChart,
    SkeletonTableRow,
    LoadingOverlay
};
