from typing import Callable
from djitellopy import Tello

import time

SPEED_SETTING_CM_S = 30
MOVEMENT_MAGNITUDE = 30
TIME_PER_ACTION_SECS = 3

# Create a Tello instance
tello = Tello()

# Connect to Tello
tello.connect()

print("Starting flying in ...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)

# Takeoff
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
    lambda: tello.send_rc_control(
        left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity
    ),
    TIME_PER_ACTION_SECS,
)

# Move forward
left_right_velocity = 0
forward_backward_velocity = MOVEMENT_MAGNITUDE
up_down_velocity = 0
yaw_velocity = 0
do_action_for_time(
    "Moving Forward",
    lambda: tello.send_rc_control(
        left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity
    ),
    TIME_PER_ACTION_SECS,
)

# Move Backwards
left_right_velocity = 0
forward_backward_velocity = -MOVEMENT_MAGNITUDE
up_down_velocity = 0
yaw_velocity = 0
do_action_for_time(
    "Moving backwards",
    lambda: tello.send_rc_control(
        left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity
    ),
    TIME_PER_ACTION_SECS,
)


# Move Left
left_right_velocity = MOVEMENT_MAGNITUDE
forward_backward_velocity = 0
up_down_velocity = 0
yaw_velocity = 0
do_action_for_time(
    "Moving left",
    lambda: tello.send_rc_control(
        left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity
    ),
    TIME_PER_ACTION_SECS,
)

# Move Right
left_right_velocity = -MOVEMENT_MAGNITUDE
forward_backward_velocity = 0
up_down_velocity = 0
yaw_velocity = 0
do_action_for_time(
    "Moving right",
    lambda: tello.send_rc_control(
        left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity
    ),
    TIME_PER_ACTION_SECS,
)

# Move Up
left_right_velocity = 0
forward_backward_velocity = 0
up_down_velocity = MOVEMENT_MAGNITUDE
yaw_velocity = 0
do_action_for_time(
    "Moving up",
    lambda: tello.send_rc_control(
        left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity
    ),
    TIME_PER_ACTION_SECS,
)

# Move down
left_right_velocity = 0
forward_backward_velocity = 0
up_down_velocity = -MOVEMENT_MAGNITUDE
yaw_velocity = 0
do_action_for_time(
    "Moving down",
    lambda: tello.send_rc_control(
        left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity
    ),
    TIME_PER_ACTION_SECS,
)

# Turn Left
left_right_velocity = 0
forward_backward_velocity = 0
up_down_velocity = 0
yaw_velocity = MOVEMENT_MAGNITUDE
do_action_for_time(
    "Turning left",
    lambda: tello.send_rc_control(
        left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity
    ),
    TIME_PER_ACTION_SECS,
)

# Turn Right
left_right_velocity = 0
forward_backward_velocity = 0
up_down_velocity = 0
yaw_velocity = -MOVEMENT_MAGNITUDE
do_action_for_time(
    "Turning right",
    lambda: tello.send_rc_control(
        left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity
    ),
    TIME_PER_ACTION_SECS,
)

print("Landing")
# Land
tello.land()

# End the connection
tello.end()
