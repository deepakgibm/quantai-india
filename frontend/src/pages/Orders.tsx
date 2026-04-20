import React, { useState, useMemo, useEffect } from 'react';
import { Order } from '../types';
import { XCircle, Clock, CheckCircle, Search, Filter, ArrowUp, ArrowDown } from 'lucide-react';
import { api } from '../services/api';

const Orders: React.FC = () => {
   const [orders, setOrders] = useState<Order[]>([]);

   useEffect(() => {
      // Fetch orders from API on mount
      api.getOrders().then(data => {
         if (Array.isArray(data)) setOrders(data);
         else setOrders([]);
      });
   }, []);

   // Filter & Sort State
   const [searchTerm, setSearchTerm] = useState('');
   const [typeFilter, setTypeFilter] = useState<'ALL' | 'BUY' | 'SELL'>('ALL');
   const [statusFilter, setStatusFilter] = useState<'ALL' | 'OPEN' | 'CLOSED'>('ALL');
   const [algoFilter, setAlgoFilter] = useState<string>('ALL');
   const [sortConfig, setSortConfig] = useState<{ key: keyof Order; direction: 'asc' | 'desc' } | null>(null);

   // Derived Options
   const uniqueAlgos = useMemo(() => {
      const algos = Array.from(new Set(orders.map(o => o.algo)));
      return ['ALL', ...algos];
   }, [orders]);

   // Sorting Handler
   const handleSort = (key: keyof Order) => {
      let direction: 'asc' | 'desc' = 'asc';
      if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
         direction = 'desc';
      }
      setSortConfig({ key, direction });
   };

   // Filter & Sort Logic
   const filteredOrders = useMemo(() => {
      let result = [...orders];

      // 1. Filter
      if (searchTerm) {
         const lower = searchTerm.toLowerCase();
         result = result.filter(o =>
            o.stock.toLowerCase().includes(lower) ||
            o.id.toLowerCase().includes(lower)
         );
      }
      if (typeFilter !== 'ALL') {
         result = result.filter(o => o.type === typeFilter);
      }
      if (statusFilter !== 'ALL') {
         result = result.filter(o => o.status === statusFilter);
      }
      if (algoFilter !== 'ALL') {
         result = result.filter(o => o.algo === algoFilter);
      }

      // 2. Sort
      if (sortConfig) {
         result.sort((a, b) => {
            const aVal = a[sortConfig.key];
            const bVal = b[sortConfig.key];

            if (aVal === bVal) return 0;

            // Handle null/undefined safe sorting
            if (aVal === undefined || aVal === null) return 1;
            if (bVal === undefined || bVal === null) return -1;

            if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
            if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
            return 0;
         });
      }

      return result;
   }, [orders, searchTerm, typeFilter, statusFilter, algoFilter, sortConfig]);

   // Helper for Sort Icons
   const SortIcon = ({ columnKey }: { columnKey: keyof Order }) => {
      if (sortConfig?.key !== columnKey) return <div className="w-4 h-4 opacity-0 group-hover:opacity-30 transition-opacity"><ArrowUp size={14} /></div>;
      return sortConfig.direction === 'asc' ? <ArrowUp size={14} className="text-brand-600" /> : <ArrowDown size={14} className="text-brand-600" />;
   };

   return (
      <div className="space-y-6">
         <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white dark:bg-slate-800 p-6 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
            <div>
               <h2 className="text-xl font-bold text-slate-800 dark:text-white">Orders & Positions</h2>
               <p className="text-sm text-slate-500 dark:text-slate-400">Manage your automated and manual trades</p>
            </div>
            <div className="flex items-center gap-3">
               <div className="flex items-center gap-2 px-4 py-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-100 dark:border-yellow-900/50 text-yellow-700 dark:text-yellow-500 text-sm font-medium">
                  <Clock size={16} />
                  Auto Square-off: 3:15 PM
                  <div className="relative inline-block w-8 h-4 rounded-full cursor-pointer transition-colors ease-in-out duration-200 bg-green-500 ml-2">
                     <span className="absolute left-4 top-0.5 bg-white w-3 h-3 rounded-full transition-transform duration-200 transform"></span>
                  </div>
               </div>
               <button className="px-4 py-2 bg-red-50 dark:bg-red-900/20 text-red-600 border border-red-100 dark:border-red-900/50 hover:bg-red-100 rounded-lg font-medium text-sm flex items-center gap-2">
                  <XCircle size={16} /> Close All Positions
               </button>
            </div>
         </div>

         {/* Filters Bar */}
         <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="relative">
               <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search size={18} className="text-slate-400" />
               </div>
               <input
                  type="text"
                  placeholder="Search Symbol or ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-brand-500 outline-none text-slate-800 dark:text-slate-200 transition-all"
               />
            </div>

            <div>
               <select
                  value={algoFilter}
                  onChange={(e) => setAlgoFilter(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-brand-500 outline-none text-slate-800 dark:text-slate-200 cursor-pointer"
               >
                  {uniqueAlgos.map(algo => (
                     <option key={algo} value={algo}>{algo === 'ALL' ? 'All Algorithms' : algo}</option>
                  ))}
               </select>
            </div>

            <div>
               <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value as any)}
                  className="w-full px-4 py-2.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-brand-500 outline-none text-slate-800 dark:text-slate-200 cursor-pointer"
               >
                  <option value="ALL">All Types</option>
                  <option value="BUY">Buy Orders</option>
                  <option value="SELL">Sell Orders</option>
               </select>
            </div>

            <div>
               <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as any)}
                  className="w-full px-4 py-2.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-brand-500 outline-none text-slate-800 dark:text-slate-200 cursor-pointer"
               >
                  <option value="ALL">All Status</option>
                  <option value="OPEN">Open Positions</option>
                  <option value="CLOSED">Closed Positions</option>
               </select>
            </div>
         </div>

         <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="overflow-x-auto">
               <table className="w-full text-left">
                  <thead>
                     <tr className="bg-slate-50 dark:bg-slate-900/50 text-slate-500 dark:text-slate-400 text-xs uppercase tracking-wider border-b border-slate-200 dark:border-slate-700">
                        {[
                           { key: 'timestamp', label: 'Time' },
                           { key: 'stock', label: 'Symbol' },
                           { key: 'type', label: 'Side' },
                           { key: 'quantity', label: 'Qty' },
                           { key: 'entryPrice', label: 'Entry' },
                           { key: 'exitPrice', label: 'LTP/Exit' },
                           { key: 'pnl', label: 'P&L' },
                           { key: 'algo', label: 'Algo' },
                           { key: 'status', label: 'Status' },
                        ].map((col) => (
                           <th
                              key={col.key}
                              onClick={() => handleSort(col.key as keyof Order)}
                              className="p-4 font-semibold cursor-pointer group hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors select-none"
                           >
                              <div className="flex items-center gap-1">
                                 {col.label}
                                 <SortIcon columnKey={col.key as keyof Order} />
                              </div>
                           </th>
                        ))}
                        <th className="p-4 font-semibold text-right">Action</th>
                     </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                     {filteredOrders.length === 0 ? (
                        <tr>
                           <td colSpan={10} className="p-8 text-center text-slate-500 dark:text-slate-400">
                              <div className="flex flex-col items-center gap-2">
                                 <Filter size={24} className="opacity-50" />
                                 <p>No orders found matching your filters.</p>
                                 <button
                                    onClick={() => { setSearchTerm(''); setTypeFilter('ALL'); setStatusFilter('ALL'); setAlgoFilter('ALL'); }}
                                    className="text-brand-600 hover:underline text-sm mt-2"
                                 >
                                    Clear all filters
                                 </button>
                              </div>
                           </td>
                        </tr>
                     ) : (
                        filteredOrders.map((order) => (
                           <tr key={order.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                              <td className="p-4 text-sm font-mono text-slate-600 dark:text-slate-400">{order.timestamp}</td>
                              <td className="p-4 font-bold text-slate-800 dark:text-white">{order.stock}</td>
                              <td className="p-4">
                                 <span className={`text-xs font-bold px-2 py-1 rounded ${order.type === 'BUY' ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400' : 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400'}`}>
                                    {order.type}
                                 </span>
                              </td>
                              <td className="p-4 text-sm text-slate-800 dark:text-slate-300">{order.quantity}</td>
                              <td className="p-4 text-sm text-slate-600 dark:text-slate-400">₹{order.entryPrice}</td>
                              <td className="p-4 text-sm text-slate-600 dark:text-slate-400">{order.status === 'OPEN' ? '₹' + (order.entryPrice * 1.01).toFixed(2) : '₹' + order.exitPrice}</td>
                              <td className={`p-4 text-sm font-bold ${order.pnl && order.pnl > 0 ? 'text-green-500' : 'text-red-500'}`}>
                                 {order.pnl ? (order.pnl > 0 ? '+' : '') + '₹' + order.pnl : '-'}
                              </td>
                              <td className="p-4 text-sm text-slate-500">
                                 <span className="flex items-center gap-1"><CheckCircle size={12} className="text-brand-500" /> {order.algo}</span>
                              </td>
                              <td className="p-4">
                                 <span className={`text-xs font-bold px-2 py-1 rounded-full ${order.status === 'OPEN' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'}`}>
                                    {order.status}
                                 </span>
                              </td>
                              <td className="p-4 text-right">
                                 {order.status === 'OPEN' && (
                                    <button className="text-xs bg-slate-100 hover:bg-red-100 hover:text-red-600 text-slate-600 px-3 py-1.5 rounded transition-colors border border-slate-200 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-red-900/30 dark:hover:text-red-400">
                                       Square Off
                                    </button>
                                 )}
                              </td>
                           </tr>
                        ))
                     )}
                  </tbody>
               </table>
            </div>
         </div>
      </div>
   );
};

export default Orders;
