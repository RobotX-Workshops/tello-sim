import time
from tello_client import TelloConnector

ROTATION_DEGREES = 90
HEIGHT_CM = 100

tello = TelloConnector()

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


print("Take off")
tello.takeoff()

tello.move_up(HEIGHT_CM)

warn_of_flip("left")
warn_of_flip("right")
warn_of_flip("forward")
warn_of_flip("back")

pause()

print("Landing")
tello.land()

# End the simulation
tello.end()
