import os
from OpenGL.GL import glReadPixels, GL_RGBA, GL_UNSIGNED_BYTE
from PIL import Image
import numpy as np
from ursina import *
from time import time, sleep
import threading
import socket
import cv2
def lerp_color(start_color, end_color, factor):
    """Custom color interpolation function"""
    return Color(
        start_color.r + (end_color.r - start_color.r) * factor,
        start_color.g + (end_color.g - start_color.g) * factor,
        start_color.b + (end_color.b - start_color.b) * factor,
        1  # Alpha channel
    )

class TelloConnector:
   
    def __init__(self, drone_sim=None, max_frames=50):
        self.battery_level = 100
        self.drone_sim = drone_sim
        self.altitude = 0
        self.speed = 0
        self.rotation_angle = 0
        self.is_flying = False
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
            if self.drone_sim:
                self.drone_sim.is_flying = True
                target_altitude = self.drone_sim.drone.y + 2  # Target altitude
                self.drone_sim.drone.animate('y', target_altitude, duration=1, curve=curve.in_out_quad)

                
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

            if self.drone_sim:
                self.drone_sim.toggle_camera_view()

            print("Tello Simulator: Video streaming started, FPV mode activated.")
            
  
    def streamoff(self):
        """Stop capturing screenshots"""
        if self.stream_active:
            self.stream_active = False
            cv2.destroyAllWindows()
            print(f"[FPV] Video streaming stopped. Frames captured: {len(self.saved_frames)}")

            if self.drone_sim:
                self.drone_sim.toggle_camera_view()

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

            if self.drone_sim:
                # Get current altitude
                current_altitude = self.drone_sim.drone.y

                
                self.drone_sim.drone.animate('y', 2.6, duration=current_altitude * 0.5, curve=curve.in_out_quad)

            self.is_flying = False
            return "Landing initiated"
        
        return "Already on ground"

    def emergency(self):
        """Initiate an emergency landing by immediately stopping and descending to altitude = 3."""
        if self.is_flying:
            print(" Emergency! Stopping all motors and descending immediately!")

            if self.drone_sim:
                # Stop movement 
                self.drone_sim.velocity = Vec3(0, 0, 0)
                self.drone_sim.acceleration = Vec3(0, 0, 0)

                # descent to altitude = 3
                self.drone_sim.drone.animate('y', 2.6, duration=1.5, curve=curve.linear)

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

        if self.drone_sim:
            # Normalize speed
            self.drone_sim.accel_force = (x / 100) * 1.5  

            print(f" Speed set to {x} cm/s. Acceleration force: {self.drone_sim.accel_force}")
        else:
            print(" Drone simulator not connected.")
    
    def move(self, direction, distance=10):
        print(f"Tello Simulator: Moving {direction}")

    def get_pitch(self) -> int:
        
        if self.drone_sim:
            return int(self.drone_sim.drone.rotation_x) 
        return 0

    def get_roll(self) -> int:
        
        if self.drone_sim:
            return int(self.drone_sim.drone.rotation_z)  
        return 0

    def get_flight_time(self) -> int:
        """Return total flight time in seconds."""
        if self.is_flying:
            return int(time() - self.start_time)  
        return 0  # Not flying

    def get_speed_x(self) -> int:
        
        if self.drone_sim:
            return int(self.drone_sim.velocity.x * 3.6)  
        return 0

    def get_speed_y(self) -> int:
        
        if self.drone_sim:
            current_time = time()
            elapsed_time = current_time - self.last_time

            if elapsed_time > 0:  
                current_altitude = (self.drone_sim.drone.y * 0.1) - 0.3
                vertical_speed = (current_altitude - self.last_altitude) / elapsed_time  
                self.last_altitude = current_altitude
                self.last_time = current_time
                return int(vertical_speed * 3.6)  

        return 0

    def get_speed_z(self) -> int:
        
        if self.drone_sim:
            return int(self.drone_sim.velocity.z * 3.6)  
        return 0

    def get_acceleration_x(self) -> float:
        """Return the current acceleration in the X direction."""
        if self.drone_sim:
            return self.drone_sim.acceleration.x * 100  
        return 0.0

    def get_acceleration_y(self) -> float:
        """Return the current acceleration in the Y direction."""
        if self.drone_sim:
            return self.drone_sim.acceleration.y * 100  
        return 0.0

    def get_acceleration_z(self) -> float:
        """Return the current acceleration in the Z direction."""
        if self.drone_sim:
            return self.drone_sim.acceleration.z * 100  
        return 0.0
    
    def rotate_smooth(self, angle):
        
        if self.drone_sim:
            current_yaw = self.drone_sim.drone.rotation_y
            target_yaw = current_yaw + angle
            duration = abs(angle) / 90  
            self.drone_sim.drone.animate('rotation_y', target_yaw, duration=duration, curve=curve.linear)
            print(f"Tello Simulator: Smoothly rotating {angle} degrees over {duration:.2f} seconds.")

    def change_altitude_smooth(self, direction, distance=20):
        
        if self.drone_sim:
            delta = distance / 20  
            current_altitude = self.drone_sim.drone.y

            if direction == "up":
                target_altitude = current_altitude + delta
            elif direction == "down":
                target_altitude = max(3, current_altitude - delta)  
            else:
                print(f"Invalid altitude direction: {direction}")
                return

            duration = abs(delta) * 1  
            self.drone_sim.drone.animate('y', target_altitude, duration=duration, curve=curve.in_out_quad)
            self.altitude = target_altitude
            

    
    def flip_forward(self):
        
        if self.drone_sim and self.is_flying:
            print("Tello Simulator: Performing Forward Flip!")
            self.drone_sim.animate_flip(direction="forward")

    def flip_back(self):
        
        if self.drone_sim and self.is_flying:
            print("Tello Simulator: Performing Backward Flip!")
            self.drone_sim.animate_flip(direction="back")

    def flip_left(self):
        
        if self.drone_sim and self.is_flying:
            print("Tello Simulator: Performing Left Flip!")
            self.drone_sim.animate_flip(direction="left")

    def flip_right(self):
        
        if self.drone_sim and self.is_flying:
            print("Tello Simulator: Performing Right Flip!")
            self.drone_sim.animate_flip(direction="right")

    def go_xyz_speed(self, x, y, z, speed):
        if self.drone_sim and self.is_flying:
            print(f"Tello Simulator: GO command to X:{x}, Y:{y}, Z:{z} at speed {speed}")
            duration = max(1, speed / 10)
            target_position = self.drone_sim.drone.position + Vec3(x / 10, y / 10, z / 10)
            self.drone_sim.drone.animate_position(target_position, duration=duration, curve=curve.in_out_quad)
        else:
            print("Tello Simulator: Cannot execute GO command. Drone not flying.")

    def curve_xyz_speed(self, x1, y1, z1, x2, y2, z2, speed):
        if self.drone_sim and self.is_flying:
            print(f"Tello Simulator: CURVE command from ({x1}, {y1}, {z1}) to ({x2}, {x2}, {z2}) at speed {speed}")
            duration = max(1, speed / 10)

            first_point = self.drone_sim.drone.position + Vec3(x1 / 10, y1 / 10, z1 / 10)
            second_point = self.drone_sim.drone.position + Vec3(x2 / 10, y2 / 10, z2 / 10)

            # Smooth curve with camera sync
            def follow_camera():
                self.drone_sim.camera_holder.position = self.drone_sim.drone.position
                self.drone_sim.camera_holder.rotation_y = self.drone_sim.drone.rotation_y

            # Follow during the first animation
            self.drone_sim.drone.animate_position(
                first_point, duration=duration / 2, curve=curve.in_out_quad)
            for t in range(int(duration * 60 // 2)):  # Assuming 60 FPS
                invoke(follow_camera, delay=t / 60)

            # Follow during the second animation
            def second_half():
                self.drone_sim.drone.animate_position(
                    second_point, duration=duration / 2, curve=curve.in_out_quad)
                for t in range(int(duration * 60 // 2)):
                    invoke(follow_camera, delay=t / 60)

            invoke(second_half, delay=duration / 2)

        else:
            print("Tello Simulator: Cannot execute CURVE command. Drone not flying.")

    def send_rc_control(self, left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity):
        
        if not self.drone_sim:
            print("[Error] Drone simulator is not initialized.")
            return

        self.drone_sim.velocity = Vec3(
            forward_backward_velocity / 100,  # forward/backward mapped to X
            up_down_velocity / 100,           # up/down mapped to Y
            -left_right_velocity / 100        # left/right mapped to Z (negated to match controls)
        )

        self.drone_sim.drone.rotation_y += yaw_velocity * 0.05  # Smooth rotation update
        print(f"[RC Control] Velocities set -> LR: {left_right_velocity}, FB: {forward_backward_velocity}, UD: {up_down_velocity}, Yaw: {yaw_velocity}")

    
    def end(self):
        
        print("Tello Simulator: Ending simulation...")
        if self.drone_sim:
            self.is_connected = False
            application.quit()

class DroneSimulator(Entity):
    def __init__(self, tello_api, **kwargs):
        super().__init__()

        self.dynamic_island = Entity(
            parent=camera.ui,
            model=Quad(radius=0.09),  # Rounded rectangle
            color=color.black50,  # Slightly transparent black
            scale=(0.5, 0.065),  # Elongated shape
            position=(0, 0.45),  # Center top position
            z=0
        )
        
        # Takeoff Indicator UI
        self.takeoff_indicator_left = Entity(
            parent=camera.ui,
            model=Circle(resolution=30),
            color=color.green,  
            scale=(0.03, 0.03, 1),  
            position=(0.07, 0.45),  
            z=-1
        )

        self.takeoff_indicator_middle = Entity(
            parent=camera.ui,
            model=Circle(resolution=30),
            color=color.green,  
            scale=(0.03, 0.03, 1),  
            position=(0.12, 0.45), 
            z=-1
        )

        
        
        self.takeoff_indicator_right = Entity(
            parent=camera.ui,
            model=Circle(resolution=30),
            color=color.green,  
            scale=(0.03, 0.03, 1),  
            position=(0.17, 0.45),  
            z=-1
        )
        
        self.help_text = Text(
            text="Controls:\nW - Forward\nS - Backward\nA - Left\nD - Right\nShift - Launch/Up\nCtrl - Down\nG - Land\nE - Emergency Land\nJ - Rotate Left\nL - Rotate Right\nC - FPV\n1 - Speed-low\n2 - Speed-medium\n3 - Speed-high\nH - Toggle Help",
            position=(-0.85, 0.43),  # Top-left position
            scale=1.2,
            color=color.white,
            visible=True
        )
        
        self.tello = tello_api
        self.drone = Entity(
            model='tello.glb',
            scale=0.06,
            position=(-15.4, 2.6, 5),
            collider='box',
            cast_shadow=True
        )


        self.car = Entity(
            model='dirty_car.glb',
            scale=0.085,  
            position=(10, 2.45, 155),  
            rotation=(0, 0, 0),
            collider='box',
            cast_shadow=True
        )

        
        self.truck = Entity(
            model='road_roller.glb',
            scale=4.0,  
            position=(-150, 2.45, 155),  
            rotation=(0, -90, 0),
            collider='box',
            cast_shadow=True
        )

        self.road_closed = Entity(
            model='road_closed.glb',
            scale=7.0,  
            position=(-15, 2, 315),  
            rotation=(0, 90, 0),
            collider='box',
            cast_shadow=True
        )
        
    
        self.business_man = Entity(
            model='business_man.glb',
            scale=7.3,  
            position=(23, 12, 155),  
            rotation=(0, 55, 0),
            collider='box',
            cast_shadow=True
        )
        
        self.man = Entity(
            model='bos_standing.glb',
            scale=10.3,  
            position=(-83, 2.8, 165),  
            rotation=(0, 120, 0),
            collider='box',
            cast_shadow=True
        )

        self.patch = Entity(
            model='pipeline_construction_site.glb',
            scale=(15, 15, 12),  
            position=(-123, 0.0, 260), 
            rotation=(0, 0, 0),
            collider='none',
            cast_shadow=True
        )
        
        self.police_man = Entity(
            model='pig.glb',
            scale=10.0,  
            position=(-35, 1.7, 230),  
            rotation=(0, -70, 0),
            collider='box',
            cast_shadow=True
        )

        self.light1 = Entity(
            model='street_light.glb',
            scale=(4, 6.5, 5),  
            position=(-55, 2.5, 260),  
            rotation=(0, -90, 0),
            collider='none',
            cast_shadow=True
        )


        self.light2 = Entity(
            model='street_light.glb',
            scale=(4, 6.5, 5),  
            position=(25, 2.5, 95),  
            rotation=(0, 90, 0),
            collider='none',
            cast_shadow=True
        )

        self.light3 = Entity(
            model='street_light.glb',
            scale=(4, 6.5, 5),  
            position=(-55, 2.5, -70),  
            rotation=(0, -90, 0),
            collider='none',
            cast_shadow=True
        )


        
        for i in range(3):
            Entity(
                model='cobblestone.glb',
                scale=(5, 10, 20),
                position=(30, 0, i * 158.5),  
            )
        for i in range(3):
            Entity(
                model='cobblestone.glb',
                scale=(5, 10, 20),
                position=(-58, 0, i * 158.5),  
            )

        self.tunnel_road = Entity(
            model='tunnel_3.glb',
            scale=(63, 45, 45),  
            position=(-199, 3.0, 380),  
            rotation=(0, 0, 0),  
            collider='None',
            cast_shadow=True
        )
        
        self.highway_road = Entity(
            model='highway.glb',
            scale=(20, 20, 5),  
            position=(-14, 2.5, 120),  
            rotation=(0, 90, 0),  
            collider='box',
            cast_shadow=True
        )

        
        self.barrier1 = Entity(
            model='construction_barrier.glb',
            scale=(3, 3, 3),  
            position=(24, 2.5, 315),  
            rotation=(0, 0, 0),  
            collider='box',
            cast_shadow=True
        )
        
        self.barrier2 = Entity(
            model='construction_barrier.glb',
            scale=(3, 3, 3),  
            position=(-54, 2.5, 315),  
            rotation=(0, 0, 0),  
            collider='box',
            cast_shadow=True
        )
        
        self.station = Entity(
            model='gas_station_-_gta_v.glb',
            scale=(12.7, 10, 10),  
            position=(-210, 2.5, 77),  
            rotation=(0, -90, 0),  
        )

        
        Entity(
            model='dirty_leaking_concrete_wall.glb',
            scale=(25, 20, 30),  
            position=(34.2, 2.5, 25),  
            rotation=(0, 90.5, 0),  
            collider='box',
            cast_shadow=True
        )

        
        Entity(
            model='dirty_leaking_concrete_wall.glb',
            scale=(25, 20, 30),  
            position=(34, 2.5, 227),  
            rotation=(0, 91, 0),  
            collider='box',
            cast_shadow=True
        )

        self.first_person_view = False
        # Create a separate entity to hold the camera
        self.camera_holder = Entity(position=self.drone.position, rotation=self.drone.rotation)   

        self.drone_camera = EditorCamera()
        self.drone_camera.parent = self.camera_holder
        self.third_person_position = (0, 5, -15)
        self.third_person_rotation = (10, 0, 0)
        self.first_person_position = (0, 0.5, 22)  
        self.drone_camera.position = self.third_person_position
        self.drone_camera.rotation = self.third_person_rotation
        self.is_flying = False

        self.velocity = Vec3(0, 0, 0)
        self.acceleration = Vec3(0, 0, 0)
        self.calculated_acceleration = Vec3(0, 0, 0)
        self.last_velocity_accel = Vec3(0, 0, 0)
        self.last_time_accel = time()
        self.drag = 0.93  
        self.rotation_speed = 5  
        self.max_speed = 1.8  
        self.accel_force = 0.65  

        self.pitch_angle = 0  
        self.roll_angle = 0  
        self.max_pitch = 20  
        self.max_roll = 20  
        self.tilt_smoothness = 0.05  

        self.create_meters()

    def get_current_fpv_view(self):
        """ Capture the current FPV camera view and return it as a texture """
        return camera.texture  # Get the current screen texture

    
    
    def update_takeoff_indicator(self):
        """Blinking effect for takeoff status"""
        pulse = (sin(time() * 5) + 1) / 2  

        if self.tello.is_flying:
            # Sky Blue Glow after Takeoff
            glow_color = color.rgba(100/255, 180/255, 225/255, pulse * 0.6 + 0.4)  
        else:
            # Green Glow before Takeoff
            glow_color = color.rgba(0/255, 255/255, 0/255, pulse * 0.6 + 0.4)  

        # Apply color changes to all three indicators
        self.takeoff_indicator_left.color = glow_color
        self.takeoff_indicator_middle.color = glow_color
        self.takeoff_indicator_right.color = glow_color

    def animate_flip(self, direction):
        
        if direction == "forward":
            self.drone.animate('rotation_x', 360, duration=0.6, curve=curve.linear)
        elif direction == "back":
            self.drone.animate('rotation_x', -360, duration=0.6, curve=curve.linear)
        elif direction == "left":
            self.drone.animate('rotation_z', -360, duration=0.6, curve=curve.linear)
        elif direction == "right":
            self.drone.animate('rotation_z', 360, duration=0.6, curve=curve.linear)
        
        # Reset rotation after flip
        invoke(self.reset_rotation, delay=0.62)
    
    def reset_rotation(self):
        
        self.drone.rotation_x = 0
        self.drone.rotation_z = 0
    
    def create_meters(self):
    
        # Main battery container
        self.battery_container = Entity(
            parent=camera.ui,
            model=Quad(radius=0.01),  
            color=color.gray,
            scale=(0.14, 0.04),  
            position=(-0.12, 0.45),
            z=-1
        )

        # Battery cap
        self.battery_cap = Entity(
            parent=self.battery_container,
            model=Quad(radius=0.004), 
            color=color.gray,
            position=(0.52, 0), 
            scale=(0.05, 0.3),  
            rotation_z=0
        )

        # Battery fill
        self.battery_fill = Entity(
            parent=self.battery_container,
            model=Quad(radius=0.01),  
            color=color.green,
            scale=(0.9, 0.7), 
            position=(-0.46, 0),  
            origin=(-0.5, 0),  
            z=-0.1
        )

        # Altitude meter
        self.altitude_meter = Text(
            text=f"Altitude: {self.tello.altitude}m",
            position=(0.63, 0.44),
            scale=0.94,
            color=color.white
        )

        # Warning text
        self.warning_text = Text(
            text="",
            position=(-0.25, 0),
            scale=3,
            color=color.red
        )

        self.orientation_text = Text(
            text="Pitch: 0° Roll: 0°",
            position=(0.63, 0.41),  # Below altitude meter
            scale=0.97,
            color=color.white
        )

        self.flight_time_text = Text(
            text="Flight Time: 0s",
            position=(0.63, 0.38),  # Below Pitch, Roll, Yaw
            scale=0.97,
            color=color.white
        )

        self.speed_x_text = Text(
            text="Speed X: 0 km/h",
            position=(0.63, 0.35),  # Below Flight Time
            scale=0.94,
            color=color.white
        )

        self.speed_y_text = Text(
            text="Speed Y: 0 km/h",
            position=(0.63, 0.32),  # Below Speed X
            scale=0.94,
            color=color.white
        )

        self.speed_z_text = Text(
            text="Speed Z: 0 km/h",
            position=(0.63, 0.29),  # Below Speed Y
            scale=0.94,
            color=color.white
        )
    
    def update_meters(self):
        """Update telemetry meters"""
        battery = self.tello.get_battery()
        
        # Update battery fill width with padding
        fill_width = 0.92 * (battery / 100)
        self.battery_fill.scale_x = fill_width
        
        # color transitions (green → yellow → orange → red)
        if battery > 60:
            factor = (battery - 60) / 40  # 100-60%: green to yellow
            col = lerp_color(color.yellow, color.green, factor)
        elif battery > 30:
            factor = (battery - 30) / 30  # 60-30%: yellow to orange
            col = lerp_color(color.orange, color.yellow, factor)
        else:
            factor = battery / 30  # 30-0%: orange to red
            col = lerp_color(color.red, color.orange, factor)
        
        self.battery_fill.color = col
        
        # Update altitude
        self.altitude_meter.text = f"Altitude: {((self.drone.y) / 10 - 3/10):.1f}m"
        
        pitch = self.tello.get_pitch()
        roll = self.tello.get_roll()
        self.orientation_text.text = f"Pitch: {pitch}°  Roll: {roll}°"

        flight_time = self.tello.get_flight_time()
        self.flight_time_text.text = f"Flight Time: {flight_time}s"

        # Update Speed X, Y, Z
        speed_x = self.tello.get_speed_x()
        speed_y = self.tello.get_speed_y()
        speed_z = self.tello.get_speed_z()
        
        self.speed_x_text.text = f"Speed X: {speed_x} km/h"
        self.speed_y_text.text = f"Speed Y: {speed_y} km/h"
        self.speed_z_text.text = f"Speed Z: {speed_z} km/h"


        # Battery warning
        current_time = time() % 1
        if battery <= 10 and battery > 0:
            if current_time < 0.5:
                self.warning_text.text = "Battery Low!"
            else:
                self.warning_text.text = ""
            print("\n========== Battery Low! ==========\n")
        
        elif battery == 0:
            self.warning_text.text = "Battery Depleted!"
            print("\n========== Battery Depleted! ==========\n")

            # **Trigger Emergency Landing**
            self.tello.emergency()
    
    def update_movement(self):
        self.velocity += self.acceleration

        if self.velocity.length() > self.max_speed:
            self.velocity = self.velocity.normalized() * self.max_speed

        self.velocity *= self.drag
        new_position = self.drone.position + self.velocity
        hit_info = raycast(self.drone.position, self.velocity.normalized(), distance=self.velocity.length(), ignore=(self.drone,))

        if not hit_info.hit:
            self.drone.position = new_position  

        if self.drone.y < 3:
            self.drone.y = 3

        self.acceleration = Vec3(0, 0, 0)

        # Apply pitch and roll to the drone
        self.drone.rotation_x = lerp(self.drone.rotation_x, self.pitch_angle, self.tilt_smoothness)
        self.drone.rotation_z = lerp(self.drone.rotation_z, self.roll_angle, self.tilt_smoothness)
        current_time = time()
        dt = current_time - self.last_time_accel

        if dt > 0:
            velocity_change = self.velocity - self.last_velocity_accel
            self.calculated_acceleration = velocity_change / dt

            self.last_velocity_accel = Vec3(self.velocity.x, self.velocity.y, self.velocity.z)
            self.last_time_accel = current_time
        if self.first_person_view:
        
            self.camera_holder.position = self.drone.position
            self.camera_holder.rotation_x = 0  # Keep horizon level
            self.camera_holder.rotation_z = 0  # Prevent roll tilting
            self.camera_holder.rotation_y = self.drone.rotation_y  # yaw only
        else:
            # Third-person view
            self.camera_holder.position = lerp(self.camera_holder.position, self.drone.position, 0.1)
            self.camera_holder.rotation_y = self.drone.rotation_y  # yaw only
            self.drone_camera.rotation_x = 10  # Prevent pitch tilting
            self.drone_camera.rotation_z = 0  # Prevent roll tilting

        self.update_meters()
    
    
    def move(self, direction, distance=10):
        self.tello.move(direction, distance)
        scale_factor = distance/10
        if direction == "forward":
            forward_vector = self.drone.forward * self.accel_force * scale_factor
            forward_vector.y = 0  
            self.acceleration += forward_vector
            self.pitch_angle = self.max_pitch  
        elif direction == "backward":
            backward_vector = -self.drone.forward * self.accel_force * scale_factor
            backward_vector.y = 0  
            self.acceleration += backward_vector
            self.pitch_angle = -self.max_pitch
        elif direction == "left":
            left_vector = -self.drone.right * self.accel_force * scale_factor
            left_vector.y = 0  
            self.acceleration += left_vector
            self.roll_angle = -self.max_roll
        elif direction == "right":
            right_vector = self.drone.right * self.accel_force * scale_factor
            right_vector.y = 0  
            self.acceleration += right_vector
            self.roll_angle = self.max_roll
    def toggle_camera_view(self):
        self.first_person_view = not self.first_person_view
        if self.first_person_view:
            # First-person view
            self.drone_camera.position = self.first_person_position
            self.drone_camera.rotation = (0, 0, 0)
        else:
            # Third-person view
            self.drone_camera.position = self.third_person_position
            self.drone_camera.rotation = self.third_person_rotation
    
    def change_altitude(self, direction, distance=5):
        delta = distance / 20
        if direction == "up":
            self.drone.y += delta 
            self.tello.altitude += delta
        elif direction == "down" and self.drone.y > 3:
            self.drone.y -= delta
            self.tello.altitude -= delta

    def rotate(self, angle):
        self.tello.rotate(angle)
        self.drone.rotation_y = lerp(self.drone.rotation_y, self.drone.rotation_y + angle, 0.2)  

    def update_pitch_roll(self):
        self.drone.rotation_x = lerp(self.drone.rotation_x, self.pitch_angle, self.tilt_smoothness)
        self.drone.rotation_z = lerp(self.drone.rotation_z, self.roll_angle, self.tilt_smoothness)


def update():
    if not drone_sim.tello.is_connected:
        return 
    if held_keys['shift']:
        if not drone_sim.tello.is_flying:
            drone_sim.tello.takeoff()
        else:
            drone_sim.change_altitude("up")
    drone_sim.update_takeoff_indicator()
    if drone_sim.tello.stream_active:
        width, height = int(window.size[0]), int(window.size[1])
        try:
            pixel_data = glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE)
            if pixel_data:
                image = Image.frombytes("RGBA", (width, height), pixel_data)
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGBA2BGR)
                
                drone_sim.tello.latest_frame = frame.copy()
                #cv2.imshow("Tello FPV Stream", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    drone_sim.tello.stream_active = False
                    cv2.destroyAllWindows()
                    print("[FPV] FPV preview stopped.")
        except Exception as e:
            print(f"[FPV] OpenGL read error: {e}")
    
    if not drone_sim.tello.is_flying:
        drone_sim.camera_holder.position = drone_sim.drone.position + Vec3(0, 3, -7)
        
        return
    
    moving = False
    rolling = False
    
    if drone_sim.tello.stream_active:
        drone_sim.tello.capture_frame()
    
    if held_keys['w']:
        drone_sim.move("forward")
        moving = True
    if held_keys['s']:
        drone_sim.move("backward")
        moving = True
    if held_keys['a']:
        drone_sim.move("left")
        rolling = True
    if held_keys['d']:
        drone_sim.move("right")
        rolling = True
    if held_keys['j']:
        drone_sim.rotate(-drone_sim.rotation_speed)
    if held_keys['l']:
        drone_sim.rotate(drone_sim.rotation_speed)
    
    if held_keys['control']:
        drone_sim.change_altitude("down")
    if not moving:
        drone_sim.pitch_angle = 0  # Reset pitch when not moving
    
    if not rolling:
        drone_sim.roll_angle = 0  # Reset roll when not rolling
    

    drone_sim.update_movement()
    drone_sim.update_pitch_roll()



app = Ursina()
window.color = color.rgb(135, 206, 235)  
window.fullscreen = False
window.borderless = False
window.fps_counter.enabled = False  
window.render_mode = 'default'  


Sky(texture='sky_sunset')

tello_sim = TelloConnector()  
drone_sim = DroneSimulator(tello_sim)  # pass TelloSimulator to DroneSimulator
tello_sim.drone_sim = drone_sim
tello_sim.connect() 
def input(key):
    current_time = time()
    # Track keypress history for triple tap detection
    if key in tello_sim.last_keys:
        tello_sim.last_keys[key].append(current_time)
        tello_sim.last_keys[key] = [t for t in tello_sim.last_keys[key] if current_time - t < 0.8]  # Keep taps within 0.8 sec
    else:
        tello_sim.last_keys[key] = [current_time]

    # Detect triple tap
    if len(tello_sim.last_keys[key]) == 3:
        if key == 'w':
            tello_sim.flip_forward()
        elif key == 's':
            tello_sim.flip_back()
        elif key == 'a':
            tello_sim.flip_left()
        elif key == 'd':
            tello_sim.flip_right()
    
    if key == 'h':
        drone_sim.help_text.visible = not drone_sim.help_text.visible
    if key == 'c':
        drone_sim.toggle_camera_view()
    if key == 'v':  
        if tello_sim.stream_active:
            tello_sim.streamoff()
        else:
            tello_sim.streamon()
    if key == 'g':  
        tello_sim.land()
    if key == 'e':  
        tello_sim.emergency()
    if key == 'r':  
        print("Opening recorded frames folder...")
        tello_sim.get_frame_read()
    if key == '1':  
        tello_sim.set_speed(30)
    if key == '2':  
        tello_sim.set_speed(43.33)
    if key == '3':  
        tello_sim.set_speed(60)

def command_listener():
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
                tello_sim.connect()
            elif data == "takeoff":
                tello_sim.takeoff()
            elif data == "land":
                tello_sim.land()
            elif data == "flip_forward":
                tello_sim.flip_forward()
            elif data == "flip_back":
                tello_sim.flip_back()
            elif data == "flip_left":
                tello_sim.flip_left()
            elif data == "flip_right":
                tello_sim.flip_right()
            elif data == "streamon":
                tello_sim.streamon()
            elif data == "streamoff":
                tello_sim.streamoff()
            elif data == "emergency":
                tello_sim.emergency()
            elif data.startswith("forward"):
                parts = data.split()
                distance = float(parts[1]) if len(parts) > 1 else 10
                drone_sim.move("forward", distance)

            elif data.startswith("backward"):
                parts = data.split()
                distance = float(parts[1]) if len(parts) > 1 else 10
                drone_sim.move("backward", distance)

            elif data.startswith("left"):
                parts = data.split()
                distance = float(parts[1]) if len(parts) > 1 else 10
                drone_sim.move("left", distance)

            elif data.startswith("right"):
                parts = data.split()
                distance = float(parts[1]) if len(parts) > 1 else 10
                drone_sim.move("right", distance)

            elif data.startswith("up"):
                parts = data.split()
                distance = float(parts[1]) if len(parts) > 1 else 10
                tello_sim.change_altitude_smooth("up", distance)

            elif data.startswith("down"):
                parts = data.split()
                distance = float(parts[1]) if len(parts) > 1 else 10
                tello_sim.change_altitude_smooth("down", distance)

            
            elif data.startswith("rotate_cw"):
                parts = data.split()
                angle = float(parts[1]) if len(parts) > 1 else 90
                tello_sim.rotate_smooth(angle)

            elif data.startswith("rotate_ccw"):
                parts = data.split()
                angle = float(parts[1]) if len(parts) > 1 else 90
                tello_sim.rotate_smooth(-angle)

            elif data.startswith("go"):
                try:
                    _, x, y, z, speed = data.split()
                    tello_sim.go_xyz_speed(float(x), float(y), float(z), float(speed))
                except ValueError:
                    print("[Error] Invalid go command format")

            elif data.startswith("send_rc_control"):
                try:
                    _, lr, fb, ud, yaw = data.split()
                    tello_sim.send_rc_control(float(lr), float(fb), float(ud), float(yaw))
                    conn.send(b"RC control applied")
                except ValueError:
                    conn.send(b"Invalid RC control parameters")

            
            elif data.startswith("curve"):
                try:
                    _, x1, y1, z1, x2, y2, z2, speed = data.split()
                    tello_sim.curve_xyz_speed(float(x1), float(y1), float(z1),
                                            float(x2), float(y2), float(z2),
                                            float(speed))
                except ValueError:
                    print("[Error] Invalid curve command format")
            
            elif data == "get_battery":
                conn.send(str(tello_sim.get_battery()).encode())
            elif data == "get_distance_tof":
                conn.send(str(100).encode())  
            elif data == "get_height":
                height = (tello_sim.drone_sim.drone.y / 10) - 0.3
                conn.send(f"{height:.1f}".encode())
            elif data == "get_flight_time":
                conn.send(str(tello_sim.get_flight_time()).encode())
            elif data == "get_speed_x":
                conn.send(str(tello_sim.get_speed_x()).encode())
            elif data == "get_speed_y":
                conn.send(str(tello_sim.get_speed_y()).encode())
            elif data == "get_speed_z":
                conn.send(str(tello_sim.get_speed_z()).encode())
            elif data == "get_acceleration_x":
                conn.send(str(tello_sim.drone_sim.calculated_acceleration.x * 100).encode())  
            elif data == "get_acceleration_y":
                conn.send(str(tello_sim.drone_sim.calculated_acceleration.y * 100).encode())
            elif data == "get_acceleration_z":
                conn.send(str(tello_sim.drone_sim.calculated_acceleration.z * 100).encode())
            elif data == "get_pitch":
                conn.send(str(tello_sim.get_pitch()).encode())
            elif data == "get_roll":
                conn.send(str(tello_sim.get_roll()).encode())
            elif data == "get_yaw":
                raw_yaw = tello_sim.drone_sim.drone.rotation_y
                yaw = ((raw_yaw + 180) % 360) - 180
                conn.send(str(yaw).encode())
            elif data == "query_attitude":
                raw_yaw = tello_sim.drone_sim.drone.rotation_y
                yaw = ((raw_yaw + 180) % 360) - 180
                attitude = {
                    "pitch": tello_sim.get_pitch(),
                    "roll": tello_sim.get_roll(),
                    "yaw": yaw
                }
                conn.send(str(attitude).encode())
            elif data == "get_current_state":
                state = "flying" if tello_sim.is_flying else "landed"
                conn.send(state.encode())

            elif data == "get_latest_frame":
                if tello_sim.saved_frames:
                    conn.send(tello_sim.saved_frames[-1].encode())
                else:
                    conn.send(b"N/A")
            
            elif data == "capture_frame":
                tello_sim.capture_frame()

            elif data.startswith("set_speed"):
                try:
                    _, speed = data.split()
                    tello_sim.set_speed(int(speed))
                except ValueError:
                    print("[Error] Invalid set_speed command format")

            elif data == "end":
                 tello_sim.end()

        conn.close()

if __name__ == "__main__":
    threading.Thread(target=command_listener, daemon=True).start()
    app.run()