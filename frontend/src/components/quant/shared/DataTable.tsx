import React from 'react';

export interface DataTableColumn<T = any> {
  key: string;
  label: string;
  render?: (row: T, index: number) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  width?: string;
}

interface DataTableProps<T = any> {
  columns: DataTableColumn<T>[];
  rows: T[];
  onRowClick?: (row: T, index: number) => void;
  emptyMessage?: string;
  maxHeight?: string;
  keyExtractor?: (row: T, index: number) => string | number;
}

const TOOLTIP_STYLE = {
  backgroundColor: '#0f172a',
  borderColor: '#1e293b',
};

/**
 * Generic dark-themed data table with sticky header and hover rows.
 * Replaces 3 duplicated table patterns (Trade Log, Walk-Forward windows, Optimization combos).
 */
function DataTable<T = any>({
  columns,
  rows,
  onRowClick,
  emptyMessage = 'No data available.',
  maxHeight = '320px',
  keyExtractor,
}: DataTableProps<T>) {
  if (rows.length === 0) {
    return (
      <div className="text-center py-10 text-slate-500 text-sm">{emptyMessage}</div>
    );
  }

  return (
    <div
      className="overflow-auto rounded-xl border border-slate-800 bg-slate-950/60"
      style={{ maxHeight }}
    >
      <table className="w-full text-xs min-w-max">
        <thead className="sticky top-0 z-10 bg-slate-900 border-b border-slate-800">
          <tr>
            {columns.map(col => (
              <th
                key={col.key}
                className={`px-3 py-2.5 text-${col.align ?? 'left'} font-bold text-slate-400 uppercase tracking-wider whitespace-nowrap`}
                style={col.width ? { width: col.width } : undefined}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr
              key={keyExtractor ? keyExtractor(row, idx) : idx}
              onClick={onRowClick ? () => onRowClick(row, idx) : undefined}
              className={`border-b border-slate-800/50 transition-colors ${
                onRowClick ? 'cursor-pointer hover:bg-slate-800/60' : 'hover:bg-slate-800/30'
              }`}
            >
              {columns.map(col => (
                <td
                  key={col.key}
                  className={`px-3 py-2 text-${col.align ?? 'left'} text-slate-300 whitespace-nowrap`}
                >
                  {col.render
                    ? col.render(row, idx)
                    : String((row as any)[col.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export { TOOLTIP_STYLE };
export default DataTable;
