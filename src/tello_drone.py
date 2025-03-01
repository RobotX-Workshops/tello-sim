import os
from PIL import Image
from ursina import *  # noqa: F403
from time import time, sleep

def lerp_color(start_color, end_color, factor):
    """Custom color interpolation function"""
    return Color(
        start_color.r + (end_color.r - start_color.r) * factor,
        start_color.g + (end_color.g - start_color.g) * factor,
        start_color.b + (end_color.b - start_color.b) * factor,
        1  # Alpha channel
    )

class DroneSimulator(Entity):
    def __init__(self, tello_api, **kwargs):
        super().__init__()

        # Takeoff Indicator UI
        self.takeoff_indicator_left = Entity(
            parent=camera.ui,
            model=Circle(resolution=30),
            color=color.green,  
            scale=(0.03, 0.03, 1),  
            position=(0.69, 0.46),  
            z=-1
        )

        self.takeoff_indicator_middle = Entity(
            parent=camera.ui,
            model=Circle(resolution=30),
            color=color.green,  
            scale=(0.03, 0.03, 1),  
            position=(0.73, 0.46), 
            z=-1
        )

        self.takeoff_indicator_right = Entity(
            parent=camera.ui,
            model=Circle(resolution=30),
            color=color.green,  
            scale=(0.03, 0.03, 1),  
            position=(0.77, 0.46),  
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
            position=(-15.4, 3, 5),
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
            scale=(0.12, 0.04),  
            position=(0.73, 0.41),
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
            position=(0.67, 0.38),
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
            text="Pitch: 0°  Roll: 0°",
            position=(0.67, 0.35),  # Below altitude meter
            scale=0.97,
            color=color.white
        )

        self.flight_time_text = Text(
            text="Flight Time: 0s",
            position=(0.67, 0.32),  # Below Pitch, Roll, Yaw
            scale=0.97,
            color=color.white
        )

        self.speed_x_text = Text(
            text="Speed X: 0 km/h",
            position=(0.67, 0.29),  # Below Flight Time
            scale=0.94,
            color=color.white
        )

        self.speed_y_text = Text(
            text="Speed Y: 0 km/h",
            position=(0.67, 0.27),  # Below Speed X
            scale=0.94,
            color=color.white
        )

        self.speed_z_text = Text(
            text="Speed Z: 0 km/h",
            position=(0.67, 0.25),  # Below Speed Y
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
        else:
            self.warning_text.text = ""
    
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
    
    
    def move(self, direction):
        self.tello.move(direction, 1)

        if direction == "forward":
            forward_vector = self.drone.forward * self.accel_force
            forward_vector.y = 0  
            self.acceleration += forward_vector
            self.pitch_angle = self.max_pitch  
        elif direction == "backward":
            backward_vector = -self.drone.forward * self.accel_force
            backward_vector.y = 0  
            self.acceleration += backward_vector
            self.pitch_angle = -self.max_pitch
        elif direction == "left":
            left_vector = -self.drone.right * self.accel_force
            left_vector.y = 0  
            self.acceleration += left_vector
            self.roll_angle = -self.max_roll
        elif direction == "right":
            right_vector = self.drone.right * self.accel_force
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
    
    def change_altitude(self, direction):
        if direction == "up":
            self.drone.y += 0.27  
            self.tello.altitude += 0.27  
        elif direction == "down" and self.drone.y > 3:
            self.drone.y -= 0.20
            self.tello.altitude -= 0.20  

    def rotate(self, angle):
        self.tello.rotate(angle)
        self.drone.rotation_y = lerp(self.drone.rotation_y, self.drone.rotation_y + angle, 0.2)  

    def update_pitch_roll(self):
        self.drone.rotation_x = lerp(self.drone.rotation_x, self.pitch_angle, self.tilt_smoothness)
        self.drone.rotation_z = lerp(self.drone.rotation_z, self.roll_angle, self.tilt_smoothness)


class TelloConnector:
   
    def __init__(self, drone_sim: DroneSimulator,max_frames=50):
        self.battery_level = 100
        self.drone_sim = drone_sim
        self.altitude = 3
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

    def take_off(self):
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
        """Start capturing screenshots at a 3-second interval"""
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
            print(f"Tello Simulator: Video streaming stopped. Frames captured: {len(self.saved_frames)}")

            if self.drone_sim:
                self.drone_sim.toggle_camera_view()

    def capture_frame(self):
        """Capture and save the FPV view directly from the GPU frame buffer"""
        if not self.stream_active:
            return  

        current_time = time()

        if self.last_screenshot_time is None or current_time - self.last_screenshot_time >= self.screenshot_interval:
            self.last_screenshot_time = current_time
            frame_path = os.path.join(self.recording_folder, f"frame_{self.frame_count}.png")

            
            width, height = int(window.size[0]), int(window.size[1])

            # Capture pixels from OpenGL buffer
            pixel_data = glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE)
            if pixel_data:
                image = Image.frombytes("RGBA", (width, height), pixel_data)
                image = image.transpose(Image.FLIP_TOP_BOTTOM)  # Flip image 
                image = image.convert("RGB")  # Convert to standard RGB format
                image.save(frame_path, "PNG")

                self.saved_frames.append(frame_path)
                self.frame_count += 1
                print(f"Screenshot {self.frame_count} saved: {frame_path}")
            else:
                print("Error: Could not capture FPV view, GPU buffer unavailable.")
    
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

                # altitude = 3
                self.drone_sim.drone.animate('y', 3, duration=current_altitude * 0.5, curve=curve.in_out_quad)

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
                self.drone_sim.drone.animate('y', 3, duration=1.5, curve=curve.linear)

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
    
    def move(self, direction, distance=1):
        print(f"Tello Simulator: Moving {direction} by {distance} meters")

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
