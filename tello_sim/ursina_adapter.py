import os
from PIL import Image
from OpenGL.GL import glReadPixels, GL_RGBA, GL_UNSIGNED_BYTE
import numpy as np
from typing import Literal
import cv2
import numpy as np
from ursina import (
    Ursina,
    window,
    color,
    Entity,
    camera,
    Quad,
    Circle,
    sin,
    EditorCamera,
    Vec3,
    Text,
    invoke,
    curve,
    Color,
    Sky,
    raycast,
    lerp,
)
from time import sleep, time
from cv2.typing import MatLike


class UrsinaAdapter():
    """
    A wrapper for managing the simulator state and drone controls in Ursina.
    """
    
    def __init__(self):
        super().__init__()
        
        self.app = Ursina()
        window.color = color.rgb(135, 206, 235)  
        window.fullscreen = False
        window.borderless = False
        window.fps_counter.enabled = False  
        window.render_mode = 'default'  
        self.command_queue = []
        self.is_moving = False
        Sky(texture='sky_sunset')
        
        self.is_flying = False
        self.battery_level = 100
        self.altitude = 0
        self.speed = 0
        self.rotation_angle = 0
        self.last_keys = {}
        self.start_time = time()
        self.last_time = self.start_time
        self.stream_active = False
        self.is_connected = False
        self.recording_folder = "tello_recording"
        self.frame_count = 0
        self.saved_frames = []
        self.screenshot_interval = 3  
        self.latest_frame = None
        self.last_screenshot_time = None  
        self.last_altitude = self.altitude  
    
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
        
        self.drone = Entity(
            model='entities/tello.glb',
            scale=0.06,
            position=(-15.4, 2.6, 5),
            collider='box',
            cast_shadow=True
        )

        self.car = Entity(
            model='entities/dirty_car.glb',
            scale=0.085,  
            position=(10, 2.45, 155),  
            rotation=(0, 0, 0),
            collider='box',
            cast_shadow=True
        )
        
        self.truck = Entity(
            model='entities/road_roller.glb',
            scale=4.0,  
            position=(-150, 2.45, 155),  
            rotation=(0, -90, 0),
            collider='box',
            cast_shadow=True
        )

        self.road_closed = Entity(
            model='entities/road_closed.glb',
            scale=7.0,  
            position=(-15, 2, 315),  
            rotation=(0, 90, 0),
            collider='box',
            cast_shadow=True
        )
        
    
        self.business_man = Entity(
            model='entities/business_man.glb',
            scale=7.3,  
            position=(23, 12, 155),  
            rotation=(0, 55, 0),
            collider='box',
            cast_shadow=True
        )
        
        self.man = Entity(
            model='entities/bos_standing.glb',
            scale=10.3,  
            position=(-83, 2.8, 165),  
            rotation=(0, 120, 0),
            collider='box',
            cast_shadow=True
        )

        self.patch = Entity(
            model='entities/pipeline_construction_site.glb',
            scale=(15, 15, 12),  
            position=(-123, 0.0, 260), 
            rotation=(0, 0, 0),
            collider='none',
            cast_shadow=True
        )
        
        self.police_man = Entity(
            model='entities/pig.glb',
            scale=10.0,  
            position=(-35, 1.7, 230),  
            rotation=(0, -70, 0),
            collider='box',
            cast_shadow=True
        )

        self.light1 = Entity(
            model='entities/street_light.glb',
            scale=(4, 6.5, 5),  
            position=(-55, 2.5, 260),  
            rotation=(0, -90, 0),
            collider='none',
            cast_shadow=True
        )


        self.light2 = Entity(
            model='entities/street_light.glb',
            scale=(4, 6.5, 5),  
            position=(25, 2.5, 95),  
            rotation=(0, 90, 0),
            collider='none',
            cast_shadow=True
        )

        self.light3 = Entity(
            model='entities/street_light.glb',
            scale=(4, 6.5, 5),  
            position=(-55, 2.5, -70),  
            rotation=(0, -90, 0),
            collider='none',
            cast_shadow=True
        )

        for i in range(3):
            Entity(
                model='entities/cobblestone.glb',
                scale=(5, 10, 20),
                position=(30, 0, i * 158.5),  
            )
        for i in range(3):
            Entity(
                model='entities/cobblestone.glb',
                scale=(5, 10, 20),
                position=(-58, 0, i * 158.5),  
            )

        self.tunnel_road = Entity(
            model='entities/tunnel_3.glb',
            scale=(63, 45, 45),  
            position=(-199, 3.0, 380),  
            rotation=(0, 0, 0),  
            collider='None',
            cast_shadow=True
        )
        
        self.highway_road = Entity(
            model='entities/highway.glb',
            scale=(20, 20, 5),  
            position=(-14, 2.5, 120),  
            rotation=(0, 90, 0),  
            collider='box',
            cast_shadow=True
        )

        
        self.barrier1 = Entity(
            model='entities/construction_barrier.glb',
            scale=(3, 3, 3),  
            position=(24, 2.5, 315),  
            rotation=(0, 0, 0),  
            collider='box',
            cast_shadow=True
        )
        
        self.barrier2 = Entity(
            model='entities/construction_barrier.glb',
            scale=(3, 3, 3),  
            position=(-54, 2.5, 315),  
            rotation=(0, 0, 0),  
            collider='box',
            cast_shadow=True
        )
        
        self.station = Entity(
            model='entities/gas_station_-_gta_v.glb',
            scale=(12.7, 10, 10),  
            position=(-210, 2.5, 77),  
            rotation=(0, -90, 0),  
        )

        Entity(
            model='entities/dirty_leaking_concrete_wall.glb',
            scale=(25, 20, 30),  
            position=(34.2, 2.5, 25),  
            rotation=(0, 90.5, 0),  
            collider='box',
            cast_shadow=True
        )
        
        Entity(
            model='entities/dirty_leaking_concrete_wall.glb',
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

        self.velocity: Vec3 = Vec3(0, 0, 0)
        self.acceleration: Vec3 = Vec3(0, 0, 0)
        self.calculated_acceleration: Vec3 = Vec3(0, 0, 0)
        self.last_velocity_accel: Vec3 = Vec3(0, 0, 0)
        self.last_time_accel = time()
        self.drag: float = 0.93  
        self.rotation_speed: float = 5  
        self.max_speed = 1.8  
        self.accel_force = 0.65  

        self.pitch_angle = 0  
        self.roll_angle = 0  
        self.max_pitch = 20  
        self.max_roll = 20  
        self.tilt_smoothness = 0.05  

        self.create_meters()
        
    def run(self):
        self.app.run()
        
    def connect(self):
        """Simulate connecting to the drone."""
        if not self.is_connected:
            print("Tello Simulator: Connecting...")
            sleep(1)  
            self.is_connected = True
            print("Tello Simulator: Connection successful! Press 'Shift' to take off.")

    def get_current_fpv_view(self):
        """ Capture the current FPV camera view and return it as a texture """
        return camera.texture  # Get the current screen texture

    def update_takeoff_indicator(self):
        """Blinking effect for takeoff status"""
        pulse = (sin(time() * 5) + 1) / 2  

        if self.is_flying:
            # Sky Blue Glow after Takeoff
            glow_color = color.rgba(100/255, 180/255, 225/255, pulse * 0.6 + 0.4)  
        else:
            # Green Glow before Takeoff
            glow_color = color.rgba(0/255, 255/255, 0/255, pulse * 0.6 + 0.4)  

        # Apply color changes to all three indicators
        self.takeoff_indicator_left.color = glow_color
        self.takeoff_indicator_middle.color = glow_color
        self.takeoff_indicator_right.color = glow_color

    def animate_flip(self, direction: Literal["forward", "back", "left", "right"]) -> None:
        
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
        
        
    def _rotate(self, angle):
        self.rotation_angle += angle
        print(f"Tello Simulator: Rotating {angle} degrees")
    
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

        metrics_x_position = 0.51
        
        # Altitude meter
        self.altitude_meter = Text(
            text=f"Altitude: {self.altitude}m",
            position=(metrics_x_position, 0.44),
            scale=1.21,
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
            position=(metrics_x_position, 0.41),  # Below altitude meter
            scale=0.97,
            color=color.white
        )

        self.flight_time_text = Text(
            text="Flight Time: 0s",
            position=(metrics_x_position, 0.38),  # Below Pitch, Roll, Yaw
            scale=0.97,
            color=color.white
        )

        self.speed_x_text = Text(
            text="Speed X: 0 km/h",
            position=(metrics_x_position, 0.35),  # Below Flight Time
            scale=0.94,
            color=color.white
        )

        self.speed_y_text = Text(
            text="Speed Y: 0 km/h",
            position=(metrics_x_position, 0.32),  # Below Speed X
            scale=0.94,
            color=color.white
        )

        self.speed_z_text = Text(
            text="Speed Z: 0 km/h",
            position=(metrics_x_position, 0.29),  # Below Speed Y
            scale=0.94,
            color=color.white
        )
        
    @staticmethod
    def lerp_color(start_color, end_color, factor):
        """Custom color interpolation function"""
        return Color(
            start_color.r + (end_color.r - start_color.r) * factor,
            start_color.g + (end_color.g - start_color.g) * factor,
            start_color.b + (end_color.b - start_color.b) * factor,
            1  # Alpha channel
        )
        
    def get_battery(self) -> float:
        elapsed_time = time() - self.start_time
        self.battery_level = max(100 - int((elapsed_time / 3600) * 100), 0)  # Reduce battery over 60 min
        return self.battery_level  
    
    
    def get_flight_time(self) -> int:
        """Return total flight time in seconds."""
        if self.is_flying:
            return int(time() - self.start_time)  
        return 0  # Not flying
    
    def get_pitch(self) -> int:
        return int(self.drone.rotation_x) 

    def get_roll(self) -> int:
        return int(self.drone.rotation_z)  

    def get_speed_x(self) -> int:
        return int(self.velocity.x * 3.6)  

    def get_speed_y(self) -> int:
        current_time = time()
        elapsed_time = current_time - self.last_time

        if elapsed_time > 0:  
            current_altitude = (self.drone.y * 0.1) - 0.3
            vertical_speed = (current_altitude - self.last_altitude) / elapsed_time  
            self.last_altitude = current_altitude
            self.last_time = current_time
            return int(vertical_speed * 3.6)  
        return 0

    def get_speed_z(self) -> int:
        return int(self.velocity.z * 3.6)  

    def get_acceleration_x(self) -> float:
        """Return the current acceleration in the X direction."""
        return self.acceleration.x * 100  

    def get_acceleration_y(self) -> float:
        """Return the current acceleration in the Y direction."""
        return self.acceleration.y * 100  

    def get_acceleration_z(self) -> float:
        """Return the current acceleration in the Z direction."""
        return self.acceleration.z * 100  
    
    def rotate_smooth(self, angle):
        current_yaw = self.drone.rotation_y
        target_yaw = current_yaw + angle
        duration = abs(angle) / 90  
        self.drone.animate('rotation_y', target_yaw, duration=duration, curve=curve.linear)
        print(f"Tello Simulator: Smoothly rotating {angle} degrees over {duration:.2f} seconds.")

    def change_altitude_smooth(self, direction: str, distance: float):
        delta = distance / 20  
        current_altitude = self.drone.y

        if direction == "up":
            target_altitude = current_altitude + delta
        elif direction == "down":
            target_altitude = max(3, current_altitude - delta)  
        else:
            print(f"Invalid altitude direction: {direction}")
            return

        duration = abs(delta) * 1  
        self.drone.animate('y', target_altitude, duration=duration, curve=curve.in_out_quad)
        self.altitude = target_altitude
    
    def update_meters(self):
        """Update telemetry meters"""
        battery = self.get_battery()
        
        # Update battery fill width with padding
        fill_width = 0.92 * (battery / 100)
        self.battery_fill.scale_x = fill_width
        
        # color transitions (green → yellow → orange → red)
        if battery > 60:
            factor = (battery - 60) / 40  # 100-60%: green to yellow
            col = UrsinaAdapter.lerp_color(color.yellow, color.green, factor)
        elif battery > 30:
            factor = (battery - 30) / 30  # 60-30%: yellow to orange
            col = UrsinaAdapter.lerp_color(color.orange, color.yellow, factor)
        else:
            factor = battery / 30  # 30-0%: orange to red
            col = UrsinaAdapter.lerp_color(color.red, color.orange, factor)
        
        self.battery_fill.color = col
        
        # Update altitude
        self.altitude_meter.text = f"Altitude: {((self.drone.y) / 10 - 3/10):.1f}m"
        
        pitch = self.get_pitch()
        roll = self.get_roll()
        self.orientation_text.text = f"Pitch: {pitch}°  Roll: {roll}°"

        flight_time = self.get_flight_time()
        self.flight_time_text.text = f"Flight Time: {flight_time}s"

        # Update Speed X, Y, Z
        speed_x = self.get_speed_x()
        speed_y = self.get_speed_y()
        speed_z = self.get_speed_z()
        
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
            self.emergency()
    
    def update_movement(self) -> None:
        self.velocity += self.acceleration
        
        if self.velocity is None:
            raise Exception("Velocity is None")

        if self.velocity.length() > self.max_speed:
            self.velocity = self.velocity.normalized() * self.max_speed

        self.velocity *= self.drag
        new_position = self.drone.position + self.velocity
        hit_info = raycast(self.drone.position, self.velocity.normalized(), distance=self.velocity.length(), ignore=(self.drone,)) # type: ignore

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
            self.calculated_acceleration = velocity_change / dt # type: ignore

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
        
    def enqueue_command(self, command_func, *args, **kwargs):
        self.command_queue.append((command_func, args, kwargs))
        if not self.is_moving:
            self._execute_next_command()
    
    def _execute_next_command(self):
        if not self.command_queue:
            return
        self.is_moving = True
        command_func, args, kwargs = self.command_queue.pop(0)
        command_func(*args, **kwargs)
        
    def go_xyz_speed(self, x: float, y: float, z: float, speed_ms: float) -> None:
        def command():
            print(f"Tello Simulator: GO command to X:{x}, Y:{y}, Z:{z} at speed {speed_ms} cm/s")

            target_position = self.drone.position + Vec3(x / 10, y / 10, z / 10)
            direction_vector = Vec3(x, 0, z)
            if direction_vector.length() != 0:
                direction_vector = direction_vector.normalized()
                target_yaw = np.degrees(np.arctan2(direction_vector.x, direction_vector.z))
            else:
                target_yaw = self.drone.rotation_y

            distance_cm = Vec3(x, y, z).length()
            duration = max(0.5, distance_cm / speed_ms)

            self.drone.animate_position(target_position, duration=duration, curve=curve.in_out_cubic)
            self.drone.animate('rotation_y', target_yaw, duration=duration, curve=curve.in_out_cubic)
            invoke(self._motion_complete_callback, delay=duration)

        self.enqueue_command(command)
    def move(self, direction: Literal["forward", "backward", "left", "right"], distance: float) -> None:
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
            
    def toggle_camera_view(self) -> None:
        self.first_person_view = not self.first_person_view
        if self.first_person_view:
            # First-person view
            self.drone_camera.position = self.first_person_position
            self.drone_camera.rotation = (0, 0, 0)
        else:
            # Third-person view
            self.drone_camera.position = self.third_person_position
            self.drone_camera.rotation = self.third_person_rotation
    
    def change_altitude(self, direction: Literal["up", "down"], distance: float=5) -> None:
        delta = distance / 20
        if direction == "up":
            self.drone.y += delta 
            self.altitude += delta
        elif direction == "down" and self.drone.y > 3:
            self.drone.y -= delta
            self.altitude -= delta

    # TODO: Is this Radians or Degrees? We should put a suffix in the argument name
    def rotate(self, angle: float) -> None:
        self._rotate(angle)
        self.drone.rotation_y = lerp(self.drone.rotation_y, self.drone.rotation_y + angle, 0.2)  

    def update_pitch_roll(self) -> None:
        self.drone.rotation_x = lerp(self.drone.rotation_x, self.pitch_angle, self.tilt_smoothness)
        self.drone.rotation_z = lerp(self.drone.rotation_z, self.roll_angle, self.tilt_smoothness)
        
    def send_rc_control(self, left_right_velocity_ms: float, forward_backward_velocity_ms: float, up_down_velocity_ms: float, yaw_velocity_ms: float):
        
        self.velocity = Vec3(
            -left_right_velocity_ms / 100,        # LEFT/RIGHT mapped to X
            up_down_velocity_ms / 100,            # UP/DOWN mapped to Y
            forward_backward_velocity_ms / 100   # FORWARD/BACKWARD mapped to Z
        )

        self.drone.rotation_y += -yaw_velocity_ms * 0.05  # Smooth yaw rotation
        print(f"[RC Control] Velocities set -> LR: {left_right_velocity_ms}, FB: {forward_backward_velocity_ms}, UD: {up_down_velocity_ms}, Yaw: {yaw_velocity_ms}")
    # TODO: Is this Radians or Degrees? We should put a suffix in the argument name
    def curve_xyz_speed(self, x1: float, y1: float, z1: float, x2: float, y2: float, z2: float, speed: float) -> None:
        def command():
            print(f"Tello Simulator: CURVE command from ({x1}, {y1}, {z1}) to ({x2}, {y2}, {z2}) at speed {speed}")

            first_point = self.drone.position + Vec3(x1 / 10, y1 / 10, z1 / 10)
            second_point = self.drone.position + Vec3(x2 / 10, y2 / 10, z2 / 10)

            distance1 = Vec3(x1, y1, z1).length()
            distance2 = Vec3(x2 - x1, y2 - y1, z2 - z1).length()
            duration1 = max(0.5, distance1 / speed)
            duration2 = max(0.5, distance2 / speed)

            def compute_yaw(dx, dz):
                if dx == 0 and dz == 0:
                    return self.drone.rotation_y
                return np.degrees(np.arctan2(dx, dz))

            yaw1 = compute_yaw(x1, z1)
            yaw2 = compute_yaw(x2 - x1, z2 - z1)

            self.drone.animate_position(first_point, duration=duration1, curve=curve.in_out_quad)
            self.drone.animate('rotation_y', yaw1, duration=duration1, curve=curve.in_out_quad)

            def follow_camera():
                self.camera_holder.position = self.drone.position
                self.camera_holder.rotation_y = self.drone.rotation_y

            for t in range(int(duration1 * 60)):
                invoke(follow_camera, delay=t / 60)

            def second_half():
                self.drone.animate_position(second_point, duration=duration2, curve=curve.in_out_quad)
                self.drone.animate('rotation_y', yaw2, duration=duration2, curve=curve.in_out_quad)
                for t in range(int(duration2 * 60)):
                    invoke(follow_camera, delay=t / 60)
                invoke(self._motion_complete_callback, delay=duration2)

            invoke(second_half, delay=duration1)

        self.enqueue_command(command)
                
    def takeoff(self) -> None:
        if not self.is_flying:
            print("Tello Simulator: Taking off...")
            
            self.is_flying = True
            target_altitude = self.drone.y + 2  # Target altitude
            self.drone.animate('y', target_altitude, duration=1, curve=curve.in_out_quad)

            print("Tello Simulator: Takeoff successful! You can now control the drone.")
        else:
            print("Tello Simulator: Already in air.")
    
    def _motion_complete_callback(self):
        self.is_moving = False
        self._execute_next_command()
    def land(self) -> None:
        if self.is_moving:
            print("Tello Simulator: Movement in progress. Deferring landing...")
            invoke(self.land, delay=1.0)
            return
        if self.is_flying:
            print("Tello Simulator: Drone landing...")
            current_altitude = self.drone.y
            self.drone.animate('y', 2.6, duration=current_altitude * 0.5, curve=curve.in_out_quad)
            self.is_flying = False
            print("Landing initiated")
        else:
            print("Already on ground")
        
    def emergency(self) -> None:
        if self.is_flying:
            print(" Emergency! Stopping all motors and descending immediately!")
            # Stop movement 
            self.velocity = Vec3(0, 0, 0)
            self.acceleration = Vec3(0, 0, 0)

            # descent to altitude = 3
            self.drone.animate('y', 2.6, duration=1.5, curve=curve.linear)

            self.is_flying = False
            print("Emergency landing initiated")
        
        print("Drone is already on the ground")
        
    def get_latest_frame(self) -> MatLike:
        """Return the latest frame directly"""
        if self.latest_frame is None:
            raise Exception("No latest frame available.")
        return cv2.cvtColor(self.latest_frame, cv2.COLOR_BGR2RGB)

          
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
        
    def set_speed(self, x: int):
        """Set drone speed by adjusting acceleration force.
        
        Arguments:
            x (int): Speed in cm/s (10-100)
        """
        if not (10 <= x <= 100):
            print(" Invalid speed! Speed must be between 10 and 100 cm/s.")
            return

      
        self.accel_force = (x / 100) * 1.5  
        print(f" Speed set to {x} cm/s. Acceleration force: {self.accel_force}")

    def end(self) -> None:
        print("Tello Simulator: Ending simulation session...")
        self.land()
        self.is_connected = False
    
    
    def tick(self) -> None:
        """
        Update the simulator state
        """
        if not self.is_connected:
            return 
             
        self.update_takeoff_indicator()
        if self.stream_active:
            width, height = int(window.size[0]), int(window.size[1])
            try:
                pixel_data = glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE)
                if pixel_data:
                    image = Image.frombytes("RGBA", (width, height), pixel_data) # type: ignore
                    image = image.transpose(Image.FLIP_TOP_BOTTOM) # type: ignore
                    frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGBA2BGR)
                    
                    self.latest_frame = frame.copy()
                    #cv2.imshow("Tello FPV Stream", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.stream_active = False
                        cv2.destroyAllWindows()
                        print("[FPV] FPV preview stopped.")
            except Exception as e:
                print(f"[FPV] OpenGL read error: {e}")
        
        if not self.is_flying:
            self.camera_holder.position = self.drone.position + Vec3(0, 3, -7)
            
            return
        
        moving = False
        rolling = False
        
        if self.stream_active:
            self.capture_frame()
        
        

        if not moving:
            self.pitch_angle = 0  # Reset pitch when not moving
        
        if not rolling:
            self.roll_angle = 0  # Reset roll when not rolling
        
        self.update_movement()
        self.update_pitch_roll()

    