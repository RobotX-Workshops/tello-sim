import os
import subprocess
import platform
import sys
import time
import socket


class TelloConnector:
    def __init__(self, host='localhost', port=9999, auto_start_simulation=True):
        self.host = host
        self.port = port

        if auto_start_simulation and not self._check_simulation_running():
            self._start_simulation()
            print("[Wrapper] Starting Tello Simulation...")
            self._wait_for_simulation()

    def _start_simulation(self):
        if platform.system() == "Windows":
            subprocess.Popen(['start', 'cmd', '/k', 'python ./tello_drone_checking.py'], shell=True)
        elif platform.system() == "Linux":
            subprocess.Popen(['gnome-terminal', '--', 'python', './tello_drone_checking.py'])
        elif platform.system() == "Darwin":
            python_path = os.path.join(os.path.dirname(sys.executable), 'python3')
            subprocess.Popen([python_path, './tello_drone_checking.py'], cwd=os.getcwd(), 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                            start_new_session=True)
        else:
            raise OSError("Unsupported OS for launching terminal simulation.")

    def _check_simulation_running(self):
        try:
            with socket.create_connection((self.host, self.port), timeout=1):
                return True
        except (ConnectionRefusedError, socket.timeout, OSError):
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

    def _send_command(self, command):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.send(command.encode())
        except ConnectionRefusedError:
            print(f"[Error] Unable to connect to the simulation at {self.host}:{self.port}")

    def connect(self):
        self._send_command('connect')

    def takeoff(self):
        self._send_command('takeoff')

    def land(self):
        self._send_command('land')

    def flip_forward(self):
        self._send_command('flip_forward')

    def streamon(self):
        self._send_command('streamon')

    def streamoff(self):
        self._send_command('streamoff')

    def emergency(self):
        self._send_command('emergency')

    def move_forward(self):
        self._send_command('forward')

    def move_back(self):
        self._send_command('backward')

    def move_left(self):
        self._send_command('left')

    def move_right(self):
        self._send_command('right')

    def move_up(self):
        self._send_command('up')

    def move_down(self):
        self._send_command('down')

    def get_info(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.send(b'get_info')
                return s.recv(4096).decode()
        except ConnectionRefusedError:
            print(f"[Error] Unable to retrieve info from {self.host}:{self.port}")
            return "{}"
