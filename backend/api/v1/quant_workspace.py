"""
FastAPI Router for Unified Quant Workspace Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd

from utils.auth import get_current_user
from models import User
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

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

from utils.rate_limit import rate_limit

router = APIRouter(
    tags=["Unified Quant Workspace"],
    dependencies=[Depends(rate_limit(120, 60, "quant_workspace"))]
)


# ==================== Request/Response Models ====================

class QuantRunRequest(BaseModel):
    symbol: Optional[str] = Field(None, description="Stock symbol (e.g. RELIANCE)")
    symbols: Optional[List[str]] = Field(None, description="List of stock symbols for batch backtesting")
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
    Supports single symbol execution (compatible with legacy format) or batch symbols execution.
    """
    # 1. Resolve strategy
    strat_id = request.strategy_id or "ma_crossover"
    strategy = resolve_unified_strategy(strat_id, request.strategy_params)

    # 2. Set dates
    end_date = request.end_date or datetime.now().strftime("%Y-%m-%d")
    start_date = request.start_date or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    # Validate capital
    if request.initial_capital <= 0:
        raise HTTPException(status_code=422, detail="initial_capital must be greater than 0.")

    # 3. Batch symbols execution if symbols is provided
    if request.symbols and len(request.symbols) > 0:
        results = {}
        data_engine = get_market_data_engine()
        for sym in request.symbols:
            try:
                df = data_engine.load_candles(sym, request.timeframe, start_date, end_date)
                if df.empty:
                    results[sym] = {"success": False, "error": f"No historical candles found for symbol: {sym}"}
                    continue

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
                        try:
                            ts_raw = df["timestamp"].iloc[i]
                            ts = pd.Timestamp(ts_raw).date().isoformat()
                        except Exception:
                            ts = str(i)
                        recharts_equity.append({"date": ts, "equity": round(float(eq), 2)})

                result["equity_curve_recharts"] = recharts_equity
                # Ensure trades have JSON-serializable timestamps
                for t in result.get("trades", []):
                    for k in ("entry_time", "exit_time"):
                        if t.get(k) is not None:
                            try:
                                t[k] = str(pd.Timestamp(t[k]))
                            except Exception:
                                t[k] = str(t[k])

                results[sym] = {
                    "success": True,
                    "metrics": result
                }
            except Exception as e:
                results[sym] = {"success": False, "error": str(e)}

        return {
            "success": True,
            "symbols": request.symbols,
            "timeframe": request.timeframe,
            "strategy": strat_id,
            "execution_type": request.execution_type,
            "batch_results": results
        }

    # 4. Fallback to single symbol execution
    if not request.symbol:
        raise HTTPException(status_code=400, detail="Either symbol or symbols must be provided.")

    data_engine = get_market_data_engine()
    df = data_engine.load_candles(request.symbol, request.timeframe, start_date, end_date)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No historical candles found for symbol: {request.symbol}")

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
                try:
                    ts_raw = df["timestamp"].iloc[i]
                    ts = pd.Timestamp(ts_raw).date().isoformat()
                except Exception:
                    ts = str(i)
                recharts_equity.append({"date": ts, "equity": round(float(eq), 2)})

        result["equity_curve_recharts"] = recharts_equity
        # Ensure trades have JSON-serializable timestamps
        for t in result.get("trades", []):
            for k in ("entry_time", "exit_time"):
                if t.get(k) is not None:
                    try:
                        t[k] = str(pd.Timestamp(t[k]))
                    except Exception:
                        t[k] = str(t[k])
        return {
            "success": True,
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            "strategy": strat_id,
            "execution_type": request.execution_type,
            "metrics": result
        }
    except HTTPException:
        raise
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


