# Not verified working on normal Tello!

from tello_sim.tello_sim_client import TelloSimClient


import time

ROTATION_DEGREES = 90

# Create a Tello instance
tello = TelloSimClient()

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

# Should go forward 1m at 10 cm/s
tello.go_xyz_speed(100, 0, 0, 10)

# Should go backwards 1m at 10 cm/s
tello.go_xyz_speed(-100, 0, 0, 10)

# Should go forward  and up at 10 cm/s
# tello.go_xyz_speed(10, 10, 10, 10)
# Should go backward left and up at 10 cm/s
# tello.go_xyz_speed(-80, 10, 10, 20)


pause()

# Should go forward to the right and up at with rotations 10 cm/s
# tello.curve_xyz_speed(10, 10, 10, 20, 20, 120, 10)
# tello.curve_xyz_speed(40, 10, 140, -200, 80, 40, 20)

pause()

print("Landing")
# Land
tello.land()

# End the connection
tello.end()
