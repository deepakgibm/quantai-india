export const getPriceColor = (change: number): string => {
    if (change > 0) return 'text-green-600 dark:text-green-400';
    if (change < 0) return 'text-red-600 dark:text-red-400';
    return 'text-slate-500 dark:text-slate-400';
};

export const getBgColor = (change: number): string => {
    if (change > 0) return 'bg-green-500';
    if (change < 0) return 'bg-red-500';
    return 'bg-slate-500';
};

export const getGlassColor = (change: number): string => {
    if (change > 0) return 'bg-green-50/50 border-green-100 dark:bg-green-900/10 dark:border-green-900/30';
    if (change < 0) return 'bg-red-50/50 border-red-100 dark:bg-red-900/10 dark:border-red-900/30';
    return 'bg-slate-50/50 border-slate-100 dark:bg-slate-800/50 dark:border-slate-700';
};
