import React from 'react';

/**
 * Price Source Badge Component
 * Displays the source of the price data with appropriate styling
 * 
 * Sources:
 * - WS: Live WebSocket feed (green, pulsing)
 * - REST: Upstox REST API (yellow)
 * - DB: Database/EOD data (gray)
 * - NONE: No data available (red)
 */

interface PriceSourceBadgeProps {
    source: 'WS' | 'REST' | 'DB' | 'CACHED' | 'NONE' | string | undefined | null;
    className?: string;
}

export const PriceSourceBadge: React.FC<PriceSourceBadgeProps> = ({ source, className = '' }) => {
    const getSourceConfig = () => {
        switch (source) {
            case 'WS':
                return {
                    label: 'LIVE',
                    bgClass: 'bg-emerald-500',
                    textClass: 'text-white',
                    pulse: true
                };
            case 'REST':
                return {
                    label: 'API',
                    bgClass: 'bg-amber-500',
                    textClass: 'text-white',
                    pulse: false
                };
            case 'DB':
                return {
                    label: 'EOD',
                    bgClass: 'bg-slate-400',
                    textClass: 'text-white',
                    pulse: false
                };
            case 'CACHED':
                return {
                    label: 'CACHED',
                    bgClass: 'bg-blue-400',
                    textClass: 'text-white',
                    pulse: false
                };
            case 'NONE':
            default:
                return {
                    label: '--',
                    bgClass: 'bg-slate-200 dark:bg-slate-700',
                    textClass: 'text-slate-500',
                    pulse: false
                };
        }
    };

    const config = getSourceConfig();

    return (
        <span
            className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${config.bgClass} ${config.textClass} ${className}`}
        >
            {config.pulse && (
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
            )}
            {config.label}
        </span>
    );
};

/**
 * Safe value formatter for price/number fields
 * Converts undefined, null, NaN to '--'
 */
export const formatValue = (value: any, decimals: number = 2): string => {
    if (value === undefined || value === null || value === 'undefined' || Number.isNaN(value)) {
        return '--';
    }
    if (typeof value === 'number') {
        return value.toLocaleString('en-IN', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    }
    return String(value);
};

/**
 * Price display with source badge
 */
interface PriceWithSourceProps {
    price: number | null | undefined;
    source?: string;
    currency?: string;
    decimals?: number;
    className?: string;
}

export const PriceWithSource: React.FC<PriceWithSourceProps> = ({
    price,
    source,
    currency = '₹',
    decimals = 2,
    className = ''
}) => {
    const displayPrice = formatValue(price, decimals);

    return (
        <div className={`flex items-center gap-1.5 ${className}`}>
            <span className="font-bold text-slate-800 dark:text-white">
                {displayPrice !== '--' ? `${currency}${displayPrice}` : displayPrice}
            </span>
            {source && <PriceSourceBadge source={source} />}
        </div>
    );
};

export default PriceSourceBadge;
