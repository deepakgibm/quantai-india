import json
import logging
import os
import asyncio
from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

class KafkaProducerWrapper:
    def __init__(self, bootstrap_servers: str = None):
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        self.producer = None
        self._connected = False

    async def start(self):
        logger.info(f"Starting Kafka producer pointing to {self.bootstrap_servers}")
        attempt = 0
        while not self._connected:
            try:
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8")
                )
                await self.producer.start()
                self._connected = True
                logger.info("Kafka producer started successfully")
            except Exception as e:
                attempt += 1
                wait_time = min(30, 2 ** attempt)
                logger.warning(f"Failed to start Kafka producer (attempt {attempt}): {e}. Retrying in {wait_time}s")
                await asyncio.sleep(wait_time)

    async def stop(self):
        if self.producer and self._connected:
            await self.producer.stop()
            self._connected = False
            logger.info("Kafka producer stopped")

    async def send_msg(self, topic: str, value: dict):
        if not self._connected or not self.producer:
            logger.warning(f"Kafka producer not connected. Dropping message for topic {topic}")
            return
        try:
            await self.producer.send(topic, value)
        except Exception as e:
            logger.error(f"Failed to send message to Kafka topic {topic}: {e}")
