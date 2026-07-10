import sys
from pathlib import Path

swarm_engine_dir = Path(__file__).resolve().parent
if str(swarm_engine_dir) not in sys.path:
    sys.path.insert(0, str(swarm_engine_dir))
