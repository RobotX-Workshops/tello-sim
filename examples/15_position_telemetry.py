
import time

from tello_sim_client import TelloSimClient

# Create a Tello instance
tello = TelloSimClient()

# Connect to Tello
tello.connect()

# --- Polling ---------------------------------------------------------------
# get_position() returns {'x': m, 'y': m, 'z': m, 'yaw': deg} on demand.
print("Position (poll):", tello.get_position())

# get_state() returns the full telemetry snapshot as a dict.
print("Full state (poll):", tello.get_state())

# --- Subscribing -----------------------------------------------------------
# subscribe_state() streams the same state dict at ~10 Hz over UDP; the
# callback runs on a background thread until unsubscribe_state() is called.
def on_state(state):
    print(f"Telemetry: x={state['x']} y={state['y']} z={state['z']} "
          f"yaw={state['yaw']} flying={state['flying']}")

tello.subscribe_state(on_state)

tello.takeoff()
tello.move_forward(50)
tello.wait_until_motion_complete()
tello.land()

time.sleep(2)
tello.unsubscribe_state()
print("Done.")
