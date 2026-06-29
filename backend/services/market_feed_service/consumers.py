import asyncio
import json
import logging
import os
from collections import defaultdict, deque
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from services.dragonfly_client import get_cache
from utils.symbol_utils import get_stock_sector

logger = logging.getLogger(__name__)

class KafkaConsumerGroup:
    def __init__(self, bootstrap_servers: str = None):
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        self.cache = get_cache()
        self._running = False
        self._tasks = []
        self._producer = None
        self._closes = defaultdict(lambda: deque(maxlen=100))

    async def start(self):
        self._running = True
        logger.info(f"Starting Kafka Consumers connected to {self.bootstrap_servers}")
        
        # Start a local producer for consumers that publish events (PriceConsumer, ScannerConsumer)
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        try:
            await self._producer.start()
            logger.info("Consumers' internal producer started successfully")
        except Exception as e:
            logger.warning(f"Failed to start consumers' internal producer: {e}. Event publishing might fail.")

        # Launch the four consumer loops
        self._tasks.append(asyncio.create_task(self._run_price_consumer()))
        self._tasks.append(asyncio.create_task(self._run_indicator_consumer()))
        self._tasks.append(asyncio.create_task(self._run_sector_consumer()))
        self._tasks.append(asyncio.create_task(self._run_scanner_consumer()))

    async def stop(self):
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._producer:
            await self._producer.stop()
        logger.info("Kafka Consumers stopped")

    async def _run_price_consumer(self):
        """PriceConsumer: ticks.raw -> price:{symbol} (Dragonfly) & ticks.processed (Kafka)"""
        attempt = 0
        while self._running:
            try:
                consumer = AIOKafkaConsumer(
                    "ticks.raw",
                    bootstrap_servers=self.bootstrap_servers,
                    group_id="price-consumer-group",
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    auto_offset_reset="latest"
                )
                await consumer.start()
                attempt = 0
                logger.info("PriceConsumer started successfully")
                
                async for msg in consumer:
                    if not self._running:
                        break
                    tick = msg.value
                    symbol = tick.get("symbol")
                    if not symbol:
                        continue
                    
                    ltp = tick.get("ltp") or tick.get("last_price") or 0.0
                    volume = tick.get("volume") or 0
                    change_pct = tick.get("change_percent") or tick.get("change_pct") or 0.0
                    timestamp = tick.get("timestamp") or ""
                    
                    normalized_tick = {
                        "symbol": symbol,
                        "ltp": ltp,
                        "volume": volume,
                        "change_percent": change_pct,
                        "timestamp": timestamp
                    }
                    
                    # Persist to Dragonfly (both new and legacy keys for compatibility)
                    try:
                        await self.cache.set_async(f"price:{symbol}", normalized_tick, ttl=300)
                        await self.cache.set_async(f"qai:tick:{symbol}", normalized_tick, ttl=300)
                    except Exception as ce:
                        logger.error(f"PriceConsumer: Failed to persist to Dragonfly: {ce}")
                    
                    # Publish to ticks.processed
                    if self._producer:
                        await self._producer.send("ticks.processed", normalized_tick)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                attempt += 1
                wait_time = min(30, 2 ** attempt)
                logger.error(f"PriceConsumer encountered error: {e}. Retrying in {wait_time}s")
                await asyncio.sleep(wait_time)

    async def _run_indicator_consumer(self):
        """IndicatorConsumer: ticks.processed -> Indicator updates"""
        attempt = 0
        while self._running:
            try:
                consumer = AIOKafkaConsumer(
                    "ticks.processed",
                    bootstrap_servers=self.bootstrap_servers,
                    group_id="indicator-consumer-group",
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    auto_offset_reset="latest"
                )
                await consumer.start()
                attempt = 0
                logger.info("IndicatorConsumer started successfully")
                
                async for msg in consumer:
                    if not self._running:
                        break
                    tick = msg.value
                    symbol = tick.get("symbol")
                    ltp = tick.get("ltp", 0.0)
                    
                    # Update local price history
                    self._closes[symbol].append(ltp)
                    
                    # Calculate real rolling RSI and MACD
                    closes_list = list(self._closes[symbol])
                    rsi_val = 50.0
                    macd_val = 0.0
                    
                    if len(closes_list) >= 15:
                        # Compute rolling RSI (simple calculation)
                        gains = 0.0
                        losses = 0.0
                        for i in range(1, len(closes_list[-15:])):
                            diff = closes_list[-15:][i] - closes_list[-15:][i-1]
                            if diff > 0:
                                gains += diff
                            else:
                                losses += abs(diff)
                        rs = gains / losses if losses > 0 else 999.0
                        rsi_val = 100.0 - (100.0 / (1.0 + rs))
                        
                    if len(closes_list) >= 26:
                        # Compute rolling MACD (simple EMA difference)
                        ema12 = closes_list[-1]
                        ema26 = closes_list[-1]
                        mult12 = 2.0 / 13.0
                        mult26 = 2.0 / 27.0
                        
                        for price in closes_list[-12:]:
                            ema12 = price * mult12 + ema12 * (1.0 - mult12)
                        for price in closes_list[-26:]:
                            ema26 = price * mult26 + ema26 * (1.0 - mult26)
                        macd_val = ema12 - ema26
                        
                    # Update local/Dragonfly indicator snapshot
                    ind_key = f"qai:ind:{symbol}:live"
                    ind_data = {
                        "symbol": symbol,
                        "ltp": ltp,
                        "rsi_14": round(rsi_val, 2),
                        "macd": round(macd_val, 3),
                        "timestamp": tick.get("timestamp")
                    }
                    try:
                        await self.cache.set_async(ind_key, ind_data, ttl=60)
                    except Exception as ce:
                        logger.error(f"IndicatorConsumer: Failed to update cache: {ce}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                attempt += 1
                wait_time = min(30, 2 ** attempt)
                logger.error(f"IndicatorConsumer encountered error: {e}. Retrying in {wait_time}s")
                await asyncio.sleep(wait_time)

    async def _run_sector_consumer(self):
        """SectorConsumer: ticks.processed -> sector.performance"""
        attempt = 0
        sector_prices = {} # sector -> list of change percents
        
        while self._running:
            try:
                consumer = AIOKafkaConsumer(
                    "ticks.processed",
                    bootstrap_servers=self.bootstrap_servers,
                    group_id="sector-consumer-group",
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    auto_offset_reset="latest"
                )
                await consumer.start()
                attempt = 0
                logger.info("SectorConsumer started successfully")
                
                async for msg in consumer:
                    if not self._running:
                        break
                    tick = msg.value
                    symbol = tick.get("symbol")
                    change_pct = tick.get("change_percent", 0.0)
                    
                    sector = get_stock_sector(symbol)
                    if not sector:
                        continue
                    
                    if sector not in sector_prices:
                        sector_prices[sector] = []
                    
                    # Keep a rolling window of last 10 ticks for each sector
                    sector_prices[sector].append(change_pct)
                    if len(sector_prices[sector]) > 10:
                        sector_prices[sector].pop(0)
                        
                    avg_performance = sum(sector_prices[sector]) / len(sector_prices[sector])
                    
                    sector_metric = {
                        "sector": sector,
                        "avg_change_pct": round(avg_performance, 2),
                        "timestamp": tick.get("timestamp")
                    }
                    
                    # Persist sector snapshots in cache
                    try:
                        await self.cache.set_async(f"qai:sector:{sector}", sector_metric, ttl=300)
                    except Exception as ce:
                        logger.error(f"SectorConsumer: Failed to update cache: {ce}")
                        
                    # Publish sector metrics to Kafka sector.performance topic
                    if self._producer:
                        await self._producer.send("sector.performance", sector_metric)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                attempt += 1
                wait_time = min(30, 2 ** attempt)
                logger.error(f"SectorConsumer encountered error: {e}. Retrying in {wait_time}s")
                await asyncio.sleep(wait_time)

    async def _run_scanner_consumer(self):
        """ScannerConsumer: ticks.processed -> runs scans -> signals.breakout, signals.vcp, signals.momentum"""
        attempt = 0
        while self._running:
            try:
                consumer = AIOKafkaConsumer(
                    "ticks.processed",
                    bootstrap_servers=self.bootstrap_servers,
                    group_id="scanner-consumer-group",
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    auto_offset_reset="latest"
                )
                await consumer.start()
                attempt = 0
                logger.info("ScannerConsumer started successfully")
                
                async for msg in consumer:
                    if not self._running:
                        break
                    tick = msg.value
                    symbol = tick.get("symbol")
                    ltp = tick.get("ltp", 0.0)
                    change_pct = tick.get("change_percent", 0.0)
                    
                    # Simple breakout/VCP/momentum mock condition checker
                    # E.g. if change_percent > 3% breakout, if > 5% momentum, etc.
                    if change_pct > 3.0:
                        signal = {
                            "symbol": symbol,
                            "signal_type": "breakout",
                            "price": ltp,
                            "change_percent": change_pct,
                            "timestamp": tick.get("timestamp"),
                            "details": "Price breakout detected on high relative intraday move"
                        }
                        if self._producer:
                            await self._producer.send("signals.breakout", signal)
                            
                    if change_pct > 5.0:
                        signal = {
                            "symbol": symbol,
                            "signal_type": "momentum",
                            "price": ltp,
                            "change_percent": change_pct,
                            "timestamp": tick.get("timestamp"),
                            "details": "Strong positive momentum detected"
                        }
                        if self._producer:
                            await self._producer.send("signals.momentum", signal)
                            
                    # Mock VCP detection: tight range followed by a volume increase
                    if 0.1 < abs(change_pct) < 0.5:
                        signal = {
                            "symbol": symbol,
                            "signal_type": "vcp",
                            "price": ltp,
                            "change_percent": change_pct,
                            "timestamp": tick.get("timestamp"),
                            "details": "Volatility contraction consolidation observed"
                        }
                        if self._producer:
                            await self._producer.send("signals.vcp", signal)
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                attempt += 1
                wait_time = min(30, 2 ** attempt)
                logger.error(f"ScannerConsumer encountered error: {e}. Retrying in {wait_time}s")
                await asyncio.sleep(wait_time)
