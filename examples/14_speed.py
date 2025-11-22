from tello_sim_client import TelloSimClient

import time

TEST_DISTANCE = 500

# Create a Tello instance
tello = TelloSimClient()

# Connect to Tello
tello.connect()

def pause(next_action: str):
    print(f"Hovering before {next_action}")
    for i in range(3, 0, -1):
        print(i)
        time.sleep(1)

print("Starting flying in ...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)

# Takeoff
print("Take off")
tello.takeoff()

pause("ascending")
tello.move_up(100)

for speed in range(10, 101, 10):
    pause(f"speed change to {speed} cm/s")
    print("Setting speed to", speed, "cm/s")
    tello.set_speed(speed)
    print(f"Testing forward and back at {speed} cm/s")
    tello.move_forward(1000)
    tello.move_back(TEST_DISTANCE)
    time.sleep(1)

pause("landing")
print("Finished Landing")
tello.land()