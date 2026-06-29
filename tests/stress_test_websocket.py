import asyncio
import time
import json
import logging
import argparse
import sys
import websockets
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("WSStressTest")

# Metrics collectors
total_messages = 0
total_errors = 0
latencies = []
active_connections = 0

async def client_worker(client_id: int, uri: str, duration: int):
    global total_messages, total_errors, active_connections
    
    start_time = time.time()
    end_time = start_time + duration
    
    logger.debug(f"Client {client_id} attempting connection to {uri}")
    try:
        async with websockets.connect(uri) as ws:
            active_connections += 1
            logger.debug(f"Client {client_id} connected.")
            
            while time.time() < end_time:
                try:
                    # Set a timeout so we can exit when duration expires
                    message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    total_messages += 1
                    
                    # Parse timestamp to measure latency
                    data = json.loads(message)
                    if "timestamp" in data:
                        try:
                            # Payload format: datetime.now().isoformat()
                            ts = datetime.fromisoformat(data["timestamp"])
                            latency = (datetime.now() - ts).total_seconds() * 1000.0 # ms
                            latencies.append(latency)
                        except Exception:
                            pass
                            
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    total_errors += 1
                    logger.debug(f"Client {client_id} receive error: {e}")
                    break
            
            active_connections -= 1
            logger.debug(f"Client {client_id} session completed.")
    except Exception as e:
        total_errors += 1
        logger.warning(f"Client {client_id} failed to connect: {e}")

async def run_stress_test(uri: str, concurrency: int, duration: int):
    global total_messages, total_errors, latencies, active_connections
    
    logger.info(f"🚀 Starting Stress Test:")
    logger.info(f"   Target URI:   {uri}")
    logger.info(f"   Concurrency:  {concurrency} active clients")
    logger.info(f"   Duration:     {duration} seconds")
    
    start_time = time.time()
    
    # Spawn tasks
    tasks = []
    for i in range(concurrency):
        tasks.append(asyncio.create_task(client_worker(i, uri, duration)))
        
    # Wait for completion
    await asyncio.gather(*tasks)
    
    total_duration = time.time() - start_time
    
    # Calculate statistics
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    throughput = total_messages / total_duration if total_duration > 0 else 0.0
    
    # Print results
    print("\n" + "="*50)
    print("           WEBSOCKET STRESS TEST RESULTS")
    print("="*50)
    print(f"Test Duration:         {total_duration:.2f} seconds")
    print(f"Target Concurrency:    {concurrency} clients")
    print(f"Max Active Conns:      {concurrency - active_connections} closed gracefully")
    print(f"Total Messages Recv:   {total_messages}")
    print(f"Throughput:            {throughput:.2f} messages/sec")
    print(f"Average Latency:       {avg_latency:.2f} ms")
    print(f"Total Errors/Drops:    {total_errors}")
    print(f"Success Connection %:  {(concurrency - total_errors) / concurrency * 100:.1f}%" if concurrency > 0 else "0%")
    print("="*50 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebSocket Stress Test Runner")
    parser.add_argument("--uri", default="ws://localhost:8000/api/scanner/ws", help="Target WS URI")
    parser.add_argument("--concurrency", type=int, default=50, help="Number of concurrent clients")
    parser.add_argument("--duration", type=int, default=10, help="Test duration in seconds")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_stress_test(args.uri, args.concurrency, args.duration))
    except KeyboardInterrupt:
        logger.info("Stress test interrupted by user.")
        sys.exit(0)
