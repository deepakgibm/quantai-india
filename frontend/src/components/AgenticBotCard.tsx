
import React, { useState } from 'react';
import { Bot, Play, AlertTriangle, TrendingUp, Activity, CheckCircle } from 'lucide-react';

interface StockResult {
  symbol: string;
  buy_score: number;
  final_decision: string;
  reason_for_buy: string;
  news_sentiment: string;
  ml_reasoning: string;
  ltp: number;
  trend_score: number;
  ml_score: number;
  risk_score: number;
  negative_news: string[];
}

const AgenticBotCard: React.FC = () => {
  const [prompt, setPrompt] = useState("Research top stocks for this week");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<StockResult[]>([]);
  const [error, setError] = useState("");

  const runAnalysis = async () => {
    setLoading(true);
    setError("");
    setResults([]);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:8000/api/agentic-bot/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ prompt })
      });

      if (!response.ok) throw new Error("Analysis failed");

      const data = await response.json();
      setResults(data.data);
    } catch (err) {
      setError("Failed to run agents. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-indigo-50 to-purple-50">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-indigo-600 rounded-lg">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-900">3-Agentic Stock Bot</h2>
            <p className="text-sm text-gray-600">Research • Risk • Decision</p>
          </div>
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="Ask the agents..."
          />
          <button
            onClick={runAnalysis}
            disabled={loading}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? <Activity className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Run
          </button>
        </div>
        {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
      </div>

      <div className="p-0">
        {results.length > 0 ? (
          <div className="divide-y divide-gray-100">
            {results.map((stock, idx) => (
              <div key={idx} className="p-4 hover:bg-gray-50 transition-colors">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-lg text-gray-900">{stock.symbol}</h3>
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${stock.final_decision === 'BUY' ? 'bg-green-100 text-green-700' :
                          stock.final_decision === 'WATCH' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-red-100 text-red-700'
                        }`}>
                        {stock.final_decision}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500">Score: {stock.buy_score}/100</p>
                  </div>
                  <div className="text-right">
                    <p className="font-mono font-medium">₹{stock.ltp}</p>
                  </div>
                </div>

                <p className="text-sm text-gray-700 mb-3">{stock.reason_for_buy}</p>

                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="bg-blue-50 p-2 rounded">
                    <div className="flex items-center gap-1 text-blue-700 font-semibold mb-1">
                      <TrendingUp className="w-3 h-3" /> Trend
                    </div>
                    <p>Score: {stock.trend_score}</p>
                  </div>
                  <div className="bg-purple-50 p-2 rounded">
                    <div className="flex items-center gap-1 text-purple-700 font-semibold mb-1">
                      <Bot className="w-3 h-3" /> ML Model
                    </div>
                    <p>{stock.ml_score}% Conf.</p>
                  </div>
                  <div className="bg-orange-50 p-2 rounded">
                    <div className="flex items-center gap-1 text-orange-700 font-semibold mb-1">
                      <AlertTriangle className="w-3 h-3" /> Risk
                    </div>
                    <p>Score: {stock.risk_score}</p>
                  </div>
                </div>

                {stock.negative_news.length > 0 && (
                  <div className="mt-3 text-xs text-red-600 bg-red-50 p-2 rounded border border-red-100">
                    <strong>Risk Alert:</strong> {stock.negative_news[0]}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          !loading && (
            <div className="p-8 text-center text-gray-400">
              <Bot className="w-12 h-12 mx-auto mb-3 opacity-20" />
              <p>Enter a command to start the agent workflow</p>
            </div>
          )
        )}

        {loading && (
          <div className="p-8 text-center">
            <div className="space-y-4">
              <div className="flex items-center justify-center gap-3 text-sm text-gray-600 animate-pulse">
                <div className="w-2 h-2 bg-indigo-600 rounded-full"></div>
                Research Agent fetching data...
              </div>
              <div className="flex items-center justify-center gap-3 text-sm text-gray-600 animate-pulse delay-75">
                <div className="w-2 h-2 bg-purple-600 rounded-full"></div>
                Risk Agent scanning news...
              </div>
              <div className="flex items-center justify-center gap-3 text-sm text-gray-600 animate-pulse delay-150">
                <div className="w-2 h-2 bg-green-600 rounded-full"></div>
                Decision Agent ranking stocks...
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AgenticBotCard;
