"""
FastAPI Router for Unified Quant Workspace Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from utils.auth import get_current_user
from models import User

# Core quant engine components
from core.quant_engine.market_data.historical import get_market_data_engine
from core.quant_engine.strategy.base import UnifiedStrategy
from core.quant_engine.execution.vectorized import VectorizedExecutionEngine
from core.quant_engine.execution.event_driven import EventDrivenExecutionEngine
from core.quant_engine.walk_forward.validator import WalkForwardValidator
from core.quant_engine.monte_carlo.simulator import MonteCarloSimulator
from core.quant_engine.optimization.grid_search import ParameterOptimizer
from core.quant_engine.adapters.legacy_adapter import LegacyStrategyAdapter

# Legacy Registries
from core.backtest.strategies_impl import StrategyRegistry as CoreStrategyRegistry
from experiment_lab.registry import StrategyRegistry as LabStrategyRegistry, STRATEGY_CATALOG

router = APIRouter(
    tags=["Unified Quant Workspace"]
)


# ==================== Request/Response Models ====================

class QuantRunRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g. RELIANCE)")
    timeframe: str = Field("1D", description="Timeframe: 5m, 15m, 1H, 1D")
    strategy_id: Optional[str] = Field(None, description="Legacy standard strategy name or Experiment Lab integer ID")
    start_date: str = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: str = Field(None, description="End date (YYYY-MM-DD)")
    initial_capital: float = Field(100000.0, description="Initial capital in INR")
    risk_mode: str = Field("percent_capital", description="percent_capital, fixed_quantity, fixed_amount, atr_based")
    risk_percent: float = Field(2.0, description="Risk percent per trade")
    execution_type: str = Field("event_driven", description="event_driven or vectorized")
    strategy_params: Dict[str, Any] = Field(default_factory=dict, description="Custom parameters overrides")


class OptimizeRequest(BaseModel):
    symbol: str
    timeframe: str = "1D"
    strategy_id: str
    start_date: str
    end_date: str
    initial_capital: float = 100000.0
    param_grid: List[Dict[str, Any]] = Field(..., description="List of parameter combination dictionaries to test")
    max_workers: int = 4


class WalkForwardRequest(BaseModel):
    symbol: str
    timeframe: str = "1D"
    strategy_id: str
    start_date: str
    end_date: str
    initial_capital: float = 100000.0
    param_grid: List[Dict[str, Any]]
    train_window_bars: int = 120
    test_window_bars: int = 30
    step_bars: int = 30
    anchored: bool = False


class MonteCarloRequest(BaseModel):
    trade_returns_pct: List[float] = Field(..., min_length=1, description="List of trade return percentages")
    initial_capital: float = 100000.0
    num_simulations: int = 1000
    num_trades_per_path: int = 50
    risk_of_ruin_pct: float = 50.0


# ==================== Helper Resolver ====================

def resolve_unified_strategy(strategy_id: str, custom_params: Dict[str, Any]) -> UnifiedStrategy:
    """
    Resolve legacy standard strategy names OR Experiment Lab ID integers to UnifiedStrategy.
    """
    # 1. Try resolving as Experiment Lab Integer ID
    try:
        lab_id = int(strategy_id)
        lab_class = LabStrategyRegistry.get_by_id(lab_id)
        if lab_class:
            legacy_inst = lab_class()
            adapter = LegacyStrategyAdapter(legacy_inst)
            # Apply custom parameter overrides
            for k, v in custom_params.items():
                adapter.params[k] = v
            return adapter
    except ValueError:
        pass

    core_inst = CoreStrategyRegistry.get(strategy_id)
    if core_inst:
        # Create core instance
        legacy_inst = core_inst.__class__()
        adapter = LegacyStrategyAdapter(legacy_inst)
        for k, v in custom_params.items():
            adapter.params[k] = v
        return adapter

    # 3. Fallback: Try matching display_name in STRATEGY_CATALOG
    catalog_entry = next((s for s in STRATEGY_CATALOG if s["name"].lower() == strategy_id.lower()), None)
    if catalog_entry:
        lab_class = LabStrategyRegistry.get_by_id(catalog_entry["id"])
        if lab_class:
            legacy_inst = lab_class()
            adapter = LegacyStrategyAdapter(legacy_inst)
            for k, v in custom_params.items():
                adapter.params[k] = v
            return adapter

    raise HTTPException(
        status_code=400,
        detail=f"Strategy '{strategy_id}' not found in standard backtest or experiment lab registry."
    )


# ==================== Endpoints ====================

@router.post("/run")
async def run_quant_backtest(
    request: QuantRunRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Run backtest on Unified Quant Engine (Layer 1 Vectorized or Layer 2 Event-Driven).
    """
    # 1. Resolve strategy
    strat_id = request.strategy_id or "ma_crossover"
    strategy = resolve_unified_strategy(strat_id, request.strategy_params)

    # 2. Load historical market data
    end_date = request.end_date or datetime.now().strftime("%Y-%m-%d")
    start_date = request.start_date or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    data_engine = get_market_data_engine()
    df = data_engine.load_candles(request.symbol, request.timeframe, start_date, end_date)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No historical candles found for symbol: {request.symbol}")

    # 3. Run execution engine
    try:
        if request.execution_type == "vectorized":
            engine = VectorizedExecutionEngine(request.initial_capital)
            result = engine.run(strategy, df)
        else:
            engine = EventDrivenExecutionEngine(request.initial_capital)
            result = engine.run(
                strategy=strategy,
                df=df,
                risk_pct=request.risk_percent,
                risk_mode=request.risk_mode
            )
            
        # Re-format output timestamps for Recharts compatibility
        recharts_equity = []
        for i, eq in enumerate(result["equity_curve"]):
            if i < len(df):
                ts = str(df["timestamp"].iloc[i].date())
                recharts_equity.append({"date": ts, "equity": round(eq, 2)})
                
        result["equity_curve_recharts"] = recharts_equity
        return {
            "success": True,
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            "strategy": strat_id,
            "execution_type": request.execution_type,
            "metrics": result
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Quant engine run failed: {str(e)}")


@router.post("/optimize")
async def run_quant_optimization(
    request: OptimizeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Execute parallel parameter sweep optimization.
    """
    # 1. Validate strategy exists
    strategy = resolve_unified_strategy(request.strategy_id, {})
    strategy_module = strategy.legacy.__class__.__module__
    strategy_class_name = strategy.legacy.__class__.__name__

    # 2. Fetch candles
    data_engine = get_market_data_engine()
    df = data_engine.load_candles(request.symbol, request.timeframe, request.start_date, request.end_date)
    if df.empty:
        raise HTTPException(status_code=404, detail="Empty historical dataset for optimization.")

    try:
        optimizer = ParameterOptimizer(request.initial_capital)
        result = optimizer.optimize_grid(
            strategy_module=strategy_module,
            strategy_class_name=strategy_class_name,
            df=df,
            param_grid=request.param_grid,
            max_workers=request.max_workers
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.post("/walk-forward")
async def run_quant_walk_forward(
    request: WalkForwardRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Perform rolling window Walk-Forward parameter validation.
    """
    # 1. Validate strategy exists
    strategy = resolve_unified_strategy(request.strategy_id, {})
    strategy_class = strategy.legacy.__class__

    # 2. Fetch candles
    data_engine = get_market_data_engine()
    df = data_engine.load_candles(request.symbol, request.timeframe, request.start_date, request.end_date)
    if df.empty:
        raise HTTPException(status_code=404, detail="Empty historical dataset for walk-forward evaluation.")

    try:
        # Wrap the class to inject the legacy class into adapter
        class WrappedAdapter(LegacyStrategyAdapter):
            def __init__(self, params=None):
                super().__init__(strategy_class(params))

        validator = WalkForwardValidator(request.initial_capital)
        result = validator.run_walk_forward(
            strategy_class=WrappedAdapter,
            df=df,
            param_grid=request.param_grid,
            train_window_bars=request.train_window_bars,
            test_window_bars=request.test_window_bars,
            step_bars=request.step_bars,
            anchored=request.anchored
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Walk forward run failed: {str(e)}")


@router.post("/monte-carlo")
async def run_quant_monte_carlo(
    request: MonteCarloRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Compute randomized Monte Carlo paths from trading returns.
    """
    try:
        simulator = MonteCarloSimulator(request.initial_capital)
        result = simulator.simulate(
            trade_returns_pct=request.trade_returns_pct,
            num_simulations=request.num_simulations,
            num_trades_per_path=request.num_trades_per_path,
            risk_of_ruin_pct=request.risk_of_ruin_pct
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monte Carlo simulation failed: {str(e)}")


@router.get("/strategies")
async def list_unified_strategies(current_user: User = Depends(get_current_user)):
    """
    Get all unified catalog strategies matching core & lab registries.
    """
    # 1. Standard strategies
    core_list = []
    try:
        categories_dict = CoreStrategyRegistry.list_by_category()
        for cat_name, strats in categories_dict.items():
            for s in strats:
                core_list.append({
                    "id": s.name,
                    "name": s.display_name,
                    "category": cat_name,
                    "description": s.description,
                    "parameters": s.parameters
                })
    except Exception:
        pass

    # 2. Experiment Lab strategies
    lab_list = []
    for s in STRATEGY_CATALOG:
        lab_list.append({
            "id": str(s["id"]),
            "name": s["name"],
            "category": f"Experiment - {s['category']}",
            "description": s["description"],
            "parameters": {}
        })

    return {
        "core_strategies": core_list,
        "lab_strategies": lab_list,
        "total_count": len(core_list) + len(lab_list)
    }
