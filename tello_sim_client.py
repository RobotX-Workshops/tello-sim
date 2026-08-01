"""Tello-compatible client for the simulator.

Every method here mirrors the real DJI Tello / djitellopy surface, so a
script written against this client also runs against real hardware.

Capabilities a real drone does not have — ground-truth position, the
telemetry stream, motion-completion polling — deliberately live on
SimulatorClient in simulator_client.py instead.
"""
from dataclasses import dataclass

import cv2
import numpy as np

from sim_connection import SimConnection


@dataclass
class BackgroundFrameRead():
    frame: cv2.typing.MatLike

class TelloSimClient:
    def __init__(self, host='localhost', port=9999):
        self._conn = SimConnection(host, port)

    @property
    def host(self):
        return self._conn.host

    @property
    def port(self):
        return self._conn.port

    def get_frame_read(self) -> BackgroundFrameRead:
        """Get the latest frame directly from the simulator over TCP."""
        blank = BackgroundFrameRead(frame=np.zeros([360, 640, 3], dtype=np.uint8))
        frame_data = self._conn.request_framed('get_latest_frame')
        if frame_data is None:
            return blank

        # Decode the frame from PNG bytes
        nparr = np.frombuffer(frame_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            print("[Error] Failed to decode frame data")
            return blank

        # imdecode yields BGR; convert to RGB so the simulator's frames match
        # the real Tello's djitellopy interface, which returns RGB. Consumers
        # using OpenCV (cv2.imshow / imwrite / cvtColor to HSV) convert
        # RGB->BGR themselves, exactly as they must for a real drone.
        return BackgroundFrameRead(frame=cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    def get_battery(self):
        return self._conn.request('get_battery')

    def get_distance_tof(self):
        return self._conn.request('get_distance_tof')

    def get_height(self):
        return self._conn.request('get_height')

    def get_flight_time(self):
        return self._conn.request('get_flight_time')

    def get_speed_x(self):
        return self._conn.request('get_speed_x')

    def get_speed_y(self):
        return self._conn.request('get_speed_y')

    def get_speed_z(self):
        return self._conn.request('get_speed_z')

    def get_acceleration_x(self):
        return self._conn.request('get_acceleration_x')

    def get_acceleration_y(self):
        return self._conn.request('get_acceleration_y')

    def get_acceleration_z(self):
        return self._conn.request('get_acceleration_z')

    def get_pitch(self):
        return self._conn.request('get_pitch')

    def get_roll(self):
        return self._conn.request('get_roll')

    def get_yaw(self):
        return self._conn.request('get_yaw')

    def query_attitude(self):
        return self._conn.request('query_attitude')

    def get_current_state(self):
        return self._conn.request('get_current_state')

    def connect(self):
        """Establish the link to the simulator, like a real Tello's connect().

        Raises ConnectionError if the simulator is not running. djitellopy's
        connect() raises when no state packet arrives, so failing here keeps
        the simulator and the real drone behaving the same way.
        """
        if not self._conn.is_reachable():
            print("\n" + "=" * 70)
            print(f"ERROR: Could not reach the Tello simulator at {self.host}:{self.port}")
            print("=" * 70)
            print("\nIs the simulator running? Start it in another terminal with:\n")
            print("  python tello_sim/run_sim.py")
            print("\n(from the repo root, with the venv activated)")
            print("=" * 70 + "\n")
            raise ConnectionError(
                f"Could not reach the Tello simulator at {self.host}:{self.port}. "
                "Start it with: python tello_sim/run_sim.py")
        self._conn.send('connect')

    def takeoff(self):
        self._conn.send('takeoff')

    def land(self):
        self._conn.send('land')

    def rotate_clockwise(self, degrees):
        self._conn.send(f'rotate_cw {degrees}')

    def rotate_counter_clockwise(self, degrees):
        self._conn.send(f'rotate_ccw {degrees}')

    def streamon(self):
        self._conn.send('streamon')

    def streamoff(self):
        self._conn.send('streamoff')

    def emergency(self):
        self._conn.send('emergency')

    def move_forward(self, distance):
        self._conn.send(f'forward {distance}')

    def move_back(self, distance):
        self._conn.send(f'backward {distance}')

    def move_left(self, distance):
        self._conn.send(f'left {distance}')

    def move_right(self, distance):
        self._conn.send(f'right {distance}')

    def move_up(self, distance):
        self._conn.send(f'up {distance}')

    def move_down(self, distance):
        self._conn.send(f'down {distance}')

    def flip_left(self):
        self._conn.send('flip_left')

    def flip_right(self):
        self._conn.send('flip_right')

    def flip_forward(self):
        self._conn.send('flip_forward')

    def flip_back(self):
        self._conn.send('flip_back')

    def go_xyz_speed(self, x, y, z, speed):
        self._conn.send(f"go {x} {y} {z} {speed}")

    def curve_xyz_speed(self, x1, y1, z1, x2, y2, z2, speed):
        self._conn.send(f"curve {x1} {y1} {z1} {x2} {y2} {z2} {speed}")

    def set_speed(self, speed):
        self._conn.send(f"set_speed {speed}")

    def send_rc_control(self, left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity):
        self._conn.send(f"send_rc_control {left_right_velocity} {forward_backward_velocity} {up_down_velocity} {yaw_velocity}")

    def end(self):
        self._conn.send('end')

    def initiate_throw_takeoff(self):
        self._conn.send('throw_takeoff')
