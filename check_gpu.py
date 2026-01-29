import torch
import logging
import sys
import psutil

def check_gpu_readiness():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("GPUReady")
    
    logger.info("🛠️ Checking GPU Readiness for QuantAI...")
    
    # 1. PyTorch CUDA check
    cuda_available = torch.cuda.is_available()
    logger.info(f"PyTorch CUDA: {'✅ Available' if cuda_available else '❌ Not Available'}")
    
    if cuda_available:
        device_count = torch.cuda.device_count()
        logger.info(f"Devices detected: {device_count}")
        for i in range(device_count):
            props = torch.cuda.get_device_properties(i)
            logger.info(f"  [{i}] {props.name} | Mem: {props.total_memory / 1024**3:.2f} GB | CC: {props.major}.{props.minor}")
    else:
        logger.warning("No NVIDIA GPU found or CUDA not installed. Model will train on CPU.")
        
    # 2. System RAM check
    ram = psutil.virtual_memory()
    logger.info(f"System RAM: {ram.total / 1024**3:.2f} GB (Available: {ram.available / 1024**3:.2f} GB)")
    
    # 3. Recommendations
    if cuda_available:
        logger.info("💡 Recommendation: Use --batch 256 or higher for training.")
    else:
        logger.info("💡 Recommendation: Limit --batch to 32-64 for CPU training.")
        
    return cuda_available

if __name__ == "__main__":
    check_gpu_readiness()
