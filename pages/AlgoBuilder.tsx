import React from 'react';
import { Plus, Play, Save, Trash2 } from 'lucide-react';

const AlgoBuilder: React.FC = () => {
  return (
    <div className="h-[calc(100vh-140px)] flex flex-col">
      <div className="flex items-center justify-between mb-4">
         <div>
            <h2 className="text-xl font-bold text-slate-800 dark:text-white">Algorithm Builder</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">Drag and drop logic to create custom strategies</p>
         </div>
         <div className="flex gap-2">
            <button className="px-4 py-2 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 rounded-lg font-medium flex items-center gap-2 shadow-sm">
               <Save size={18} /> Save Strategy
            </button>
            <button className="px-4 py-2 bg-brand-600 text-white rounded-lg font-medium flex items-center gap-2 shadow-lg shadow-brand-500/30">
               <Play size={18} /> Backtest
            </button>
         </div>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden">
         {/* Toolbox */}
         <div className="w-64 bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-200 dark:border-slate-700 overflow-y-auto">
            <h3 className="font-bold text-xs text-slate-400 uppercase mb-4">Logic Blocks</h3>
            
            <div className="space-y-3">
               <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-900/50 rounded-lg cursor-move hover:shadow-md transition-shadow">
                  <span className="font-bold text-sm text-blue-700 dark:text-blue-400">Price Condition</span>
                  <p className="text-xs text-blue-500 dark:text-blue-300 mt-1">Close &gt; Open</p>
               </div>
               <div className="p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-900/50 rounded-lg cursor-move hover:shadow-md transition-shadow">
                  <span className="font-bold text-sm text-purple-700 dark:text-purple-400">Indicator</span>
                  <p className="text-xs text-purple-500 dark:text-purple-300 mt-1">RSI, MACD, EMA</p>
               </div>
               <div className="p-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-100 dark:border-orange-900/50 rounded-lg cursor-move hover:shadow-md transition-shadow">
                  <span className="font-bold text-sm text-orange-700 dark:text-orange-400">Time Filter</span>
                  <p className="text-xs text-orange-500 dark:text-orange-300 mt-1">Between 09:30 - 11:00</p>
               </div>
               <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-100 dark:border-green-900/50 rounded-lg cursor-move hover:shadow-md transition-shadow">
                  <span className="font-bold text-sm text-green-700 dark:text-green-400">Action</span>
                  <p className="text-xs text-green-500 dark:text-green-300 mt-1">Buy / Sell / Square Off</p>
               </div>
            </div>
         </div>

         {/* Canvas */}
         <div className="flex-1 bg-slate-100 dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 relative bg-[url('https://www.transparenttextures.com/patterns/grid-me.png')]">
            {/* Mock Flowchart */}
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-full h-full p-10 flex flex-col items-center gap-8">
               
               <div className="w-64 p-4 bg-white dark:bg-slate-800 rounded-xl shadow-lg border-l-4 border-orange-500 flex items-center justify-between">
                  <div>
                     <span className="text-xs font-bold text-slate-400">TRIGGER</span>
                     <p className="font-bold text-slate-800 dark:text-white">Every 1 Minute</p>
                  </div>
                  <SettingsIcon size={16} className="text-slate-400" />
               </div>

               <div className="h-8 w-0.5 bg-slate-300 dark:bg-slate-600"></div>

               <div className="w-64 p-4 bg-white dark:bg-slate-800 rounded-xl shadow-lg border-l-4 border-purple-500 flex items-center justify-between">
                  <div>
                     <span className="text-xs font-bold text-slate-400">CONDITION</span>
                     <p className="font-bold text-slate-800 dark:text-white">RSI(14) &lt; 30</p>
                  </div>
                  <SettingsIcon size={16} className="text-slate-400" />
               </div>

               <div className="h-8 w-0.5 bg-slate-300 dark:bg-slate-600"></div>

               <div className="w-64 p-4 bg-white dark:bg-slate-800 rounded-xl shadow-lg border-l-4 border-green-500 flex items-center justify-between">
                  <div>
                     <span className="text-xs font-bold text-slate-400">ACTION</span>
                     <p className="font-bold text-slate-800 dark:text-white">Buy Market Order</p>
                  </div>
                  <SettingsIcon size={16} className="text-slate-400" />
               </div>

               <button className="p-2 rounded-full bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors">
                  <Plus size={24} className="text-slate-500 dark:text-slate-400" />
               </button>

            </div>
         </div>
      </div>
    </div>
  );
};

function SettingsIcon({size, className}: {size: number, className?: string}) {
    return <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
}

export default AlgoBuilder;