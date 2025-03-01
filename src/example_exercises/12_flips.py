from djitellopy import Tello

import time

ROTATION_DEGREES = 90
HIGHT_CM = 10 

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


def warn_of_flip(direction: str):
    print("WARNING!")
    print(f"Flipping {direction} in ...")
    for i in range(3, 0, -1):
        print(i)
        time.sleep(1)
    flip_func = getattr(tello, f"flip_{direction}")
    flip_func()


# Takeoff
print("Take off")
tello.takeoff()

tello.move_up(HIGHT_CM)

warn_of_flip("left")

warn_of_flip("right")

warn_of_flip("forward")

warn_of_flip("back")

pause()

print("Landing")
# Land
tello.land()

# End the connection
tello.end()
