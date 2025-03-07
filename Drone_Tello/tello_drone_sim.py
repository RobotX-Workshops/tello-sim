from Drone_Tello.command_server import CommandServer

from Drone_Tello.ursina_adapter import UrsinaAdapter


class TelloDroneSim:
    def __init__(self):
        self.ursina_adapter = UrsinaAdapter()
        self.sever = CommandServer(self.ursina_adapter)

    def start(self):
        self.sever.run()
        
