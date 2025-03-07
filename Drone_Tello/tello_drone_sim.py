from tello_simulation_server import TelloSimulationServer

from tello_drone import DroneSimulator


drone_sim = DroneSimulator()
tello_sim = TelloSimulationServer(drone_sim)  
tello_sim.connect() 
