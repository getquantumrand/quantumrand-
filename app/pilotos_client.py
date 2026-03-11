"""
Origin Quantum Python Simulator client using ZMQ DEALER protocol.

Connects to the Python quantum simulator (superconducting mode)
which uses a ZMQ Router-Dealer pattern:
  - Submit task via MsgTask → receive MsgTaskAck
  - Receive MsgTaskResult asynchronously with Key/ProbCount arrays
"""

import json
import time
import uuid
import logging
from typing import Optional

import zmq

logger = logging.getLogger("quantumrand")

RECV_TIMEOUT = 15000  # ms


class PilotOSClient:
    """ZMQ DEALER client for Origin Quantum Python Simulator."""

    def __init__(self, host: str, port: int, api_key: str = ""):
        self.host = host
        self.port = port
        self._context: Optional[zmq.Context] = None
        self._socket: Optional[zmq.Socket] = None
        self._sn = 0

    def _ensure_connected(self):
        """Lazily connect to the ZMQ server."""
        if self._socket is not None:
            return
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.DEALER)
        self._socket.setsockopt_string(
            zmq.IDENTITY, f"quantumrand-{uuid.uuid4().hex[:8]}"
        )
        self._socket.setsockopt(zmq.RCVTIMEO, RECV_TIMEOUT)
        self._socket.setsockopt(zmq.LINGER, 0)
        addr = f"tcp://{self.host}:{self.port}"
        self._socket.connect(addr)
        logger.info(f"Connected to quantum simulator at {addr}")

    def _next_sn(self) -> int:
        self._sn += 1
        return self._sn

    def _send(self, request: dict):
        """Send a request (fire-and-forget)."""
        self._ensure_connected()
        request["SN"] = self._next_sn()
        self._socket.send_string(json.dumps(request))

    def _recv(self) -> dict:
        """Receive one message."""
        try:
            return json.loads(self._socket.recv_string())
        except zmq.Again:
            raise TimeoutError("Quantum simulator did not respond in time")

    def _recv_until(self, msg_type: str, task_id: str) -> dict:
        """
        Keep receiving messages until we get one matching the expected
        MsgType and TaskId. Discards ACKs and unrelated messages.
        """
        deadline = time.time() + (RECV_TIMEOUT / 1000.0)
        while time.time() < deadline:
            msg = self._recv()
            if msg.get("MsgType") == msg_type and msg.get("TaskId") == task_id:
                return msg
            # Log and skip non-matching messages (ACKs, status updates, etc.)
            logger.debug(f"Skipping message: {msg.get('MsgType')}")
        raise TimeoutError(f"Timed out waiting for {msg_type} for task {task_id}")

    def run_circuit(
        self,
        num_qubits: int,
        shots: int = 1000,
        use_real_chip: bool = False,
    ) -> dict:
        """
        Submit a quantum task and return measurement results.

        Returns dict of {bitstring: count}, e.g. {'010': 123, '101': 877}.
        """
        task_id = str(uuid.uuid4())

        # Build gate list: H on all qubits, then measure
        gates = []
        for i in range(num_qubits):
            gates.append({"H": [i]})
        for i in range(num_qubits):
            gates.append({"Measure": [[i]]})

        request = {
            "MsgType": "MsgTask",
            "TaskId": task_id,
            "ConvertQProg": json.dumps([[gates]]),
            "Configure": {
                "Shot": shots,
                "MeasureQubitNum": [num_qubits],
                "TaskPriority": 0,
                "IsExperiment": False,
                "PointLabel": 128,
            },
        }

        self._send(request)

        # Wait for MsgTaskResult with our task_id (skip ACKs automatically)
        result = self._recv_until("MsgTaskResult", task_id)

        if result.get("ErrCode", -1) != 0:
            raise RuntimeError(
                f"Simulator task failed: {result.get('ErrInfo', result)}"
            )

        return self._parse_result(result, num_qubits)

    @staticmethod
    def _parse_result(data: dict, num_qubits: int) -> dict:
        """Parse MsgTaskResult into {bitstring: count} dict."""
        keys = data.get("Key", [])
        counts = data.get("ProbCount", [])

        if not keys or not counts:
            raise RuntimeError(f"Empty result from simulator: {data}")

        key_list = keys[0] if keys and isinstance(keys[0], list) else keys
        count_list = counts[0] if counts and isinstance(counts[0], list) else counts

        result = {}
        for hex_val, count in zip(key_list, count_list):
            if isinstance(hex_val, str):
                n = int(hex_val, 16) if hex_val.startswith("0x") else int(hex_val)
            else:
                n = int(hex_val)
            bitstring = bin(n)[2:].zfill(num_qubits)
            result[bitstring] = count
        return result

    def close(self):
        """Clean up ZMQ resources."""
        if self._socket:
            self._socket.close()
            self._socket = None
        if self._context:
            self._context.term()
            self._context = None
