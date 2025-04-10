
import time

from tello_sim.tello_sim_client import TelloSimClient

# Create a Tello instance
tello = TelloSimClient()

# Connect to Tello
tello.connect()

print("Get some information from the drone")

# Print battery capacity
battery_capacity = tello.get_battery()
print("Battery Capacity:", battery_capacity, "%")





# Print distance from time-of-flight sensor
print("Distance (TOF):", tello.get_distance_tof(), "cm")

# Print height
print("Height:", tello.get_height(), "cm")

# Print flight time
print("Flight Time:", tello.get_flight_time(), "seconds")

# Print speed in the x, y, z directions
print("Speed X:", tello.get_speed_x(), "cm/s")
print("Speed Y:", tello.get_speed_y(), "cm/s")
print("Speed Z:", tello.get_speed_z(), "cm/s")

# Print acceleration in the x, y, z directions
print("Acceleration X:", tello.get_acceleration_x(), "cm/s²")
print("Acceleration Y:", tello.get_acceleration_y(), "cm/s²")
print("Acceleration Z:", tello.get_acceleration_z(), "cm/s²")



print("Pitch", tello.get_pitch(), "degrees")

print("Roll", tello.get_roll(), "degrees")

print("Yaw", tello.get_yaw(), "degrees")

print("IMU data", tello.query_attitude())


print("State", tello.get_current_state())
