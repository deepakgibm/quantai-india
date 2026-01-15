import asyncio
import logging
from datetime import datetime
from services.yearly_breakout_engine import YearlyBreakoutEngine

logger = logging.getLogger(__name__)

class YearlyBreakoutWorker:
    def __init__(self, interval_seconds: int = 3600):
        self.engine = YearlyBreakoutEngine()
        self.interval_seconds = interval_seconds
        self.is_running = False

    async def start(self):
        """Start the background worker."""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info(f"Yearly Breakout Worker started. Running every {self.interval_seconds} seconds.")
        
        while self.is_running:
            import time
            start_perf = time.perf_counter()
            try:
                start_time = datetime.now()
                logger.info(f"Worker iteration started at {start_time}")
                
                await self.engine.run_scanner()
                
                duration_perf = time.perf_counter() - start_perf
                end_time = datetime.now()
                logger.info(f"Worker iteration completed in {duration_perf:.2f} seconds.")
                
                # Record metrics
                try:
                    from core.observability.metrics import get_metrics
                    get_metrics().record_worker_job("yearly_breakout", duration_perf, True)
                except ImportError:
                    pass
                
                # Sleep for the remaining interval
                duration_total = (end_time - start_time).total_seconds()
                sleep_time = max(0, self.interval_seconds - duration_total)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                duration_perf = time.perf_counter() - start_perf
                logger.error(f"Error in Yearly Breakout Worker iteration: {e}")
                
                # Record metrics
                try:
                    from core.observability.metrics import get_metrics
                    get_metrics().record_worker_job("yearly_breakout", duration_perf, False)
                except ImportError:
                    pass
                    
                await asyncio.sleep(60) # Retry after 1 minute if error

    def stop(self):
        """Stop the background worker."""
        self.is_running = False
        logger.info("Yearly Breakout Worker stopping...")

if __name__ == "__main__":
    # Test run
    logging.basicConfig(level=logging.INFO)
    worker = YearlyBreakoutWorker(interval_seconds=3600)
    asyncio.run(worker.start())
