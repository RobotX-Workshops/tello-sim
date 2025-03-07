import os
import socket
import threading
from time import time, sleep
import cv2

from tello_drone_sim import UrsinaAdapter

        
class CommandServer:
    """
    Serves a TCP connections to receive commands and control the Tello drone simulator.
    """
   
    def __init__(self, ursina_adapter: UrsinaAdapter):
        self.battery_level = 100
        self.ursina_adapter = ursina_adapter
        self.altitude = 0
        self.speed = 0
        self.rotation_angle = 0
        self.last_keys = {}
        self.start_time = time()
        self.stream_active = False
        self.is_connected = False
        self.recording_folder = "tello_recording"
        self.frame_count = 0
        self.saved_frames = []
        self.screenshot_interval = 3  
        self.latest_frame = None
        self.last_screenshot_time = None  
        self.last_altitude = self.altitude  
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
            print("Tello Simulator: Cannot take off. Connect first using 'connect()'.")
            
            return
        
        if not self.is_flying:
            print("Tello Simulator: Taking off...")
            
            self.is_flying = True
            if self.ursina_adapter:
                self.ursina_adapter.is_flying = True
                target_altitude = self.ursina_adapter.drone.y + 2  # Target altitude
                self.ursina_adapter.drone.animate('y', target_altitude, duration=1, curve=curve.in_out_quad)

                
            print("Tello Simulator: Takeoff successful! You can now control the drone.")
        else:
            print("Tello Simulator: Already in air.")

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

    def get_latest_frame(self):
        """Return the latest frame directly"""
        if self.latest_frame is not None:
            return cv2.cvtColor(self.latest_frame, cv2.COLOR_BGR2RGB)
        print("[Get Frame] No latest frame available.")
        return None
    
    def capture_frame(self):
        """Capture and save the latest FPV frame from update()"""
        if not self.stream_active:
            print("[Capture] Stream not active. Cannot capture frame.")
            return  

        if self.latest_frame is None:
            print("[Capture] No latest frame available.")
            return

        frame_path = os.path.join(self.recording_folder, f"frame_{self.frame_count}.png")
        cv2.imwrite(frame_path, self.latest_frame)
        self.saved_frames.append(frame_path)
        self.frame_count += 1
        print(f"[Capture] Screenshot {self.frame_count} saved: {frame_path}")

    
    def get_frame_read(self):
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
        if self.is_flying:
            print("Tello Simulator: Drone landing...")

            if self.ursina_adapter:
                # Get current altitude
                current_altitude = self.ursina_adapter.drone.y

                
                self.ursina_adapter.drone.animate('y', 2.6, duration=current_altitude * 0.5, curve=curve.in_out_quad)

            self.is_flying = False
            return "Landing initiated"
        
        return "Already on ground"

    def emergency(self):
        """Initiate an emergency landing by immediately stopping and descending to altitude = 3."""
        if self.is_flying:
            print(" Emergency! Stopping all motors and descending immediately!")

            if self.ursina_adapter:
                # Stop movement 
                self.ursina_adapter.velocity = Vec3(0, 0, 0)
                self.ursina_adapter.acceleration = Vec3(0, 0, 0)

                # descent to altitude = 3
                self.ursina_adapter.drone.animate('y', 2.6, duration=1.5, curve=curve.linear)

            self.is_flying = False
            return "Emergency landing initiated"
        
        return "Drone is already on the ground"
    
    def set_speed(self, x: int):
        """Set drone speed by adjusting acceleration force.
        
        Arguments:
            x (int): Speed in cm/s (10-100)
        """
        if not (10 <= x <= 100):
            print(" Invalid speed! Speed must be between 10 and 100 cm/s.")
            return

        if self.ursina_adapter:
            # Normalize speed
            self.ursina_adapter.accel_force = (x / 100) * 1.5  

            print(f" Speed set to {x} cm/s. Acceleration force: {self.ursina_adapter.accel_force}")
        else:
            print(" Drone simulator not connected.")
    
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
            

    
    def flip_forward(self):
        
        if self.ursina_adapter and self.is_flying:
            print("Tello Simulator: Performing Forward Flip!")
            self.ursina_adapter.animate_flip(direction="forward")

    def flip_back(self):
        
        if self.ursina_adapter and self.is_flying:
            print("Tello Simulator: Performing Backward Flip!")
            self.ursina_adapter.animate_flip(direction="back")

    def flip_left(self):
        
        if self.ursina_adapter and self.is_flying:
            print("Tello Simulator: Performing Left Flip!")
            self.ursina_adapter.animate_flip(direction="left")

    def flip_right(self):
        
        if self.ursina_adapter and self.is_flying:
            print("Tello Simulator: Performing Right Flip!")
            self.ursina_adapter.animate_flip(direction="right")

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
    

    def run(self):
        """Starts the server and listens for commands while running the Simulator."""
        self.ursina_adapter.run()
        threading.Thread(target=self.listen, daemon=True).start()
        
        
        
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
                    self.flip_forward()
                elif data == "flip_back":
                    self.flip_back()
                elif data == "flip_left":
                    self.flip_left()
                elif data == "flip_right":
                    self.flip_right()
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
                    if self.saved_frames:
                        conn.send(self.saved_frames[-1].encode())
                    else:
                        conn.send(b"N/A")
                
                elif data == "capture_frame":
                    self.capture_frame()

                elif data.startswith("set_speed"):
                    try:
                        _, speed = data.split()
                        self.set_speed(int(speed))
                    except ValueError:
                        print("[Error] Invalid set_speed command format")

                elif data == "end":
                    self.end()

            conn.close()