@router.get("/strategies/list")
async def list_backtest_strategies(current_user: User = Depends(get_current_user)):
    """
    Get all backtest strategies categorized with details (matching the test requirements).
    """
    try:
        categories_dict = {}
        all_metadata = CoreStrategyRegistry.list_all()
        
        tier_mapping = {
            "rsi_mean_reversion": "tier_1",
            "bollinger_reversion": "tier_1",
            "zscore_reversion": "tier_1",
            "orb": "tier_1",
            "volume_breakout": "tier_1",
            "atr_expansion": "tier_1",
            
            "ma_crossover": "tier_2",
            "supertrend": "tier_2",
            "adx_trend": "tier_2",
            "donchian_breakout": "tier_2",
            "macd_crossover": "tier_2",
            "stochastic_oscillator": "tier_2",
            "price_momentum": "tier_2",
            "rsi_macd_confluence": "tier_2",
            
            "vwap_pullback": "tier_3",
            "vwap_trend": "tier_3",
            "atr_volatility_breakout": "tier_3",
        }
        
        for s in all_metadata:
            cat = s.category
            if cat not in categories_dict:
                if cat in ["Mean Reversion", "Breakout & Volatility", "Mean Reversion & Classic Breakouts"]:
                    tier = "tier_1"
                elif cat in ["Trend & Momentum", "Momentum & Trend Confirmation"]:
                    tier = "tier_2"
                else:
                    tier = "tier_3"
                
                categories_dict[cat] = {
                    "category_name": cat,
                    "strategies": [],
                    "tier": tier
                }
            
            params_formatted = {}
            for param_name, param_info in s.parameters.items():
                params_formatted[param_name] = {
                    "type": param_info.get("type", "float"),
                    "default": param_info.get("default"),
                    "min": float(param_info.get("min")) if param_info.get("min") is not None else None,
                    "max": float(param_info.get("max")) if param_info.get("max") is not None else None,
                    "description": param_info.get("description", "")
                }
                
            categories_dict[cat]["strategies"].append({
                "name": s.name,
                "display_name": s.display_name,
                "category": cat,
                "description": s.description,
                "parameters": params_formatted,
                "time_horizon": s.time_horizon,
                "tier": tier_mapping.get(s.name, categories_dict[cat]["tier"]),
                "is_implemented": True
            })
            
        return {
            "total_strategies": len(all_metadata),
            "categories": list(categories_dict.values())
        }
    except Exception as e:
        logger.error(f"Error fetching strategy list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching strategy list: {str(e)}")


@router.get("/strategies/by-tier")
async def list_strategies_by_tier(current_user: User = Depends(get_current_user)):
    """
    Get strategies grouped by tier.
    """
    try:
        all_metadata = CoreStrategyRegistry.list_all()
        
        tier_mapping = {
            "rsi_mean_reversion": "tier_1",
            "bollinger_reversion": "tier_1",
            "zscore_reversion": "tier_1",
            "orb": "tier_1",
            "volume_breakout": "tier_1",
            "atr_expansion": "tier_1",
            
            "ma_crossover": "tier_2",
            "supertrend": "tier_2",
            "adx_trend": "tier_2",
            "donchian_breakout": "tier_2",
            "macd_crossover": "tier_2",
            "stochastic_oscillator": "tier_2",
            "price_momentum": "tier_2",
            "rsi_macd_confluence": "tier_2",
            
            "vwap_pullback": "tier_3",
            "vwap_trend": "tier_3",
            "atr_volatility_breakout": "tier_3",
        }
        
        tiers = {
            "tier_1": {
                "name": "Tier 1: Mean Reversion & Classic Breakouts",
                "categories": {}
            },
            "tier_2": {
                "name": "Tier 2: Momentum & Trend Confirmation",
                "categories": {}
            },
            "tier_3": {
                "name": "Tier 3: Advanced & Structural",
                "categories": {}
            }
        }
        
        for s in all_metadata:
            cat = s.category
            
            if cat in ["Mean Reversion", "Breakout & Volatility", "Mean Reversion & Classic Breakouts"]:
                default_tier = "tier_1"
            elif cat in ["Trend & Momentum", "Momentum & Trend Confirmation"]:
                default_tier = "tier_2"
            else:
                default_tier = "tier_3"
                
            s_tier = tier_mapping.get(s.name, default_tier)
            tier_data = tiers.get(s_tier, tiers["tier_3"])
            
            if cat not in tier_data["categories"]:
                tier_data["categories"][cat] = {
                    "category_name": cat,
                    "strategies": [],
                    "tier": s_tier
                }
                
            params_formatted = {}
            for param_name, param_info in s.parameters.items():
                params_formatted[param_name] = {
                    "type": param_info.get("type", "float"),
                    "default": param_info.get("default"),
                    "min": float(param_info.get("min")) if param_info.get("min") is not None else None,
                    "max": float(param_info.get("max")) if param_info.get("max") is not None else None,
                    "description": param_info.get("description", "")
                }
                
            tier_data["categories"][cat]["strategies"].append({
                "name": s.name,
                "display_name": s.display_name,
                "category": cat,
                "description": s.description,
                "parameters": params_formatted,
                "time_horizon": s.time_horizon,
                "tier": s_tier,
                "is_implemented": True
            })
            
        for t_key in tiers:
            tiers[t_key]["categories"] = list(tiers[t_key]["categories"].values())
            
        return tiers
    except Exception as e:
        logger.error(f"Error fetching strategies by tier: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching strategies by tier: {str(e)}")


