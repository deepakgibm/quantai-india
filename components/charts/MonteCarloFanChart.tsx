import React, { useEffect, useRef } from 'react';

interface MonteCarloFanChartProps {
    simulations: number[][]; // Array of equity paths
    dates?: string[];
    height?: number;
    percentiles?: number[]; // e.g., [5, 25, 50, 75, 95]
}

const MonteCarloFanChart: React.FC<MonteCarloFanChartProps> = ({
    simulations,
    dates,
    height = 350,
    percentiles = [5, 25, 50, 75, 95]
}) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        if (!canvasRef.current || simulations.length === 0) return;

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
        const padding = { top: 30, right: 80, bottom: 40, left: 80 };
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = h - padding.top - padding.bottom;

        // Clear
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(0, 0, width, h);

        // Calculate percentile bands at each time step
        const numSteps = simulations[0]?.length || 0;
        const percentileBands: { [key: number]: number[] } = {};

        percentiles.forEach(p => {
            percentileBands[p] = [];
        });

        for (let step = 0; step < numSteps; step++) {
            const valuesAtStep = simulations.map(sim => sim[step]).sort((a, b) => a - b);

            percentiles.forEach(p => {
                const idx = Math.floor((p / 100) * valuesAtStep.length);
                percentileBands[p].push(valuesAtStep[idx]);
            });
        }

        // Get min/max for scaling
        const allValues = Object.values(percentileBands).flat();
        const minVal = Math.min(...allValues) * 0.95;
        const maxVal = Math.max(...allValues) * 1.05;

        // Scale functions
        const xScale = (i: number) => padding.left + (i / (numSteps - 1)) * chartWidth;
        const yScale = (val: number) => padding.top + chartHeight - ((val - minVal) / (maxVal - minVal)) * chartHeight;

        // Draw grid
        ctx.strokeStyle = '#334155';
        ctx.lineWidth = 0.5;
        for (let i = 0; i <= 5; i++) {
            const y = padding.top + (i / 5) * chartHeight;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(width - padding.right, y);
            ctx.stroke();

            const value = maxVal - (i / 5) * (maxVal - minVal);
            ctx.fillStyle = '#94a3b8';
            ctx.font = '10px Inter, sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText(`₹${(value / 100000).toFixed(0)}L`, padding.left - 8, y + 3);
        }

        // Draw fan bands (outer to inner)
        const bandColors = [
            { outer: 5, inner: 95, fill: 'rgba(59, 130, 246, 0.1)' },
            { outer: 25, inner: 75, fill: 'rgba(59, 130, 246, 0.2)' },
        ];

        bandColors.forEach(({ outer, inner, fill }) => {
            ctx.fillStyle = fill;
            ctx.beginPath();

            // Draw upper bound (outer percentile low to high x)
            for (let i = 0; i < numSteps; i++) {
                const x = xScale(i);
                const y = yScale(percentileBands[inner][i]);
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }

            // Draw lower bound (inner percentile high to low x)
            for (let i = numSteps - 1; i >= 0; i--) {
                const x = xScale(i);
                const y = yScale(percentileBands[outer][i]);
                ctx.lineTo(x, y);
            }

            ctx.closePath();
            ctx.fill();
        });

        // Draw percentile lines
        const lineColors: { [key: number]: { color: string; width: number; dash: number[] } } = {
            5: { color: '#3b82f6', width: 1, dash: [4, 4] },
            25: { color: '#60a5fa', width: 1, dash: [2, 2] },
            50: { color: '#f59e0b', width: 2.5, dash: [] },
            75: { color: '#60a5fa', width: 1, dash: [2, 2] },
            95: { color: '#3b82f6', width: 1, dash: [4, 4] },
        };

        percentiles.forEach(p => {
            const { color, width: lineWidth, dash } = lineColors[p];
            ctx.strokeStyle = color;
            ctx.lineWidth = lineWidth;
            ctx.setLineDash(dash);

            ctx.beginPath();
            percentileBands[p].forEach((val, i) => {
                const x = xScale(i);
                const y = yScale(val);
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            });
            ctx.stroke();
            ctx.setLineDash([]);
        });

        // Legend
        const legendY = h - 15;
        const legendItems = [
            { label: '5th-95th', color: 'rgba(59, 130, 246, 0.3)' },
            { label: '25th-75th', color: 'rgba(59, 130, 246, 0.5)' },
            { label: 'Median', color: '#f59e0b' }
        ];

        let legendX = padding.left;
        ctx.font = '11px Inter, sans-serif';

        legendItems.forEach(item => {
            ctx.fillStyle = item.color;
            ctx.fillRect(legendX, legendY - 8, 16, 8);

            ctx.fillStyle = '#94a3b8';
            ctx.textAlign = 'left';
            ctx.fillText(item.label, legendX + 20, legendY);
            legendX += 90;
        });

        // Title
        ctx.fillStyle = '#f8fafc';
        ctx.font = 'bold 14px Inter, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('Monte Carlo Simulation (10,000 paths)', padding.left, 20);

        // Final value stats
        const finalPercentiles = percentiles.map(p => ({
            percentile: p,
            value: percentileBands[p][numSteps - 1]
        }));

        ctx.textAlign = 'left';
        ctx.font = '10px Inter, sans-serif';
        let statY = padding.top + 20;

        finalPercentiles.forEach(({ percentile, value }) => {
            ctx.fillStyle = percentile === 50 ? '#f59e0b' : '#94a3b8';
            ctx.fillText(`P${percentile}: ₹${(value / 100000).toFixed(1)}L`, width - padding.right + 10, statY);
            statY += 18;
        });

    }, [simulations, height, percentiles]);

    if (simulations.length === 0) {
        return (
            <div className="bg-slate-800 rounded-xl p-6 flex items-center justify-center" style={{ height }}>
                <p className="text-slate-400">Run Monte Carlo simulation to see results</p>
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

export default MonteCarloFanChart;
