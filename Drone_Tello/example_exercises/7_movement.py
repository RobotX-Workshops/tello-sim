from djitellopy import Tello

import time

MOVEMENT_DISTANCE_CM = 10

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


def pause(next_action: str):
    print(f"Hovering before {next_action}")
    for i in range(3, 0, -1):
        print(i)
        time.sleep(1)


pause("forward")
print(f"Moving forward {MOVEMENT_DISTANCE_CM}cm")
tello.move_forward(MOVEMENT_DISTANCE_CM)

pause("backwards")
print(f"Moving backwards {MOVEMENT_DISTANCE_CM}cm")
tello.move_back(MOVEMENT_DISTANCE_CM)

pause("left")
print(f"Moving left {MOVEMENT_DISTANCE_CM}cm")
tello.move_left(MOVEMENT_DISTANCE_CM)

pause("right")
print(f"Moving right {MOVEMENT_DISTANCE_CM}cm")
tello.move_right(MOVEMENT_DISTANCE_CM)

pause("up")
print(f"Moving up {MOVEMENT_DISTANCE_CM}cm")
tello.move_up(MOVEMENT_DISTANCE_CM)

pause("down")
print(f"Moving down {MOVEMENT_DISTANCE_CM}cm")
tello.move_down(MOVEMENT_DISTANCE_CM)

pause("landing")
print("Landing")
# Land
tello.land()

# End the connection
tello.end()
