import React, { useState, useEffect } from 'react';
import { Newspaper, Loader2, Plus, Sparkles, RefreshCw, X, FileText, Download } from 'lucide-react';
import { api } from '../services/api';

const ResearchCenter: React.FC = () => {
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // AI Generator topic input
  const [topic, setTopic] = useState('');
  const [generating, setGenerating] = useState(false);

  // View Modal state
  const [selectedReport, setSelectedReport] = useState<any>(null);

  const fetchReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getResearchReports();
      if (response && response.status === 'success') {
        setReports(response.reports);
      } else {
        setError('Failed to load research reports');
      }
    } catch (e: any) {
      setError(e.message || 'Error communicating with research archive.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleGenerateAIReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    
    setGenerating(true);
    try {
      const result = await api.generateAIResearchReport(topic.trim());
      if (result && result.status === 'success') {
        setTopic('');
        // Append at top of reports
        setReports(prev => [result.report, ...prev]);
        setSelectedReport(result.report);
      }
    } catch (e: any) {
      alert(e.message || 'Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 size={40} className="text-brand-500 animate-spin mb-4" />
        <p className="text-slate-400">Opening Research Archive...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white font-display flex items-center gap-2">
            <Newspaper size={28} /> Research Center
          </h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Access daily/weekly research newsletters, generate custom reports via Gemini AI, and print to PDF.
          </p>
        </div>
        <button
          onClick={fetchReports}
          className="flex items-center gap-2 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs font-bold rounded-xl transition-all uppercase tracking-wide shrink-0"
        >
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Archive list */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
          <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4">Research Archive</h3>
          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
            {reports.map((r) => (
              <div
                key={r.id}
                onClick={() => setSelectedReport(r)}
                className="flex items-start justify-between rounded-xl p-4 border border-slate-100 dark:border-slate-700/50 bg-slate-50 dark:bg-slate-900/50 hover:border-brand-500/30 transition-all cursor-pointer"
              >
                <div className="space-y-2 max-w-[80%]">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-[9px] font-black uppercase tracking-wide ${
                      r.report_type === 'DAILY' ? 'bg-blue-500/10 text-blue-500' : r.report_type === 'WEEKLY' ? 'bg-purple-500/10 text-purple-500' : 'bg-brand-500/10 text-brand-500'
                    }`}>{r.report_type}</span>
                    <span className="text-[10px] text-slate-400 font-mono font-bold">{r.created_at}</span>
                  </div>
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white">{r.title}</h4>
                  <p className="text-[10px] text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed">{r.summary}</p>
                </div>
                
                <button className="p-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-500 hover:text-brand-500 shrink-0">
                  <FileText size={15} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: AI Research Generator */}
        <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 border border-brand-500/20 rounded-2xl p-6 shadow-xl relative overflow-hidden flex flex-col justify-between min-h-[300px]">
          <div className="absolute top-0 right-0 w-32 h-32 bg-brand-500/10 rounded-full blur-3xl"></div>
          
          <div className="space-y-4 relative z-10">
            <div className="flex items-center gap-2">
              <Sparkles className="text-brand-400 animate-pulse" size={18} />
              <h3 className="text-white font-bold text-sm tracking-wide">Generate AI Research Report</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Enter any stock, sector, or investment thesis. QuantAI will analyze precomputed indicators, valuation multiples, and generate a customized institutional digest.
            </p>
          </div>

          <form onSubmit={handleGenerateAIReport} className="mt-8 space-y-3 relative z-10">
            <input
              type="text"
              placeholder="e.g. Reliance Q1 margins, BHEL breakout thesis"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              disabled={generating}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs font-bold focus:border-brand-500 focus:outline-none text-slate-100 placeholder-slate-600"
            />
            <button
              type="submit"
              disabled={generating || !topic.trim()}
              className="w-full py-2.5 bg-gradient-to-r from-brand-600 to-purple-600 text-white text-xs font-bold uppercase tracking-wider rounded-xl hover:from-brand-500 hover:to-purple-500 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {generating ? (
                <>
                  <Loader2 size={13} className="animate-spin" /> Compiling Research...
                </>
              ) : (
                <>
                  <Sparkles size={13} /> Compile Report
                </>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* Selected Report Viewer Modal */}
      {selectedReport && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl max-w-3xl w-full max-h-[85vh] overflow-hidden shadow-2xl flex flex-col justify-between">
            {/* Modal Header */}
            <div className="flex justify-between items-center p-6 border-b border-slate-200 dark:border-slate-700">
              <div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-white leading-snug">{selectedReport.title}</h2>
                <span className="text-[10px] text-slate-400 font-mono font-bold">{selectedReport.created_at}</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handlePrint}
                  className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-slate-500 hover:text-brand-500"
                  title="Print / Save PDF"
                >
                  <Download size={18} />
                </button>
                <button onClick={() => setSelectedReport(null)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-slate-500">
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto flex-grow max-h-[60vh] prose dark:prose-invert text-xs leading-relaxed text-slate-700 dark:text-slate-300">
              <div className="whitespace-pre-line font-medium">{selectedReport.content_markdown}</div>
            </div>
            
            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-200 dark:border-slate-700 flex justify-end">
              <button
                onClick={() => setSelectedReport(null)}
                className="px-4 py-2 bg-slate-900 dark:bg-slate-100 dark:text-slate-900 text-white rounded-xl text-xs font-bold uppercase"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ResearchCenter;
