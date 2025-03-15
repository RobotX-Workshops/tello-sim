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
        self._ursina_adapter.connect()
        global update
        def update():
            self._ursina_adapter.tick()

        global input
        def input(key):
            sim._ursina_adapter.handle_input(key)
        # Start socket server in separate thread
        server_thread = threading.Thread(target=self._server.listen)
        server_thread.daemon = True
        server_thread.start()

        # Start Ursina application
        self._ursina_adapter.run()

if __name__ == "__main__":
    sim = TelloDroneSim()
    sim.start()
