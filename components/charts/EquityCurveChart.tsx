import React, { useEffect, useRef } from 'react';

interface EquityCurveChartProps {
    data: { date: string; equity: number }[];
    initialCapital?: number;
    height?: number;
    showGrid?: boolean;
}

const EquityCurveChart: React.FC<EquityCurveChartProps> = ({
    data,
    initialCapital = 1000000,
    height = 300,
    showGrid = true
}) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        if (!canvasRef.current || data.length === 0) return;

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
        const padding = { top: 20, right: 60, bottom: 40, left: 80 };
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = h - padding.top - padding.bottom;

        // Clear
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(0, 0, width, h);

        // Get min/max values
        const equities = data.map(d => d.equity);
        const minEquity = Math.min(...equities) * 0.98;
        const maxEquity = Math.max(...equities) * 1.02;

        // Scale functions
        const xScale = (i: number) => padding.left + (i / (data.length - 1)) * chartWidth;
        const yScale = (val: number) => padding.top + chartHeight - ((val - minEquity) / (maxEquity - minEquity)) * chartHeight;

        // Draw grid
        if (showGrid) {
            ctx.strokeStyle = '#334155';
            ctx.lineWidth = 0.5;

            // Horizontal grid lines
            const yTicks = 5;
            for (let i = 0; i <= yTicks; i++) {
                const y = padding.top + (i / yTicks) * chartHeight;
                ctx.beginPath();
                ctx.moveTo(padding.left, y);
                ctx.lineTo(width - padding.right, y);
                ctx.stroke();

                // Y-axis labels
                const value = maxEquity - (i / yTicks) * (maxEquity - minEquity);
                ctx.fillStyle = '#94a3b8';
                ctx.font = '10px Inter, sans-serif';
                ctx.textAlign = 'right';
                ctx.fillText(`₹${(value / 100000).toFixed(1)}L`, padding.left - 8, y + 3);
            }

            // X-axis labels (show 5 dates)
            ctx.textAlign = 'center';
            const xTicks = Math.min(5, data.length);
            for (let i = 0; i < xTicks; i++) {
                const idx = Math.floor((i / (xTicks - 1)) * (data.length - 1));
                const x = xScale(idx);
                ctx.fillStyle = '#94a3b8';
                ctx.fillText(data[idx].date.slice(5), x, h - padding.bottom + 20);
            }
        }

        // Draw initial capital line
        ctx.strokeStyle = '#64748b';
        ctx.setLineDash([5, 5]);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding.left, yScale(initialCapital));
        ctx.lineTo(width - padding.right, yScale(initialCapital));
        ctx.stroke();
        ctx.setLineDash([]);

        // Draw equity curve
        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 2;
        ctx.beginPath();
        data.forEach((d, i) => {
            const x = xScale(i);
            const y = yScale(d.equity);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();

        // Fill area under curve
        const gradient = ctx.createLinearGradient(0, padding.top, 0, h - padding.bottom);
        gradient.addColorStop(0, 'rgba(16, 185, 129, 0.3)');
        gradient.addColorStop(1, 'rgba(16, 185, 129, 0)');

        ctx.fillStyle = gradient;
        ctx.beginPath();
        data.forEach((d, i) => {
            const x = xScale(i);
            const y = yScale(d.equity);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.lineTo(xScale(data.length - 1), h - padding.bottom);
        ctx.lineTo(padding.left, h - padding.bottom);
        ctx.closePath();
        ctx.fill();

        // Title
        ctx.fillStyle = '#f8fafc';
        ctx.font = 'bold 14px Inter, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('Equity Curve', padding.left, 15);

    }, [data, initialCapital, height, showGrid]);

    if (data.length === 0) {
        return (
            <div className="bg-slate-800 rounded-xl p-6 flex items-center justify-center" style={{ height }}>
                <p className="text-slate-400">No equity data available</p>
            </div>
        );
    }

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

export default EquityCurveChart;
