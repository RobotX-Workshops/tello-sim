from tello_sim.tello_sim_client import TelloSimClient


import time

# Create a Tello instance
tello = TelloSimClient()

# Connect to Tello
tello.connect()

print("Get ready to throw in ...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)

print("Throw the drone within 5 seconds!")
tello.initiate_throw_takeoff()

for i in range(5, 0, -1):
    print(i)
    time.sleep(1)

print("Waiting for...")
for i in range(10, 0, -1):
    print(i)
    time.sleep(1)

print("Landing")
# Land
tello.land()

# End the connection
tello.end()
