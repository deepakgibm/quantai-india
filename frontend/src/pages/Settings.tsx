import React from 'react';
import { Settings as SettingsIcon, User, Bell, Database, Key, Mail, Send } from 'lucide-react';

const Settings: React.FC = () => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
      {/* Sidebar Nav */}
      <div className="col-span-1 bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden h-fit">
         <nav className="flex flex-col p-2">
            <button className="flex items-center gap-3 px-4 py-3 rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400 font-medium text-left">
               <Key size={18} /> Broker & API
            </button>
            <button className="flex items-center gap-3 px-4 py-3 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-left">
               <Database size={18} /> AI Model Config
            </button>
            <button className="flex items-center gap-3 px-4 py-3 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-left">
               <Bell size={18} /> Notifications
            </button>
            <button className="flex items-center gap-3 px-4 py-3 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-left">
               <User size={18} /> Profile
            </button>
         </nav>
      </div>

      {/* Content */}
      <div className="col-span-1 md:col-span-3 space-y-6">
         {/* Broker Integration */}
         <div className="bg-white dark:bg-slate-800 rounded-2xl p-8 shadow-sm border border-slate-200 dark:border-slate-700">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-6">Broker Integration</h2>
            
            <div className="flex items-center justify-between p-4 border border-green-200 bg-green-50 dark:bg-green-900/10 dark:border-green-900/30 rounded-xl mb-6">
               <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-white rounded-lg flex items-center justify-center shadow-sm">
                     {/* Placeholder Upstox Logo */}
                     <div className="w-6 h-6 bg-[#5d3d90] rounded-sm"></div>
                  </div>
                  <div>
                     <h4 className="font-bold text-slate-900 dark:text-white">Upstox Pro</h4>
                     <p className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
                        ● Connected (Token Exp: 4h 12m)
                     </p>
                  </div>
               </div>
               <button className="px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors">
                  Disconnect
               </button>
            </div>

            <div className="space-y-4">
               <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">API Key</label>
                  <div className="flex gap-2">
                     <input type="password" value="************************" readOnly className="flex-1 px-4 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-500" />
                     <button className="px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-lg font-medium">Regenerate</button>
                  </div>
               </div>
               <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">API Secret</label>
                  <input type="password" value="************************" readOnly className="w-full px-4 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-500" />
               </div>
            </div>
         </div>

         {/* AI Settings */}
         <div className="bg-white dark:bg-slate-800 rounded-2xl p-8 shadow-sm border border-slate-200 dark:border-slate-700">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-6">AI Settings</h2>
            <div className="space-y-4">
               <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Reasoning Model</label>
                  <select className="w-full px-4 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 outline-none focus:ring-2 focus:ring-brand-500 text-slate-800 dark:text-slate-200">
                     <option>GPT-4o (Recommended)</option>
                     <option>Gemini 1.5 Pro</option>
                     <option>Claude 3 Opus</option>
                     <option>Llama 3 (Local - Fast)</option>
                  </select>
               </div>
               <div>
                  <div className="flex justify-between mb-1">
                     <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Creativity (Temperature)</label>
                     <span className="text-sm text-slate-500">0.7</span>
                  </div>
                  <input type="range" min="0" max="1" step="0.1" className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-brand-600" />
               </div>
            </div>
         </div>

         {/* Notification Settings */}
         <div className="bg-white dark:bg-slate-800 rounded-2xl p-8 shadow-sm border border-slate-200 dark:border-slate-700">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-6">Notification Settings</h2>
            
            {/* Channels */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
               <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                     <div className="p-2 bg-blue-100 dark:bg-blue-900/30 text-blue-600 rounded-lg">
                        <Mail size={20} />
                     </div>
                     <div>
                        <p className="font-bold text-sm text-slate-800 dark:text-white">Email Alerts</p>
                        <p className="text-xs text-slate-500">arjun@example.com</p>
                     </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                     <input type="checkbox" className="sr-only peer" defaultChecked />
                     <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-brand-300 dark:peer-focus:ring-brand-800 rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-brand-600"></div>
                  </label>
               </div>

               <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                     <div className="p-2 bg-sky-100 dark:bg-sky-900/30 text-sky-600 rounded-lg">
                        <Send size={20} className="ml-0.5" /> 
                     </div>
                     <div>
                        <p className="font-bold text-sm text-slate-800 dark:text-white">Telegram Bot</p>
                        <p className="text-xs text-slate-500">Not Connected</p>
                     </div>
                  </div>
                  <button className="text-xs font-bold text-brand-600 hover:underline px-2 py-1 rounded hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors">Connect</button>
               </div>
            </div>

            {/* Preferences */}
            <div className="space-y-5">
               <h3 className="font-bold text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider">Alert Preferences</h3>
               
               {[
                  { title: 'Trade Executions', desc: 'Instant alerts when AI places a buy or sell order.' },
                  { title: 'Significant Market Events', desc: 'NIFTY 50 large movements (>1%) or high VIX alerts.' },
                  { title: 'AI Strategy Insights', desc: 'Daily pre-market analysis and end-of-day summaries.' }
               ].map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-700 last:border-0">
                     <div className="pr-4">
                        <p className="font-medium text-sm text-slate-800 dark:text-slate-200">{item.title}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{item.desc}</p>
                     </div>
                     <label className="relative inline-flex items-center cursor-pointer flex-shrink-0">
                        <input type="checkbox" className="sr-only peer" defaultChecked />
                        <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all dark:border-gray-600 peer-checked:bg-brand-600"></div>
                     </label>
                  </div>
               ))}
            </div>
         </div>
      </div>
    </div>
  );
};

export default Settings;