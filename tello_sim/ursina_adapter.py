import os
import json
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
    Pipe,
    pi,
    cos,
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
    destroy,
    Button,
    Slider,
    WindowPanel,
)
from time import sleep, time
from cv2.typing import MatLike


# --- Gate configuration --------------------------------------------------------
# The world isn't built to a real-world scale, and the drone model is large
# (~5.9 world units across). Gate diameters are given in nominal "cm" but scaled
# up so a 23-50 cm gate is actually big enough for the drone to fly through.
# Height/clearance uses the movement scale (1 cm -> 0.1 units).
GATE_DIAMETER_SCALE = 0.36     # cm -> world units for gate diameter (fits the drone)
UNITS_PER_CM = 0.1             # cm -> world units for gate height/clearance
GROUND_Y = 3.0                 # drone floor clamp; used as the ground reference

MIN_GATE_DIAMETER_CM = 23.0
MAX_GATE_DIAMETER_CM = 50.0
MIN_GATE_CLEARANCE_CM = 30.0   # minimum gap from ground to the bottom of the ring
MAX_GATE_CLEARANCE_CM = 200.0  # upper bound for the editor's height slider

# Lateral / along-corridor bounds for the editor position sliders.
GATE_X_RANGE = (-55.0, 25.0)
GATE_Z_RANGE = (-50.0, 370.0)
GATE_YAW_RANGE = (-180.0, 180.0)  # gate heading in degrees (0 = opening faces +z)

GATE_COLORS = {
    'yellow': color.yellow,
    'green': color.green,
    'red': color.red,
    'blue': color.blue,
    'violet': color.violet,   # Ursina's name for purple
}

