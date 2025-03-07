from tello_client import TelloSimClient
import time
from typing import Callable

SPEED_SETTING_CM_S = 50
MOVEMENT_MAGNITUDE = 70
TIME_PER_ACTION_SECS = 3

tello = TelloSimClient()
tello.connect()

print("Starting flying in ...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)

print("Take off")
tello.takeoff()
print("Setting speed to", SPEED_SETTING_CM_S)
tello.set_speed(SPEED_SETTING_CM_S)


def do_action_for_time(label: str, action: Callable, time_in_seconds: int):
    print(label)
    action()
    time.sleep(time_in_seconds)

left_right_velocity = 0
forward_backward_velocity = 0
up_down_velocity = 0
yaw_velocity = 0
do_action_for_time(
    "Staying still",
    lambda: tello.send_rc_control(0, 0, 0, 0),
    TIME_PER_ACTION_SECS,
)
left_right_velocity = 0
forward_backward_velocity = MOVEMENT_MAGNITUDE
up_down_velocity = 0
yaw_velocity = 0
do_action_for_time(
    "Moving Forward",
    lambda: tello.send_rc_control(0, MOVEMENT_MAGNITUDE, 0, 0),
    TIME_PER_ACTION_SECS,
)
left_right_velocity = 0
forward_backward_velocity = -MOVEMENT_MAGNITUDE
up_down_velocity = 0
yaw_velocity = 0
do_action_for_time(
    "Moving Backwards",
    lambda: tello.send_rc_control(0, -MOVEMENT_MAGNITUDE, 0, 0),
    TIME_PER_ACTION_SECS,
)
left_right_velocity = MOVEMENT_MAGNITUDE
forward_backward_velocity = 0
up_down_velocity = 0
yaw_velocity = 0
do_action_for_time(
    "Moving Left",
    lambda: tello.send_rc_control(MOVEMENT_MAGNITUDE, 0, 0, 0),
    TIME_PER_ACTION_SECS,
)
left_right_velocity = -MOVEMENT_MAGNITUDE
forward_backward_velocity = 0
up_down_velocity = 0
yaw_velocity = 0
do_action_for_time(
    "Moving Right",
    lambda: tello.send_rc_control(-MOVEMENT_MAGNITUDE, 0, 0, 0),
    TIME_PER_ACTION_SECS,
)
left_right_velocity = 0
forward_backward_velocity = 0
up_down_velocity = MOVEMENT_MAGNITUDE
yaw_velocity = 0
do_action_for_time(
    "Moving up",
    lambda: tello.send_rc_control(0, 0, MOVEMENT_MAGNITUDE, 0),
    TIME_PER_ACTION_SECS,
)
left_right_velocity = 0
forward_backward_velocity = 0
up_down_velocity = -MOVEMENT_MAGNITUDE
yaw_velocity = 0
do_action_for_time(
    "Moving down",
    lambda: tello.send_rc_control(0, 0, -MOVEMENT_MAGNITUDE, 0),
    TIME_PER_ACTION_SECS,
)
left_right_velocity = 0
forward_backward_velocity = 0
up_down_velocity = 0
yaw_velocity = MOVEMENT_MAGNITUDE
do_action_for_time(
    "Turning left",
    lambda: tello.send_rc_control(0, 0, 0, MOVEMENT_MAGNITUDE),
    TIME_PER_ACTION_SECS,
)
left_right_velocity = 0
forward_backward_velocity = 0
up_down_velocity = 0
yaw_velocity = -MOVEMENT_MAGNITUDE
do_action_for_time(
    "Turning right",
    lambda: tello.send_rc_control(0, 0, 0, -MOVEMENT_MAGNITUDE),
    TIME_PER_ACTION_SECS,
)

print("Landing")
tello.land()
