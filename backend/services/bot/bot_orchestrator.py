"""
Bot Orchestrator

Coordinates the full 6-step signal generation pipeline with progress tracking.
Manages run state, error handling, and result storage.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class BotStep(str, Enum):
    IDLE = "IDLE"
    COLLECTING_DATA = "COLLECTING_DATA"
    ANALYZING_CORRELATION = "ANALYZING_CORRELATION"
    ANALYZING_VOLATILITY = "ANALYZING_VOLATILITY"
    DETECTING_TREND = "DETECTING_TREND"
    GENERATING_SIGNALS = "GENERATING_SIGNALS"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


STEP_LABELS = {
    BotStep.IDLE: "Idle",
    BotStep.COLLECTING_DATA: "Collecting Market Data",
    BotStep.ANALYZING_CORRELATION: "Analyzing Correlations",
    BotStep.ANALYZING_VOLATILITY: "Analyzing Volatility",
    BotStep.DETECTING_TREND: "Detecting Market Trend",
    BotStep.GENERATING_SIGNALS: "Generating Signals",
    BotStep.COMPLETED: "Completed",
    BotStep.ERROR: "Error",
}

STEP_ORDER = [
    BotStep.COLLECTING_DATA,
    BotStep.ANALYZING_CORRELATION,
    BotStep.ANALYZING_VOLATILITY,
    BotStep.DETECTING_TREND,
    BotStep.GENERATING_SIGNALS,
    BotStep.COMPLETED,
]


@dataclass
class BotRunStatus:
    run_id: str
    status: str
    current_step: str
    current_step_label: str
    progress_pct: int
    elapsed_seconds: float
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BotRunResult:
    run_id: str
    market_trend: Optional[dict] = None
    buy_signals: List[dict] = field(default_factory=list)
    sell_signals: List[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class BotOrchestrator:
    """
    Pipeline coordinator for the signal generation bot.
    
    Singleton pattern — stores run state and results in memory.
    """

    def __init__(self):
        self._runs: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    def _set_step(self, run_id: str, step: BotStep, progress: int = 0):
        if run_id in self._runs:
            self._runs[run_id]["step"] = step
            self._runs[run_id]["progress"] = progress
            self._runs[run_id]["step_label"] = STEP_LABELS.get(step, str(step))

    async def run(self, history_days: int = 90, triggered_by: str = "manual") -> str:
        """
        Execute the full bot pipeline.
        
        Returns:
            run_id for status polling
        """
        run_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        self._runs[run_id] = {
            "step": BotStep.IDLE,
            "step_label": "Starting",
            "progress": 0,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "error": None,
            "result": None,
            "triggered_by": triggered_by,
        }

        try:
            # ─── Step 1: Data Collection ─────────────────────────
            self._set_step(run_id, BotStep.COLLECTING_DATA, 5)
            from services.bot.data_collector import DataCollector
            collector = DataCollector()

            # Load symbol registry
            symbols = collector.load_nifty500_symbols()
            if not symbols:
                raise RuntimeError("Failed to load NIFTY 500 symbols")

            self._set_step(run_id, BotStep.COLLECTING_DATA, 10)

            # Fetch NIFTY 50 index data
            nifty50_df = await collector.fetch_nifty50_history(days=history_days)
            self._set_step(run_id, BotStep.COLLECTING_DATA, 20)

            # Fetch stock data from DB
            stock_data = await collector.fetch_stock_data_from_db(days=history_days)
            self._set_step(run_id, BotStep.COLLECTING_DATA, 30)

            # Fetch live quotes for price changes
            instrument_keys = [ik for _, ik in symbols]
            live_quotes = await collector.fetch_live_quotes(instrument_keys)
            self._set_step(run_id, BotStep.COLLECTING_DATA, 40)

            # Build instrument_key → symbol mapping
            ik_to_symbol = {ik: sym for sym, ik in symbols}

            logger.info(
                f"Data collected: {len(stock_data)} DB stocks, "
                f"{len(live_quotes)} live quotes, "
                f"NIFTY50: {len(nifty50_df)} days"
            )

            # ─── Step 2: Correlation Analysis ────────────────────
            self._set_step(run_id, BotStep.ANALYZING_CORRELATION, 45)
            from services.bot.analysis_engine import AnalysisEngine
            engine = AnalysisEngine()

            correlations = engine.calculate_correlations(stock_data, nifty50_df)
            self._set_step(run_id, BotStep.ANALYZING_CORRELATION, 55)

            # ─── Step 3: Volatility Analysis ─────────────────────
            self._set_step(run_id, BotStep.ANALYZING_VOLATILITY, 60)
            volatilities = engine.calculate_volatility(stock_data)
            self._set_step(run_id, BotStep.ANALYZING_VOLATILITY, 70)

            # ─── Step 4: Market Trend Detection ──────────────────
            self._set_step(run_id, BotStep.DETECTING_TREND, 75)
            market_trend = engine.detect_market_trend(nifty50_df)
            if market_trend is None:
                raise RuntimeError("Could not determine market trend — insufficient NIFTY 50 data")
            self._set_step(run_id, BotStep.DETECTING_TREND, 80)

            # ─── Step 5 & 6: Signal Generation + PCR ─────────────
            self._set_step(run_id, BotStep.GENERATING_SIGNALS, 85)

            # Build price change dict
            price_changes: Dict[str, dict] = {}
            for ik, quote in live_quotes.items():
                sym = ik_to_symbol.get(ik)
                if not sym:
                    continue
                ltp = quote.get("last_price", 0)
                prev = quote.get("previous_close", 0)
                if ltp and prev and prev > 0:
                    pct = round(((ltp - prev) / prev) * 100, 2)
                    price_changes[sym] = {
                        "current": ltp,
                        "previous": prev,
                        "change_pct": pct,
                    }

            # Also add price changes from DB data for stocks without live quotes
            for sym, df in stock_data.items():
                if sym not in price_changes and len(df) >= 2:
                    curr = float(df["close"].iloc[-1])
                    prev = float(df["close"].iloc[-2])
                    if prev > 0:
                        price_changes[sym] = {
                            "current": curr,
                            "previous": prev,
                            "change_pct": round(((curr - prev) / prev) * 100, 2),
                        }

            # Fetch PCR data (real Upstox option chain + simulated fallback)
            pcr_data: Dict[str, dict] = {}
            pcr_source_summary = {"upstox": 0, "simulated": 0}
            try:
                from services.derivatives_service import DerivativesService
                deriv_svc = DerivativesService()
                for sym in correlations.keys():
                    pc = price_changes.get(sym, {})
                    dd = await deriv_svc.get_derivatives_data(sym, pc.get("change_pct", 0))
                    if dd.has_derivatives and dd.pcr is not None:
                        pcr_data[sym] = {"pcr": dd.pcr, "source": dd.data_source}
                        pcr_source_summary[dd.data_source] = pcr_source_summary.get(dd.data_source, 0) + 1
            except Exception as e:
                logger.warning(f"PCR fetch failed (non-critical): {e}")

            pcr_source_label = "upstox" if pcr_source_summary.get("upstox", 0) > 0 else "simulated"
            logger.info(f"PCR data sources: {pcr_source_summary}")

            self._set_step(run_id, BotStep.GENERATING_SIGNALS, 90)

            # Generate signals
            from services.bot.signal_generator import SignalGenerator
            generator = SignalGenerator()
            signals = generator.generate_signals(
                market_trend=market_trend.trend,
                correlations=correlations,
                volatilities=volatilities,
                price_changes=price_changes,
                pcr_data=pcr_data,
            )

            # ─── Build Result ────────────────────────────────────
            elapsed = round(time.time() - start_time, 1)
            buy_signals = [s.to_dict() for s in signals if s.signal_type == "BUY"]
            sell_signals = [s.to_dict() for s in signals if s.signal_type == "SELL"]

            result = BotRunResult(
                run_id=run_id,
                market_trend={
                    "trend": market_trend.trend,
                    "ema_50": market_trend.ema_50,
                    "ema_200": market_trend.ema_200,
                    "momentum": market_trend.momentum,
                    "last_close": market_trend.last_close,
                },
                buy_signals=buy_signals,
                sell_signals=sell_signals,
                summary={
                    "total_stocks_analyzed": len(stock_data),
                    "total_correlations": len(correlations),
                    "high_correlation_count": sum(
                        1 for c in correlations.values() if c.category == "HIGH"
                    ),
                    "total_signals": len(signals),
                    "buy_count": len(buy_signals),
                    "sell_count": len(sell_signals),
                    "execution_time_seconds": elapsed,
                    "data_sources": {
                        "historical": "database" if stock_data else "api",
                        "live_quotes": len(live_quotes),
                        "pcr": pcr_source_label,
                        "pcr_breakdown": pcr_source_summary,
                    },
                },
                completed_at=datetime.now().isoformat(),
            )

            self._runs[run_id]["result"] = result
            self._runs[run_id]["completed_at"] = result.completed_at
            self._set_step(run_id, BotStep.COMPLETED, 100)

            logger.info(f"Bot run {run_id} completed in {elapsed}s: {len(signals)} signals")

            # ─── Persist to Database ─────────────────────────────
            try:
                await self._persist_run(run_id, result, triggered_by)
            except Exception as pe:
                logger.error(f"DB persistence failed (non-critical): {pe}")

            # ─── Send Telegram Alerts ────────────────────────────
            try:
                from services.bot.alert_service import AlertService
                alert_svc = AlertService()
                all_signals = buy_signals + sell_signals
                await alert_svc.send_telegram_alert(all_signals, result.market_trend, run_id)
            except Exception as ae:
                logger.warning(f"Telegram alert failed (non-critical): {ae}")

            return run_id

        except Exception as e:
            logger.error(f"Bot run {run_id} failed: {e}", exc_info=True)
            self._runs[run_id]["error"] = str(e)
            self._set_step(run_id, BotStep.ERROR, 0)
            return run_id

    def get_status(self, run_id: str) -> Optional[BotRunStatus]:
        run = self._runs.get(run_id)
        if not run:
            return None

        started = run.get("started_at", "")
        elapsed = 0.0
        if started:
            try:
                st = datetime.fromisoformat(started)
                elapsed = round((datetime.now() - st).total_seconds(), 1)
            except Exception:
                pass

        return BotRunStatus(
            run_id=run_id,
            status=run["step"].value if isinstance(run["step"], BotStep) else run["step"],
            current_step=run["step"].value if isinstance(run["step"], BotStep) else run["step"],
            current_step_label=run.get("step_label", ""),
            progress_pct=run.get("progress", 0),
            elapsed_seconds=elapsed,
            error_message=run.get("error"),
            started_at=run.get("started_at"),
            completed_at=run.get("completed_at"),
        )

    def get_result(self, run_id: str) -> Optional[BotRunResult]:
        # Check in-memory first
        run = self._runs.get(run_id)
        if run and run.get("result"):
            return run["result"]

        # Fallback to DB
        try:
            return self._load_result_from_db(run_id)
        except Exception as e:
            logger.debug(f"DB result lookup failed for {run_id}: {e}")
            return None

    def get_last_run_id(self) -> Optional[str]:
        # Check in-memory first
        if self._runs:
            return list(self._runs.keys())[-1]

        # Fallback to DB
        try:
            from database import SessionLocal
            from models_bot import BotRun
            db = SessionLocal()
            try:
                row = db.query(BotRun).order_by(BotRun.started_at.desc()).first()
                return row.run_id if row else None
            finally:
                db.close()
        except Exception:
            return None

    async def _persist_run(self, run_id: str, result: BotRunResult, triggered_by: str = "manual"):
        """Persist a completed bot run and its signals to PostgreSQL."""
        from database import SessionLocal
        from models_bot import BotRun, BotSignalRecord

        db = SessionLocal()
        try:
            bot_run = BotRun(
                run_id=run_id,
                status="COMPLETED",
                market_trend=result.market_trend,
                summary=result.summary,
                started_at=datetime.fromisoformat(self._runs[run_id]["started_at"]),
                completed_at=datetime.fromisoformat(result.completed_at) if result.completed_at else None,
                triggered_by=triggered_by,
                buy_count=len(result.buy_signals),
                sell_count=len(result.sell_signals),
            )
            db.add(bot_run)

            for sig in result.buy_signals + result.sell_signals:
                record = BotSignalRecord(
                    run_id=run_id,
                    symbol=sig.get("symbol", ""),
                    signal_type=sig.get("signal_type", ""),
                    correlation=sig.get("correlation"),
                    correlation_category=sig.get("correlation_category"),
                    price_change_pct=sig.get("price_change_pct"),
                    current_price=sig.get("current_price"),
                    volatility_level=sig.get("volatility_level"),
                    volatility_atr=sig.get("volatility_atr"),
                    pcr_value=sig.get("pcr_value"),
                    pcr_source=sig.get("pcr_source"),
                    conviction=sig.get("conviction"),
                )
                db.add(record)

            db.commit()
            logger.info(f"Bot run {run_id} persisted to DB ({len(result.buy_signals)} buys, {len(result.sell_signals)} sells)")
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    def _load_result_from_db(self, run_id: str) -> Optional[BotRunResult]:
        """Load a bot run result from the database."""
        from database import SessionLocal
        from models_bot import BotRun, BotSignalRecord

        db = SessionLocal()
        try:
            run = db.query(BotRun).filter(BotRun.run_id == run_id).first()
            if not run:
                return None

            signals = db.query(BotSignalRecord).filter(BotSignalRecord.run_id == run_id).all()
            buy_signals = [
                {
                    "symbol": s.symbol, "signal_type": s.signal_type,
                    "correlation": s.correlation, "correlation_category": s.correlation_category,
                    "price_change_pct": s.price_change_pct, "current_price": s.current_price,
                    "volatility_level": s.volatility_level, "volatility_atr": s.volatility_atr,
                    "pcr_value": s.pcr_value, "pcr_source": s.pcr_source,
                    "conviction": s.conviction,
                }
                for s in signals if s.signal_type == "BUY"
            ]
            sell_signals = [
                {
                    "symbol": s.symbol, "signal_type": s.signal_type,
                    "correlation": s.correlation, "correlation_category": s.correlation_category,
                    "price_change_pct": s.price_change_pct, "current_price": s.current_price,
                    "volatility_level": s.volatility_level, "volatility_atr": s.volatility_atr,
                    "pcr_value": s.pcr_value, "pcr_source": s.pcr_source,
                    "conviction": s.conviction,
                }
                for s in signals if s.signal_type == "SELL"
            ]

            return BotRunResult(
                run_id=run.run_id,
                market_trend=run.market_trend,
                buy_signals=buy_signals,
                sell_signals=sell_signals,
                summary=run.summary or {},
                completed_at=run.completed_at.isoformat() if run.completed_at else None,
            )
        finally:
            db.close()


# Singleton instance
_orchestrator: Optional[BotOrchestrator] = None


def get_bot_orchestrator() -> BotOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = BotOrchestrator()
    return _orchestrator

