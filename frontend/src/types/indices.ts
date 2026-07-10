/**
 * TypeScript types for NSE Index Management System
 */

export type IndexCategory = 'Broad Market' | 'Sector' | 'Midcap' | 'Smallcap' | 'Thematic';

export interface IndexInfo {
  index_name: string;
  display_name: string;
  category: IndexCategory;
  description: string;
  constituent_count: number;
  last_refreshed: string | null;
  is_active: boolean;
  nse_index_code: string;
  coverage_pct: number;
}

export interface IndexSymbol {
  symbol: string;
  instrument_key: string;
  company_name: string;
  sector: string;
  weight: number | null;
  industry: string;
  added_at: string | null;
  removed_at: string | null;
}

export interface IndexStats {
  index_name: string;
  display_name: string;
  category: IndexCategory;
  last_refreshed: string | null;
  live_constituent_count: number;
  last_refresh: {
    matched_count: number;
    missing_count: number;
    total_nse_count: number;
    coverage_pct: number;
    status: 'success' | 'partial' | 'failed' | 'never_run';
    refreshed_at: string | null;
    missing_symbols: string;
  } | null;
}

export interface IndexRefreshLog {
  index_name: string;
  refreshed_at: string | null;
  added_count: number;
  removed_count: number;
  matched_count: number;
  missing_count: number;
  total_nse_count: number;
  coverage_pct: number;
  status: string;
  error_message: string | null;
}

export interface ValidationReport {
  index_name: string;
  total_nse: number;
  matched_count: number;
  auto_resolved_count: number;
  missing_count: number;
  coverage_pct: number;
  missing: Array<{ nse_symbol: string; company_name: string; isin: string; reason: string }>;
  auto_resolved: Array<{ nse_symbol: string; db_symbol: string; resolution: string }>;
}

/** The full list of supported universe names for filter dropdowns */
export const UNIVERSE_OPTIONS: Array<{ label: string; value: string; category: IndexCategory }> = [
  { label: 'All Stocks',         value: 'ALL',                      category: 'Broad Market' },
  { label: 'NIFTY 50',           value: 'NIFTY 50',                 category: 'Broad Market' },
  { label: 'NIFTY Next 50',      value: 'NIFTY NEXT 50',            category: 'Broad Market' },
  { label: 'NIFTY 100',          value: 'NIFTY 100',                category: 'Broad Market' },
  { label: 'NIFTY 200',          value: 'NIFTY 200',                category: 'Broad Market' },
  { label: 'NIFTY 500',          value: 'NIFTY 500',                category: 'Broad Market' },
  { label: 'NIFTY Total Market', value: 'NIFTY TOTAL MARKET',       category: 'Broad Market' },
  { label: 'NIFTY Bank',         value: 'NIFTY BANK',               category: 'Sector' },
  { label: 'NIFTY IT',           value: 'NIFTY IT',                 category: 'Sector' },
  { label: 'NIFTY Auto',         value: 'NIFTY AUTO',               category: 'Sector' },
  { label: 'NIFTY FMCG',         value: 'NIFTY FMCG',              category: 'Sector' },
  { label: 'NIFTY Pharma',       value: 'NIFTY PHARMA',             category: 'Sector' },
  { label: 'NIFTY Metal',        value: 'NIFTY METAL',              category: 'Sector' },
  { label: 'NIFTY Realty',       value: 'NIFTY REALTY',             category: 'Sector' },
  { label: 'NIFTY Media',        value: 'NIFTY MEDIA',              category: 'Sector' },
  { label: 'NIFTY Energy',       value: 'NIFTY ENERGY',             category: 'Sector' },
  { label: 'NIFTY Oil & Gas',    value: 'NIFTY OIL AND GAS',        category: 'Sector' },
  { label: 'NIFTY PSU Bank',     value: 'NIFTY PSU BANK',           category: 'Sector' },
  { label: 'NIFTY Private Bank', value: 'NIFTY PRIVATE BANK',       category: 'Sector' },
  { label: 'NIFTY Fin Services', value: 'NIFTY FINANCIAL SERVICES', category: 'Sector' },
  { label: 'NIFTY Healthcare',   value: 'NIFTY HEALTHCARE',         category: 'Sector' },
  { label: 'NIFTY Cons Durables',value: 'NIFTY CONSUMER DURABLES',  category: 'Sector' },
  { label: 'NIFTY Capital Goods',value: 'NIFTY CAPITAL GOODS',      category: 'Sector' },
  { label: 'NIFTY Chemicals',    value: 'NIFTY CHEMICALS',          category: 'Sector' },
  { label: 'NIFTY Midcap 50',    value: 'NIFTY MIDCAP 50',          category: 'Midcap' },
  { label: 'NIFTY Midcap 100',   value: 'NIFTY MIDCAP 100',         category: 'Midcap' },
  { label: 'NIFTY Smallcap 100', value: 'NIFTY SMALLCAP 100',       category: 'Smallcap' },
];
