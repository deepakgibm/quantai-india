"""
Cost Model for Backtesting
Production-grade transaction cost modeling for NSE Cash Segment
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class CostConfig:
    """
    NSE Cash Segment Transaction Costs
    Based on SEBI-regulated charges
    """
    # Brokerage (varies by broker, using standard discount broker rates)
    brokerage_rate: float = 0.0003  # 0.03% per side
    
    # STT (Securities Transaction Tax)
    stt_buy: float = 0.0  # No STT on buy for delivery
    stt_sell: float = 0.001  # 0.1% on sell for delivery (intraday: 0.025%)
    stt_intraday_sell: float = 0.00025  # 0.025% on sell for intraday
    
    # Exchange Transaction Charges (NSE)
    exchange_txn_charge: float = 0.0000345  # 0.00345%
    
    # SEBI Turnover Fee
    sebi_fee: float = 0.000001  # 0.0001%
    
    # GST on brokerage + exchange charges (18%)
    gst_rate: float = 0.18
    
    # Stamp Duty (on buy side only)
    stamp_duty_rate: float = 0.00015  # 0.015% on buy
    
    # Slippage model
    slippage_rate: float = 0.001  # 0.1% default slippage
    slippage_volume_factor: float = 0.0001  # Additional slippage per 1L volume


@dataclass
class TransactionCost:
    """Result of cost calculation"""
    brokerage: float
    stt: float
    exchange_charges: float
    sebi_fee: float
    gst: float
    stamp_duty: float
    slippage: float
    total: float


class CostCalculator:
    """
    Calculate realistic transaction costs for NSE trades
    """
    
    def __init__(self, config: Optional[CostConfig] = None):
        self.config = config or CostConfig()
    
    def calculate(
        self,
        price: float,
        quantity: int,
        side: OrderSide,
        is_intraday: bool = False,
        avg_volume: Optional[float] = None
    ) -> TransactionCost:
        """
        Calculate all transaction costs for a trade
        
        Args:
            price: Trade price per share
            quantity: Number of shares
            side: BUY or SELL
            is_intraday: True for intraday trades
            avg_volume: Average daily volume for slippage calculation
            
        Returns:
            TransactionCost with breakdown
        """
        turnover = price * quantity
        
        # Brokerage
        brokerage = turnover * self.config.brokerage_rate
        
        # STT
        if side == OrderSide.SELL:
            if is_intraday:
                stt = turnover * self.config.stt_intraday_sell
            else:
                stt = turnover * self.config.stt_sell
        else:
            stt = turnover * self.config.stt_buy
        
        # Exchange charges
        exchange_charges = turnover * self.config.exchange_txn_charge
        
        # SEBI fee
        sebi_fee = turnover * self.config.sebi_fee
        
        # GST (on brokerage + exchange charges)
        gst = (brokerage + exchange_charges) * self.config.gst_rate
        
        # Stamp duty (only on buy side)
        if side == OrderSide.BUY:
            stamp_duty = turnover * self.config.stamp_duty_rate
        else:
            stamp_duty = 0.0
        
        # Slippage estimation
        slippage = self._calculate_slippage(price, quantity, avg_volume)
        
        total = brokerage + stt + exchange_charges + sebi_fee + gst + stamp_duty + slippage
        
        return TransactionCost(
            brokerage=round(brokerage, 2),
            stt=round(stt, 2),
            exchange_charges=round(exchange_charges, 2),
            sebi_fee=round(sebi_fee, 2),
            gst=round(gst, 2),
            stamp_duty=round(stamp_duty, 2),
            slippage=round(slippage, 2),
            total=round(total, 2)
        )
    
    def _calculate_slippage(
        self,
        price: float,
        quantity: int,
        avg_volume: Optional[float]
    ) -> float:
        """
        Estimate slippage based on order size vs average volume
        """
        base_slippage = price * quantity * self.config.slippage_rate
        
        if avg_volume and avg_volume > 0:
            # Additional slippage for large orders relative to volume
            order_impact = quantity / avg_volume
            volume_slippage = price * quantity * self.config.slippage_volume_factor * order_impact
            return base_slippage + volume_slippage
        
        return base_slippage
    
    def get_effective_buy_price(
        self,
        price: float,
        quantity: int,
        is_intraday: bool = False,
        avg_volume: Optional[float] = None
    ) -> float:
        """Get effective price including all costs for a buy order"""
        costs = self.calculate(price, quantity, OrderSide.BUY, is_intraday, avg_volume)
        return price + (costs.total / quantity)
    
    def get_effective_sell_price(
        self,
        price: float,
        quantity: int,
        is_intraday: bool = False,
        avg_volume: Optional[float] = None
    ) -> float:
        """Get effective price after all costs for a sell order"""
        costs = self.calculate(price, quantity, OrderSide.SELL, is_intraday, avg_volume)
        return price - (costs.total / quantity)
    
    def calculate_round_trip_cost(
        self,
        buy_price: float,
        sell_price: float,
        quantity: int,
        is_intraday: bool = False
    ) -> float:
        """Calculate total round-trip transaction cost"""
        buy_cost = self.calculate(buy_price, quantity, OrderSide.BUY, is_intraday)
        sell_cost = self.calculate(sell_price, quantity, OrderSide.SELL, is_intraday)
        return buy_cost.total + sell_cost.total
