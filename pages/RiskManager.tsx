import React, { useState } from 'react';
import { ShieldAlert, Lock, PieChart as PieIcon } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const RiskManager: React.FC = () => {
  const [maxLoss, setMaxLoss] = useState(5000);
  const [capital, setCapital] = useState(500000);
  const [riskPerTrade, setRiskPerTrade] = useState(1);

  const data = [
    { name: 'Free Margin', value: 300000, color: '#10b981' },
    { name: 'Used Margin', value: 200000, color: '#3b82f6' },
  ];

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/10 dark:to-orange-900/10 p-6 rounded-2xl border border-red-100 dark:border-red-900/30 flex items-start gap-4">
         <div className="p-3 bg-white dark:bg-slate-800 rounded-xl shadow-sm text-red-500">
            <ShieldAlert size={24} />
         </div>
         <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Risk Guardian Active</h2>
            <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">
               Your account is protected by AI-driven stops. Trading will automatically halt if daily loss exceeds <span className="font-bold text-red-600">₹{maxLoss.toLocaleString()}</span>.
            </p>
         </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
         {/* Risk Controls */}
         <div className="bg-white dark:bg-slate-800 rounded-2xl p-8 shadow-sm border border-slate-200 dark:border-slate-700 space-y-8">
            <h3 className="font-bold text-lg flex items-center gap-2 text-slate-800 dark:text-white">
               <Lock size={18} /> Configuration
            </h3>

            <div>
               <div className="flex justify-between mb-2">
                  <label className="text-sm font-medium text-slate-600 dark:text-slate-300">Total Allocated Capital</label>
                  <span className="font-bold text-brand-600">₹{capital.toLocaleString()}</span>
               </div>
               <input 
                  type="range" 
                  min="100000" 
                  max="2000000" 
                  step="50000"
                  value={capital} 
                  onChange={(e) => setCapital(parseInt(e.target.value))}
                  className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-brand-600"
               />
            </div>

            <div>
               <div className="flex justify-between mb-2">
                  <label className="text-sm font-medium text-slate-600 dark:text-slate-300">Max Daily Loss Limit</label>
                  <span className="font-bold text-red-500">₹{maxLoss.toLocaleString()}</span>
               </div>
               <input 
                  type="range" 
                  min="1000" 
                  max="50000" 
                  step="1000"
                  value={maxLoss} 
                  onChange={(e) => setMaxLoss(parseInt(e.target.value))}
                  className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-red-500"
               />
            </div>

            <div>
               <div className="flex justify-between mb-2">
                  <label className="text-sm font-medium text-slate-600 dark:text-slate-300">Risk Per Trade</label>
                  <span className="font-bold text-orange-500">{riskPerTrade}%</span>
               </div>
               <input 
                  type="range" 
                  min="0.5" 
                  max="5" 
                  step="0.5"
                  value={riskPerTrade} 
                  onChange={(e) => setRiskPerTrade(parseFloat(e.target.value))}
                  className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-orange-500"
               />
            </div>

            <div className="flex items-center justify-between py-4 border-t border-slate-100 dark:border-slate-700 mt-4">
               <div>
                  <p className="font-medium text-slate-700 dark:text-slate-200">Auto-Hedge Overnight</p>
                  <p className="text-xs text-slate-500">Buy PE options for overnight holdings</p>
               </div>
               <div className="relative inline-block w-12 h-6 rounded-full bg-slate-200 dark:bg-slate-600 cursor-pointer">
                   <span className="absolute left-1 top-1 bg-white w-4 h-4 rounded-full shadow transition-transform duration-200"></span>
               </div>
            </div>
         </div>

         {/* Visuals */}
         <div className="bg-white dark:bg-slate-800 rounded-2xl p-8 shadow-sm border border-slate-200 dark:border-slate-700 flex flex-col items-center justify-center">
             <h3 className="font-bold text-lg mb-6 text-slate-800 dark:text-white w-full text-left">Capital Exposure</h3>
             <div className="h-64 w-full relative">
               <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                     <Pie
                        data={data}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                        stroke="none"
                     >
                        {data.map((entry, index) => (
                           <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                     </Pie>
                     <Tooltip 
                        contentStyle={{ backgroundColor: '#fff', borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                        itemStyle={{ color: '#1e293b' }}
                     />
                  </PieChart>
               </ResponsiveContainer>
               {/* Center Text */}
               <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
                  <p className="text-xs text-slate-500 uppercase">Used</p>
                  <p className="text-xl font-bold text-slate-800 dark:text-white">40%</p>
               </div>
             </div>
             <div className="flex gap-6 mt-4">
                {data.map((item) => (
                   <div key={item.name} className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
                      <span className="text-sm text-slate-600 dark:text-slate-400">{item.name}</span>
                   </div>
                ))}
             </div>
         </div>
      </div>
    </div>
  );
};

export default RiskManager;