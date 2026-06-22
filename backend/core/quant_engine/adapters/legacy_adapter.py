"""
Legacy Strategy Adapter
Adapts standard backtest or experiment lab strategies to the new UnifiedStrategy protocol.
"""

from typing import Dict, Any, Optional
import pandas as pd

from ..strategy.base import UnifiedStrategy, StrategyMetadata, SignalResult, SignalType


class LegacyStrategyAdapter(UnifiedStrategy):
    """
    Polymorphic adapter wrapping legacy strategies.
    Delegates signal generation and bar events to legacy methods.
    """

    def __init__(self, legacy_strategy_instance: Any):
        self.legacy = legacy_strategy_instance
        super().__init__(getattr(legacy_strategy_instance, "params", {}))

    @property
    def metadata(self) -> StrategyMetadata:
        # Check if legacy metadata exists
        leg_meta = getattr(self.legacy, "metadata", None)
        if leg_meta:
            return StrategyMetadata(
                name=getattr(leg_meta, "name", "legacy_strategy"),
                display_name=getattr(leg_meta, "display_name", "Legacy Strategy"),
                category=getattr(leg_meta, "category", "Legacy"),
                description=getattr(leg_meta, "description", ""),
                parameters=getattr(leg_meta, "parameters", {}),
                time_horizon=getattr(leg_meta, "time_horizon", "Swing")
            )
        
        # Check Experiment Lab strategy metadata
        leg_info = getattr(self.legacy, "info", None)
        if leg_info:
            return StrategyMetadata(
                name=getattr(leg_info, "name", "legacy_strategy").lower().replace(" ", "_"),
                display_name=getattr(leg_info, "name", "Legacy Strategy"),
                category=getattr(leg_info, "category", "Legacy").value if hasattr(getattr(leg_info, "category"), "value") else str(getattr(leg_info, "category")),
                description=getattr(leg_info, "description", ""),
                parameters={},
                time_horizon="Swing"
            )

        # Fallback default metadata
        return StrategyMetadata(
            name="legacy_strategy",
            display_name="Legacy Strategy",
            category="Legacy",
            description="Adapted legacy strategy",
            parameters={},
            time_horizon="Swing"
        )

    def preload_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        # If legacy class has a custom calculation logic, trigger it
        if hasattr(self.legacy, "calculate_indicators"):
            return self.legacy.calculate_indicators(df)
        return df.copy()

    def generate_signals_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        # For standard backtest strategies
        if hasattr(self.legacy, "generate_signals"):
            try:
                return self.legacy.generate_signals(df, self.params)
            except TypeError:
                # If experiment lab strategy, generate_signals(df) takes no params
                # Returns List[SignalResult]
                res_signals = self.legacy.generate_signals(df)
                df_out = df.copy()
                df_out["signal"] = "HOLD"
                for sig in res_signals:
                    # Find closest timestamp index
                    ts = sig.timestamp
                    mask = df_out["timestamp"] == ts
                    if mask.any():
                        df_out.loc[mask, "signal"] = sig.signal.value
                return df_out
        return df.copy()

    def on_bar(
        self,
        bar: pd.Series,
        history: pd.DataFrame,
        positions: Dict[str, Any],
        executor: Any
    ) -> Optional[SignalResult]:
        # For standard event-driven backtest strategies
        if hasattr(self.legacy, "on_bar"):
            # Existing legacy on_bar signature: on_bar(bar, history, positions, executor)
            legacy_sig = self.legacy.on_bar(bar, history, positions, executor)
            if legacy_sig:
                # Translate legacy signals
                sig_type = SignalType.HOLD
                if getattr(legacy_sig, "signal", None) == "BUY" or getattr(legacy_sig, "signal", None) == SignalType.BUY:
                    sig_type = SignalType.BUY
                elif getattr(legacy_sig, "signal", None) == "SELL" or getattr(legacy_sig, "signal", None) == SignalType.SELL:
                    sig_type = SignalType.SELL
                elif getattr(legacy_sig, "signal", None) == "EXIT" or getattr(legacy_sig, "signal", None) == SignalType.EXIT:
                    sig_type = SignalType.EXIT
                    
                return SignalResult(
                    timestamp=bar['timestamp'],
                    signal=sig_type,
                    price=float(bar['close']),
                    stop_loss=getattr(legacy_sig, "stop_loss", None),
                    take_profit=getattr(legacy_sig, "target_1", None) or getattr(legacy_sig, "take_profit", None),
                    reason=getattr(legacy_sig, "reason", "")
                )
        
        # For Experiment Lab strategies, run batch signals first and retrieve matching timestamp signal
        df_bar = pd.DataFrame([bar])
        df_sig = self.generate_signals_batch(df_bar)
        sig_str = df_sig["signal"].iloc[0] if not df_sig.empty else "HOLD"
        
        if sig_str != "HOLD":
            return SignalResult(
                timestamp=bar['timestamp'],
                signal=SignalType(sig_str),
                price=float(bar['close'])
            )
            
        return None
