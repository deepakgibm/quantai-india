"""
Enhanced Backtest Strategy API
================================
Production-ready API endpoints for strategy listing with tier organization
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from enum import Enum

# Import StrategyRegistry
from core.backtest.strategies_impl import StrategyRegistry

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class StrategyTier(str, Enum):
    """Strategy complexity tiers"""
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"


class StrategyParameter(BaseModel):
    """Strategy parameter definition"""
    type: str
    default: Any
    min: Optional[float] = None
    max: Optional[float] = None
    description: str


class StrategyInfo(BaseModel):
    """Detailed strategy information"""
    name: str
    display_name: str
    category: str
    description: str
    parameters: Dict[str, StrategyParameter]
    time_horizon: str
    tier: Optional[str] = None
    is_implemented: bool = True


class StrategyCategory(BaseModel):
    """Category of strategies"""
    category_name: str
    strategies: List[StrategyInfo]
    tier: Optional[str] = None


class StrategyListResponse(BaseModel):
    """Response for strategy listing"""
    total_strategies: int
    categories: List[StrategyCategory]
    tiers: Dict[str, int]  # Count per tier


# =============================================================================
# Helper Functions
# =============================================================================

def categorize_by_tier(category_name: str) -> str:
    """Map category name to tier"""
    tier_mapping = {
        # Tier 1: Mean Reversion & Classic Breakouts
        "Mean Reversion": "tier_1",
        "Breakout & Volatility": "tier_1",
        
        # Tier 2: Momentum & Trend Confirmation
        "Momentum & Trend Confirmation": "tier_2",
        "Trend & Momentum": "tier_2",
        
        # Tier 3: Advanced & Structural
        "Advanced & Structural Strategies": "tier_3",
        "VWAP & Institutional": "tier_3"
    }
    return tier_mapping.get(category_name, "tier_1")


def mark_implementation_status(strategy_info: Dict[str, Any]) -> Dict[str, Any]:
    """Mark whether a strategy is fully implemented"""
    not_implemented_keywords = ["NOT IMPLEMENTED", "Placeholder"]
    description = strategy_info.get("description", "")
    
    strategy_info["is_implemented"] = not any(
        keyword in description for keyword in not_implemented_keywords
    )
    return strategy_info


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/strategies/list", response_model=StrategyListResponse)
async def list_all_strategies(
    tier: Optional[str] = Query(None, description="Filter by tier: tier_1, tier_2, tier_3"),
    category: Optional[str] = Query(None, description="Filter by category name"),
    implemented_only: bool = Query(False, description="Show only implemented strategies")
):
    """
    List all available trading strategies organized by category and tier
    """
    try:
        categories_dict = StrategyRegistry.list_by_category()
        
        strategy_categories = []
        tier_counts = {"tier_1": 0, "tier_2": 0, "tier_3": 0}
        total_count = 0
        
        for cat_name, strategies in categories_dict.items():
            category_tier = categorize_by_tier(cat_name)
            
            if tier and category_tier != tier:
                continue
            
            if category and cat_name.lower() != category.lower():
                continue
            
            strategy_list = []
            for strat_meta in strategies:
                strat_info = {
                    "name": strat_meta.name,
                    "display_name": strat_meta.display_name,
                    "category": strat_meta.category,
                    "description": strat_meta.description,
                    "parameters": {
                        param_name: StrategyParameter(
                            type=param_def.get("type", "float"),
                            default=param_def.get("default"),
                            min=param_def.get("min"),
                            max=param_def.get("max"),
                            description=param_def.get("description", "")
                        )
                        for param_name, param_def in strat_meta.parameters.items()
                    },
                    "time_horizon": strat_meta.time_horizon,
                    "tier": category_tier
                }
                
                strat_info = mark_implementation_status(strat_info)
                
                if implemented_only and not strat_info["is_implemented"]:
                    continue
                
                strategy_list.append(StrategyInfo(**strat_info))
                tier_counts[category_tier] += 1
                total_count += 1
            
            if strategy_list:
                strategy_categories.append(StrategyCategory(
                    category_name=cat_name,
                    strategies=strategy_list,
                    tier=category_tier
                ))
        
        tier_order = {"tier_1": 0, "tier_2": 1, "tier_3": 2}
        strategy_categories.sort(key=lambda x: tier_order.get(x.tier, 999))
        
        return StrategyListResponse(
            total_strategies=total_count,
            categories=strategy_categories,
            tiers=tier_counts
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching strategy list: {str(e)}")


@router.get("/strategies/by-tier")
async def get_strategies_by_tier():
    """
    Get strategies organized strictly by tier
    """
    try:
        categories_dict = StrategyRegistry.list_by_category()
        
        tiers = {
            "tier_1": {"name": "Tier 1: Mean Reversion & Classic Breakouts", "categories": []},
            "tier_2": {"name": "Tier 2: Momentum & Trend Confirmation", "categories": []},
            "tier_3": {"name": "Tier 3: Advanced & Structural", "categories": []}
        }
        
        for cat_name, strategies in categories_dict.items():
            category_tier = categorize_by_tier(cat_name)
            
            strategy_list = []
            for strat_meta in strategies:
                strat_info = {
                    "name": strat_meta.name,
                    "display_name": strat_meta.display_name,
                    "category": strat_meta.category,
                    "description": strat_meta.description,
                    "parameters": {
                        param_name: {
                            "type": param_def.get("type", "float"),
                            "default": param_def.get("default"),
                            "min": param_def.get("min"),
                            "max": param_def.get("max"),
                            "description": param_def.get("description", "")
                        }
                        for param_name, param_def in strat_meta.parameters.items()
                    },
                    "time_horizon": strat_meta.time_horizon,
                    "tier": category_tier
                }
                
                strat_info = mark_implementation_status(strat_info)
                strategy_list.append(strat_info)
            
            if strategy_list:
                tiers[category_tier]["categories"].append({
                    "category_name": cat_name,
                    "strategies": strategy_list,
                    "tier": category_tier
                })
        
        return tiers
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error organizing strategies by tier: {str(e)}")


@router.get("/strategies/search")
async def search_strategies(
    query: str = Query(..., min_length=2, description="Search term"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Search for strategies
    """
    try:
        all_strategies = StrategyRegistry.list_all()
        query_lower = query.lower()
        
        results = []
        for strat_meta in all_strategies:
            score = 0
            if query_lower in strat_meta.name.lower(): score += 10
            if query_lower in strat_meta.display_name.lower(): score += 8
            if query_lower in strat_meta.category.lower(): score += 5
            if query_lower in strat_meta.description.lower(): score += 3
            
            if score > 0:
                category_tier = categorize_by_tier(strat_meta.category)
                result = {
                    "name": strat_meta.name,
                    "display_name": strat_meta.display_name,
                    "category": strat_meta.category,
                    "tier": category_tier,
                    "description": strat_meta.description,
                    "relevance_score": score
                }
                result = mark_implementation_status(result)
                results.append(result)
        
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return {"query": query, "total_matches": len(results), "results": results[:limit]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching strategies: {str(e)}")


@router.get("/strategies/{strategy_name}")
async def get_strategy_details(strategy_name: str):
    """
    Get detailed information about a specific strategy
    """
    try:
        strategy = StrategyRegistry.get(strategy_name)
        
        if not strategy:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not found. Use /api/v1/backtest/strategies/list to see available strategies."
            )
        
        metadata = strategy.metadata
        category_tier = categorize_by_tier(metadata.category)
        
        strategy_detail = {
            "name": metadata.name,
            "display_name": metadata.display_name,
            "category": metadata.category,
            "tier": category_tier,
            "description": metadata.description,
            "time_horizon": metadata.time_horizon,
            "parameters": {
                param_name: {
                    "type": param_def.get("type", "float"),
                    "default": param_def.get("default"),
                    "min": param_def.get("min"),
                    "max": param_def.get("max"),
                    "description": param_def.get("description", "")
                }
                for param_name, param_def in metadata.parameters.items()
            }
        }
        
        strategy_detail = mark_implementation_status(strategy_detail)
        return strategy_detail
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching strategy details: {str(e)}")
