from command_server import CommandServer
from ursina_adapter import UrsinaAdapter
from threading import Thread
from ursina import Ursina
print(">>> Starting Simulation...")

class TelloDroneSim:
    def __init__(self):
        
        self.app = Ursina()

        self._ursina_adapter = UrsinaAdapter()
        self._server = CommandServer(self._ursina_adapter)

    @property
    def state(self):
        return self._ursina_adapter

    def update(self):
        self._ursina_adapter.tick()

    def start(self):
        # Register global update() BEFORE app.run()
        def update():
            self.update()

        # Start command server in a background thread
        server_thread = Thread(target=self._server.listen, daemon=True)
        server_thread.start()

        # Start simulation loop
        self.app.run()


if __name__ == "__main__":
    sim = TelloDroneSim()
    sim.start()
