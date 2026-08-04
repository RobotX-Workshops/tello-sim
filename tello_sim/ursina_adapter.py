import os
import json
import logging
import threading
from OpenGL.GL import glReadPixels, GL_RGBA, GL_UNSIGNED_BYTE
import numpy as np
from typing import Literal
import cv2
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
)
from time import sleep, time
import time as time_module  # ursina publishes the per-frame delta as time.dt on the module
import traceback
from cv2.typing import MatLike

logger = logging.getLogger(__name__)


# --- Gate configuration --------------------------------------------------------
# The world isn't built to a real-world scale, and the drone model is large
# (~5.9 world units across). Gate diameters are given in nominal "cm" but scaled
# up so a 23-50 cm gate is actually big enough for the drone to fly through.
# Height/clearance uses the movement scale (1 cm -> 0.1 units).
GATE_DIAMETER_SCALE = 0.36     # cm -> world units for gate diameter (fits the drone)
UNITS_PER_CM = 0.1             # cm -> world units for gate height/clearance
GROUND_Y = 3.0                 # drone floor clamp; used as the ground reference

RC_YAW_RATE_DEG_S = 1.0             # deg/s per rc stick unit; full stick (100) ≈ 100 deg/s
BATTERY_FLIGHT_DURATION_S = 3600.0  # full battery lasts this much accumulated flight time

# On-screen telemetry overlay: battery bar, altitude/orientation/speed readouts, and the
# pulsing takeoff-status dots. Off by default — it clutters the view and, because the FPV
# path grabs the whole framebuffer, it gets burned into captured photos and video.
# Set to True to restore it.
SHOW_HUD = False

# Keyboard shortcuts. Nothing is drawn on screen for these; the bindings are printed to
# the console on startup by print_controls().
# Ursina reports modifier keys per side ('left shift'/'right shift' — see the
# _input_name_changes map in ursina/main.py); a bare 'shift' event is never emitted, so
# takeoff has to accept both.
LAND_KEY = 'l'
RESET_VIEW_KEY = 'v'
TAKEOFF_KEYS = ('left shift', 'right shift')
TAKEOFF_LABEL = 'shift'

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

# --- People ---------------------------------------------------------------------
# The pedestrians scattered along the corridor. Unlike the rest of the scenery
# (cars, barriers, street lights) these are repositionable at runtime from the
# scene editor, so they live in a registry keyed by name rather than as one-off
# attributes. `model`/`scale` are fixed; only x/y/z/yaw are editable and
# persisted to people.json.
DEFAULT_PEOPLE = [
    {'name': 'business_man', 'model': 'entities/business_man.glb', 'scale': 7.3,
     'x': 23, 'y': 12, 'z': 155, 'yaw': 55},
    {'name': 'man', 'model': 'entities/bos_standing.glb', 'scale': 10.3,
     'x': -83, 'y': 2.8, 'z': 165, 'yaw': 120},
    {'name': 'police_man', 'model': 'entities/pig.glb', 'scale': 10.0,
     'x': -35, 'y': 1.7, 'z': 230, 'yaw': -70},
]

# Bounds for the people position sliders. Wider than the gate ranges: the gates
# sit in the flight corridor, but the people stand out on the verges (x = -83
# through 23 by default) and need room to be moved further out.
PERSON_X_RANGE = (-220.0, 40.0)
PERSON_Y_RANGE = (0.0, 30.0)
PERSON_Z_RANGE = (-70.0, 390.0)
PERSON_YAW_RANGE = (-180.0, 180.0)

