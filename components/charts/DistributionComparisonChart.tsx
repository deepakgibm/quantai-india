import React, { useEffect, useRef } from 'react';

interface DistributionComparisonChartProps {
    backtestReturns: number[];
    liveReturns: number[];
    height?: number;
    bins?: number;
}

const DistributionComparisonChart: React.FC<DistributionComparisonChartProps> = ({
    backtestReturns,
    liveReturns,
    height = 280,
    bins = 20
}) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        if (!canvasRef.current) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Get dimensions
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);

        const width = rect.width;
        const h = rect.height;
        const padding = { top: 30, right: 30, bottom: 50, left: 50 };
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = h - padding.top - padding.bottom;

        // Clear
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(0, 0, width, h);

        if (backtestReturns.length === 0 && liveReturns.length === 0) {
            ctx.fillStyle = '#94a3b8';
            ctx.font = '14px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('No data available', width / 2, h / 2);
            return;
        }

        // Combine all returns to get range
        const allReturns = [...backtestReturns, ...liveReturns];
        const minReturn = Math.min(...allReturns);
        const maxReturn = Math.max(...allReturns);
        const binWidth = (maxReturn - minReturn) / bins;

        // Create histograms
        const createHistogram = (returns: number[]) => {
            const hist = new Array(bins).fill(0);
            returns.forEach(r => {
                const binIdx = Math.min(Math.floor((r - minReturn) / binWidth), bins - 1);
                hist[binIdx]++;
            });
            // Normalize
            const total = returns.length;
            return hist.map(count => count / total);
        };

        const btHist = backtestReturns.length > 0 ? createHistogram(backtestReturns) : new Array(bins).fill(0);
        const liveHist = liveReturns.length > 0 ? createHistogram(liveReturns) : new Array(bins).fill(0);

        const maxFreq = Math.max(...btHist, ...liveHist) * 1.1;

        // Scale functions
        const xScale = (i: number) => padding.left + (i / bins) * chartWidth;
        const yScale = (val: number) => padding.top + chartHeight - (val / maxFreq) * chartHeight;
        const barWidth = chartWidth / bins - 2;

        // Draw backtest histogram
        ctx.fillStyle = 'rgba(59, 130, 246, 0.6)';
        btHist.forEach((freq, i) => {
            const x = xScale(i) + 1;
            const y = yScale(freq);
            const barHeight = chartHeight - (y - padding.top);
            ctx.fillRect(x, y, barWidth / 2, barHeight);
        });

        // Draw live histogram (offset)
        ctx.fillStyle = 'rgba(16, 185, 129, 0.6)';
        liveHist.forEach((freq, i) => {
            const x = xScale(i) + 1 + barWidth / 2;
            const y = yScale(freq);
            const barHeight = chartHeight - (y - padding.top);
            ctx.fillRect(x, y, barWidth / 2, barHeight);
        });

        // Draw zero line if in range
        if (minReturn < 0 && maxReturn > 0) {
            const zeroX = padding.left + ((-minReturn) / (maxReturn - minReturn)) * chartWidth;
            ctx.strokeStyle = '#ef4444';
            ctx.lineWidth = 2;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.moveTo(zeroX, padding.top);
            ctx.lineTo(zeroX, h - padding.bottom);
            ctx.stroke();
            ctx.setLineDash([]);
        }

        // X-axis labels
        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px Inter, sans-serif';
        ctx.textAlign = 'center';
        for (let i = 0; i <= 4; i++) {
            const val = minReturn + (i / 4) * (maxReturn - minReturn);
            const x = padding.left + (i / 4) * chartWidth;
            ctx.fillText(`${(val * 100).toFixed(1)}%`, x, h - padding.bottom + 15);
        }

        // Y-axis label
        ctx.save();
        ctx.translate(15, h / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Frequency', 0, 0);
        ctx.restore();

        // Legend
        const legendY = h - 15;
        ctx.font = '11px Inter, sans-serif';

        ctx.fillStyle = 'rgba(59, 130, 246, 0.8)';
        ctx.fillRect(padding.left, legendY - 8, 16, 8);
        ctx.fillStyle = '#94a3b8';
        ctx.textAlign = 'left';
        ctx.fillText(`Backtest (n=${backtestReturns.length})`, padding.left + 20, legendY);

        ctx.fillStyle = 'rgba(16, 185, 129, 0.8)';
        ctx.fillRect(padding.left + 140, legendY - 8, 16, 8);
        ctx.fillStyle = '#94a3b8';
        ctx.fillText(`Live (n=${liveReturns.length})`, padding.left + 160, legendY);

        // Title
        ctx.fillStyle = '#f8fafc';
        ctx.font = 'bold 14px Inter, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('Return Distribution Comparison', padding.left, 20);

        // Stats box
        if (backtestReturns.length > 0 && liveReturns.length > 0) {
            const btMean = backtestReturns.reduce((a, b) => a + b, 0) / backtestReturns.length;
            const liveMean = liveReturns.reduce((a, b) => a + b, 0) / liveReturns.length;

            ctx.fillStyle = '#1e293b';
            ctx.fillRect(width - 120, padding.top, 100, 50);
            ctx.strokeStyle = '#334155';
            ctx.strokeRect(width - 120, padding.top, 100, 50);

            ctx.font = '10px Inter, sans-serif';
            ctx.fillStyle = '#3b82f6';
            ctx.textAlign = 'left';
            ctx.fillText(`BT μ: ${(btMean * 100).toFixed(2)}%`, width - 115, padding.top + 18);
            ctx.fillStyle = '#10b981';
            ctx.fillText(`Live μ: ${(liveMean * 100).toFixed(2)}%`, width - 115, padding.top + 36);
        }

    }, [backtestReturns, liveReturns, height, bins]);

    return (
        <div className="bg-slate-800 rounded-xl overflow-hidden">
            <canvas
                ref={canvasRef}
                style={{ width: '100%', height }}
                className="block"
            />
        </div>
    );
};

export default DistributionComparisonChart;
