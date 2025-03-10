from .command_server import CommandServer
from .ursina_adapter import UrsinaAdapter


class TelloDroneSim:
    def __init__(self):
        self._ursina_adapter = UrsinaAdapter()
        self._server = CommandServer(self._ursina_adapter)
        
    @property
    def state(self):
        return self._ursina_adapter

    def start(self):
        self._ursina_adapter.run()
        self._server.listen()
        
    
    def update(self) -> None:
        self._ursina_adapter.update()
