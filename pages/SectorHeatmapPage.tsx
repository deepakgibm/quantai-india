import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { TrendingUp, TrendingDown, ArrowLeft, Loader2, Search, ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';
import { getBgColor, getGlassColor, getPriceColor } from '../utils/price';

const SectorHeatmapPage: React.FC = () => {
    const [sectors, setSectors] = useState<any[]>([]);
    const [selectedSector, setSelectedSector] = useState<string | null>(null);
    const [stocks, setStocks] = useState<any[]>([]);
    const [loadingSectors, setLoadingSectors] = useState(true);
    const [loadingStocks, setLoadingStocks] = useState(false);
    const [showLongLoadingMsg, setShowLongLoadingMsg] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' | null }>({ key: 'change_pct', direction: 'desc' });

    useEffect(() => {
        fetchSectors();
    }, []);

    const fetchSectors = async () => {
        setLoadingSectors(true);
        const response = await api.getSectorHeatmap();
        if (response?.status === 'success' && Array.isArray(response.data)) {
            setSectors(response.data);
        } else {
            setSectors([]);
        }
        setLoadingSectors(false);
    };

    const handleSectorClick = async (sectorName: string) => {
        setSelectedSector(sectorName);
        setLoadingStocks(true);
        setShowLongLoadingMsg(false);
        setSearchTerm('');

        const timer = setTimeout(() => setShowLongLoadingMsg(true), 3000);

        try {
            const response = await api.getSectorStocks(sectorName);
            if (response?.status === 'success' && Array.isArray(response.stocks)) {
                setStocks(response.stocks);
            } else {
                setStocks([]);
            }
        } finally {
            clearTimeout(timer);
            setLoadingStocks(false);
            setShowLongLoadingMsg(false);
        }
    };

    const requestSort = (key: string) => {
        let direction: 'asc' | 'desc' | null = 'desc';
        if (sortConfig.key === key && sortConfig.direction === 'desc') {
            direction = 'asc';
        } else if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = null;
        }
        setSortConfig({ key, direction });
    };

    const sortedStocks = [...stocks].sort((a, b) => {
        if (!sortConfig.key || !sortConfig.direction) return 0;

        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];

        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
    });

    const filteredStocks = sortedStocks.filter(s =>
        (s.symbol?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
        (s.company_name?.toLowerCase() || '').includes(searchTerm.toLowerCase())
    );

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-display font-bold text-slate-900 dark:text-white">Sector Heatmap</h1>
                    <p className="text-slate-500 dark:text-slate-400">Live performance of major NSE sectors and their stocks</p>
                </div>
                {selectedSector && (
                    <button
                        onClick={() => setSelectedSector(null)}
                        className="flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors font-medium self-start"
                    >
                        <ArrowLeft size={18} /> Back to Sectors
                    </button>
                )}
            </div>

            {!selectedSector ? (
                // Sector Grid View
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
                    {loadingSectors ? (
                        [...Array(10)].map((_, i) => (
                            <div key={i} className="h-32 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-2xl border border-slate-200 dark:border-slate-700"></div>
                        ))
                    ) : sectors.length > 0 ? (
                        sectors.map((sector) => (
                            <div
                                key={sector.sector}
                                onClick={() => handleSectorClick(sector.sector)}
                                className={`relative h-full overflow-hidden p-6 rounded-2xl border transition-all duration-300 hover:scale-[1.02] hover:shadow-xl cursor-pointer ${getGlassColor(sector.change_pct)}`}
                            >
                                <div className="flex justify-between items-start mb-4">
                                    <h3 className="font-bold text-lg text-slate-800 dark:text-white uppercase tracking-wider">{sector.sector}</h3>
                                    {sector.change_pct > 0 ? (
                                        <TrendingUp size={20} className="text-green-500" />
                                    ) : (
                                        <TrendingDown size={20} className="text-red-500" />
                                    )}
                                </div>
                                <div className="flex items-end justify-between mt-2">
                                    <div className="flex flex-col">
                                        <span className={`text-3xl font-bold ${sector.change_pct > 0 ? 'text-green-600 dark:text-green-400' : sector.change_pct < 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-500'}`}>
                                            {sector.change_pct > 0 ? '+' : ''}{sector.change_pct}%
                                        </span>
                                        <span className="text-sm text-slate-400 font-medium">{sector.stock_count} Stocks</span>
                                    </div>
                                    <div className="text-brand-600 dark:text-brand-400 text-xs font-bold uppercase tracking-tighter">
                                        Stocks →
                                    </div>
                                </div>
                                {/* Intensity Bar */}
                                <div className="mt-4 w-full h-1.5 bg-slate-200 dark:bg-slate-700/50 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full transition-all duration-500 ${getBgColor(sector.change_pct)}`}
                                        style={{ width: `${Math.min(Math.abs(sector.change_pct) * 10, 100)}%` }}
                                    ></div>
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="col-span-full py-20 text-center bg-white dark:bg-slate-800 rounded-2xl border border-dashed border-slate-300 dark:border-slate-700">
                            <p className="text-slate-500">No sector data currently available from API.</p>
                        </div>
                    )}
                </div>
            ) : (
                // Stock Detail View
                <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
                    <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div>
                            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                {selectedSector} Stocks
                                <span className={`text-sm px-2 py-0.5 rounded-full ${loadingStocks ? 'bg-slate-100 dark:bg-slate-700' : 'bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 border border-brand-100 dark:border-brand-800'}`}>
                                    {loadingStocks ? '...' : filteredStocks.length} Stocks
                                </span>
                            </h2>
                        </div>
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                            <input
                                type="text"
                                placeholder="Search symbols..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="pl-10 pr-4 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 w-full sm:w-64 text-sm"
                            />
                        </div>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full text-left">
                            <thead className="bg-slate-50 dark:bg-slate-900/50 text-slate-500 dark:text-slate-400 text-xs font-bold uppercase tracking-wider">
                                <tr>
                                    <th className="px-6 py-4 cursor-pointer hover:text-brand-500 transition-colors" onClick={() => requestSort('symbol')}>
                                        <div className="flex items-center gap-2">
                                            Symbol
                                            {sortConfig.key === 'symbol' ? (
                                                sortConfig.direction === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                                            ) : <ChevronsUpDown size={14} className="opacity-30" />}
                                        </div>
                                    </th>
                                    <th className="px-6 py-4 cursor-pointer hover:text-brand-500 transition-colors" onClick={() => requestSort('company_name')}>
                                        <div className="flex items-center gap-2">
                                            Company Name
                                            {sortConfig.key === 'company_name' ? (
                                                sortConfig.direction === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                                            ) : <ChevronsUpDown size={14} className="opacity-30" />}
                                        </div>
                                    </th>
                                    <th className="px-6 py-4 text-right cursor-pointer hover:text-brand-500 transition-colors" onClick={() => requestSort('ltp')}>
                                        <div className="flex items-center justify-end gap-2">
                                            LTP
                                            {sortConfig.key === 'ltp' ? (
                                                sortConfig.direction === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                                            ) : <ChevronsUpDown size={14} className="opacity-30" />}
                                        </div>
                                    </th>
                                    <th className="px-6 py-4 text-right cursor-pointer hover:text-brand-500 transition-colors" onClick={() => requestSort('change_pct')}>
                                        <div className="flex items-center justify-end gap-2">
                                            Change %
                                            {sortConfig.key === 'change_pct' ? (
                                                sortConfig.direction === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                                            ) : <ChevronsUpDown size={14} className="opacity-30" />}
                                        </div>
                                    </th>
                                    <th className="px-6 py-4 text-center cursor-pointer hover:text-brand-500 transition-colors" onClick={() => requestSort('change_pct')}>
                                        <div className="flex items-center justify-center gap-2">
                                            Trend
                                            {sortConfig.key === 'change_pct' ? (
                                                sortConfig.direction === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                                            ) : <ChevronsUpDown size={14} className="opacity-30" />}
                                        </div>
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                                {loadingStocks ? (
                                    <>
                                        {showLongLoadingMsg && (
                                            <tr>
                                                <td colSpan={5} className="px-6 py-4 text-center bg-brand-50/30 dark:bg-brand-900/10 border-b border-brand-100/50 dark:border-brand-900/20">
                                                    <div className="flex items-center justify-center gap-2 text-brand-600 dark:text-brand-400 font-medium animate-pulse">
                                                        <Loader2 size={16} className="animate-spin" />
                                                        Fetching sector stocks, please wait...
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                        {[...Array(8)].map((_, i) => (
                                            <tr key={i} className="animate-pulse">
                                                <td colSpan={5} className="px-6 py-6">
                                                    <div className="h-4 bg-slate-100 dark:bg-slate-800 rounded w-full"></div>
                                                </td>
                                            </tr>
                                        ))}
                                    </>
                                ) : filteredStocks.length > 0 ? (
                                    filteredStocks.map((stock) => (
                                        <tr key={stock.symbol} className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors group">
                                            <td className="px-6 py-4">
                                                <span className="font-bold text-slate-900 dark:text-white">{stock.symbol}</span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className="text-sm text-slate-500 dark:text-slate-400 truncate max-w-[200px] block">{stock.company_name}</span>
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <span className={`font-mono font-bold ${getPriceColor(stock.change_pct)}`}>
                                                    ₹{(stock.ltp || stock.last_price || 0).toLocaleString()}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <span className={`font-bold px-2 py-1 rounded-lg ${stock.change_pct > 0 ? 'text-green-600 bg-green-50 dark:bg-green-900/20' : stock.change_pct < 0 ? 'text-red-600 bg-red-50 dark:bg-red-900/20' : 'text-slate-500 bg-slate-50'}`}>
                                                    {stock.change_pct > 0 ? '+' : ''}{stock.change_pct}%
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-center">
                                                {stock.change_pct > 0 ? (
                                                    <TrendingUp size={16} className="text-green-500 mx-auto" />
                                                ) : stock.change_pct < 0 ? (
                                                    <TrendingDown size={16} className="text-red-500 mx-auto" />
                                                ) : (
                                                    <span className="text-slate-300 mx-auto">-</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan={5} className="px-6 py-12 text-center text-slate-500 italic">
                                            {searchTerm ? `No stocks matching "${searchTerm}"` : 'No stocks found for this sector.'}
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SectorHeatmapPage;
