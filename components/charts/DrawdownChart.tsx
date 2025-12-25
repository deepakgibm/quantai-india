import React, { useEffect, useRef } from 'react';

interface DrawdownChartProps {
    data: { date: string; drawdown: number }[];
    height?: number;
}

const DrawdownChart: React.FC<DrawdownChartProps> = ({
    data,
    height = 200
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
        const padding = { top: 20, right: 60, bottom: 30, left: 60 };
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = h - padding.top - padding.bottom;

        // Clear
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(0, 0, width, h);

        // Get min drawdown (most negative)
        const drawdowns = data.map(d => d.drawdown);
        const minDD = Math.min(...drawdowns) * 1.1;
        const maxDD = 0;

        // Scale functions
        const xScale = (i: number) => padding.left + (i / (data.length - 1)) * chartWidth;
        const yScale = (val: number) => padding.top + ((val - maxDD) / (minDD - maxDD)) * chartHeight;

        // Draw zero line
        ctx.strokeStyle = '#64748b';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding.left, yScale(0));
        ctx.lineTo(width - padding.right, yScale(0));
        ctx.stroke();

        // Draw -10%, -20%, -30% lines
        [-0.1, -0.2, -0.3].forEach(level => {
            if (level >= minDD) {
                ctx.strokeStyle = '#334155';
                ctx.setLineDash([3, 3]);
                ctx.beginPath();
                ctx.moveTo(padding.left, yScale(level));
                ctx.lineTo(width - padding.right, yScale(level));
                ctx.stroke();
                ctx.setLineDash([]);

                // Label
                ctx.fillStyle = '#94a3b8';
                ctx.font = '10px Inter, sans-serif';
                ctx.textAlign = 'right';
                ctx.fillText(`${(level * 100).toFixed(0)}%`, padding.left - 8, yScale(level) + 3);
            }
        });

        // Fill drawdown area
        const gradient = ctx.createLinearGradient(0, padding.top, 0, h - padding.bottom);
        gradient.addColorStop(0, 'rgba(239, 68, 68, 0.1)');
        gradient.addColorStop(1, 'rgba(239, 68, 68, 0.4)');

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.moveTo(padding.left, yScale(0));
        data.forEach((d, i) => {
            ctx.lineTo(xScale(i), yScale(d.drawdown));
        });
        ctx.lineTo(xScale(data.length - 1), yScale(0));
        ctx.closePath();
        ctx.fill();

        // Draw drawdown line
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2;
        ctx.beginPath();
        data.forEach((d, i) => {
            const x = xScale(i);
            const y = yScale(d.drawdown);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();

        // Max drawdown marker
        const maxDDIdx = drawdowns.indexOf(Math.min(...drawdowns));
        if (maxDDIdx >= 0) {
            const x = xScale(maxDDIdx);
            const y = yScale(data[maxDDIdx].drawdown);

            ctx.fillStyle = '#ef4444';
            ctx.beginPath();
            ctx.arc(x, y, 5, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = '#f8fafc';
            ctx.font = 'bold 10px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(`Max: ${(data[maxDDIdx].drawdown * 100).toFixed(1)}%`, x, y - 10);
        }

        // Title
        ctx.fillStyle = '#f8fafc';
        ctx.font = 'bold 14px Inter, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('Drawdown', padding.left, 15);

    }, [data, height]);

    if (data.length === 0) {
        return (
            <div className="bg-slate-800 rounded-xl p-6 flex items-center justify-center" style={{ height }}>
                <p className="text-slate-400">No drawdown data available</p>
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

export default DrawdownChart;
