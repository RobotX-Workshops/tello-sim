"Here try to create a script that navigates the drone through a course."

from djitellopy import Tello
import time

# Create a Tello instance
tello = Tello()

# Connect to Tello
tello.connect()

print("Starting flying in ...")
for i in range(10, 0, -1):
    print(i)
    time.sleep(1)


# Takeoff
tello.takeoff()

# Here change the commands to navigate though the course

# # Go forward 100 cm
tello.move_forward(100)

# # Turn right
# tello.rotate_clockwise(90)

# # Go forward 150 cm
# tello.move_forward(150)

#####

# Land
tello.land()

# End the connection
tello.end()
