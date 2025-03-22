from command_server import CommandServer
from ursina_adapter import UrsinaAdapter
import threading

class TelloDroneSim:
    def __init__(self):
        self._ursina_adapter = UrsinaAdapter()
        self._server = CommandServer(self._ursina_adapter)

    @property
    def state(self):
        return self._ursina_adapter

    def start(self):
        server_thread = threading.Thread(target=self._server.listen)
        server_thread.daemon = True
        server_thread.start()
        self._ursina_adapter.run()

    def update(self) -> None:
        self._ursina_adapter.tick()