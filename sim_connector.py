
from time import time

from tello_drone_simulator import TelloDroneSimulator


class TelloSimulatorConnector:
   
    def __init__(self, simulator: TelloDroneSimulator):
        self.battery_level = 100
        self.altitude = 3
        self.speed = 0
        self.rotation_angle = 0
        self.is_flying = False
        self.start_time = time()
        self.simulator = simulator  

    def connect(self):
        print("Tello Simulator: Drone connected")
        return True

    def get_battery(self):
        elapsed_time = time() - self.start_time
        self.battery_level = max(100 - int((elapsed_time / 3600) * 100), 0)  # Reduce battery over 60 min
        return self.battery_level  

    def takeoff(self):
        if not self.is_flying:
            print("Tello Simulator: Drone taking off")
            self.is_flying = True
            return "Taking off"
        return "Already in air"

    def land(self):
        if self.is_flying:
            print("Tello Simulator: Drone landing")
            self.is_flying = False
            return "Landing"
        return "Already on ground"

    def move(self, direction, distance=1):
        self.simulator.move(direction, distance)
        print(f"Tello Simulator: Moving {direction} by {distance} meters")

    def rotate(self, angle):
        self.rotation_angle += angle
        print(f"Tello Simulator: Rotating {angle} degrees")

    #def start_video_stream(self):
        #print("Tello Simulator: Starting video stream...")

   # def get_video_frame(self):
        #return "Simulated video frame"

