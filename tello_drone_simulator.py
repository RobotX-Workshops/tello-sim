from sim_connector import TelloSimulatorConnector
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


class TelloDroneSimulator(Entity):
    def __init__(self, tello_api: TelloSimulatorConnector, **kwargs):
        super().__init__()

        self.help_text = Text(
            text="Controls:\nW - Forward\nS - Backward\nA - Left\nD - Right\nShift - Launch/Up\nCtrl - Down\nJ - Rotate Left\nL - Rotate Right\nC - FPV\nH - Toggle Help",
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
        self.camera_holder = Entity(position=self.drone.position)  

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

    def create_meters(self):
    
        # Main battery container
        self.battery_container = Entity(
            parent=camera.ui,
            model=Quad(radius=0.01),  
            color=color.gray,
            scale=(0.12, 0.04),  
            position=(0.74, 0.41),
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
        self.altitude_meter.text = f"Altitude: {int(self.drone.y - 3)}m"
        
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
            self.drone_camera.rotation_x = 0  # Prevent pitch tilting
            self.drone_camera.rotation_z = 0  # Prevent roll tilting

        self.update_meters()
    
    
    def move(self, direction):
        self.tello.move(direction, 1)

        if direction == "forward":
            self.acceleration += self.drone.forward * self.accel_force
            self.pitch_angle = self.max_pitch  
        elif direction == "backward":
            self.acceleration -= self.drone.forward * self.accel_force
            self.pitch_angle = -self.max_pitch  
        elif direction == "left":
            self.acceleration -= self.drone.right * self.accel_force
            self.roll_angle = -self.max_roll  
        elif direction == "right":
            self.acceleration += self.drone.right * self.accel_force
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

    #def land_drone(self):
    #    """ Land the drone when battery reaches zero """
    #    while self.drone.y > 0:
    #        self.drone.y -= 0.1
    #        self.update_meters()
    #    self.drone.y = 0
    #    self.warning_text.text = "Landed."