# Default gate layout: alternating heights (>= 30 cm clearance) and varied
# diameters (23-50 cm) along the flight corridor. Overridden by gates.json if present.
DEFAULT_GATES = [
    {'color': 'yellow', 'x': -15, 'z': 45,  'diameter_cm': 30, 'clearance_cm': 30, 'yaw': 0},
    {'color': 'green',  'x': -15, 'z': 100, 'diameter_cm': 45, 'clearance_cm': 55, 'yaw': 0},
    {'color': 'red',    'x': -14, 'z': 200, 'diameter_cm': 23, 'clearance_cm': 40, 'yaw': 0},
    {'color': 'blue',   'x': -15, 'z': 270, 'diameter_cm': 50, 'clearance_cm': 70, 'yaw': 0},
    {'color': 'violet', 'x': -15, 'z': 340, 'diameter_cm': 35, 'clearance_cm': 45, 'yaw': 0},
]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


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
        self.bezier_path = []
        self.bezier_duration = 0
        self.bezier_start_time = None
        self.bezier_mode = False
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

        # Translucent "blur" discs over each rotor to convey spin while flying.
        # Hidden on the ground (the model's molded blades show as still).
        self.propeller_spin_speed = 6000  # degrees per second
        self.propellers = []
        # Rotor hub centers measured from the tello.glb propeller sub-meshes
        # (drone-local units; the molded blades top out at y ~= 25.1).
        rotor_offsets = [
            Vec3(-24.3, 21.5,  22.0),
            Vec3( 24.3, 21.5,  22.0),
            Vec3(-24.2, 21.5, -22.0),
            Vec3( 24.2, 21.5, -22.0),
        ]
        for i, offset in enumerate(rotor_offsets):
            spin_dir = 1 if i % 2 == 0 else -1  # counter-rotating pairs, like a real quad
            self.propellers.append((self.create_propeller(offset), spin_dir))

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
            cast_shadow=True
        )


        self.light2 = Entity(
            model='entities/street_light.glb',
            scale=(4, 6.5, 5),  
            position=(25, 2.5, 95),  
            rotation=(0, 90, 0),
            cast_shadow=True
        )

        self.light3 = Entity(
            model='entities/street_light.glb',
            scale=(4, 6.5, 5),  
            position=(-55, 2.5, -70),  
            rotation=(0, -90, 0),
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
        
        # Colored circular gates for the drone to fly through. Sizes/positions are
        # loaded from gates.json (or DEFAULT_GATES) and editable at runtime.
        self.gate_specs = self.load_gate_specs()
        self.gates = []
        self.build_gates()

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
        # Measured per-frame displacement, for telemetry. Animated moves don't
        # go through self.velocity, so speeds are derived from position deltas.
        self.measured_velocity: Vec3 = Vec3(0, 0, 0)
        self._last_position: Vec3 = Vec3(self.drone.position)
        self.acceleration: Vec3 = Vec3(0, 0, 0)
        self.calculated_acceleration: Vec3 = Vec3(0, 0, 0)
        self.last_velocity_accel: Vec3 = Vec3(0, 0, 0)
        self.last_time_accel = time()
        self.drag: float = 0.93  
        self.rotation_speed: float = 5  
        self.max_speed = 1.8
        self.accel_force = 0.65
        self.speed_cm_s = 50  # discrete-move speed (Tello range 10-100 cm/s)

        self.pitch_angle = 0  
        self.roll_angle = 0  
        self.max_pitch = 20  
        self.max_roll = 20  
        self.tilt_smoothness = 0.05  

        self.create_meters()
        self.create_gate_editor()

    # ------------------------------------------------------------------ gates ---
    def _gates_config_path(self) -> str:
        return os.path.join(os.path.dirname(__file__), 'gates.json')

    def load_gate_specs(self) -> list[dict]:
        """Load the gate layout from gates.json, falling back to the defaults."""
        path = self._gates_config_path()
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    return [dict(g) for g in data]
            except Exception as e:
                print(f"[Gates] Failed to load {path}: {e}")
        return [dict(g) for g in DEFAULT_GATES]

    def save_gate_specs(self) -> None:
        """Persist the current gate layout to gates.json."""
        path = self._gates_config_path()
        try:
            with open(path, 'w') as f:
                json.dump(self.gate_specs, f, indent=2)
            print(f"[Gates] Saved layout to {path}")
        except Exception as e:
            print(f"[Gates] Failed to save layout: {e}")

    def build_gates(self) -> None:
        """(Re)build every gate entity from self.gate_specs."""
        for gate in self.gates:
            destroy(gate)
        self.gates = [self._make_gate_entity(spec) for spec in self.gate_specs]

    def rebuild_gate(self, index: int) -> None:
        """Rebuild a single gate in place (used when its diameter changes)."""
        destroy(self.gates[index])
        self.gates[index] = self._make_gate_entity(self.gate_specs[index])

    @staticmethod
    def _gate_center_y(diameter_cm: float, clearance_cm: float) -> float:
        """Y of the ring centre so its bottom sits `clearance_cm` above ground."""
        radius = (diameter_cm / 2) * GATE_DIAMETER_SCALE
        return GROUND_Y + clearance_cm * UNITS_PER_CM + radius

    def _make_gate_entity(self, spec: dict, segments: int = 48) -> Entity:
        """Build one colored ring from a cm-based spec.

        The ring is a torus (a small Circle cross-section extruded along a
        circular path in the XY plane) so its opening faces along z, the
        drone's travel axis. No collider, so the drone flies straight through.
        """
        diameter_cm = _clamp(spec['diameter_cm'], MIN_GATE_DIAMETER_CM, MAX_GATE_DIAMETER_CM)
        clearance_cm = max(spec['clearance_cm'], MIN_GATE_CLEARANCE_CM)
        radius = (diameter_cm / 2) * GATE_DIAMETER_SCALE
        tube = max(radius * 0.09, 0.06)
        center_y = self._gate_center_y(diameter_cm, clearance_cm)
        ring_color = GATE_COLORS.get(spec.get('color'), color.white)
        path = [
            Vec3(cos(i / segments * 2 * pi) * radius,
                 sin(i / segments * 2 * pi) * radius, 0)
            for i in range(segments + 1)
        ]
        return Entity(
            model=Pipe(
                base_shape=Circle(resolution=12, radius=tube),
                path=path,
                cap_ends=False,
            ),
            color=ring_color,
            position=(spec['x'], center_y, spec['z']),
            rotation_y=spec.get('yaw', 0),  # heading: turns the ring's opening
            cast_shadow=True,
        )

    # ----------------------------------------------------------- gate editor ---
    def create_gate_editor(self) -> None:
        """Build the in-sim panel of sliders for editing gates at runtime."""
        self.selected_gate_index = 0
        self._suppress_slider_cb = False

        self.gate_x_slider = Slider(*GATE_X_RANGE, default=0, text='X', dynamic=True)
        self.gate_z_slider = Slider(*GATE_Z_RANGE, default=0, text='Z', dynamic=True)
        self.gate_dia_slider = Slider(
            MIN_GATE_DIAMETER_CM, MAX_GATE_DIAMETER_CM, default=MIN_GATE_DIAMETER_CM,
            text='Diameter', dynamic=True)
        self.gate_height_slider = Slider(
            MIN_GATE_CLEARANCE_CM, MAX_GATE_CLEARANCE_CM, default=MIN_GATE_CLEARANCE_CM,
            text='Height', dynamic=True)
        self.gate_yaw_slider = Slider(*GATE_YAW_RANGE, default=0, text='Heading', dynamic=True)

        self.gate_x_slider.on_value_changed = self._on_gate_position_changed
        self.gate_z_slider.on_value_changed = self._on_gate_position_changed
        self.gate_height_slider.on_value_changed = self._on_gate_position_changed
        self.gate_dia_slider.on_value_changed = self._on_gate_diameter_changed
        self.gate_yaw_slider.on_value_changed = self._on_gate_yaw_changed

        self.gate_select_button = Button(text='Gate: -', color=color.azure)
        self.gate_select_button.on_click = self._select_next_gate
        save_button = Button(text='Save to gates.json', color=color.green)
        save_button.on_click = self.save_gate_specs

        self.gate_editor_panel = WindowPanel(
            title='Gate Editor',
            content=(
                self.gate_select_button,
                self.gate_x_slider,
                self.gate_z_slider,
                self.gate_dia_slider,
                self.gate_height_slider,
                self.gate_yaw_slider,
                save_button,
            ),
            popup=False,
        )
        # Anchor near the top-left and shrink so the whole panel stays on screen
        # (Ursina's default sliders are wide). The panel is draggable by its title.
        self.gate_editor_panel.scale *= 0.7
        self.gate_editor_panel.x = -0.15
        self.gate_editor_panel.y = 0.4
        self.gate_editor_panel.enabled = False

        # Always-visible toggle for the editor panel.
        self.gate_editor_toggle = Button(
            parent=camera.ui, text='Edit Gates', color=color.azure,
            scale=(0.15, 0.05), position=(-0.7, -0.43),
        )
        self.gate_editor_toggle.on_click = self.toggle_gate_editor

        self._sync_editor_to_gate()

    def toggle_gate_editor(self) -> None:
        self.gate_editor_panel.enabled = not self.gate_editor_panel.enabled
        if self.gate_editor_panel.enabled:
            self._sync_editor_to_gate()

    def _update_editor_visibility(self) -> None:
        """Hide the gate editor while streaming so it isn't captured in the video."""
        streaming = self.stream_active
        self.gate_editor_toggle.enabled = not streaming
        if streaming and self.gate_editor_panel.enabled:
            self.gate_editor_panel.enabled = False

    def _select_next_gate(self) -> None:
        self.selected_gate_index = (self.selected_gate_index + 1) % len(self.gate_specs)
        self._sync_editor_to_gate()

    def _sync_editor_to_gate(self) -> None:
        """Load the selected gate's values into the sliders (without firing edits)."""
        spec = self.gate_specs[self.selected_gate_index]
        self._suppress_slider_cb = True
        self.gate_x_slider.value = _clamp(spec['x'], *GATE_X_RANGE)
        self.gate_z_slider.value = _clamp(spec['z'], *GATE_Z_RANGE)
        self.gate_dia_slider.value = _clamp(
            spec['diameter_cm'], MIN_GATE_DIAMETER_CM, MAX_GATE_DIAMETER_CM)
        self.gate_height_slider.value = _clamp(
            spec['clearance_cm'], MIN_GATE_CLEARANCE_CM, MAX_GATE_CLEARANCE_CM)
        self.gate_yaw_slider.value = _clamp(spec.get('yaw', 0), *GATE_YAW_RANGE)
        self._suppress_slider_cb = False
        self._refresh_editor_labels()

    def _refresh_editor_labels(self) -> None:
        i = self.selected_gate_index
        spec = self.gate_specs[i]
        self.gate_select_button.text = (
            f"Gate {i + 1}/{len(self.gate_specs)}: {spec.get('color', '?')}")
        self.gate_x_slider.label.text = f"X (side): {self.gate_x_slider.value:.1f}"
        self.gate_z_slider.label.text = f"Z (along): {self.gate_z_slider.value:.1f}"
        self.gate_dia_slider.label.text = f"Diameter: {self.gate_dia_slider.value:.0f} cm"
        self.gate_height_slider.label.text = f"Height: {self.gate_height_slider.value:.0f} cm"
        self.gate_yaw_slider.label.text = f"Heading: {self.gate_yaw_slider.value:.0f}°"

    def _on_gate_position_changed(self) -> None:
        if self._suppress_slider_cb:
            return
        i = self.selected_gate_index
        spec = self.gate_specs[i]
        spec['x'] = round(self.gate_x_slider.value, 2)
        spec['z'] = round(self.gate_z_slider.value, 2)
        spec['clearance_cm'] = round(
            max(self.gate_height_slider.value, MIN_GATE_CLEARANCE_CM), 1)
        gate = self.gates[i]
        gate.x = spec['x']
        gate.z = spec['z']
        gate.y = self._gate_center_y(spec['diameter_cm'], spec['clearance_cm'])
        self._refresh_editor_labels()

    def _on_gate_diameter_changed(self) -> None:
        if self._suppress_slider_cb:
            return
        i = self.selected_gate_index
        spec = self.gate_specs[i]
        spec['diameter_cm'] = round(
            _clamp(self.gate_dia_slider.value, MIN_GATE_DIAMETER_CM, MAX_GATE_DIAMETER_CM), 1)
        self.rebuild_gate(i)  # diameter changes the mesh, so rebuild it
        self._refresh_editor_labels()

    def _on_gate_yaw_changed(self) -> None:
        if self._suppress_slider_cb:
            return
        i = self.selected_gate_index
        spec = self.gate_specs[i]
        spec['yaw'] = round(self.gate_yaw_slider.value, 1)
        self.gates[i].rotation_y = spec['yaw']  # cheap: just re-orient the ring
        self._refresh_editor_labels()

    def create_propeller(self, local_pos: tuple, radius: float = 15) -> Entity:
        """Build a translucent spinning-blur visual for one rotor.

        Returns a flat pivot entity parented to the drone (so it tracks the
        drone's position, tilt and yaw for free). The pivot is spun about its
        local up-axis in `tick()`. Starts hidden; shown only while flying.
        """
        pivot = Entity(parent=self.drone, position=local_pos, visible=False)

        # Faint disc for the motion-blur halo, laid flat (facing up).
        # color.rgba here takes 0-1 floats, so alpha 0.27 keeps it translucent.
        Entity(
            parent=pivot,
            model=Circle(resolution=24, radius=radius),
            color=color.rgba(0.02, 0.02, 0.02, 0.3),
            rotation_x=90,
            double_sided=True,
        )

        # A few thin blade streaks so the rotation actually reads as motion
        # (a symmetric disc alone shows no visible change when it turns).
        for blade_angle in (0, 60, 120):
            Entity(
                parent=pivot,
                model=Quad(radius=0.05),
                color=color.rgba(0, 0, 0, 0.85),
                rotation_x=90,
                rotation_y=blade_angle,
                scale=(radius * 3.0, radius * 0.46, 1),
                double_sided=True,
            )

        return pivot

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
        # measured_velocity is in world units/s; 1 unit = 0.1 m (same scale
        # as get_speed_y's altitude), then m/s -> km/h.
        return int(self.measured_velocity.x * 0.1 * 3.6)

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
        return int(self.measured_velocity.z * 0.1 * 3.6)

    def get_acceleration_x(self) -> float:
        """Return the current acceleration in the X direction."""
        return self.calculated_acceleration.x * 100

    def get_acceleration_y(self) -> float:
        """Return the current acceleration in the Y direction."""
        return self.calculated_acceleration.y * 100

    def get_acceleration_z(self) -> float:
        """Return the current acceleration in the Z direction."""
        return self.calculated_acceleration.z * 100
    
    def rotate_smooth(self, angle):
        def command() -> None:
            target_yaw = self.drone.rotation_y + angle
            duration = max(0.5, abs(angle) / 90)
            self.drone.animate('rotation_y', target_yaw, duration=duration, curve=curve.in_out_quad)
            print(f"Tello Simulator: Smoothly rotating {angle} degrees over {duration:.2f} seconds.")
            invoke(self._motion_complete_callback, delay=duration)

        self.enqueue_command(command)

    def change_altitude_smooth(self, direction: str, distance: float) -> None:
        if direction not in ("up", "down"):
            print(f"Invalid altitude direction: {direction}")
            return

        def command() -> None:
            delta = distance / 20
            current_altitude = self.drone.y
            if direction == "up":
                target_altitude = current_altitude + delta
            else:
                target_altitude = max(3, current_altitude - delta)

            duration = max(0.5, abs(target_altitude - current_altitude))
            self.drone.animate('y', target_altitude, duration=duration, curve=curve.in_out_quad)
            self.altitude = target_altitude
            invoke(self._motion_complete_callback, delay=duration)

        self.enqueue_command(command)
    
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

        displacement = self.drone.position - self._last_position
        self._last_position = Vec3(self.drone.position)

        # Apply pitch and roll to the drone
        self.drone.rotation_x = lerp(self.drone.rotation_x, self.pitch_angle, self.tilt_smoothness)
        self.drone.rotation_z = lerp(self.drone.rotation_z, self.roll_angle, self.tilt_smoothness)
        current_time = time()
        dt = current_time - self.last_time_accel

        if dt > 0:
            # Normalize the per-frame displacement by elapsed time so the
            # telemetry speed (world units/s) is frame-rate independent.
            self.measured_velocity = displacement / dt
            velocity_change = self.measured_velocity - self.last_velocity_accel
            self.calculated_acceleration = velocity_change / dt # type: ignore

            self.last_velocity_accel = Vec3(self.measured_velocity.x, self.measured_velocity.y, self.measured_velocity.z)
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
        
    def move(self, direction: Literal["forward", "backward", "left", "right"], distance: float) -> None:
        def command() -> None:
            if direction == "forward":
                dir_vec = self.drone.forward
                self.pitch_angle = self.max_pitch
            elif direction == "backward":
                dir_vec = -self.drone.forward
                self.pitch_angle = -self.max_pitch
            elif direction == "left":
                dir_vec = -self.drone.right
                self.roll_angle = -self.max_roll
            else:
                dir_vec = self.drone.right
                self.roll_angle = self.max_roll

            dir_vec = Vec3(dir_vec.x, 0, dir_vec.z)
            if dir_vec.length() == 0:
                self._motion_complete_callback()
                return
            dir_vec = dir_vec.normalized()

            # Clamp the move short of any obstacle: the animated path bypasses
            # the per-tick velocity collision check in update_movement().
            travel = distance / 10
            hit_info = raycast(self.drone.position, dir_vec, distance=travel, ignore=(self.drone,))  # type: ignore
            if hit_info.hit:
                travel = max(0.0, hit_info.distance - 1.0)

            target_position = self.drone.position + dir_vec * travel
            duration = max(0.5, (travel * 10) / self.speed_cm_s)
            self.drone.animate_position(target_position, duration=duration, curve=curve.in_out_quad)
            # Ease the tilt back out before the move finishes.
            invoke(self._reset_tilt, delay=duration * 0.7)
            invoke(self._motion_complete_callback, delay=duration)

        self.enqueue_command(command)

    def _reset_tilt(self) -> None:
        self.pitch_angle = 0
        self.roll_angle = 0


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

    @staticmethod
    def map_coords(x: float, y: float, z: float) -> Vec3:
        """
        Maps the differences between normal robotics coordinates system to the Ursina Coordinate system
        """
        # Simulator Z-axis is positive forwards, while Tello Z-axis is positive upwards
        sim_z = x
        # Simulator X-axis is positive right, while Tello Y-axis is positive left
        sim_x = -y
        # Simulator Y-axis is positive upwards, while Tello Z-axis is positive forwards
        sim_y = z
        return Vec3(
            sim_x,
            sim_y,
            sim_z
        )
        
    def go_xyz_speed(self, x: float, y: float, z: float, speed_ms: float) -> None:
        """
        Moves in a linear path to the specified coordinates at the given speed.
        """
        def command() -> None:
            print(f"Tello Simulator: GO command to X:{x}, Y:{y}, Z:{z} at speed {speed_ms} cm/s")

            target_position = self.drone.position + self.map_coords(x / 10, y / 10, z / 10)
            direction_vector = self.map_coords(x, 0, z)
            if direction_vector.length() != 0:
                direction_vector = direction_vector.normalized()
                target_yaw = np.degrees(np.arctan2(direction_vector.x, direction_vector.z))
            else:
                target_yaw = self.drone.rotation_y

            distance_cm = self.map_coords(x, y, z).length()
            duration = max(0.5, distance_cm / speed_ms)

            self.drone.animate_position(target_position, duration=duration, curve=curve.in_out_cubic)
            self.drone.animate('rotation_y', target_yaw, duration=duration, curve=curve.in_out_cubic)
            invoke(self._motion_complete_callback, delay=duration)

        self.enqueue_command(command)

    # TODO: Is this Radians or Degrees? We should put a suffix in the argument name
    
    def start_bezier_motion(self, x1, y1, z1, x2, y2, z2, speed):
        
        # Define start, control and end points
        start = self.drone.position
        control = self.drone.position + self.map_coords(x1 / 10, y1 / 10, z1 / 10)
        end = self.drone.position + self.map_coords(x2 / 10, y2 / 10, z2 / 10)

        self.bezier_path = [start, control, end]

        chord = (end - start).length()
        cont_net = (control - start).length() + (end - control).length()
        approx_length = (chord + cont_net) / 2
        self.bezier_duration = max(1.0, approx_length / speed)
        self.bezier_start_time = time()
        self.bezier_mode = True
    
    def curve_xyz_speed(self, x1: float, y1: float, z1: float, x2: float, y2: float, z2: float, speed: float) -> None:
        def command() -> None:
            self.start_bezier_motion(x1, y1, z1, x2, y2, z2, speed)
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
        """Capture the latest FPV frame. Optionally save to disk if save_frames_to_disk is True."""
        if not self.stream_active:
            print("[Capture] Stream not active. Cannot capture frame.")
            return  

        if self.latest_frame is None:
            print("[Capture] No latest frame available.")
            return

        # Always increment frame count for tracking
        self.frame_count += 1
        print(f"[Capture] Frame {self.frame_count} captured (memory only)")
        
    def set_speed(self, x: int):
        """Set drone speed by adjusting acceleration force.
        
        Arguments:
            x (int): Speed in cm/s (10-100)
        """
        if not (10 <= x <= 100):
            print(" Invalid speed! Speed must be between 10 and 100 cm/s.")
            return


        self.speed_cm_s = x
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
        # Spin the propeller blur discs while flying; hide them when stationary
        # (the model's own molded blades show instead). Runs before the
        # is_connected check so the discs still hide after end()/disconnect.
        # land()/emergency() clear is_flying while the descent still animates,
        # so also keep spinning until the drone reaches its rest height (2.6).
        if self.is_flying or self.drone.y > 2.7:
            angle = (time() - self.start_time) * self.propeller_spin_speed
            for pivot, spin_dir in self.propellers:
                pivot.visible = True
                pivot.rotation_y = angle * spin_dir
        else:
            for pivot, _ in self.propellers:
                pivot.visible = False

        if not self.is_connected:
            return

        self.update_takeoff_indicator()

        # Keep the gate editor hidden while streaming (the FPV grabs the whole frame).
        self._update_editor_visibility()

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
        
        if self.bezier_mode:
            t_now = time()
            elapsed = t_now - self.bezier_start_time # type: ignore
            t = min(1.0, elapsed / self.bezier_duration)

            # Bézier point
            start, control, end = self.bezier_path
            pos = (1 - t)**2 * start + 2 * (1 - t)*t * control + t**2 * end
            self.drone.position = pos

            # Update yaw
            if t < 0.99:
                pos2 = (1 - t - 0.01)**2 * start + 2 * (1 - t - 0.01)*(t + 0.01) * control + (t + 0.01)**2 * end
                dir_vec = pos2 - pos
                if dir_vec.length() > 0:
                    yaw = np.degrees(np.arctan2(dir_vec.x, dir_vec.z))
                    self.drone.rotation_y = lerp(self.drone.rotation_y, yaw, 0.1)

            # Update camera
            self.camera_holder.position = pos
            self.camera_holder.rotation_y = self.drone.rotation_y

            if t >= 1.0:
                self.bezier_mode = False
                self._motion_complete_callback()
        
        if self.stream_active:
            self.capture_frame()

        if not self.is_moving:
            self.pitch_angle = 0  # Reset tilt when no move is in progress
            self.roll_angle = 0

        self.update_movement()
        self.update_pitch_roll()

    