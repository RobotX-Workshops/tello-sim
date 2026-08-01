
# This example uses TWO clients, and the split is the point:
#
#   tello -> TelloSimClient   the real Tello surface. Everything you call on
#                             it also works on real hardware.
#   sim   -> SimulatorClient  simulator-only powers. A real drone cannot tell
#                             you its true position in the room.
#
# So anything reading `sim.` below is something you would have to solve
# another way (a camera, a motion capture rig, dead reckoning) on a real Tello.

import time

from tello_sim_client import TelloSimClient
from simulator_client import SimulatorClient

# Create a Tello instance, plus a handle on the simulator itself
tello = TelloSimClient()
sim = SimulatorClient()

# Connect to Tello
tello.connect()

# --- Polling ---------------------------------------------------------------
# get_position() returns {'x': m, 'y': m, 'z': m, 'yaw': deg} on demand.
print("Position (poll):", sim.get_position())

# get_state() returns the full telemetry snapshot as a dict.
print("Full state (poll):", sim.get_state())

# --- Subscribing -----------------------------------------------------------
# subscribe_state() streams the same state dict at ~10 Hz over UDP; the
# callback runs on a background thread until unsubscribe_state() is called.
def on_state(state):
    print(f"Telemetry: x={state['x']} y={state['y']} z={state['z']} "
          f"yaw={state['yaw']} flying={state['flying']}")

sim.subscribe_state(on_state)

tello.takeoff()
tello.move_forward(50)
sim.wait_until_motion_complete()
tello.land()

time.sleep(2)
sim.unsubscribe_state()
print("Done.")
