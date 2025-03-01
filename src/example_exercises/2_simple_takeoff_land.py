# Create a Tello instance
import time

from tello_drone import DroneSimulator, TelloConnector


tello = TelloConnector(DroneSimulator())

print("Attempting to connect to drone ...")

# Connect to Tello
tello.connect()

print("Starting flying in ...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)

# Takeoff
print("Take off")
tello.take_off()

print("Hovering for...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)

print("Landing")
# Land
tello.land()

# End the connection
tello.end()
