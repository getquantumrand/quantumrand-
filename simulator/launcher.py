"""
Launches the quantum simulator in a background thread.
Called from FastAPI lifespan when PILOTOS_ENABLED is True.
"""

import os
import sys
import threading
import time
import logging

logger = logging.getLogger("quantumrand")

_server = None
_thread = None


def start_simulator(port: int = 7100):
    """Start the superconducting quantum simulator on the given port."""
    global _server, _thread

    if _server is not None:
        logger.info("Simulator already running")
        return

    # Add simulator package to path so its internal imports work
    sim_dir = os.path.dirname(os.path.abspath(__file__))
    if sim_dir not in sys.path:
        sys.path.insert(0, sim_dir)

    from config import QuantumSystemType, ServerConfig

    # Override ports to avoid conflicts
    ServerConfig.ROUTER_PORTS[QuantumSystemType.SUPERCONDUCTING] = port
    ServerConfig.PUB_PORTS[QuantumSystemType.SUPERCONDUCTING] = port + 1000
    ServerConfig.BIND_ADDRESS = "127.0.0.1"
    ServerConfig.LOG_LEVEL = "WARNING"

    from zmq_router_server import ZmqRouterServer

    server = ZmqRouterServer(QuantumSystemType.SUPERCONDUCTING)

    def _run():
        try:
            server.start()
            logger.info(f"Quantum simulator started on port {port}")
            while _server is not None:
                time.sleep(1)
        except Exception as e:
            logger.error(f"Simulator failed: {e}")

    _server = server
    _thread = threading.Thread(target=_run, daemon=True)
    _thread.start()

    # Give it a moment to bind
    time.sleep(0.5)
    logger.info(f"Quantum simulator ready on 127.0.0.1:{port}")


def stop_simulator():
    """Stop the simulator."""
    global _server, _thread
    if _server is not None:
        _server.stop()
        _server = None
        _thread = None
        logger.info("Quantum simulator stopped")
