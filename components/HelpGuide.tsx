import React, { useState } from 'react';
import { HelpCircle, X, ChevronDown, ChevronRight, BookOpen, Lightbulb, AlertTriangle, CheckCircle, TrendingUp, Zap, Target } from 'lucide-react';

interface HelpSection {
    title: string;
    content: string | React.ReactNode;
    icon?: React.ReactNode;
}

interface HelpGuideProps {
    title: string;
    sections: HelpSection[];
    buttonLabel?: string;
}

const HelpGuide: React.FC<HelpGuideProps> = ({ title, sections, buttonLabel = "How It Works" }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set([0]));

    const toggleSection = (index: number) => {
        const newExpanded = new Set(expandedSections);
        if (newExpanded.has(index)) {
            newExpanded.delete(index);
        } else {
            newExpanded.add(index);
        }
        setExpandedSections(newExpanded);
    };

    return (
        <>
            {/* Trigger Button */}
            <button
                onClick={() => setIsOpen(true)}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-lg hover:bg-indigo-100 dark:hover:bg-indigo-900/50 transition-colors text-sm font-medium"
            >
                <HelpCircle size={16} />
                {buttonLabel}
            </button>

            {/* Modal Overlay */}
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[85vh] overflow-hidden flex flex-col">
                        {/* Header */}
                        <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700 bg-gradient-to-r from-indigo-500 to-purple-600">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-white/20 rounded-xl">
                                    <BookOpen size={24} className="text-white" />
                                </div>
                                <h2 className="text-xl font-bold text-white">{title}</h2>
                            </div>
                            <button
                                onClick={() => setIsOpen(false)}
                                className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                            >
                                <X size={20} className="text-white" />
                            </button>
                        </div>

                        {/* Content */}
                        <div className="flex-1 overflow-y-auto p-6 space-y-3">
                            {sections.map((section, index) => (
                                <div
                                    key={index}
                                    className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden"
                                >
                                    <button
                                        onClick={() => toggleSection(index)}
                                        className="w-full flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-left"
                                    >
                                        <div className="flex items-center gap-3">
                                            {section.icon || <Lightbulb size={18} className="text-amber-500" />}
                                            <span className="font-semibold text-slate-800 dark:text-white">
                                                {section.title}
                                            </span>
                                        </div>
                                        {expandedSections.has(index) ? (
                                            <ChevronDown size={18} className="text-slate-400" />
                                        ) : (
                                            <ChevronRight size={18} className="text-slate-400" />
                                        )}
                                    </button>
                                    {expandedSections.has(index) && (
                                        <div className="p-4 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-sm leading-relaxed">
                                            {typeof section.content === 'string' ? (
                                                <div dangerouslySetInnerHTML={{ __html: section.content }} />
                                            ) : (
                                                section.content
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>

                        {/* Footer */}
                        <div className="p-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/50">
                            <p className="text-xs text-slate-500 dark:text-slate-400 text-center">
                                ⚠️ This is for educational purposes only. Past performance does not guarantee future results.
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};

// Pre-built guide content for Backtest page
export const BacktestHelpGuide: React.FC = () => {
    const sections: HelpSection[] = [
        {
            title: "What is Backtesting?",
            icon: <BookOpen size={18} className="text-indigo-500" />,
            content: `
                <p class="mb-3">Backtesting is a way to test your trading strategy using <strong>past market data</strong> before risking real money.</p>
                <p class="mb-3">Think of it like a "practice run" — you simulate how your strategy would have performed during a specific historical period.</p>
                <ul class="list-disc pl-5 space-y-1">
                    <li><strong>No real money</strong> is involved — it's purely a simulation</li>
                    <li>Uses actual historical price data from the market</li>
                    <li>Helps you validate your strategy logic before going live</li>
                </ul>
            `
        },
        {
            title: "When Should You Use Backtesting?",
            icon: <Lightbulb size={18} className="text-amber-500" />,
            content: `
                <ul class="space-y-2">
                    <li><strong>Before live trading</strong> — Validate that your strategy has an edge</li>
                    <li><strong>After modifying parameters</strong> — See if changes improve or hurt performance</li>
                    <li><strong>Comparing strategies</strong> — Objectively measure which performs better</li>
                    <li><strong>Testing on new symbols</strong> — Check if your strategy works across different stocks</li>
                </ul>
            `
        },
        {
            title: "How to Run a Backtest (Step-by-Step)",
            icon: <CheckCircle size={18} className="text-emerald-500" />,
            content: `
                <ol class="list-decimal pl-5 space-y-2">
                    <li><strong>Select Symbol</strong> — Choose a stock from the dropdown</li>
                    <li><strong>Choose Strategy</strong> — Pick from available trading strategies</li>
                    <li><strong>Select Timeframe</strong> — 5m, 15m, 1H, 1D based on your trading style</li>
                    <li><strong>Set Date Range</strong> — Start and end dates for the test</li>
                    <li><strong>Set Capital</strong> — Your starting capital (e.g., ₹10,00,000)</li>
                    <li><strong>Click "Run Backtest"</strong> — Wait 5-15 seconds for results</li>
                </ol>
            `
        },
        {
            title: "Understanding Results",
            icon: <BookOpen size={18} className="text-blue-500" />,
            content: `
                <div class="space-y-3">
                    <div><strong>Total Return %:</strong> Overall profit or loss as percentage of starting capital</div>
                    <div><strong>Sharpe Ratio:</strong> Risk-adjusted return (>1.0 is good, >2.0 is excellent)</div>
                    <div><strong>Max Drawdown:</strong> Worst peak-to-trough decline (<20% is moderate)</div>
                    <div><strong>Win Rate:</strong> Percentage of trades that were profitable</div>
                    <div><strong>Profit Factor:</strong> Gross profits ÷ gross losses (>1.5 is good)</div>
                    <div><strong>Trade Count:</strong> More trades = more statistically reliable results</div>
                </div>
            `
        },
        {
            title: "What Backtesting Does NOT Tell You",
            icon: <AlertTriangle size={18} className="text-red-500" />,
            content: `
                <ul class="space-y-2">
                    <li><strong>No guarantee of future profits</strong> — Markets are dynamic and change over time</li>
                    <li><strong>Execution may differ live</strong> — Slippage, liquidity, and gaps affect real trades</li>
                    <li><strong>Costs are simplified</strong> — Brokerage, STT, and taxes reduce actual returns</li>
                    <li><strong>Overfitting risk</strong> — If you keep adjusting until it looks perfect, it may fail on new data</li>
                </ul>
            `
        }
    ];

    return <HelpGuide title="Backtest Guide" sections={sections} />;
};

// Pre-built guide content for Experiment Lab page
export const ExperimentLabHelpGuide: React.FC = () => {
    const sections: HelpSection[] = [
        {
            title: "What is Experiment Lab?",
            icon: <BookOpen size={18} className="text-indigo-500" />,
            content: `
                <p class="mb-3">Experiment Lab is a <strong>sandbox environment</strong> for quickly testing and comparing trading ideas.</p>
                <p class="mb-3">Think of it as your "strategy workshop" where you can:</p>
                <ul class="list-disc pl-5 space-y-1">
                    <li>Test different strategy combinations rapidly</li>
                    <li>Compare results across multiple symbols</li>
                    <li>Tweak parameters and see immediate feedback</li>
                    <li>Generate hypotheses to validate with proper backtesting</li>
                </ul>
            `
        },
        {
            title: "When to Use Experiment Lab",
            icon: <Lightbulb size={18} className="text-amber-500" />,
            content: `
                <ul class="space-y-2">
                    <li><strong>Early idea validation</strong> — Quickly check if a concept has merit</li>
                    <li><strong>Strategy tuning</strong> — Test parameter variations rapidly</li>
                    <li><strong>Symbol screening</strong> — Find which stocks work best with a strategy</li>
                    <li><strong>Learning</strong> — Understand how indicators behave on real data</li>
                </ul>
                <p class="mt-3 text-slate-500">Use Full Backtest when you need accurate P&L and risk metrics.</p>
            `
        },
        {
            title: "How to Run an Experiment (Step-by-Step)",
            icon: <CheckCircle size={18} className="text-emerald-500" />,
            content: `
                <ol class="list-decimal pl-5 space-y-2">
                    <li><strong>Add Symbols</strong> — Search and add stocks to test</li>
                    <li><strong>Select Strategies</strong> — Choose one or more from the catalog</li>
                    <li><strong>Choose Timeframe</strong> — 5m, 15m, 1H, 1D based on your style</li>
                    <li><strong>Set Date Range</strong> — At least 6 months recommended</li>
                    <li><strong>Configure Capital & Risk</strong> — Set starting capital</li>
                    <li><strong>Click "Run Backtest"</strong> — Review comparative results</li>
                </ol>
            `
        },
        {
            title: "Reading Experiment Results",
            icon: <BookOpen size={18} className="text-blue-500" />,
            content: `
                <div class="space-y-3">
                    <p>Each strategy result shows key metrics:</p>
                    <div><strong>Total Return %:</strong> Overall profit/loss</div>
                    <div><strong>Sharpe Ratio:</strong> Risk-adjusted return</div>
                    <div><strong>Max Drawdown:</strong> Worst decline from peak</div>
                    <div><strong>Win Rate:</strong> Profitable trade percentage</div>
                    <div><strong>Trade Count:</strong> Number of trades executed</div>
                    <p class="mt-3"><strong>Performance Tiers:</strong></p>
                    <div>🟢 <strong>Top Performers</strong> — Highest returns and Sharpe</div>
                    <div>🟡 <strong>Moderate</strong> — Decent results, worth investigating</div>
                    <div>🔴 <strong>Underperformers</strong> — May need adjustment</div>
                </div>
            `
        },
        {
            title: "Workflow: Where Experiment Lab Fits",
            icon: <Lightbulb size={18} className="text-purple-500" />,
            content: `
                <div class="bg-slate-100 dark:bg-slate-700 rounded-lg p-4 font-mono text-sm">
                    <div class="text-indigo-600 dark:text-indigo-400 font-bold">1. Experiment Lab ← You are here</div>
                    <div class="ml-4 text-slate-500">↓ Quick idea validation</div>
                    <div class="font-bold">2. Backtest</div>
                    <div class="ml-4 text-slate-500">↓ Full performance metrics</div>
                    <div class="font-bold">3. Walk-Forward</div>
                    <div class="ml-4 text-slate-500">↓ Out-of-sample validation</div>
                    <div class="font-bold">4. Live Trading</div>
                </div>
            `
        }
    ];

    return <HelpGuide title="Experiment Lab Guide" sections={sections} />;
};

// Pre-built guide content for Price Forecast page
export const PriceForecastHelpGuide: React.FC = () => {
    const sections: HelpSection[] = [
        {
            title: "What is AI Price Forecasting?",
            icon: <TrendingUp size={18} className="text-indigo-500" />,
            content: `
                <p class="mb-3">AI Price Forecasting uses <strong>machine learning and statistical models</strong> to predict future price movements based on historical price action (OHLCV) and technical indicators.</p>
                <p class="mb-3">Unlike traditional analysis, these models analyze thousands of previous patterns to find the most probable direction and volatility for the upcoming sessions.</p>
                <div class="bg-indigo-50 dark:bg-indigo-900/20 p-3 rounded-lg border border-indigo-100 dark:border-indigo-800">
                    <strong>Note:</strong> Predictive modeling is probabilistic. It identifies "likely" paths, not guaranteed certainties.
                </div>
            `
        },
        {
            title: "Understanding Algorithms",
            icon: <Zap size={18} className="text-amber-500" />,
            content: `
                <div class="space-y-4">
                    <div>
                        <div class="flex items-center gap-2 mb-1">
                            <span class="text-[10px] bg-blue-500 text-white px-1.5 py-0.5 rounded font-bold">RECOMMENDED</span>
                            <strong class="text-slate-800 dark:text-white">Adaptive Ensemble</strong>
                        </div>
                        <p class="text-xs opacity-80">Combines XGBoost and Ridge regression. It balances different model strengths to provide the most stable and accurate forecasts across various market regimes.</p>
                    </div>
                    <div>
                        <strong class="text-slate-800 dark:text-white">LSTM (Deep Learning)</strong>
                        <p class="text-xs opacity-80">A Recurrent Neural Network designed to remember long-term dependencies. Best for identifying complex trend reversals and volatile breakouts.</p>
                    </div>
                    <div>
                        <strong class="text-slate-800 dark:text-white">XGBoost Fast</strong>
                        <p class="text-xs opacity-80">A high-speed Gradient Boosting model. Optimized for quick turnaround, ideal for intraday "scalping" forecasts where speed is prioritized over depth.</p>
                    </div>
                    <div>
                        <strong class="text-slate-800 dark:text-white">ARIMA Stable</strong>
                        <p class="text-xs opacity-80">A classical statistical model (AutoRegressive Integrated Moving Average). Highly reliable for stable, trending markets without excessive "noise".</p>
                    </div>
                </div>
            `
        },
        {
            title: "How to Configure",
            icon: <CheckCircle size={18} className="text-emerald-500" />,
            content: `
                <ul class="space-y-3">
                    <li><strong>Hybrid Chart View:</strong> The chart now displays <strong>Historical data as Candlesticks</strong> (OHLC) and <strong>Forecast data as a Line graph</strong> for maximum clarity.</li>
                    <li><strong>Interval (Timeframe):</strong> Choose the resolution of data. <br/><span class="text-xs opacity-70">Example: 5m for intraday, 1d for swing trading.</span></li>
                    <li><strong>Horizon:</strong> How many future candles to predict. <br/><span class="text-xs opacity-70">Note: Confidence typically decreases as you move further into the future (longer horizons).</span></li>
                    <li><strong>Confidence Bands:</strong> The shaded area around the forecast line. There is a statistical probability that price will stay within this range.</li>
                </ul>
            `
        },
        {
            title: "Interpreting Results",
            icon: <Target size={18} className="text-blue-500" />,
            content: `
                <div class="space-y-3">
                    <div class="grid grid-cols-2 gap-3">
                        <div class="p-2 bg-slate-100 dark:bg-slate-700 rounded-lg">
                            <div class="text-[10px] uppercase font-bold text-slate-500 mb-1">Confidence Score</div>
                            <div class="text-sm font-bold text-slate-800 dark:text-white">>80% is high stability</div>
                        </div>
                        <div class="p-2 bg-slate-100 dark:bg-slate-700 rounded-lg">
                            <div class="text-[10px] uppercase font-bold text-slate-500 mb-1">Predicted Delta</div>
                            <div class="text-sm font-bold text-slate-800 dark:text-white">The expected % move</div>
                        </div>
                    </div>
                    <p class="text-xs italic">A "Service Online" badge indicates the neural inference engine is ready for real-time calculations.</p>
                </div>
            `
        },
        {
            title: "Risk & Limitations",
            icon: <AlertTriangle size={18} className="text-red-500" />,
            content: `
                <ul class="list-disc pl-5 space-y-2">
                    <li>External news events (black swans) can invalidate any statistical model.</li>
                    <li>Forecasts are more reliable in high-liquidity assets (e.g., Nifty 50 constituents).</li>
                    <li>Always combine AI forecasts with your own risk management (Stop-Loss/Take-Profit).</li>
                    <li>Model performance may vary based on market volatility (High/Medium/Low).</li>
                </ul>
            `
        }
    ];

    return <HelpGuide title="AI Forecast Guide" sections={sections} buttonLabel="Help & Documentation" />;
};

export default HelpGuide;
