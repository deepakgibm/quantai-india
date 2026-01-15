/**
 * Chart Data Utilities
 * Provides data downsampling and virtualization for large datasets
 * to prevent UI freezes when rendering charts with 1000+ data points
 */

export interface ChartDataPoint {
    timestamp?: string;
    date?: string;
    equity?: number;
    drawdown?: number;
    value?: number;
    [key: string]: any;
}

/**
 * Downsample data using Largest Triangle Three Buckets (LTTB) algorithm
 * This preserves visual fidelity while reducing data points
 * 
 * @param data - Original data array
 * @param threshold - Maximum number of points to return
 * @returns Downsampled data array
 */
export function downsampleLTTB<T extends ChartDataPoint>(
    data: T[],
    threshold: number,
    valueKey: keyof T = 'equity' as keyof T
): T[] {
    if (threshold >= data.length || threshold <= 2) {
        return data;
    }

    const sampled: T[] = [];
    const bucketSize = (data.length - 2) / (threshold - 2);

    // Always include first point
    sampled.push(data[0]);

    let a = 0; // Previously selected point index

    for (let i = 0; i < threshold - 2; i++) {
        // Calculate bucket boundaries
        const bucketStart = Math.floor((i + 1) * bucketSize) + 1;
        const bucketEnd = Math.min(Math.floor((i + 2) * bucketSize) + 1, data.length - 1);

        // Calculate average of next bucket for area calculation
        const avgBucketStart = Math.floor((i + 2) * bucketSize) + 1;
        const avgBucketEnd = Math.min(Math.floor((i + 3) * bucketSize) + 1, data.length - 1);

        let avgX = 0;
        let avgY = 0;
        let avgCount = 0;

        for (let j = avgBucketStart; j < avgBucketEnd && j < data.length; j++) {
            avgX += j;
            avgY += Number(data[j][valueKey]) || 0;
            avgCount++;
        }

        if (avgCount > 0) {
            avgX /= avgCount;
            avgY /= avgCount;
        }

        // Find point in current bucket that creates largest triangle
        let maxArea = -1;
        let maxAreaIndex = bucketStart;

        const pointAX = a;
        const pointAY = Number(data[a][valueKey]) || 0;

        for (let j = bucketStart; j < bucketEnd && j < data.length; j++) {
            // Calculate triangle area
            const area = Math.abs(
                (pointAX - avgX) * (Number(data[j][valueKey]) - pointAY) -
                (pointAX - j) * (avgY - pointAY)
            ) * 0.5;

            if (area > maxArea) {
                maxArea = area;
                maxAreaIndex = j;
            }
        }

        sampled.push(data[maxAreaIndex]);
        a = maxAreaIndex;
    }

    // Always include last point
    sampled.push(data[data.length - 1]);

    return sampled;
}

/**
 * Simple time-based downsampling
 * Groups data by time intervals and takes the last value in each group
 * 
 * @param data - Original data array
 * @param maxPoints - Maximum number of points
 * @returns Downsampled data array
 */
export function downsampleByInterval<T extends ChartDataPoint>(
    data: T[],
    maxPoints: number
): T[] {
    if (data.length <= maxPoints) {
        return data;
    }

    const ratio = Math.ceil(data.length / maxPoints);
    const sampled: T[] = [];

    for (let i = 0; i < data.length; i += ratio) {
        sampled.push(data[i]);
    }

    // Ensure last point is included
    if (sampled[sampled.length - 1] !== data[data.length - 1]) {
        sampled.push(data[data.length - 1]);
    }

    return sampled;
}

/**
 * Get optimal max points based on container width
 * Uses 2 data points per pixel as a reasonable default
 */
export function getOptimalMaxPoints(containerWidth: number = 800): number {
    return Math.max(100, Math.min(500, containerWidth / 2));
}

/**
 * Memoization helper for chart data
 * Creates a stable reference that only changes when data actually changes
 */
export function createChartDataKey(data: ChartDataPoint[]): string {
    if (data.length === 0) return 'empty';
    const first = data[0];
    const last = data[data.length - 1];
    return `${data.length}-${first.timestamp || first.date}-${last.timestamp || last.date}`;
}

export default {
    downsampleLTTB,
    downsampleByInterval,
    getOptimalMaxPoints,
    createChartDataKey
};
