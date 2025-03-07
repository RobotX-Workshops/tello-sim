import time
from tello_client import TelloSimClient

tello = TelloSimClient()
tello.connect()

print("Starting flying in ...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)

print("Take off")
tello.takeoff()

print("Hovering for...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)

print("Landing")
tello.land()
