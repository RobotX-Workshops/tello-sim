from tello_client import TelloConnector
import time

ROTATION_DEGREES = 90

# Create a Tello instance
tello = TelloConnector()

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

tello.go_xyz_speed(20, 20, 20, 20)

pause()

tello.curve_xyz_speed(10, 10, 10, 40, 40, 40, 10)

pause()

print("Landing")
# Land
tello.land()

# End the connection
tello.end()