# Editable fields, and the range each is clamped to. The scene editor reads
# these bounds off the wire (get_scene) rather than duplicating them.
GATE_FIELD_RANGES = {
    'x': GATE_X_RANGE,
    'z': GATE_Z_RANGE,
    'diameter_cm': (MIN_GATE_DIAMETER_CM, MAX_GATE_DIAMETER_CM),
    'clearance_cm': (MIN_GATE_CLEARANCE_CM, MAX_GATE_CLEARANCE_CM),
    'yaw': GATE_YAW_RANGE,
}
PERSON_FIELD_RANGES = {
    'x': PERSON_X_RANGE,
    'y': PERSON_Y_RANGE,
    'z': PERSON_Z_RANGE,
    'yaw': PERSON_YAW_RANGE,
}


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
        # The scheduled Sequence returned by the latest
        # invoke(self._motion_complete_callback, ...). Commands are serialized
        # through command_queue/is_moving, so at most one is ever pending. Held
        # so emergency() can cancel it — a stale callback firing after an
        # emergency (and a subsequent takeoff/move) would otherwise flip
        # is_moving and launch the next queued command mid-flight.
        self._motion_complete_seq = None
        # The scheduled Sequence returned by the deferred land retry —
        # invoke(self._deferred_land_callback, delay=1.0) when a movement is
        # still in progress. land() refuses to schedule a second retry while
        # this is set, so at most one is ever pending and emergency() cancelling
        # it is sufficient. Held so emergency() can cancel it; a stale deferred
        # land firing after an emergency (and a subsequent takeoff/move) would
        # otherwise flip is_flying and begin descending mid-flight.
        self._deferred_land_seq = None
        Sky(texture='sky_sunset')
        
        self.is_flying = False
        self.battery_level = 100
        # Tracks the last battery warning tier logged ("", "low", "depleted")
        # so the console message prints once per transition rather than every
        # frame across the whole 10%-to-0% interval.
        self._battery_warning_state = ""
        self.altitude = 0
        self.start_time = time()
        self.last_time = self.start_time
        self.last_tick_time = time()
        self.total_flight_seconds = 0.0
        self.takeoff_time = None
        self.rc_control = None
        self.stream_active = False
        self.is_connected = False
        self.frame_count = 0
        self.latest_frame = None
        self.last_altitude = self.altitude
        # Vertical speed (km/h) sampled once per tick by _sample_vertical_speed().
        # get_speed_y() only reads it, so the reading no longer depends on how
        # often the API is polled or on whether the HUD is drawn.
        self._vertical_speed_kmh = 0
        self.bezier_path = []
        self.bezier_duration = 0
        self.bezier_start_time = None
        self.bezier_mode = False
        self.show_hud = SHOW_HUD
        # Scene edits arriving from the command server's socket thread, applied
        # on the main thread by _apply_scene_edits(). Gate diameter changes
        # destroy and rebuild a Pipe mesh, and Panda3D scene-graph surgery off
        # the render thread is a crash risk — same reason send_rc_control()
        # defers to _apply_rc_control(). Keyed by (kind, target, field) so a
        # slider drag coalesces to its latest value instead of applying every
        # intermediate one.
        self._pending_scene_edits = {}
        self._scene_edit_lock = threading.Lock()

        if self.show_hud:
            self.create_takeoff_indicator()

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
        
    
        # The pedestrians are built from a spec registry (people.json, falling
        # back to DEFAULT_PEOPLE) so the scene editor can move them at runtime.
        self.person_specs = self.load_person_specs()
        self.people = {}
        self.build_people()

        self.patch = Entity(
            model='entities/pipeline_construction_site.glb',
            scale=(15, 15, 12),  
            position=(-123, 0.0, 260), 
            rotation=(0, 0, 0),
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
        self.grounded_camera_offset = Vec3(0, 3, -7)  # holder offset while landed
        # Create a separate entity to hold the camera. Seed it with the grounded
        # offset the tick applies once connected, so the pre-connect framing is
        # the same one reset_view() restores — otherwise pressing RESET_VIEW_KEY
        # before connecting shifts the view instead of leaving it alone.
        self.camera_holder = Entity(
            position=self.drone.position + self.grounded_camera_offset,
            rotation=self.drone.rotation,
        )

        self.drone_camera = EditorCamera()
        self.drone_camera.parent = self.camera_holder
        self.third_person_position = (0, 5, -15)
        self.third_person_rotation = (10, 0, 0)
        self.first_person_position = (0, 0.5, 22)
        self.first_person_rotation = (0, 0, 0)
        self.drone_camera.position = self.third_person_position
        self.drone_camera.rotation = self.third_person_rotation

        # Snapshot for reset_view(). EditorCamera lets the user orbit/pan/zoom freely and
        # never restores any of it, so remember where the view started. camera.position /
        # camera.fov already hold Ursina's defaults here: EditorCamera.on_enable runs during
        # its __init__, and the reparent above doesn't re-fire it.
        self._default_camera_local_position = Vec3(camera.position)
        self._default_camera_target_z = self.drone_camera.target_z
        self._default_camera_fov = camera.fov
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

        if self.show_hud:
            self.create_meters()

    # ----------------------------------------------------------------- people ---
    def _people_config_path(self) -> str:
        return os.path.join(os.path.dirname(__file__), 'people.json')

    def load_person_specs(self) -> list[dict]:
        """Load the people layout from people.json, falling back to the defaults.

        Saved specs are merged *onto* DEFAULT_PEOPLE by name rather than
        replacing the list, so a hand-edited or stale file can neither drop a
        person from the scene nor introduce one with no model to load.
        """
        specs = [dict(p) for p in DEFAULT_PEOPLE]
        path = self._people_config_path()
        if not os.path.exists(path):
            return specs
        try:
            with open(path) as f:
                data = json.load(f)
            required = {'name', 'x', 'y', 'z'}
            if not (isinstance(data, list)
                    and all(isinstance(p, dict) and required <= p.keys() for p in data)):
                print(f"[People] {path} is invalid or missing required keys; using defaults")
                return specs
            saved = {p['name']: p for p in data}
            for spec in specs:
                override = saved.get(spec['name'])
                if override:
                    # model/scale stay whatever the defaults say — only the
                    # placement is editable.
                    for field in PERSON_FIELD_RANGES:
                        if field in override:
                            spec[field] = override[field]
        except Exception as e:
            print(f"[People] Failed to load {path}: {e}")
        return specs

    def save_person_specs(self) -> bool:
        """Persist the current people layout to people.json. True if written."""
        path = self._people_config_path()
        try:
            with open(path, 'w') as f:
                json.dump(self.person_specs, f, indent=2)
            print(f"[People] Saved layout to {path}")
            return True
        except Exception as e:
            print(f"[People] Failed to save layout: {e}")
            return False

    def build_people(self) -> None:
        """(Re)build every pedestrian entity from self.person_specs."""
        for person in self.people.values():
            destroy(person)
        self.people = {
            spec['name']: Entity(
                model=spec['model'],
                scale=spec['scale'],
                position=(spec['x'], spec['y'], spec['z']),
                rotation=(0, spec.get('yaw', 0), 0),
                collider='box',
                cast_shadow=True,
            )
            for spec in self.person_specs
        }

    def _person_spec(self, name: str) -> dict | None:
        return next((s for s in self.person_specs if s['name'] == name), None)

    def apply_person_spec(self, name: str) -> None:
        """Push a person's spec onto its entity. Cheap — no mesh to rebuild."""
        person = self.people.get(name)
        spec = self._person_spec(name)
        if person is None or spec is None:
            return
        person.position = (spec['x'], spec['y'], spec['z'])
        person.rotation_y = spec.get('yaw', 0)

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
                required = {'x', 'z', 'diameter_cm', 'clearance_cm'}
                if (isinstance(data, list) and data
                        and all(isinstance(g, dict) and required <= g.keys() for g in data)):
                    return [dict(g) for g in data]
                print(f"[Gates] {path} is invalid or missing required keys; using defaults")
            except Exception as e:
                print(f"[Gates] Failed to load {path}: {e}")
        return [dict(g) for g in DEFAULT_GATES]

    def save_gate_specs(self) -> bool:
        """Persist the current gate layout to gates.json. True if written."""
        path = self._gates_config_path()
        try:
            with open(path, 'w') as f:
                json.dump(self.gate_specs, f, indent=2)
            print(f"[Gates] Saved layout to {path}")
            return True
        except Exception as e:
            print(f"[Gates] Failed to save layout: {e}")
            return False

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
            for i in range(segments)
        ]
        # Repeat the exact first point rather than computing it at 2*pi: Pipe only
        # mitres the closing seam when path[0] == path[-1] exactly, and sin(2*pi)
        # is -2.4e-16, not 0. Without this the seam renders as an open wedge.
        path.append(path[0])
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

    # ---------------------------------------------------------- scene editor ---
    # The editor itself is a separate process (tools/scene_editor.py) driving
    # these methods over the command server. It used to be an in-window Ursina
    # panel, but the FPV path grabs the whole framebuffer, so anything drawn on
    # screen ended up burned into captured photos and video.
    def scene_snapshot(self) -> dict:
        """The editable scene, plus the bounds each field is clamped to.

        The editor builds its sliders from `ranges` so the limits live in one
        place (this module) rather than being duplicated client-side.
        """
        return {
            'gates': [dict(spec) for spec in self.gate_specs],
            'people': [dict(spec) for spec in self.person_specs],
            'ranges': {
                'gate': {field: list(bounds) for field, bounds in GATE_FIELD_RANGES.items()},
                'person': {field: list(bounds) for field, bounds in PERSON_FIELD_RANGES.items()},
            },
        }

    def queue_scene_edit(self, kind: str, target, field: str, value: float) -> None:
        """Validate a scene edit and queue it for the next tick.

        Raises ValueError for an unknown kind/target/field so the command
        server can answer the client synchronously; the edit itself is applied
        on the main thread by _apply_scene_edits().
        """
        if kind == 'gate':
            ranges = GATE_FIELD_RANGES
            if not isinstance(target, int) or not 0 <= target < len(self.gate_specs):
                raise ValueError(f"no gate at index {target}")
        elif kind == 'person':
            ranges = PERSON_FIELD_RANGES
            if self._person_spec(target) is None:
                raise ValueError(f"no person named '{target}'")
        else:
            raise ValueError(f"unknown target kind '{kind}'")

        if field not in ranges:
            raise ValueError(f"{kind} has no editable field '{field}'")
        clamped = round(_clamp(float(value), *ranges[field]), 2)
        with self._scene_edit_lock:
            self._pending_scene_edits[(kind, target, field)] = clamped

    def _apply_scene_edits(self) -> None:
        """Apply queued scene edits. Main thread only; called every tick."""
        if not self._pending_scene_edits:
            return
        with self._scene_edit_lock:
            edits = self._pending_scene_edits
            self._pending_scene_edits = {}

        # Diameter is baked into the Pipe mesh, so those gates need a full
        # rebuild; every other field is a transform write. Both are collected
        # per gate and applied once, since a drag can queue several edits for
        # the same gate in a single frame.
        gates_dirty = set()
        gates_to_rebuild = set()
        people_dirty = set()
        for (kind, target, field), value in edits.items():
            if kind == 'gate':
                if not 0 <= target < len(self.gate_specs):
                    continue  # the layout changed under us; drop the stale edit
                self.gate_specs[target][field] = value
                gates_dirty.add(target)
                if field == 'diameter_cm':
                    gates_to_rebuild.add(target)
            else:
                spec = self._person_spec(target)
                if spec is None:
                    continue
                spec[field] = value
                people_dirty.add(target)

        for index in gates_dirty:
            if index in gates_to_rebuild:
                # _make_gate_entity reads the whole spec, so this picks up any
                # position/heading edits queued alongside the diameter.
                self.rebuild_gate(index)
            else:
                self._apply_gate_spec(index)
        for name in people_dirty:
            self.apply_person_spec(name)

    def _apply_gate_spec(self, index: int) -> None:
        """Push a gate's spec onto its entity. Callers handle diameter changes."""
        spec = self.gate_specs[index]
        gate = self.gates[index]
        gate.x = spec['x']
        gate.z = spec['z']
        gate.y = self._gate_center_y(spec['diameter_cm'], spec['clearance_cm'])
        gate.rotation_y = spec.get('yaw', 0)

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

    def print_controls(self) -> None:
        """Print the keyboard shortcuts. Called once on startup."""
        lines = [
            "",
            "=" * 70,
            "  Tello Simulator - keyboard controls",
            "=" * 70,
            f"  {TAKEOFF_LABEL:<12} take off",
            f"  {LAND_KEY:<12} land",
            f"  {RESET_VIEW_KEY:<12} reset the camera view to its starting position",
            "",
            "  Drag with the right mouse button to orbit, the middle button to pan, and",
            f"  scroll to zoom. Press '{RESET_VIEW_KEY}' to put the view back where it started.",
            "",
            "  Gates and people are edited from a separate window: run",
            "  'python tools/scene_editor.py' (or start both with 'python run.py').",
            "  Edits apply live; 'Save' writes gates.json and people.json.",
            "",
            "  Flight can also be driven over TCP on port 9999 (see examples/).",
        ]
        if not SHOW_HUD:
            lines += [
                "",
                f"  The on-screen telemetry overlay is off (SHOW_HUD in "
                f"{os.path.basename(__file__)}).",
                "  Read telemetry with the API instead - see examples/3_drone_information.py.",
            ]
        lines += ["=" * 70, ""]
        print("\n".join(lines))

    def handle_input(self, key: str) -> None:
        """Dispatch a key press from Ursina's global input hook."""
        if key == RESET_VIEW_KEY:
            # A view control, not a flight command - no is_connected guard.
            self.reset_view()
        elif key in TAKEOFF_KEYS:
            if self.is_connected:
                self.takeoff()
            else:
                print("Tello Simulator: Not connected yet - connect first.")
        elif key == LAND_KEY:
            if self.is_connected:
                self.land()
            else:
                print("Tello Simulator: Not connected yet - connect first.")

    def run(self):
        self.print_controls()
        self.app.run()

    def connect(self):
        """Simulate connecting to the drone."""
        if not self.is_connected:
            print("Tello Simulator: Connecting...")
            sleep(1)
            self.total_flight_seconds = 0.0
            self.takeoff_time = None
            self.battery_level = 100
            self.is_connected = True
            print("Tello Simulator: Connection successful! "
                  f"Press '{TAKEOFF_LABEL}' to take off.")

    def create_takeoff_indicator(self):
        """Build the top-center status plate and its three pulsing dots."""
        self.dynamic_island = Entity(
            parent=camera.ui,
            model=Quad(radius=0.09),  # Rounded rectangle
            color=color.black50,  # Slightly transparent black
            scale=(0.5, 0.065),  # Elongated shape
            position=(0, 0.45),  # Center top position
            z=0
        )

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
        
    def _current_flight_seconds(self) -> float:
        """Accumulated airborne time across takeoffs, including the current flight."""
        seconds = self.total_flight_seconds
        if self.is_flying and self.takeoff_time is not None:
            seconds += time() - self.takeoff_time
        return seconds

    def _stop_flight_clock(self) -> None:
        if self.takeoff_time is not None:
            self.total_flight_seconds += time() - self.takeoff_time
            self.takeoff_time = None

    def get_battery(self) -> float:
        # Battery drains with flight time only, not wall-clock app uptime.
        drained = int(self._current_flight_seconds() / BATTERY_FLIGHT_DURATION_S * 100)
        self.battery_level = max(100 - drained, 0)
        return self.battery_level


    def get_flight_time(self) -> int:
        """Return total flight time in seconds."""
        return int(self._current_flight_seconds())
    
    def get_pitch(self) -> int:
        return int(self.drone.rotation_x) 

    def get_roll(self) -> int:
        return int(self.drone.rotation_z)  

    def get_speed_x(self) -> int:
        # measured_velocity is in world units/s; 1 unit = 0.1 m (same scale
        # as get_speed_y's altitude), then m/s -> km/h.
        return int(self.measured_velocity.x * 0.1 * 3.6)

    def _sample_vertical_speed(self) -> None:
        """Advance the vertical-speed sample. Called once per tick.

        Unlike speed X/Z, which read the per-frame `measured_velocity`, vertical
        speed is a differential over `last_altitude`/`last_time`. Sampling has to
        happen on the tick rather than inside get_speed_y(): if the getter
        advanced the state, the value would be the *average* since whenever the
        API last happened to poll, not the current speed. That used to be masked
        by update_meters() calling the getter every frame, which SHOW_HUD=False
        no longer does.
        """
        current_time = time()
        elapsed_time = current_time - self.last_time
        if elapsed_time <= 0:
            return

        current_altitude = (self.drone.y * 0.1) - 0.3
        vertical_speed = (current_altitude - self.last_altitude) / elapsed_time
        self.last_altitude = current_altitude
        self.last_time = current_time
        self._vertical_speed_kmh = int(vertical_speed * 3.6)

    def get_speed_y(self) -> int:
        return self._vertical_speed_kmh

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
            self._motion_complete_seq = invoke(self._motion_complete_callback, delay=duration)

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
            self._motion_complete_seq = invoke(self._motion_complete_callback, delay=duration)

        self.enqueue_command(command)
    
    def _check_battery_warnings(self) -> str:
        """Battery warnings and the automatic emergency landing at 0%.

        Runs every frame regardless of show_hud: the emergency landing is flight
        behaviour, not display. Returns the text the HUD should show ("" for none).
        """
        battery = self.get_battery()

        if 0 < battery <= 10:
            # Log only when we first cross into the low-battery tier, not every
            # frame, but keep blinking the on-screen warning twice a second.
            if self._battery_warning_state != "low":
                print("\n========== Battery Low! ==========\n")
                self._battery_warning_state = "low"
            return "Battery Low!" if time() % 1 < 0.5 else ""

        if battery == 0:
            if self._battery_warning_state != "depleted":
                print("\n========== Battery Depleted! ==========\n")
                self._battery_warning_state = "depleted"
            if self.is_flying:
                self.emergency()
            return "Battery Depleted!"

        self._battery_warning_state = ""
        return ""

    def update_meters(self, warning: str = ""):
        """Update telemetry meters. Only called when show_hud is set."""
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

        self.warning_text.text = warning


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

        warning = self._check_battery_warnings()
        if self.show_hud:
            self.update_meters(warning)

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
            self._motion_complete_seq = invoke(self._motion_complete_callback, delay=duration)

        self.enqueue_command(command)

    def _reset_tilt(self) -> None:
        self.pitch_angle = 0
        self.roll_angle = 0


    def toggle_camera_view(self) -> None:
        self.first_person_view = not self.first_person_view
        if self.first_person_view:
            # First-person view
            self.drone_camera.position = self.first_person_position
            self.drone_camera.rotation = self.first_person_rotation
        else:
            # Third-person view
            self.drone_camera.position = self.third_person_position
            self.drone_camera.rotation = self.third_person_rotation

    def reset_view(self) -> None:
        """Restore the camera to its startup framing. Bound to the RESET_VIEW_KEY press.

        EditorCamera lets the user orbit (right-drag), pan (middle-drag) and zoom
        (scroll), and none of it is fully undone by the follow code - while landed
        nothing touches the camera at all. So undo every piece here: rig offset, orbit
        rotation, zoom (target_z *and* camera.z, which is only lerped toward it) and the
        orthographic/fov state from EditorCamera's built-in shift+p shortcut. Doesn't
        touch first_person_view, which is owned by the streamon/streamoff pairing.
        """
        if self.first_person_view:
            self.drone_camera.position = self.first_person_position
            self.drone_camera.rotation = self.first_person_rotation
        else:
            self.drone_camera.position = self.third_person_position
            self.drone_camera.rotation = self.third_person_rotation

        camera.orthographic = False
        camera.position = self._default_camera_local_position
        self.drone_camera.target_z = self._default_camera_target_z
        camera.fov = self._default_camera_fov
        self.drone_camera.target_fov = self._default_camera_fov

        # Snap the follower so the view doesn't drift back over the next second
        # (mirrors the per-frame logic in update_movement/_tick_impl).
        if self.is_flying:
            self.camera_holder.position = self.drone.position
        else:
            self.camera_holder.position = self.drone.position + self.grounded_camera_offset
        self.camera_holder.rotation = (0, self.drone.rotation_y, 0)

        print("Tello Simulator: View reset.")
    
    def send_rc_control(self, left_right_velocity_ms: float, forward_backward_velocity_ms: float, up_down_velocity_ms: float, yaw_velocity_ms: float):
        # Store the stick values atomically; tick() applies them in the body
        # frame on the main thread each frame (see _apply_rc_control).
        self.rc_control = (left_right_velocity_ms, forward_backward_velocity_ms,
                           up_down_velocity_ms, yaw_velocity_ms)
        logger.debug("[RC Control] Velocities set -> LR: %s, FB: %s, UD: %s, Yaw: %s",
                     left_right_velocity_ms, forward_backward_velocity_ms,
                     up_down_velocity_ms, yaw_velocity_ms)

    def _apply_rc_control(self) -> None:
        if self.rc_control is None:
            return
        lr, fb, ud, yaw = self.rc_control
        if yaw:
            # Positive stick = clockwise = +rotation_y, same convention as rotate_cw.
            self.drone.rotation_y += yaw * RC_YAW_RATE_DEG_S * time_module.dt
        if lr or fb or ud:
            # Body-frame translation; flatten like move() so tilt doesn't bleed
            # into the horizontal axes. Positive lr = right, positive fb = forward.
            right = Vec3(self.drone.right.x, 0, self.drone.right.z)
            forward = Vec3(self.drone.forward.x, 0, self.drone.forward.z)
            if right.length() > 0 and forward.length() > 0:
                self.velocity = (right.normalized() * (lr / 100)
                                 + forward.normalized() * (fb / 100)
                                 + Vec3(0, ud / 100, 0))

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
            self._motion_complete_seq = invoke(self._motion_complete_callback, delay=duration)

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
            if self.get_battery() <= 0:
                print("Tello Simulator: Cannot take off - battery depleted!")
                return
            print("Tello Simulator: Taking off...")

            self.is_flying = True
            self.takeoff_time = time()
            target_altitude = self.drone.y + 2  # Target altitude
            self.drone.animate('y', target_altitude, duration=1, curve=curve.in_out_quad)

            print("Tello Simulator: Takeoff successful! You can now control the drone.")
        else:
            print("Tello Simulator: Already in air.")
    
    def _motion_complete_callback(self):
        # This fired, so the sequence has run — drop the stale reference.
        self._motion_complete_seq = None
        self.is_moving = False
        self._execute_next_command()
        
    def _deferred_land_callback(self) -> None:
        # The scheduled retry has fired, so the Sequence is consumed — drop the
        # stale reference before re-entering land(). Clearing it here rather
        # than at the top of land() is what lets land() distinguish "a retry is
        # already pending" from "this call *is* the retry".
        self._deferred_land_seq = None
        self.land()

    def land(self) -> None:
        if self.is_moving:
            if self._deferred_land_seq is not None:
                # A retry is already pending. Overwriting the reference here
                # would orphan that Sequence without cancelling it: it stays
                # scheduled, but emergency() (and the next land()) can only see
                # the newest one. Each orphan re-arms itself on every tick it
                # fires, so N land() calls during one move would leave N
                # independent retry chains alive past the emergency that was
                # supposed to cancel them. land() has three unserialized entry
                # points — the command queue, the LAND_KEY handler, and end() —
                # so overlapping calls are reachable.
                print("Tello Simulator: Landing already deferred until movement completes.")
                return
            print("Tello Simulator: Movement in progress. Deferring landing...")
            self._deferred_land_seq = invoke(self._deferred_land_callback, delay=1.0)
            return
        # Not moving, so this call lands now and any retry still pending from an
        # earlier land() is redundant — cancel it rather than let it fire into an
        # already-grounded drone. No-op when this call came from the retry
        # itself, which cleared the reference before re-entering.
        if self._deferred_land_seq is not None:
            self._deferred_land_seq.kill()
            self._deferred_land_seq = None
        if self.is_flying:
            print("Tello Simulator: Drone landing...")
            current_altitude = self.drone.y
            self.drone.animate('y', 2.6, duration=current_altitude * 0.5, curve=curve.in_out_quad)
            self.is_flying = False
            self._stop_flight_clock()
            print("Landing initiated")
        else:
            print("Already on ground")
        
    def emergency(self) -> None:
        if self.is_flying:
            print(" Emergency! Stopping all motors and descending immediately!")
            # Cancel any in-flight animated move (animate_position runs on
            # Ursina's animation system, independent of the is_flying tick gate)
            # and drop queued/held commands so the drone can't keep travelling —
            # or start the next command — while it descends.
            for animation in list(self.drone.animations):
                animation.kill()
            # invoke(self._motion_complete_callback, ...) returns a standalone
            # Sequence that is NOT in self.drone.animations, so the loop above
            # never cancels it. Kill it explicitly, or a delayed callback could
            # fire after a later takeoff/move and flip is_moving / launch the
            # next queued command mid-flight.
            if self._motion_complete_seq is not None:
                self._motion_complete_seq.kill()
                self._motion_complete_seq = None
            # A deferred land retry (invoke(self._deferred_land_callback,
            # delay=1.0), scheduled while a move was in progress) is likewise a
            # standalone Sequence outside self.drone.animations. Kill it too, or
            # it could fire after a later takeoff/move and begin descending
            # mid-flight. land() dedupes, so cancelling this one reference
            # cancels every pending retry.
            if self._deferred_land_seq is not None:
                self._deferred_land_seq.kill()
                self._deferred_land_seq = None
            self.command_queue.clear()
            self.is_moving = False
            self.bezier_mode = False
            self.rc_control = None
            self._reset_tilt()

            # Stop movement
            self.velocity = Vec3(0, 0, 0)
            self.acceleration = Vec3(0, 0, 0)

            # descent to altitude = 3
            self.drone.animate('y', 2.6, duration=1.5, curve=curve.linear)

            self.is_flying = False
            self._stop_flight_clock()
            print("Emergency landing initiated")
        else:
            print("Drone is already on the ground")
        
    def get_latest_frame(self) -> MatLike:
        """Return the latest frame directly"""
        if self.latest_frame is None:
            raise Exception("No latest frame available.")
        return cv2.cvtColor(self.latest_frame, cv2.COLOR_BGR2RGB)

          
    def capture_frame(self):
        """Capture the latest FPV frame. Optionally save to disk if save_frames_to_disk is True."""
        if not self.stream_active:
            logger.debug("[Capture] Stream not active. Cannot capture frame.")
            return

        if self.latest_frame is None:
            logger.debug("[Capture] No latest frame available.")
            return

        # Always increment frame count for tracking
        self.frame_count += 1
        logger.debug("[Capture] Frame %d captured (memory only)", self.frame_count)
        
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
        Update the simulator state. Never lets an exception escape into the
        engine's task loop — one bad frame must not take down the whole sim.
        """
        self.last_tick_time = time()
        try:
            self._tick_impl()
        except Exception:
            print("[Sim] Exception in update tick:")
            traceback.print_exc()

    def _tick_impl(self) -> None:
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

        # Scene edits arrive on the command server's socket thread and are
        # applied here. Runs before the is_connected check so the scene editor
        # works whether or not a client has connected the drone.
        self._apply_scene_edits()

        if not self.is_connected:
            return

        # Sample telemetry before any of the early returns below: the drone is
        # still descending on the landing animation after is_flying clears, and
        # a grounded drone has to read 0 rather than hold the last airborne value.
        self._sample_vertical_speed()

        if self.show_hud:
            self.update_takeoff_indicator()

        if self.stream_active:
            width, height = int(window.size[0]), int(window.size[1])
            try:
                pixel_data = glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE)
                if pixel_data:
                    # glReadPixels returns rows bottom-to-top (OpenGL's origin is
                    # bottom-left), so the framebuffer has to be flipped vertically.
                    # Wrap the raw bytes as an array (a zero-copy view) rather than
                    # routing through PIL: Image.frombytes + transpose + np.array
                    # allocated three extra full-framebuffer copies on every
                    # streamed frame. cvtColor and cv2.flip each return one fresh
                    # array, so this path makes two allocations instead of four and
                    # drops the (undeclared, transitive) Pillow dependency.
                    arr = np.frombuffer(pixel_data, np.uint8).reshape(height, width, 4)  # type: ignore
                    frame = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
                    frame = cv2.flip(frame, 0)

                    # cv2.flip returns a freshly allocated array that nothing else
                    # mutates (readers re-encode/convert into new arrays), so store
                    # it directly. An extra .copy() here would duplicate the whole
                    # framebuffer on every streamed frame.
                    self.latest_frame = frame
            except Exception as e:
                print(f"[FPV] OpenGL read error: {e}")
        
        if not self.is_flying:
            self.camera_holder.position = self.drone.position + self.grounded_camera_offset
            
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

        self._apply_rc_control()
        self.update_movement()

    