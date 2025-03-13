from dataclasses import dataclass
import logging
import subprocess
import platform
import sys
import time
import socket
import cv2
import os
import numpy as np

@dataclass
class BackgroundFrameRead():
    frame: cv2.typing.MatLike

class TelloSimClient:
    def __init__(self, host='localhost', port=9999, auto_start_simulation=True):
        self.host = host
        self.port = port
        self.latest_frame = None
        if auto_start_simulation and not self._check_simulation_running():
            self._start_simulation()
            print("[Wrapper] Starting Tello Simulation...")
            self._wait_for_simulation()

    def _start_simulation(self):
        sim_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'tello_drone_sim.py'))
        if platform.system() == "Windows":
            command = f'start cmd /k python "{sim_path}"'
            print("[DEBUG] Launching simulation command:", command) 
            subprocess.Popen(command, shell=True)
        elif platform.system() == "Linux":
            subprocess.Popen(['gnome-terminal', '--', 'python3', 'tello_drone_sim.py'])
        elif platform.system() == "Darwin":
            subprocess.Popen(['ls'])
            subprocess.Popen(['pwd'])
            python_path = os.path.join(os.path.dirname(sys.executable), 'python3')
            print("Running python3 from path:", python_path)
            subprocess.Popen([python_path, './tello_drone_sim.py'], cwd=os.getcwd(), 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                            start_new_session=True)
        else:
            raise OSError("Unsupported OS for launching terminal simulation.")

    def _check_simulation_running(self):
        try:
            with socket.create_connection((self.host, self.port), timeout=1):
                return True
        except (ConnectionRefusedError, socket.timeout, OSError) as ex:
            logging.error("[Wrapper] Simulation is not running.", ex)
            return False

    def _wait_for_simulation(self, timeout=30):
        print("[Wrapper] Waiting for simulation to become ready...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._check_simulation_running():
                print("[Wrapper] Simulation is now ready!")
                return
            time.sleep(1)
        raise TimeoutError("[Error] Simulation did not become ready in time.")

    def _send_command(self, command: str):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.send(command.encode())
        except ConnectionRefusedError:
            print(f"[Error] Unable to connect to the simulation at {self.host}:{self.port}")
    
    def get_frame_read(self) -> BackgroundFrameRead:
        """Retrieve the latest frame path from the simulation and load the image."""
        frame_path = self._request_data('get_latest_frame')
        if frame_path != "N/A" and os.path.exists(frame_path):
            image = cv2.imread(frame_path)
            if image is not None:
                return BackgroundFrameRead(frame=cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        return BackgroundFrameRead(frame=np.zeros([300, 400, 3], dtype=np.uint8))
    
    def _request_data(self, command):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.send(command.encode())
                return s.recv(4096).decode()
        except ConnectionRefusedError:
            print(f"[Error] Unable to retrieve '{command}' from {self.host}:{self.port}")
            return "N/A"

    def get_battery(self):
        return self._request_data('get_battery')

    def get_distance_tof(self):
        return self._request_data('get_distance_tof')

    def get_height(self):
        return self._request_data('get_height')

    def get_flight_time(self):
        return self._request_data('get_flight_time')

    def get_speed_x(self):
        return self._request_data('get_speed_x')

    def get_speed_y(self):
        return self._request_data('get_speed_y')

    def get_speed_z(self):
        return self._request_data('get_speed_z')

    def get_acceleration_x(self):
        return self._request_data('get_acceleration_x')

    def get_acceleration_y(self):
        return self._request_data('get_acceleration_y')

    def get_acceleration_z(self):
        return self._request_data('get_acceleration_z')

    def get_pitch(self):
        return self._request_data('get_pitch')

    def get_roll(self):
        return self._request_data('get_roll')

    def get_yaw(self):
        return self._request_data('get_yaw')

    def query_attitude(self):
        return self._request_data('query_attitude')

    def get_current_state(self):
        return self._request_data('get_current_state')
  
    def connect(self):
        self._send_command('connect')

    def takeoff(self):
        self._send_command('takeoff')

    def land(self):
        self._send_command('land')

    def rotate_clockwise(self, degrees):
        self._send_command(f'rotate_cw {degrees}')

    def rotate_counter_clockwise(self, degrees):
        self._send_command(f'rotate_ccw {degrees}')

    def streamon(self):
        self._send_command('streamon')

    def streamoff(self):
        self._send_command('streamoff')

    def capture_frame(self):
        self._send_command('capture_frame')

    def emergency(self):
        self._send_command('emergency')

    def move_forward(self, distance):
        self._send_command(f'forward {distance}')

    def move_back(self, distance):
        self._send_command(f'backward {distance}')

    def move_left(self, distance):
        self._send_command(f'left {distance}')

    def move_right(self, distance):
        self._send_command(f'right {distance}')

    def move_up(self, distance):
        self._send_command(f'up {distance}')

    def move_down(self, distance):
        self._send_command(f'down {distance}')

    def flip_left(self):
        self._send_command('flip_left')

    def flip_right(self):
        self._send_command('flip_right')

    def flip_forward(self):
        self._send_command('flip_forward')

    def flip_back(self):
        self._send_command('flip_back')

    def go_xyz_speed(self, x, y, z, speed):
        self._send_command(f"go {x} {y} {z} {speed}")

    def curve_xyz_speed(self, x1, y1, z1, x2, y2, z2, speed):
        self._send_command(f"curve {x1} {y1} {z1} {x2} {y2} {z2} {speed}")

    def set_speed(self, speed):
        self._send_command(f"set_speed {speed}")

    def send_rc_control(self, left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity):
        self._send_command(f"send_rc_control {left_right_velocity} {forward_backward_velocity} {up_down_velocity} {yaw_velocity}")


    def end(self):
        self._send_command('end')
    
    def get_info(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.send(b'get_info')
                return s.recv(4096).decode()
        except ConnectionRefusedError:
            print(f"[Error] Unable to retrieve info from {self.host}:{self.port}")
            return "{}"
