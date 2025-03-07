from typing import Literal
from ursina import *
from time import time

def lerp_color(start_color, end_color, factor):
    """Custom color interpolation function"""
    return Color(
        start_color.r + (end_color.r - start_color.r) * factor,
        start_color.g + (end_color.g - start_color.g) * factor,
        start_color.b + (end_color.b - start_color.b) * factor,
        1  # Alpha channel
    )

class UrsinaAdapter(Entity):
    def __init__(self):
        super().__init__()
        self.is_flying = False


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
    
    
    def move(self, direction: Literal["forward", "backward", "left", "right"], distance: float) -> None:
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
            self.tello.altitude += delta
        elif direction == "down" and self.drone.y > 3:
            self.drone.y -= delta
            self.tello.altitude -= delta

    def rotate(self, angle: float) -> None:
        self.tello.rotate(angle)
        self.drone.rotation_y = lerp(self.drone.rotation_y, self.drone.rotation_y + angle, 0.2)  

    def update_pitch_roll(self) -> None:
        self.drone.rotation_x = lerp(self.drone.rotation_x, self.pitch_angle, self.tilt_smoothness)
        self.drone.rotation_z = lerp(self.drone.rotation_z, self.roll_angle, self.tilt_smoothness)
        
    def send_rc_control(self, left_right_velocity_ms: float, forward_backward_velocity_ms: float, up_down_velocity_ms: float, yaw_velocity_ms: float):
        
        self.velocity = Vec3(
            forward_backward_velocity_ms / 100,  # forward/backward mapped to X
            up_down_velocity_ms / 100,           # up/down mapped to Y
            -left_right_velocity_ms / 100        # left/right mapped to Z (negated to match controls)
        )

        self.drone.rotation_y += yaw_velocity_ms * 0.05  # Smooth rotation update
        print(f"[RC Control] Velocities set -> LR: {left_right_velocity_ms}, FB: {forward_backward_velocity_ms}, UD: {up_down_velocity_ms}, Yaw: {yaw_velocity_ms}")

    def curve_xyz_speed(self, x1: float, y1: float, z1: float, x2: float, y2: float, z2: float, speed: float) -> None:
        if self.ursina_adapter and self.is_flying:


            print(f"Tello Simulator: CURVE command from ({x1}, {y1}, {z1}) to ({x2}, {x2}, {z2}) at speed {speed}")
            duration = max(1, speed / 10)

            first_point = self.drone.position + Vec3(x1 / 10, y1 / 10, z1 / 10)
            second_point = self.drone.position + Vec3(x2 / 10, y2 / 10, z2 / 10)

            # Smooth curve with camera sync ∂∂
            self.camera_holder.rotation_y = self.drone.rotation_y
            
            # Smooth curve with camera sync
            def follow_camera():
                self.camera_holder.position = self.drone.position
                self.camera_holder.rotation_y = self.drone.rotation_y

            # Follow during the first animation ∂
            self.drone.animate_position(
                first_point, duration=duration / 2, curve=curve.in_out_quad)
            for t in range(int(duration * 60 // 2)):  # Assuming 60 FPS
                invoke(follow_camera, delay=t / 60)

            # Follow during the second animation
            def second_half():
                self.drone.animate_position(
                    second_point, duration=duration / 2, curve=curve.in_out_quad)
                for t in range(int(duration * 60 // 2)):
                    invoke(follow_camera, delay=t / 60)

            invoke(second_half, delay=duration / 2)
            
        
        else:
            print("Tello Simulator: Cannot execute CURVE command. Drone not flying.")


    def takeoff(self) -> None:
    
        if not self.is_flying:
            print("Tello Simulator: Taking off...")
            
            self.is_flying = True
            target_altitude = self.drone.y + 2  # Target altitude
            self.drone.animate('y', target_altitude, duration=1, curve=curve.in_out_quad)
 ∂∂∂
            print("Tello Simulator: Takeoff successful! You can now control the drone.")
        else:
            print("Tello Simulator: Already in air.")∂