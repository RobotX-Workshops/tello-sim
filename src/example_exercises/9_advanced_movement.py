# Not verified working on normal Tello!

from djitellopy import Tello

import time

ROTATION_DEGREES = 90

# Create a Tello instance
tello = Tello()

# Connect to Tello
tello.connect()

print("Starting flying in ...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)


def pause():
    print("Hovering for...")
    for i in range(3, 0, -1):
        print(i)
        time.sleep(1)


# Takeoff
print("Take off")
tello.takeoff()

pause()

tello.go_xyz_speed(10, 10, 10, 10)

pause()

tello.curve_xyz_speed(10, 10, 10, 20, 20, 20, 10)

print("Landing")
# Land
tello.land()

# End the connection
tello.end()
