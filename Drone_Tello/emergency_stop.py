import time
from tello_client import TelloConnector

tello = TelloConnector()

tello.connect()

print("Starting flying in ...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)

print("Take off")
tello.takeoff()

for i in range(10, 0, -1):
    print("Get Ready to catch drone!")
    print("Emergency stop in", i)
    time.sleep(1)

print("Emergency stop now!")
tello.emergency()