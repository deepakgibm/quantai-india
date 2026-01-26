import React, { useEffect, useState } from 'react';
import { List, Plus, Trash2, Search, X, Loader2, ArrowLeft, ArrowRight, Layers } from 'lucide-react';
import { api } from '../services/api';

interface IndexInfo {
    index_id: number;
    index_name: string;
    description: string;
    base_index_id?: number;
}

const AdminIndices: React.FC = () => {
    const [indices, setIndices] = useState<IndexInfo[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedIdx, setSelectedIdx] = useState<IndexInfo | null>(null);
    const [constituents, setConstituents] = useState<string[]>([]);
    const [newSymbol, setNewSymbol] = useState('');
    const [newIndexName, setNewIndexName] = useState('');
    const [newIndexDesc, setNewIndexDesc] = useState('');
    const [isCreating, setIsCreating] = useState(false);

    const fetchIndices = async () => {
        try {
            setLoading(true);
            const data = await api.getAdminIndices();
            setIndices(data);
        } catch (e: any) {
            setError(e.message || 'Failed to fetch indices');
        } finally {
            setLoading(false);
        }
    };

    const fetchConstituents = async (name: string) => {
        try {
            const data = await api.runScanner(`/api/trading/index-constituents?index=${name}`);
            setConstituents(data.constituents || []);
        } catch (e) {
            console.error('Failed to fetch constituents', e);
        }
    };

    useEffect(() => {
        fetchIndices();
    }, []);

    const handleSelectIndex = (idx: IndexInfo) => {
        setSelectedIdx(idx);
        fetchConstituents(idx.index_name);
    };

    const handleAddSymbol = async () => {
        if (!selectedIdx || !newSymbol) return;
        try {
            await api.addIndexConstituent(selectedIdx.index_id, newSymbol.toUpperCase());
            setNewSymbol('');
            fetchConstituents(selectedIdx.index_name);
        } catch (e: any) {
            alert(e.message || 'Failed to add symbol');
        }
    };

    const handleRemoveSymbol = async (sym: string) => {
        if (!selectedIdx) return;
        if (!confirm(`Remove ${sym} from ${selectedIdx.index_name}?`)) return;
        try {
            await api.removeIndexConstituent(selectedIdx.index_id, sym);
            fetchConstituents(selectedIdx.index_name);
        } catch (e: any) {
            alert(e.message || 'Failed to remove symbol');
        }
    };

    const handleCreateIndex = async () => {
        if (!newIndexName) return;
        try {
            await api.createAdminIndex(newIndexName, newIndexDesc);
            setNewIndexName('');
            setNewIndexDesc('');
            setIsCreating(false);
            fetchIndices();
        } catch (e: any) {
            alert(e.message || 'Failed to create index');
        }
    };

    const handleDeleteIndex = async (id: number) => {
        if (!confirm('Delete this index and all its mappings?')) return;
        try {
            await api.deleteAdminIndex(id);
            if (selectedIdx?.index_id === id) setSelectedIdx(null);
            fetchIndices();
        } catch (e: any) {
            alert(e.message || 'Failed to delete index');
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Index Management</h1>
                    <p className="text-slate-500 dark:text-slate-400">Dynamic scanner configuration & index hierarchies</p>
                </div>
                <button
                    onClick={() => setIsCreating(true)}
                    className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-lg transition-colors"
                >
                    <Plus size={18} />
                    <span>New Index</span>
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Indices List */}
                <div className="lg:col-span-1 space-y-4">
                    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                        <div className="p-4 border-b border-slate-100 dark:border-slate-700 font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2">
                            <Layers size={18} className="text-brand-500" />
                            Available Indices
                        </div>
                        <div className="divide-y divide-slate-100 dark:divide-slate-700 max-h-[600px] overflow-y-auto">
                            {loading ? (
                                <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-slate-400" /></div>
                            ) : indices.length === 0 ? (
                                <div className="p-8 text-center text-slate-400">No indices found</div>
                            ) : indices.map(idx => (
                                <div
                                    key={idx.index_id}
                                    onClick={() => handleSelectIndex(idx)}
                                    className={`p-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors flex justify-between items-center ${selectedIdx?.index_id === idx.index_id ? 'bg-brand-50 dark:bg-brand-900/20 border-l-4 border-brand-500' : ''}`}
                                >
                                    <div>
                                        <h3 className="font-bold text-slate-900 dark:text-white">{idx.index_name}</h3>
                                        <p className="text-xs text-slate-500 line-clamp-1">{idx.description || 'No description'}</p>
                                    </div>
                                    <X className="w-4 h-4 text-slate-400 hover:text-red-500" onClick={(e) => { e.stopPropagation(); handleDeleteIndex(idx.index_id); }} />
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Constituent Management */}
                <div className="lg:col-span-2 space-y-4">
                    {!selectedIdx ? (
                        <div className="bg-slate-100 dark:bg-slate-800/50 rounded-xl h-96 flex flex-col items-center justify-center border-2 border-dashed border-slate-200 dark:border-slate-700">
                            <Layers size={48} className="text-slate-300 mb-4" />
                            <p className="text-slate-500">Select an index to manage constituents</p>
                        </div>
                    ) : (
                        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col h-[650px]">
                            <div className="p-6 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/50">
                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <h2 className="text-xl font-bold text-slate-900 dark:text-white">{selectedIdx.index_name}</h2>
                                        <p className="text-sm text-slate-500">{selectedIdx.description}</p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <input
                                            type="text"
                                            placeholder="Symbol (e.g. RELIANCE)"
                                            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 outline-none"
                                            value={newSymbol}
                                            onChange={(e) => setNewSymbol(e.target.value)}
                                            onKeyDown={(e) => e.key === 'Enter' && handleAddSymbol()}
                                        />
                                        <button
                                            onClick={handleAddSymbol}
                                            className="p-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors"
                                        >
                                            <Plus size={18} />
                                        </button>
                                    </div>
                                </div>
                                <div className="flex gap-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                                    <span>Count: {constituents.length} Symbols</span>
                                    {selectedIdx.base_index_id && <span className="text-brand-500">Includes Base Index</span>}
                                </div>
                            </div>

                            <div className="flex-1 p-6 overflow-y-auto">
                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                                    {constituents.map(sym => (
                                        <div key={sym} className="group relative bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-3 flex items-center justify-between hover:border-brand-300 dark:hover:border-brand-800 transition-all">
                                            <span className="font-bold text-slate-900 dark:text-white">{sym}</span>
                                            <button
                                                onClick={() => handleRemoveSymbol(sym)}
                                                className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500 transition-opacity"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Create Modal Overlay */}
            {isCreating && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[60] p-4">
                    <div className="bg-white dark:bg-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6">
                        <h2 className="text-xl font-bold mb-4">Create New Index</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-500 mb-1">Index Name</label>
                                <input
                                    type="text"
                                    className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-brand-500"
                                    placeholder="e.g. NIFTY 50"
                                    value={newIndexName}
                                    onChange={(e) => setNewIndexName(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-500 mb-1">Description</label>
                                <textarea
                                    className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-brand-500"
                                    placeholder="Purpose of this index..."
                                    value={newIndexDesc}
                                    onChange={(e) => setNewIndexDesc(e.target.value)}
                                />
                            </div>
                            <div className="flex gap-3 pt-2">
                                <button
                                    onClick={() => setIsCreating(false)}
                                    className="flex-1 px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 font-bold hover:bg-slate-50 dark:hover:bg-slate-700 transition-all"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleCreateIndex}
                                    className="flex-1 px-4 py-3 rounded-xl bg-brand-500 text-white font-bold hover:bg-brand-600 transition-all shadow-lg shadow-brand-500/25"
                                >
                                    Create
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AdminIndices;
