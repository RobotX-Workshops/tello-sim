from Drone_Tello.command_server import CommandServer

from Drone_Tello.ursina_adapter import UrsinaAdapter


drone_sim = UrsinaAdapter()
tello_sim = CommandServer(drone_sim)  
tello_sim.connect() 