@router.get("/strategies/search")
async def search_backtest_strategies(
    query: str = Query(..., description="Search query string"),
    current_user: User = Depends(get_current_user)
):
    """
    Search backtest strategies.
    """
    query_lower = query.lower()
    all_metadata = CoreStrategyRegistry.list_all()
    results = []
    
    tier_mapping = {
        "rsi_mean_reversion": "tier_1",
        "bollinger_reversion": "tier_1",
        "zscore_reversion": "tier_1",
        "orb": "tier_1",
        "volume_breakout": "tier_1",
        "atr_expansion": "tier_1",
        
        "ma_crossover": "tier_2",
        "supertrend": "tier_2",
        "adx_trend": "tier_2",
        "donchian_breakout": "tier_2",
        "macd_crossover": "tier_2",
        "stochastic_oscillator": "tier_2",
        "price_momentum": "tier_2",
        "rsi_macd_confluence": "tier_2",
        
        "vwap_pullback": "tier_3",
        "vwap_trend": "tier_3",
        "atr_volatility_breakout": "tier_3",
    }
    
    for s in all_metadata:
        score = 0
        if query_lower in s.name.lower():
            score += 10
        if query_lower in s.display_name.lower():
            score += 15
        if query_lower in s.category.lower():
            score += 5
        if query_lower in s.description.lower():
            score += 3
            
        if score > 0:
            cat = s.category
            if cat in ["Mean Reversion", "Breakout & Volatility", "Mean Reversion & Classic Breakouts"]:
                tier = "tier_1"
            elif cat in ["Trend & Momentum", "Momentum & Trend Confirmation"]:
                tier = "tier_2"
            else:
                tier = "tier_3"
                
            results.append({
                "name": s.name,
                "display_name": s.display_name,
                "category": cat,
                "tier": tier_mapping.get(s.name, tier),
                "description": s.description,
                "relevance_score": score,
                "is_implemented": True
            })
            
    results = sorted(results, key=lambda x: x["relevance_score"], reverse=True)
    
    return {
        "query": query,
        "total_matches": len(results),
        "results": results
    }


@router.get("/strategies/{strategy_name}")
async def get_backtest_strategy_details(
    strategy_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed parameters and info for a specific backtest strategy.
    """
    s = CoreStrategyRegistry.get(strategy_name)
    if not s:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{strategy_name}' not found. Use /api/v1/backtest/strategies/list to see available strategies."
        )
        
    metadata = s.metadata
    
    tier_mapping = {
        "rsi_mean_reversion": "tier_1",
        "bollinger_reversion": "tier_1",
        "zscore_reversion": "tier_1",
        "orb": "tier_1",
        "volume_breakout": "tier_1",
        "atr_expansion": "tier_1",
        
        "ma_crossover": "tier_2",
        "supertrend": "tier_2",
        "adx_trend": "tier_2",
        "donchian_breakout": "tier_2",
        "macd_crossover": "tier_2",
        "stochastic_oscillator": "tier_2",
        "price_momentum": "tier_2",
        "rsi_macd_confluence": "tier_2",
        
        "vwap_pullback": "tier_3",
        "vwap_trend": "tier_3",
        "atr_volatility_breakout": "tier_3",
    }
    
    cat = metadata.category
    if cat in ["Mean Reversion", "Breakout & Volatility", "Mean Reversion & Classic Breakouts"]:
        tier = "tier_1"
    elif cat in ["Trend & Momentum", "Momentum & Trend Confirmation"]:
        tier = "tier_2"
    else:
        tier = "tier_3"
        
    params_formatted = {}
    for param_name, param_info in metadata.parameters.items():
        params_formatted[param_name] = {
            "type": param_info.get("type", "float"),
            "default": param_info.get("default"),
            "min": float(param_info.get("min")) if param_info.get("min") is not None else None,
            "max": float(param_info.get("max")) if param_info.get("max") is not None else None,
            "description": param_info.get("description", "")
        }
        
    return {
        "name": metadata.name,
        "display_name": metadata.display_name,
        "category": cat,
        "description": metadata.description,
        "parameters": params_formatted,
        "time_horizon": metadata.time_horizon,
        "tier": tier_mapping.get(metadata.name, tier),
        "is_implemented": True
    }


@router.get("/symbols")
async def list_quant_symbols(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of available symbols for quant backtesting.
    """
    try:
        from sqlalchemy.future import select
        from models_alpha import InstrumentMaster
        
        stmt = select(InstrumentMaster.symbol).where(InstrumentMaster.is_active == True).distinct()
        res = await db.execute(stmt)
        symbols = list(res.scalars().all())
        if not symbols:
            symbols = [
                "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", 
                "SBIN", "BHARTIARTL", "ITC", "LTIM", "HINDUNILVR",
                "AXISBANK", "LT", "BAJFINANCE", "KOTAKBANK", "MARUTI"
            ]
        return {
            "status": "success",
            "symbols": sorted(symbols),
            "count": len(symbols)
        }
    except Exception as e:
        logger.warning(f"Failed to fetch symbols in quant workspace: {e}")
        return {
            "status": "success",
            "symbols": [
                "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", 
                "SBIN", "BHARTIARTL", "ITC", "LTIM", "HINDUNILVR"
            ],
            "count": 10
        }
