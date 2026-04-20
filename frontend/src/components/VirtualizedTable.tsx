import React, { useMemo, useRef, useEffect, useState, useCallback } from 'react';

/**
 * VirtualizedTable Component
 * Renders only visible rows for optimal performance with large datasets.
 * Uses IntersectionObserver for smooth scrolling.
 */

interface Column<T> {
    key: keyof T | string;
    header: string;
    width?: number | string;
    render?: (item: T, index: number) => React.ReactNode;
    className?: string;
    headerClassName?: string;
}

interface VirtualizedTableProps<T> {
    data: T[];
    columns: Column<T>[];
    rowHeight?: number;
    overscan?: number;
    className?: string;
    containerClassName?: string;
    headerClassName?: string;
    rowClassName?: string | ((item: T, index: number) => string);
    onRowClick?: (item: T, index: number) => void;
    emptyMessage?: string;
    keyExtractor?: (item: T, index: number) => string | number;
}

export function VirtualizedTable<T>({
    data,
    columns,
    rowHeight = 52,
    overscan = 5,
    className = '',
    containerClassName = '',
    headerClassName = '',
    rowClassName = '',
    onRowClick,
    emptyMessage = 'No data available',
    keyExtractor = (_, index) => index,
}: VirtualizedTableProps<T>) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [scrollTop, setScrollTop] = useState(0);
    const [containerHeight, setContainerHeight] = useState(0);

    // Handle scroll events
    const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
        setScrollTop(e.currentTarget.scrollTop);
    }, []);

    // Update container height on resize
    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        const observer = new ResizeObserver((entries) => {
            for (const entry of entries) {
                setContainerHeight(entry.contentRect.height);
            }
        });

        observer.observe(container);
        setContainerHeight(container.clientHeight);

        return () => observer.disconnect();
    }, []);

    // Calculate visible range
    const { startIndex, endIndex, visibleData, offsetTop } = useMemo(() => {
        const totalHeight = data.length * rowHeight;
        const start = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
        const visibleCount = Math.ceil(containerHeight / rowHeight) + 2 * overscan;
        const end = Math.min(data.length, start + visibleCount);

        return {
            startIndex: start,
            endIndex: end,
            visibleData: data.slice(start, end),
            offsetTop: start * rowHeight,
            totalHeight,
        };
    }, [data, scrollTop, containerHeight, rowHeight, overscan]);

    const totalHeight = data.length * rowHeight;

    // Get row class name
    const getRowClassName = (item: T, index: number) => {
        if (typeof rowClassName === 'function') {
            return rowClassName(item, index);
        }
        return rowClassName;
    };

    // Get cell value
    const getCellValue = (item: T, column: Column<T>) => {
        if (column.render) {
            return column.render(item, startIndex);
        }
        const key = column.key as keyof T;
        const value = item[key];
        if (value === null || value === undefined) return '-';
        if (typeof value === 'number') return value.toLocaleString();
        return String(value);
    };

    if (data.length === 0) {
        return (
            <div className={`flex items-center justify-center h-64 text-slate-500 dark:text-slate-400 ${className}`}>
                {emptyMessage}
            </div>
        );
    }

    return (
        <div className={`flex flex-col h-full ${containerClassName}`}>
            {/* Fixed Header */}
            <div
                className={`flex bg-slate-100 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-600 sticky top-0 z-10 ${headerClassName}`}
            >
                {columns.map((column, colIndex) => (
                    <div
                        key={colIndex}
                        className={`px-4 py-3 text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider ${column.headerClassName || ''}`}
                        style={{
                            width: column.width || 'auto',
                            flexGrow: column.width ? 0 : 1,
                            flexShrink: column.width ? 0 : 1,
                        }}
                    >
                        {column.header}
                    </div>
                ))}
            </div>

            {/* Scrollable Body */}
            <div
                ref={containerRef}
                className={`flex-1 overflow-auto ${className}`}
                onScroll={handleScroll}
            >
                {/* Spacer for total scrollable area */}
                <div style={{ height: totalHeight, position: 'relative' }}>
                    {/* Visible rows positioned absolutely */}
                    <div
                        style={{
                            position: 'absolute',
                            top: offsetTop,
                            left: 0,
                            right: 0,
                        }}
                    >
                        {visibleData.map((item, localIndex) => {
                            const actualIndex = startIndex + localIndex;
                            return (
                                <div
                                    key={keyExtractor(item, actualIndex)}
                                    className={`flex border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors ${onRowClick ? 'cursor-pointer' : ''
                                        } ${getRowClassName(item, actualIndex)}`}
                                    style={{ height: rowHeight }}
                                    onClick={() => onRowClick?.(item, actualIndex)}
                                >
                                    {columns.map((column, colIndex) => (
                                        <div
                                            key={colIndex}
                                            className={`flex items-center px-4 py-2 text-sm text-slate-700 dark:text-slate-300 ${column.className || ''}`}
                                            style={{
                                                width: column.width || 'auto',
                                                flexGrow: column.width ? 0 : 1,
                                                flexShrink: column.width ? 0 : 1,
                                            }}
                                        >
                                            {getCellValue(item, column)}
                                        </div>
                                    ))}
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* Footer with row count */}
            <div className="flex justify-between items-center px-4 py-2 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400">
                <span>
                    Showing {startIndex + 1}-{Math.min(endIndex, data.length)} of {data.length} rows
                </span>
                <span>
                    {data.length > 100 && '⚡ Virtualized for performance'}
                </span>
            </div>
        </div>
    );
}

/**
 * Hook for virtualized list rendering
 * Can be used for custom implementations
 */
export function useVirtualizedList<T>(
    items: T[],
    containerRef: React.RefObject<HTMLElement>,
    itemHeight: number,
    overscan: number = 5
) {
    const [scrollTop, setScrollTop] = useState(0);
    const [containerHeight, setContainerHeight] = useState(0);

    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        const handleScroll = () => setScrollTop(container.scrollTop);
        const handleResize = () => setContainerHeight(container.clientHeight);

        container.addEventListener('scroll', handleScroll, { passive: true });
        window.addEventListener('resize', handleResize);
        handleResize();

        return () => {
            container.removeEventListener('scroll', handleScroll);
            window.removeEventListener('resize', handleResize);
        };
    }, [containerRef]);

    return useMemo(() => {
        const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
        const visibleCount = Math.ceil(containerHeight / itemHeight) + 2 * overscan;
        const endIndex = Math.min(items.length, startIndex + visibleCount);

        return {
            virtualItems: items.slice(startIndex, endIndex).map((item, i) => ({
                item,
                index: startIndex + i,
                style: {
                    position: 'absolute' as const,
                    top: (startIndex + i) * itemHeight,
                    height: itemHeight,
                    left: 0,
                    right: 0,
                },
            })),
            totalHeight: items.length * itemHeight,
            startIndex,
            endIndex,
        };
    }, [items, scrollTop, containerHeight, itemHeight, overscan]);
}

export default VirtualizedTable;
