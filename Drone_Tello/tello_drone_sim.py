from Drone_Tello.command_server import CommandServer

from Drone_Tello.ursina_adapter import UrsinaAdapter


class TelloDroneSim:
    def __init__(self):
        self._ursina_adapter = create_ursina_adapter()
        self.sever = CommandServer(self._ursina_adapter)
        
    @property
    def state(self):
        return self._ursina_adapter

    def start(self):
        self._ursina_adapter.launch()
        self.sever.run()
        
        

sim = TelloDroneSim()
sim.start()
