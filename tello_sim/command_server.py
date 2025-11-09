import os
import socket
import errno
from ursina import * # type: ignore
from time import time
import cv2
from ursina_adapter import UrsinaAdapter
        
class CommandServer:
    """
    Serves a TCP connections to receive and parse commands and forward controls to the simulator.
    """
   
    def __init__(self, ursina_adapter: UrsinaAdapter):
        self._ursina_adapter = ursina_adapter
        self.latest_frame = None
        self.stream_active = False
        self.last_altitude = 0
        self._recording_folder = "output/recordings"
        self.server_socket = None
        
        if not os.path.exists(self._recording_folder):
            os.makedirs(self._recording_folder)

    def check_port_available(self, port: int = 9999) -> bool:
        """
        Check if the specified port is available.
        Returns True if available, False if in use.
        """
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_socket.bind(('localhost', port))
            test_socket.close()
            return True
        except OSError:
            return False

    def cleanup(self):
        """Clean up resources and close the server socket."""
        if self.server_socket:
            try:
                self.server_socket.close()
                print("[Command Listener] Server socket closed.")
            except Exception as e:
                print(f"[Command Listener] Error closing socket: {e}")

    def streamon(self):
        """Start capturing screenshots and enable FPV video preview."""
        if not self.stream_active:
            self.stream_active = True
            self._ursina_adapter.stream_active = True
            self.frame_count = 0
            self.saved_frames = []
            self.last_screenshot_time = time() + 3  # First capture after 3 sec

            if self._ursina_adapter:
                self._ursina_adapter.toggle_camera_view()

            print("Tello Simulator: Video streaming started, FPV mode activated.")
            
  
    def streamoff(self):
        """Stop capturing screenshots"""
        if self.stream_active:
            self.stream_active = False
            self._ursina_adapter.stream_active = False
            cv2.destroyAllWindows()
            print(f"[FPV] Video streaming stopped. Frames captured: {len(self.saved_frames)}")

            if self._ursina_adapter:
                self._ursina_adapter.toggle_camera_view()

    def curve_xyz_speed(self, x1: float, y1: float, z1: float, x2: float, y2: float, z2: float, speed: float) -> None:
        self._ursina_adapter.curve_xyz_speed(x1, y1, z1, x2, y2, z2, speed)

    def send_rc_control(self, left_right_velocity_ms: float, forward_backward_velocity_ms: float, up_down_velocity_ms: float, yaw_velocity_ms: float) -> None:
        self._ursina_adapter.send_rc_control(left_right_velocity_ms, forward_backward_velocity_ms, up_down_velocity_ms, yaw_velocity_ms)
        
    def end(self):
        self._ursina_adapter.end()
        
    def listen(self) -> None:
        """
        Listens for commands to send to the Simulator
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind(('localhost', 9999))  # Port number for communication
            self.server_socket.listen(5)
            print("[Command Listener] Listening on port 9999...")
        except OSError as e:
            if e.errno == errno.EADDRINUSE:  # Address already in use
                print("\n" + "="*70)
                print("ERROR: Port 9999 is already in use!")
                print("="*70)
                print("\nAnother instance of the simulator may be running.")
                print("\nTo fix this, run one of these commands in your terminal:")
                print("  macOS/Linux: lsof -ti:9999 | xargs kill -9")
                print("  Windows:     netstat -ano | findstr :9999")
                print("               taskkill /PID <PID> /F")
                print("\nOr simply restart your computer.")
                print("="*70 + "\n")
                raise
            else:
                raise

        try:
            while True:
                conn, _ = self.server_socket.accept()
                data = conn.recv(1024).decode()
                if data:
                    print(f"[Command Listener] Received command: {data}")
                
                if data == "connect":
                    self._ursina_adapter.connect()
                elif data == "takeoff":
                    self._ursina_adapter.takeoff()
                elif data == "land":
                    self._ursina_adapter.land()
                elif data == "flip_forward":
                    self._ursina_adapter.animate_flip(direction="forward")
                elif data == "flip_back":
                     self._ursina_adapter.animate_flip(direction="back")
                elif data == "flip_left":
                     self._ursina_adapter.animate_flip(direction="left")
                elif data == "flip_right":
                    self._ursina_adapter.animate_flip(direction="right")
                elif data == "streamon":
                    self.streamon()
                elif data == "streamoff":
                    self.streamoff()
                elif data == "emergency":
                    self._ursina_adapter.emergency()
                elif data.startswith("forward"):
                    parts = data.split()
                    distance = float(parts[1]) if len(parts) > 1 else 10
                    self._ursina_adapter.move("forward", distance)

                elif data.startswith("backward"):
                    parts = data.split()
                    distance = float(parts[1]) if len(parts) > 1 else 10
                    self._ursina_adapter.move("backward", distance)

                elif data.startswith("left"):
                    parts = data.split()
                    distance = float(parts[1]) if len(parts) > 1 else 10
                    self._ursina_adapter.move("left", distance)

                elif data.startswith("right"):
                    parts = data.split()
                    distance = float(parts[1]) if len(parts) > 1 else 10
                    self._ursina_adapter.move("right", distance)

                elif data.startswith("up"):
                    parts = data.split()
                    distance = float(parts[1]) if len(parts) > 1 else 10
                    self._ursina_adapter.change_altitude_smooth("up", distance)

                elif data.startswith("down"):
                    parts = data.split()
                    distance = float(parts[1]) if len(parts) > 1 else 10
                    self._ursina_adapter.change_altitude_smooth("down", distance)

                
                elif data.startswith("rotate_cw"):
                    parts = data.split()
                    angle = float(parts[1]) if len(parts) > 1 else 90
                    self._ursina_adapter.rotate_smooth(angle)

                elif data.startswith("rotate_ccw"):
                    parts = data.split()
                    angle = float(parts[1]) if len(parts) > 1 else 90
                    self._ursina_adapter.rotate_smooth(-angle)

                elif data.startswith("go"):
                    try:
                        _, x, y, z, speed = data.split()
                        self._ursina_adapter.go_xyz_speed(float(x), float(y), float(z), float(speed))
                    except ValueError:
                        print("[Error] Invalid go command format")

                elif data.startswith("send_rc_control"):
                    try:
                        _, lr, fb, ud, yaw = data.split()
                        self.send_rc_control(float(lr), float(fb), float(ud), float(yaw))
                        conn.send(b"RC control applied")
                    except ValueError:
                        conn.send(b"Invalid RC control parameters")

                elif data == "get_is_moving":
                    conn.send(str(self._ursina_adapter.is_moving).encode())
                
                elif data.startswith("curve"):
                    try:
                        _, x1, y1, z1, x2, y2, z2, speed = data.split()
                        self.curve_xyz_speed(float(x1), float(y1), float(z1),
                                                float(x2), float(y2), float(z2),
                                                float(speed))
                    except ValueError:
                        print("[Error] Invalid curve command format")
                
                elif data == "get_battery":
                    conn.send(str(self._ursina_adapter.get_battery()).encode())
                elif data == "get_distance_tof":
                    conn.send(str(100).encode())  
                elif data == "get_height":
                    height = (self._ursina_adapter.drone.y / 10) - 0.3
                    conn.send(f"{height:.1f}".encode())
                elif data == "get_flight_time":
                    conn.send(str(self._ursina_adapter.get_flight_time()).encode())
                elif data == "get_speed_x":
                    conn.send(str(self._ursina_adapter.get_speed_x()).encode())
                elif data == "get_speed_y":
                    conn.send(str(self._ursina_adapter.get_speed_y()).encode())
                elif data == "get_speed_z":
                    conn.send(str(self._ursina_adapter.get_speed_z()).encode())
                elif data == "get_acceleration_x":
                    conn.send(str(self._ursina_adapter.calculated_acceleration.x * 100).encode())  
                elif data == "get_acceleration_y":
                    conn.send(str(self._ursina_adapter.calculated_acceleration.y * 100).encode())
                elif data == "get_acceleration_z":
                    conn.send(str(self._ursina_adapter.calculated_acceleration.z * 100).encode())
                elif data == "get_pitch":
                    conn.send(str(self._ursina_adapter.get_pitch()).encode())
                elif data == "get_roll":
                    conn.send(str(self._ursina_adapter.get_roll()).encode())
                elif data == "get_yaw":
                    raw_yaw = self._ursina_adapter.drone.rotation_y
                    yaw = ((raw_yaw + 180) % 360) - 180
                    conn.send(str(yaw).encode())
                elif data == "query_attitude":
                    raw_yaw = self._ursina_adapter.drone.rotation_y
                    yaw = ((raw_yaw + 180) % 360) - 180
                    attitude = {
                        "pitch": self._ursina_adapter.get_pitch(),
                        "roll": self._ursina_adapter.get_roll(),
                        "yaw": yaw
                    }
                    conn.send(str(attitude).encode())
                elif data == "get_current_state":
                    state = "flying" if self._ursina_adapter.is_flying else "landed"
                    conn.send(state.encode())

                elif data == "get_latest_frame":
                    # Send frame data directly over TCP instead of using filesystem
                    if self._ursina_adapter.latest_frame is not None:
                        # Encode frame as PNG in memory
                        success, buffer = cv2.imencode('.png', self._ursina_adapter.latest_frame)
                        if success:
                            # Send frame size first (4 bytes)
                            frame_data = buffer.tobytes()
                            frame_size = len(frame_data)
                            conn.send(frame_size.to_bytes(4, byteorder='big'))
                            # Then send the actual frame data
                            conn.send(frame_data)
                            print(f"[Frame Transfer] Sent {frame_size} bytes over TCP")
                        else:
                            # Send 0 size to indicate no frame
                            conn.send((0).to_bytes(4, byteorder='big'))
                    else:
                        # Send 0 size to indicate no frame available
                        conn.send((0).to_bytes(4, byteorder='big'))
                        
                elif data == "capture_frame":
                    self._ursina_adapter.capture_frame()
                elif data.startswith("set_speed"):
                    try:
                        _, speed = data.split()
                        self._ursina_adapter.set_speed(int(speed))
                    except ValueError:
                        print("[Error] Invalid set_speed command format")

                elif data == "end":
                    self.end()

                conn.close()
        except KeyboardInterrupt:
            print("\n[Command Listener] Shutting down...")
            self.cleanup()
        except Exception as e:
            print(f"[Command Listener] Error: {e}")
            self.cleanup()
            raise
