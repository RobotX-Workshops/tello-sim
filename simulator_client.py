"""Simulator-only client.

Everything here is a capability the simulator has and a real DJI Tello does
not: ground-truth position, a push telemetry stream, motion-completion
polling. Keeping it off TelloSimClient means a call site reads as `sim.` the
moment it stops being portable to real hardware.

Construct it alongside the drone client:

    tello = TelloSimClient()     # what a real Tello can do
    sim = SimulatorClient()      # what only a simulator can do
"""
import json
import logging
# Only for the UDP telemetry stream. The TCP command channel lives entirely
# in SimConnection; this socket is a different protocol on a different port.
import socket
import threading
import time

from sim_connection import SimConnection


class SimulatorClient:
    def __init__(self, host='localhost', port=9999, telemetry_port=9998):
        self._conn = SimConnection(host, port)
        self.telemetry_port = telemetry_port
        self._telemetry_thread = None
        self._telemetry_stop = None
        self._telemetry_socket = None
        self._telemetry_addr = None

    @property
    def host(self):
        return self._conn.host

    @property
    def port(self):
        return self._conn.port

    def is_simulator_running(self) -> bool:
        """True if the simulator's command server is accepting connections."""
        return self._conn.is_reachable()

    def wait_until_motion_complete(self):
        """Block until the simulated drone has finished moving.

        A real Tello blocks inside the move command itself, so there is no
        djitellopy equivalent to poll.
        """
        while self._conn.request("get_is_moving") == "True":
            time.sleep(0.1)

    def capture_frame(self):
        """Tell the simulator to capture the current FPV frame.

        The simulator holds the frame in memory and bumps its capture counter
        (reported when the stream is stopped); nothing is written to disk.
        """
        self._conn.send('capture_frame')

    def get_position(self):
        """Poll the drone's position: {'x': m, 'y': m, 'z': m, 'yaw': deg}.

        x/z are metres in the simulator's world frame, y is height above the
        ground (same value as get_height).
        """
        data = self._conn.request('get_position')
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None

    def get_state(self):
        """Poll the full telemetry snapshot (position, attitude, speeds,
        battery, flying flag) as a dict, or None if unavailable."""
        data = self._conn.request('get_state')
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None

    # --- scene editing -------------------------------------------------------
    # Used by tools/scene_editor.py. Edits apply live in the simulator window;
    # save_scene() persists them to gates.json / people.json.

    def get_scene(self):
        """Poll the editable scene: {'gates': [...], 'people': [...], 'ranges': {...}}.

        'ranges' gives the min/max each field is clamped to, so a caller can
        build its controls without hardcoding the simulator's bounds. Returns
        None if unavailable.
        """
        data = self._conn.request('get_scene')
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_gate(self, index, field, value):
        """Move/resize one gate. `field` is x, z, diameter_cm, clearance_cm or yaw.

        Returns "ok", or "error: ..." if the index or field is rejected. The
        value is clamped to the simulator's range for that field.
        """
        return self._conn.request(f'set_gate {index} {field} {value}')

    def set_person(self, name, field, value):
        """Move one pedestrian. `field` is x, y, z or yaw; `name` is a key from
        get_scene()['people']. Returns "ok" or "error: ..."."""
        return self._conn.request(f'set_person {name} {field} {value}')

    def save_scene(self):
        """Persist the current gate and people layout. Returns "ok" or "error: ..."."""
        return self._conn.request('save_scene')

    def subscribe_state(self, callback):
        """Subscribe to the simulator's UDP telemetry stream (~10 Hz).

        `callback` is invoked with a state dict for every update, from a
        background thread, until unsubscribe_state() is called. The
        subscription is kept alive automatically.
        """
        if self._telemetry_thread:
            print("[Wrapper] Already subscribed to telemetry.")
            return
        # The stream is UDP, so a missing simulator is silent — the callback
        # would simply never fire. Say so up front instead.
        if not self._conn.is_reachable():
            print(f"[Warning] Simulator not reachable at {self.host}:{self.port}; "
                  "telemetry updates will not arrive until it is started.")
        # Every subscription owns its own socket and stop event, captured as
        # locals by the reader. Sharing them on self let a resubscribe (e.g.
        # from inside a callback that first unsubscribed) hand a still-running
        # old reader the new subscription's socket/flag — so the old reader
        # could keep receiving on, or close, the new socket.
        stop_event = threading.Event()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        addr = (self.host, self.telemetry_port)

        def _reader() -> None:
            last_keepalive = 0.0
            try:
                while not stop_event.is_set():
                    now = time.time()
                    # Refresh the subscription well inside the server's 10 s TTL.
                    if now - last_keepalive > 3.0:
                        try:
                            sock.sendto(b'subscribe', addr)
                            last_keepalive = now
                        except OSError:
                            pass
                    try:
                        data, _ = sock.recvfrom(4096)
                    except TimeoutError:
                        continue
                    except OSError:
                        break
                    try:
                        callback(json.loads(data.decode()))
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        # A failing callback must not kill the stream.
                        logging.exception("[Wrapper] Telemetry callback raised")
            finally:
                # This reader owns `sock`, so it closes only its own socket.
                # Clear the shared handle only if it still points at us — a
                # resubscribe may already have installed a newer reader.
                sock.close()
                if self._telemetry_thread is thread:
                    self._telemetry_thread = None

        thread = threading.Thread(target=_reader, daemon=True)
        # Record this subscription's handles so unsubscribe_state can signal it.
        self._telemetry_stop = stop_event
        self._telemetry_socket = sock
        self._telemetry_addr = addr
        self._telemetry_thread = thread
        thread.start()

    def unsubscribe_state(self):
        """Stop the UDP telemetry subscription started by subscribe_state()."""
        thread = self._telemetry_thread
        if not thread:
            return
        # Signal this subscription's reader via its own stop event, and nudge
        # the server on this subscription's own socket/addr.
        self._telemetry_stop.set()
        try:
            self._telemetry_socket.sendto(b'unsubscribe', self._telemetry_addr)
        except OSError:
            pass
        # Safe to call from within the callback itself: the reader thread
        # can't join itself, so let it wind down on its stop event instead
        # (it closes its own socket as it exits).
        if threading.current_thread() is not thread:
            thread.join(timeout=2.0)
        # Clear the handle only if a resubscribe hasn't already replaced it.
        if self._telemetry_thread is thread:
            self._telemetry_thread = None
