import os
import socket
import threading
from time import time, sleep
import cv2

from tello_drone_sim import UrsinaAdapter

        
class CommandServer:
    """
    Serves a TCP connections to receive commands and forward controls to the simulator.
    """
   
    def __init__(self, ursina_adapter: UrsinaAdapter):
        self.ursina_adapter = ursina_adapter

        self.last_time = self.start_time
        
        if not os.path.exists(self.recording_folder):
            os.makedirs(self.recording_folder)

    def connect(self):
        """Simulate connecting to the drone."""
        if not self.is_connected:
            print("Tello Simulator: Connecting...")
            sleep(1)  
            self.is_connected = True
            print("Tello Simulator: Connection successful! Press 'Shift' to take off.")

    def takeoff(self):
        """Simulate takeoff only if connected."""
        if not self.is_connected:
            raise Exception("Drone not connected. Cannot take off.")
        self.ursina_adapter.takeoff()

    def streamon(self):
        """Start capturing screenshots and enable FPV video preview."""
        if not self.stream_active:
            self.stream_active = True
            self.frame_count = 0
            self.saved_frames = []
            self.last_screenshot_time = time() + 3  # First capture after 3 sec

            if self.ursina_adapter:
                self.ursina_adapter.toggle_camera_view()

            print("Tello Simulator: Video streaming started, FPV mode activated.")
            
  
    def streamoff(self):
        """Stop capturing screenshots"""
        if self.stream_active:
            self.stream_active = False
            cv2.destroyAllWindows()
            print(f"[FPV] Video streaming stopped. Frames captured: {len(self.saved_frames)}")

            if self.ursina_adapter:
                self.ursina_adapter.toggle_camera_view()

    def get_latest_frame(self) -> :
        """Return the latest frame directly"""
        if self.latest_frame is not None:
            return cv2.cvtColor(self.latest_frame, cv2.COLOR_BGR2RGB)
        print("[Get Frame] No latest frame available.")
        return None


    
    def get_frame_read(self) -> None:
        """Open the folder containing saved frames"""
        os.startfile(self.recording_folder)  # Open folder in File Explorer
        print(f"Opened recording folder: {self.recording_folder}")
    
    def get_battery(self):
        elapsed_time = time() - self.start_time
        self.battery_level = max(100 - int((elapsed_time / 3600) * 100), 0)  # Reduce battery over 60 min
        return self.battery_level  
    
    def rotate(self, angle):
        self.rotation_angle += angle
        print(f"Tello Simulator: Rotating {angle} degrees")

    def land(self):
        """Initiate a smooth landing animation to altitude = 3"""
        self.ursina_adapter.land()

    def emergency(self):
        """Initiate an emergency landing by immediately stopping and descending to altitude = 3."""
        self.ursina_adapter.emergency()
        print("Tello Simulator: Emergency stop initiated!")
    
    def move(self, direction, distance=10):
        print(f"Tello Simulator: Moving {direction}")

    def get_pitch(self) -> int:
        
        if self.ursina_adapter:
            return int(self.ursina_adapter.drone.rotation_x) 
        return 0

    def get_roll(self) -> int:
        
        if self.ursina_adapter:
            return int(self.ursina_adapter.drone.rotation_z)  
        return 0

    def get_flight_time(self) -> int:
        """Return total flight time in seconds."""
        if self.is_flying:
            return int(time() - self.start_time)  
        return 0  # Not flying

    def get_speed_x(self) -> int:
        
        if self.ursina_adapter:
            return int(self.ursina_adapter.velocity.x * 3.6)  
        return 0

    def get_speed_y(self) -> int:
        
        if self.ursina_adapter:
            current_time = time()
            elapsed_time = current_time - self.last_time

            if elapsed_time > 0:  
                current_altitude = (self.ursina_adapter.drone.y * 0.1) - 0.3
                vertical_speed = (current_altitude - self.last_altitude) / elapsed_time  
                self.last_altitude = current_altitude
                self.last_time = current_time
                return int(vertical_speed * 3.6)  

        return 0

    def get_speed_z(self) -> int:
        
        if self.ursina_adapter:
            return int(self.ursina_adapter.velocity.z * 3.6)  
        return 0

    def get_acceleration_x(self) -> float:
        """Return the current acceleration in the X direction."""
        if self.ursina_adapter:
            return self.ursina_adapter.acceleration.x * 100  
        return 0.0

    def get_acceleration_y(self) -> float:
        """Return the current acceleration in the Y direction."""
        if self.ursina_adapter:
            return self.ursina_adapter.acceleration.y * 100  
        return 0.0

    def get_acceleration_z(self) -> float:
        """Return the current acceleration in the Z direction."""
        if self.ursina_adapter:
            return self.ursina_adapter.acceleration.z * 100  
        return 0.0
    
    def rotate_smooth(self, angle):
        
        if self.ursina_adapter:
            current_yaw = self.ursina_adapter.drone.rotation_y
            target_yaw = current_yaw + angle
            duration = abs(angle) / 90  
            self.ursina_adapter.drone.animate('rotation_y', target_yaw, duration=duration, curve=curve.linear)
            print(f"Tello Simulator: Smoothly rotating {angle} degrees over {duration:.2f} seconds.")

    def change_altitude_smooth(self, direction: str, distance: float):
        
        if self.ursina_adapter:
            delta = distance / 20  
            current_altitude = self.ursina_adapter.drone.y

            if direction == "up":
                target_altitude = current_altitude + delta
            elif direction == "down":
                target_altitude = max(3, current_altitude - delta)  
            else:
                print(f"Invalid altitude direction: {direction}")
                return

            duration = abs(delta) * 1  
            self.ursina_adapter.drone.animate('y', target_altitude, duration=duration, curve=curve.in_out_quad)
            self.altitude = target_altitude
            

    def go_xyz_speed(self, x, y, z, speed):
        if self.ursina_adapter and self.is_flying:
            print(f"Tello Simulator: GO command to X:{x}, Y:{y}, Z:{z} at speed {speed}")
            duration = max(1, speed / 10)
            target_position = self.ursina_adapter.drone.position + Vec3(x / 10, y / 10, z / 10)
            self.ursina_adapter.drone.animate_position(target_position, duration=duration, curve=curve.in_out_quad)
        else:
            print("Tello Simulator: Cannot execute GO command. Drone not flying.")

    def curve_xyz_speed(self, x1: float, y1: float, z1: float, x2: float, y2: float, z2: float, speed: float) -> None:
        self.ursina_adapter.curve_xyz_speed(x1, y1, z1, x2, y2, z2, speed)


    def send_rc_control(self, left_right_velocity_ms: float, forward_backward_velocity_ms: float, up_down_velocity_ms: float, yaw_velocity_ms: float) -> None:
        if not self.ursina_adapter:
            raise Exception("Drone simulator not connected.")
        self.ursina_adapter.send_rc_control(left_right_velocity_ms, forward_backward_velocity_ms, up_down_velocity_ms, yaw_velocity_ms)

    
    def end(self):
        
        print("Tello Simulator: Ending simulation...")
        if self.ursina_adapter:
            self.is_connected = False
            application.quit()
      
    def listen(self) -> None:
        """
        Listens for commands to send to the Simulator
        """
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('localhost', 9999))  # Port number for communication
        server.listen(5)
        print("[Command Listener] Listening on port 9999...")

        while True:
            conn, addr = server.accept()
            data = conn.recv(1024).decode()
            if data:
                print(f"[Command Listener] Received command: {data}")
                
                if data == "connect":
                    self.connect()
                elif data == "takeoff":
                    self.takeoff()
                elif data == "land":
                    self.land()
                elif data == "flip_forward":
                    self.ursina_adapter.animate_flip(direction="forward")
                elif data == "flip_back":
                     self.ursina_adapter.animate_flip(direction="back")
                elif data == "flip_left":
                     self.ursina_adapter.animate_flip(direction="left")
                elif data == "flip_right":
                    self.ursina_adapter.animate_flip(direction="right")
                elif data == "streamon":
                    self.streamon()
                elif data == "streamoff":
                    self.streamoff()
                elif data == "emergency":
                    self.emergency()
                elif data.startswith("forward"):
                    parts = data.split()
                    distance = float(parts[1]) if len(parts) > 1 else 10
                    self.ursina_adapter.move("forward", distance)

                elif data.startswith("backward"):
                    parts = data.split()
                    distance = float(parts[1]) if len(parts) > 1 else 10
                    self.ursina_adapter.move("backward", distance)

                elif data.startswith("left"):
                    parts = data.split()
                    distance = float(parts[1]) if len(parts) > 1 else 10
                    self.ursina_adapter.move("left", distance)

                elif data.startswith("right"):
                    parts = data.split()
                    distance = float(parts[1]) if len(parts) > 1 else 10
                    self.ursina_adapter.move("right", distance)

                elif data.startswith("up"):
                    parts = data.split()
                    distance = float(parts[1]) if len(parts) > 1 else 10
                    self.change_altitude_smooth("up", distance)

                elif data.startswith("down"):
                    parts = data.split()
                    distance = float(parts[1]) if len(parts) > 1 else 10
                    self.change_altitude_smooth("down", distance)

                
                elif data.startswith("rotate_cw"):
                    parts = data.split()
                    angle = float(parts[1]) if len(parts) > 1 else 90
                    self.rotate_smooth(angle)

                elif data.startswith("rotate_ccw"):
                    parts = data.split()
                    angle = float(parts[1]) if len(parts) > 1 else 90
                    self.rotate_smooth(-angle)

                elif data.startswith("go"):
                    try:
                        _, x, y, z, speed = data.split()
                        self.go_xyz_speed(float(x), float(y), float(z), float(speed))
                    except ValueError:
                        print("[Error] Invalid go command format")

                elif data.startswith("send_rc_control"):
                    try:
                        _, lr, fb, ud, yaw = data.split()
                        self.send_rc_control(float(lr), float(fb), float(ud), float(yaw))
                        conn.send(b"RC control applied")
                    except ValueError:
                        conn.send(b"Invalid RC control parameters")

                
                elif data.startswith("curve"):
                    try:
                        _, x1, y1, z1, x2, y2, z2, speed = data.split()
                        self.curve_xyz_speed(float(x1), float(y1), float(z1),
                                                float(x2), float(y2), float(z2),
                                                float(speed))
                    except ValueError:
                        print("[Error] Invalid curve command format")
                
                elif data == "get_battery":
                    conn.send(str(self.get_battery()).encode())
                elif data == "get_distance_tof":
                    conn.send(str(100).encode())  
                elif data == "get_height":
                    height = (self.ursina_adapter.drone.y / 10) - 0.3
                    conn.send(f"{height:.1f}".encode())
                elif data == "get_flight_time":
                    conn.send(str(self.get_flight_time()).encode())
                elif data == "get_speed_x":
                    conn.send(str(self.get_speed_x()).encode())
                elif data == "get_speed_y":
                    conn.send(str(self.get_speed_y()).encode())
                elif data == "get_speed_z":
                    conn.send(str(self.get_speed_z()).encode())
                elif data == "get_acceleration_x":
                    conn.send(str(self.ursina_adapter.calculated_acceleration.x * 100).encode())  
                elif data == "get_acceleration_y":
                    conn.send(str(self.ursina_adapter.calculated_acceleration.y * 100).encode())
                elif data == "get_acceleration_z":
                    conn.send(str(self.ursina_adapter.calculated_acceleration.z * 100).encode())
                elif data == "get_pitch":
                    conn.send(str(self.get_pitch()).encode())
                elif data == "get_roll":
                    conn.send(str(self.get_roll()).encode())
                elif data == "get_yaw":
                    raw_yaw = self.ursina_adapter.drone.rotation_y
                    yaw = ((raw_yaw + 180) % 360) - 180
                    conn.send(str(yaw).encode())
                elif data == "query_attitude":
                    raw_yaw = self.ursina_adapter.drone.rotation_y
                    yaw = ((raw_yaw + 180) % 360) - 180
                    attitude = {
                        "pitch": self.get_pitch(),
                        "roll": self.get_roll(),
                        "yaw": yaw
                    }
                    conn.send(str(attitude).encode())
                elif data == "get_current_state":
                    state = "flying" if self.is_flying else "landed"
                    conn.send(state.encode())

                elif data == "get_latest_frame":
                    return self.ursina_adapter.get_latest_frame()
                elif data == "capture_frame":
                    self.ursina_adapter.capture_frame()
                elif data.startswith("set_speed"):
                    try:
                        _, speed = data.split()
                        self.ursina_adapter.set_speed(int(speed))
                    except ValueError:
                        print("[Error] Invalid set_speed command format")

                elif data == "end":
                    self.end()

            conn.close()
