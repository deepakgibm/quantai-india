import React from 'react';
import { Calendar } from 'lucide-react';
import { useGlobalSymbol } from '../contexts/GlobalSymbolContext';

export const DayFilter: React.FC = () => {
  const { selectedDays, setSelectedDays } = useGlobalSymbol();

  const options = [7, 15, 30, 45, 60];

  return (
    <div className="flex items-center gap-2">
      <Calendar className="text-slate-400 dark:text-slate-500" size={16} />
      <select
        value={selectedDays}
        onChange={e => setSelectedDays(parseInt(e.target.value, 10))}
        className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 text-xs font-semibold focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 dark:focus:ring-emerald-500/50 dark:focus:border-emerald-500 transition-all outline-none cursor-pointer"
      >
        {options.map(day => (
          <option key={day} value={day}>
            {day} Days Lookback
          </option>
        ))}
      </select>
    </div>
  );
};

export default DayFilter;
