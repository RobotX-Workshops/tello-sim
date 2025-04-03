
import time

from tello_sim.tello_sim_client import TelloSimClient


# Create a Tello instance
tello = TelloSimClient()

print("Attempting to connect to drone ...")

# Connect to Tello
tello.connect()

print("Starting flying in ...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)

# Takeoff
print("Take off")
tello.takeoff()

print("Hovering for...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)

print("Landing")
# Land
tello.land()

# End the connection
tello.end()
