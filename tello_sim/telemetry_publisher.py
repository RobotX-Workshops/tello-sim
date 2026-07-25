import json
import logging
import socket
import threading
from time import sleep, time

logger = logging.getLogger(__name__)

TELEMETRY_PORT = 9998
PUBLISH_HZ = 10
# A subscriber that hasn't re-sent "subscribe" within this window is dropped,
# so crashed clients don't accumulate forever.
SUBSCRIBER_TTL_S = 10.0


def build_state(adapter) -> dict:
    """Snapshot the drone state as a plain dict.

    Position is in metres in the simulator's world frame (1 world unit =
    0.1 m, the same scale get_height/get_speed_* already use); y is height
    above the ground, matching get_height. Angles are degrees.
    """
    raw_yaw = adapter.drone.rotation_y
    return {
        "x": round(adapter.drone.x * 0.1, 3),
        "y": round((adapter.drone.y * 0.1) - 0.3, 3),
        "z": round(adapter.drone.z * 0.1, 3),
        "yaw": round(((raw_yaw + 180) % 360) - 180, 1),
        "pitch": adapter.get_pitch(),
        "roll": adapter.get_roll(),
        "speed_x": adapter.get_speed_x(),
        "speed_y": adapter.get_speed_y(),
        "speed_z": adapter.get_speed_z(),
        "battery": adapter.get_battery(),
        "flying": adapter.is_flying,
        "time": round(time(), 3),
    }


class TelemetryPublisher:
    """UDP push stream of drone state.

    Clients send the datagram b"subscribe" to TELEMETRY_PORT and then receive
    one JSON state datagram every 1/PUBLISH_HZ seconds until they send
    b"unsubscribe" or stop refreshing their subscription for SUBSCRIBER_TTL_S.
    """

    def __init__(self, ursina_adapter, port: int = TELEMETRY_PORT):
        self._ursina_adapter = ursina_adapter
        self._port = port
        self._subscribers: dict[tuple, float] = {}  # addr -> last-seen time
        self._lock = threading.Lock()
        self._running = False
        self._socket = None

    def start(self) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("localhost", self._port))
        self._running = True

        listen_thread = threading.Thread(target=self._listen, daemon=True)
        listen_thread.start()
        publish_thread = threading.Thread(target=self._publish_loop, daemon=True)
        publish_thread.start()
        print(f"[Telemetry] Publishing state on UDP port {self._port} "
              f"(send 'subscribe' to receive)")

    def stop(self) -> None:
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass

    def _listen(self) -> None:
        """Register/unregister subscribers from incoming datagrams."""
        while self._running:
            try:
                data, addr = self._socket.recvfrom(64)
            except OSError:
                break  # socket closed during shutdown
            message = data.decode(errors="replace").strip().lower()
            with self._lock:
                if message == "subscribe":
                    if addr not in self._subscribers:
                        logger.info("[Telemetry] Subscriber added: %s", addr)
                    self._subscribers[addr] = time()
                elif message == "unsubscribe":
                    if self._subscribers.pop(addr, None) is not None:
                        logger.info("[Telemetry] Subscriber removed: %s", addr)

    def _publish_loop(self) -> None:
        interval = 1.0 / PUBLISH_HZ
        while self._running:
            sleep(interval)
            with self._lock:
                now = time()
                expired = [a for a, seen in self._subscribers.items()
                           if now - seen > SUBSCRIBER_TTL_S]
                for addr in expired:
                    del self._subscribers[addr]
                    logger.info("[Telemetry] Subscriber expired: %s", addr)
                targets = list(self._subscribers)
            if not targets:
                continue
            try:
                payload = json.dumps(build_state(self._ursina_adapter)).encode()
            except Exception:
                logger.exception("[Telemetry] Failed to build state")
                continue
            for addr in targets:
                try:
                    self._socket.sendto(payload, addr)
                except OSError:
                    with self._lock:
                        self._subscribers.pop(addr, None)
