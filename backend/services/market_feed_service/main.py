"""
Market Feed Service — main.py
FastAPI standalone microservice maintaining WebSocket connection to Upstox,
decoding Protobuf ticks, publishing to Kafka, and consuming via specialized consumers.
"""

import logging
from fastapi import FastAPI
from services.market_feed_service.producer import KafkaProducerWrapper
from services.market_feed_service.feed_client import UpstoxFeedClient
from services.market_feed_service.consumers import KafkaConsumerGroup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("market_feed_service")

app = FastAPI(title="QuantAI Market Feed Service")

# Initialize components
producer = KafkaProducerWrapper()
feed_client = UpstoxFeedClient(producer=producer)
consumer_group = KafkaConsumerGroup()

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Market Feed Service...")
    
    # 1. Start Kafka Producer
    await producer.start()
    
    # 2. Start WebSocket Feed Client
    await feed_client.start()
    
    # 3. Start Kafka Consumers
    await consumer_group.start()
    
    logger.info("Market Feed Service components initialized and running")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Market Feed Service...")
    
    # 1. Stop Feed Client
    await feed_client.stop()
    
    # 2. Stop Consumers
    await consumer_group.stop()
    
    # 3. Stop Producer
    await producer.stop()
    
    logger.info("Market Feed Service shutdown complete")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "online",
        "ws_connected": feed_client.ws is not None and feed_client.is_running,
        "is_running": feed_client.is_running,
        "subscribed_symbols_count": len(feed_client.subscribed_symbols)
    }

@app.get("/status")
async def get_status():
    """Detailed status endpoint."""
    return {
        "is_running": feed_client.is_running,
        "subscribed_count": len(feed_client.subscribed_symbols),
        "subscribed_symbols": list(feed_client.subscribed_symbols)[:20]  # Return first 20
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
