from djitellopy import Tello

import time

ROTATION_DEGREES = 180

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

print(f"Rotating clockwise {ROTATION_DEGREES} degrees")
tello.rotate_clockwise(ROTATION_DEGREES)

pause()

print(f"Rotating counter clockwise {ROTATION_DEGREES} degrees")
tello.rotate_counter_clockwise(ROTATION_DEGREES)

pause()

print("Landing")
# Land
tello.land()

# End the connection
tello.end()
