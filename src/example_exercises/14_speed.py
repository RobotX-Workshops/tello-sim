from djitellopy import Tello

import time


TEST_DISTANCE = 30

# Create a Tello instance
tello = Tello()

# Connect to Tello
tello.connect()

print("Starting flying in ...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)

# Takeoff
print("Take off")
tello.takeoff()

tello.move_up(100)


for speed in range(10, 101, 10):
    print("Setting speed to", speed, "cm/s")
    tello.set_speed(speed)
    print("Testing forward and back at given speed")
    tello.move_forward(30)
    tello.move_back(TEST_DISTANCE)
    time.sleep(1)


print("Finished Landing")
# Land
tello.land()

# End the connection
tello.end()
